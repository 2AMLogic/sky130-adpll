# Roadmap

sky130-adpll is a standard-cell-only all-digital PLL on SkyWater sky130 (DCO,
phase detector, digital PI loop filter, divider, lock detect), built to push
the open digital flow through placement-dependent timing.

Status as of 2026-11-13, `main` @ `f14d440`.

[`WORK_PLAN.md`](WORK_PLAN.md) is the machine-generated view of label state;
this file is the plan behind it. The gap tracker is #6 (checklist text dated
2026-10-17); the verdict of record is `manifests/sky130-adpll.signoff.json`.

## Where it stands

On the README's ladder (spec ratified → loop modelled and RTL verified → DCO
and TDC characterized post-layout → … → measured silicon) the block is still
before the first rung: the spec is **Proposed**, not ratified. The README's
own status line ("Nothing is designed yet") is stale against the tree; see Now.

Done and evidenced on `main`:

- **Spec proposed** (#9): `spec/spec.md` (parameter table, corner sets C27 /
  C27+skew / C5, jitter method, open items O1–O7),
  `spec/placement-constraints.md`, decision record `0001` (Proposed).
- **Phase-detector comparison prepared** (#22, #26): decision record `0002`
  (Proposed). It recommends ratifying neither detector on present evidence,
  carries the multi-bit TDC as a placeholder baseline, and states a decision
  rule and a bounded validation plan (V0–V3) that is written but not authorised.
- **Digital RTL** (#34): loop filter, divider, lock detect, DCO code path and
  `adpll_top` under `rtl/`, with the phase detector left as a port boundary
  (`fb_clk`, `pd_err`, `pd_valid`). Five cocotb suites, each with a negative
  control, run in CI (`verification/`, `.github/workflows/ci.yml`).
- **DCO structural netlist** (#48): `design/dco.v`, library cells only,
  provisional until cell SPICE (O3).
- **Synthesized netlist** (#49): `flow/adpll/records/adpll_top_synth.v`, 579
  `sky130_fd_sc_hd` leaf cells, byte-reproducible from `flow/adpll/synthesize.json`.
- **Pinned environment and smoke runs** (#10): `flow/smoke/`, `sim/pdk-smoke/`.

T1 checklist (`klt signoff`, 3 of 11 met):

| Item | State | Evidence or gap |
|---|---|---|
| 1 Design sources | met | `manifests/item1.attestation.json` (#50); phase detector not inventoried |
| 2 Layout | unmet | #29; no DCO or phase detector in the top-level netlist yet |
| 3 DRC clean | unmet | #30, needs item 2 |
| 4 LVS clean | unmet | #31, needs items 1 and 2 |
| 5 Corner verification vs a ratified spec | unmet | no issue; needs a ratified spec (#2) |
| 6 Monte Carlo for statistical claims | unmet | no issue; spec must say which rows are statistical |
| 7 Post-layout verification | unmet | no issue; needs items 2 and 5 and the O7 extraction path |
| 8 Characterization report | unmet | no issue; needs items 5–7 |
| 9 Testbenches shipped | met | `manifests/item9.attestation.json` (#53); DCO and TDC benches not in it (#51, #52) |
| 10 Repo hygiene | met | `manifests/item10.attestation.json`; inventory predates the verification CI job |
| 11 Power delivery | unmet | #33, needs items 2 and 4 |

## Now

Each fits one PR, needs no ratification and changes no spec number.

1. **Land the reviewer trees** (#18, PR #21). In flight: PR #21 has been
   awaiting review since 2026-10-24 with CI green. Done when it merges with #2
   still open; a triage comment on the PR warns that its body currently
   auto-closes #2 and must be reworded first.
2. **Bring the README status in line with the tree** (no issue; seed 1). Done
   when the status line and "Current position" name what is actually on `main`
   (proposed spec, RTL, synthesized netlist, 3 of 11 T1 items), the repo
   layout lists `flow/`, `manifests/` and `scripts/`, and the target table
   keeps its DRAFT marker.
3. **Refresh the item-10 inventory** (no issue; seed 2). Its description still
   says the verification CI "is added when #4 lands"; #4 closed on 2026-10-17
   and `.github/workflows/ci.yml` exists. Done when the inventory lists it,
   the attestation and signoff record are regenerated, and
   `manifests/check-signoff.sh` passes.
4. **Remove the 64 dangling tie cells from the loop filter** (no issue; seed
   3). `flow/adpll/README.md` records 64 `conb_1` cells driving `imin_x` /
   `imax_x`. Done when the regenerated netlist has none from that source, the
   suites still pass, and the item-1 attestation is regenerated.
5. **Exercise the gate-level re-run slot on the real netlist** (no issue; seed
   4). `verification/gate-level/README.md` still says no netlist exists. Done
   when a committed script runs the `top` suite on
   `flow/adpll/records/adpll_top_synth.v` with `--level gate`, the smoke test
   passes and the negative control fails, and the cell-model source list is
   committed.

## Next

- **DCO cell SPICE benches and O1** (#51, parked). Partial work is on branch
  `feature/issue-51`: the bench, a 225-unit request, and the O1 corner
  mapping. The batch grid timed out, so there is no `records.json`. Unblocked
  by re-scoping the grid (fewer code points or a shorter run); done when `sim/dco/records.json` holds row 2 and row 3 numbers at every
  C27+skew corner, labelled pre-layout. The one local probe on that branch put
  the provisional ring near 1 GHz at one corner, so expect a follow-up on the
  ring in `design/dco.v` against row 2.
- **Open the ratification PR** (#19). Blocked by #18. Done when a PR names the
  exact records and rows to ratify, links #2, and carries both key reviews.
- **Phase-detector netlist and RTL.** Unblocked by ratification of decision
  0002 (#19 → #2). Done when the detector is instantiated behind
  `adpll_top`'s `pd_err` / `pd_valid` boundary and inventoried in item 1.
- **TDC cell benches** (#52). Blocked by #19; closes as not planned if 0002
  selects bang-bang.
- **Placed-and-routed GDS with DCO/TDC regions** (#29, item 2). Blocked by
  the phase-detector netlist. Its builder note of 2026-11-05 reports the
  placement-region gap, 2AMLogic/klayout-tools#4804, closed upstream but not
  yet exercised here; re-check it against the pinned `klt` first.
- **DRC, LVS, power delivery** (#30, #31, #33; items 3, 4, 11): after #29.

## Later

- **Behavioural loop model (O4, step V3 of decision 0002).** First question:
  is the validation plan authorised, and what DCO LSB (O3) and tap spread feed it?
- **Extraction hand-off into ngspice (O7).** First question: which route
  (SPEF from OpenROAD, or layout extraction through `klt`) survives the
  small-ring round trip that `spec/placement-constraints.md` requires?
- **Jitter evidence (rows 11, 11l; O5).** First question: how is the
  equivalent noise injection calibrated to device thermal noise?
- **Items 5–8.** First question: which spec rows are statistical (item 6)?
  None of these has an issue, and none should be filed before the spec is ratified.

## Blocked and waiting

- **Spec ratification** (#2, `loom:operator`). Only the operator ratifies.
  Items 2–8 and 11 all trace back to it, through #19 and decision 0002.
- **Decision 0002's validation plan.** Its §7 says nothing in it may start
  without approval; #51 (parked on batch timeouts) overlaps steps V0 and V1.
- Every open implementation issue carries `loom:blocked`, and no issue carries
  `loom:issue`. Until the Now items above are filed, the tracker has nothing
  an agent can draw.

## Not planned

- The reference oscillator, any analog loop element, any hand-drawn cell.
- Fractional-N and 400 MHz before integer-N closes; they are stretches.
- Relaxing a Proposed or ratified number to make a result pass.
