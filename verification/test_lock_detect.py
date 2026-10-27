"""adpll_lock_detect: 64 consecutive |err| <= 4 asserts lock (spec row 9);
the deassert hysteresis (UNLOCK_THRESH = 8) is a placeholder, not spec."""

import cocotb
from cocotb.triggers import RisingEdge, Timer

from _common import control_failed, from_signed, start_clock

ERR_W = 9


async def reset(dut):
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.err.value = 0
    start_clock(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def tick(dut, err):
    dut.err.value = from_signed(err, ERR_W)
    dut.en.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, units="ns")
    return int(dut.lock.value)


@cocotb.test()
async def test_lock_asserts_after_64(dut):
    await reset(dut)
    assert int(dut.lock.value) == 0
    for i in range(63):
        assert await tick(dut, -4 if i % 2 else 4) == 0, f"early lock at sample {i + 1}"
    assert await tick(dut, 0) == 1, "lock not asserted on 64th sample"


@cocotb.test()
async def test_run_resets(dut):
    await reset(dut)
    for _ in range(63):
        await tick(dut, 0)
    assert await tick(dut, 5) == 0  # out of the lock band: run restarts
    for _ in range(63):
        assert await tick(dut, 0) == 0
    assert await tick(dut, 0) == 1


@cocotb.test()
async def test_deassert_hysteresis(dut):
    await reset(dut)
    for _ in range(64):
        await tick(dut, 0)
    assert int(dut.lock.value) == 1
    assert await tick(dut, 6) == 1, "lock dropped inside the hysteresis band"
    assert await tick(dut, -8) == 1
    assert await tick(dut, 9) == 0, "lock held past the unlock threshold"
    assert await tick(dut, -256) == 0  # most negative error, magnitude 256
    for _ in range(63):
        assert await tick(dut, 0) == 0
    assert await tick(dut, 0) == 1


@cocotb.test()
async def negative_control(dut):
    """Wrong model (lock after 32): must fail."""
    await reset(dut)
    for _ in range(32):
        await tick(dut, 0)
    try:
        assert int(dut.lock.value) == 1, "deliberately-wrong lock count"
    except AssertionError:
        control_failed()
        raise
