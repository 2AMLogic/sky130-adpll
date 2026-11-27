# 0003 — Spec ratification: the scope proposed for operator approval

- **Status: Proposed.** Not ratified. Only the operator ratifies; an agent
  must not change this line to Ratified.
- Issue: #19 (child of #2). Spec tracker: #2 (an issue, not a PR).
- Authorization: operator ruling on #2, 2026-10-24, attended fleet:decide
  round 20261024-r1, Q10 option 1 — open the ratification PR; the operator
  ratifies, agents do not.
- Records in scope, as of `ba95b1c` (2026-11-22): [`../spec.md`](../spec.md),
  [`0001-target-spec.md`](0001-target-spec.md),
  [`0002-phase-detector-comparison.md`](0002-phase-detector-comparison.md),
  [`../placement-constraints.md`](../placement-constraints.md).
- **Unchanged by this record:** every spec number, every `Status: Proposed`
  line in the records above, and the README draft status. No simulation was
  run to write it.

## Context

0001 proposed the target spec and asked the operator to confirm or choose the
phase detector. The operator asked for an evidence-led comparison first; 0002
delivered it and recommends that neither detector be ratified on the present
evidence. Verification cannot record a graded result against a draft, so the
numeric and architecture targets that do not depend on that choice need the
operator's approval now. This record names exactly what is put to the
operator, so that one approval is one auditable act. It restates no number
and alters none: the values are those of the records named above, at the
commit named above.

## 1. Scope proposed for ratification

Two groups. Group A is put forward for ratification as written. Group B is
the phase-detector fork, where the operator chooses (§2).

### A. Numeric and architecture targets outside the phase-detector fork

| Record | What is put forward |
|---|---|
| `spec/spec.md` corner sets | **C27**, **C27+skew**, **C5** and their uses, as defined there |
| `spec/spec.md` rows | `1` output frequency (Target); `1f` output frequency (Fallback); `1s` output frequency (Stretch); `2` DCO tuning range; `3` DCO frequency resolution (fine LSB, after dither); `4` reference input frequency; `5` multiplication N (integer-N, Target); `5f` multiplication (Fallback); `5s` multiplication (Stretch); `7` loop bandwidth; `8` loop filter; `10` lock time; `11` period jitter (rms); `11l` long-term jitter (informational); `12` supply; `13` power; `14` implementation; `15` signoff |
| `spec/spec.md` jitter method | The whole "Jitter method" section as written: basis, simulator and noise, run length, seeds, estimator, convergence check, supply noise |
| `spec/spec.md` open items | O1–O7 preserved as explicit gates (table below) |
| `0001-target-spec.md` decisions | 1 library and supply; 2 DCO structure; 4 loop; 5 jitter method; 6 placement |
| `placement-constraints.md` | The DCO/TDC placement-constraint approach; the "Check, not trust" verification (a result whose placement check is missing or failed is not recorded); the extraction hand-off (O7) |

| Open item | Question it leaves open |
|---|---|
| O1 | Which PDK corner files implement C27 / C27+skew for `sky130_fd_sc_hd` |
| O2 | Whether a ≈170-tap delay line is affordable in the power budget and area *(phase-detector-coupled; §2)* |
| O3 | DCO tuning range and fine LSB actually achieved at each corner |
| O4 | PI gains and word widths |
| O5 | Calibration of equivalent noise injection to device thermal noise |
| O6 | Pinned harness reference from a sibling |
| O7 | Path from extracted placed-block parasitics into ngspice |

Ratifying O1–O7 as gates confirms each as an open item that only its named
measurement closes. It settles none of them and authorizes no number.

### B. Phase-detector-coupled rows

These are written in multi-bit TDC terms and wait on the operator's choice in
§2; group A does not ratify them.

| Item | Why it is coupled |
|---|---|
| `spec/spec.md` row `6` | Phase detector: names the multi-bit TDC |
| `spec/spec.md` row `6a` | TDC resolution: one delay-line LSB |
| `spec/spec.md` row `6b` | TDC range: delay-line length |
| `spec/spec.md` row `8a` | Word widths: the 9-bit signed phase error assumes a multi-bit detector |
| `spec/spec.md` row `9` | Lock definition: written in TDC LSBs |
| Open item O2 | The delay line's cost against rows 13 and 6b |
| `0001-target-spec.md` decision 3 | Phase detector: multi-bit TDC |

Rows 11 and 13 do not change with the choice; they are the criteria the
choice is graded against (0002 §1, C1 and C2).

## 2. The phase-detector fork: the operator's choice

**What 0002 §6–7 recommends.** Do not ratify either detector on the present
evidence: jitter and power rank first in the criteria and are gaps for both
alternatives. Carry the multi-bit TDC as the working baseline, explicitly as a
placeholder and not as a result of the comparison. Authorize the bounded
validation plan so that the choice is made on measured numbers. The decision
rule is stated in advance (0002 §6, rule 3): keep the TDC if the extrapolated
block stays within row 13 at every C27 corner with LSB within row 6a's limit;
otherwise propose the bang-bang detector as a spec change if its behavioural
model meets row 11 with margin; otherwise ask the operator to relax a tier.
Agents do not relax the spec.

**The plan and its cap (0002 §7).**

| Step | Work |
|---|---|
| V0 | Resolve O1: list the PDK corner files |
| V1 | One `hd` delay tap and a 16-tap segment, extracted, SPICE over C27+skew: per-tap delay and power, LSB spread, extrapolation to O2 |
| V2 | Hybrid (coarse counter + short line) estimate from V1 |
| V3 | Behavioural loop model, bang-bang vs TDC, parameterised with V1 and O3 |
| V4 | Excluded: ngspice transient-noise confirmation needs its own estimate and approval |

Cap: V0–V3 only — at most one corner grid of V1 (`klt sim` corners request on
the batch fleet) and zero transient-noise campaigns.

**The options.**

- **A — adopt 0002 §6–7 as written (the recommendation).** Group A is
  ratified. Rows 6, 6a, 6b, 8a, 9, O2 and 0001 decision 3 stay **Proposed** as
  the placeholder baseline. V0–V3 are authorized within the cap. The detector
  is chosen later, on measured numbers, by a new decision record and the
  operator.
- **B1 — choose the multi-bit TDC now.** Group A plus rows 6, 6a, 6b, 8a, 9
  and 0001 decision 3, ratified as written. O2 stays open as the risk to
  row 13.
- **B2 — choose the bang-bang detector now.** A spec change this record
  cannot encode, because the replacement values do not exist. Per 0002 §3:
  row 6 rewritten; rows 6a and 6b no longer apply; row 8a's 9-bit phase error
  and row 9's lock-in-TDC-LSBs rewritten; 0001 decision 3 rewritten to select
  the bang-bang detector; O2 (the delay line) no longer applies; the 2-bit
  sigma-delta dither of 0001 decision 2 re-examined. It needs a new decision
  record carrying those values before anything is ratified.

**Recording the choice.** The operator names the option in the ratification
comment on this PR. As written, this record is option A. B1 or B2 is a request
to amend it first — B2 through a new decision record carrying the replacement
rows — so that the text approved and the text merged are the same. Silence on
the fork approves option A only: B1 and B2 cannot happen by silence, because
both change what rows 6, 6a, 6b, 8a and 9 mean.

## 3. What this ratification does not do

- Settles no open item: O1–O7 stay open until the measurement named for each
  is recorded.
- Runs nothing: under option A, V0–V3 are authorized, not run; V4 stays
  excluded.
- Ratifies no detector on the present evidence (option A).
- Changes no numeric target.
- Flips no `Status` line and removes no README draft marker: after the
  operator's approval, those are updated on the operator's instruction, and #2
  keeps that sign-off.

## 4. Ratification

**This record is ratified only on human merge approval by the operator;
merging this PR ratifies the named scope above.**

Two independent key reviews, EE and market, precede that approval and are
posted on this PR by review sessions other than the one that wrote this
record. No agent ratifies, and no agent merge substitutes for the operator's
approval. Once ratified, a change to any row, decision or open item named
here needs a new decision record (0001, Consequences).

## 5. Downstream

Parked on #19 and released by the operator's ruling, each per its own park
record:

- #29 (T1 item 2, layout) — waits on `placement-constraints.md` (§1 A) and on
  the phase-detector choice (§2).
- #52 (TDC cell-level SPICE benches for rows 6a and 6b) — waits on the
  phase-detector choice (§2); its own scope closes it as not planned under
  B2.
- #30, #31, #33 — transitively behind #29.

## 6. Validation of this record (what a reviewer should check)

- The four records and `README.md` are unchanged since `ba95b1c`:
  `git diff --stat ba95b1c HEAD -- spec/spec.md
  spec/decisions/0001-target-spec.md
  spec/decisions/0002-phase-detector-comparison.md spec/placement-constraints.md
  README.md` prints nothing.
- Every row ID of `spec/spec.md` is in §1: the 23 IDs `1, 1f, 1s, 2, 3, 4, 5,
  5f, 5s, 6, 6a, 6b, 7, 8, 8a, 9, 10, 11, 11l, 12, 13, 14, 15`; every decision
  of 0001 (1–6); every open item (O1–O7).
- The summary of 0002 §6–7 matches that record, and the cap is not enlarged.
