"""The Walrus interop adapter (vision §8).

Exports a cvsim ``GaussianState`` (ħ=1, xxpp) into The Walrus
conventions, plus thin GBS probability/sampling wrappers (``pnr_probs``,
``gbs_sample``, ``threshold_sample``). Optional extra: ``cvsim[gbs]`` —
the walrus is imported lazily inside the wrappers; this module has no
hard dependency on it.
"""

from __future__ import annotations

from types import ModuleType

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


def _require_state(state: object) -> None:
    """Guard: walrus-facing APIs take cvsim states only."""
    if not isinstance(state, GaussianState):
        raise TypeError(f"state must be a GaussianState, got {type(state).__name__}")


def _check_positive_int(name: str, value: object) -> None:
    if not isinstance(value, (int, np.integer)) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive int, got {value!r}")


def _walrus_module(submodule: str) -> ModuleType:
    """Lazy-import a thewalrus submodule; RuntimeError when ``cvsim[gbs]`` is missing."""
    try:
        import importlib

        return importlib.import_module(f"thewalrus.{submodule}")
    except ImportError as e:
        raise RuntimeError("cvsim GBS requires thewalrus: pip install cvsim[gbs]") from e


def pnr_probs(state: GaussianState, cutoff: int) -> np.ndarray:
    """PNR joint distribution P(n1, ..., nm) of a Gaussian state.

    Returns shape ``[cutoff]^m`` (m = number of modes), where
    ``P[n1, ..., nm]`` is the probability of detecting (n1..nm) photons,
    nᵢ ∈ {0..cutoff−1}. ``P.sum() < 1`` is normal truncation leakage —
    the array is **not** renormalized.

    Implementation: ``thewalrus.quantum.probabilities`` on
    ``export_cov_for_walrus(state)`` (ħ=2, xxpp — fixed, no hbar knob;
    the export already normalizes σ = 2V). Lazy import — raises
    ``RuntimeError`` (with install hint) when ``cvsim[gbs]`` is missing.

    RNG is not injectable: thewalrus draws from the global ``np.random``
    (unlike cvsim sampling APIs that take ``rng=``) — upstream constraint.

    Gaussian counterpart of the fock-side ``pnrd_probs`` (which takes a
    FockLike state and reads |c|² / diag ρ).

    Args:
        state: cvsim ``GaussianState`` (ħ=1, xxpp).
        cutoff: Fock truncation per mode; nᵢ ∈ {0..cutoff−1}.

    Returns:
        Joint P(n1..nm), shape ``(cutoff,) * m``, float.
    """
    _require_state(state)
    _check_positive_int("cutoff", cutoff)
    sigma, mu = export_cov_for_walrus(state)
    return np.asarray(_walrus_module("quantum").probabilities(mu, sigma, cutoff, hbar=2))


def gbs_sample(
    state: GaussianState, n_samples: int, *, cutoff: int = 5, max_photons: int = 30
) -> np.ndarray:
    """Sample PNR outcomes (n1..nm) from a Gaussian state, shape ``(n_samples, m)``.

    Implementation: ``thewalrus.samples.hafnian_sample_state`` on
    ``export_cov_for_walrus(state)`` (ħ=2, xxpp). Lazy import — raises
    ``RuntimeError`` (with install hint) when ``cvsim[gbs]`` is missing.

    RNG is not injectable: thewalrus draws from the global ``np.random``
    (unlike cvsim sampling APIs that take ``rng=``) — upstream constraint.
    Out-of-truncation samples (per-mode ``cutoff`` / total ``max_photons``)
    are internally rejected and resampled by thewalrus, so the output has
    exactly ``n_samples`` rows.

    Args:
        state: cvsim ``GaussianState`` (ħ=1, xxpp).
        n_samples: number of samples to draw.
        cutoff: per-mode Fock truncation (default 5).
        max_photons: total-photon rejection cap (default 30).

    Returns:
        int64 array of PNR samples, shape ``(n_samples, m)``.
    """
    _require_state(state)
    _check_positive_int("n_samples", n_samples)
    _check_positive_int("cutoff", cutoff)
    _check_positive_int("max_photons", max_photons)
    sigma, mu = export_cov_for_walrus(state)
    samples = _walrus_module("samples").hafnian_sample_state(
        sigma, n_samples, mean=mu, hbar=2, cutoff=cutoff, max_photons=max_photons
    )
    return np.asarray(samples, dtype=np.int64)


def threshold_sample(
    state: GaussianState, n_samples: int, *, max_photons: int = 30, fanout: int = 10
) -> np.ndarray:
    """Sample threshold (click-pattern) outcomes from a Gaussian state.

    Returns shape ``(n_samples, m)`` int8, values ∈ {0, 1}: 1 = at least
    one photon detected in that mode.

    Implementation: ``thewalrus.samples.torontonian_sample_state`` on
    ``export_cov_for_walrus(state)`` (ħ=2, xxpp). Lazy import — raises
    ``RuntimeError`` (with install hint) when ``cvsim[gbs]`` is missing.

    RNG is not injectable: thewalrus draws from the global ``np.random``
    (unlike cvsim sampling APIs that take ``rng=``) — upstream constraint.
    Out-of-truncation samples (total ``max_photons`` / ``fanout``) are
    internally rejected and resampled by thewalrus.

    Args:
        state: cvsim ``GaussianState`` (ħ=1, xxpp).
        n_samples: number of samples to draw.
        max_photons: total-photon rejection cap (default 30).
        fanout: torontonian fanout parameter (default 10).

    Returns:
        int8 click patterns, shape ``(n_samples, m)``.
    """
    _require_state(state)
    _check_positive_int("n_samples", n_samples)
    _check_positive_int("max_photons", max_photons)
    _check_positive_int("fanout", fanout)
    sigma, mu = export_cov_for_walrus(state)
    samples = _walrus_module("samples").torontonian_sample_state(
        sigma, n_samples, mu=mu, hbar=2, max_photons=max_photons, fanout=fanout
    )
    return np.asarray(samples, dtype=np.int8)
