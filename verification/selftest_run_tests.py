#!/usr/bin/env python3
"""Self-test of run_tests.py's own CLI gating (stdlib only; no simulator).

The --record/--suite-all guard in run_tests.main() is positional: it must sit
after the --sources early return (so the documented gate-level invocation
still reaches run_one) and before the registry loop (so five suites are not
collapsed into one record). Nothing else exercises either property, so this
module pins the four argv shapes that matter, with run_one stubbed.

The GateRecordSources cases pin dut.sources portability (#143): sources under
the caller's PDK_ROOT are recorded as '$PDK_ROOT/...' tokens identically at
two checkout depths, the simulator still receives the real paths, and every
other source keeps its existing representation. The WrapperPdkRoot cases run
run-gate-level.sh itself over stubbed tooling (a PATH stub covers iverilog,
which CI has not installed when this self-test runs) and check the runner
process receives the root the wrapper built its source list from.

The GateRecordGrading cases pin where run_one's verdict comes from (#163):
the record checker's content checks, the same ones the standalone checker
runs over the file on disk, so a record the checker rejects is failed by the
runner that wrote it -- through both entry points, for each case of the
finding.

Run from the repo root:
    python3 verification/selftest_run_tests.py
or via npm: npm run check:selftest

The filename is deliberately outside the test*.py glob: unittest discover
over this directory would try to import the cocotb DUT modules, which need a
simulator toolchain. This module needs neither cocotb nor a venv -- bare
system python3 runs it.
"""

import argparse
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import run_tests

RTL = run_tests.REPO / "rtl"
VERIF = run_tests.REPO / "verification"

# The four dut.sources entries a gate-level record must carry, in the
# wrapper's order, at any checkout depth (#143 acceptance criteria).
GATE_SOURCES = [
    "verification/gate-level/sky130_fd_sc_hd_sim_defines.v",
    "$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v",
    "$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/verilog/sky130_fd_sc_hd.v",
    "flow/adpll/records/adpll_top_synth.v",
]
# What run_one hands the simulator instead: the real files, same order.
GATE_BASENAMES = ["sky130_fd_sc_hd_sim_defines.v", "primitives.v",
                  "sky130_fd_sc_hd.v", "adpll_top_synth.v"]


def _provision_gate_tree(checkout, pdk_root, sky130a_symlink=False):
    """Create a checkout carrying the two repo-side gate sources and a PDK
    root carrying the two cell models; return the source list in wrapper
    order. With sky130a_symlink, 'sky130A' is a symlink to 'sky130A-real'
    the way an open_pdks install may lay it out -- the sources still name
    the logical 'sky130A/...' path."""
    for rel in (GATE_SOURCES[0], GATE_SOURCES[3]):
        f = checkout / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("// selftest fixture\n")
    target = "sky130A-real" if sky130a_symlink else "sky130A"
    verilog = (pdk_root / target / "libs.ref" / "sky130_fd_sc_hd" / "verilog")
    for name in ("primitives.v", "sky130_fd_sc_hd.v"):
        verilog.mkdir(parents=True, exist_ok=True)
        (verilog / name).write_text("// selftest fixture\n")
    if sky130a_symlink:
        (pdk_root / "sky130A").symlink_to(target, target_is_directory=True)
    logical = pdk_root / "sky130A" / "libs.ref" / "sky130_fd_sc_hd" / "verilog"
    return [checkout / GATE_SOURCES[0], logical / "primitives.v",
            logical / "sky130_fd_sc_hd.v", checkout / GATE_SOURCES[3]]


def _load_runner(checkout):
    """Import run_tests.py with REPO rooted at `checkout` -- the way a
    checkout at a different depth (e.g. a .loom worktree) runs the very
    same file. The copy needs exactly one other repo file beside it: the
    record checker, which the runner loads from its own directory, so this
    copy grades with its own neighbour and not with the importer's. Other
    than that the module's imports are stdlib-only at top level."""
    verification = checkout / "verification"
    verification.mkdir(parents=True, exist_ok=True)
    for name in ("run_tests.py", "check_records.py"):
        shutil.copyfile(VERIF / name, verification / name)
    spec = importlib.util.spec_from_file_location(
        f"run_tests_selftest_{id(checkout)}", verification / "run_tests.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_record(mod, sources, pdk_root=None, level="gate", netlist=None,
                  arm="functional", build=None, outcome=None, commit="a" * 40):
    """Run mod.run_one with the simulator and its tool probes stubbed;
    return (exit status, record dict, per-invocation source lists). PDK_ROOT
    is set to `pdk_root` (or removed) for the call only, exactly as
    run-gate-level.sh arranges the environment for the real runner. The
    record lands under `build` -- a throwaway directory unless the caller
    passes its own, which then stays on disk for the caller to inspect.
    `outcome(testcase)` overrides what the stubbed simulator reports, as a
    list of (name, passed, assertion_failure); the default is a passing
    smoke test and a control failing on its assertion. `commit` is what the
    stubbed `git rev-parse HEAD` prints: empty stands for a tree with no
    HEAD, which run_one records as "unknown"."""
    seen = []
    saved = (mod.simulate, mod.tool_versions, mod.cell_model_arm, mod.sh)
    outcome = outcome or (lambda testcase: [(testcase, testcase != mod.CONTROL,
                                             testcase == mod.CONTROL)])
    mod.simulate = lambda a, b, testcase, seed: (
        seen.append([str(s) for s in a.sources]),
        [{"name": n, "passed": p, "assertion_failure": m}
         for n, p, m in outcome(testcase)])[1]
    mod.tool_versions = lambda: {"iverilog": "stub", "verilator": "stub",
                                 "cocotb": "stub", "python": "stub"}
    mod.cell_model_arm = lambda log: arm
    # run_one also asks git for HEAD and the dirty flag; answered here so no
    # case depends on whether the tree it runs in is a git checkout
    mod.sh = lambda *cmd: subprocess.CompletedProcess(
        cmd, 0, stdout=f"{commit}\n" if cmd[1] == "rev-parse" else "")
    own_build = build is None
    build = Path(build or tempfile.mkdtemp(prefix="run-tests-selftest-"))
    args = argparse.Namespace(
        sources=[str(s) for s in sources], toplevel="adpll_top",
        test_module="test_top", test_dir=str(Path(mod.REPO) / "verification"),
        tests="test_integrates_and_locks", seed=12345,
        build_dir=str(build), record=str(build / "result.json"),
        level=level, netlist=netlist)
    env_saved = os.environ.get("PDK_ROOT")
    if pdk_root is not None:
        os.environ["PDK_ROOT"] = str(pdk_root)
    else:
        os.environ.pop("PDK_ROOT", None)
    try:
        rc = mod.run_one(args, "custom")
        record = json.loads(Path(args.record).read_text())
    finally:
        mod.simulate, mod.tool_versions, mod.cell_model_arm, mod.sh = saved
        if env_saved is None:
            os.environ.pop("PDK_ROOT", None)
        else:
            os.environ["PDK_ROOT"] = env_saved
        if own_build:
            shutil.rmtree(build, ignore_errors=True)
    return rc, record, seen


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


class GateRecordSources(unittest.TestCase):
    """dut.sources as run_one writes it (#143): '$PDK_ROOT/...' tokens for
    the cell models at any checkout depth, real paths to the simulator,
    and the pre-existing representation for everything else."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)

    def test_gate_sources_tokenized_at_two_checkout_depths(self):
        trees = [
            # a primary checkout and its sibling PDK ...
            (self.base / "a" / "checkout", self.base / "a" / "pdk"),
            # ... and a .loom worktree checkout, two levels deeper, whose
            # relpath to its PDK carries five '../' segments instead of one
            (self.base / "b" / "checkout" / ".loom" / "worktrees" / "issue-42",
             self.base / "b" / "pdk"),
        ]
        for checkout, pdk_root in trees:
            with self.subTest(checkout=checkout):
                sources = _provision_gate_tree(checkout, pdk_root)
                rc, record, seen = _write_record(
                    _load_runner(checkout), sources, pdk_root=pdk_root,
                    netlist=str(checkout / GATE_SOURCES[3]))
                self.assertEqual(rc, 0)
                self.assertEqual(record["dut"]["sources"], GATE_SOURCES)
                self.assertEqual(record["dut"]["netlist"], GATE_SOURCES[3])
                # the simulator was handed the real files, twice (smoke +
                # control), in the wrapper's order -- never a token
                self.assertEqual(seen, seen[:1] * 2)
                self.assertEqual([Path(p).name for p in seen[0]], GATE_BASENAMES)
                self.assertTrue(all(Path(p).is_file() for p in seen[0]))

    def test_pdk_symlink_keeps_logical_sky130a_suffix(self):
        checkout, pdk_root = self.base / "checkout", self.base / "pdk"
        sources = _provision_gate_tree(checkout, pdk_root, sky130a_symlink=True)
        rc, record, _ = _write_record(
            _load_runner(checkout), sources, pdk_root=pdk_root,
            netlist=str(checkout / GATE_SOURCES[3]))
        self.assertEqual(rc, 0)
        self.assertEqual(record["dut"]["sources"], GATE_SOURCES)

    def test_repo_local_rtl_with_pdk_root_unset_stays_repo_relative(self):
        rc, record, seen = _write_record(
            run_tests, [RTL / "adpll_top.v"], pdk_root=None, level="rtl")
        self.assertEqual(rc, 0)
        self.assertEqual(record["dut"]["sources"], ["rtl/adpll_top.v"])

    def test_sources_outside_the_selected_root_keep_the_relpath_form(self):
        pdk_root = self.base / "pdk"
        # a directory whose name starts with the root's own name: a match by
        # string prefix would wrongly tokenize it
        sibling = pdk_root.with_name(pdk_root.name + "-backup")
        model = (sibling / "sky130A" / "libs.ref" /
                 "sky130_fd_sc_hd" / "verilog" / "primitives.v")
        model.parent.mkdir(parents=True)
        model.write_text("// selftest fixture\n")
        outside = self.base / "elsewhere" / "extra.v"
        outside.parent.mkdir(parents=True)
        outside.write_text("// selftest fixture\n")
        for source, why in ((model, "sibling of the selected root"),
                            (outside, "outside checkout and PDK")):
            with self.subTest(case=why):
                rc, record, _ = _write_record(
                    run_tests, [source, RTL / "adpll_top.v"], pdk_root=pdk_root,
                    level="rtl")
                self.assertEqual(rc, 0)
                self.assertEqual(
                    record["dut"]["sources"],
                    [os.path.relpath(source, run_tests.REPO), "rtl/adpll_top.v"])
                self.assertFalse(record["dut"]["sources"][0].startswith("$PDK_ROOT"))


class GateRecordGrading(unittest.TestCase):
    """run_one takes 'ok' and problems[] from check_records' content checks
    (#163): the same function the standalone checker runs over the file on
    disk, so the runner cannot report success for a record its checker
    rejects. Each case of the finding goes through both entry points: the
    netlist the compile used, the designation omitted, and a netlist that
    exists in the tree but was not compiled. The simulator is stubbed, so an
    RTL file stands in for the netlist."""

    NETLIST = RTL / "adpll_top.v"
    STRAY = run_tests.REPO / "flow/smoke/records/smoke_counter_synth.v"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.build = Path(tmp.name)

    def _grade(self, netlist, arm="functional", outcome=None, commit="a" * 40):
        """run_one over [NETLIST] designating `netlist`. Returns the
        runner's (exit status, record) and the standalone checker's
        completed process over the file the runner wrote."""
        rc, record, _ = _write_record(
            run_tests, [self.NETLIST], netlist=netlist, arm=arm, outcome=outcome,
            commit=commit, build=str(self.build))
        checker = subprocess.run(
            [sys.executable, str(VERIF / "check_records.py"),
             str(self.build / "result.json")],
            capture_output=True, text=True)
        return rc, record, checker

    def _assert_both_fail(self, rc, record, checker, *diagnostics):
        self.assertEqual(rc, 1)
        self.assertFalse(record["ok"])
        for fragment in diagnostics:
            self.assertTrue(any(fragment in p for p in record["problems"]),
                            record["problems"])
        self.assertEqual(checker.returncode, 1, checker.stderr)
        # the checker's complaints are the runner's, and no more: the stored
        # "ok": false agrees with the contents it rechecked from disk
        self.assertNotIn("disagrees", checker.stderr)
        for p in record["problems"]:
            self.assertIn(p, checker.stderr)

    def test_the_compiled_netlist_passes_both_entry_points(self):
        rc, record, checker = self._grade(str(self.NETLIST))
        self.assertEqual((rc, record["ok"], record["problems"]), (0, True, []))
        self.assertEqual(record["dut"]["netlist"], "rtl/adpll_top.v")
        self.assertEqual(checker.returncode, 0, checker.stderr)

    def test_omitted_netlist_fails_both_entry_points(self):
        rc, record, checker = self._grade(None)
        self._assert_both_fail(rc, record, checker, "missing dut.netlist",
                               "missing dut.netlist_sha256")
        self.assertNotIn("netlist", record["dut"])

    def test_netlist_outside_the_compile_sources_fails_both_entry_points(self):
        rc, record, checker = self._grade(str(self.STRAY))
        self._assert_both_fail(rc, record, checker, "not listed in dut.sources")
        self.assertEqual(record["dut"]["netlist"],
                         "flow/smoke/records/smoke_counter_synth.v")

    def test_timing_arm_still_fails_naming_the_remedy(self):
        rc, record, checker = self._grade(str(self.NETLIST), arm="timing")
        self._assert_both_fail(rc, record, checker, "timing arm",
                               "Define FUNCTIONAL")

    def test_a_record_without_a_commit_fails(self):
        # every checker rule grades the runner's record now, not only the
        # netlist ones: outside a git checkout HEAD is unknown, and that is
        # a failed record instead of an "unknown" only the checker rejects
        rc, record, checker = self._grade(str(self.NETLIST), commit="")
        self._assert_both_fail(rc, record, checker, "commit is not a 40-hex sha")

    def test_a_run_that_recorded_no_smoke_test_fails(self):
        # a second silent pass of the same class, closed by the same means:
        # the runner's own rules asked only that the control ran, so a
        # record holding nothing but the control was reported as a pass
        rc, record, checker = self._grade(
            str(self.NETLIST),
            outcome=lambda testcase: [] if testcase != run_tests.CONTROL
            else [(testcase, False, True)])
        self._assert_both_fail(rc, record, checker,
                               "no smoke (expected-pass) tests recorded")

    def test_runner_copy_grades_with_the_checker_beside_it(self):
        checkout, pdk_root = self.build / "checkout", self.build / "pdk"
        _provision_gate_tree(checkout, pdk_root)
        mod = _load_runner(checkout)
        beside = (checkout / "verification" / "check_records.py").resolve()
        self.assertEqual(Path(mod.check_records.__file__).resolve(), beside)
        rc, record, _ = _write_record(
            mod, [checkout / GATE_SOURCES[3]], netlist=str(checkout / GATE_SOURCES[3]))
        self.assertEqual((rc, record["ok"], record["problems"]), (0, True, []))


# The record the wrapper's stubbed runner "writes": enough schema for the
# companion method-note step (which reads it back) to succeed verbatim.
_STUB_RECORD = {
    "schema": 2,
    "timestamp": "2026-01-01T00:00:00+00:00",
    "commit": "a" * 40,
    "dirty": False,
    "level": "gate",
    "dut": {"sources": GATE_SOURCES, "toplevel": "adpll_top",
            "netlist": GATE_SOURCES[3], "netlist_sha256": "0" * 64},
    "seed": 12345,
    "tools": {"iverilog": "stub", "verilator": "stub", "cocotb": "stub",
              "python": "stub"},
    "method": {"cell_model_arm": "functional"},
    "tests": [
        {"name": "test_integrates_and_locks", "passed": True,
         "assertion_failure": False, "expected_fail": False, "ok": True},
        {"name": "negative_control", "passed": False,
         "assertion_failure": True, "expected_fail": True, "ok": True},
    ],
    "ok": True,
    "problems": [],
}


class WrapperPdkRoot(unittest.TestCase):
    """run-gate-level.sh hands the runner its effective PDK_ROOT (default or
    --pdk-root-resolved), not whatever the environment exports: run_tests.py
    tokenizes dut.sources against exactly that root (#143). Everything past
    the wrapper's own plumbing -- interpreter, simulator -- is stubbed."""

    PIN = "0123456789abcdef0123456789abcdef01234567"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.checkout = self.base / "checkout"
        self.home = self.base / "home"
        self.alt = self.base / "pdk-alt"
        self._provision()

    def _pdk_tree(self, root):
        sources = root / "sky130A" / "SOURCES"
        sources.parent.mkdir(parents=True, exist_ok=True)
        sources.write_text(f"open_pdks {self.PIN}\n")
        verilog = root / "sky130A" / "libs.ref" / "sky130_fd_sc_hd" / "verilog"
        verilog.mkdir(parents=True, exist_ok=True)
        for name in ("primitives.v", "sky130_fd_sc_hd.v"):
            (verilog / name).write_text("// selftest fixture\n")

    def _provision(self):
        # the wrapper's two candidate roots: the $HOME default and an
        # explicit --pdk-root target
        self._pdk_tree(self.home / ".ciel")
        self._pdk_tree(self.alt)
        for rel in (GATE_SOURCES[0], GATE_SOURCES[3]):
            f = self.checkout / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("// selftest fixture\n")
        pin = self.checkout / "scripts" / "setup-env.sh"
        pin.parent.mkdir(parents=True, exist_ok=True)
        pin.write_text(f'CIEL_SKY130_VERSION="{self.PIN}"\n')
        shutil.copyfile(Path(run_tests.__file__),
                        self.checkout / "verification" / "run_tests.py")
        shutil.copyfile(VERIF / "gate-level" / "run-gate-level.sh",
                        self.checkout / "verification" / "gate-level" / "run-gate-level.sh")
        # stub interpreter: one argv per line, the PDK_ROOT it saw, and the
        # record the wrapper's method-note step reads back
        self.argv_file = self.base / "capture.argv"
        self.root_file = self.base / "capture.root"
        stub = self.base / "stub-python"
        stub.write_text("\n".join([
            "#!/bin/sh",
            f'printf \'%s\\n\' "$@" > "{self.argv_file}"',
            f'printf \'%s\\n\' "$PDK_ROOT" > "{self.root_file}"',
            'rec=""',
            'prev=""',
            'for a in "$@"; do',
            '  if [ "$prev" = "--record" ]; then rec="$a"; fi',
            '  prev="$a"',
            'done',
            'mkdir -p "$(dirname "$rec")"',
            "cat > \"$rec\" <<'EOF'",
            json.dumps(_STUB_RECORD, indent=2),
            "EOF",
            "exit 0",
        ]) + "\n")
        stub.chmod(0o755)
        # the wrapper requires iverilog on PATH before it runs; CI executes
        # this self-test before installing a toolchain, so stub it too
        stubbin = self.base / "bin"
        stubbin.mkdir()
        iverilog = stubbin / "iverilog"
        iverilog.write_text("#!/bin/sh\nexit 0\n")
        iverilog.chmod(0o755)
        self.env = {
            "PATH": f"{stubbin}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.home),
            "PYTHON": str(stub),
        }

    def _run_wrapper(self, args=(), pdk_root=None):
        env = dict(self.env)
        if pdk_root is not None:
            env["PDK_ROOT"] = str(pdk_root)
        r = subprocess.run(
            ["bash", str(self.checkout / "verification" / "gate-level" / "run-gate-level.sh"),
             *args], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         f"wrapper failed:\n{r.stdout}\n{r.stderr}")
        root = self.root_file.read_text().strip()
        argv = self.argv_file.read_text().splitlines()
        return root, argv

    def _assert_sources_built_from(self, argv, root):
        """The wrapper's --sources list must name the same root the runner
        process received in PDK_ROOT -- the tokenization contract."""
        i = argv.index("--sources")
        verilog = (Path(root) / "sky130A" / "libs.ref" /
                   "sky130_fd_sc_hd" / "verilog")
        self.assertEqual(argv[i + 1:i + 5], [
            GATE_SOURCES[0],
            str(verilog / "primitives.v"),
            str(verilog / "sky130_fd_sc_hd.v"),
            GATE_SOURCES[3],
        ])

    def test_default_root_is_passed_when_environment_has_none(self):
        root, argv = self._run_wrapper()
        self.assertEqual(root, str(self.home / ".ciel"))
        self._assert_sources_built_from(argv, root)

    def test_inherited_root_wins_over_the_home_default(self):
        root, argv = self._run_wrapper(pdk_root=self.alt)
        self.assertEqual(root, str(self.alt))
        self._assert_sources_built_from(argv, root)

    def test_flag_overrides_an_inherited_root(self):
        root, argv = self._run_wrapper([f"--pdk-root={self.alt}"],
                                       pdk_root=self.home / ".ciel")
        self.assertEqual(root, str(self.alt))
        self._assert_sources_built_from(argv, root)


if __name__ == "__main__":
    unittest.main()
