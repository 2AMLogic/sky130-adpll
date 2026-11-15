#!/usr/bin/env python3
"""Self-test of run_tests.py's own CLI gating (stdlib only; no simulator).

The --record/--suite-all guard in run_tests.main() is positional: it must sit
after the --sources early return (so the documented gate-level invocation
still reaches run_one) and before the registry loop (so five suites are not
collapsed into one record). Nothing else exercises either property, so this
module pins the four argv shapes that matter, with run_one stubbed.

Run from the repo root:
    python3 verification/selftest_run_tests.py
or via npm: npm run check:selftest

The filename is deliberately outside the test*.py glob: unittest discover
over this directory would try to import the cocotb DUT modules, which need a
simulator toolchain. This module needs neither cocotb nor a venv -- bare
system python3 runs it.
"""

import contextlib
import io
import sys
import unittest

import run_tests

RTL = run_tests.REPO / "rtl"
VERIF = run_tests.REPO / "verification"


class CliGating(unittest.TestCase):
    def dispatch(self, argv):
        """Run main() with run_one stubbed; return [(suite, record), ...]."""
        seen = []
        orig_run_one, orig_argv = run_tests.run_one, sys.argv
        run_tests.run_one = lambda a, name: (seen.append((name, a.record)), 0)[1]
        sys.argv = ["run_tests.py"] + argv
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                run_tests.main()
        finally:
            run_tests.run_one, sys.argv = orig_run_one, orig_argv
        return seen

    def test_record_with_default_suite_all_is_rejected(self):
        with self.assertRaises(SystemExit) as cm:
            self.dispatch(["--record", "/tmp/one.json"])
        self.assertEqual(cm.exception.code, 2)

    def test_default_run_gives_each_suite_its_own_record(self):
        seen = self.dispatch([])
        self.assertEqual(len(seen), len(run_tests.SUITES))
        self.assertEqual(len({r for _, r in seen}), len(run_tests.SUITES))

    def test_record_with_explicit_single_suite_is_honoured(self):
        self.assertEqual(
            self.dispatch(["--suite", "top", "--record", "/tmp/one.json"]),
            [("top", "/tmp/one.json")])

    def test_gate_level_sources_invocation_still_reaches_run_one(self):
        self.assertEqual(self.dispatch([
            "--level", "gate", "--sources", str(RTL / "adpll_top.v"),
            "--toplevel", "adpll_top", "--test-module", "test_top",
            "--test-dir", str(VERIF), "--tests", "test_x",
            "--record", "/tmp/gate.json"]), [("custom", "/tmp/gate.json")])


if __name__ == "__main__":
    unittest.main()
