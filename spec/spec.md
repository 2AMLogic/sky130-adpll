# Target specification — PROPOSED

Status: **Proposed** (decision record `decisions/0001-target-spec.md`). Agents
do not ratify this spec; the operator does. Every number below is a **design
target**, not a result. No row has been simulated or measured; each cites the
evidence that will grade it.

Tiers match the README table: **Target** = 200 MHz integer-N, **Fallback** =
100 MHz / 25 MHz fixed reference, **Stretch** = 400 MHz and fractional-N.
Integer-N must close before fractional-N influences the loop architecture.

## Corner sets

Library: `sky130_fd_sc_hd` (high-density, 1.8 V core). Supply 1.80 V ±10 %
(1.62 – 1.98 V). Temperature −40 °C to +125 °C. No narrower set is argued for.

| Set | Definition | Used for |
|---|---|---|
| **C27** | process {SS, TT, FF} × VDD {1.62, 1.80, 1.98} × T {−40, 25, 125} °C | every recorded, graded result |
| **C27+skew** | C27 plus SF and FS process at the same VDD/T grid | DCO and TDC cell-level SPICE (ring duty cycle and delay-line linearity depend on N/P skew) |
| **C5** | TT/1.80/25, SS/1.62/125, SS/1.62/−40, FF/1.98/−40, FF/1.98/125 | iteration smoke only; never a recorded result |

Mapping of these names to the liberty/SPICE corner files the installed PDK
actually ships is open item O1.

## Parameter table

"Corners" is the set the row is graded over. "—" in min or max means the row is
one-sided. Typ is graded at TT/1.80 V/25 °C unless the condition says otherwise.

| # | Parameter | Min | Typ | Max | Grading condition | Corners | Evidence |
|---|---|---|---|---|---|---|---|
| 1 | Output frequency (Target) | 200 MHz at every corner | 200 MHz | — | Locked, N set for 200 MHz | C27 | post-layout loop sim |
| 1f | Output frequency (Fallback) | 100 MHz at every corner | 100 MHz | — | fref = 25 MHz, N = 4 | C27 | post-layout loop sim |
| 1s | Output frequency (Stretch) | 400 MHz at every corner | 400 MHz | — | fref = 25 MHz or 50 MHz, N = 16 or 8 | C27 | post-layout loop sim |
| 2 | DCO tuning range | 150 MHz | — | ≥ 300 MHz | Open-loop sweep of full code; the range must contain 200 MHz with ≥ 20 % margin on both sides at every corner (so process spread cannot push the lock point to a code limit) | C27+skew | DCO cell SPICE, post-layout |
| 3 | DCO frequency resolution (fine LSB, after dither) | — | 0.05 % of f (100 kHz at 200 MHz) | 0.1 % of f | Mean frequency step between adjacent fine codes, measured over the whole fine range | C27+skew | DCO cell SPICE |
| 4 | Reference input frequency | 10 MHz | 25 MHz | 50 MHz | Reference is an ideal source at the block boundary, 50 % duty, ≤ 1 ps rms jitter | n/a (boundary) | testbench |
| 5 | Multiplication N (integer-N, Target) | 4 | 8 | 20 | N = fout / fref, integer, fout = 200 MHz | C27 | RTL + loop sim |
| 5f | Multiplication (Fallback) | fixed N = 4 | N = 4 | fixed N = 4 | fref = 25 MHz fixed | C27 | RTL + loop sim |
| 5s | Multiplication (Stretch) | integer 8 | — | fractional-N (sigma-delta, 1/2^k step) | Not designed until integer-N closes | C27 | — |
| 6 | Phase detector | — | multi-bit TDC (delay line of `hd` cells) | — | See decision record | — | — |
| 6a | TDC resolution (one LSB) | — | ≤ 40 ps | ≤ 60 ps | Mean per-tap delay under the extracted layout, with the DCO running | C27+skew | TDC cell SPICE, post-layout |
| 6b | TDC range | ≥ 1 DCO period at the slowest corner (see note) | 1 DCO period | — | Linear range, DNL ≤ 1 LSB | C27+skew | TDC cell SPICE, post-layout |
| 7 | Loop bandwidth | fref / 100 | fref / 50 | fref / 20 | Closed-loop −3 dB of the linearised model, then confirmed from step response | C27 | behavioural model, then loop sim |
| 8 | Loop filter | — | digital PI: proportional gain Kp = 2^-a, integral gain Ki = 2^-b, power-of-two shifts | — | Structure fixed; values set by the behavioural model | — | behavioural model |
| 8a | Word widths (initial) | — | phase error 9 b signed, integrator 24 b, DCO code 12 b (coarse 6 b + fine 6 b) + 2 b sigma-delta dither | — | Re-derived when O4 closes; any change is a spec change | — | behavioural model |
| 9 | Lock definition | — | \|phase error\| ≤ 4 TDC LSB for 64 consecutive reference cycles, and `lock` asserted | — | Starting from reset, DCO at mid-code | C27 | RTL sim, loop sim |
| 10 | Lock time | — | ≤ 20 µs | ≤ 20 µs (Fallback ≤ 100 µs, Stretch ≤ 5 µs) | Reset release to first `lock` assertion, worst case over fref 10–50 MHz and over starting code | C27 | RTL sim, loop sim |
| 11 | Period jitter (rms) | — | ≤ 1 % of output period (≤ 50 ps at 200 MHz) | ≤ 1 % at every corner (Fallback ≤ 2 %, Stretch ≤ 0.5 %) | Method in "Jitter method" below; post-layout only | C27 | post-layout transient noise |
| 11l | Long-term jitter (informational) | — | reported, not graded | — | Same method; 100-cycle accumulated jitter | C27 | post-layout transient noise |
| 12 | Supply | 1.62 V | 1.80 V | 1.98 V | Single 1.8 V core supply, `hd` cells only | C27 | — |
| 13 | Power | — | ≤ 2 mW | ≤ 2 mW (Fallback ≤ 5 mW, Stretch ≤ 1 mW) | Average supply current × VDD, locked at the tier's frequency, whole block (DCO + TDC + digital) | C27 | post-layout transient |
| 14 | Implementation | standard cells only, no custom analog | | | Netlist contains only library cells; a hand-drawn cell is a spec change | — | netlist audit |
| 15 | Signoff | DRC clean, LVS clean, STA and post-layout re-verified | | | Through `klt` | — | layout flow |

Note on 6b: range is stated relative to the DCO period at the *slowest* corner
(about 6.7 ns if the slow-corner DCO is at its 150 MHz floor). At 40 ps per tap
that is on the order of 170 taps. The area and power cost of that delay line is
the main risk to row 13 and is open item O2.

## Jitter method

Every recorded jitter figure must restate these items next to the number.

- **Basis.** Post-layout (extracted parasitics of the placed DCO, TDC and
  block) is the only graded basis. Pre-layout numbers may be recorded but are
  labelled "pre-layout, not graded".
- **Simulator and noise.** ngspice transient noise. ngspice has no
  periodic-noise (PSS/PNOISE) analysis. Noise is injected through `trnoise`
  sources and noisy resistors; whether ngspice injects MOSFET channel noise
  directly in transient is not assumed. Where it does not, an equivalent
  `trnoise` current source is placed at each DCO stage output, with its level
  calibrated to the device thermal-noise PSD (open item O5).
- **Run length.** After lock, at least 2000 consecutive output periods
  (10 µs at 200 MHz), the lock-in transient discarded.
- **Seeds.** At least 16 independent noise seeds per corner; the seed list is
  recorded.
- **Estimator.** Edge times are the linearly interpolated rising crossings of
  VDD/2 on the output. Period jitter is the sample standard deviation of
  successive periods, pooled across seeds. The reported figure is the pooled
  value with the across-seed spread (min/max of the per-seed estimates). Long-term
  jitter is the standard deviation of the 100-cycle accumulated edge error.
- **Convergence check.** A result is only recorded if halving the seed count
  moves the pooled value by less than 5 %.
- **Supply noise.** Graded runs use a quiet ideal supply; a separate
  supply-noise sensitivity run is informational.

## Open items

Each names the measurement that settles it. None is settled by guessing a number.

| ID | Question | Settled by |
|---|---|---|
| O1 | Which PDK corner files implement C27 / C27+skew for `sky130_fd_sc_hd` | List the installed liberty and SPICE corner files; record the mapping in this table |
| O2 | Is a ≈170-tap delay line affordable in the 2 mW budget and area | Characterize one tap and a 16-tap segment extracted; extrapolate; revisit row 6b range or add a coarse counter |
| O3 | DCO tuning range and fine LSB actually achieved by the chosen structure at each corner | SPICE sweep of the DCO code over C27+skew, pre- then post-layout |
| O4 | PI gains and word widths | Behavioural loop model (see `placement-constraints.md` for the layout side); gains must meet rows 7, 9, 10 over the DCO gain spread from O3 |
| O5 | Calibration of equivalent noise injection to device thermal noise | Compare an ngspice small ring with injected noise against a published or analytical ring-oscillator phase-noise estimate |
| O6 | Pinned harness reference from a sibling (for example `sky130-modexp`) | Tracked in #3; recorded in `reuse.lock.json` there, not here |
| O7 | Path from extracted placed-block parasitics into ngspice | See `placement-constraints.md` § Extraction hand-off |
