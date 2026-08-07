"""The Walrus interop adapter (vision §8).

Exports a cvsim ``GaussianState`` (ħ=1, xxpp) into The Walrus
conventions. Optional extra: ``cvsim[gbs]``. No walrus import here —
the adapter is pure numpy; callers import thewalrus themselves.
"""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState


def export_cov_for_walrus(state: GaussianState) -> tuple[np.ndarray, np.ndarray]:
    """Export ``GaussianState`` → (σ, μ) in The Walrus convention.

    Conventions (metadata, vision §8):
      - ħ: The Walrus default is ``hbar=2``; output σ is normalized so
        vacuum is σ = I, i.e. σ = 2V/ħ = 2V with cvsim ħ = 1.
      - Ordering: with thewalrus >= 0.22 the quantum module uses the
        same **xxpp** (q1..qm, p1..pm) ordering as cvsim — no
        permutation. Verified against thewalrus 0.22.0: ``density_matrix``
        and ``photon_number_mean`` read xxpp blocks (their docstrings say
        "xp-ordering", which is stale for this version; a two-mode TMSV
        cross-check confirms xxpp). The extra pins ``thewalrus>=0.22``.
      - Mean: μ = √2 · r̄ (The Walrus uses SF quadratures x̂ = â+â†,
        vacuum variance 1; cvsim uses x̂ = (â+â†)/√2, vacuum variance ½).
        This makes its complex amplitude (μ[:m] + i·μ[m:])/√(2ħ) equal α.
      - Input is not validated for physicality (like ``GaussianState``
        construction); call ``cvsim.gaussian.validate_state`` if needed.

    Args:
        state: cvsim ``GaussianState`` (ħ=1, xxpp).

    Returns:
        (σ, μ): The Walrus covariance (2m, 2m) and means (2m,), xxpp.
        Fresh arrays; does not alias ``state``.
    """
    if not isinstance(state, GaussianState):
        raise TypeError(f"state must be a GaussianState, got {type(state).__name__}")
    V = np.asarray(state.V, dtype=float)
    if V.ndim != 2 or V.shape[0] != V.shape[1] or V.shape[0] % 2 != 0:
        raise ValueError(f"expected even square covariance, got shape {V.shape}")
    return 2.0 * V, np.sqrt(2.0) * state.rbar
