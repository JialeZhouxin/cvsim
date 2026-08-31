"""Differentiable Gaussian target chain (Phase 4 F-AD, child 6).

jnp mirror of the numpy analysis chain in ``cvsim/gaussian/analyse.py``
(``_partial_transpose_cov`` / ``_symplectic_eigenvalues_raw`` /
``log_negativity``), kept minimal for the optimisation notebook:

    params → S (gates, backend=) → V' = S V Sᵀ → PT → raw spectrum → E_N

Formulas live upstream in ``analyse.py`` (single source of truth); this module
mirrors them on jnp so ``jax.grad`` can trace the parameter path through
squeeze/BS weights. The numpy backend resolves to the same jnp-free math via
``cvsim.backend`` — both paths share the tests (Phase 4 exit 2).

Honesty note: ``log_neg_loss`` mirrors the *per-term* PPT log-negativity
Σⱼ max{0, −log₂(2ν̃ⱼ)} (vision v0.1.3+); see ``analyse.log_negativity``.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from cvsim.backend import _get_xp, _set
from cvsim.conventions import omega


def apply_gaussian(backend: str, S: np.ndarray, V: np.ndarray) -> np.ndarray:
    """Evolve covariance V ↦ S V Sᵀ (xxpp), differentiable in S/V entries.

    Backend-agnostic: accepts numpy or jax arrays; result type follows the
    input arrays (mixed input types are coerced by the backend's asarray).
    """
    xp = _get_xp(backend)
    S = xp.asarray(S, dtype=float)
    V = xp.asarray(V, dtype=float)
    return cast(np.ndarray, S @ V @ S.T)


def _partial_transpose(xp: Any, V: np.ndarray, nmode: int, modes_A: list[int]) -> np.ndarray:
    """V ↦ Λ V Λ with p-quadrature flip on modes_A (xxpp; mirror of analyse)."""
    lam = xp.ones(2 * nmode, dtype=float)
    for k in modes_A:
        lam = _set(xp, lam, (nmode + k,), -1.0)
    L = xp.diag(lam)
    return cast(np.ndarray, L @ V @ L)


def _raw_symplectic_spectrum(xp: Any, V: np.ndarray) -> np.ndarray:
    """|eig(i Ω V)| one-per-pair (no vacuum-floor clip; mirror of analyse).

    PT covariances are typically not positive-definite, so the Cholesky path
    is unsuitable — this is the direct-eigval route used by log-negativity.
    """
    m = V.shape[0] // 2
    ev = xp.linalg.eigvals(1j * xp.asarray(omega(m)) @ V)
    nu_all = xp.sort(xp.abs(ev.real))
    return cast(np.ndarray, nu_all[::2])


def log_neg_loss(backend: str, V: np.ndarray, modes_A: int) -> float:
    """Log-negativity E_N(V, modes_A) in bits — jnp-differentiable.

    Mirrors ``analyse.log_negativity`` on the given backend:

        E_N = Σⱼ max{0, −log₂(2 ν̃ⱼ)}

    Only ``modes_A: int`` (single-mode party A) is supported — enough for the
    optimisation notebook's bipartition; iterable A is a ponytail: add when a
    multi-mode party needs gradient descent.

    The numpy backend returns a float64 scalar (np.ndarray 0-d or float);
    jax returns a traced scalar suitable for ``jax.grad``.
    """
    xp = _get_xp(backend)
    V = xp.asarray(V, dtype=float)
    V = 0.5 * (V + V.T)
    m = V.shape[0] // 2
    A = [int(modes_A)]
    if not 0 <= A[0] < m:
        raise IndexError(f"mode {modes_A} out of range for nmode={m}")
    Vp = _partial_transpose(xp, V, m, A)
    nu = _raw_symplectic_spectrum(xp, Vp)
    # log2 guard mirrors analyse.py (floor only against float noise, not a cutoff)
    contrib = -xp.log2(xp.maximum(2.0 * nu, 1e-300))
    return cast(float, xp.sum(xp.maximum(contrib, 0.0)))
