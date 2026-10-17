#!/usr/bin/env python3
"""cocotb + Icarus runner; writes a machine-readable result record.

Runs the smoke tests (must pass) and the negative control (must fail) as two
simulator invocations, then writes one JSON record with per-test pass/fail,
seed, commit and tool versions. Exit 0 only if every smoke test passed AND
the negative control failed. A missing tool is an error, never a skip.

Cold start (from the repo root):
    uv venv .venv && uv pip install --python .venv/bin/python -r verification/requirements.txt
    .venv/bin/python verification/run_tests.py

Gate-level re-run: see verification/gate-level/README.md (--sources/--toplevel).
"""

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CONTROL = "negative_control"


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)


def tool_versions():
    """Versions from each tool's own --version output; missing tool -> exit."""
    specs = {
        "iverilog": ["iverilog", "-V"],
        "verilator": ["verilator", "--version"],
        "yosys": ["yosys", "-V"],
    }
    out = {}
    for name, cmd in specs.items():
        if shutil.which(cmd[0]) is None:
            sys.exit(f"run_tests: required tool '{cmd[0]}' not found")
        r = sh(*cmd)
        lines = (r.stdout or r.stderr).strip().splitlines()
        out[name] = lines[0].strip() if lines else "unknown"
    import cocotb

    out["cocotb"] = cocotb.__version__
    out["python"] = sys.version.split()[0]
    return out


def read_results(xml_path, marker):
    tests = []
    for tc in ET.parse(xml_path).getroot().iter("testcase"):
        fail = tc.find("failure")
        err = tc.find("error")
        bad = fail is not None or err is not None
        # A control that dies on a simulator/Python error proves nothing, so
        # the control leaves a marker when it fails on its assertion.
        tests.append({"name": tc.get("name"), "passed": not bad,
                      "assertion_failure": bad and marker.exists()})
    return tests


def simulate(args, build_dir, testcase, seed):
    from cocotb.runner import get_runner

    runner = get_runner("icarus")
    runner.build(
        sources=[Path(s).resolve() for s in args.sources],
        hdl_toplevel=args.toplevel,
        build_dir=build_dir,
        always=True,
    )
    xml = build_dir / f"results_{testcase}.xml"
    marker = build_dir / "control_assertion.marker"
    marker.unlink(missing_ok=True)
    os.environ["CONTROL_MARKER"] = str(marker)
    try:
        runner.test(
            hdl_toplevel=args.toplevel,
            test_module=args.test_module,
            testcase=testcase,
            test_dir=args.test_dir,
            build_dir=build_dir,
            results_xml=xml,
            seed=seed,
        )
    except RuntimeError:
        pass  # failures are read from the xml, which is always written
    if not xml.exists():
        sys.exit(f"run_tests: simulator produced no results for {testcase}")
    return read_results(xml, marker)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", nargs="+", default=[str(HERE / "placeholder/counter.v")])
    ap.add_argument("--toplevel", default="counter")
    ap.add_argument("--test-module", default="test_counter")
    ap.add_argument("--test-dir", default=str(HERE / "placeholder"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--build-dir", default=str(REPO / "sim/build/verification"))
    ap.add_argument("--record", default=str(REPO / "sim/build/verification/result.json"))
    ap.add_argument("--level", default="rtl", help="rtl | gate (recorded only)")
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else random.randrange(2**31)
    versions = tool_versions()
    build_dir = Path(args.build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    smoke_dir, ctl_dir = build_dir / "smoke", build_dir / "control"
    smoke_dir.mkdir(exist_ok=True)
    ctl_dir.mkdir(exist_ok=True)
    smoke = simulate(args, smoke_dir, "test_counter_counts,test_counter_wraps", seed)
    control = simulate(args, ctl_dir, CONTROL, seed)

    tests = [dict(t, expected_fail=False) for t in smoke]
    tests += [dict(t, expected_fail=True) for t in control]
    problems = []
    for t in tests:
        t["ok"] = t["passed"] != t["expected_fail"]
        if not t["ok"]:
            problems.append(
                f"{t['name']}: expected {'FAIL' if t['expected_fail'] else 'PASS'}, "
                f"got {'pass' if t['passed'] else 'fail'}"
            )
    if not any(t["expected_fail"] for t in tests):
        problems.append("negative control did not run")
    for t in tests:
        if t["expected_fail"] and not t["passed"] and not t["assertion_failure"]:
            problems.append(f"{t['name']}: failed, but not on an assertion")

    rev = sh("git", "rev-parse", "HEAD").stdout.strip() or "unknown"
    dirty = bool(sh("git", "status", "--porcelain", "--untracked-files=no").stdout.strip())
    record = {
        "schema": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": rev,
        "dirty": dirty,
        "level": args.level,
        "dut": {"sources": [os.path.relpath(s, REPO) for s in args.sources], "toplevel": args.toplevel},
        "seed": seed,
        "tools": versions,
        "tests": tests,
        "ok": not problems,
        "problems": problems,
    }
    Path(args.record).parent.mkdir(parents=True, exist_ok=True)
    Path(args.record).write_text(json.dumps(record, indent=2) + "\n")
    for t in tests:
        print(f"{'ok  ' if t['ok'] else 'BAD '} {t['name']} "
              f"({'expected fail' if t['expected_fail'] else 'expected pass'}, "
              f"{'passed' if t['passed'] else 'failed'})")
    print(f"record: {args.record}")
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    return 0 if record["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
