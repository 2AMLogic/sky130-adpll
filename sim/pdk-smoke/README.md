# sim/pdk-smoke

Cell-level SPICE toolchain proof for issue #3 (not a design): one
`sky130_fd_sc_hd__inv_1`, from the library's own SPICE view, driven by a pulse
into 10 fF, at the PDK `tt`/`ff`/`ss` corners (1.80 V, 27 C) in ngspice,
expressed as one `klt sim` request so it runs on the batch fleet.

```bash
PDK=sky130A PDK_ROOT=$HOME/.ciel klt sim sim/pdk-smoke/request.json -o sim/pdk-smoke/build --wait-for-capacity 420 --format json
```

`records.json` is the committed result (job `klt-sim-57a3aa314ac4`, simulated,
not measured). Propagation delay orders ss > tt > ff for both edges:

| corner | tpHL (ps) | tpLH (ps) |
|---|---|---|
| ff | 52.7 | 104.6 |
| tt | 60.6 | 111.4 |
| ss | 68.3 | 131.2 |

Use the host `klt` for this request: the setup-pinned klt 0.6.0 ran it locally
(and failed on the `$PDK_ROOT` include), so it is not the submit path here.
The record had its batch bucket name redacted (klayout-tools#3777) and its absolute paths rewritten (`$PDK_ROOT`, repo-relative) after
the run. Versions: `flow/smoke/records/environment.json`.
