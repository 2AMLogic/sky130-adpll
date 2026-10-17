"""Smoke test and negative control for the placeholder `counter.v`.

`test_counter_*` must PASS. `negative_control` compares the DUT against a
deliberately wrong reference model and must FAIL: if it passes, the harness
cannot detect a failing DUT and `run_tests.py` reports a runner failure.
The two groups are run as separate simulator invocations by the runner.
"""

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


async def reset(dut):
    dut.rst_n.value = 0
    dut.en.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def count_cycles(dut, n):
    """Enable counting for `n` clock edges, return the DUT count afterwards."""
    dut.en.value = 1
    await ClockCycles(dut.clk, n)
    dut.en.value = 0
    await RisingEdge(dut.clk)
    return int(dut.count.value)


@cocotb.test()
async def test_counter_counts(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)
    assert int(dut.count.value) == 0
    mask = (1 << len(dut.count)) - 1
    got = await count_cycles(dut, 5)
    assert got == 5 & mask, f"got {got}, want 5"


@cocotb.test()
async def test_counter_wraps(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)
    mod = 1 << len(dut.count)
    got = await count_cycles(dut, mod + 3)
    assert got == 3, f"got {got}, want 3 after wrap"


@cocotb.test()
async def negative_control(dut):
    """Wrong model (counts by 2): must fail against a counter that counts by 1."""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset(dut)
    got = await count_cycles(dut, 5)
    try:
        assert got == 10, f"got {got}, deliberately-wrong model wants 10"
    except AssertionError:
        # cocotb's results XML does not carry the exception type; leave a
        # marker so the runner can tell this failure from a crashed test.
        marker = os.environ.get("CONTROL_MARKER")
        if marker:
            with open(marker, "w") as f:
                f.write("assertion\n")
        raise
