"""adpll_divider: fb_clk period is exactly N dco_clk cycles, 50 % +/- 1."""

import cocotb
from cocotb.triggers import RisingEdge

from _common import control_failed, start_clock


async def measure(dut, n, cycles=None):
    dut.rst_n.value = 0
    dut.n.value = n
    start_clock(dut.dco_clk)
    await RisingEdge(dut.dco_clk)
    await RisingEdge(dut.dco_clk)
    dut.rst_n.value = 1
    rises, high, prev = [], 0, 0
    for i in range(cycles or 6 * n + 4):
        await RisingEdge(dut.dco_clk)
        v = int(dut.fb_clk.value)
        if v and not prev:
            rises.append(i)
        high += v
        prev = v
    return rises, high


async def check_ratio(dut, n):
    rises, high = await measure(dut, n)
    assert len(rises) >= 4, f"N={n}: only {len(rises)} fb_clk edges"
    gaps = {b - a for a, b in zip(rises, rises[1:])}
    assert gaps == {n}, f"N={n}: fb_clk periods {gaps}"
    assert abs(high / (6 * n + 4) - 0.5) < 0.3, f"N={n}: duty {high}"


@cocotb.test()
async def test_ratio_200mhz(dut):
    """fref = 25 MHz, fout = 200 MHz."""
    await check_ratio(dut, 8)


@cocotb.test()
async def test_ratio_100mhz_fallback(dut):
    """fref = 25 MHz, fout = 100 MHz."""
    await check_ratio(dut, 4)


@cocotb.test()
async def test_ratio_range(dut):
    for n in range(4, 21):  # spec row 5: N = 4..20
        await check_ratio(dut, n)


@cocotb.test()
async def negative_control(dut):
    """Wrong model (period N+1): must fail."""
    rises, _ = await measure(dut, 8)
    try:
        assert rises[1] - rises[0] == 9, "deliberately-wrong period"
    except AssertionError:
        control_failed()
        raise
