"""Fock gates: single-mode D/R/S/Kerr (+mode=); two-mode BS; 1-mode ρ via UρU†."""

from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from cvsim.fock.density import FockDensity
from cvsim.fock.state import FockState

FockLike1 = FockState | FockDensity


def annihilation(cutoff: int) -> np.ndarray:
    """Truncated a: a|n⟩ = √n |n-1⟩, shape (N, N)."""
    a = np.zeros((cutoff, cutoff), dtype=complex)
    for n in range(1, cutoff):
        a[n - 1, n] = np.sqrt(n)
    return a


def _check_mode_pure(state: FockState, mode: int) -> None:
    if not 0 <= mode < state.nmode:
        raise IndexError(f"mode {mode} out of range for nmode={state.nmode}")


def _apply_1mode_U_pure(state: FockState, U: np.ndarray, mode: int = 0) -> FockState:
    _check_mode_pure(state, mode)
    if state.nmode == 1:
        return FockState(amps=U @ state.amps)
    if mode == 0:
        return FockState(amps=U @ state.amps)
    # mode 1: c'_{n0,m} = Σ_n1 U_{m n1} c_{n0 n1}
    return FockState(amps=state.amps @ U.T)


def _apply_U_density(state: FockDensity, U: np.ndarray) -> FockDensity:
    """ρ' = U ρ U† (1-mode)."""
    rho = U @ state.rho @ U.conj().T
    rho = 0.5 * (rho + rho.conj().T)
    return FockDensity(rho=rho)


def _diag_phase_pure(state: FockState, phases: np.ndarray, mode: int = 0) -> FockState:
    """Multiply Fock levels on `mode` by phases[n]."""
    _check_mode_pure(state, mode)
    if state.nmode == 1:
        return FockState(amps=state.amps * phases)
    if mode == 0:
        return FockState(amps=state.amps * phases[:, None])
    return FockState(amps=state.amps * phases[None, :])


def _squeeze_U(N: int, r: float) -> np.ndarray:
    a = annihilation(N)
    ad = a.conj().T
    G = 0.5 * r * (a @ a - ad @ ad)
    return expm(G)


def _displace_U(N: int, alpha: complex) -> np.ndarray:
    a = annihilation(N)
    ad = a.conj().T
    alpha = complex(alpha)
    G = alpha * ad - np.conj(alpha) * a
    return expm(G)


def squeeze(state: FockLike1, r: float, mode: int = 0) -> FockLike1:
    """Single-mode squeeze S(r) = exp(½ r (a² − a†²)) for real r.

    FockDensity: ρ' = U ρ U† (1-mode only; mode must be 0).
    """
    if isinstance(state, FockDensity):
        if mode != 0:
            raise IndexError("FockDensity is single-mode; mode must be 0")
        return _apply_U_density(state, _squeeze_U(state.cutoff, r))
    return _apply_1mode_U_pure(state, _squeeze_U(state.cutoff, r), mode)


def phase(state: FockLike1, theta: float, mode: int = 0) -> FockLike1:
    """Phase shift: |n⟩ → e^{i n θ} |n⟩."""
    if isinstance(state, FockDensity):
        if mode != 0:
            raise IndexError("FockDensity is single-mode; mode must be 0")
        n = np.arange(state.cutoff)
        phases = np.exp(1j * theta * n)
        U = np.diag(phases)
        return _apply_U_density(state, U)
    n = np.arange(state.cutoff)
    return _diag_phase_pure(state, np.exp(1j * theta * n), mode)


def displace(state: FockLike1, alpha: complex, mode: int = 0) -> FockLike1:
    """Displacement D(α) = exp(α a† − α* a)."""
    if isinstance(state, FockDensity):
        if mode != 0:
            raise IndexError("FockDensity is single-mode; mode must be 0")
        return _apply_U_density(state, _displace_U(state.cutoff, alpha))
    return _apply_1mode_U_pure(state, _displace_U(state.cutoff, alpha), mode)


def kerr(state: FockLike1, chi: float, mode: int = 0) -> FockLike1:
    """Kerr: |n⟩ → e^{i χ n²} |n⟩. Density: UρU† (1-mode)."""
    if isinstance(state, FockDensity):
        if mode != 0:
            raise IndexError("FockDensity is single-mode; mode must be 0")
        n = np.arange(state.cutoff)
        U = np.diag(np.exp(1j * chi * n * n))
        return _apply_U_density(state, U)
    n = np.arange(state.cutoff)
    return _diag_phase_pure(state, np.exp(1j * chi * n * n), mode)


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
