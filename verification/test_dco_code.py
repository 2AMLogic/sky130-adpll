"""adpll_dco_code: coarse/fine split and 2 b first-order dither."""

import cocotb
from cocotb.triggers import RisingEdge, Timer

from _common import control_failed, start_clock


async def reset(dut, code):
    dut.rst_n.value = 0
    dut.code.value = code
    start_clock(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await Timer(1, units="ns")


@cocotb.test()
async def test_split(dut):
    await reset(dut, 0b101010_110011_00)
    assert int(dut.coarse.value) == 0b101010
    assert int(dut.fine.value) == 0b110011


@cocotb.test()
async def test_dither_average(dut):
    for frac in (0, 1, 2, 3):
        fine_in = 20
        await reset(dut, (7 << 8) | (fine_in << 2) | frac)
        extra = 0
        for _ in range(16):  # four full dither periods
            await RisingEdge(dut.clk)
            await Timer(1, units="ns")
            f = int(dut.fine.value) - fine_in
            assert f in (0, 1), f"dither step {f}"
            extra += f
        assert extra == 4 * frac, f"frac {frac}: {extra} extra LSB in 16 cycles"
        assert int(dut.coarse.value) == 7


@cocotb.test()
async def test_fine_saturates(dut):
    await reset(dut, (3 << 8) | (63 << 2) | 3)
    for _ in range(8):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        assert int(dut.fine.value) == 63 and int(dut.coarse.value) == 3


@cocotb.test()
async def negative_control(dut):
    """Wrong model (no dither): must fail for a fractional code."""
    await reset(dut, (1 << 8) | (10 << 2) | 2)
    seen = set()
    for _ in range(8):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        seen.add(int(dut.fine.value))
    try:
        assert seen == {10}, f"fine took values {sorted(seen)}; deliberately-wrong model wants only 10"
    except AssertionError:
        control_failed()
        raise
