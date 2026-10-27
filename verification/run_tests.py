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
RTL = REPO / "rtl"

# DUT registry: name -> (sources, toplevel, test module, smoke testcases).
# Every module also carries a `negative_control`. The placeholder is the
# harness self-check and stays first.
SUITES = {
    "placeholder": ([HERE / "placeholder/counter.v"], "counter", "test_counter",
                    "test_counter_counts,test_counter_wraps", HERE / "placeholder"),
    "loop_filter": ([RTL / "adpll_loop_filter.v"], "adpll_loop_filter", "test_loop_filter",
                    "test_step_response,test_integrator_saturation,test_hold_without_en", HERE),
    "divider": ([RTL / "adpll_divider.v"], "adpll_divider", "test_divider",
                "test_ratio_200mhz,test_ratio_100mhz_fallback,test_ratio_range", HERE),
    "lock_detect": ([RTL / "adpll_lock_detect.v"], "adpll_lock_detect", "test_lock_detect",
                    "test_lock_asserts_after_64,test_run_resets,test_deassert_hysteresis", HERE),
    "dco_code": ([RTL / "adpll_dco_code.v"], "adpll_dco_code", "test_dco_code",
                 "test_split,test_dither_average,test_fine_saturates", HERE),
    "top": ([RTL / f"adpll_{m}.v" for m in
             ("top", "divider", "loop_filter", "lock_detect", "dco_code")],
            "adpll_top", "test_top", "test_integrates_and_locks", HERE),
}


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
    ap.add_argument("--sources", nargs="+", default=None)
    ap.add_argument("--toplevel", default="counter")
    ap.add_argument("--test-module", default="test_counter")
    ap.add_argument("--test-dir", default=str(HERE / "placeholder"))
    ap.add_argument("--tests", default="test_counter_counts,test_counter_wraps",
                    help="comma-separated smoke testcases (with --sources)")
    ap.add_argument("--suite", choices=sorted(SUITES) + ["all"], default="all",
                    help="registered DUT to run (default: all; ignored with --sources)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--build-dir", default=str(REPO / "sim/build/verification"))
    ap.add_argument("--record", default=None,
                    help="record path (default: <build-dir>/<suite>.json)")
    ap.add_argument("--level", default="rtl", help="rtl | gate (recorded only)")
    args = ap.parse_args()

    if args.sources is not None:
        return run_one(args, "custom")
    rc = 0
    for name in (sorted(SUITES) if args.suite == "all" else [args.suite]):
        srcs, top, mod, tests, tdir = SUITES[name]
        a = argparse.Namespace(**vars(args))
        a.sources, a.toplevel, a.test_module = [str(x) for x in srcs], top, mod
        a.tests, a.test_dir = tests, str(tdir)
        a.build_dir = str(Path(args.build_dir) / name)
        a.record = args.record or str(Path(args.build_dir) / f"{name}.json")
        print(f"== suite {name} ==")
        rc |= run_one(a, name)
    return rc


def run_one(args, name):
    seed = args.seed if args.seed is not None else random.randrange(2**31)
    versions = tool_versions()
    build_dir = Path(args.build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    smoke_dir, ctl_dir = build_dir / "smoke", build_dir / "control"
    smoke_dir.mkdir(exist_ok=True)
    ctl_dir.mkdir(exist_ok=True)
    smoke = simulate(args, smoke_dir, args.tests, seed)
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
    rec_path = Path(args.record or Path(args.build_dir) / "result.json")
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    rec_path.write_text(json.dumps(record, indent=2) + "\n")
    for t in tests:
        print(f"{'ok  ' if t['ok'] else 'BAD '} {t['name']} "
              f"({'expected fail' if t['expected_fail'] else 'expected pass'}, "
              f"{'passed' if t['passed'] else 'failed'})")
    print(f"record: {rec_path}")
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    return 0 if record["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
