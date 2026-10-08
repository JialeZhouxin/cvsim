#!/usr/bin/env python3
"""CPU load generator: keeps an Always Free OCI instance off Oracle's idle list.

Oracle reclaims Always Free instances when, over a 7-day window, CPU 95th
percentile AND network AND (A1 shapes only) memory are all below 20%.  Memory is
not checked on E2.1.Micro and network here is negligible, so CPU is the one bar
to clear.  A duty cycle of 3.5 h/day puts ~15% of the samples above the bar,
which is what a 95th percentile needs.  See docs/agents/server.md.

Each cycle is one wall second: burn ``cpu_fraction`` of it, sleep the rest.
Under a CPUQuota the kernel throttles the burn, so the quota - not this script -
sets the machine's actual load.  It never allocates, so its RSS stays flat.

Usage: oci_keepalive.py <seconds> [cpu_fraction]   # cpu_fraction in (0, 1]
"""

from __future__ import annotations

import sys
import time


def burn(seconds: float) -> None:
    """Spin for `seconds` of wall time without allocating anything."""
    deadline = time.monotonic() + seconds
    x = 0.0
    while time.monotonic() < deadline:
        for i in range(200):
            x += i * i
    if x < 0:  # unreachable; keeps the loop from being optimised away
        print(x, file=sys.stderr)


def main(argv: list[str]) -> int:
    if not 2 <= len(argv) <= 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    duration = float(argv[1])
    fraction = float(argv[2]) if len(argv) == 3 else 0.5
    if not 0.0 < fraction <= 1.0:
        print(f"cpu_fraction must be in (0, 1], got {fraction}", file=sys.stderr)
        return 2

    end = time.monotonic() + duration
    while time.monotonic() < end:
        cycle = time.monotonic()
        burn(fraction)
        rest = 1.0 - (time.monotonic() - cycle)
        if rest > 0:
            time.sleep(rest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
