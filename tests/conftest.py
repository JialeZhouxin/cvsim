"""Shared pytest fixtures and utilities for cvsim test suite.

Design principles:
- Keep fixtures minimal and composable — no "god fixture".
- Default tolerances are strict (atol=1e-12) matching the physics expectations.

**Pruned (2026-09-18 audit §4.8).** This file used to carry twelve symbols that
nothing referenced (verified one by one, definition site excluded):
``vacuum_1`` / ``vacuum_2`` / ``vacuum_3`` fixtures, the ``*_VALUES``
parametrize tables (``SQUEEZING_`` / ``NBAR_`` / ``ALPHA_`` / ``PHASE_`` /
``TRANSMITTANCE_`` / ``NMODE_``), ``assert_allclose_weak`` /
``assert_physical`` / ``assert_pure`` helpers, plus an ``rng`` fixture that no
test ever requested (0 ``def test_*(rng)``; tests call ``default_rng()``
directly) and ``TOL_LOOSE``, whose only user was ``assert_allclose_weak``.
Tests that genuinely need a helper define it next to their own assertions —
a dead fixture is worse than no fixture, because it suggests coverage that
does not exist.
"""

from __future__ import annotations

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Numerical tolerances — single source of truth
# ---------------------------------------------------------------------------

TOL = 1e-12
"""Default atol for physics-correctness assertions."""

# ---------------------------------------------------------------------------
# Backend parametrization (Phase 4 F-AD)
# ---------------------------------------------------------------------------

try:
    import jax  # noqa: F401

    HAS_JAX = True
except ImportError:
    HAS_JAX = False


@pytest.fixture(
    params=[
        "numpy",
        pytest.param("jax", marks=pytest.mark.skipif(not HAS_JAX, reason="jax not installed")),
    ]
)
def backend(request: pytest.FixtureRequest) -> str:
    """Backend name for numpy/jax shared tests (exit 2 of Phase 4)."""
    return request.param


# ---------------------------------------------------------------------------
# Reusable helper functions
# ---------------------------------------------------------------------------


def assert_allclose(actual, desired, msg: str = "") -> None:
    """Assert with strict physics tolerance."""
    np.testing.assert_allclose(actual, desired, atol=TOL, err_msg=msg)


# ---------------------------------------------------------------------------
# Lab result contract helpers (payload-unification, ADR-0008)
# ---------------------------------------------------------------------------


def gaussian_V(res) -> np.ndarray:
    """Gaussian LabResult covariance matrix (xxpp) as an array.

    Under the unified LabResult contract rbar/V ride in ``extensions``
    (JSON-ready lists); this helper restores the array view runner-path tests
    assert against — same shape ``serialize`` serves over the API.
    """
    return np.asarray(res.extensions["V"])


def gaussian_rbar(res) -> np.ndarray:
    """Gaussian LabResult mean vector as an array (see gaussian_V)."""
    return np.asarray(res.extensions["rbar"])


def wigner_result(res) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """LabResult wigner view as an (X, P, W) array triple (runner-path tests).

    Under the unified contract ``res.wigner`` is the sliced ``{x, p, W}``
    payload (or None); this restores the array view the pre-unification
    RunResult exposed. Returns None for the honest-null (singular/empty) case.
    """
    w = res.wigner
    if w is None:
        return None
    return (
        np.asarray(w["x"]),
        np.asarray(w["p"]),
        np.asarray(w["W"]),
    )
