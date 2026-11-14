# Block manifest and tier-verdict record

`klt signoff` input and committed output for T1 of
[`klayout-tools` `docs/design-evidence-tiers.md`](https://github.com/2AMLogic/klayout-tools/blob/v0.8.0/docs/design-evidence-tiers.md).
The committed record is the verdict of record; it is graded, not hand-read.

## Files

- `sky130-adpll.json`: block manifest (`block: sky130-adpll`, `kind: digital`).
  It cites items 1, 9 and 10; every other item stays uncited until its evidence lands.
- `sky130-adpll.signoff.json`: tool-produced verdict of record (`--format json`).
  All items except 1, 9 and 10 are unmet. CI gates drift, not tier.
- `item1.inventory.json`: item 1 (design sources) attestation inventory. It lists
  the RTL under `rtl/`, `design/dco.v` (structural, cells only), the
  `flow/adpll/synthesize.json` request, and the synthesized netlist
  `flow/adpll/records/adpll_top_synth.v` as the derived artifact.
- `item1.attestation.json`: tool-produced envelope from `klt signoff --attest 1`.
  The grade rests on file presence plus a freshness check of the derived netlist
  (`klt synthesize --check`, cheap mode: re-hash the request sources and
  liberty). That check is `local_only`: it needs the sky130 PDK, so CI skips it
  and carries the committed outcome; re-run it locally when you regenerate. It
  attests design sources and a pre-layout synthesized netlist only. It does not
  claim DCO frequency, tuning, timing or any post-layout behaviour, and the phase
  detector is not inventoried (its choice waits on decision 0002).
- `item9.inventory.json`: item 9 (testbenches shipped) attestation inventory. It
  lists the five RTL cocotb suites, the runner/checker and `sim/pdk-smoke/`, the
  cold-start command, and the PDK revision and tool versions. DCO and TDC benches
  are not in it (#51, #52); regenerate when they land.
- `item9.attestation.json`: tool-produced envelope from `klt signoff --attest 9`.
  The cold start is `local_only` (needs iverilog/verilator), so CI skips it and
  carries the committed outcome; re-run it locally when you regenerate. It
  attests that the listed benches exist and run, with pins recorded. Results are
  simulated, none measured.
- `item10.inventory.json`: item 10 (repo hygiene) attestation inventory. It lists
  the README, the licence, both CI workflows (`ci.yml`, `signoff.yml`) and
  `check-signoff.sh`. The verification suite's own files are item 9's inventory,
  not this one.
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
PDK=sky130A PDK_ROOT=$HOME/.ciel uvx --from "$K" klt signoff --attest 1 \
    --inventory manifests/item1.inventory.json -o manifests/item1.attestation.json
uvx --from "$K" klt signoff --attest 9 --inventory manifests/item9.inventory.json \
    -o manifests/item9.attestation.json
uvx --from "$K" klt signoff --attest 10 --inventory manifests/item10.inventory.json \
    -o manifests/item10.attestation.json
# if the inventory changed, copy provenance.input.content_hash of the envelope
# into evidence.<item>.content_hash in sky130-adpll.json, then:
uvx --from "$K" klt signoff --manifest manifests/sky130-adpll.json \
    --tiers-doc manifests/design-evidence-tiers.md --format json \
    > manifests/sky130-adpll.signoff.json   # exit 3 = some item unmet; expected
sh manifests/check-signoff.sh
```

CI uses `--check` rather than a byte compare: it ignores the report's `build`
block and the checklist's wording (reported as `doc_drift`), which move
without any verdict moving.
