"""Duty-cycle checks for scripts/oci_keepalive.py.

The script's only job is to hold a CPU fraction, so the bookkeeping is what gets
pinned down: one wall second per cycle, `fraction` of it burned.  Getting that
wrong would quietly change how many 7-day samples clear Oracle's 20% bar, and
nothing would notice until the instance is reclaimed.

The bookkeeping tests run on a fake clock with `burn` stubbed out, so they are
deterministic on a loaded CI box.  That the real `burn` consumes CPU is a
separate, deliberately loose smoke test; the actual duty cycle under a CPUQuota
was measured on the target machine and is recorded in docs/agents/server.md.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location("oci_keepalive", _SCRIPTS / "oci_keepalive.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["oci_keepalive"] = module
    spec.loader.exec_module(module)
    return module


keepalive = _load()


class _FakeClock:
    """Stands in for `time` inside the module under test."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        assert seconds > 0
        self.slept.append(seconds)
        self.now += seconds


def _run_fake(duration: float, fraction: float, monkeypatch) -> tuple[_FakeClock, list[float]]:
    """Run main() on a fake clock; return (clock, burn arguments)."""
    clock = _FakeClock()
    burns: list[float] = []

    def fake_burn(seconds: float) -> None:
        # Pretend the CPU kept up exactly: burning `seconds` costs that much time.
        burns.append(seconds)
        clock.now += seconds

    monkeypatch.setattr(keepalive, "time", clock)
    monkeypatch.setattr(keepalive, "burn", fake_burn)
    assert keepalive.main([sys.argv[0], str(duration), str(fraction)]) == 0
    return clock, burns


def test_each_cycle_is_one_wall_second(monkeypatch) -> None:
    clock, burns = _run_fake(10, 0.5, monkeypatch)
    assert len(burns) == 10
    assert burns == [0.5] * 10
    assert clock.slept == pytest.approx([0.5] * 10)
    assert clock.now == pytest.approx(1000.0 + 10.0)


def test_fraction_shortens_the_sleep_not_the_burn(monkeypatch) -> None:
    _, burns = _run_fake(4, 0.9, monkeypatch)
    assert burns == [0.9] * 4


def test_default_fraction_is_half(monkeypatch) -> None:
    _, burns = _run_fake(2, 0.5, monkeypatch)
    assert burns == [0.5, 0.5]


def test_overshooting_burn_does_not_sleep_a_negative_time(monkeypatch) -> None:
    # A throttled CPU can take longer than the fraction asks for; the cycle must
    # then skip the sleep instead of calling time.sleep() with a negative value.
    clock = _FakeClock()
    monkeypatch.setattr(keepalive, "time", clock)
    monkeypatch.setattr(keepalive, "burn", lambda seconds: setattr(clock, "now", clock.now + 3.0))
    assert keepalive.main([sys.argv[0], "2", "0.5"]) == 0
    assert clock.slept == []


def test_rejects_out_of_range_fraction() -> None:
    for bad in ("0", "-0.5", "1.5"):
        assert keepalive.main([sys.argv[0], "1", bad]) == 2


def test_rejects_missing_duration() -> None:
    assert keepalive.main([sys.argv[0]]) == 2


def test_burn_consumes_cpu() -> None:
    """Smoke test with a loose bound: a busy thread must use real CPU time."""
    before = os.times()
    keepalive.burn(0.3)
    used = (os.times().user + os.times().system) - (before.user + before.system)
    assert used > 0.05


def test_burn_respects_its_deadline() -> None:
    start = time.monotonic()
    keepalive.burn(0.2)
    assert time.monotonic() - start == pytest.approx(0.2, abs=0.2)
