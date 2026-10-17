# verification

cocotb + Icarus testbench harness. It runs on a placeholder DUT
(`placeholder/counter.v`) until real ADPLL RTL exists; the harness does not
depend on the spec's numbers.

## Cold start

From a fresh clone (needs `iverilog`, `verilator`, `yosys`, `uv` on `PATH`; a
missing tool is an error, not a skip):

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r verification/requirements.txt
.venv/bin/python verification/run_tests.py
.venv/bin/python verification/check_records.py
scripts/lint-rtl.sh
```

`run_tests.py` exits 0 only if the smoke tests pass **and** the negative
control fails. It writes `sim/build/verification/result.json` (gitignored
scratch): per-test pass/fail and `expected_fail`, seed (`--seed N` to
replay), commit, `dirty` flag, DUT, and the version of every tool used.
`check_records.py` validates that record.

## Layout

| Path | Role |
|---|---|
| `run_tests.py` | runner: smoke group + negative-control group, writes the record |
| `check_records.py` | validates a record (versions present, control failed on an assertion) |
| `requirements.txt` | pinned Python deps |
| `placeholder/` | counter DUT, smoke tests and `negative_control` |
| `gate-level/` | slot for re-running the same tests on a netlist |
| `../scripts/lint-rtl.sh` | `verilator --lint-only -Wall` over `rtl/`; prints "vacuous pass" while `rtl/` is empty |

## Negative control

`negative_control` compares the DUT against a deliberately wrong model and
must fail on its assertion. If it passes, or dies on some other error, the
runner reports a failure: a harness that cannot fail proves nothing.

## Tool versions

Python deps are pinned in `requirements.txt`. Simulator and lint tools come
from the host until the pinned environment (#3) lands; their versions are
read from each tool's own `--version` output into every record.

## Reference

Shape follows `2AMLogic/sky130-modexp` @ `18f4d8fd5e104f64550817a5468f262c159f734f`
(`verification/_dut.py`, `test_modexp.py`, `check_records.py`,
`gate-level/`); see `reuse.lock.json`. The `check_records.py` here is a new,
smaller checker for run records, not a copy of modexp's evidence-record linter.
