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
#   3. Compiles the source list with iverilog and REFUSES to continue if the
#      cell models' timing arm was selected. Omitting `FUNCTIONAL` does not
#      fail: it silently produces a timing simulation that passes, whose
#      record is indistinguishable from this one but carries the models'
#      built-in typ delays. A `Choosing typ expression' warning is the tell.
#   4. Runs verification/run_tests.py (unmodified, --level gate) on the
#      netlist with the RTL suite's own test module, test_top.
#   5. Writes a companion method note beside the record naming the netlist
#      sha256 that was graded, the defines, the PDK revision and the seed --
#      the record schema has no field for any of those.
#
# Exit codes:
#   0  smoke test passed, negative control failed on its assertion, record written
#   1  a pre-check failed (PDK/model/netlist/toolchain), the wrong cell-model
#      arm was selected, or the simulation did not meet the expectation
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
    -h|--help)    sed -n '2,46p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *)            die "unknown option: ${arg}" ;;
  esac
done

# --- 1/4 PDK revision ------------------------------------------------------
# The pin lives in exactly one place: scripts/setup-env.sh. Parse it rather
# than duplicating it, so a re-pin there cannot leave this script grading a
# different PDK than the one the environment provisions.
echo "== 1/4 sky130A PDK under ${PDK_ROOT} =="
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

# --- 2/4 source list -------------------------------------------------------
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
echo "== 2/4 source list =="
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

# --- 3/4 method guard ------------------------------------------------------
# Refuse to mint a record from the wrong cell-model arm. This is the whole
# reason the step exists: without `FUNCTIONAL the compile still exits 0 and
# the suite still passes, so nothing downstream would catch it.
echo
echo "== 3/4 cell-model arm (method guard) =="
COMPILE_LOG="$(mktemp -t gate-level-compile.XXXXXX)"
COMPILE_OUT="$(mktemp -t gate-level-compile.XXXXXX.vvp)"
trap 'rm -f "${COMPILE_LOG}" "${COMPILE_OUT}"' EXIT
if ! iverilog -o "${COMPILE_OUT}" -s "${TOPLEVEL}" "${SOURCES[@]}" \
     >"${COMPILE_LOG}" 2>&1; then
  sed 's/^/    /' "${COMPILE_LOG}" >&2
  die "iverilog could not compile the source list above."
fi
if grep -q "Choosing typ expression" "${COMPILE_LOG}"; then
  grep "Choosing typ expression" "${COMPILE_LOG}" | sort | uniq -c |
    head -5 | sed 's/^/    /' >&2
  die "the cell models' specify/timing arm was selected, not the behavioural one.
  -> this run would produce a passing record carrying the models' built-in typ
     delays -- an unstated timing claim. Check that ${DEFINES} defines
     FUNCTIONAL and is listed FIRST on the source list above."
fi
if [ -s "${COMPILE_LOG}" ]; then
  echo "  NOTE: the compile was not warning-free ($(wc -l < "${COMPILE_LOG}" | tr -d ' ') lines):"
  sort "${COMPILE_LOG}" | uniq -c | head -5 | sed 's/^/    /'
  echo "  (not fatal, but the expected result is zero warnings -- see ${DEFINES})"
else
  echo "  warning-free compile: FUNCTIONAL arm, zero delay, no timing claim"
fi

# --- 4/4 simulation --------------------------------------------------------
echo
echo "== 4/4 cocotb run (test_top on the netlist, --level gate) =="
# --build-dir must be ABSOLUTE: cocotb's runner resolves results_xml relative
# to --test-dir (it chdir's there to run the simulator), so a relative build
# dir sends the xml to verification/<build-dir>/... while the simulator writes
# to <repo>/<build-dir>/..., and the run reports "simulator produced no
# results" even though every test passed.
RUN=("${PYTHON}" verification/run_tests.py
     --level gate
     --sources "${SOURCES[@]}"
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
# run_tests.py's record schema has no field for the defines, the PDK revision
# or the netlist hash, so the method is not self-evident from the record alone.
# Write it beside the record, generated from the same run.
NETLIST_SHA="$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "${NETLIST}")"
PINNED_PDK="${PINNED_PDK}" NETLIST_SHA="${NETLIST_SHA}" NETLIST="${NETLIST}" \
DEFINES="${DEFINES}" RECORD="${RECORD}" NOTE="${NOTE}" \
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
| netlist | `{os.environ['NETLIST']}` |
| netlist sha256 | `{os.environ['NETLIST_SHA']}` |
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

The netlist sha256 above is the artifact this record grades. If it no longer
matches `netlist_sha256` in `flow/adpll/records/synthesize-output.json`, the
netlist has been regenerated since and this record describes an artifact that
is no longer in the tree -- re-run the script.
""")
print(f"note:   {os.environ['NOTE']}")
PY

echo
echo "RESULT: gate-level functional run passed; record + method note committed-ready."
