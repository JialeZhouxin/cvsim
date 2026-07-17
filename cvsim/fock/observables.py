"""Fock observables."""

from __future__ import annotations

import numpy as np

from cvsim.fock.state import FockState


def norm(state: FockState) -> float:
    """∑|c_n|² — truncation deficit shows as norm < 1."""
    return float(np.vdot(state.amps, state.amps).real)


def mean_photon(state: FockState) -> float:
    """⟨n⟩ = ∑ n |c_n|² (unnormalized sum; use with norm for diagnostics)."""
    n = np.arange(state.cutoff)
    return float(np.sum(n * np.abs(state.amps) ** 2))
