"""adpll_top: boundary wiring only (PD is pending decision 0002). A stub
drives pd_err/pd_valid; DCO word and lock must follow."""

import cocotb
from cocotb.triggers import RisingEdge, Timer

from _common import control_failed, from_signed, start_clock


async def reset(dut, n=8):
    dut.rst_n.value = 0
    dut.n.value = n
    dut.pd_err.value = 0
    dut.pd_valid.value = 0
    start_clock(dut.ref_clk, 40)
    start_clock(dut.dco_clk, 5)
    for _ in range(3):
        await RisingEdge(dut.ref_clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.ref_clk)


async def tick(dut, err):
    dut.pd_err.value = from_signed(err, 9)
    dut.pd_valid.value = 1
    await RisingEdge(dut.ref_clk)
    await Timer(1, units="ns")


@cocotb.test()
async def test_integrates_and_locks(dut):
    await reset(dut)
    # Mid-code after reset: 12 b code 2048 -> coarse 32, fine 0.
    assert (int(dut.dco_coarse.value), int(dut.dco_fine.value)) == (32, 0)
    for _ in range(64):
        await tick(dut, 0)
    assert int(dut.lock.value) == 1
    # Positive error pushes the code up; a large error drops lock.
    for _ in range(60):
        await tick(dut, 120)
    assert int(dut.lock.value) == 0
    word = (int(dut.dco_coarse.value) << 6) | int(dut.dco_fine.value)
    assert word > 32 << 6, f"code did not rise: {word}"
    # fb_clk toggles at dco_clk / N.
    edges, prev = 0, 0
    for _ in range(8 * 10):
        await RisingEdge(dut.dco_clk)
        v = int(dut.fb_clk.value)
        edges += v and not prev
        prev = v
    assert edges in (9, 10), f"fb_clk rising edges in 80 dco cycles: {edges}"


@cocotb.test()
async def negative_control(dut):
    """Wrong model (lock without any in-band samples): must fail."""
    await reset(dut)
    for _ in range(10):
        await tick(dut, 0)
    try:
        assert int(dut.lock.value) == 1, "deliberately-wrong early lock"
    except AssertionError:
        control_failed()
        raise
