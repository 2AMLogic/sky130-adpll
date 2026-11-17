# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide role (newest first).

### 2026-11-17

- **PR #127**: ci: widen loom-tooling allowlist with wired merge-pr/spawn-claude suites
- **PR #125**: ci: add loom-tooling job gating vendored Loom suites on .loom/ paths
- **PR #123**: chore(loom): resync installed Loom to v0.19.1306
- **Issue #128** (closed): loom-tooling's path gate skips the suites on the very PR that edits the allowlist
- **Issue #126** (closed): loom-tooling job runs 3 of 334 vendored suites, so a .loom/ diff outside the lease scripts still gets a green that covers nothing
- **Issue #124** (closed): CI gives no signal on .loom/** tooling changes, so resync PRs show a green badge that never ran their diff

### 2026-11-16

- **PR #121**: chore(loom): resync installed Loom to v0.19.1305
- **PR #119**: chore(loom): resync installed Loom to v0.19.1302

### 2026-11-15

- **PR #118**: verification: record the graded netlist's sha256 and check it against the tree
- **Issue #114** (closed): Nothing binds the gate-level record to the netlist it graded: the #92 drift can recur silently
- **PR #115**: manifests: attest reuse.lock.json under T1 item 10
- **PR #108**: test(verification): pin run_tests.py CLI gating with a stdlib self-test
- **PR #112**: fix(verification): regrade gate-level record on the 515-instance netlist
- **PR #111**: fix(manifests): resolve klt venv-first with PATH fallback in check-signoff.sh
- **PR #110**: fix: echo iverilog compile diagnostics and fail the arm rule closed on non-int schema
- **PR #103**: docs: refresh klt environment-record field to observed 0.8.0 and document partial-refresh convention
- **Issue #90** (closed): No automated coverage for run_tests.py's own CLI gating: the --record guard can regress silently
- **Issue #105** (closed): check-reuse-lock.sh passes vacuously when reuse.lock.json carries no hashes
- **Issue #107** (closed): check-signoff.sh resolves bare klt from PATH, so npm run check:ci drifts spuriously under a non-pinned host klt
- **Issue #104** (closed): run_tests.py hides iverilog compile diagnostics in compile.log; check_records.py's arm rule fails open on a non-int schema
- **Issue #96** (closed): environment.json freshness drift: klt_pinned_synth_par still records 0.6.0 while setup-env.sh pins 0.8.0, and recorded_on has no partial-refresh convention
- **Issue #92** (closed): Gate-level record will name a netlist sha256 that no longer exists once #80 and #77 both land
- **PR #109**: fix: fail run_tests when a gated tool exits non-zero instead of recording its stderr as a version
- **PR #106**: fix: derive setup-env.sh --help header from the block itself
- **PR #101**: feat: record the cell-model arm in result records, enforce it for gate level
- **PR #99**: docs: correct spec-ratification and TDC claims in README layout fence
- **PR #97**: fix(setup-env): install cocotb via verification/requirements.txt, not an unpinned resolve
- **PR #94**: manifests: attest scripts/lint-rtl.sh in item 10 hygiene inventory
- **PR #93**: ci: check reuse.lock.json hashes against committed content
- **Issue #98** (closed): tool_versions() records a failing tool's stderr as its version string, and check_records.py certifies it
- **Issue #91** (closed): setup-env.sh --help truncates the last line of its own header block (pre-existing off-by-one in the sed range)
- **Issue #88** (closed): README: two residual claim-vs-reality drifts after #67 ("ratified spec", rtl/ TDC)
- **Issue #83** (closed): A wrong-method gate-level record still validates: check_records.py cannot see which cell-model arm produced it
- **Issue #82** (closed): reuse.lock.json attests a sha256 scripts/setup-env.sh no longer has, and nothing checks it
- **Issue #81** (closed): setup-env.sh resolves its own unpinned cocotb into the harness venv: consolidate on the requirements.txt pin
- **Issue #76** (closed): Item-10 attests ci.yml but not scripts/lint-rtl.sh, the script it invokes
- **PR #95**: chore: drop yosys from the verification tool gate
- **PR #89**: fix(setup-env): probe verilator in the toolchain check and correct the step-4 gate advisory
- **PR #87**: docs: state the actual design status in the READMEs
- **PR #86**: fix: reject --record with multi-suite registry run in run_tests.py
- **PR #80**: rtl: make loop-filter saturation bounds localparams, dropping 64 tie cells
- **PR #77**: feat(verification): run test_top on the synthesized netlist, with a cell-model-arm guard
- **Issue #74** (closed): Drop yosys from the verification tool gate: the RTL/gate-level leg never invokes it
- **Issue #85** (closed): setup-env.sh certifies a clean toolchain on a host that cannot run the gates it recommends: verilator unprobed, plus two dead references
- **Issue #73** (closed): run_tests.py --record silently collapses five suite records into one: reject the combination it cannot express
- **Issue #70** (closed): Gate-level re-run slot is still documentation only: run the top suite on the synthesized ADPLL netlist
- **Issue #69** (closed): Loop filter synthesizes 64 conb_1 tie cells for constants no logic reads: remove them and regenerate the netlist
- **Issue #67** (closed): README status is stale: it says nothing is designed, while RTL, a synthesized netlist and 3 of 11 T1 items are on main

### 2026-11-14

- **PR #84**: ci: upload the per-suite verification records instead of a path that matches nothing
- **PR #78**: refactor: drop unused to_signed, trigger re-exports and __all__ from test helpers
- **PR #75**: chore: attest .github/workflows/ci.yml in the item-10 hygiene inventory
- **PR #66**: docs: roadmap as of 2026-11-13
- **Issue #72** (closed): Remove dead export surface in verification/_common.py: to_signed and the unused trigger re-exports
- **Issue #71** (closed): CI's verification-result artifact uploads nothing: the upload path matches no record the multi-suite runner writes
- **Issue #68** (closed): Item-10 inventory predates the verification CI job: add ci.yml and regenerate the attestation

### 2026-11-12

- **PR #61**: Bump Repo Skills 0.25.10 -> 0.26.1

### 2026-11-07

- **PR #58**: Bump Repo Skills 0.25.1 -> 0.25.10

### 2026-11-06

- **Issue #46** (closed): Remove vendored design-evidence-tiers.md: the pinned klt already ships it

### 2026-11-02

- **PR #53**: feat(manifests): attest T1 item 9 testbench inventory for the RTL benches
- **PR #50**: feat(manifests): attest T1 item 1 design sources and cite it in the block manifest
- **PR #49**: feat(flow): add klt synthesize request and gate-level netlist for ADPLL RTL
- **PR #48**: feat(design): add DCO structural ring netlist (library cells only)
- **Issue #32** (closed): T1 item 9 (testbenches shipped): replace the placeholder DUT with the ADPLL benches and attest item 9
- **Issue #28** (closed): T1 item 1 (design sources): ADPLL RTL (PI loop filter, divider, lock detect, DCO code path) plus synthesized sky130_fd_sc_hd netlist with item-1 attestation

### 2026-11-01

- **PR #45**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-30

- **PR #43**: chore: remove vendored OpenROAD smoke test
- **Issue #42** (closed): Remove vendored OpenROAD smoke test: flow/smoke already proves the toolchain

### 2026-10-28

- **PR #40**: refactor(verification): drop the counter placeholder suite and require --sources args
- **Issue #36** (closed): Remove verification/placeholder counter suite: its stated reason (empty rtl/) is gone

### 2026-10-27

- **PR #38**: chore(deps): pin klayout-tools to the 0.8.0 PyPI release
- **Issue #37** (closed): Bump klayout-tools pin 267ea83a0510, dac2b5daceb6 → 0.8.0
- **PR #34**: feat(rtl): add ADPLL loop filter, divider, lock detector, DCO code path and top

### 2026-10-24

- **PR #26**: docs(spec): verify S1 citation and renumber sources in record 0002
- **Issue #23** (closed): Resolve unverified source S1 in decision record 0002
- **PR #22**: docs(spec): add proposed phase-detector comparison record 0002
- **Issue #20** (closed): Prepare the multi-bit TDC vs bang-bang phase-detector comparison (authorized on #2, 2026-10-19)
- **PR #7**: ci: add klt signoff manifest, committed T1 record and drift check
- **Issue #5** (closed): Signoff scaffolding: block manifest, committed klt signoff record, and CI (T1 item 10)

### 2026-10-21

- **PR #15**: Bump Repo Skills 0.24.3 -> 0.24.7

### 2026-10-20

- **PR #12**: fix: wire package.json lint/test/check:ci to real verification commands
- **Issue #11** (closed): Replace always-pass package.json gates (check:ci/test/lint) with the real checks

### 2026-10-18

- **PR #14**: docs: drop stale sibling-repo references from vendored smoke scripts
- **Issue #13** (closed): Remove stale sibling-repo references from smoke scripts (missing environment doc, modexp RTL)

### 2026-10-17

- **PR #10**: feat: pin toolchain and add digital and cell-SPICE smoke records
- **PR #9**: docs(spec): propose target spec, decision record and placement approach
- **PR #8**: feat: add cocotb/Icarus harness with negative control, RTL lint gate and CI job
- **PR #1**: chore(loom): Install Loom 0.19.1181
- **Issue #4** (closed): Testbench harness and RTL lint skeleton: cocotb + Icarus runner, negative control, CI (T1 item 9)
- **Issue #3** (closed): Pin the sky130 environment (adopt sky130-modexp's setup) and commit digital and cell-level SPICE smoke runs
