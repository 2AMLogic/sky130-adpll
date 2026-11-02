# sim/dco

DCO cell-level bench for spec rows 2/3 (tuning range, fine LSB) and open item O3.
**Pre-layout, simulated only. Status: bench verified on one local corner; the
C27+skew grid has NOT completed, so there is no `records.json` yet.**

`dco_tb.spice` is the electrical netlist of `design/dco.v` (same cells and
connectivity); `.param cc` / `fc` set the coarse / fine code. `request.json`
expresses the grid as one `klt sim` request: 5 processes (tt ss ff sf fs) x
VDD {1.62, 1.80, 1.98} x T {-40, 25, 125} x 5 code points = 225 units; each unit
measures the time of 10 output periods (`t10_s`; f = 10 / t10_s).

```bash
PDK=sky130A PDK_ROOT=$HOME/.ciel klt sim sim/dco/request.json --backend batch \
  --max-units-per-job 22 --max-concurrent-jobs 4 -o sim/dco/build --wait-for-capacity 300 --format json
```

Probe (local, one corner, sf/1.80 V/25 C, cc=32 fc=32): t10 = 10.13 ns, i.e. about
0.99 GHz, far above the 200 MHz target. The provisional ring in `design/dco.v`
therefore does not put 200 MHz inside its range at that corner.

Batch status: workers took about 120 s per unit (29 s locally), so many units hit
`options.timeout_s`; the grid needs a cheaper bench or a longer timeout with
smaller jobs (the fleet caps jobs at 3600 s).
