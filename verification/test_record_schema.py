#!/usr/bin/env python3
"""Unit tests for check_records.py's cell-model-arm and netlist-hash rules,
and for the content-errors split the runner grades with (stdlib only).

Run from the repo root:
    .venv/bin/python -m unittest discover -s verification \
        -p 'test_record_schema.py'
or directly: python3 verification/test_record_schema.py

The discovery pattern is pinned in package.json and .github/workflows/ci.yml
so unittest never tries to import the cocotb test modules in this directory.
"""

import hashlib
import tempfile
import unittest
from pathlib import Path

from check_records import check, content_errors

NETLIST = "flow/adpll/records/adpll_top_synth.v"
OK_DISAGREES = "'ok' field disagrees with the checked contents"


def record(**over):
    """A minimal valid schema-2 gate record; keyword args override fields.

    Mirrors the committed gate record: the designated netlist is the
    synthesized netlist and the PDK model paths sit outside the repo (only
    dut.netlist is ever hashed). The recorded digest is derived from the
    tree at import, never a literal, so the fixture cannot itself become a
    stale-hash drift site.
    """
    rec = {
        "schema": 2,
        "timestamp": "2026-11-15T00:00:00+00:00",
        "commit": "a" * 40,
        "dirty": False,
        "level": "gate",
        "dut": {"sources": ["verification/gate-level/sky130_fd_sc_hd_sim_defines.v",
                            "../../../../../.ciel/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v",
                            "../../../../../.ciel/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v",
                            NETLIST],
                "toplevel": "adpll_top",
                "netlist": NETLIST,
                "netlist_sha256": hashlib.sha256(
                    (Path(__file__).resolve().parent.parent / NETLIST).read_bytes()
                ).hexdigest()},
        "seed": 12345,
        "tools": {"iverilog": "Icarus Verilog 13.0", "verilator": "Verilator 5.050",
                  "cocotb": "1.9.2", "python": "3.12.3"},
        "tests": [
            {"name": "test_integrates_and_locks", "passed": True,
             "expected_fail": False, "ok": True, "assertion_failure": False},
            {"name": "negative_control", "passed": False, "expected_fail": True,
             "ok": True, "assertion_failure": True},
        ],
        "method": {"cell_model_arm": "functional"},
        "ok": True,
        "problems": [],
    }
    rec.update(over)
    return rec


class CellModelArmRule(unittest.TestCase):
    def test_gate_timing_arm_is_rejected(self):
        errs = check(record(method={"cell_model_arm": "timing"}))
        self.assertTrue(any("timing arm" in e for e in errs), errs)

    def test_gate_functional_arm_passes(self):
        self.assertEqual(check(record()), [])

    def test_gate_empty_method_is_rejected(self):
        errs = check(record(method={}))
        self.assertTrue(
            any("missing method.cell_model_arm" in e for e in errs), errs)

    def test_gate_non_dict_method_is_rejected(self):
        errs = check(record(method=None))
        self.assertTrue(
            any("missing method.cell_model_arm" in e for e in errs), errs)

    def test_schema1_gate_is_not_exempt_from_the_arm(self):
        errs = check(record(schema=1, method={"cell_model_arm": "timing"}))
        self.assertTrue(any("timing arm" in e for e in errs), errs)

    def test_schema1_gate_with_no_arm_is_rejected(self):
        rec = record(schema=1)
        del rec["method"]
        errs = check(rec)
        self.assertTrue(
            any("missing method.cell_model_arm" in e for e in errs), errs)

    def test_schema2_rtl_needs_no_arm(self):
        rec = record(level="rtl")
        del rec["method"]
        self.assertEqual(check(rec), [])

    def test_arm_error_precedes_ok_disagreement(self):
        errs = check(record(method={"cell_model_arm": "timing"}, ok=True))
        self.assertTrue(any("timing arm" in e for e in errs), errs)
        self.assertTrue(any("'ok' field disagrees" in e for e in errs), errs)
        self.assertLess(
            next(i for i, e in enumerate(errs) if "timing arm" in e),
            next(i for i, e in enumerate(errs) if "'ok' field disagrees" in e),
        )

    def test_timing_arm_error_names_the_remedy(self):
        # The runner's PROBLEM line is this message now: it has to say what
        # to do, not only what is wrong.
        errs = content_errors(record(method={"cell_model_arm": "timing"}))
        self.assertTrue(any("Define FUNCTIONAL" in e for e in errs), errs)


class ContentErrors(unittest.TestCase):
    """check() = content_errors() + the 'ok' comparison (#163). The runner
    assigns content_errors() to problems[] before an 'ok' flag exists, so
    it must read everything from the record except that flag; the
    standalone checker adds the flag comparison on top."""

    def test_valid_record_has_no_content_errors(self):
        self.assertEqual(content_errors(record()), [])

    def test_content_errors_do_not_read_the_ok_flag(self):
        rec = record()
        del rec["ok"]
        self.assertEqual(content_errors(rec), [])
        bad = record(method={"cell_model_arm": "timing"})
        self.assertEqual(content_errors(bad), content_errors(dict(bad, ok=False)))
        self.assertTrue(content_errors(bad))

    def test_check_is_the_content_errors_plus_the_flag_comparison(self):
        bad = record(method={"cell_model_arm": "timing"})
        content = content_errors(bad)
        self.assertEqual(check(bad), content + [OK_DISAGREES])
        self.assertEqual(check(dict(bad, ok=False)), content)
        self.assertEqual(check(record()), [])

    def test_check_still_requires_the_ok_key(self):
        rec = record()
        del rec["ok"]
        self.assertEqual(check(rec), ["missing key 'ok'"])

    def test_a_record_missing_a_key_still_has_its_ok_flag_held_against_it(self):
        # The flag comparison no longer sits behind the missing-key early
        # return: a record that lacks a key and yet says "ok": true is
        # reported as both. The verdict was already a failure either way.
        rec = record()
        del rec["commit"]
        self.assertEqual(check(rec), ["missing key 'commit'", OK_DISAGREES])
        self.assertEqual(check(dict(rec, ok=False)), ["missing key 'commit'"])

    def test_netlist_rules_reach_the_runner_through_content_errors(self):
        # These two are the finding's invalid cases: the runner used to
        # write "ok": true for both while the checker rejected them.
        omitted = record()
        del omitted["dut"]["netlist"]
        del omitted["dut"]["netlist_sha256"]
        errs = content_errors(omitted)
        self.assertTrue(any("missing dut.netlist" in e for e in errs), errs)
        self.assertTrue(any("missing dut.netlist_sha256" in e for e in errs), errs)
        # ... and the error says which flag supplies the missing field
        self.assertTrue(any("--netlist" in e for e in errs), errs)
        stray = record()
        stray["dut"]["netlist"] = "flow/smoke/records/smoke_counter_synth.v"
        errs = content_errors(stray)
        self.assertTrue(
            any("not listed in dut.sources" in e and "--sources" in e for e in errs),
            errs)


class NetlistHashRule(unittest.TestCase):
    """The rule hashes a real file, so these tests build a throwaway repo
    root in a TemporaryDirectory and inject it as check()'s repo_root --
    the injectable root exists precisely so tests never monkeypatch a
    module global."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.netlist_rel = "flow/adpll/records/adpll_top_synth.v"
        self.netlist = self.root / self.netlist_rel
        self.netlist.parent.mkdir(parents=True)
        self.netlist.write_bytes(b"module adpll_top(); endmodule\n")

    def rec(self, **over):
        r = record()
        r["dut"] = {
            "sources": ["verification/gate-level/sky130_fd_sc_hd_sim_defines.v",
                        self.netlist_rel],
            "toplevel": "adpll_top",
            "netlist": self.netlist_rel,
            "netlist_sha256": hashlib.sha256(self.netlist.read_bytes()).hexdigest(),
        }
        r.update(over)
        return r

    def test_hash_mismatch_fails_naming_both_hashes(self):
        before = self.rec()
        recorded = before["dut"]["netlist_sha256"]
        with self.netlist.open("a") as f:
            f.write("// regenerated: tie cells removed\n")
        actual = hashlib.sha256(self.netlist.read_bytes()).hexdigest()
        errs = check(before, repo_root=self.root)
        self.assertTrue(
            any("does not match" in e and recorded in e and actual in e for e in errs),
            errs)

    def test_missing_netlist_field_fails(self):
        r = self.rec()
        del r["dut"]["netlist"]
        errs = check(r, repo_root=self.root)
        self.assertTrue(any("missing dut.netlist" in e for e in errs), errs)

    def test_missing_sha_field_fails(self):
        r = self.rec()
        del r["dut"]["netlist_sha256"]
        errs = check(r, repo_root=self.root)
        self.assertTrue(any("missing dut.netlist_sha256" in e for e in errs), errs)

    def test_netlist_absent_from_tree_fails(self):
        # A record naming a netlist that no longer exists is the #92 state:
        # a missing file is a failure, never a skip.
        r = self.rec()
        self.netlist.unlink()
        errs = check(r, repo_root=self.root)
        self.assertTrue(any("no longer exists" in e for e in errs), errs)

    def test_netlist_not_in_sources_fails(self):
        r = self.rec()
        r["dut"]["sources"] = ["verification/gate-level/sky130_fd_sc_hd_sim_defines.v"]
        errs = check(r, repo_root=self.root)
        self.assertTrue(any("not listed in dut.sources" in e for e in errs), errs)

    def test_escape_path_is_rejected_not_hashed(self):
        r = self.rec()
        r["dut"]["netlist"] = "../../etc/passwd"
        r["dut"]["sources"].append("../../etc/passwd")
        errs = check(r, repo_root=self.root)
        self.assertTrue(any("escapes the repo root" in e for e in errs), errs)

    def test_non_string_netlist_or_sha_is_rejected(self):
        r = self.rec()
        r["dut"]["netlist_sha256"] = 12345
        errs = check(r, repo_root=self.root)
        self.assertTrue(any("must both be strings" in e for e in errs), errs)

    def test_sources_outside_the_repo_are_never_hashed(self):
        # The PDK model paths in the fixture point outside the repo; only
        # dut.netlist is hashed, so the fixture passes against the real root.
        self.assertEqual(check(record()), [])

    def test_schema1_gate_is_not_exempt_from_netlist_fields(self):
        r = self.rec(schema=1)
        del r["dut"]["netlist"]
        del r["dut"]["netlist_sha256"]
        errs = check(r, repo_root=self.root)
        self.assertTrue(any("missing dut.netlist" in e for e in errs), errs)
        self.assertTrue(
            any("missing dut.netlist_sha256" in e for e in errs), errs)

    def test_rtl_record_with_no_netlist_fields_passes(self):
        r = record(level="rtl")
        del r["dut"]["netlist"]
        del r["dut"]["netlist_sha256"]
        self.assertEqual(check(r), [])

    def test_netlist_error_precedes_ok_disagreement(self):
        r = self.rec(ok=True)
        r["dut"]["netlist_sha256"] = "0" * 64
        errs = check(r, repo_root=self.root)
        self.assertTrue(any("does not match" in e for e in errs), errs)
        self.assertTrue(any("'ok' field disagrees" in e for e in errs), errs)
        self.assertLess(
            next(i for i, e in enumerate(errs) if "does not match" in e),
            next(i for i, e in enumerate(errs) if "'ok' field disagrees" in e),
        )


if __name__ == "__main__":
    unittest.main()
