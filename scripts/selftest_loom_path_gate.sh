#!/bin/sh
# Self-test for scripts/loom-path-gate-base.sh (the ci.yml path gate's base
# selection). Drives the gate with env vars and covers every event shape the
# workflow can see: pull_request, push, merge_group with a valid base, and
# the fail-closed cases (empty or all-zero base on any event, unknown event).
# Run in CI beside the Runner CLI gating self-test.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/loom-path-gate-base.sh"

pass=0
fail=0

# expect_base <desc> <expected-base> [ENV=value ...] -- gate must exit 0 and
# print exactly the expected base.
expect_base() {
  desc="$1"; expected="$2"; shift 2
  out="$(env "$@" sh "$GATE")" && rc=0 || rc=$?
  if [ "$rc" -eq 0 ] && [ "$out" = "$expected" ]; then
    pass=$((pass + 1)); echo "ok: $desc"
  else
    fail=$((fail + 1))
    echo "FAIL: $desc (rc=$rc out='$out' expected='$expected')"
  fi
}

# expect_fail <desc> [ENV=value ...] -- gate must exit non-zero, emit the
# ::error:: annotation on stderr, and leave stdout clean: ci.yml consumes the
# gate's stdout as its return channel (`BASE="$(sh …)"`), so an annotation on
# stdout would be captured and discarded and the step would die with no
# message. Assert on the channels the workflow actually shows, not on a
# merged stream.
expect_fail() {
  desc="$1"; shift
  err_file="$(mktemp)"
  out="$(env "$@" sh "$GATE" 2>"$err_file")" && rc=0 || rc=$?
  err="$(cat "$err_file")"
  rm -f "$err_file"
  if [ "$rc" -ne 0 ]; then
    if [ -n "$out" ]; then
      fail=$((fail + 1)); echo "FAIL: $desc (rc=$rc but stdout not clean: '$out')"
    elif [ -z "$err" ]; then
      fail=$((fail + 1)); echo "FAIL: $desc (rc=$rc but nothing on stderr)"
    else
      case "$err" in
        *"::error::"*)
          pass=$((pass + 1)); echo "ok: $desc"
          ;;
        *)
          fail=$((fail + 1)); echo "FAIL: $desc (rc=$rc but no ::error:: line on stderr)"
          ;;
      esac
    fi
  else
    fail=$((fail + 1)); echo "FAIL: $desc (unexpected exit 0, out='$out')"
  fi
}

SHA1=d4c69cb80c5f66674085f1eacc02008d30d4c69c
ZERO=0000000000000000000000000000000000000000

# pull_request: base is the PR's base sha.
expect_base "pull_request uses the PR base sha" "$SHA1" \
  EVENT=pull_request PR_BASE="$SHA1" PUSH_BEFORE= MG_BASE=
expect_fail "pull_request with empty base fails" \
  EVENT=pull_request PR_BASE= PUSH_BEFORE= MG_BASE=
expect_fail "pull_request with all-zero base fails" \
  EVENT=pull_request PR_BASE="$ZERO" PUSH_BEFORE= MG_BASE=

# push: base is the event's `before` sha.
expect_base "push uses event before sha" "$SHA1" \
  EVENT=push PUSH_BEFORE="$SHA1" PR_BASE= MG_BASE=
expect_fail "push with empty before fails (branch creation)" \
  EVENT=push PUSH_BEFORE= PR_BASE= MG_BASE=
expect_fail "push with all-zero before fails" \
  EVENT=push PUSH_BEFORE="$ZERO" PR_BASE= MG_BASE=

# merge_group: base is the trial-merge commit's base sha.
expect_base "merge_group uses merge_group base sha" "$SHA1" \
  EVENT=merge_group MG_BASE="$SHA1" PR_BASE= PUSH_BEFORE=
expect_fail "merge_group with empty base fails" \
  EVENT=merge_group MG_BASE= PR_BASE= PUSH_BEFORE=
expect_fail "merge_group with all-zero base fails" \
  EVENT=merge_group MG_BASE="$ZERO" PR_BASE= PUSH_BEFORE=

# Any other event falls into the push branch: with the empty env a real run
# has there, it must fail closed rather than silently pass the gate.
expect_fail "unknown event fails closed" \
  EVENT=schedule PUSH_BEFORE= PR_BASE= MG_BASE=

echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
exit 0
