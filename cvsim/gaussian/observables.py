"""Gaussian observables: Homodyne + Heterodyne (sample / condition)."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState

_EPS = 1e-14


def det_cov(state: GaussianState) -> float:
    """det(V). Pure single-mode Gaussian: 1/4."""
    return float(np.linalg.det(state.V))


def _check_mode(state: GaussianState, mode: int) -> int:
    m = state.nmode
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    return m


def _homodyne_u(nmode: int, mode: int, phi: float) -> np.ndarray:
    u = np.zeros(2 * nmode, dtype=float)
    u[mode] = np.cos(phi)
    u[nmode + mode] = np.sin(phi)
    return u


def homodyne_mean(state: GaussianState, mode: int = 0, phi: float = 0.0) -> float:
    """Edge mean ⟨x_φ⟩, x_φ = x cosφ + p sinφ (xxpp, ħ=1)."""
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    return float(u @ state.rbar)


def homodyne_var(state: GaussianState, mode: int = 0, phi: float = 0.0) -> float:
    """Edge variance Var(x_φ) = uᵀ V u (central; independent of r̄)."""
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    return float(u @ state.V @ u)


def homodyne_sample(
    state: GaussianState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
) -> float:
    """Sample outcome from ideal Homodyne edge N(μ, σ²). Does not condition."""
    if rng is None:
        rng = np.random.default_rng()
    mu = homodyne_mean(state, mode, phi)
    var = homodyne_var(state, mode, phi)
    if var <= _EPS:
        raise ValueError(f"homodyne variance too small: σ²={var}")
    return float(rng.normal(mu, np.sqrt(var)))


def homodyne_condition(
    state: GaussianState,
    mode: int,
    phi: float,
    outcome: float,
) -> GaussianState:
    """Ideal Homodyne condition (no mode delete; V singular on u).

    V' = V - vvᵀ/σ,  r̄' = r̄ + v (outcome-μ)/σ,  v=Vu, σ=uᵀVu, μ=u·r̄.
    """
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    V = state.V
    r = state.rbar
    v = V @ u
    sigma = float(u @ v)
    if sigma <= _EPS:
        raise ValueError(f"homodyne variance too small: σ={sigma}")
    mu = float(u @ r)
    Vn = V - np.outer(v, v) / sigma
    rn = r + v * ((outcome - mu) / sigma)
    # symmetrize float noise
    Vn = 0.5 * (Vn + Vn.T)
    return GaussianState(V=Vn, rbar=rn)


def homodyne_sample_and_condition(
    state: GaussianState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
) -> tuple[float, GaussianState]:
    """Sample Homodyne outcome then condition. Thin combo; no new physics."""
    o = homodyne_sample(state, mode, phi, rng=rng)
    return o, homodyne_condition(state, mode, phi, o)


def _xp_indices(nmode: int, mode: int) -> list[int]:
    """xxpp indices of (x_k, p_k) for logical mode k."""
    return [mode, nmode + mode]


def _as_beta(outcome: complex | float | np.ndarray) -> complex:
    """Normalize heterodyne outcome to complex β."""
    if isinstance(outcome, np.ndarray):
        if outcome.shape != (2,):
            raise ValueError(
                f"heterodyne real outcome must be shape (2,) [x,p], got {outcome.shape}"
            )
        return complex((outcome[0] + 1j * outcome[1]) / np.sqrt(2.0))
    return complex(outcome)


def _beta_to_xp(beta: complex) -> np.ndarray:
    """Map β → (x, p) with x = √2 Re β, p = √2 Im β (ħ=1)."""
    b = complex(beta)
    return np.array([np.sqrt(2.0) * b.real, np.sqrt(2.0) * b.imag], dtype=float)


def heterodyne_mean(state: GaussianState, mode: int = 0) -> complex:
    """Expected heterodyne outcome ⟨β⟩ = (⟨x⟩ + i⟨p⟩)/√2 on ``mode``.

    Matches coherent-state labelling: a coherent |α⟩ has ⟨β⟩ = α.
    """
    m = _check_mode(state, mode)
    ix, ip = _xp_indices(m, mode)
    return complex((state.rbar[ix] + 1j * state.rbar[ip]) / np.sqrt(2.0))


def heterodyne_cov_xp(state: GaussianState, mode: int = 0) -> np.ndarray:
    """2×2 outcome covariance of (x, p) for heterodyne on ``mode``.

    POVM |β⟩⟨β|/π (Husimi): Gaussian states give

        Σ = V_{xp,xp} + I₂/2

    (ħ=1, vacuum block I/2 → vacuum outcomes have Σ = I).
    """
    m = _check_mode(state, mode)
    idx = _xp_indices(m, mode)
    Vblk = np.asarray(state.V, dtype=float)[np.ix_(idx, idx)]
    Vblk = 0.5 * (Vblk + Vblk.T)
    return Vblk + 0.5 * np.eye(2)


def _heterodyne_params(
    state: GaussianState, mode: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """(mu, Sigma) of the heterodyne outcome edge N(r̄_xp, V_xp + I/2).
    Shared by single-shot and batch samplers (no formula drift)."""
    m = _check_mode(state, mode)
    idx = _xp_indices(m, mode)
    mu = np.asarray(state.rbar, dtype=float)[idx]
    Sigma = heterodyne_cov_xp(state, mode)
    # PSD guard for float noise
    Sigma = 0.5 * (Sigma + Sigma.T)
    w = np.linalg.eigvalsh(Sigma)
    if np.min(w) <= _EPS:
        raise ValueError(
            f"heterodyne outcome covariance not PD: min eig={float(np.min(w))}"
        )
    return mu, Sigma


def heterodyne_sample(
    state: GaussianState,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
) -> complex:
    """Sample heterodyne outcome β without conditioning.

    Draws (x, p) ~ N(r̄_xp, V_xp + I/2), returns β = (x + i p)/√2.
    """
    if rng is None:
        rng = np.random.default_rng()
    mu, Sigma = _heterodyne_params(state, mode)
    z = rng.multivariate_normal(mu, Sigma)
    return complex((z[0] + 1j * z[1]) / np.sqrt(2.0))


def heterodyne_condition(
    state: GaussianState,
    mode: int,
    outcome: complex | float | np.ndarray,
) -> GaussianState:
    """Condition on heterodyne outcome and **remove** the measured mode.

    Dual-quadrature POVM |β⟩⟨β|/π completely measures one mode. Unlike
    ``homodyne_condition`` (which leaves a singular mode in place), the
    returned state lives on ``nmode-1`` modes.

    Let A = measured mode, B = the rest, Σ_A = V_A + I/2, C = cov(B,A)
    (rows B, cols A). With outcome z = (x, p) from β:

        V_B' = V_B - C Σ_A^{-1} Cᵀ
        r̄_B' = r̄_B + C Σ_A^{-1} (z - r̄_A)

    Math: vision §4 F-MEASURE-FULL; Weedbrook RMP §III.B (heterodyne).
    """
    m = _check_mode(state, mode)
    beta = _as_beta(outcome)
    z = _beta_to_xp(beta)

    V = 0.5 * (
        np.asarray(state.V, dtype=float) + np.asarray(state.V, dtype=float).T
    )
    r = np.asarray(state.rbar, dtype=float).copy()
    idx_A = _xp_indices(m, mode)
    idx_B = [i for i in range(2 * m) if i not in idx_A]

    # Single-mode state: measurement leaves vacuum-on-nothing → nmode=0
    if not idx_B:
        return GaussianState(V=np.zeros((0, 0)), rbar=np.zeros(0))

    VA = V[np.ix_(idx_A, idx_A)]
    VB = V[np.ix_(idx_B, idx_B)]
    # C = cov(B, A): shape (2m-2, 2)
    C = V[np.ix_(idx_B, idx_A)]
    rA = r[idx_A]
    rB = r[idx_B]

    Sigma = VA + 0.5 * np.eye(2)
    Sigma = 0.5 * (Sigma + Sigma.T)
    try:
        invS = np.linalg.inv(Sigma)
    except np.linalg.LinAlgError as exc:
        raise ValueError("heterodyne Σ_A = V_A + I/2 is singular") from exc

    innov = z - rA
    VB_n = VB - C @ invS @ C.T
    rB_n = rB + C @ invS @ innov
    VB_n = 0.5 * (VB_n + VB_n.T)

    # Reorder B indices back to xxpp on the reduced mode set.
    # idx_B lists remaining axes in original xxpp order: all x's then all p's
    # of surviving modes, but *not* packed as xxpp for nmode-1 yet.
    # Example nmode=2 measure 0: idx_B = [1, 3] (x1, p1) — already xxpp for 1 mode.
    # Example nmode=3 measure 1: idx_B = [0, 2, 3, 5] (x0,x2,p0,p2) — need pack
    # → [x0,x2,p0,p2] is already xxpp for modes sorted [0,2]. Good if we keep
    # mode order sorted by original index.
    keep_modes = sorted(i for i in range(m) if i != mode)
    # Build packed order: xs of keep_modes then ps of keep_modes
    pack = []
    for k in keep_modes:
        pack.append(k)  # x_k original index
    for k in keep_modes:
        pack.append(m + k)  # p_k original index
    # Map original axis → position in idx_B slice
    pos = {ax: j for j, ax in enumerate(idx_B)}
    perm = [pos[ax] for ax in pack]
    VB_n = VB_n[np.ix_(perm, perm)]
    rB_n = rB_n[perm]
    return GaussianState(V=VB_n, rbar=rB_n)


def heterodyne_sample_and_condition(
    state: GaussianState,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
) -> tuple[complex, GaussianState]:
    """Sample heterodyne β then condition (measured mode removed)."""
    beta = heterodyne_sample(state, mode, rng=rng)
    return beta, heterodyne_condition(state, mode, beta)


def mean_photon(state: GaussianState, mode: int | None = None) -> float:
    """Mean photon number ⟨n⟩.

    ħ=1, x=(a+a†)/√2, p=(a-a†)/(i√2):
      ⟨n_i⟩ = ½(⟨x_i²⟩ + ⟨p_i²⟩ − 1)

    If mode is None, return sum over all modes.
    """
    m = state.nmode
    V, r = state.V, state.rbar

    def one(i: int) -> float:
        _check_mode(state, i)
        # ⟨x²⟩ = V_xx + ⟨x⟩², ⟨p²⟩ = V_pp + ⟨p⟩²
        xx = V[i, i] + r[i] ** 2
        pp = V[m + i, m + i] + r[m + i] ** 2
        return 0.5 * (xx + pp - 1.0)

    if mode is not None:
        return one(mode)
    return sum(one(i) for i in range(m))


# ── F-SAMPLE batch (vision §4.2): vectorized size=10³ standard ──────────────

def _vacuum_probability(V: np.ndarray, rbar: np.ndarray, mode: int) -> float:
    """P(0) of a Gaussian state on one mode — same formula as
    ``cvsim.bridge.vacuum_probability`` (kept in lock by
    ``test_threshold`` / ``test_bridge`` cross-checks; xxpp, ħ=1).
    """
    V = np.asarray(V, dtype=float)
    rbar = np.asarray(rbar, dtype=float)
    m = V.shape[0] // 2
    i = mode
    # xxpp: mode-i block is (V[i,i], V[i,m+i]; V[m+i,i], V[m+i,m+i])
    V1 = np.array([[V[i, i], V[i, m + i]], [V[m + i, i], V[m + i, m + i]]])
    r1 = np.array([rbar[i], rbar[m + i]])
    A = V1 + 0.5 * np.eye(2)
    if np.linalg.eigvalsh(A).min() <= 0.0:
        raise ValueError(f"V+½I on mode {mode} is not positive-definite")
    exponent = -0.5 * float(r1 @ np.linalg.solve(A, r1))
    return float(np.exp(exponent) / np.sqrt(np.linalg.det(A)))


def p_click(state: GaussianState, mode: int = 0) -> float:
    """Threshold (on/off) click probability p = 1 − ⟨0|ρ|0⟩.

    **Outcome-only** (grill 2026-08-10): sampling returns {0,1} with no
    state update — the post-click state leaves the Gaussian manifold, and
    this module does not pretend to update it. Full post-measurement
    conditioning is a ponytail (needs the Gaussian→Fock state bridge).
    """
    if not isinstance(state, GaussianState):
        raise TypeError(
            f"p_click requires GaussianState, got {type(state).__name__}"
        )
    _check_mode(state, mode)
    return 1.0 - _vacuum_probability(state.V, state.rbar, mode)


def sample_threshold(
    state: GaussianState,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
) -> bool:
    """Sample one threshold outcome: ``True`` = click, ``False`` = no click.

    Outcome-only (no state update, see :func:`p_click`).
    """
    if rng is None:
        rng = np.random.default_rng()
    return bool(rng.random() < p_click(state, mode))


def _check_size(size: int) -> None:
    if not isinstance(size, (int, np.integer)) or isinstance(size, bool) or size < 1:
        raise ValueError(f"size must be a positive int, got {size!r}")


def homodyne_sample_batch(
    state: GaussianState,
    mode: int = 0,
    phi: float = 0.0,
    size: int = 1000,
    *,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Batch homodyne outcomes (size,) from the same edge N(μ, σ²).

    μ = u·r̄, σ² = uᵀVu with u the φ-quadrature vector; iid across shots
    (no per-shot conditioning). One RNG call; σ² ≤ EPS rejected as in
    the single-shot sampler.
    """
    if rng is None:
        rng = np.random.default_rng()
    _check_size(size)
    mu = homodyne_mean(state, mode, phi)
    var = homodyne_var(state, mode, phi)
    if var <= _EPS:
        raise ValueError(f"homodyne variance too small: σ²={var}")
    return rng.normal(mu, np.sqrt(var), size=size)


def heterodyne_sample_batch(
    state: GaussianState,
    mode: int = 0,
    size: int = 1000,
    *,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Batch heterodyne outcomes (size,) complex, β=(x+ip)/√2.

    Draws (x, p) ~ N(r̄_xp, V_xp + I/2) once for all shots (vectorized).
    """
    if rng is None:
        rng = np.random.default_rng()
    _check_size(size)
    mu, Sigma = _heterodyne_params(state, mode)
    z = rng.multivariate_normal(mu, Sigma, size=size)
    return (z[:, 0] + 1j * z[:, 1]) / np.sqrt(2.0)
