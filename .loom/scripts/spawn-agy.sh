#!/usr/bin/env bash
# spawn-agy.sh - Tier-3 "generic passthrough" adapter for Google's Antigravity
# CLI (`agy`), the second route of the Gemini pilot (issue #14945).
#
# Thinner than spawn-aider.sh but thicker than spawn-gemini.sh, deliberately:
# like gemini, the launch SHAPE (cliBin/promptFlag/modelFlag) lives in
# `defaults/runtimes/agy.json` and is resolved by spawn-generic-launch.sh.
# Unlike gemini, the pilot carries two per-launch requirements the shared
# template cannot express as static manifest data:
#
#   1. An isolated CLI settings location OUTSIDE the checkout. The canary
#      (loom-crew-8, 2026-11-22, agy 1.5.14) ran with its own HOME holding a
#      settings file naming "modelProvider": "gemini" and needed no Google
#      login. A fresh per-launch HOME both supplies that settings file and
#      keeps agy away from any cached login under the operator's real HOME —
#      the credential MUST come from the gemini API-key pool the worker
#      process selected (manifest credentialPool), never from a stored
#      session, or the pilot's shared maxConcurrent cap is bypassable.
#   2. The guarded permission choice: `--sandbox` (plus the `--settings`
#      argument naming the isolated file). agy's headless default can
#      auto-approve some edits; the pilot pins the explicit sandbox policy
#      instead of the auto-approve flag. A tool denial can still exit 0, so
#      the read-only outcome is verified live, not trusted (see
#      defaults/docs/runtime-adapters.md's agy section).
#
# Both are composed here as LOOM_GENERIC_EXTRA_ARGS DEFAULTS: an operator who
# exported LOOM_GENERIC_EXTRA_ARGS already wins (the env > manifest tier
# spawn-generic-launch.sh documents), and the manifest's launch object stays
# free of per-launch paths.
#
# The GEMINI_API_KEY itself is NOT handled here: `loom-daemon spawn-worker`
# selects the gemini pool account and injects the key into this process's
# environment before exec'ing the runner, so the lease is counted against
# the worker PID that becomes the run.
#
# Usage:
#   .loom/scripts/spawn-agy.sh -p "your prompt"
#   LOOM_RUNTIME=agy .loom/scripts/spawn-worker.sh -p "your prompt"
set -euo pipefail

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Per-launch isolated HOME: outside every checkout, owner-only, never reused.
# `agy` state (settings, any cache) lives and dies with the launch; nothing
# accumulates on the host and no cached login can be picked up.
AGY_HOME="$(mktemp -d "${TMPDIR:-/tmp}/loom-agy-XXXXXX")"
chmod 700 "$AGY_HOME"
printf '{"modelProvider": "gemini"}\n' >"$AGY_HOME/settings.json"
chmod 600 "$AGY_HOME/settings.json"

# Guarded launch argv: the settings argument selecting the gemini provider,
# and the sandbox policy (never agy's auto-approve flag). Set as DEFAULTS
# only — an operator-pinned LOOM_GENERIC_EXTRA_ARGS stays authoritative and
# this script adds nothing on top of it.
if [[ -z "${LOOM_GENERIC_EXTRA_ARGS:-}" ]]; then
    LOOM_GENERIC_EXTRA_ARGS="--settings $AGY_HOME/settings.json --sandbox"
    export LOOM_GENERIC_EXTRA_ARGS
fi
export HOME="$AGY_HOME"

exec "${_SCRIPT_DIR}/spawn-generic-launch.sh" agy "$@"
