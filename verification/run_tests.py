#!/usr/bin/env python3
"""cocotb + Icarus runner; writes a machine-readable result record.

Runs the smoke tests (must pass) and the negative control (must fail) as two
simulator invocations, then writes one JSON record with per-test pass/fail,
seed, commit, tool versions and the cell-model arm the compile selected
(method.cell_model_arm, derived from the captured compile log). A gate-level
run that selected the models' timing arm is a recorded problems[] failure.
With --netlist, the designated netlist's repo-relative path and its sha256
are recorded too (dut.netlist / dut.netlist_sha256), so check_records.py can
re-derive the hash and fail a record the tree no longer backs.
Exit 0 only if every smoke test passed AND the negative control failed. A
missing tool is an error, never a skip.

Cold start (from the repo root):
    uv venv .venv && uv pip install --python .venv/bin/python -r verification/requirements.txt
    .venv/bin/python verification/run_tests.py

Gate-level re-run: see verification/gate-level/README.md (--sources/--toplevel).
"""

import argparse
import hashlib
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
COMPILE_LOG = "compile.log"


def cell_model_arm(log_path):
    """Cell-model arm the compile selected, from its own log: any
    'Choosing typ expression' warning means the models' specify/timing arm
    was selected. A missing or unreadable log is an error, never a silent
    pass -- an unknown arm must not be recorded as the functional one."""
    try:
        text = log_path.read_text(errors="replace")
    except OSError as e:
        sys.exit(f"run_tests: compile log missing or unreadable ({log_path}): {e}")
    return "timing" if "Choosing typ expression" in text else "functional"

# DUT registry: name -> (sources, toplevel, test module, smoke testcases).
# Every module also carries a `negative_control`.
SUITES = {
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
    }
    out = {}
    for name, cmd in specs.items():
        if shutil.which(cmd[0]) is None:
            sys.exit(f"run_tests: required tool '{cmd[0]}' not found")
        r = sh(*cmd)
        if r.returncode != 0:
            sys.exit(f"run_tests: required tool '{cmd[0]}' exited with status {r.returncode}")
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
    try:
        runner.build(
            sources=[Path(s).resolve() for s in args.sources],
            hdl_toplevel=args.toplevel,
            build_dir=build_dir,
            always=True,
            log_file=build_dir / COMPILE_LOG,
        )
    except SystemExit:
        # cocotb redirects the compile's stdout AND stderr into the log, so
        # iverilog's own diagnostic never reaches the console; echo it, name
        # the log (CI archives only the JSON records, not the log), then
        # re-raise so the exit status is unchanged. SystemExit, not
        # Exception: cocotb raises SystemExit, which derives directly from
        # BaseException. The log may not exist at all -- the same exception
        # is raised for a missing iverilog executable, before any log is
        # written.
        log = build_dir / COMPILE_LOG
        print(f"run_tests: iverilog could not compile the source list "
              f"(compile log: {log}):", file=sys.stderr)
        if log.exists():
            for line in log.read_text(errors="replace").splitlines():
                print(f"    {line}", file=sys.stderr)
        raise
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
    ap.add_argument("--toplevel", default=None, help="required with --sources")
    ap.add_argument("--test-module", default=None, help="required with --sources")
    ap.add_argument("--test-dir", default=None, help="required with --sources")
    ap.add_argument("--tests", default=None,
                    help="comma-separated smoke testcases (required with --sources)")
    ap.add_argument("--suite", choices=sorted(SUITES) + ["all"], default="all",
                    help="registered DUT to run (default: all; ignored with --sources)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--build-dir", default=str(REPO / "sim/build/verification"))
    ap.add_argument("--record", default=None,
                    help="record path for a single DUT (--suite NAME or --sources; "
                         "default: <build-dir>/<suite>.json)")
    ap.add_argument("--level", choices=("rtl", "gate"), default="rtl",
                    help="rtl | gate")
    ap.add_argument("--netlist", default=None,
                    help="designated netlist file; records its repo-relative "
                         "path and sha256 into the record (dut.netlist / "
                         "dut.netlist_sha256) so check_records.py can verify "
                         "the record against the committed netlist")
    args = ap.parse_args()

    if args.sources is not None:
        for flag in ("toplevel", "test_module", "test_dir", "tests"):
            if getattr(args, flag) is None:
                ap.error(f"--sources requires --{flag.replace('_', '-')}")
        return run_one(args, "custom")
    if args.record is not None and args.suite == "all":
        # One path cannot hold five suites' records; the registry loop would
        # have each suite overwrite the last, silently losing four of five.
        ap.error("--record names one record; use --suite NAME or --sources")
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

    # Both compiles are handed the same --sources, so the two arms must agree;
    # a disagreement is a runner bug to fail on, not a tolerable case.
    smoke_arm = cell_model_arm(smoke_dir / COMPILE_LOG)
    control_arm = cell_model_arm(ctl_dir / COMPILE_LOG)
    if smoke_arm != control_arm:
        sys.exit(
            f"run_tests: the two compiles selected different cell-model arms "
            f"(smoke: {smoke_arm}, control: {control_arm}); both are handed the "
            "same --sources, so this is a runner bug, not a tolerable case"
        )
    arm = smoke_arm

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
    if args.level == "gate" and arm != "functional":
        problems.append(
            f"gate-level run selected the cell models' timing arm ({arm}), not "
            "the functional one: the result carries the models' built-in typ "
            "delays -- an unstated timing claim. Define FUNCTIONAL before the "
            "models (a sim-defines file first on --sources does this) and re-run."
        )

    rev = sh("git", "rev-parse", "HEAD").stdout.strip() or "unknown"
    dirty = bool(sh("git", "status", "--porcelain", "--untracked-files=no").stdout.strip())
    dut = {"sources": [os.path.relpath(s, REPO) for s in args.sources], "toplevel": args.toplevel}
    if args.netlist is not None:
        netlist = Path(args.netlist)
        if not netlist.is_file():
            sys.exit(f"run_tests: --netlist file not found: {netlist}")
        dut["netlist"] = os.path.relpath(netlist.resolve(), REPO)
        dut["netlist_sha256"] = hashlib.sha256(netlist.read_bytes()).hexdigest()
    record = {
        "schema": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": rev,
        "dirty": dirty,
        "level": args.level,
        "dut": dut,
        "seed": seed,
        "tools": versions,
        "method": {"cell_model_arm": arm},
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
