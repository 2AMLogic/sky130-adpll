// Simulation defines for the sky130_fd_sc_hd Verilog cell models.
//
// MUST be listed FIRST on iverilog's source list (run_tests.py --sources
// preserves the order it is given): iverilog shares one macro scope across
// every file named on its command line and evaluates each cell's
// `ifdef FUNCTIONAL where it appears, so these defines only reach the models
// if they are parsed before them. Measured (issue #70): defines first -> 0
// warnings; defines last -> 10 `Choosing typ expression' warnings, i.e. the
// specify/timing arm was selected after all.
//
// FUNCTIONAL selects each cell's behavioural arm instead of its
// specify/timing arm. Leaving it undefined does NOT fail -- it compiles,
// simulates and passes, silently producing a *timing* simulation carrying the
// models' built-in typ delays. That record would be an unstated timing claim,
// which this repo's method-disclosure rule forbids. The tell is a
// `Choosing typ expression' warning from iverilog; run-gate-level.sh refuses
// to run when it sees one.
`define FUNCTIONAL

// UNIT_DELAY is the delay the behavioural arm applies to its outputs. Empty
// replacement text = zero delay, which is the method this record claims.
//
// Deliberately NOT `#1`: the sibling pattern this directory references
// (2AMLogic/sky130-modexp @ 18f4d8fd, verification/gate-level/) defines it as
// `#1`, which fails this design. test_top's tick() samples at
// `Timer(1, units="ns")` after each ref_clk rising edge -- exactly when a #1
// flop output transitions -- so the 64th in-band sample reads lock on the edge
// of its own update and `test_integrates_and_locks` fails at test_top.py:37.
// Measured failing on seeds 12345, 777 and 20260114 (issue #70). The sibling's
// 10 ns clock has no such 1 ns settle window.
//
// Defining it empty rather than leaving it undefined is also deliberate:
// undefined works functionally too, but costs 58 `macro UNIT_DELAY undefined
// (and assumed null)' warnings, and a warning-free compile is what makes the
// `Choosing typ expression' check above a usable signal.
`define UNIT_DELAY

// USE_POWER_PINS is deliberately NOT defined: the synthesized netlist
// instantiates cells without VPWR/VGND/VPB/VNB (verified: 0 occurrences in
// flow/adpll/records/adpll_top_synth.v), so defining it would add ports the
// netlist never connects.
