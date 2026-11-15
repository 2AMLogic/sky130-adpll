#!/usr/bin/env bash
#
# verification/gate-level/run-gate-level.sh -- run the `top` suite's cocotb
# test module against the synthesized sky130_fd_sc_hd netlist.
#
# This is a PRE-LAYOUT, ZERO-DELAY FUNCTIONAL simulation. It is not a timing
# result: no SDF is back-annotated and the cell models' specify/timing arm is
# deliberately not selected. See verification/gate-level/README.md.
#
# What it does, in order:
#   1. Resolves the sky130 cell models under $PDK_ROOT and verifies the tree
#      IS the open_pdks revision scripts/setup-env.sh pins (its SOURCES file).
#   2. Verifies every source file on the list exists -- a missing PDK or model
#      file is a hard error with the path, never a skip and never a Python
#      traceback.
#   3. Runs verification/run_tests.py (--level gate) on the netlist with the
#      RTL suite's own test module, test_top. run_tests.py itself captures the
#      compile log, derives the cell-model arm from it, records the arm in the
#      record and fails a gate-level run that selected the timing arm -- so
#      this wrapper carries no duplicate of that check. It also records the
#      netlist's path and sha256 into the record (--netlist), which
#      check_records.py re-derives against the tree.
#   4. Writes a companion method note beside the record naming the defines
#      and the PDK revision -- fields the record schema does not carry.
#      (The netlist path and its sha256 moved into the record itself:
#      the note reads them back from it rather than recomputing the hash.)
#
# Exit codes:
#   0  smoke test passed, negative control failed on its assertion, record written
#   1  a pre-check failed (PDK/model/netlist/toolchain) or the run did not
#      meet its expectation -- including the timing-arm refusal, which
#      run_tests.py reports as a PROBLEM line and a failed record
#
# Usage:
#   ./verification/gate-level/run-gate-level.sh
#   ./verification/gate-level/run-gate-level.sh --seed=12345
#   ./verification/gate-level/run-gate-level.sh --pdk-root=/custom/path
#   PYTHON=/path/to/python ./verification/gate-level/run-gate-level.sh
#
# Scope: the `top` suite is the only one that can run here. It drives ports
# only, while e.g. test_loop_filter reads dut.integ -- an internal net
# synthesis does not preserve.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}" || exit 1

HERE="verification/gate-level"
DEFINES="${HERE}/sky130_fd_sc_hd_sim_defines.v"
NETLIST="flow/adpll/records/adpll_top_synth.v"
RECORD="${HERE}/records/result-gate.json"
NOTE="${HERE}/records/result-gate.method.md"
TOPLEVEL="adpll_top"
TEST_MODULE="test_top"
TEST_DIR="verification"
TESTS="test_integrates_and_locks"
SETUP_ENV="scripts/setup-env.sh"

PDK_ROOT="${PDK_ROOT:-${HOME}/.ciel}"
PYTHON="${PYTHON:-${REPO_ROOT}/.venv/bin/python}"
SEED=""

die() {
  echo "FATAL: $*" >&2
  exit 1
}

for arg in "$@"; do
  case "${arg}" in
    --pdk-root=*) PDK_ROOT="${arg#--pdk-root=}" ;;
    --seed=*)     SEED="${arg#--seed=}" ;;
    --record=*)   RECORD="${arg#--record=}"; NOTE="${RECORD%.json}.method.md" ;;
    --pdk-root|--seed|--record)
      die "${arg} requires a value, e.g. ${arg}=<value>" ;;
    -h|--help)    sed -n '2,40p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *)            die "unknown option: ${arg}" ;;
  esac
done

# --- 1/3 PDK revision ------------------------------------------------------
# The pin lives in exactly one place: scripts/setup-env.sh. Parse it rather
# than duplicating it, so a re-pin there cannot leave this script grading a
# different PDK than the one the environment provisions.
echo "== 1/3 sky130A PDK under ${PDK_ROOT} =="
[ -f "${SETUP_ENV}" ] || die "${SETUP_ENV} not found; cannot read the PDK pin."
PINNED_PDK="$(sed -n 's/^CIEL_SKY130_VERSION="\([0-9a-f]\{40\}\)"$/\1/p' "${SETUP_ENV}" | head -1)"
[ -n "${PINNED_PDK}" ] ||
  die "could not parse CIEL_SKY130_VERSION from ${SETUP_ENV}
  -> that pin is this script's only source of truth for the PDK revision; if
     its assignment form changed, update the sed expression here too."

SOURCES_FILE="${PDK_ROOT}/sky130A/SOURCES"
[ -f "${SOURCES_FILE}" ] ||
  die "${SOURCES_FILE} not found: no sky130A tree under PDK_ROOT=${PDK_ROOT}.
  -> run ${SETUP_ENV} (step 4/4 fetches the pinned PDK), or pass
     --pdk-root=<path> / set PDK_ROOT to the tree you mean."
if ! grep -q "${PINNED_PDK}" "${SOURCES_FILE}"; then
  die "PDK revision mismatch under ${PDK_ROOT}.
  expected (${SETUP_ENV} pin): open_pdks ${PINNED_PDK}
  installed (${SOURCES_FILE}): $(tr '\n' ' ' < "${SOURCES_FILE}" | sed 's/ *$//')
  -> a stray tree must not stand in for the pin: cell models differ between
     open_pdks revisions, so a record minted here would not be the pinned
     environment's result. Re-run ${SETUP_ENV}."
fi
echo "  open_pdks ${PINNED_PDK:0:12} verified via SOURCES"

# --- 2/3 source list -------------------------------------------------------
# The defines file MUST come first: iverilog shares one macro scope across the
# files named on its command line and evaluates each cell's `ifdef FUNCTIONAL
# where it appears, and run_tests.py preserves the order given here.
V="${PDK_ROOT}/sky130A/libs.ref/sky130_fd_sc_hd/verilog"
SOURCES=(
  "${DEFINES}"
  "${V}/primitives.v"
  "${V}/sky130_fd_sc_hd.v"
  "${NETLIST}"
)

echo
echo "== 2/3 source list =="
for src in "${SOURCES[@]}"; do
  [ -f "${src}" ] ||
    die "source file not found: ${src}
  -> if it is under ${PDK_ROOT}, run ${SETUP_ENV} to provision the pinned
     sky130A cell models; if it is in the repo, it is missing from the tree."
  echo "  $(du -h "${src}" | cut -f1)	${src}"
done

command -v iverilog >/dev/null 2>&1 ||
  die "iverilog not found on \$PATH.
  -> 'apt-get install iverilog' (Debian/Ubuntu) or 'brew install
     icarus-verilog' (macOS); ${SETUP_ENV} reports it under 'toolchain check'."
[ -x "${PYTHON}" ] ||
  die "python interpreter not found: ${PYTHON}
  -> run ${SETUP_ENV} to create the venv (it installs cocotb), or set
     PYTHON=<interpreter with cocotb> explicitly."

# --- 3/3 simulation --------------------------------------------------------
# The arm guard lives in run_tests.py itself now: it captures the compile log,
# derives the cell-model arm from it and fails a gate-level run that selected
# the timing arm. This wrapper carries no duplicate of that check.
echo
echo "== 3/3 cocotb run (test_top on the netlist, --level gate) =="
# --build-dir must be ABSOLUTE: cocotb's runner resolves results_xml relative
# to --test-dir (it chdir's there to run the simulator), so a relative build
# dir sends the xml to verification/<build-dir>/... while the simulator writes
# to <repo>/<build-dir>/..., and the run reports "simulator produced no
# results" even though every test passed.
RUN=("${PYTHON}" verification/run_tests.py
     --level gate
     --sources "${SOURCES[@]}"
     --netlist "${NETLIST}"
     --toplevel "${TOPLEVEL}"
     --test-module "${TEST_MODULE}"
     --test-dir "${TEST_DIR}"
     --tests "${TESTS}"
     --build-dir "${REPO_ROOT}/sim/build/gate-level"
     --record "${RECORD}")
[ -n "${SEED}" ] && RUN+=(--seed "${SEED}")
"${RUN[@]}" || die "the gate-level run did not meet its expectation (see PROBLEM lines above).
  -> the record at ${RECORD} carries the detail; it is NOT evidence of a pass."

# --- companion method note -------------------------------------------------
# The record now carries the netlist path and its sha256 (dut.netlist /
# dut.netlist_sha256, written by run_tests.py --netlist and re-derived
# against the tree by check_records.py). The note adds the two fields the
# record still does not carry -- the sim defines and the PDK revision --
# and reads the netlist rows back from the record: one hash computation,
# one source of truth.
PINNED_PDK="${PINNED_PDK}" DEFINES="${DEFINES}" RECORD="${RECORD}" NOTE="${NOTE}" \
python3 - <<'PY' || die "could not write the companion method note."
import json
import os
from pathlib import Path

rec = json.loads(Path(os.environ["RECORD"]).read_text())
tools = rec["tools"]
tests = "\n".join(
    f"| `{t['name']}` | {'FAIL' if t['expected_fail'] else 'PASS'} "
    f"| {'pass' if t['passed'] else 'fail'} | {'ok' if t['ok'] else 'BAD'} |"
    for t in rec["tests"]
)
Path(os.environ["NOTE"]).write_text(f"""# gate-level result: method

Generated by `verification/gate-level/run-gate-level.sh` alongside
`{os.path.basename(os.environ['RECORD'])}`. Do not hand-edit; re-run the script.

**Pre-layout, zero-delay functional simulation. Not a timing result.**
No SDF is back-annotated, no static timing is involved, and the cell models'
`specify`/timing arm is deliberately not selected, so this record says nothing
about frequency, delay or jitter -- only that the RTL suite's own test module
behaves identically on the synthesized netlist.

| | |
|---|---|
| netlist | `{rec['dut']['netlist']}` |
| netlist sha256 | `{rec['dut']['netlist_sha256']}` |
| cell models | `$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/verilog/{{primitives,sky130_fd_sc_hd}}.v` |
| open_pdks revision | `{os.environ['PINNED_PDK']}` |
| sim defines | `FUNCTIONAL`, `UNIT_DELAY` (empty = zero delay); `USE_POWER_PINS` undefined |
| defines file | `{os.environ['DEFINES']}` (first on the source list) |
| SDF | none |
| toplevel | `{rec['dut']['toplevel']}` |
| test module | `verification/test_top.py`, unmodified from the RTL run (the `top` suite's own) |
| seed | `{rec['seed']}` |
| iverilog | {tools['iverilog']} |
| cocotb | {tools['cocotb']} |
| python | {tools['python']} |
| commit | `{rec['commit']}` (dirty: {str(rec['dirty']).lower()}) |
| level | `{rec['level']}` |

| test | expected | observed | verdict |
|---|---|---|---|
{tests}

The netlist sha256 above is recorded in
`{os.path.basename(os.environ['RECORD'])}` as `dut.netlist_sha256`;
`check_records.py` re-derives the sha256 of that file in the tree and fails
the record if it no longer matches or the file is gone -- staleness is a
failure, not a manual comparison.
""")
print(f"note:   {os.environ['NOTE']}")
PY

echo
echo "RESULT: gate-level functional run passed; record + method note committed-ready."
