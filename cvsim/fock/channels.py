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
    eye = np.eye(N, dtype=complex)
    out = np.zeros((d, d), dtype=complex)
    for E in _kraus_ops(N, T):
        Ef = np.kron(E, eye) if mode == 0 else np.kron(eye, E)
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


FockLike = FockState | FockDensity


def _to_density(state: FockLike) -> FockDensity:
    if isinstance(state, FockDensity):
        return state
    return FockDensity.from_pure(state)


def phase_noise(state: FockLike, sigma: float, mode: int = 0) -> FockDensity:
    """Phase diffusion: ρ' = ∫ R(φ) ρ R(φ)† p(φ)dφ, φ∼N(0,σ²).

    Closed form: ρ'_{nm} = ρ_{nm}·e^{−σ²(n−m)²/2} (diagonal invariant).
    Output is a density operator (random phase decorrelates).
    """
    if sigma < 0.0:
        raise ValueError(f"sigma must be >= 0, got {sigma}")
    rho = _to_density(state)
    if rho.nmode == 1:
        if mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        return _apply_phase_diffusion(rho, sigma)
    if mode not in (0, 1):
        raise IndexError(f"mode {mode} out of range for nmode=2")
    N = rho.cutoff
    # 2-mode: act on mode `mode` — elementwise mask on the (N²×N²) rho
    n0, n1 = np.meshgrid(np.arange(N), np.arange(N), indexing="ij")
    fock_idx = n0.ravel() * N + n1.ravel()  # row-major |n0 n1⟩
    nn = fock_idx // N if mode == 0 else fock_idx % N
    damp = np.exp(-sigma * sigma / 2.0 * (nn[:, None] - nn[None, :]) ** 2)
    rho2 = rho.rho * damp
    return FockDensity(rho=rho2, nmode=2)


def _apply_phase_diffusion(rho: FockDensity, sigma: float) -> FockDensity:
    n = np.arange(rho.cutoff)
    damp = np.exp(-sigma * sigma / 2.0 * (n[:, None] - n[None, :]) ** 2)
    return FockDensity(rho=rho.rho * damp, nmode=1)


def amplifier(
    state: FockLike, G: float, mode: int = 0, nbar: float = 0.0
) -> FockDensity:
    """Quantum-limited phase-insensitive amplifier (nbar=0).

    Kraus (vacuum environment TMS): A_k|n⟩ = √C(n+k,k)·(√(G−1))^k·G^{−(n+k+1)/2}|n+k⟩.
    Verified: Σ_k A_k†A_k = I (trace-preserving); vacuum → thermal n̄ = G−1.
    Matches Gaussian amplifier(G, nbar=0): X=√G·I₂, Y=(G−1)/2·I₂.
    ``nbar>0``: not implemented (F3 truncation engineering).
    """
    if not G >= 1.0:
        raise ValueError(f"G must be >= 1, got {G}")
    if nbar != 0.0:
        raise NotImplementedError(
            "amplifier nbar>0 not implemented in Fock (F3 truncation engineering)"
        )
    rho = _to_density(state)
    if rho.nmode == 1:
        if mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        return _kraus_sum(rho, _amplify_kraus(rho.cutoff, G))
    if mode not in (0, 1):
        raise IndexError(f"mode {mode} out of range for nmode=2")
    N = rho.cutoff
    eye = np.eye(N, dtype=complex)
    ks = _amplify_kraus(N, G)
    full = [np.kron(a, eye) if mode == 0 else np.kron(eye, a) for a in ks]
    return _kraus_sum(rho, full)


def _amplify_kraus(N: int, G: float) -> list[np.ndarray]:
    """Quantum-limited amplifier Kraus ops A_k (see amplifier docstring).

    k loop stops early once the k-th op is negligible ((√(G−1)/√G)^k < 1e-15);
    column truncation (input n near cutoff) is the same truncation-honest
    boundary as ``loss`` — leakage visible via check_leakage/estimate.
    """
    sG = math.sqrt(G)
    gm1 = math.sqrt(G - 1.0)
    ratio = gm1 / sG  # < 1 for G > 1; A_k norm decays as ratio^k
    ks: list[np.ndarray] = []
    k = 0
    while k < N and (ratio**k) * (sG ** (-1)) > 1e-15:
        ns = np.arange(N - k)
        coef = np.sqrt(np.array([math.comb(n + k, k) for n in ns]))
        ak = np.zeros((N, N), dtype=complex)
        ak[np.arange(k, N), ns] = coef * (gm1**k) * (1.0 / sG) ** (ns + k + 1.0)
        ks.append(ak)
        k += 1
    return ks


def apply_kraus(
    state: FockLike, kraus: list[np.ndarray], mode: int | None = None
) -> FockDensity:
    """Apply a Kraus decomposition ρ' = Σ_k A_k ρ A_k†.

    - 1-mode state: each A_k is (N, N); ``mode`` must be None/0.
    - 2-mode state with ``mode``: (N, N) Kraus on that mode (tensor I).
    - 2-mode state with ``mode=None``: (N², N²) full-space Kraus.
    Validates Σ_k A_k†A_k = I (trace preservation) unless it is a
    post-selection (measurement) channel, in which case pass the
    unnormalized list and renormalize the output.
    """
    rho = _to_density(state)
    N = rho.cutoff
    ks = [np.asarray(a, dtype=complex) for a in kraus]
    if not ks:
        raise ValueError("kraus list must be non-empty")
    if rho.nmode == 1:
        if mode not in (None, 0):
            raise IndexError(f"mode {mode} out of range for nmode=1")
        for a in ks:
            if a.shape != (N, N):
                raise ValueError(f"Kraus must be ({N},{N}) for 1-mode, got {a.shape}")
        return _kraus_sum(rho, ks)
    d = N * N
    if mode is None:
        for a in ks:
            if a.shape != (d, d):
                raise ValueError(f"Kraus must be ({d},{d}) full-space, got {a.shape}")
        return _kraus_sum(rho, ks)
    if mode not in (0, 1):
        raise IndexError(f"mode {mode} out of range for nmode=2")
    eye = np.eye(N, dtype=complex)
    for a in ks:
        if a.shape != (N, N):
            raise ValueError(f"Kraus must be ({N},{N}) for mode application, got {a.shape}")
    full = [np.kron(a, eye) if mode == 0 else np.kron(eye, a) for a in ks]
    return _kraus_sum(rho, full)


def _kraus_sum(rho: FockDensity, ks: list[np.ndarray]) -> FockDensity:
    out = np.zeros_like(rho.rho, dtype=complex)
    for a in ks:
        out += a @ rho.rho @ a.conj().T
    out = 0.5 * (out + out.conj().T)
    return FockDensity(rho=out, nmode=rho.nmode)
