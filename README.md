# sky130-adpll

A synthesizable all-digital phase-locked loop (ADPLL) on
[SkyWater sky130](https://github.com/google/skywater-pdk), the 130 nm open
PDK — a digitally controlled oscillator, a time-to-digital converter, and a
digital loop filter, built from standard cells — designed by AI agents
driving [klayout-tools](https://github.com/2AMLogic/klayout-tools),
cocotb + Icarus and Yosys/OpenROAD on the digital side, and ngspice for the
timing-critical cells.

**Status: spec Proposed (not ratified), design under way.** The digital RTL —
loop filter, divider, lock detect, DCO code path, top level — is written and
verified at the RTL level with cocotb suites, and a pre-layout synthesized
gate-level netlist of the top level is recorded under `flow/adpll/records/`.
There is no phase detector yet: its choice (TDC vs bang-bang) waits on
decision record `0002`, so the loop is open at the PD boundary. There is no
layout. Nothing here is a measurement; every number in the target table below
is a target, not a result.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using sky130, not just this repo.

## Why this block, on this PDK

The program's sky130 PLL, [sky130-pll](https://github.com/2AMLogic/sky130-pll),
is an analog charge-pump design drawn transistor by transistor. This block
is the same function by the other route: every element is a standard cell,
placed and routed by the digital flow. That makes it portable in a way an
analog PLL is not, and it makes it a hard test of the digital flow.

The hard part is that an ADPLL is digital in its netlist and analog in its
behaviour. The oscillator's frequency and the TDC's resolution depend on
cell delays, wire loads, and placement, so the flow has to honour placement
constraints and the evidence has to come from post-layout extraction, not
from static timing alone. Jitter is the block's figure of merit, and
measuring it with open tools needs a stated method. Both push the tools
somewhere a purely digital or purely analog block does not.

## Scope

- **In scope**: the digitally controlled oscillator (DCO), the TDC or
  bang-bang phase detector, the digital loop filter, the feedback divider,
  lock detection, and the placement constraints that make the DCO and TDC
  repeatable.
- **Not in scope**: the reference oscillator, and any analog loop element.
  The reference clock is a source at the block boundary.
- **Not a duplicate of sky130-pll.** Same function, different architecture:
  that repo's ring VCO, charge pump, and analog loop filter have no
  counterpart here.

## Target specification (DRAFT — engineering to ratify, see issue #2)

| Parameter | Target | Fallback | Stretch |
|---|---|---|---|
| Output frequency | 200 MHz | 100 MHz | 400 MHz |
| Reference input | 10–50 MHz | 25 MHz fixed | — |
| Multiplication | integer-N | fixed N | fractional-N |
| Period jitter (rms, simulated, post-layout) | ≤ 1% of the output period | ≤ 2% | ≤ 0.5% |
| Lock time | ≤ 20 µs | ≤ 100 µs | ≤ 5 µs |
| Supply / power | 1.8 V core cells; ≤ 2 mW | ≤ 5 mW | ≤ 1 mW |
| Implementation | standard cells only, no custom analog | — | — |
| Signoff | DRC + LVS clean, STA and post-layout re-verified | — | — |

Maturity ladder: spec ratified → loop modelled and RTL verified → DCO and
TDC characterized post-layout → full loop simulated post-layout across PVT →
layout DRC/LVS-clean → shuttle seat → measured silicon. **Current position:
before the first rung — spec Proposed (not ratified); RTL verified at the RTL
level; top-level netlist synthesized pre-layout; no post-layout
characterization yet.**

## Cold start

```bash
./scripts/setup-env.sh && source .venv/bin/activate   # pinned klt, Yosys, sky130A; fails on an open_pdks revision mismatch
```

Digital smoke: `flow/smoke/`. Cell SPICE smoke: `sim/pdk-smoke/`. Versions and
commit: `flow/smoke/records/environment.json`. Vendored scripts: `reuse.lock.json`.

## Repo layout

```
spec/          target spec + decision records (Proposed, not ratified)
rtl/           loop filter, divider, control, and DCO/TDC structural RTL
design/        cell-level netlists for the DCO and TDC characterization
flow/          digital flow: smoke checks + synthesized netlist records
sim/           SPICE testbenches + PVT corner results (ngspice)
verification/  cocotb testbenches + behavioural loop model
layout/        GDS + DRC/LVS reports (klayout-tools driven; empty)
measurements/  silicon characterization (empty until tape-out)
manifests/     evidence chain: inventories, attestations, signoff records
scripts/       environment setup, lint, and flow helpers
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
