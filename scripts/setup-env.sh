#!/usr/bin/env bash
#
# scripts/setup-env.sh -- pin and provision this repo's verification
# environment.
#
#   1. Creates a local .venv (Python) and installs `klayout-tools` (`klt`)
#      into it at the pinned release version below.
#   2. Installs the pinned Yosys build (YoWASP wheel) into that .venv and
#      verifies its WebAssembly module's sha256 -- the mapper identity that
#      `yosys -V` does NOT report (issue #143) -- then exposes it as
#      `.venv/bin/yosys`.
#   3. Fetches the pinned `sky130A` PDK version via `ciel` into
#      `${PDK_ROOT:-$HOME/.ciel}` and verifies the installed tree's open_pdks
#      revision (its `SOURCES` file) matches the pin.
#   4. Reports -- with an actionable message, never a Python traceback --
#      which of `iverilog`, `verilator`, `openroad` are missing from `$PATH`.
#
# Exit codes:
#   0  venv + klt + yosys + PDK provisioned. iverilog/verilator/openroad may
#      still be individually reported missing (see step 4's summary) -- this
#      is not itself a failure: the gates that need them each report a
#      missing tool as their own hard error when run (npm run lint needs
#      verilator; npm run test needs iverilog, verilator and yosys).
#      P&R specifically needs `openroad`; see the openroad fallback below.
#   1  venv creation, klt install, pinned-yosys install/verification, or PDK
#      fetch failed.
#
# Usage:
#   ./scripts/setup-env.sh
#   ./scripts/setup-env.sh --pdk-root /custom/path
#
# The resolved versions this script pins are recorded in
# flow/smoke/records/environment.json -- update both together if you re-pin.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
cd "${REPO_ROOT}" || exit 1

# --- pinned versions -- keep in sync with flow/smoke/records/environment.json ---
# Keep assignments in plain NAME="value" form so tooling can parse them.
KLT_VERSION="0.9.2"
CIEL_VERSION="2.6.1"
CIEL_PDK_FAMILY="sky130"
CIEL_SKY130_VERSION="f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7"
# Yosys is pinned as a YoWASP PyPI wheel, not as a host package. The wheel is
# `py3-none-any` and ships a single WebAssembly module,
# `yowasp_yosys/yosys.wasm`, which contains Yosys *and* the `abc` mapper
# compiled into it -- so two hosts on the same pinned version execute a
# byte-identical mapper. A host-built `yosys` does not have that property:
# `yosys -V` names the Yosys version but says nothing about the embedded abc
# build, and issue #141 measured two hosts at the same nominal `yosys -V`
# mapping the same design to 1204 vs. 1105 instances. So the pin below is
# checked by CONTENT (the wasm sha256), not by version string.
YOWASP_YOSYS_VERSION="0.68.0.0.post1208"
YOWASP_YOSYS_WASM_SHA256="e37a7e65e3fa4efbbd64a9c1b0e906be16cdc6c4d5273109d17537f78449f38c"
# ----------------------------------------------------------------------------

PDK_ROOT="${PDK_ROOT:-${HOME}/.ciel}"
VENV_DIR="${REPO_ROOT}/.venv"

for arg in "$@"; do
  case "${arg}" in
    --pdk-root)
      echo "error: --pdk-root requires a value, e.g. --pdk-root=/path" >&2
      exit 1
      ;;
    --pdk-root=*)
      PDK_ROOT="${arg#--pdk-root=}"
      ;;
    -h|--help)
      awk 'NR > 1 && /^#/ { print; next } NR > 1 { exit }' "${SELF}"
      exit 0
      ;;
    *)
      echo "unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

status=0

echo "== 1/4 python venv =="
# cocotb is pinned by verification/requirements.txt (cocotb==1.9.2), which
# this script installs via -r in step 2 -- that pin publishes wheels only
# through cp313, so on Python 3.14+ pip would fall back to a source build.
# Pick a compatible interpreter up front so that failure surfaces here, as
# an actionable message, rather than as a pip build-backend traceback in
# step 2.
PYTHON_BIN=""
for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
  found="$(command -v "${candidate}" || true)"
  if [ -z "${found}" ]; then
    continue
  fi
  ver="$("${found}" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null)"
  major="${ver%%.*}"
  minor="${ver##*.}"
  if [ "${major}" = "3" ] && [ "${minor}" -le 13 ] 2>/dev/null; then
    PYTHON_BIN="${found}"
    break
  fi
done

if [ -z "${PYTHON_BIN}" ]; then
  echo "FATAL: no Python <= 3.13 interpreter found on \$PATH."
  echo "  cocotb 1.9.2 (pinned by verification/requirements.txt) publishes"
  echo "  no wheel for Python 3.14+."
  echo "  -> install a compatible interpreter, e.g.:"
  echo "       brew install python@3.13   (macOS/Homebrew)"
  echo "       uv python install 3.13     (if 'uv' is available)"
  echo "       apt-get install python3.13 (Debian/Ubuntu with deadsnakes/backports)"
  echo "     then re-run this script; it prefers python3.13 > 3.12 > 3.11 >"
  echo "     3.10 > plain python3 automatically once one exists on \$PATH."
  exit 1
fi
echo "python3: $(${PYTHON_BIN} --version 2>&1) (${PYTHON_BIN})"

if [ ! -d "${VENV_DIR}" ]; then
  if ! "${PYTHON_BIN}" -m venv "${VENV_DIR}"; then
    echo "FATAL: 'python3 -m venv ${VENV_DIR}' failed."
    echo "  -> on Debian/Ubuntu this usually means the venv module is"
    echo "     missing: 'apt-get install python3-venv'."
    exit 1
  fi
  echo "created ${VENV_DIR}"
else
  echo "reusing existing ${VENV_DIR}"
fi

VENV_PY="${VENV_DIR}/bin/python3"
VENV_PIP="${VENV_DIR}/bin/pip"
if [ ! -x "${VENV_PY}" ]; then
  echo "FATAL: ${VENV_PY} not found after venv creation -- venv looks corrupt."
  echo "  -> remove ${VENV_DIR} and re-run this script."
  exit 1
fi

echo
echo "== 2/4 klayout-tools (klt) ${KLT_VERSION} =="
if ! "${VENV_PY}" -m pip --version >/dev/null 2>&1; then
  echo "FATAL: pip is not available inside ${VENV_DIR}."
  echo "  -> remove ${VENV_DIR} and re-run this script (venv bootstrap likely"
  echo "     failed partway through)."
  exit 1
fi

if ! "${VENV_PIP}" install --quiet --upgrade pip; then
  echo "WARNING: could not upgrade pip in ${VENV_DIR}; continuing with the"
  echo "  version venv bundled."
fi

if ! "${VENV_PIP}" install --quiet \
    "klayout-tools==${KLT_VERSION}" "ciel==${CIEL_VERSION}" \
    -r "${REPO_ROOT}/verification/requirements.txt"; then
  echo "FATAL: failed to install klayout-tools/ciel/verification/requirements.txt"
  echo "  (cocotb harness pin included) into ${VENV_DIR}."
  echo "  -> common causes: no network access to PyPI, or no C/C++"
  echo "     toolchain for a dependency's native build (install Xcode CLI"
  echo "     tools on macOS: 'xcode-select --install'; build-essential on"
  echo "     Debian/Ubuntu)."
  echo "  -> re-run with the venv's own pip for a full traceback:"
  echo "       ${VENV_PIP} install \"klayout-tools==${KLT_VERSION}\" ciel==${CIEL_VERSION} -r verification/requirements.txt"
  exit 1
fi
INSTALLED_KLT_VERSION="$("${VENV_PY}" -m klayout_tools.cli --version 2>/dev/null || true)"
INSTALLED_KLT_VERSION="${INSTALLED_KLT_VERSION#klt }"
echo "installed: klt ${INSTALLED_KLT_VERSION:-(version unknown)} from PyPI (pinned ${KLT_VERSION})"
echo "activate with: source ${VENV_DIR}/bin/activate"

echo
echo "== 3/4 yosys (YoWASP ${YOWASP_YOSYS_VERSION}) =="
# Why a wheel and not the host's `yosys`: see the pin block at the top of this
# file. The check below is the load-bearing half -- it verifies the *content*
# of the WebAssembly module (Yosys + its embedded `abc`), which is the mapper
# identity `yosys -V` does not expose.
if ! "${VENV_PIP}" install --quiet "yowasp-yosys==${YOWASP_YOSYS_VERSION}"; then
  echo "FATAL: failed to install yowasp-yosys==${YOWASP_YOSYS_VERSION} into ${VENV_DIR}."
  echo "  -> common causes: no network access to PyPI, or a proxy that"
  echo "     rejects the ~40 MB wheel download."
  echo "  -> re-run with the venv's own pip for a full traceback:"
  echo "       ${VENV_PIP} install \"yowasp-yosys==${YOWASP_YOSYS_VERSION}\""
  exit 1
fi

WASM_INFO="$("${VENV_PY}" - <<'PY'
import hashlib
import os
import sys

try:
    import yowasp_yosys
except Exception as exc:  # pragma: no cover - reported, never raised at user
    print(f"ERROR\t{exc}")
    sys.exit(0)

path = os.path.join(os.path.dirname(yowasp_yosys.__file__), "yosys.wasm")
if not os.path.isfile(path):
    print(f"ERROR\tno yosys.wasm at {path}")
    sys.exit(0)

digest = hashlib.sha256()
with open(path, "rb") as handle:
    for chunk in iter(lambda: handle.read(1 << 20), b""):
        digest.update(chunk)
print(f"OK\t{path}\t{digest.hexdigest()}")
PY
)"

case "${WASM_INFO}" in
  OK*)
    WASM_PATH="$(printf '%s' "${WASM_INFO}" | cut -f2)"
    WASM_SHA="$(printf '%s' "${WASM_INFO}" | cut -f3)"
    ;;
  *)
    echo "FATAL: could not locate the installed YoWASP Yosys WebAssembly module."
    echo "  detail: $(printf '%s' "${WASM_INFO}" | cut -f2-)"
    echo "  -> remove ${VENV_DIR} and re-run this script."
    exit 1
    ;;
esac

if [ "${WASM_SHA}" != "${YOWASP_YOSYS_WASM_SHA256}" ]; then
  echo "FATAL: pinned Yosys/ABC build identity does NOT match."
  echo "  module:   ${WASM_PATH}"
  echo "  expected: sha256:${YOWASP_YOSYS_WASM_SHA256}"
  echo "  actual:   sha256:${WASM_SHA}"
  echo "  -> this is exactly the failure the pin exists to catch: a different"
  echo "     mapper build maps the same RTL to a different instance count and"
  echo "     can move a timing-closure verdict across the threshold (issue"
  echo "     #141 measured 1.06 ns of setup slack at ss_n40C_1v28). Do NOT"
  echo "     mint evidence records from this environment."
  echo "  -> re-pin deliberately (update YOWASP_YOSYS_VERSION and"
  echo "     YOWASP_YOSYS_WASM_SHA256 here and the matching entry in"
  echo "     flow/smoke/records/environment.json together), or remove ${VENV_DIR} and re-run."
  exit 1
fi
echo "yosys.wasm: sha256:${WASM_SHA} (matches pin)"

# Expose the pinned build under the plain name `yosys`: klt shells out to
# `yosys` by name (klayout_tools/synthesize.py runs `["yosys", "-s", script]`),
# so after `source .venv/bin/activate` the venv's bin/ leads $PATH and the
# pinned build wins over any host install.
if ! ln -sfn "yowasp-yosys" "${VENV_DIR}/bin/yosys"; then
  echo "FATAL: could not link ${VENV_DIR}/bin/yosys -> yowasp-yosys."
  exit 1
fi
echo "linked:     ${VENV_DIR}/bin/yosys -> yowasp-yosys"
echo "reports:    $("${VENV_DIR}/bin/yosys" -V 2>&1 | head -1)"
if command -v yosys >/dev/null 2>&1; then
  echo "note: a host 'yosys' is also on \$PATH ($(command -v yosys)). It is NOT"
  echo "  the pinned build unless it resolves to the link above -- activate the"
  echo "  venv ('source ${VENV_DIR}/bin/activate') before running"
  echo "  'klt synthesize', or the mapper that produced your numbers is"
  echo "  unidentified."
fi

echo
echo "== 4/4 sky130A PDK (ciel ${CIEL_VERSION}, open_pdks ${CIEL_SKY130_VERSION:0:12}) =="
mkdir -p "${PDK_ROOT}"
if "${VENV_DIR}/bin/ciel" enable \
    --pdk-root "${PDK_ROOT}" --pdk-family "${CIEL_PDK_FAMILY}" \
    -l sky130_fd_pr "${CIEL_SKY130_VERSION}"; then
  # Verify the tree we will actually use IS the pinned open_pdks revision: its
  # SOURCES file names the revision it was built from. A missing or different
  # revision is a hard failure, never a silent pass -- a stray tree (e.g. a
  # leftover ~/.volare at the previous pin) must not stand in for the pin.
  SOURCES_FILE="${PDK_ROOT}/sky130A/SOURCES"
  if [ ! -f "${SOURCES_FILE}" ]; then
    echo "FATAL: ${SOURCES_FILE} not found; cannot verify the open_pdks revision."
    status=1
  elif ! grep -q "${CIEL_SKY130_VERSION}" "${SOURCES_FILE}"; then
    echo "FATAL: PDK revision mismatch under ${PDK_ROOT}: ${SOURCES_FILE} does not"
    echo "  name the pinned open_pdks ${CIEL_SKY130_VERSION}. It says:"
    sed 's/^/    /' "${SOURCES_FILE}"
    status=1
  else
    echo "sky130A ready under ${PDK_ROOT} (open_pdks ${CIEL_SKY130_VERSION:0:12} verified via SOURCES)"
  fi
else
  echo "FATAL: 'ciel enable' failed to fetch sky130 ${CIEL_SKY130_VERSION:0:12}."
  echo "  -> common causes: no network access to GitHub releases, or a rate"
  echo "     limit on unauthenticated GitHub API requests -- set GITHUB_TOKEN"
  echo "     and re-run, or run manually:"
  echo "       ${VENV_DIR}/bin/ciel enable --pdk-root ${PDK_ROOT} --pdk-family ${CIEL_PDK_FAMILY} -l sky130_fd_pr ${CIEL_SKY130_VERSION}"
  status=1
fi

echo
echo "== toolchain check (iverilog / verilator / openroad) =="
# yosys is NOT probed here: step 3 provisions it into the venv at a pinned,
# digest-verified build. A host `yosys` on $PATH is not that build (issue
# #143), so "some yosys resolves" is not the property this check should
# report.
echo "  yosys:    ${VENV_DIR}/bin/yosys (pinned, verified in step 3)"
missing=()
if command -v iverilog >/dev/null 2>&1; then
  echo "  iverilog: $(iverilog -V 2>&1 | head -1)"
else
  missing+=("iverilog")
fi

if command -v verilator >/dev/null 2>&1; then
  echo "  verilator: $(verilator --version 2>&1 | head -1)"
else
  missing+=("verilator")
fi

# openroad: prefer a native install already on $PATH. Otherwise, openroad has
# no Homebrew formula or common-distro package (see scripts/openroad-docker.sh), so
# fall back to the pinned openroad/orfs Docker image via
# scripts/openroad-docker.sh, symlinked into .venv/bin so activating the venv
# makes `openroad` resolve the same way iverilog/yosys do. This only installs
# the symlink (no network needed); the image itself is pulled lazily on first
# `openroad` invocation.
if command -v openroad >/dev/null 2>&1; then
  echo "  openroad: $(openroad -version 2>&1 | head -1) (native, on \$PATH)"
elif command -v docker >/dev/null 2>&1; then
  ln -sf "../../scripts/openroad-docker.sh" "${VENV_DIR}/bin/openroad"
  chmod +x "${VENV_DIR}/bin/openroad"
  echo "  openroad: not native, but docker is available -- symlinked"
  echo "    ${VENV_DIR}/bin/openroad -> scripts/openroad-docker.sh (pinned"
  echo "    openroad/orfs image; see scripts/openroad-docker.sh). After"
  echo "    'source ${VENV_DIR}/bin/activate', 'openroad -version' resolves"
  echo "    through Docker (first call pulls the image)."
else
  missing+=("openroad")
fi

if [ "${#missing[@]}" -gt 0 ]; then
  echo
  echo "MISSING TOOLS: ${missing[*]}"
  for tool in "${missing[@]}"; do
    case "${tool}" in
      iverilog)
        echo "  - iverilog (Icarus Verilog): 'brew install icarus-verilog' (macOS)"
        echo "    or 'apt-get install iverilog' (Debian/Ubuntu). Required for"
        echo "    'klt functional-verification' and verification/run_tests.py"
        echo "    (npm run test)."
        ;;
      verilator)
        echo "  - verilator: 'brew install verilator' (macOS) or"
        echo "    'apt-get install verilator' (Debian/Ubuntu). Required for"
        echo "    scripts/lint-rtl.sh (npm run lint) and"
        echo "    verification/run_tests.py (npm run test)."
        ;;
      openroad)
        echo "  - openroad: no package-manager formula on macOS or common Linux"
        echo "    distros as of this writing, and no 'docker' found on \$PATH"
        echo "    either, so scripts/openroad-docker.sh's fallback route"
        echo "    couldn't be wired up automatically. Install Docker (or"
        echo "    Docker Desktop), then re-run this script -- or see"
        echo "    scripts/openroad-docker.sh for the pinned image and"
        echo "    flow/smoke/records/environment.json."
        echo "    Required for 'klt place-and-route' -- see scripts/openroad-docker.sh."
        ;;
    esac
  done
  echo
  echo "This is expected and non-fatal for this script: each verification"
  echo "gate reports a missing tool as its own hard error when you run it."
  echo "npm run lint needs verilator; npm run test needs iverilog,"
  echo "verilator and yosys; npm run check:records needs only python3."
  echo "synthesis uses the pinned yosys above (already provisioned);"
  echo "place-and-route additionally needs openroad -- see the 'Cold"
  echo "start' and 'T1 item 9' sections of verification/README.md for"
  echo "which legs run where."
else
  echo "all of iverilog/verilator/yosys/openroad resolve (yosys from the"
  echo "  pin above, iverilog and verilator natively, openroad natively or"
  echo "  via the pinned Docker route)."
fi

echo
if [ "${status}" -eq 0 ]; then
  echo "RESULT: environment provisioned (venv + klt + pinned yosys + sky130A)."
else
  echo "RESULT: environment provisioning incomplete -- see FATAL messages above."
fi
exit "${status}"
