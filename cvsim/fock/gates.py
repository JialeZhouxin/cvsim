"""Fock gates: single-mode D/R/S/Kerr (+mode=); two-mode BS."""

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


def _check_mode(state: FockState, mode: int) -> None:
    if not 0 <= mode < state.nmode:
        raise IndexError(f"mode {mode} out of range for nmode={state.nmode}")


def _apply_1mode_U(state: FockState, U: np.ndarray, mode: int = 0) -> FockState:
    _check_mode(state, mode)
    if state.nmode == 1:
        return FockState(amps=U @ state.amps)
    if mode == 0:
        return FockState(amps=U @ state.amps)
    # mode 1: c'_{n0,m} = Σ_n1 U_{m n1} c_{n0 n1}
    return FockState(amps=state.amps @ U.T)


def _diag_phase(state: FockState, phases: np.ndarray, mode: int = 0) -> FockState:
    """Multiply Fock levels on `mode` by phases[n]."""
    _check_mode(state, mode)
    if state.nmode == 1:
        return FockState(amps=state.amps * phases)
    if mode == 0:
        return FockState(amps=state.amps * phases[:, None])
    return FockState(amps=state.amps * phases[None, :])


def squeeze(state: FockState, r: float, mode: int = 0) -> FockState:
    """Single-mode squeeze S(r) = exp(½ r (a² − a†²)) for real r."""
    N = state.cutoff
    a = annihilation(N)
    ad = a.conj().T
    G = 0.5 * r * (a @ a - ad @ ad)
    return _apply_1mode_U(state, expm(G), mode)


def phase(state: FockState, theta: float, mode: int = 0) -> FockState:
    """Phase shift: |n⟩ → e^{i n θ} |n⟩."""
    n = np.arange(state.cutoff)
    return _diag_phase(state, np.exp(1j * theta * n), mode)


def displace(state: FockState, alpha: complex, mode: int = 0) -> FockState:
    """Displacement D(α) = exp(α a† − α* a)."""
    N = state.cutoff
    a = annihilation(N)
    ad = a.conj().T
    alpha = complex(alpha)
    G = alpha * ad - np.conj(alpha) * a
    return _apply_1mode_U(state, expm(G), mode)


def kerr(state: FockState, chi: float, mode: int = 0) -> FockState:
    """Kerr: |n⟩ → e^{i χ n²} |n⟩."""
    n = np.arange(state.cutoff)
    return _diag_phase(state, np.exp(1j * chi * n * n), mode)


def beamsplitter(state: FockState, theta: float, phi: float = 0.0) -> FockState:
    """Two-mode BS(θ, φ) = exp[θ(e^{iφ} a0† a1 − h.c.)]. Requires nmode==2."""
    if state.nmode != 2:
        raise ValueError("beamsplitter requires two-mode state")
    N = state.cutoff
    a = annihilation(N)
    I = np.eye(N, dtype=complex)
    a0 = np.kron(a, I)
    a1 = np.kron(I, a)
    ad0 = a0.conj().T
    ad1 = a1.conj().T
    eip = np.exp(1j * phi)
    G = theta * (eip * ad0 @ a1 - np.conj(eip) * ad1 @ a0)
    vec = state.amps.reshape(N * N)
    out = expm(G) @ vec
    return FockState(amps=out.reshape(N, N))
