"""Shared pytest fixtures and utilities for cvsim test suite.

Design principles:
- Keep fixtures minimal and composable — no "god fixture".
- Default tolerances are strict (atol=1e-12) matching the physics expectations.
- Parameterized fixture variants for common scan values.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import GaussianState

# ---------------------------------------------------------------------------
# Numerical tolerances — single source of truth
# ---------------------------------------------------------------------------

TOL = 1e-12
"""Default atol for physics-correctness assertions."""

TOL_LOOSE = 1e-8
"""Relaxed atol for numerical operations with larger floating-point error."""


# ---------------------------------------------------------------------------
# Random state seeding — deterministic across runs
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def rng() -> np.random.Generator:
    """Deterministic RNG for reproducible random tests."""
    return np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Common states
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def vacuum_1() -> GaussianState:
    """Single-mode vacuum GaussianState."""
    return GaussianState.vacuum(1)


@pytest.fixture(scope="session")
def vacuum_2() -> GaussianState:
    """Two-mode vacuum GaussianState."""
    return GaussianState.vacuum(2)


@pytest.fixture(scope="session")
def vacuum_3() -> GaussianState:
    """Three-mode vacuum GaussianState."""
    return GaussianState.vacuum(3)


# ---------------------------------------------------------------------------
# Standard parameters for parametrized scanning
# ---------------------------------------------------------------------------

SQUEEZING_VALUES = [0.1, 0.3, 0.6, 1.0]
"""Common squeezing parameters r for parametrize."""

NBAR_VALUES = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]
"""Common thermal photon numbers for parametrize."""

ALPHA_VALUES = [0.1, 0.5 + 0.2j, 1.0 - 0.5j, 1.5j, 2.0]
"""Common displacement amplitudes for parametrize."""

PHASE_VALUES = [0.0, np.pi / 4, np.pi / 2, np.pi, 3 * np.pi / 2]
"""Common phase angles for parametrize."""

TRANSMITTANCE_VALUES = [0.01, 0.1, 0.5, 0.9, 0.99, 1.0]
"""Common loss channel transmittance for parametrize."""

NMODE_VALUES = [1, 2, 3]
"""Common mode counts for parametrize."""

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

def assert_allclose_weak(actual, desired, msg: str = "") -> None:
    """Assert with relaxed tolerance — for stochastic/approximate tests."""
    np.testing.assert_allclose(actual, desired, atol=TOL_LOOSE, err_msg=msg)


def assert_allclose(actual, desired, msg: str = "") -> None:
    """Assert with strict physics tolerance."""
    np.testing.assert_allclose(actual, desired, atol=TOL, err_msg=msg)


def assert_physical(state: GaussianState, msg: str = "") -> None:
    """Assert a GaussianState satisfies the uncertainty relation."""
    assert state.is_physical(), (
        f"State is not physical: {msg}" if msg else "State is not physical"
    )

def assert_pure(state: GaussianState, msg: str = "") -> None:
    """Assert a GaussianState is pure (det(V) = (1/4)^m)."""
    from cvsim.gaussian import det_cov

    expected = 0.25 ** state.nmode
    actual = det_cov(state)
    np.testing.assert_allclose(actual, expected, atol=TOL, err_msg=msg)
