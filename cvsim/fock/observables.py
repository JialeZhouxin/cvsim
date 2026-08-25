"""Fock observables: pure amps + 1-mode density + Homodyne (1-mode)."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy.special import eval_hermite, factorial

from cvsim.fock.density import FockDensity
from cvsim.fock.gates import annihilation
from cvsim.fock.state import FockState

FockLike = FockState | FockDensity

_EPS = 1e-14
_SAMPLE_L = 8.0
_SAMPLE_N = 513


def _is_density(state: FockLike) -> bool:
    return isinstance(state, FockDensity)


def _require_1mode_homodyne(state: FockLike, mode: int) -> None:
    if mode != 0:
        raise IndexError("fock homodyne: single-mode only; mode must be 0")
    if isinstance(state, FockState) and state.nmode != 1:
        raise ValueError("fock homodyne: single-mode only")
    if isinstance(state, FockDensity) and state.nmode != 1:
        raise ValueError("fock homodyne: single-mode only")


def norm(state: FockState) -> float:
    """∑|c|² — truncation deficit shows as norm < 1."""
    return float(np.vdot(state.amps.ravel(), state.amps.ravel()).real)


def trace(state: FockDensity) -> float:
    """Tr ρ (should be ~1 if fully contained in cutoff)."""
    return float(np.trace(state.rho).real)


def _dens_joint_pn(state: FockDensity) -> np.ndarray:
    """Joint P(n0,n1) for 2-mode dens, shape (N,N); 1-mode returns (N,)."""
    p = np.asarray(np.real(np.diag(state.rho)), dtype=float)
    if state.nmode == 1:
        return p
    N = state.cutoff
    return p.reshape(N, N)


def mean_photon(state: FockLike, mode: int | None = None) -> float:
    """⟨n⟩ from pure |c|² or from diag(ρ)."""
    if _is_density(state):
        if state.nmode == 1:
            if mode is not None and mode != 0:
                raise IndexError(f"mode {mode} out of range for nmode=1")
            N = state.cutoff
            n = np.arange(N)
            p = np.real(np.diag(state.rho))
            return float(np.sum(n * p))
        # 2-mode dens
        N = state.cutoff
        n = np.arange(N)
        p2 = _dens_joint_pn(state)
        n0 = float(np.sum(n[:, None] * p2))
        n1 = float(np.sum(n[None, :] * p2))
        if mode is None:
            return n0 + n1
        if mode == 0:
            return n0
        if mode == 1:
            return n1
        raise IndexError(f"mode {mode} out of range for nmode=2")

    N = state.cutoff
    n = np.arange(N)
    p = np.abs(state.amps) ** 2
    if state.nmode == 1:
        return float(np.sum(n * p))
    n0 = float(np.sum(n[:, None] * p))
    n1 = float(np.sum(n[None, :] * p))
    if mode is None:
        return n0 + n1
    if mode == 0:
        return n0
    if mode == 1:
        return n1
    raise IndexError(f"mode {mode} out of range for nmode=2")


def pnrd_probs(state: FockLike, mode: int | None = None) -> np.ndarray:
    """Photon-number probabilities from |c|² or diag(ρ).

    2-mode dens: mode=None → joint (N,N); mode=0|1 → marginal (N,).

    Gaussian-state counterpart (joint P(n) via thewalrus):
    ``cvsim.gaussian.pnr_probs``.
    """
    if _is_density(state):
        if state.nmode == 1:
            if mode is not None and mode != 0:
                raise IndexError(f"mode {mode} out of range for nmode=1")
            return np.asarray(np.real(np.diag(state.rho)), dtype=float)
        p2 = _dens_joint_pn(state)
        if mode is None:
            return p2
        if mode == 0:
            return np.asarray(p2.sum(axis=1), dtype=float)
        if mode == 1:
            return np.asarray(p2.sum(axis=0), dtype=float)
        raise IndexError(f"mode {mode} out of range for nmode=2")

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


def _expect_a_ops(state: FockLike) -> tuple[complex, float, complex]:
    """Return (⟨a⟩, ⟨a†a⟩, ⟨a²⟩) for 1-mode pure or density."""
    N = state.cutoff
    a = annihilation(N)
    ad = a.conj().T
    if isinstance(state, FockDensity):
        rho = state.rho
        ea = complex(np.trace(rho @ a))
        n = float(np.trace(rho @ (ad @ a)).real)
        a2 = complex(np.trace(rho @ (a @ a)))
        return ea, n, a2
    psi = state.amps
    ea = complex(np.vdot(psi, a @ psi))
    n = float(np.vdot(psi, ad @ a @ psi).real)
    a2 = complex(np.vdot(psi, a @ a @ psi))
    return ea, n, a2


def homodyne_mean(state: FockLike, mode: int = 0, phi: float = 0.0) -> float:
    """Edge mean ⟨x_φ⟩, x_φ = x cosφ + p sinφ (ħ=1). 1-mode only."""
    _require_1mode_homodyne(state, mode)
    ea, _, _ = _expect_a_ops(state)
    mx = np.sqrt(2.0) * ea.real
    mp = np.sqrt(2.0) * ea.imag
    return float(mx * np.cos(phi) + mp * np.sin(phi))


def homodyne_var(state: FockLike, mode: int = 0, phi: float = 0.0) -> float:
    """Edge variance Var(x_φ) (ħ=1). 1-mode only."""
    _require_1mode_homodyne(state, mode)
    ea, n_op, a2 = _expect_a_ops(state)
    mx = np.sqrt(2.0) * ea.real
    mp = np.sqrt(2.0) * ea.imag
    # ⟨x²⟩ = ⟨n⟩ + 1/2 + Re⟨a²⟩; ⟨p²⟩ = ⟨n⟩ + 1/2 − Re⟨a²⟩
    x2 = n_op + 0.5 + a2.real
    p2 = n_op + 0.5 - a2.real
    # ⟨{x,p}/2⟩ = Im⟨a²⟩
    xp_sym = a2.imag
    c, s = np.cos(phi), np.sin(phi)
    mu = mx * c + mp * s
    xphi2 = c * c * x2 + s * s * p2 + 2.0 * s * c * xp_sym
    return float(xphi2 - mu * mu)


def _ho_basis_x(N: int, x: np.ndarray) -> np.ndarray:
    """ψ_n(x) rows n=0..N-1; ħ=m=ω=1, ⟨x²⟩_vac=1/2."""
    x = np.asarray(x, dtype=float)
    out = np.empty((N, x.size), dtype=float)
    g = np.exp(-0.5 * x * x) * (np.pi**-0.25)
    for n in range(N):
        H = eval_hermite(n, x)
        out[n] = g * H / np.sqrt((2.0**n) * factorial(n))
    return out


def _amps_for_phi(amps: np.ndarray, phi: float) -> np.ndarray:
    """Rotate so that measuring x is measuring x_φ: |n⟩ → e^{-i n φ}|n⟩."""
    n = np.arange(amps.size)
    return amps * np.exp(-1j * phi * n)


def _pdf_from_amps(amps: np.ndarray, qs: np.ndarray) -> np.ndarray:
    basis = _ho_basis_x(len(amps), qs)
    psi_x = basis.T @ amps  # (nq,)
    pdf = np.abs(psi_x) ** 2
    pdf = np.maximum(pdf.real, 0.0)
    s = pdf.sum()
    if s <= _EPS:
        raise ValueError("homodyne_sample: PDF sum ~ 0")
    return pdf / s


def homodyne_sample(
    state: FockLike,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    lim: float = _SAMPLE_L,
    n_grid: int = _SAMPLE_N,
) -> float:
    """Sample Homodyne outcome on discrete x_φ grid (teaching approx).

    Pure: HO wavefunction PDF. Density: spectral mixture of pure PDFs.
    Does not condition. 1-mode only.
    """
    _require_1mode_homodyne(state, mode)
    if rng is None:
        rng = np.random.default_rng()
    if n_grid < 3:
        raise ValueError("n_grid must be >= 3")
    qs = np.linspace(-lim, lim, n_grid)

    if isinstance(state, FockState):
        amps = _amps_for_phi(state.amps, phi)
        # renorm soft truncation
        nm = np.linalg.norm(amps)
        if nm <= _EPS:
            raise ValueError("homodyne_sample: zero state")
        amps = amps / nm
        pdf = _pdf_from_amps(amps, qs)
    else:
        # mixture over eigenstates of ρ
        w, v = np.linalg.eigh(state.rho)
        w = np.maximum(w.real, 0.0)
        sw = w.sum()
        if sw <= _EPS:
            raise ValueError("homodyne_sample: zero density")
        w = w / sw
        pdf = np.zeros(n_grid, dtype=float)
        for i, wi in enumerate(w):
            if wi < 1e-14:
                continue
            amps = _amps_for_phi(v[:, i], phi)
            nm = np.linalg.norm(amps)
            if nm <= _EPS:
                continue
            pdf += wi * _pdf_from_amps(amps / nm, qs)
        s = pdf.sum()
        if s <= _EPS:
            raise ValueError("homodyne_sample: PDF sum ~ 0")
        pdf /= s

    idx = int(rng.choice(n_grid, p=pdf))
    return float(qs[idx])


def _x_phi_matrix(cutoff: int, phi: float) -> np.ndarray:
    """Truncated x_φ = x cosφ + p sinφ = (a e^{-iφ} + a† e^{iφ})/√2."""
    a = annihilation(cutoff)
    ad = a.conj().T
    eip = np.exp(-1j * phi)
    return (eip * a + np.conj(eip) * ad) / np.sqrt(2.0)


def _x_eigen_amps(cutoff: int, outcome: float, phi: float) -> np.ndarray:
    """Eigenvector of truncated x_φ nearest to outcome (projective, finite N).

    Discrete spectrum of cutoff X; exact eigenstate ⇒ ⟨x_φ⟩=λ, var_φ≈0 in
    truncated space. Not continuous Dirac |x⟩; not Gaussian Kalman.
    """
    X = _x_phi_matrix(cutoff, phi)
    # Hermitian numerically: eigh wants Hermitian matrix
    Xh = 0.5 * (X + X.conj().T)
    evals, evecs = np.linalg.eigh(Xh)
    idx = int(np.argmin(np.abs(evals - float(outcome))))
    amps = evecs[:, idx].astype(complex)
    # global phase: make first large component real-positive
    k = int(np.argmax(np.abs(amps)))
    if abs(amps[k]) > _EPS:
        amps = amps * np.exp(-1j * np.angle(amps[k]))
    return amps


def homodyne_condition(
    state: FockLike,
    mode: int = 0,
    phi: float = 0.0,
    outcome: float = 0.0,
) -> FockState:
    """Projective Homodyne condition → truncated x_φ eigenstate near outcome.

    1-mode only. Post-state independent of prior amps/ρ (projective);
    uses state.cutoff only. Not Gaussian Kalman. Returns pure FockState.
    """
    _require_1mode_homodyne(state, mode)
    amps = _x_eigen_amps(state.cutoff, outcome, phi)
    return FockState(amps=amps)


def homodyne_sample_and_condition(
    state: FockLike,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    lim: float = _SAMPLE_L,
    n_grid: int = _SAMPLE_N,
) -> tuple[float, FockState]:
    """Sample Homodyne outcome then condition. Thin combo; no new physics."""
    o = homodyne_sample(state, mode, phi, rng=rng, lim=lim, n_grid=n_grid)
    return o, homodyne_condition(state, mode, phi, o)


# -- PNR measurement (vision §4 F2) ----------------------------------------


def pnr_sample(
    state: FockLike, mode: int = 0, *, rng: np.random.Generator | None = None
) -> int:
    """Sample a photon-number outcome from p_n = ⟨n|ρ|n⟩ (marginal on `mode`)."""
    p = pnrd_probs(state, mode)
    if rng is None:
        rng = np.random.default_rng()
    return int(rng.choice(p.size, p=p))


def pnr_sample_batch(
    state: FockLike,
    mode: int = 0,
    size: int = 1000,
    *,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Vectorized batch of :func:`pnr_sample` — ``size`` i.i.d. outcomes in one call.

    Same Born-rule marginal as the single-shot path (shared ``pnrd_probs``),
    so 10³ shots cost one multinomial draw (F3 vision §4.3).
    """
    p = pnrd_probs(state, mode)
    if rng is None:
        rng = np.random.default_rng()
    return rng.choice(p.size, p=p, size=size)


def pnr_condition(state: FockLike, mode: int = 0, n: int = 0) -> FockState | FockDensity:
    """Posterior after photon-number outcome `n` on `mode` (Born rule).

    - 1-mode pure: posterior |n⟩ (projective, independent of prior).
    - 1-mode density: |n⟩⟨n|.
    - 2-mode pure: remaining mode conditioned on ⟨n|: ψ'[k] ∝ ψ[n,k] (mode 0)
      or ψ[k,n] (mode 1).
    - 2-mode density: (P⊗I)ρ(P⊗I)†/p with P=|n⟩⟨n|.
    Outcome with zero probability → ValueError (honest, no silent renormalize).
    """
    if isinstance(state, FockDensity):
        return _pnr_condition_density(state, mode, n)
    return _pnr_condition_pure(state, mode, n)


def _pnr_condition_pure(state: FockState, mode: int, n: int) -> FockState:
    N = state.cutoff
    if not 0 <= n < N:
        raise IndexError(f"n={n} out of range for cutoff={N}")
    if state.nmode == 1:
        if mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        p = abs(state.amps[n]) ** 2
        if p <= _EPS:
            raise ValueError(f"pnr_condition: outcome n={n} has zero probability")
        amps = np.zeros(N, dtype=complex)
        amps[n] = 1.0
        return FockState(amps=amps)
    if mode not in (0, 1):
        raise IndexError(f"mode {mode} out of range for nmode=2")
    vec = state.amps[n, :].copy() if mode == 0 else state.amps[:, n].copy()
    p = np.sum(abs(vec) ** 2)
    if p <= _EPS:
        raise ValueError(f"pnr_condition: outcome n={n} has zero probability")
    return FockState(amps=vec / np.sqrt(p))


def _pnr_condition_density(state: FockDensity, mode: int, n: int) -> FockDensity:
    N = state.cutoff
    if not 0 <= n < N:
        raise IndexError(f"n={n} out of range for cutoff={N}")
    if state.nmode == 1:
        if mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        p = np.real(state.rho[n, n])
        if p <= _EPS:
            raise ValueError(f"pnr_condition: outcome n={n} has zero probability")
        rho = np.zeros((N, N), dtype=complex)
        rho[n, n] = 1.0
        return FockDensity(rho=rho, nmode=1)
    if mode not in (0, 1):
        raise IndexError(f"mode {mode} out of range for nmode=2")
    P = np.zeros((N, N), dtype=complex)
    P[n, n] = 1.0
    eye = np.eye(N, dtype=complex)
    A = np.kron(P, eye) if mode == 0 else np.kron(eye, P)
    rho2 = A @ state.rho @ A.conj().T
    p = np.real(np.trace(rho2))
    if p <= _EPS:
        raise ValueError(f"pnr_condition: outcome n={n} has zero probability")
    return FockDensity(rho=rho2 / p, nmode=2)


def pnr_sample_and_condition(
    state: FockLike, mode: int = 0, *, rng: np.random.Generator | None = None
) -> tuple[int, FockState | FockDensity]:
    """Sample a photon number then condition. Thin combo."""
    n = pnr_sample(state, mode, rng=rng)
    return n, pnr_condition(state, mode, n)


# -- heterodyne measurement (vision §4 F2) ----------------------------------


@lru_cache(maxsize=8)
def _coherent_overlap_matrix(N: int, betas_key: tuple[complex, ...]) -> np.ndarray:
    """v_n(β) = ⟨n|β⟩ = e^{−|β|²/2}·β^n/√n! — rows n, columns β (recurrence).

    Cached on the beta tuple; grid samples reuse the same matrix."""
    betas = np.asarray(betas_key, dtype=complex)
    v = np.empty((N, betas.size), dtype=complex)
    v[0] = np.exp(-0.5 * np.abs(betas) ** 2)
    for n in range(1, N):
        v[n] = v[n - 1] * betas / np.sqrt(n)
    return v


def _marginal_density(state: FockLike, mode: int) -> np.ndarray:
    """Reduced density matrix of `mode` (N×N) from pure 2-mode or density."""
    N = state.cutoff
    if isinstance(state, FockDensity):
        if state.nmode == 1:
            if mode != 0:
                raise IndexError(f"mode {mode} out of range for nmode=1")
            return state.rho
        rho4 = state.rho.reshape(N, N, N, N)
        if mode == 0:
            return np.einsum("abcb->ac", rho4)
        return np.einsum("abad->bd", rho4)
    if state.nmode == 1:
        if mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        return np.outer(state.amps, state.amps.conj())
    if mode == 0:
        return np.einsum("ab,cb->ac", state.amps, state.amps.conj())
    return np.einsum("ab,ac->bc", state.amps, state.amps.conj())


def _q_function(state: FockLike, mode: int, betas: np.ndarray) -> np.ndarray:
    """Q(β) = ⟨β|ρ_m|β⟩ on the marginal density of `mode` (vectorized)."""
    rho = _marginal_density(state, mode)
    V = _coherent_overlap_matrix(state.cutoff, tuple(betas))
    return np.real(np.einsum("ng,nm,mg->g", V.conj(), rho, V))


def heterodyne_sample(
    state: FockLike,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
    lim: float = _SAMPLE_L,
    n_grid: int = 129,
) -> complex:
    """Sample a heterodyne outcome β from Q(β) ∝ ⟨β|ρ|β⟩ on the discrete
    (x,p) grid (teaching approx, same style as homodyne_sample)."""
    if rng is None:
        rng = np.random.default_rng()
    if n_grid < 3:
        raise ValueError("n_grid must be >= 3")
    xs = np.linspace(-lim, lim, n_grid)
    betas = (xs[None, :] + 1j * xs[:, None]).ravel()
    q = _q_function(state, mode, betas)
    q = np.maximum(q, 0.0)
    s = q.sum()
    if s <= _EPS:
        raise ValueError("heterodyne_sample: Q-sum ~ 0 (zero state?)")
    i = rng.choice(q.size, p=q / s)
    return complex(betas[i])


def heterodyne_condition(
    state: FockLike, mode: int = 0, beta: complex = 0.0
) -> FockState | FockDensity:
    """Posterior after heterodyne outcome β (coherent POVM |β⟩⟨β|/π).

    Rank-1 POVM: 1-mode posterior is always the coherent state |β⟩
    (independent of prior). 2-mode: remaining mode conditioned on ⟨β|.
    """
    beta = complex(beta)
    N = state.cutoff
    if isinstance(state, FockDensity):
        if state.nmode == 1:
            if mode != 0:
                raise IndexError(f"mode {mode} out of range for nmode=1")
            return FockDensity.from_pure(FockState.coherent(N, beta))
        if mode not in (0, 1):
            raise IndexError(f"mode {mode} out of range for nmode=2")
        v = _coherent_overlap_matrix(N, (beta,))[:, 0]
        A = np.kron(np.outer(v, v.conj()), np.eye(N)) if mode == 0 else \
            np.kron(np.eye(N), np.outer(v, v.conj()))
        rho2 = A @ state.rho @ A.conj().T
        p = np.real(np.trace(rho2))
        if p <= _EPS:
            raise ValueError(f"heterodyne_condition: outcome β={beta} has ~zero probability")
        return FockDensity(rho=rho2 / p, nmode=2)
    if state.nmode == 1:
        if mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        return FockState.coherent(N, beta)
    if mode not in (0, 1):
        raise IndexError(f"mode {mode} out of range for nmode=2")
    v = _coherent_overlap_matrix(N, (beta,))[:, 0]
    if mode == 0:
        vec = np.sum(state.amps * np.conj(v)[:, None], axis=0)  # Σ_n ψ[n,k] conj(v_n)
    else:
        vec = np.sum(state.amps * np.conj(v)[None, :], axis=1)
    p = np.sum(abs(vec) ** 2)
    if p <= _EPS:
        raise ValueError(f"heterodyne_condition: outcome β={beta} has ~zero probability")
    return FockState(amps=vec / np.sqrt(p))


def heterodyne_sample_and_condition(
    state: FockLike,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
) -> tuple[complex, FockState | FockDensity]:
    """Sample a heterodyne outcome then condition. Thin combo."""
    b = heterodyne_sample(state, mode, rng=rng)
    return b, heterodyne_condition(state, mode, b)
