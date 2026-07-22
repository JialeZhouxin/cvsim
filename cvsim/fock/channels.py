"""Fock channels: pure loss via Kraus (1–2 mode, truncated)."""

from __future__ import annotations

import math

import numpy as np

from cvsim.fock.density import FockDensity
from cvsim.fock.state import FockState


def _to_density(state: FockState | FockDensity) -> FockDensity:
    if isinstance(state, FockDensity):
        return state
    if isinstance(state, FockState):
        if state.nmode not in (1, 2):
            raise ValueError("fock.loss supports nmode 1 or 2 only")
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
            amp = math.sqrt(math.comb(n, k)) * (sT**m) * (sR**k)
            E[m, n] = amp
        ops.append(E)
    return ops


def _apply_kraus_1mode(rho: np.ndarray, T: float) -> np.ndarray:
    N = rho.shape[0]
    out = np.zeros((N, N), dtype=complex)
    for E in _kraus_ops(N, T):
        out += E @ rho @ E.conj().T
    return 0.5 * (out + out.conj().T)


def _apply_kraus_2mode_side(rho: np.ndarray, N: int, T: float, mode: int) -> np.ndarray:
    d = N * N
    I = np.eye(N, dtype=complex)
    out = np.zeros((d, d), dtype=complex)
    for E in _kraus_ops(N, T):
        if mode == 0:
            Ef = np.kron(E, I)
        else:
            Ef = np.kron(I, E)
        out += Ef @ rho @ Ef.conj().T
    return 0.5 * (out + out.conj().T)


def loss(
    state: FockState | FockDensity,
    T: float,
    mode: int | None = None,
) -> FockDensity:
    """Photon loss with transmissivity T (vacuum environment).

    1-mode: Kraus on the only mode (mode ignored).
    2-mode: mode=0|1 one-sided; mode=None both modes same T (serial).
    ρ' = Σ E ρ E†. Truncation honesty: boundary error.
    """
    if not 0.0 <= T <= 1.0:
        raise ValueError(f"T must be in [0,1], got {T}")
    dens = _to_density(state)
    m = dens.nmode
    if m == 1:
        out = _apply_kraus_1mode(dens.rho, T)
        return FockDensity(rho=out, nmode=1)

    # m == 2
    if mode is None:
        return loss(loss(dens, T, mode=0), T, mode=1)
    if mode not in (0, 1):
        raise IndexError(f"mode {mode} out of range for nmode=2")
    N = dens.cutoff
    out = _apply_kraus_2mode_side(dens.rho, N, T, mode)
    return FockDensity(rho=out, nmode=2)
