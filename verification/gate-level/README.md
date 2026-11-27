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
| netlist | `flow/adpll/records/adpll_top_synth.v` — the sha256 it graded is recorded in `records/result-gate.json` (`dut.netlist_sha256`) and re-derived against the tree by `check_records.py` |
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

The record now states the method it used. `run_tests.py` captures its own
compile log, derives the cell-model arm from it (any `Choosing typ
expression` warning means the timing arm was selected) and records the arm as
`method.cell_model_arm` in every record. A `--level gate` run that selected
the timing arm is a recorded `problems[]` failure with a non-zero exit, and
`check_records.py` independently fails any schema-2 gate record whose arm is
missing or not `functional`. The rule lives in the checker: the runner
grades every record with the checker's content checks before it assigns
`ok`, so the direct `run_tests.py` invocation documented below is no longer
the unguarded path. That closes two more silent passes of the same shape
(#163): a gate run with `--netlist` omitted, and one whose `--netlist` names
a file the compile was not given. Both used to exit 0 with `"ok": true` and
were rejected only by the standalone checker. The expected compile is
warning-free.

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
  --netlist <netlist.v, as listed on --sources> \
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
- `--netlist` names the netlist that was graded and must be one of the files
  on `--sources`: the record's `dut.netlist` and `dut.netlist_sha256` are
  written from it. A gate-level run that omits it, or names a file the
  compile was not given, is a failed record with a non-zero exit — the
  runner applies `check_records.py`'s content checks before it writes `ok`.
- `--build-dir` must be an **absolute** path. cocotb's runner resolves the
  results XML relative to `--test-dir`, so a relative build dir makes the run
  report "simulator produced no results" even when every test passed.
- `--level` is restricted to `rtl` | `gate` (any other spelling is an
  argparse error, so the enforcement cannot be dodged by a variant) and
  recorded; `run_tests.py` captures the compile log and records the selected
  cell-model arm as `method.cell_model_arm`, failing a gate run that selected
  the timing arm. The sources are recorded too, so `dut.sources[0]` names the
  defines file that selected the functional arm.
- The netlist must keep the RTL port names, since the tests drive ports by name.
- Gate-level needs the sky130 cell models and sim defines on the source list.
  Shape taken from `2AMLogic/sky130-modexp` @
  `18f4d8fd5e104f64550817a5468f262c159f734f`, `verification/gate-level/`
  (`run-gate-level-sim.sh`, `sky130_fd_sc_hd_sim_defines.v`) — see
  `reuse.lock.json`; the `UNIT_DELAY` value diverges, for the reason above.
- A post-route result is graded on the extracted netlist, never inferred from
  the RTL result.

## Staleness

`records/result-gate.json` names the netlist it graded (`dut.netlist`) and the
sha256 it graded (`dut.netlist_sha256`, written by `run_tests.py --netlist`).
`check_records.py` re-derives the sha256 of that file in the tree and **fails**
the record on a mismatch, a missing field, or a file that is gone — so a
regenerated netlist (e.g. by #69, which removes the 64 `conb_1` tie cells)
invalidates the record loudly instead of silently. `npm run check:records` and
CI both run that check against the committed record; re-run
`run-gate-level.sh` to mint a fresh one. The runner holds a record to the
same rule as it writes it — `--netlist` present, naming a file on
`--sources`, hashing to what it records — so a record that would fail here
cannot be reported as a pass there.
