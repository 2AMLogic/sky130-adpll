# gate-level re-run slot

Documentation only: no netlist exists yet. Items 5 and 7 (digital columns)
re-run the **same** cocotb tests on a synthesized or post-route netlist.

## DUT-swap mechanism

`run_tests.py` takes the DUT as arguments, so the RTL and gate-level runs
share one test module:

```bash
.venv/bin/python verification/run_tests.py \
  --level gate \
  --sources <netlist.v> <sky130_fd_sc_hd_sim_defines.v-and-cell-models...> \
  --toplevel <top> \
  --test-module <same test module as the RTL run> \
  --test-dir <its directory> \
  --record sim/build/verification/result-gate.json
```

- `--level gate` is recorded in the result; the sources are recorded too.
- The netlist must keep the RTL port names, since the tests drive ports by name.
- Gate-level needs the sky130 cell models and sim defines on the source list.
  Pattern: `2AMLogic/sky130-modexp` @ `18f4d8fd5e104f64550817a5468f262c159f734f`,
  `verification/gate-level/` (`run-gate-level-sim.sh`,
  `sky130_fd_sc_hd_sim_defines.v`).
- A post-route result is graded on the extracted netlist, never inferred from
  the RTL result.

Not yet done: the cell-model source list, timing back-annotation (SDF), and a
placeholder-netlist exercise of this path.
