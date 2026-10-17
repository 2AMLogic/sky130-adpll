#!/usr/bin/env bash
# RTL lint gate: verilator --lint-only -Wall over rtl/**/*.v (and .sv).
# Passes visibly-vacuously while rtl/ holds no Verilog; fails if verilator
# is missing (a skipped lint must never look like a pass).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RTL_DIR="${RTL_DIR:-$ROOT/rtl}"

command -v verilator >/dev/null 2>&1 || { echo "lint-rtl: verilator not found" >&2; exit 2; }

mapfile -t files < <(find "$RTL_DIR" -type f \( -name '*.v' -o -name '*.sv' \) | sort)
if [ "${#files[@]}" -eq 0 ]; then
  echo "lint-rtl: no RTL files under $RTL_DIR, vacuous pass"
  exit 0
fi

echo "lint-rtl: $(verilator --version)"
echo "lint-rtl: linting ${#files[@]} file(s)"
# All files in one run so cross-module references resolve. Set TOP to pick
# the top module once there is more than one uppermost module.
exec verilator --lint-only -Wall -I"$RTL_DIR" ${TOP:+--top-module "$TOP"} "${files[@]}"
