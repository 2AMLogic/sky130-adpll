"""adpll_loop_filter: model-checked step response, saturation, hold.

Provisional parameters (Kp = 2^-3, Ki = 2^-9, 9 b err, 24 b integ, 14 b code)
mirror the RTL defaults; the model below restates the same equations
independently of the RTL.
"""

import cocotb
from cocotb.triggers import RisingEdge, Timer

from _common import control_failed, from_signed, start_clock

ERR_W, INT_W, CODE_W, KP, KI = 9, 24, 14, 3, 9
MID, CMAX = 1 << (CODE_W - 1), (1 << CODE_W) - 1
IMAX, IMIN = (1 << (INT_W - 1)) - 1, -(1 << (INT_W - 1))


class Model:
    def __init__(self):
        self.integ, self.code = 0, MID

    def step(self, err):
        raw = MID + (err >> KP) + (self.integ >> KI)
        self.code = min(max(raw, 0), CMAX)
        self.integ = min(max(self.integ + err, IMIN), IMAX)


async def reset(dut):
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.err.value = 0
    start_clock(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def pulse(dut, err):
    dut.err.value = from_signed(err, ERR_W)
    dut.en.value = 1
    await RisingEdge(dut.clk)
    dut.en.value = 0
    await Timer(1, units="ns")


@cocotb.test()
async def test_step_response(dut):
    await reset(dut)
    assert int(dut.code.value) == MID
    m = Model()
    prev = MID
    for err in [100] * 300 + [-50] * 300 + [0] * 5:
        await pulse(dut, err)
        m.step(err)
        assert int(dut.code.value) == m.code, f"code {int(dut.code.value)} != model {m.code}"
    # Positive step then negative step: the integrator must have moved.
    assert m.integ != 0 and m.code != MID


@cocotb.test()
async def test_integrator_saturation(dut):
    await reset(dut)
    for _ in range((IMAX // 255) + 5):
        await pulse(dut, 255)
    assert int(dut.integ.value.signed_integer) == IMAX
    assert int(dut.code.value) == CMAX
    await reset(dut)
    for _ in range((-IMIN // 256) + 5):
        await pulse(dut, -256)
    assert int(dut.integ.value.signed_integer) == IMIN
    assert int(dut.code.value) == 0


@cocotb.test()
async def test_hold_without_en(dut):
    """Held without en the code does not move; err is ignored."""
    await reset(dut)
    await pulse(dut, 40)
    c = int(dut.code.value)
    dut.err.value = from_signed(-200, ERR_W)
    for _ in range(10):
        await RisingEdge(dut.clk)
    assert int(dut.code.value) == c


@cocotb.test()
async def negative_control(dut):
    """Wrong model (Kp = 2^-2): must fail against Kp = 2^-3."""
    await reset(dut)
    await pulse(dut, 64)
    try:
        assert int(dut.code.value) == MID + (64 >> 2), "deliberately-wrong gain"
    except AssertionError:
        control_failed()
        raise
