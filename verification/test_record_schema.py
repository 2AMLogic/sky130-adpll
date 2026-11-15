#!/usr/bin/env python3
"""Unit tests for check_records.py's cell-model-arm rule (stdlib only).

Run from the repo root:
    .venv/bin/python -m unittest discover -s verification \
        -p 'test_record_schema.py'
or directly: python3 verification/test_record_schema.py

The discovery pattern is pinned in package.json and .github/workflows/ci.yml
so unittest never tries to import the cocotb test modules in this directory.
"""

import unittest

from check_records import check


def record(**over):
    """A minimal valid schema-2 gate record; keyword args override fields."""
    rec = {
        "schema": 2,
        "timestamp": "2026-11-15T00:00:00+00:00",
        "commit": "a" * 40,
        "dirty": False,
        "level": "gate",
        "dut": {"sources": ["verification/gate-level/sky130_fd_sc_hd_sim_defines.v"],
                "toplevel": "adpll_top"},
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

    def test_schema1_gate_is_grandfathered(self):
        rec = record(schema=1)
        del rec["method"]
        self.assertEqual(check(rec), [])

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


if __name__ == "__main__":
    unittest.main()
