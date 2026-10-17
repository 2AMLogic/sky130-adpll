# sky130-adpll — agent instructions

Open-source canary block: a synthesizable all-digital PLL on SkyWater sky130,
designed and verified by AI agents. **Mixed-signal** — the netlist is
standard cells, but the oscillator and TDC are characterized as analog
circuits — so both flows apply.

- **PDK**: SkyWater sky130 (open PDK, google/skywater-pdk). Digital: cocotb +
  Icarus, Yosys, OpenROAD. Analog: ngspice (with xschem where a schematic
  helps) for the DCO and TDC cells. Layout, DRC, and LVS through
  klayout-tools (`klt`) in both cases.
- **Placement-dependent timing is the point, and the risk.** The DCO's
  frequency and the TDC's resolution come from cell delays and wire loads,
  so they move with placement. Constrain the DCO and TDC placement
  explicitly, extract them, and grade them post-layout; never take their
  behaviour from static timing or a pre-layout netlist. Expect the flow to be
  weakest at placement constraints, extraction of a placed digital block, and
  handing extracted results back to SPICE — file accordingly.
- **Standard cells only.** The block is defined by needing no custom analog.
  A hand-drawn cell is a spec change and needs a decision record.
- **Jitter needs its method.** ngspice has no periodic-noise analysis. Every
  jitter number states the method that produced it (transient noise, run
  length, seeds, estimator), and whether it is pre- or post-layout, next to
  the number. A jitter figure without its method is not a result.
- **Scope discipline.** `sky130-pll` is the analog PLL on this PDK; this
  block is a different architecture, not a duplicate, and shares nothing
  device-level with it. Take PDK-independent harness material (sim harness
  mechanics, cocotb structure) from a sibling by pinned reference
  (`reuse.lock.json`) rather than rewriting it. The reference oscillator is
  out of scope; the reference clock is a source at the boundary.
- **Friction protocol (the canary's job)**: every time klayout-tools is
  awkward, missing a capability, or wrong for what you need, file an issue at
  `2AMLogic/klayout-tools` describing the tool gap generically — that tracker
  is scoped to the tool, so keep design-specific detail out of it and describe
  the gap, not the design.
- **Verification is the product**: no claim without a testbench. PVT corners
  on every recorded result; recorded results are append-only evidence. A
  simulated number is never called measured.
- Spec changes go through `spec/` with a decision record; agents do not relax
  the ratified spec to make results pass.
- **200 MHz integer-N is the target.** 100 MHz is the fallback; 400 MHz and
  fractional-N are stretches. Do not let fractional-N drive the loop
  architecture before integer-N closes.
