"""Fock observables: pure amps + 1-mode density."""

from __future__ import annotations

import numpy as np

from cvsim.fock.density import FockDensity
from cvsim.fock.state import FockState

FockLike = FockState | FockDensity


def _is_density(state: FockLike) -> bool:
    return isinstance(state, FockDensity)


def norm(state: FockState) -> float:
    """∑|c|² — truncation deficit shows as norm < 1."""
    return float(np.vdot(state.amps.ravel(), state.amps.ravel()).real)


def trace(state: FockDensity) -> float:
    """Tr ρ (should be ~1 if fully contained in cutoff)."""
    return float(np.trace(state.rho).real)


def mean_photon(state: FockLike, mode: int | None = None) -> float:
    """⟨n⟩ from pure |c|² or from diag(ρ)."""
    if _is_density(state):
        if mode is not None and mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        N = state.cutoff
        n = np.arange(N)
        p = np.real(np.diag(state.rho))
        return float(np.sum(n * p))

    N = state.cutoff
    n = np.arange(N)
    p = np.abs(state.amps) ** 2
    if state.nmode == 1:
        return float(np.sum(n * p))
    n0 = float(np.sum(n[:, None] * p))
    n1 = float(np.sum(n[None, :] * p))
    if mode is None:
        return n0 + n1
    if mode == 0:
        return n0
    if mode == 1:
        return n1
    raise IndexError(f"mode {mode} out of range for nmode=2")


def pnrd_probs(state: FockLike, mode: int | None = None) -> np.ndarray:
    """Photon-number probabilities from |c|² or diag(ρ)."""
    if _is_density(state):
        if mode is not None and mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        return np.asarray(np.real(np.diag(state.rho)), dtype=float)

    p = np.abs(state.amps) ** 2
    if state.nmode == 1:
        return np.asarray(p, dtype=float)
    if mode is None:
        return np.asarray(p, dtype=float)
    if mode == 0:
        return np.asarray(p.sum(axis=1), dtype=float)
    if mode == 1:
        return np.asarray(p.sum(axis=0), dtype=float)
    raise IndexError(f"mode {mode} out of range for nmode=2")
