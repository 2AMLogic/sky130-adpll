# gate-level re-run

Items 5 and 7 (digital columns) re-run the **same** cocotb tests on a
synthesized or post-route netlist. The synthesized leg is now exercised: a
netlist exists (`flow/adpll/records/adpll_top_synth.v`) and the `top` suite's
test module runs on it unmodified.

Still not done: **timing back-annotation (SDF)** and the post-route leg. This
directory contains no timing result.

## What was run

```bash
./verification/gate-level/run-gate-level.sh            # or --seed=12345
```

Result: `records/result-gate.json`, with its method in
`records/result-gate.method.md`. Both are written by the script; re-run it
rather than editing them.

**The method, stated next to the result** (this repo does not accept a number
without one):

| | |
|---|---|
| what | pre-layout, **zero-delay functional** simulation of the synthesized netlist |
| what it is not | not a timing result — **no SDF**, no static timing, no frequency/delay/jitter claim |
| netlist | `flow/adpll/records/adpll_top_synth.v`, sha256 `9a9a836f646883beac3e6477e76b98dbf567b960a51cd74cf2ee8f7b60418dea` |
| cell models | `$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/verilog/{primitives,sky130_fd_sc_hd}.v` |
| open_pdks | `f6eeac7dad08` (the `CIEL_SKY130_VERSION` pin in `scripts/setup-env.sh`) |
| sim defines | `FUNCTIONAL` and `UNIT_DELAY` (empty replacement → zero delay); `USE_POWER_PINS` **not** defined |
| DUT | `adpll_top`, driven by `verification/test_top.py` — byte-identical to the RTL run's test module |
| tools | Icarus Verilog 13.0, cocotb 1.9.2 |
| seed | recorded per run; `test_integrates_and_locks` passes on 12345, 777 and 20260114 |

The netlist keeps the RTL port names, order and widths (`ref_clk, dco_clk,
rst_n, n[4:0], fb_clk, pd_err[8:0], pd_valid, dco_coarse[5:0], dco_fine[5:0],
lock`), so nothing in `test_top.py` had to change and nothing in the netlist
was hand-edited.

`top` is the only suite that can run here: it drives ports only, while e.g.
`test_loop_filter` reads `dut.integ`, an internal net synthesis does not
preserve.

## The trap this directory exists to document

**Omitting `` `define FUNCTIONAL `` does not fail. It silently produces a
timing simulation that passes.** Measured on Icarus 13.0 with the pinned
sky130A: compiling the cell models with no defines exits 0, selects each cell's
`specify`/timing arm (10 `Choosing typ expression` warnings), and the suite
then reports `ok test_integrates_and_locks` / `ok negative_control` with exit 0
and a record whose `"ok": true` and `"level": "gate"` are **indistinguishable
from the intended one** — while carrying the models' built-in typ delays, i.e.
an unstated timing claim.

Nothing in the record schema catches that, so `run-gate-level.sh` does: it
compiles the source list first and refuses to run the simulation if it sees a
`Choosing typ expression` warning. The expected compile is warning-free.

Two more measured details behind `sky130_fd_sc_hd_sim_defines.v`:

- **The defines file must be listed first.** iverilog shares one macro scope
  across the files on its command line and evaluates each cell's
  `` `ifdef FUNCTIONAL `` where it appears. Defines first: 0 warnings. Defines
  after the models: the same 10 timing-arm warnings. `run_tests.py` passes
  `--sources` through in order.
- **`` `define UNIT_DELAY #1 `` fails this design**, so the sibling pattern's
  value is not used here. `test_top`'s `tick()` samples at
  `Timer(1, units="ns")` after each `ref_clk` rising edge — exactly when a `#1`
  flop output transitions — so the 64th in-band sample reads `lock` on the edge
  of its own update and `test_integrates_and_locks` fails at `test_top.py:37`
  on seeds 12345, 777 and 20260114. Empty (zero-delay) `UNIT_DELAY` is used
  instead; leaving it undefined also works but costs 58
  `macro UNIT_DELAY undefined` warnings, which would blunt the warning-free
  compile the method guard relies on.

## DUT-swap mechanism

`run_tests.py` takes the DUT as arguments, so the RTL and gate-level runs share
one test module:

```bash
.venv/bin/python verification/run_tests.py \
  --level gate \
  --sources <sim_defines.v> <cell models...> <netlist.v> \
  --toplevel <top> \
  --test-module <same test module as the RTL run> \
  --test-dir <its directory> \
  --tests <comma-separated smoke testcases> \
  --build-dir <absolute path> \
  --record <record.json>
```

- `--sources` requires **all four** of `--toplevel`, `--test-module`,
  `--test-dir` and `--tests`; omitting any one is an argparse error before the
  simulator starts.
- `--build-dir` must be an **absolute** path. cocotb's runner resolves the
  results XML relative to `--test-dir`, so a relative build dir makes the run
  report "simulator produced no results" even when every test passed.
- `--level gate` is recorded in the result; the sources are recorded too, so
  `dut.sources[0]` names the defines file that selected the functional arm.
- The netlist must keep the RTL port names, since the tests drive ports by name.
- Gate-level needs the sky130 cell models and sim defines on the source list.
  Shape taken from `2AMLogic/sky130-modexp` @
  `18f4d8fd5e104f64550817a5468f262c159f734f`, `verification/gate-level/`
  (`run-gate-level-sim.sh`, `sky130_fd_sc_hd_sim_defines.v`) — see
  `reuse.lock.json`; the `UNIT_DELAY` value diverges, for the reason above.
- A post-route result is graded on the extracted netlist, never inferred from
  the RTL result.

## Staleness

`records/result-gate.method.md` names the netlist sha256 the record graded. If
it stops matching `netlist_sha256` in
`flow/adpll/records/synthesize-output.json`, the netlist has been regenerated
since (e.g. by #69, which removes the 64 `conb_1` tie cells) and the record
describes an artifact no longer in the tree — re-run the script.
