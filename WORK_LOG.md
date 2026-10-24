# Work Log

Chronological record of merged PRs and closed issues, maintained by the Guide role (newest first).

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
