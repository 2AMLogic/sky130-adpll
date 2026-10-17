# 0001 — Target specification

- **Status: Proposed.** Not ratified. Only the operator ratifies; an agent
  must not change this line to Ratified.
- Issue: #2
- Spec: [`../spec.md`](../spec.md)

## Context

The README target table is a proposal. Verification needs a fixed spec, a
fixed corner set and a fixed jitter method before any result is recorded.

## Decisions requested

1. **Library and supply.** `sky130_fd_sc_hd`, 1.8 V ±10 %, −40 to +125 °C,
   corner set C27 (C27+skew for cell-level SPICE).
   *Rejected:* `hdll`/`ms`/`ls` flavors — no benefit that justifies leaving
   the best-supported flavor in the open flow; a narrower corner set — nothing
   in the issue argues for one.
2. **DCO structure.** A ring of an odd number of inverting `hd` stages with
   coarse tuning by selecting the stage count (tap mux) and fine tuning by
   enabling banks of parallel tri-state drivers (`ebufn`) on the ring nodes,
   with a 2-bit sigma-delta dither on the lowest bits.
   *Rejected:* tri-state banks only (coarse range too small to cover the
   process spread); switched shunt-capacitor loads (needs pass gates or custom
   cells, which breaks "standard cells only"); a delay-line / digitally
   controlled delay element fed back as a ring (equivalent in principle,
   but the stage-count + drive-bank form is simpler to place and constrain).
   Frequency resolution at each corner is a measurement, not a claim (spec O3).
3. **Phase detector: multi-bit TDC** (delay line of `hd` cells), 40 ps typ
   resolution, range of one DCO period.
   *Rejected:* bang-bang detector — smaller and cheaper, but its limit-cycle
   dither sets period jitter directly against the 1 % target and lock-time
   behaviour is harder to bound; revisit if spec O2 shows the TDC delay line
   does not fit the 2 mW budget. **This is the real fork in the spec**; the
   operator is asked to confirm or choose the bang-bang alternative.
4. **Loop.** Digital PI with power-of-two gains, bandwidth fref/50 typ
   (fref/100 to fref/20), integer-N first; fractional-N is a stretch and does
   not influence the architecture until integer-N closes.
5. **Jitter method.** ngspice transient noise, post-layout graded, ≥ 2000
   periods, ≥ 16 seeds, edge-crossing estimator — full text in the spec.
   *Rejected:* a jitter number from static timing or a pre-layout netlist;
   a periodic-noise analysis (not available in ngspice).
6. **Placement.** Constrained and checked as in
   [`../placement-constraints.md`](../placement-constraints.md).

## Open items

Spec O1–O7. Where a choice needed a measurement, no number was invented; the
measurement that settles it is named.

## Answers to the issue's open questions

| Question | Answer |
|---|---|
| DCO structure and resolution | Decision 2; resolution is open item O3 |
| Placement constraint via `klt`, checkable | `placement-constraints.md` |
| Extracted parasitics back into ngspice | `placement-constraints.md` § Extraction hand-off; open item O7 |
| Behavioural loop model | `verification/`: discrete-time linear model of TDC → PI → DCO (z-domain, with quantisation) for setting gains, cross-checked against RTL simulation lock time; sets spec O4 |
| Sibling harness | Open item O6, pinned via `reuse.lock.json` in #3 |

## Consequences

Once ratified, the README table matches `spec.md`, its DRAFT marker is
removed, and a change to any row needs a new decision record.
