# Block manifest and tier-verdict record

`klt signoff` input and committed output for T1 of
[`klayout-tools` `docs/design-evidence-tiers.md`](https://github.com/2AMLogic/klayout-tools/blob/v0.8.0/docs/design-evidence-tiers.md).
The committed record is the verdict of record; it is graded, not hand-read.

## Files

- `sky130-adpll.json`: block manifest (`block: sky130-adpll`, `kind: digital`).
  It cites item 10 only; every other item stays uncited until its evidence lands.
- `sky130-adpll.signoff.json`: tool-produced verdict of record (`--format json`).
  All items except 10 are unmet. CI gates drift, not tier.
- `item10.inventory.json`: item 10 (repo hygiene) attestation inventory. It lists
  only files that exist today. Add `verification/` CI here when #4 lands.
- `item10.attestation.json`: tool-produced envelope from
  `klt signoff --attest 10`. The grade rests on file presence plus one command
  check (no placeholder scripts in `package.json`); it does not show that every
  result is reproducible from the README.
- `design-evidence-tiers.md`: the checklist the grader parses, vendored
  byte-identical from `2AMLogic/klayout-tools` tag
  `v0.8.0` (commit `c572046be644`, git blob `2f7f69825f8c93d13237dce6df9ac6c122ddd6ac`,
  unchanged from the previous vendored copy). Upstream is MIT-licensed.
  Re-vendor from a named tag when upstream moves.
- `check-signoff.sh`: what CI and `npm run check:ci` run. It fails if `klt` is
  missing or a record has drifted.

## klt pin

`klayout-tools==0.8.0` from PyPI (`klt 0.8.0`). The same pin is in
`.github/workflows/signoff.yml` and `scripts/setup-env.sh`; CI fails if
`klt --version` does not print `klt 0.8.0`.

## Regenerate (same PR as any change to a cited file, the manifest or the checklist)

```sh
K="klayout-tools==0.8.0"
uvx --from "$K" klt signoff --attest 10 --inventory manifests/item10.inventory.json \
    -o manifests/item10.attestation.json
# if the inventory changed, copy provenance.input.content_hash of the envelope
# into evidence.10.content_hash in sky130-adpll.json, then:
uvx --from "$K" klt signoff --manifest manifests/sky130-adpll.json \
    --tiers-doc manifests/design-evidence-tiers.md --format json \
    > manifests/sky130-adpll.signoff.json   # exit 3 = some item unmet; expected
sh manifests/check-signoff.sh
```

CI uses `--check` rather than a byte compare: it ignores the report's `build`
block and the checklist's wording (reported as `doc_drift`), which move
without any verdict moving.
