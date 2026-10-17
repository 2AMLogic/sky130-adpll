# DCO and TDC placement constraints — approach

Status: Proposed (part of decision 0001). This records the approach and how it
is checked. Nothing here has been run; the exact `klt` and OpenROAD commands
are open until the first attempt, and every gap found is filed against
`2AMLogic/klayout-tools` as generic tool friction.

## Why

DCO frequency and TDC resolution depend on cell delays and wire loads. A
placement that moves between runs moves those numbers, so the spec rows that
depend on them (2, 3, 6a, 6b, 11) are only valid for a constrained placement.

## Constraint

- The DCO ring cells, its tuning banks, and the TDC delay-line cells are
  grouped; each group is placed in an explicit region (a rectangle in the
  floorplan) with the delay-line cells in a fixed order along one axis, so
  adjacent taps are adjacent cells.
- Mechanism: OpenROAD placement regions/groups, or pre-placed instances with
  FIXED status, driven through `klt`. Which is available and how `klt` expresses
  it is the first thing to find out.
- Routing of the ring and delay-line nets is kept inside the region (no
  detours) where the router allows it.

## Check, not trust

After placement, and again after routing, a script reads the placed design
(DEF/ODB) and fails if any group instance is outside its region, if tap order
differs from the netlist order, or if instance pitch deviates from the
expectation. The check output is stored with the result it supports. A result
whose placement check is missing or failed is not recorded.

## Extraction hand-off (open item O7)

Route: placed-and-routed block → parasitic extraction (SPEF from OpenROAD, or
layout extraction through `klt`) → conversion to an ngspice netlist with the
DCO/TDC cells as SPICE subcircuits and the parasitics annotated → transient.
The path is accepted only after a round trip on a small ring: the frequency
from the extracted netlist must agree with a second extraction route (or hand
estimate) within a stated tolerance, and the gap found is filed as tool
friction if it is awkward.
