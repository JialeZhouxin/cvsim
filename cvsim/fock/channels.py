"""Fock channels: pure loss via Kraus (1-mode, truncated)."""

from __future__ import annotations

import math

import numpy as np

from cvsim.fock.density import FockDensity
from cvsim.fock.state import FockState


def _to_density(state: FockState | FockDensity) -> FockDensity:
    if isinstance(state, FockDensity):
        return state
    if isinstance(state, FockState):
        if state.nmode != 1:
            raise ValueError("fock.loss supports single-mode only")
        return FockDensity.from_pure(state)
    raise TypeError("state must be FockState or FockDensity")


def _kraus_ops(N: int, T: float) -> list[np.ndarray]:
    """E_k |n⟩ = √C(n,k) (√T)^{n-k} (√(1-T))^k |n-k⟩, k=0..N-1."""
    sT = np.sqrt(T)
    sR = np.sqrt(1.0 - T)
    ops: list[np.ndarray] = []
    for k in range(N):
        E = np.zeros((N, N), dtype=complex)
        for n in range(k, N):
            m = n - k
            # C(n,k) = n! / (k! (n-k)!)
            amp = math.sqrt(math.comb(n, k)) * (sT ** m) * (sR ** k)
            E[m, n] = amp
        ops.append(E)
    return ops


def loss(state: FockState | FockDensity, T: float) -> FockDensity:
    """Photon loss with transmissivity T (vacuum environment, 1-mode).

    ρ' = Σ_k E_k ρ E_k† with number-basis Kraus operators.
    Truncation: only photon numbers < cutoff; honesty: boundary error.
    """
    if not 0.0 <= T <= 1.0:
        raise ValueError(f"T must be in [0,1], got {T}")
    dens = _to_density(state)
    N = dens.cutoff
    rho = dens.rho
    out = np.zeros((N, N), dtype=complex)
    for E in _kraus_ops(N, T):
        out += E @ rho @ E.conj().T
    out = 0.5 * (out + out.conj().T)
    return FockDensity(rho=out)
