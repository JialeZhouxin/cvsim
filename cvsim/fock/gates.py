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
    """Single-mode squeeze S(r) = exp(½(r* a² − r a†²)).

    Real r: S(r) = exp(½ r (a² − a†²)).
    """
    N = state.cutoff
    a = annihilation(N)
    ad = a.conj().T
    # generator G = ½ r (a² − ad²); S = exp(G)
    G = 0.5 * r * (a @ a - ad @ ad)
    U = expm(G)
    return FockState(amps=U @ state.amps)
