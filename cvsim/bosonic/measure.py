"""Bosonic measurements (A4): homodyne + heterodyne + threshold.

Homodyne implementation lives in ``observables.py`` (CDF grid inversion
exact edge distribution, B3); this module re-exports it so
``cvsim.bosonic.homodyne_*`` import paths are unchanged. ``homodyne_pdf``
is the exact edge density ``P(x_φ) = Σ_k w_k p_k(x)`` on a grid (complex
weights kept, interference terms included).

Heterodyne (B1) is a **teaching cut**: sample and condition both use the
real-diagonal-component pool only (components with real r̄ and Re(w) > 0,
mirroring the pre-B3 homodyne teaching cut). K=1 states match the Gaussian
package exactly. Exact mixed-state heterodyne (complex centres/weights, CDF
strategy) is deferred to B3 — do not use on mixed states for production.

Threshold is outcome-only ({0,1}, no state update); the post-click state
leaves the Gaussian mixture manifold.
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.observables import (
    _SIG_EPS,
    _as_real,
    _check_mode,
    homodyne_condition,  # noqa: F401  (re-export: single implementation source)
    homodyne_mean,  # noqa: F401
    homodyne_pdf,  # noqa: F401
    homodyne_sample,  # noqa: F401
    homodyne_sample_and_condition,  # noqa: F401
    homodyne_var,  # noqa: F401
)
from cvsim.bosonic.state import BosonicState, Component

_POOL_IMAG_TOL = 1e-12


# ---------------------------------------------------------------------------
# heterodyne — teaching cut (real-diagonal pool)
# ---------------------------------------------------------------------------


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


def _real_diag_pool(state: BosonicState, imag_tol: float) -> tuple[list[Component], list[float]]:
    """Teaching-cut pool: real-mean, real-weight components (Re(w) > 0, |Im(w)| ≤ tol).

    Complex-weight guard (OCR 2026-08-14): a complex-weight real-mean component
    would be conditioned without phase rotation → silently wrong state.
    """
    pool: list[Component] = []
    weights: list[float] = []
    for c in state.components:
        if np.max(np.abs(c.rbar.imag)) > imag_tol:
            continue
        rw = float(c.w.real)
        if rw <= 0.0 or abs(c.w.imag) > imag_tol:
            continue
        pool.append(c)
        weights.append(rw)
    return pool, weights


def heterodyne_sample(
    state: BosonicState,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
    imag_tol: float = _POOL_IMAG_TOL,
) -> complex:
    """Sample heterodyne outcome β without conditioning (teaching cut).

    Pool components with real r̄ and Re(w)>0; pick k ∝ Re(w_k), then
    (x, p) ~ N(r̄_xp, V_xp + I/2) of that component; returns β = (x + i p)/√2.
    K=1: identical distribution to the Gaussian heterodyne_sample.
    """
    if rng is None:
        rng = np.random.default_rng()
    m = _check_mode(state, mode)
    pool, weights = _real_diag_pool(state, imag_tol)
    if not pool:
        raise ValueError("heterodyne_sample: no real-mean positive-weight components")

    if len(pool) == 1:
        idx = 0
    else:
        p = np.asarray(weights, dtype=float)
        p = p / p.sum()
        idx = int(rng.choice(len(pool), p=p))
    c = pool[idx]
    ixp = _xp_indices(m, mode)
    mu = c.rbar[ixp].real
    Sigma = c.V[np.ix_(ixp, ixp)] + 0.5 * np.eye(2)
    Sigma = 0.5 * (Sigma + Sigma.T)
    w = np.linalg.eigvalsh(Sigma)
    if np.min(w) <= _SIG_EPS:
        raise ValueError(f"heterodyne outcome covariance not PD: min eig={float(np.min(w))}")
    z = rng.multivariate_normal(mu, Sigma)
    return complex((z[0] + 1j * z[1]) / np.sqrt(2.0))


def heterodyne_condition(
    state: BosonicState,
    mode: int,
    outcome: complex | float | np.ndarray,
    *,
    imag_tol: float = _POOL_IMAG_TOL,
) -> BosonicState:
    """Condition on heterodyne outcome β and **remove** the measured mode.

    Teaching cut: only pool components (real r̄, Re(w) > 0) are conditioned.
    Per component (Gaussian ``heterodyne_condition`` formula, mode removal +
    xxpp repack):

        Σ_A = V_A + I/2,  C = cov(B, A)
        V_B' = V_B − C Σ_A⁻¹ Cᵀ,   r̄_B' = r̄_B + C Σ_A⁻¹ (z − r̄_A)

    Weights reweighted by the real Gaussian edge density
    w_k ∝ w_k · N(z; r̄_A,k, Σ_A,k) then renormalized to Σw = 1.
    K=1 matches the Gaussian heterodyne_condition exactly; a single-mode
    K=1 condition leaves a 0-mode state (``nmode == 0``).
    """
    m = _check_mode(state, mode)
    beta = _as_beta(outcome)
    if abs(beta) > 30.0:
        raise ValueError(f"heterodyne outcome |β|={abs(beta):.3g} out of range (|β| ≤ 30)")
    z = _beta_to_xp(beta)

    idx_A = _xp_indices(m, mode)
    idx_B = [i for i in range(2 * m) if i not in idx_A]
    keep_modes = sorted(i for i in range(m) if i != mode)
    pack = list(keep_modes) + [m + k for k in keep_modes]
    pos = {ax: j for j, ax in enumerate(idx_B)}
    perm = [pos[ax] for ax in pack]

    pool, _ = _real_diag_pool(state, imag_tol)
    if not pool:
        raise ValueError("heterodyne_condition: no real-mean positive-weight components")

    kept: list[Component] = []
    raw_w: list[complex] = []
    for c in pool:
        VA = c.V[np.ix_(idx_A, idx_A)]
        rA = c.rbar[idx_A].real
        Sigma = VA + 0.5 * np.eye(2)
        Sigma = 0.5 * (Sigma + Sigma.T)
        try:
            invS = np.linalg.inv(Sigma)
        except np.linalg.LinAlgError as exc:
            raise ValueError("heterodyne Σ_A = V_A + I/2 is singular") from exc
        dmu = z - rA
        wlik = np.exp(-0.5 * float(dmu @ invS @ dmu)) / (
            2.0 * np.pi * np.sqrt(float(np.linalg.det(Sigma)))
        )
        raw_w.append(c.w * complex(wlik))
        VB = c.V[np.ix_(idx_B, idx_B)]
        C = c.V[np.ix_(idx_B, idx_A)]
        rB = c.rbar[idx_B].real
        VB_n = VB - C @ invS @ C.T
        rB_n = rB + C @ invS @ dmu
        VB_n = 0.5 * (VB_n + VB_n.T)
        VB_n = VB_n[np.ix_(perm, perm)]
        rB_n = rB_n[perm]
        kept.append(Component(V=VB_n, rbar=rB_n, w=0.0 + 0.0j))

    s = sum(raw_w)
    if abs(s) < _SIG_EPS:
        raise ValueError("heterodyne_condition: weight sum ~ 0 after likelihood")
    for comp, w in zip(kept, raw_w, strict=True):
        comp.w = w / s
    return BosonicState(components=kept)


def heterodyne_sample_and_condition(
    state: BosonicState,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
    imag_tol: float = _POOL_IMAG_TOL,
) -> tuple[complex, BosonicState]:
    """Sample heterodyne β then condition (measured mode removed)."""
    beta = heterodyne_sample(state, mode, rng=rng, imag_tol=imag_tol)
    return beta, heterodyne_condition(state, mode, beta, imag_tol=imag_tol)


# ---------------------------------------------------------------------------
# threshold — outcome-only
# ---------------------------------------------------------------------------


def _vacuum_probability_complex(V: np.ndarray, rbar: np.ndarray, mode: int) -> complex:
    """⟨0|ρ|0⟩ of one Gaussian component, complex r̄ allowed.

    Same quadratic form as ``cvsim.bridge.vacuum_probability`` (ħ=1, xxpp):

        p₀ = exp(−½ r̄ᵀ (V+½I)⁻¹ r̄) / √det(V+½I)

    evaluated on the mode block with complex r̄. The bridge helper casts
    rbar to float (drops interference imaginary parts), so the complex
    quadratic form lives here; real r̄ gives exactly the bridge value.
    """
    V = np.asarray(V, dtype=float)
    rbar = np.asarray(rbar, dtype=complex)
    m = V.shape[0] // 2
    i = mode
    V1 = np.array([[V[i, i], V[i, m + i]], [V[m + i, i], V[m + i, m + i]]])
    r1 = np.array([rbar[i], rbar[m + i]])
    A = V1 + 0.5 * np.eye(2)
    if np.linalg.eigvalsh(A).min() <= 0.0:
        raise ValueError(f"V+½I on mode {mode} is not positive-definite")
    exponent = -0.5 * complex(r1 @ np.linalg.solve(A, r1))
    return np.exp(exponent) / np.sqrt(np.linalg.det(A))


def p_click(state: BosonicState, mode: int = 0) -> float:
    """Threshold (on/off) click probability p = 1 − Σ_k w_k ⟨0|ρ_k|0⟩.

    Per-component vacuum overlap may be complex (complex-mean interference
    components); the weighted sum is reduced to real with a strict
    imaginary-part tolerance check (raises if |Im| > 1e-8). K=1 matches
    the Gaussian p_click.

    **Outcome-only**: no state update — the post-click state leaves the
    Gaussian mixture manifold.
    """
    _check_mode(state, mode)
    total = 0.0 + 0.0j
    for c in state.components:
        total += c.w * _vacuum_probability_complex(c.V, c.rbar, mode)
    return 1.0 - _as_real(total, "p_click")


def sample_threshold(
    state: BosonicState,
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
