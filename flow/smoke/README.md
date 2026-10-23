# flow/smoke

Digital toolchain smoke for issue #3: `klt synthesize` then
`klt place-and-route` of a trivial 4-bit counter (`smoke_counter.v`) on
`sky130_fd_sc_hd`, tt_025C_1v80. Toolchain proof only.

```bash
./scripts/setup-env.sh && source .venv/bin/activate
cd flow/smoke
PDK=sky130A PDK_ROOT=$HOME/.ciel klt synthesize synthesize.json --format json > records/synthesize-output.json
cp .klt/synthesize/run-*/smoke_counter_synth.v records/
PDK=sky130A PDK_ROOT=$HOME/.ciel klt place-and-route par.json --format json > records/par-output.json
```

`records/` holds the committed responses, the synthesized and routed netlists,
DEF and GDS, and `environment.json` (commit, PDK pin, tool versions). The
utilization is 5% because the template's met4/met5 straps need a core wider
than a 10-cell design gives at normal utilization. The par output had its
absolute paths rewritten after the run.
