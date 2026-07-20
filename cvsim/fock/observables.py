"""Fock observables: norm, ⟨n⟩, PNRD probabilities."""

from __future__ import annotations

import numpy as np

from cvsim.fock.state import FockState


def norm(state: FockState) -> float:
    """∑|c|² — truncation deficit shows as norm < 1."""
    return float(np.vdot(state.amps.ravel(), state.amps.ravel()).real)


def mean_photon(state: FockState, mode: int | None = None) -> float:
    """⟨n⟩ (unnormalized sum over |c|²).

    single-mode: total ⟨n⟩
    two-mode: mode=i → ⟨n_i⟩; mode=None → ⟨n0⟩+⟨n1⟩
    """
    N = state.cutoff
    n = np.arange(N)
    p = np.abs(state.amps) ** 2
    if state.nmode == 1:
        return float(np.sum(n * p))
    # two-mode
    n0 = float(np.sum(n[:, None] * p))
    n1 = float(np.sum(n[None, :] * p))
    if mode is None:
        return n0 + n1
    if mode == 0:
        return n0
    if mode == 1:
        return n1
    raise IndexError(f"mode {mode} out of range for nmode=2")


def pnrd_probs(state: FockState, mode: int | None = None) -> np.ndarray:
    """Photon-number probabilities (not necessarily normalized if truncated).

    single-mode: p[n]
    two-mode: mode=None → joint p[n0,n1]; mode=i → marginal
    """
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
