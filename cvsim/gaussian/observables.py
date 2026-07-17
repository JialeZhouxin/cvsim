"""Gaussian observables (no sampling measurements)."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState


def det_cov(state: GaussianState) -> float:
    """det(V). Pure single-mode Gaussian: 1/4."""
    return float(np.linalg.det(state.V))


def mean_photon(state: GaussianState, mode: int | None = None) -> float:
    """Mean photon number ⟨n⟩.

    ħ=1, x=(a+a†)/√2, p=(a-a†)/(i√2):
      ⟨n_i⟩ = ½(⟨x_i²⟩ + ⟨p_i²⟩ − 1)

    If mode is None, return sum over all modes.
    """
    m = state.nmode
    V, r = state.V, state.rbar

    def one(i: int) -> float:
        if not 0 <= i < m:
            raise IndexError(f"mode {i} out of range for nmode={m}")
        # ⟨x²⟩ = V_xx + ⟨x⟩², ⟨p²⟩ = V_pp + ⟨p⟩²
        xx = V[i, i] + r[i] ** 2
        pp = V[m + i, m + i] + r[m + i] ** 2
        return 0.5 * (xx + pp - 1.0)

    if mode is not None:
        return one(mode)
    return sum(one(i) for i in range(m))
