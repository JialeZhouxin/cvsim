"""Gaussian analysis helpers (physicality, spectrum, purity, entropy, ptrace).

Phase 2 F-ANALYSE: physicality, symplectic eigenvalues, purity, entropy_vn,
partial_trace, log_negativity, fidelity.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from scipy.linalg import sqrtm

from cvsim.conventions import omega
from cvsim.gaussian.state import GaussianState


def _as_cov(state: GaussianState | np.ndarray) -> np.ndarray:
    """Normalize input to a float64 covariance matrix (2m × 2m)."""
    if isinstance(state, GaussianState):
        return np.asarray(state.V, dtype=float)
    V = np.asarray(state, dtype=float)
    if V.ndim != 2 or V.shape[0] != V.shape[1] or V.shape[0] % 2 != 0:
        raise ValueError(f"covariance must be even square, got shape {V.shape}")
    return V


def is_physical(
    state: GaussianState | np.ndarray,
    *,
    atol: float = 1e-10,
) -> bool:
    """Return True if covariance satisfies the uncertainty relation.

    With ħ=1, xxpp: ``V = Vᵀ`` (after symmetrization) and

        V + i Ω/2  ≽  0

    (Hermitian positive semidefinite). ``atol`` allows tiny negative
    eigenvalues from float64 roundoff.
    """
    try:
        V = _as_cov(state)
    except ValueError:
        return False
    V = 0.5 * (V + V.T)
    m = V.shape[0] // 2
    H = V + 1j * (omega(m) / 2.0)
    # Numerical Hermitian projection
    H = 0.5 * (H + H.conj().T)
    w = np.linalg.eigvalsh(H)
    return bool(np.all(w >= -atol))


def validate_state(state: GaussianState, *, atol: float = 1e-10) -> None:
    """Raise ValueError if ``state`` is not a physical Gaussian covariance."""
    if not is_physical(state, atol=atol):
        raise ValueError(
            "non-physical Gaussian covariance: V + iΩ/2 is not PSD (ħ=1, xxpp)"
        )


def symplectic_eigenvalues(
    state: GaussianState | np.ndarray,
    *,
    atol: float = 1e-10,
    validate: bool = False,
) -> np.ndarray:
    """Return *m* symplectic eigenvalues νⱼ ≥ 1/2 (ascending, float64).

    Williamson decomposition via the Cholesky path (Serafini / Weedbrook):

    1. Symmetrize ``V ← ½(V+Vᵀ)``.
    2. ``K = chol(V)`` so ``V = K Kᵀ`` (tiny jitter if near-singular pure state).
    3. ``A = Kᵀ Ω K`` (skew-symmetric).
    4. Eigenvalues of ``iA`` are real pairs ``±ν``.
    5. Take one per pair: ``sort(|Re λ|)[::2]`` → length *m*.
    6. Clip ``ν ≥ 1/2 - atol`` for float64 roundoff (vision §7).

    Accepts ``GaussianState`` or bare covariance ``V`` (2m×2m).

    **Physicality is not checked by default.** Non-physical ``V`` (e.g. sub-vacuum
    diagonal) may yield eigenvalues that are then clipped to the vacuum floor,
    masking the violation. Pass ``validate=True`` to reject non-physical input
    via ``is_physical``, or call ``validate_state`` yourself.

    Parameters
    ----------
    atol :
        Floor tolerance: clip ``ν ← max(ν, 0.5 - atol)``. Default ``1e-10``.
    validate :
        If True, raise ``ValueError`` when ``is_physical`` fails.

    References
    ----------
    - Serafini, *Quantum Continuous Variables* §3.2
    - Weedbrook et al., Rev. Mod. Phys. 84, 621 (2012) §II.B
    """
    V = _as_cov(state)
    V = 0.5 * (V + V.T)
    if validate and not is_physical(V, atol=atol):
        raise ValueError(
            "non-physical Gaussian covariance: V + iΩ/2 is not PSD (ħ=1, xxpp)"
        )
    m = V.shape[0] // 2

    try:
        K = np.linalg.cholesky(V)
    except np.linalg.LinAlgError:
        # Near-singular pure states: det V = (1/4)^m can underflow chol.
        K = np.linalg.cholesky(V + 1e-14 * np.eye(2 * m))

    A = K.T @ omega(m) @ K  # skew-symmetric
    ev = np.linalg.eigvals(1j * A)  # real ±ν pairs
    nu_all = np.sort(np.abs(ev.real))  # length 2m
    # Take one from each ± pair (NOT nu_all[m:] which fails on unequal ν).
    nu = nu_all[::2]
    # Clip roundoff below the vacuum floor; atol makes the floor adjustable.
    nu = np.maximum(nu, 0.5 - atol)
    return nu.astype(float)


def purity(
    state: GaussianState | np.ndarray,
    *,
    validate: bool = False,
) -> float:
    """Return μ = 1 / (2^m √det V). Pure Gaussian → 1.

    Uses ``slogdet`` for numerical stability (vision §7).
    Symmetrizes ``V ← ½(V+Vᵀ)`` before the determinant (same as
    ``symplectic_eigenvalues`` / vision §7 noisy-update hygiene).
    Raises ``ValueError`` if ``det(V) ≤ 0`` (non-physical / singular sign).

    Accepts ``GaussianState`` or bare covariance ``V`` (2m×2m).

    **Physicality is not checked by default.** Non-physical ``V`` with
    ``det V > 0`` can yield ``μ > 1`` (e.g. ``V = 0.4 I`` → μ = 1.25).
    Pass ``validate=True`` to reject non-physical input via ``is_physical``,
    or call ``validate_state`` yourself.

    Math (vision §4.2, ħ=1)::

        μ = 1 / (2^m √det V)

    Cross-check: μ = ∏ⱼ 1/(2 νⱼ) via ``symplectic_eigenvalues``.

    Parameters
    ----------
    validate :
        If True, raise ``ValueError`` when ``is_physical`` fails.
    """
    V = _as_cov(state)
    V = 0.5 * (V + V.T)
    if validate and not is_physical(V):
        raise ValueError(
            "non-physical Gaussian covariance: V + iΩ/2 is not PSD (ħ=1, xxpp)"
        )
    m = V.shape[0] // 2
    sign, logdet = np.linalg.slogdet(V)
    if sign <= 0:
        raise ValueError(
            f"det(V) ≤ 0 (slogdet sign={sign}): non-physical or singular covariance"
        )
    return float(np.exp(-0.5 * logdet) / (2**m))


def _bosonic_g(nu: np.ndarray, *, eps: float = 1e-15) -> np.ndarray:
    """Bosonic thermal entropy g(ν) in nats, elementwise.

    With occupation n = ν - 1/2:

        g = (n+1) ln(n+1) - n ln n

    At ν = 1/2 (n = 0), g = 0 by continuity.
    """
    n = np.maximum(np.asarray(nu, dtype=float) - 0.5, 0.0)
    out = np.zeros_like(n, dtype=float)
    mask = n > eps
    nm = n[mask]
    out[mask] = (nm + 1.0) * np.log(nm + 1.0) - nm * np.log(nm)
    return out


def entropy_vn(
    state: GaussianState | np.ndarray,
    *,
    validate: bool = False,
) -> float:
    """Von Neumann entropy S = Σⱼ g(νⱼ) in **nats** (ħ=1).

    Symplectic eigenvalues νⱼ from ``symplectic_eigenvalues``; bosonic
    thermal function

        g(ν) = (n+1) ln(n+1) - n ln n,   n = ν - 1/2

    with g(1/2) = 0. Pure Gaussians → S = 0.

    Accepts ``GaussianState`` or bare covariance ``V``.
    **Physicality is not checked by default**; pass ``validate=True`` to
    reject non-physical input (same pattern as ``purity``).

    References
    ----------
    - Vision §4.2 F-ANALYSE
    - Serafini, *Quantum Continuous Variables* §3.3
    - Weedbrook et al., Rev. Mod. Phys. 84, 621 (2012) §II.C
    """
    nu = symplectic_eigenvalues(state, validate=validate)
    return float(np.sum(_bosonic_g(nu)))


def partial_trace(
    state: GaussianState,
    keep: int | Iterable[int],
) -> GaussianState:
    """Partial trace onto subsystem ``keep`` (logical mode indices).

    Drops all modes not in ``keep`` from ``V`` and ``r̄`` **without**
    measurement collapse or conditioning. This is *not* the same as
    mid-circuit Homodyne + ``remove_mode`` when outcomes condition the
    remaining state; use measurement APIs for that.

    Parameters
    ----------
    state :
        Input Gaussian state (required; bare V alone cannot carry ``r̄``).
    keep :
        Mode index or iterable of indices in ``0 .. nmode-1``. Order does
        not matter; output modes are sorted ascending.

    Returns
    -------
    GaussianState
        Reduced state on ``len(keep_unique)`` modes in xxpp order.

    Raises
    ------
    TypeError
        If ``state`` is not a ``GaussianState``.
    ValueError
        If ``keep`` is empty after normalization.
    IndexError
        If any index is outside ``0 .. nmode-1``.
    """
    if not isinstance(state, GaussianState):
        raise TypeError(
            f"partial_trace requires GaussianState, got {type(state).__name__}"
        )
    m = state.nmode
    keep_list = [int(keep)] if isinstance(keep, (int, np.integer)) else [int(k) for k in keep]
    # unique, sorted — stable subsystem order
    keep_u = sorted(set(keep_list))
    if not keep_u:
        raise ValueError("partial_trace requires at least one mode in keep")
    for k in keep_u:
        if not 0 <= k < m:
            raise IndexError(f"mode {k} out of range for nmode={m}")

    # xxpp: mode k → axes k (x) and m+k (p)
    idx = keep_u + [m + k for k in keep_u]
    V = np.asarray(state.V, dtype=float)
    r = np.asarray(state.rbar, dtype=float)
    return GaussianState(V=V[np.ix_(idx, idx)], rbar=r[idx])


def _partial_transpose_cov(
    V: np.ndarray,
    nmode: int,
    modes_A: list[int],
) -> np.ndarray:
    """Partial transpose on p-quadratures of modes_A (xxpp): V ↦ Λ V Λ."""
    lam = np.ones(2 * nmode, dtype=float)
    for k in modes_A:
        lam[nmode + k] = -1.0
    L = np.diag(lam)
    return L @ V @ L


def _symplectic_eigenvalues_raw(V: np.ndarray) -> np.ndarray:
    """Symplectic spectrum without vacuum-floor clip (for PT / log-neg).

    Uses |eig(i Ω V)| directly so non-physical PT covariances with ν̃ < 1/2
    are preserved. Cholesky-Williamson is unsuitable: PT V is typically not PD.
    """
    V = 0.5 * (V + V.T)
    m = V.shape[0] // 2
    ev = np.linalg.eigvals(1j * omega(m) @ V)
    nu_all = np.sort(np.abs(ev.real))
    return nu_all[::2].astype(float)


def log_negativity(
    state: GaussianState,
    modes_A: int | Iterable[int],
) -> float:
    """Logarithmic negativity E_N of a bipartition (bits).

    Partial-transpose the covariance on subsystem ``modes_A`` (flip each
    selected mode's *p* quadrature in xxpp), compute raw symplectic
    eigenvalues ν̃_j of the PT matrix, then

        E_N = Σ_j max{0, -log₂(2 ν̃_j)}

    Only ν̃_j < 1/2 contribute. This matches the TMSV freeze
    E_N = -log₂(e^{-2r}) = 2r / ln(2) and standard CV references
    (Weedbrook RMP §III.D; Adesso et al.; Vidal & Werner 2002).

    Note (vision history): prior to vision v0.1.3 the formula was written as
    max{0, -Σ_j log₂(2ν̃_j)} (max over the *full* sum). That form cancels on
    TMSV and is incorrect for general multimode states. Vision v0.1.3 and this
    implementation use the per-term PPT log-negativity
    Σ_j max{0, -log₂(2ν̃_j)}.

    Numerics: ``log2`` is guarded with floor ``2ν̃ ≥ 1e-300`` only to avoid
    ``log2(0)`` from float noise. Exact ν̃ = 0 is not a physical PT outcome
    here; the guard is not a physics cutoff.

    Parameters
    ----------
    state :
        Multipartite Gaussian state.
    modes_A :
        Mode index or iterable defining party A. Party B is the complement.
        Empty A or A = all modes → E_N = 0 (no cut).

    Returns
    -------
    float
        E_N ≥ 0 in bits.
    """
    if not isinstance(state, GaussianState):
        raise TypeError(
            f"log_negativity requires GaussianState, got {type(state).__name__}"
        )
    m = state.nmode
    if isinstance(modes_A, (int, np.integer)):
        A = [int(modes_A)]
    else:
        A = sorted({int(k) for k in modes_A})
    for k in A:
        if not 0 <= k < m:
            raise IndexError(f"mode {k} out of range for nmode={m}")
    if not A or len(A) == m:
        return 0.0

    V = np.asarray(state.V, dtype=float)
    V = 0.5 * (V + V.T)
    Vp = _partial_transpose_cov(V, m, A)
    nu = _symplectic_eigenvalues_raw(Vp)
    # E_N = sum max(0, -log2(2 ν̃))
    contrib = -np.log2(np.maximum(2.0 * nu, 1e-300))
    return float(np.sum(np.maximum(contrib, 0.0)))


def fidelity(
    state1: GaussianState,
    state2: GaussianState,
    *,
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> float:
    """Uhlmann fidelity F(ρ₁, ρ₂) ∈ [0, 1] between two Gaussian states.

    Multimode Banchi–Braunstein–Pirandola formula (PRL 115, 260501 (2015)),
    implemented via the thewalrus / Brask transcription (arXiv:2102.05748
    Eq. 112, squared form — this function returns that square, i.e. the
    standard Uhlmann fidelity |⟨ψ|φ⟩|² on pure states).

    Conventions: ħ=1, xxpp, V_vac = I/2. Means and covariances are converted
    internally to the unit-ħσ variables of the reference implementation.

    Freeze checks (tests):

    - identical states → 1
    - coherent: F = exp(-|α-β|²)
    - thermal n,m: F = [√((n+1)(m+1)) - √(n m)]^{-2}
    - squeezed vacuum vs vacuum: F = sech(r)

    Parameters
    ----------
    state1, state2 :
        Gaussian states on the **same** number of modes.
    rtol, atol :
        Tolerances for the early-exit identical-state check and for the
        near-zero branch of ``sqrtm``.

    Returns
    -------
    float
        Fidelity in ``[0, 1]`` (real part taken if residual imag noise).

    Raises
    ------
    TypeError
        If either argument is not a ``GaussianState``.
    ValueError
        If the two states have different ``nmode``.
    """
    if not isinstance(state1, GaussianState):
        raise TypeError(
            f"fidelity requires GaussianState, got state1={type(state1).__name__}"
        )
    if not isinstance(state2, GaussianState):
        raise TypeError(
            f"fidelity requires GaussianState, got state2={type(state2).__name__}"
        )
    if state1.nmode != state2.nmode:
        raise ValueError(
            f"fidelity nmode mismatch: {state1.nmode} vs {state2.nmode}"
        )

    mu1 = np.asarray(state1.rbar, dtype=float).ravel()
    mu2 = np.asarray(state2.rbar, dtype=float).ravel()
    cov1 = 0.5 * (
        np.asarray(state1.V, dtype=float) + np.asarray(state1.V, dtype=float).T
    )
    cov2 = 0.5 * (
        np.asarray(state2.V, dtype=float) + np.asarray(state2.V, dtype=float).T
    )

    if np.allclose(mu1, mu2, rtol=rtol, atol=atol) and np.allclose(
        cov1, cov2, rtol=rtol, atol=atol
    ):
        return 1.0

    # thewalrus path: normalize to ħ=1 variables (our native ħ is already 1,
    # so σ = V / ħ = V and δr = Δμ / √ħ = Δμ).
    hbar = 1.0
    sigma1 = cov1 / hbar
    sigma2 = cov2 / hbar
    deltar = (mu1 - mu2) / np.sqrt(hbar)
    n0 = sigma1.shape[0]
    m = n0 // 2
    om = omega(m)

    sigma = sigma1 + sigma2
    sigma_inv = np.linalg.inv(sigma)
    vaux = om.T @ sigma_inv @ (0.25 * om + sigma2 @ om @ sigma1)
    sqrtm_arg = np.eye(n0) + 0.25 * np.linalg.inv(vaux @ om @ vaux @ om)

    if np.allclose(sqrtm_arg, 0.0, rtol=rtol, atol=atol):
        mat_sqrtm = np.zeros_like(sqrtm_arg)
    else:
        mat_sqrtm = sqrtm(sqrtm_arg)

    det_arg = 2.0 * (mat_sqrtm + np.eye(n0)) @ vaux
    # det may pick up tiny imag from sqrtm; take real parts of dets.
    det_inv = np.linalg.det(sigma_inv)
    det_da = np.linalg.det(det_arg)
    pref = np.sqrt(np.real_if_close(det_inv * det_da))
    exp_term = np.exp(-0.5 * deltar @ sigma_inv @ deltar)
    F = pref * exp_term
    F = float(np.real_if_close(F))
    # Numerical guard: clip tiny excursions outside [0, 1]
    if -1e-12 < F < 0.0:
        F = 0.0
    if 1.0 < F < 1.0 + 1e-12:
        F = 1.0
    return F
