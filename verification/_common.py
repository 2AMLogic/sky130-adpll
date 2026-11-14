"""Shared helpers for the ADPLL block tests."""

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


def start_clock(sig, period_ns=10):
    cocotb.start_soon(Clock(sig, period_ns, units="ns").start())


def to_signed(v, bits):
    v = int(v)
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def from_signed(v, bits):
    return v & ((1 << bits) - 1)


def control_failed():
    """Leave the marker the runner needs to tell an assertion from a crash."""
    marker = os.environ.get("CONTROL_MARKER")
    if marker:
        with open(marker, "w") as f:
            f.write("assertion\n")


__all__ = ["start_clock", "to_signed", "from_signed", "control_failed",
           "ClockCycles", "RisingEdge"]
