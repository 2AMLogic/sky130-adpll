#!/bin/sh
# Verify the committed T1 evidence records still reproduce. Run by
# .github/workflows/signoff.yml and `npm run check:ci`; see manifests/README.md.
# Fails (non-zero) if klt is missing, a render errors, or a record has drifted.
set -eu
cd "$(dirname "$0")/.."

command -v klt >/dev/null 2>&1 || { echo "error: klt not on PATH (pin: see manifests/README.md)" >&2; exit 1; }
klt --version

klt signoff --attest 10 --inventory manifests/item10.inventory.json \
    --check manifests/item10.attestation.json
klt signoff --manifest manifests/sky130-adpll.json \
    --tiers-doc manifests/design-evidence-tiers.md \
    --check manifests/sky130-adpll.signoff.json
