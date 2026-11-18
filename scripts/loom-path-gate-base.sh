#!/bin/sh
# Select the base sha for the ci.yml path gate (job `loom-tooling`, step
# "Detect changed vendored Loom tooling paths"): the commit to diff against
# HEAD when deciding whether `.loom/` paths changed. Prints the base sha on
# stdout, or exits non-zero with a `::error::` annotation on stderr -- stdout
# stays clean because ci.yml consumes it as the return channel
# (`BASE="$(sh scripts/loom-path-gate-base.sh)"`), so an annotation written to
# stdout there would be captured and discarded -- when no usable base exists
# (empty or all-zero), so the gate fails loudly instead of silently skipping
# the suites below (see .loom/docs/ci-principles.md).
#
# Inputs arrive as step `env:` set from event context, never as `${{ }}`
# interpolation into this script: EVENT, PR_BASE (pull_request base sha),
# PUSH_BEFORE (push event `before`), MG_BASE (merge_group base_sha -- on the
# queue the checked-out ref is the trial merge, so this is its base).
# pull_request and push keep their pre-merge-queue behaviour byte-identical;
# any other event falls into the push branch, whose empty env fails closed.
set -u

EVENT="${EVENT:-}"
PR_BASE="${PR_BASE:-}"
PUSH_BEFORE="${PUSH_BEFORE:-}"
MG_BASE="${MG_BASE:-}"

case "$EVENT" in
  pull_request) BASE="$PR_BASE" ;;
  merge_group)  BASE="$MG_BASE" ;;
  *)            BASE="$PUSH_BEFORE" ;;
esac

fail() {
  # stderr, not stdout: ci.yml captures stdout as the return channel.
  echo "::error::base sha unavailable ('$BASE'); cannot diff .loom/ paths" >&2
  exit 1
}

[ -n "$BASE" ] || fail
# An all-zero sha is GitHub's "no commit" placeholder (e.g. a branch-creation
# push): unusable, same as empty.
case "$BASE" in
  *[!0]*) printf '%s\n' "$BASE" ;;
  *)      fail ;;
esac
