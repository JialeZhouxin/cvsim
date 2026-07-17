"""Fock gates via truncated ladder operators + expm."""

from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from cvsim.fock.state import FockState


def annihilation(cutoff: int) -> np.ndarray:
    """Truncated a: a|n⟩ = √n |n-1⟩, shape (N, N)."""
    a = np.zeros((cutoff, cutoff), dtype=complex)
    for n in range(1, cutoff):
        a[n - 1, n] = np.sqrt(n)
    return a


def squeeze(state: FockState, r: float) -> FockState:
    """Single-mode squeeze S(r) = exp(½ r (a² − a†²)) for real r."""
    N = state.cutoff
    a = annihilation(N)
    ad = a.conj().T
    G = 0.5 * r * (a @ a - ad @ ad)
    return FockState(amps=expm(G) @ state.amps)


def phase(state: FockState, theta: float) -> FockState:
    """Phase shift: |n⟩ → e^{i n θ} |n⟩."""
    n = np.arange(state.cutoff)
    return FockState(amps=state.amps * np.exp(1j * theta * n))


def displace(state: FockState, alpha: complex) -> FockState:
    """Displacement D(α) = exp(α a† − α* a)."""
    N = state.cutoff
    a = annihilation(N)
    ad = a.conj().T
    alpha = complex(alpha)
    G = alpha * ad - np.conj(alpha) * a
    return FockState(amps=expm(G) @ state.amps)
