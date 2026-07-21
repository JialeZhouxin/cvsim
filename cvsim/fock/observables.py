"""Fock observables: pure amps + 1-mode density + Homodyne (1-mode)."""

from __future__ import annotations

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


def mean_photon(state: FockLike, mode: int | None = None) -> float:
    """⟨n⟩ from pure |c|² or from diag(ρ)."""
    if _is_density(state):
        if mode is not None and mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        N = state.cutoff
        n = np.arange(N)
        p = np.real(np.diag(state.rho))
        return float(np.sum(n * p))

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
    """Photon-number probabilities from |c|² or diag(ρ)."""
    if _is_density(state):
        if mode is not None and mode != 0:
            raise IndexError(f"mode {mode} out of range for nmode=1")
        return np.asarray(np.real(np.diag(state.rho)), dtype=float)

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
