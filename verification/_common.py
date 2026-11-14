"""Shared helpers for the ADPLL block tests."""

import os

import cocotb
from cocotb.clock import Clock


def start_clock(sig, period_ns=10):
    cocotb.start_soon(Clock(sig, period_ns, units="ns").start())


def from_signed(v, bits):
    return v & ((1 << bits) - 1)


def control_failed():
    """Leave the marker the runner needs to tell an assertion from a crash."""
    marker = os.environ.get("CONTROL_MARKER")
    if marker:
        with open(marker, "w") as f:
            f.write("assertion\n")
