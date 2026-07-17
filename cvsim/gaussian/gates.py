"""Gaussian gates via affine symplectic maps: V ← S V Sᵀ, r̄ ← S r̄ + d."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState


def apply_symplectic(
    state: GaussianState, S: np.ndarray, d: np.ndarray | None = None
) -> GaussianState:
    """Apply r ↦ S r + d to a Gaussian state. Returns new state."""
    S = np.asarray(S, dtype=float)
    if d is None:
        d = np.zeros(state.rbar.shape[0])
    else:
        d = np.asarray(d, dtype=float)
    V = S @ state.V @ S.T
    rbar = S @ state.rbar + d
    return GaussianState(V=V, rbar=rbar)


def squeeze(state: GaussianState, r: float, mode: int = 0) -> GaussianState:
    """Single-mode squeeze S(r) in xxpp.

    On mode i: x_i → e^{-r} x_i, p_i → e^{r} p_i.
    Notes: vacuum → V = ½ diag(e^{-2r}, e^{2r}) for m=1.
    """
    m = state.nmode
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    S = np.eye(2 * m)
    S[mode, mode] = np.exp(-r)
    S[m + mode, m + mode] = np.exp(r)
    return apply_symplectic(state, S)
