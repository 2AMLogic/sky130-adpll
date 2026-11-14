# rtl

Synthesizable ADPLL digital blocks (integer-N). Spec numbers come from the
**Proposed** spec and are marked `provisional` in each module's parameters.

| Module | Role | Spec rows |
|---|---|---|
| `adpll_loop_filter.v` | PI filter, power-of-two Kp/Ki, 9 b error, 24 b saturating integrator, 14 b code | 8, 8a |
| `adpll_divider.v` | integer-N feedback divider, N = 4..20 | 5, 5f |
| `adpll_lock_detect.v` | 64 consecutive \|err\| <= 4 LSB; deassert hysteresis is a placeholder | 9 |
| `adpll_dco_code.v` | 12 b code to coarse[5:0] / fine[5:0], 2 b first-order dither | 8a |
| `adpll_top.v` | top level with an explicit phase-detector port boundary | — |

**Pending decision 0002:** the phase detector (TDC vs bang-bang) is not in
this directory. `adpll_top` exposes `fb_clk`, `pd_err` and `pd_valid` as the
boundary; the PD RTL/netlist lands after the decision is ratified.

Tests: `verification/test_*.py`, run by `verification/run_tests.py`. Lint:
`scripts/lint-rtl.sh`.
