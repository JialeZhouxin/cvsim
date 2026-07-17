"""Bosonic weight checks."""

from __future__ import annotations

from cvsim.bosonic.state import BosonicState


def weight_sum(state: BosonicState) -> complex:
    """∑ w_k — should be 1 for a normalized density-operator decomposition."""
    return sum(c.w for c in state.components)
