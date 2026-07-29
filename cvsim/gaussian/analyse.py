"""Gaussian analysis helpers (physicality first; more in F-ANALYSE)."""

from __future__ import annotations

import numpy as np

from cvsim.conventions import omega
from cvsim.gaussian.state import GaussianState


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
    if isinstance(state, GaussianState):
        V = state.V
    else:
        V = np.asarray(state, dtype=float)
    if V.ndim != 2 or V.shape[0] != V.shape[1] or V.shape[0] % 2 != 0:
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
