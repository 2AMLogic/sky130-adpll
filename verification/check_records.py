#!/usr/bin/env python3
"""Validate a result record written by run_tests.py (stdlib only).

Usage: python3 verification/check_records.py [record.json ...]
With no argument, checks every <suite>.json under sim/build/verification/
(and fails if there are none).
Checks schema, that tool versions and the commit are present, that the
smoke tests passed, and that every expected-fail test (the negative
control) actually failed. A gate-level record must also state the
cell-model arm the compile selected and it must be the functional one, and
must name the netlist it graded (dut.netlist + dut.netlist_sha256): the
sha256 is re-derived from the committed file and any mismatch -- including a
netlist that no longer exists in the tree -- is a failure, never a skip.
Exit 0 pass, 1 invalid.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = REPO_ROOT / "sim/build/verification"
TOOLS = ("iverilog", "verilator", "cocotb", "python")


def check(rec, repo_root=None):
    """repo_root defaults to this checkout; tests inject a throwaway tree."""
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
    # Gate-level records must state the cell-model arm the compile selected,
    # and it must be the functional one: a timing-arm record carries the
    # models' built-in typ delays -- an unstated timing claim. Appended before
    # the 'ok' comparison below, so a wrong-arm record claiming "ok": true is
    # reported as both.
    if rec["level"] == "gate":
        method = rec.get("method")
        arm = method.get("cell_model_arm") if isinstance(method, dict) else None
        if arm is None:
            errs.append("gate-level record missing method.cell_model_arm")
        elif arm != "functional":
            errs.append(
                f"gate-level record selected the cell models' timing arm "
                f"(method.cell_model_arm: {arm!r}); the result carries the "
                "models' built-in typ delays -- an unstated timing claim"
            )
        _check_netlist(rec, errs, repo_root)
    if rec["ok"] is not (not errs):
        errs.append("'ok' field disagrees with the checked contents")
    return errs


def _check_netlist(rec, errs, repo_root):
    """A gate record must name the netlist it graded, and the named file
    must still be in the tree with that sha256. Fail closed on every
    degenerate case -- a missing field, a path outside the repo, a file that
    no longer exists: #92 was a record on main naming a netlist that no
    longer existed, and nothing failed."""
    dut = rec["dut"]
    if not isinstance(dut, dict):
        errs.append("gate-level record: 'dut' is not an object")
        return
    netlist = dut.get("netlist")
    sha = dut.get("netlist_sha256")
    if netlist is None:
        errs.append("gate-level record missing dut.netlist")
    if sha is None:
        errs.append("gate-level record missing dut.netlist_sha256")
    if netlist is None or sha is None:
        return
    if not isinstance(netlist, str) or not isinstance(sha, str):
        errs.append(
            f"dut.netlist and dut.netlist_sha256 must both be strings: "
            f"{netlist!r} / {sha!r}"
        )
        return
    sources = dut.get("sources")
    if not isinstance(sources, list) or netlist not in sources:
        errs.append(f"dut.netlist {netlist!r} is not listed in dut.sources")
        return
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    path = (root / netlist).resolve()
    if not path.is_relative_to(root.resolve()):
        errs.append(f"dut.netlist {netlist!r} escapes the repo root; refusing to hash it")
        return
    if not path.is_file():
        errs.append(
            f"dut.netlist {netlist!r} is not in the tree: the record names a "
            "netlist that no longer exists"
        )
        return
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != sha:
        errs.append(
            f"dut.netlist_sha256 {sha} does not match {netlist} "
            f"(actual sha256 {actual}): the netlist was regenerated since "
            "the record was written"
        )


def check_file(path):
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


def main():
    paths = [Path(a) for a in sys.argv[1:]] or sorted(DEFAULT_DIR.glob("*.json"))
    if not paths:
        print(f"check_records: no records under {DEFAULT_DIR}", file=sys.stderr)
        return 1
    return max(check_file(p) for p in paths)


if __name__ == "__main__":
    sys.exit(main())
