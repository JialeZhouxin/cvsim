"""Bosonic observables: weights + weighted moments + condition Homodyne (ħ=1, xxpp)."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import (  # noqa: F401  (re-export: weight_sum moved to state.py, B1)
    BosonicState,
    Component,
    weight_sum,
)

_IM_TOL = 1e-8
_SIG_EPS = 1e-14


def _nmode(state: BosonicState) -> int:
    return state.nmode


def _check_mode(state: BosonicState, mode: int) -> int:
    m = _nmode(state)
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    return m


def _homodyne_u(nmode: int, mode: int, phi: float) -> np.ndarray:
    u = np.zeros(2 * nmode, dtype=complex)
    u[mode] = np.cos(phi)
    u[nmode + mode] = np.sin(phi)
    return u


def _as_real(z: complex, name: str) -> float:
    if abs(z.imag) > _IM_TOL:
        raise ValueError(f"{name} has large imaginary part: {z}")
    return float(z.real)


def _mean_photon_component(c: Component, mode: int | None) -> complex:
    m = c.V.shape[0] // 2
    V, r = c.V, c.rbar

    def one(i: int) -> complex:
        xx = V[i, i] + r[i] ** 2
        pp = V[m + i, m + i] + r[m + i] ** 2
        return 0.5 * (xx + pp - 1.0)

    if mode is not None:
        if not 0 <= mode < m:
            raise IndexError(f"mode {mode} out of range for nmode={m}")
        return one(mode)
    return sum(one(i) for i in range(m))


def mean_photon(state: BosonicState, mode: int | None = None) -> float:
    """⟨n⟩ = ∑_k w_k ⟨n⟩_k (ħ=1). Returns real part."""
    if mode is not None:
        _check_mode(state, mode)
    total = 0.0 + 0.0j
    for c in state.components:
        total += c.w * _mean_photon_component(c, mode)
    return _as_real(total, "mean_photon")


def homodyne_mean(state: BosonicState, mode: int = 0, phi: float = 0.0) -> float:
    """Weighted edge mean ⟨x_φ⟩ = ∑ w_k (u·r̄_k)."""
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    total = 0.0 + 0.0j
    for c in state.components:
        total += c.w * (u @ c.rbar)
    return _as_real(total, "homodyne_mean")


def homodyne_var(state: BosonicState, mode: int = 0, phi: float = 0.0) -> float:
    """Weighted Var(x_φ) = ⟨x_φ²⟩ − μ² with ⟨x_φ²⟩ = ∑ w (uᵀVu + (u·r)²)."""
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    uf = u.real
    mu = 0.0 + 0.0j
    x2 = 0.0 + 0.0j
    for c in state.components:
        mean_k = complex(u @ c.rbar)
        var_k = float(uf @ c.V @ uf)
        mu += c.w * mean_k
        x2 += c.w * (var_k + mean_k**2)
    return _as_real(x2 - mu**2, "homodyne_var")


def _xphi_params(c: Component, mode: int, nmode: int, phi: float) -> tuple[complex, float]:
    """Per-component x_φ projection: μ_k = u·r̄_k (complex), σ²_k = uᵀ V u (real)."""
    u = np.zeros(2 * nmode, dtype=float)
    u[mode] = np.cos(phi)
    u[nmode + mode] = np.sin(phi)
    mu_k = complex(u @ c.rbar)
    var_k = float(u @ c.V @ u)
    return mu_k, var_k


def _auto_grid(state: BosonicState, mode: int, phi: float) -> tuple[np.ndarray, float]:
    """Auto grid: δx ≤ σ_min/5, range = centroid ± 6σ_max.

    σ from per-component x_φ variance. Centroid = Re(Σ w_k μ_k)/Re(Σ w_k).
    """
    m = _check_mode(state, mode)
    mus: list[complex] = []
    sigmas: list[float] = []
    ws: list[complex] = []
    for c in state.components:
        mu_k, var_k = _xphi_params(c, mode, m, phi)
        if var_k <= _SIG_EPS:
            raise ValueError(f"homodyne variance too small: σ²={var_k}")
        mus.append(mu_k)
        sigmas.append(float(np.sqrt(var_k)))
        ws.append(c.w)
    sigma_min = min(sigmas)
    sigma_max = max(sigmas)
    wsum = sum(ws)
    if abs(wsum) < _SIG_EPS:
        raise ValueError("homodyne_pdf: weight sum ~ 0")
    centroid = float(np.real(sum(w * mu for w, mu in zip(ws, mus, strict=True)) / wsum))
    dx = sigma_min / 5.0
    lo = centroid - 6.0 * sigma_max
    hi = centroid + 6.0 * sigma_max
    n_grid = int(np.ceil((hi - lo) / dx)) + 1
    xs = np.linspace(lo, hi, n_grid)
    return xs, dx


def _edge_density(state: BosonicState, mode: int, phi: float, xs: np.ndarray) -> np.ndarray:
    """S(x) = Σ_k w_k p_k(x) on grid; complex dtype (interference kept)."""
    m = _check_mode(state, mode)
    S = np.zeros_like(xs, dtype=complex)
    for c in state.components:
        mu_k, var_k = _xphi_params(c, mode, m, phi)
        if var_k <= _SIG_EPS:
            raise ValueError(f"homodyne variance too small: σ²={var_k}")
        coeff = c.w / np.sqrt(2.0 * np.pi * var_k)
        S += coeff * np.exp(-0.5 * (xs - mu_k) ** 2 / var_k)
    return S


def homodyne_pdf(
    state: BosonicState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    n_grid: int | None = None,
    lim: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Exact edge density P(x_φ) = Σ_k w_k p_k(x) on a grid.

    Returns ``(xs, P)`` where ``P = max(Re S, 0)`` and ``S = Σ_k w_k p_k(x)``.
    Complex weights/centres are kept (interference terms included); the
    Hermitian-pair closure of a physical state ensures ``Im(S) ≈ 0``.
    ``is_hermitian`` (component_eng) is the upstream guard.

    Grid auto (default): ``δx ≤ σ_min/5``, range = centroid ± 6σ_max.
    Override ``n_grid``/``lim`` to force ``np.linspace(-lim, lim, n_grid)``.

    Negative ``Re(S)`` values (non-physical leak) are clipped to 0 with a
    warning.
    """
    import warnings

    m = _check_mode(state, mode)
    if n_grid is not None and lim is not None:
        if n_grid < 3:
            raise ValueError("n_grid must be >= 3")
        xs = np.linspace(-lim, lim, int(n_grid))
    elif n_grid is not None or lim is not None:
        raise ValueError("homodyne_pdf: n_grid and lim must be both set or both None")
    else:
        xs, _ = _auto_grid(state, mode, phi)

    S = _edge_density(state, mode, phi, xs)
    imag_max = float(np.max(np.abs(S.imag))) if S.size else 0.0
    if imag_max > _IM_TOL:
        raise ValueError(
            f"homodyne_pdf: large imaginary part in edge density (max |Im|={imag_max:.3e}); "
            "state is not Hermitian-closed"
        )
    P = S.real.copy()
    neg = P < 0.0
    if np.any(neg):
        n_neg = int(np.sum(neg))
        leak = float(-np.sum(P[neg]) * (xs[1] - xs[0]) if xs.size > 1 else 0.0)
        warnings.warn(
            f"homodyne_pdf: {n_neg} grid points have Re(S)<0 (leak mass ~{leak:.3e}); clipped to 0",
            stacklevel=2,
        )
        P[neg] = 0.0
    return xs, P


def homodyne_sample(
    state: BosonicState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    n_grid: int | None = None,
    lim: float | None = None,
    shots: int = 1000,
) -> np.ndarray:
    """Sample homodyne outcomes via CDF grid inversion (exact edge distribution).

    ``P(x) = Σ_k w_k p_k(x)`` is computed on a grid; complex weights are
    handled via ``Re(S)`` with Hermitian-pair closure (``is_hermitian`` guard).
    Sampling uses ``rng.uniform`` + ``searchsorted`` on the normalised CDF —
    deterministic, rejection-free, vectorised over ``shots``.

    Grid auto: ``δx ≤ σ_min/5``, range = centroid ± 6σ_max.
    Override ``n_grid``/``lim`` to force a specific linspace.

    Returns ``np.ndarray`` of shape ``(shots,)``.
    """
    if rng is None:
        rng = np.random.default_rng()
    if shots < 1:
        raise ValueError("shots must be >= 1")
    xs, P = homodyne_pdf(state, mode, phi, n_grid=n_grid, lim=lim)
    if xs.size < 2:
        raise ValueError("homodyne_sample: grid too small")
    dx = xs[1] - xs[0]
    cdf = np.cumsum(P) * dx
    total = cdf[-1]
    if total <= _SIG_EPS:
        raise ValueError("homodyne_sample: PDF integrates to ~0 (zero state?)")
    cdf = cdf / total
    u = rng.uniform(0.0, 1.0, int(shots))
    idx = np.searchsorted(cdf, u, side="right")
    np.clip(idx, 0, xs.size - 1, out=idx)
    return xs[idx]


def homodyne_condition(
    state: BosonicState,
    mode: int,
    phi: float,
    outcome: float,
) -> BosonicState:
    """Ideal Homodyne condition on all components (complex-mean OK).

    Per component (same shape as Gaussian; r̄ may be complex):
      v=Vu, σ=uᵀVu, μ=u·r̄
      V'=V−vvᵀ/σ,  r̄'=r̄+v(outcome−μ)/σ
      w *= (2πσ)^{-1/2} exp(−(outcome−μ)²/(2σ))  # L may be complex
    Then renorm ∑w=1. Does not delete modes.

    Honesty: teaching closed-form extension; not full Generaldyne POVM.
    """
    m = _check_mode(state, mode)
    u = np.zeros(2 * m, dtype=float)
    u[mode] = np.cos(phi)
    u[m + mode] = np.sin(phi)

    kept: list[Component] = []
    raw_w: list[complex] = []

    for c in state.components:
        v = c.V @ u
        sigma = float(u @ v)
        if sigma <= _SIG_EPS:
            raise ValueError(f"homodyne variance too small: σ={sigma}")
        mu = complex(u @ c.rbar)
        L = (2.0 * np.pi * sigma) ** (-0.5) * np.exp(-0.5 * (outcome - mu) ** 2 / sigma)
        Vn = c.V - np.outer(v, v) / sigma
        Vn = 0.5 * (Vn + Vn.T)
        rn = c.rbar + v * ((outcome - mu) / sigma)
        kept.append(Component(V=Vn, rbar=rn, w=0.0 + 0.0j))
        raw_w.append(c.w * complex(L))

    s = sum(raw_w)
    if abs(s) < _SIG_EPS:
        raise ValueError("homodyne_condition: weight sum ~ 0 after likelihood")
    for comp, w in zip(kept, raw_w, strict=False):
        comp.w = w / s
    return BosonicState(components=kept)


def homodyne_sample_and_condition(
    state: BosonicState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    n_grid: int | None = None,
    lim: float | None = None,
    shots: int = 1,
) -> tuple[np.ndarray, BosonicState]:
    """Sample (CDF inversion) then condition (exact Born-rule). Returns
    ``(outcomes, posterior)`` where ``outcomes`` has shape ``(shots,)`` and
    ``posterior`` is conditioned on ``outcomes[0]``.
    """
    outcomes = homodyne_sample(state, mode, phi, rng=rng, n_grid=n_grid, lim=lim, shots=shots)
    posterior = homodyne_condition(state, mode, phi, float(outcomes[0]))
    return outcomes, posterior
