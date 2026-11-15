# flow/adpll

`klt synthesize` of the digital ADPLL RTL (`rtl/`, top `adpll_top`) on
`sky130_fd_sc_hd`, `tt_025C_1v80`. Stage 3 of issue #28.

```bash
cd flow/adpll
PDK=sky130A PDK_ROOT=$HOME/.ciel uvx --from "klayout-tools==0.8.0" \
    klt synthesize synthesize.json --format json > records/synthesize-output.json
cp .klt/synthesize/run-*/adpll_top_synth.v records/
```

`records/adpll_top_synth.v` is the generated gate-level netlist; rerunning the
request reproduces it byte for byte (checked with klt 0.8.0, yosys 0.67+post,
open_pdks `f6eeac7dad08`).

## Scope and caveats

- **Pre-layout, synthesized only.** No timing, placement or extraction is
  claimed. `clock_period_ns` is `null`, so ABC ran without a delay target.
- **No phase detector.** Its choice waits on decision 0002 (PENDING); the
  top-level exposes `pd_err`/`pd_valid` as ports. `design/dco.v` (the DCO ring)
  is not part of this request: it is already a structural netlist.
- **Netlist audit.** All 515 leaf instances are `sky130_fd_sc_hd__*` cells
  (`engine_version` `0.67+post`), matching `instance_count` in the response.
  The four remaining instances are the synthesized sub-modules defined in the
  same file (hierarchy is kept).
- **Spec numbers are provisional** (Proposed spec), as in the RTL.
