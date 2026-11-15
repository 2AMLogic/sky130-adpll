#!/bin/sh
# Verify reuse.lock.json attests the committed content of the files it pins.
# Run by .github/workflows/signoff.yml and `npm run check:ci`; see
# manifests/README.md. Fails (non-zero) if a recorded sha256 does not match
# the committed content of the file it records. Hashes are taken from HEAD,
# not the working tree, so a dirty worktree cannot bake a local edit into the
# attestation. Entries without per-file hashes (mode "referenced") carry no
# content and are skipped.
set -eu
cd "$(dirname "$0")/.."

command -v git >/dev/null 2>&1 || { echo "error: git not on PATH" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "error: python3 not on PATH" >&2; exit 1; }

python3 - <<'EOF'
import hashlib
import json
import subprocess
import sys

with open("reuse.lock.json", encoding="utf-8") as f:
    lock = json.load(f)

failures = []
checked = 0
for entry in lock.get("entries", []):
    for rec in entry.get("files", []):
        path = rec.get("path")
        recorded = rec.get("sha256")
        if not path or not recorded:
            continue  # no hash attested, nothing to check
        checked += 1
        try:
            blob = subprocess.run(
                ["git", "cat-file", "blob", f"HEAD:{path}"],
                capture_output=True, check=True,
            ).stdout
        except subprocess.CalledProcessError:
            failures.append(f"{path}: recorded {recorded}, but the file is not in HEAD")
            continue
        actual = hashlib.sha256(blob).hexdigest()
        if actual != recorded:
            failures.append(f"{path}: recorded {recorded}, committed content hashes to {actual}")

for msg in failures:
    print(f"error: reuse.lock.json: {msg}", file=sys.stderr)
print(f"reuse.lock.json: {checked} attested file(s) checked against HEAD")
if failures:
    sys.exit(1)
EOF
