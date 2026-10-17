#!/usr/bin/env python3
"""Validate a result record written by run_tests.py (stdlib only).

Usage: python3 verification/check_records.py [record.json]
Checks schema, that tool versions and the commit are present, that the
smoke tests passed, and that every expected-fail test (the negative
control) actually failed. Exit 0 pass, 1 invalid.
"""

import json
import re
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent.parent / "sim/build/verification/result.json"
TOOLS = ("iverilog", "verilator", "yosys", "cocotb", "python")


def check(rec):
    errs = []
    for k in ("schema", "timestamp", "commit", "level", "dut", "seed", "tools", "tests", "ok"):
        if k not in rec:
            errs.append(f"missing key '{k}'")
    if errs:
        return errs
    if not re.fullmatch(r"[0-9a-f]{40}", rec["commit"]):
        errs.append(f"commit is not a 40-hex sha: {rec['commit']!r}")
    if not isinstance(rec["seed"], int):
        errs.append("seed is not an integer")
    for t in TOOLS:
        if not rec["tools"].get(t) or rec["tools"][t] == "unknown":
            errs.append(f"tool version missing: {t}")
    tests = rec["tests"]
    if not any(not t.get("expected_fail") for t in tests):
        errs.append("no smoke (expected-pass) tests recorded")
    if not any(t.get("expected_fail") for t in tests):
        errs.append("no negative control (expected_fail) recorded")
    for t in tests:
        for k in ("name", "passed", "expected_fail"):
            if k not in t:
                errs.append(f"test entry missing '{k}': {t}")
                break
        else:
            if t["passed"] == t["expected_fail"]:
                want = "FAIL" if t["expected_fail"] else "PASS"
                errs.append(f"{t['name']}: expected {want} but did not")
            elif t["expected_fail"] and not t.get("assertion_failure"):
                errs.append(f"{t['name']}: control failed but not on an assertion")
    if rec["ok"] is not (not errs):
        errs.append("'ok' field disagrees with the checked contents")
    return errs


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    try:
        rec = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        print(f"check_records: cannot read {path}: {e}", file=sys.stderr)
        return 1
    errs = check(rec)
    for e in errs:
        print(f"check_records: {e}", file=sys.stderr)
    print(f"check_records: {path}: {'FAIL' if errs else 'ok'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
