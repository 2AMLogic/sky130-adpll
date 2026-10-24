# 0002 — Phase detector comparison: multi-bit TDC vs bang-bang

- **Status: Proposed.** Prepares the choice; does not make it. Neither detector
  is ratified. Only the operator ratifies; an agent must not change this line.
- Issue: #20 (child of #2). Ratification tracker: #19 (an issue, not a PR).
- Authorization: operator ruling on #2, 2026-10-19, option 1 of revision 2
  ("evidence-led comparison, prepared before choosing").
- Spec: [`../spec.md`](../spec.md) rows 6, 6a, 6b, 13 and open item O2.
  [`0001-target-spec.md`](0001-target-spec.md) decision 3.
- **Unchanged by this record:** every spec number, `spec/spec.md`, the README
  draft status, and the status of #2. No simulation was run to write it.

## How to read the evidence

Every claim below is one of: **[S]** traced to a cited source, **[D]** derived
by arithmetic from a spec row (shown), **[A]** an assumption of this record, or
**GAP** (not answerable from the sources consulted; named, not guessed).
Cited designs are other people's silicon on other processes; none is a
capability demonstrated here.

**Source verification status.** Bibliographic details of S2, S3, S3b and S5 were
checked against index records (IEEE Xplore / publisher / institutional listings) on
2026-10-24; only abstracts and records were read, **not full texts**. Any
figure that would need a full-text read (for example a specific power or
jitter value of a cited design) is therefore *not* quoted and is listed as a
GAP. S1 is named from background knowledge and was **not**
re-verified in this pass; a reviewer must resolve it before relying on it
(see Validation of this record).

## 1. Selection criteria (derived from the use case, before scoring)

Use case, from the README/spec: a synthesizable all-digital PLL, standard
cells only, `sky130_fd_sc_hd`, 1.8 V ±10 %, −40..+125 °C, 200 MHz integer-N
from 10–50 MHz reference, whole block ≤ 2 mW, period jitter ≤ 1 % of period,
lock ≤ 20 µs, graded post-layout over C27, and — because the repo is a
canary for the open flow — the result must be reproducible through
Yosys/OpenROAD/`klt` without hand-drawn cells.

Criteria, in priority order, with the reason each ranks where it does:

| # | Criterion | Why it ranks here |
|---|---|---|
| C1 | Closes the loop-level jitter target (row 11) with margin at all C27 corners | It is a graded pass/fail row; failure invalidates the block |
| C2 | Fits the whole-block power budget (row 13) | Second hard row; DCO power is not negotiable, so the detector competes for the remainder |
| C3 | Implementable from standard cells and constrainable in placement (rows 14, 15) | The block's definition; a detector that cannot be placed repeatably breaks the premise |
| C4 | Verifiability: its behaviour can be measured by the sim budget available (ngspice, no PNOISE) | "No claim without a testbench"; a detector whose key behaviour needs periodic-noise analysis is costlier to verify |
| C5 | Lock behaviour bounded: lock time (row 10) and lock definition (row 9) are demonstrable | Graded rows, and row 9 is currently written in TDC LSBs |
| C6 | Robustness to PVT and DCO gain spread | Spec corners are wide (SS/1.62 V/125 °C to FF/1.98 V/−40 °C) |
| C7 | Area | Secondary: no area row exists in the spec |
| C8 | Path to fractional-N (stretch) | Explicitly **not** a driver (CLAUDE.md); recorded for information only and given zero weight |

Rows 6a/6b/9 are written in TDC terms; choosing bang-bang would change them,
which is a spec change needing the operator (see §6).

## 2. Alternative A — multi-bit TDC (delay line of `hd` cells)

**Mechanism.** A chain of delay cells timestamps the reference edge against the
DCO edge; the position is a multi-bit phase error feeding a linear PI filter.
Resolution is one cell delay; range is the chain length. [S1] demonstrates this
class in an all-digital PLL for a mobile transmitter, and [S2] a 90 nm TDC whose
resolution step is one inverter delay, with self-calibration and measured INL
reported in the abstract (the specific numbers are in S2 and were not
full-text verified; GAP for quoting). Both are 90 nm, not sky130.

**Strengths.**
- Linear regime: a quantised-phase PI loop has a conventional linear model
  (spec O4 already assumes one); gain is set by the LSB, which is a physical
  property of the cell, not of the noise. [S1][S2] [A for transfer to sky130]
- Quantisation noise is bounded by the LSB (≤ 40 ps typ in row 6a), well below
  the 50 ps rms jitter budget *if* the LSB holds across corners. [D]
- Lock definition (row 9) is already expressed against it.

**Costs and risks.**
- **Range/area/power (the O2 question).** Row 6b asks for ≥ 1 DCO period at the
  slowest corner: 1 / 150 MHz = 6.67 ns. At 40 ps/tap that is
  6.67 ns / 40 ps ≈ 167 taps; at the 60 ps max in row 6a ≈ 111 taps. [D]
  Power per tap at sky130 `hd` and the toggle rate are not in the spec and not
  established by the sources consulted: **GAP**. See §4.
- LSB varies with PVT. In `sky130_fd_sc_hd` the spread of a nominal cell delay
  across C27+skew is expected to be large (order of 2–3× between SS/1.62 V/125 °C
  and FF/1.98 V/−40 °C) [A, unquantified; must be measured — spec 6a]. A fixed
  40 ps typ does not imply ≤ 60 ps at SS; calibration (as in S2) or a
  coarse counter may be required. GAP.
- Mismatch/INL of a standard-cell chain is placement- and routing-dependent;
  needs explicit placement constraints (`placement-constraints.md`). [A]
- Metastability at the capture flops at chain end: the spec does not yet state
  a resolution policy. GAP.

## 3. Alternative B — bang-bang phase detector (Alexander / early-late)

**Mechanism.** A single flop (plus the sign output) reports only early/late.
The loop is nonlinear (a hard limiter); its steady state is a limit cycle.
[S3] derives, for first- and second-order digital bang-bang PLLs, conditions
for limit-cycle existence and evaluates the resulting timing jitter, with
emphasis on loop delay (abstract-level; equations not full-text verified).

**Strengths.**
- Detector is one flop plus an early/late decision: area and detector power are
  a small fraction of a 167-tap line. [A: not quantified for sky130; the
  qualitative direction is not in dispute, the magnitude is a GAP]
- No resolution/range tradeoff, no delay-line calibration, little placement
  sensitivity in the detector itself.
- Gain does not depend on a cell-delay LSB.

**Costs and risks (assessed, not dismissed).**
- **Jitter is set by the nonlinearity.** The limit-cycle amplitude depends on
  the proportional step, the loop delay, and the input jitter [S3]. The DCO
  ring's own accumulated jitter [S5] adds to it. Whether the 1 % (50 ps rms
  at 200 MHz) is met is therefore an *interaction* of ring noise, DCO fine-LSB
  (row 3: 0.05 % of f typ ≈ 100 kHz at 200 MHz), digital loop delay and
  proportional gain. Not answerable from sources alone: **GAP**, closed only by
  a behavioural + transient-noise model.
- **Effective gain is amplitude-dependent**, so the loop's closed-loop
  bandwidth (row 7) and jitter transfer depend on input jitter; a linearised
  analysis has validity limits [S3b, record verified only]. A PVT-wide
  guarantee of lock time (row 10) needs simulation over C27, not a formula.
- Dithering/limit cycles interact with the DCO's 2-bit sigma-delta dither
  (decision 2 in 0001); a bang-bang loop would need that dither re-examined.
  GAP.
- Rows 6a, 6b, 8a (9-bit phase error) and 9 (lock in TDC LSBs) all assume a
  multi-bit detector and would be rewritten. Spec change.
- Verification cost: jitter figures need a long transient-noise campaign
  (≥ 2000 periods × ≥ 16 seeds × 27+ corners per spec) because the limit
  cycle is a nonlinear, noise-driven quantity; no periodic-noise analysis
  exists in ngspice. [D from the Jitter method section]

## 4. The O2 question: ≈ 170 taps in 2 mW

Answer status: **GAP — not answerable from the sources consulted.**

What is established: the tap count follows from the spec ([D], §2), 167 at
40 ps and 111 at 60 ps. What is not: (a) dynamic power per `hd` tap at the
operating toggle rate, (b) the leakage at 125 °C/FF/1.98 V, (c) the fraction of
2 mW left after the DCO. None of the consulted abstracts gives sky130 figures.

Ways the question could be reduced without simulating a full chain (all are
*proposals*, in §7):
- The delay line does not need to toggle every cycle at 200 MHz; the reference
  edge (≤ 50 MHz) launches the transition, so activity is bounded by the
  reference rate rather than the DCO rate. [A — depends on the chosen
  architecture; must be confirmed against the actual TDC schematic]
- A coarse counter + short fine line (hybrid) reduces taps to roughly
  (range of the fine line) / LSB. Spec 6b allows revisiting range per O2.
  Hybrid is *consistent with* "standard cells only".

## 5. Open-question ledger (from #2 / #20)

| Question | Status | Where |
|---|---|---|
| Taps vs power (≈ 170 at 2 mW) | **GAP**; tap count derived, power unknown | §4 |
| Jitter (TDC) | Quantisation term bounded by LSB [D]; total GAP until simulated | §2 |
| Jitter (bang-bang) | Mechanism answered [S3]; value GAP | §3 |
| Lock behaviour (TDC) | Linear model available [S1,S2]; row 9/10 values GAP | §2 |
| Lock behaviour (bang-bang) | Limit-cycle theory [S3]; PVT-wide lock time GAP | §3 |
| Standard-cell feasibility | Both feasible in principle; TDC placement sensitivity and metastability GAP | §2, §3 |
| PVT/model limits | Delay spread across C27+skew unquantified; sky130 liberty/SPICE gate-delay accuracy for sub-ns chains unknown (relates O1) GAP | §2 |
| Model limits (ngspice) | No PNOISE; transient noise calibration open (O5); GAP | spec |

Total: of eight rows, two are answered at mechanism level from sources, six
are named gaps. That is the honest state of the evidence; the sources
consulted do not support a quantitative choice.

## 6. Recommendation

**Do not ratify either detector on the present evidence.** The criteria in §1
rank jitter and power first, and both are exactly the quantities that are
gaps for *both* alternatives. A recommendation that follows from the criteria
is therefore conditional:

1. **Carry the multi-bit TDC as the working baseline** (it is what spec rows
   6/6a/6b/8a/9 and decision 3 already assume, so keeping it avoids a spec
   rewrite while evidence is collected), explicitly as a *placeholder*, not as
   a result of this comparison.
2. **Authorise the bounded validation plan (§7) so the choice is made on
   measured numbers**, specifically the two that discriminate:
   per-tap power and LSB spread (decides the TDC against C2/C6), and the
   bang-bang jitter in a behavioural loop model with measured DCO LSB and
   ring noise (decides the alternative against C1).
3. **Decision rule, stated now so results cannot move it:** if the extrapolated
   TDC (hybrid allowed) leaves the whole block ≤ 2 mW at every C27 corner with
   LSB ≤ 60 ps, keep the TDC; else if the bang-bang behavioural model meets
   row 11 with ≥ 20 % margin, propose the bang-bang as a spec change for the
   operator; else neither fits and the operator is asked to relax a tier
   (Fallback is already defined). Agents do not relax the spec themselves.

C8 (fractional-N) was given no weight, per CLAUDE.md.

## 7. Bounded validation plan (written, **not run, not authorised**)

Nothing here may start without operator approval of #2/#19. Estimates are
planning figures [A], not measurements.

| Step | Work | Output | Est. compute | Est. agent effort |
|---|---|---|---|---|
| V0 | Resolve spec O1 (list PDK corner files) | O1 mapping | negligible | small |
| V1 | One `hd` delay tap + 16-tap segment, extracted, SPICE over C27+skew; delay and dynamic/leakage power vs corner | per-tap delay and power; LSB spread (6a); extrapolation to O2 | ~27–54 single-corner runs, seconds–minutes each; a `klt sim` corner grid request, not a hand loop | 1 sweep |
| V2 | Hybrid (coarse counter + short line) area/power estimate from V1 | tap count vs power table | none beyond V1 | small |
| V3 | Behavioural loop model of bang-bang vs TDC (spec O4 model), parameterised with V1 LSB spread and DCO LSB from O3 | jitter and lock-time comparison, pre-layout, labelled as such | MATLAB/Python-class model, minutes | 1–2 sweeps |
| V4 | (only if V3 is close) ngspice transient-noise confirmation of the surviving candidate, method per spec "Jitter method" | graded jitter, post-layout | the large item: ≥ 16 seeds × ≥ 2000 periods × corners via batch fleet | separate approval |

**Cap.** V0–V3 only: at most one corner grid of V1 on the batch fleet
(`klt sim` corners request), and zero transient-noise campaigns. V4 is
**excluded from this plan** and needs its own estimate and approval. No step
is authorised by this record.

## 8. Validation of this record (what a reviewer should check)

- Resolve S1 (not re-verified): give full citation or drop it.
- Confirm arithmetic: 1/150 MHz = 6.67 ns; /40 ps = 167; /60 ps = 111.
- Confirm no row of `spec.md` or the README changed (`git diff --stat`).

## References

- [S1] R. B. Staszewski et al., all-digital PLL for a mobile transmitter
  (TDC-based ADPLL, 90 nm). Named from background knowledge; **not
  re-verified** in this pass.
- [S2] R. B. Staszewski et al., "1.3 V 20 ps time-to-digital converter for
  frequency synthesis in 90-nm CMOS," IEEE TCAS-II, vol. 53, no. 3,
  pp. 220–224, 2006, DOI 10.1109/TCSII.2005.858754. Record verified; abstract
  only.
- [S3] N. Da Dalt, "A design-oriented study of the nonlinear dynamics of
  digital bang-bang PLLs," IEEE TCAS-I, vol. 52, no. 1, pp. 21–31, Jan. 2005.
  Record verified; abstract only.
- [S3b] N. Da Dalt, "Linearized analysis of a digital bang-bang PLL and its
  validity limits applied to jitter transfer and jitter generation," IEEE
  TCAS-I, vol. 55, no. 11, 2008. Record verified.
- [S5] A. Hajimiri, S. Limotyrakis, T. H. Lee, "Jitter and phase noise in ring
  oscillators," IEEE JSSC, vol. 34, no. 6, pp. 790–804, June 1999. Record
  verified (https://ieeexplore.ieee.org/document/766813); abstract only.
