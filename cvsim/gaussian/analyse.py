"""Gaussian analysis helpers (physicality, symplectic spectrum, purity).

Phase 2 F-ANALYSE: physicality first, then symplectic eigenvalues and purity.
Downstream (entropy_vn, log_negativity, fidelity, partial_trace) come later.
"""

from __future__ import annotations

import numpy as np

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
