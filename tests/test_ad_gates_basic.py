"""Backend-parameterised gate tests — Phase 4 F-AD child 2 (basic gates).

Covers ``d_displace`` / ``S_squeeze`` / ``S_phase`` / ``S_beamsplitter`` /
``S_two_mode_squeeze`` backend= paths:

- numpy path regression vs hard-coded known values
- jax path element-wise identical to numpy path (exit 2: shared tests)
- JAX gradient vs central finite difference (exit 1: squeeze/BS params)
- error paths consistent across backends
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import backend as be
from cvsim.symplectic import (
    S_beamsplitter,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    d_displace,
)

R = 0.3
"""Squeezing parameter for gate tests."""

THETA = 0.45
"""BS angle for gate tests."""

PHI = 0.2
"""BS phase for gate tests."""


# ---------------------------------------------------------------------------
# d_displace
# ---------------------------------------------------------------------------


def test_d_displace_known_values() -> None:
    d = d_displace(2, 0.5 + 1.5j, mode=1)
    assert d.shape == (4,)
    np.testing.assert_allclose(
        d, [0.0, np.sqrt(2.0) * 0.5, 0.0, np.sqrt(2.0) * 1.5], atol=1e-12
    )


def test_d_displace_backend(backend: str) -> None:
    d = d_displace(2, 0.5 + 1.5j, mode=1, backend=backend)
    np.testing.assert_allclose(
        np.asarray(d), [0.0, np.sqrt(2.0) * 0.5, 0.0, np.sqrt(2.0) * 1.5], atol=1e-12
    )


def test_d_displace_index_error(backend: str) -> None:
    with pytest.raises(IndexError):
        d_displace(2, 1.0, mode=2, backend=backend)


# ---------------------------------------------------------------------------
# S_squeeze
# ---------------------------------------------------------------------------


def test_s_squeeze_backend(backend: str) -> None:
    S = S_squeeze(2, R, mode=0, backend=backend)
    S = np.asarray(S)
    assert S.shape == (4, 4)
    np.testing.assert_allclose(S[0, 0], np.exp(-R), atol=1e-12)
    np.testing.assert_allclose(S[2, 2], np.exp(R), atol=1e-12)
    np.testing.assert_allclose(S[0, 2], 0.0, atol=1e-12)
    np.testing.assert_allclose(S[1, 1], 1.0, atol=1e-12)


def test_s_squeeze_index_error(backend: str) -> None:
    with pytest.raises(IndexError):
        S_squeeze(2, R, mode=2, backend=backend)


# ---------------------------------------------------------------------------
# S_phase
# ---------------------------------------------------------------------------


def test_s_phase_backend(backend: str) -> None:
    # xxpp: mode 0 x->idx0, p->idx2 (nmode + 0)
    S = np.asarray(S_phase(2, THETA, mode=0, backend=backend))
    c, s = np.cos(THETA), np.sin(THETA)
    expected = np.eye(4)
    expected[0, 0], expected[0, 2] = c, -s
    expected[2, 0], expected[2, 2] = s, c
    np.testing.assert_allclose(S, expected, atol=1e-12)


# ---------------------------------------------------------------------------
# S_beamsplitter
# ---------------------------------------------------------------------------


def test_s_beamsplitter_backend(backend: str) -> None:
    S = np.asarray(S_beamsplitter(2, 0, 1, THETA, PHI, backend=backend))
    c, s = np.cos(THETA), np.sin(THETA)
    eip = np.exp(1j * PHI)
    U = np.array([[c, eip * s], [-np.conj(eip) * s, c]], dtype=complex)
    expected = np.block([[U.real, -U.imag], [U.imag, U.real]])
    np.testing.assert_allclose(S, expected, atol=1e-12)


def test_s_beamsplitter_nmode3_backend(backend: str) -> None:
    # embedding on modes (0, 2) of 3 modes — block layout exercise
    S = np.asarray(S_beamsplitter(3, 0, 2, THETA, PHI, backend=backend))
    assert S.shape == (6, 6)
    # untouched mode 1 block must stay identity
    np.testing.assert_allclose(S[1, 1], 1.0, atol=1e-12)
    np.testing.assert_allclose(S[4, 4], 1.0, atol=1e-12)


def test_s_beamsplitter_same_mode_error(backend: str) -> None:
    with pytest.raises(ValueError):
        S_beamsplitter(2, 0, 0, THETA, backend=backend)


# ---------------------------------------------------------------------------
# S_two_mode_squeeze
# ---------------------------------------------------------------------------


def test_s_two_mode_squeeze_backend(backend: str) -> None:
    S = np.asarray(S_two_mode_squeeze(2, R, 0, 1, backend=backend))
    ch, sh = np.cosh(R), np.sinh(R)
    expected = np.array(
        [
            [ch, sh, 0.0, 0.0],
            [sh, ch, 0.0, 0.0],
            [0.0, 0.0, ch, -sh],
            [0.0, 0.0, -sh, ch],
        ]
    )
    np.testing.assert_allclose(S, expected, atol=1e-12)


# ---------------------------------------------------------------------------
# Gradients vs finite difference (exit 1)
# ---------------------------------------------------------------------------

_VAC = np.eye(4) * 0.5
"""2-mode vacuum covariance (xxpp)."""


def _apply_objective(S: np.ndarray) -> float:
    """Scalar objective: sum of evolved vacuum covariance entries."""
    return float(np.sum(S @ _VAC @ S.T))


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_squeeze_gradient_vs_fd() -> None:
    import jax
    import jax.numpy as jnp

    def objective(r: float) -> jnp.ndarray:
        S = S_squeeze(2, r, 0, backend="jax")
        return jnp.sum(S @ (jnp.asarray(_VAC)) @ S.T)

    r0 = 0.6
    g = float(jax.grad(objective)(r0))
    h = 1e-6
    fd = (objective(r0 + h) - objective(r0 - h)) / (2 * h)
    np.testing.assert_allclose(g, float(fd), atol=1e-6, rtol=1e-6)


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_beamsplitter_gradient_vs_fd() -> None:
    import jax
    import jax.numpy as jnp

    def objective(theta: float) -> jnp.ndarray:
        S = S_beamsplitter(2, 0, 1, theta, PHI, backend="jax")
        return jnp.sum(S @ jnp.asarray(_VAC) @ S.T)

    t0 = 0.4
    g = float(jax.grad(objective)(t0))
    h = 1e-6
    fd = (objective(t0 + h) - objective(t0 - h)) / (2 * h)
    np.testing.assert_allclose(g, float(fd), atol=1e-6, rtol=1e-6)


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_two_mode_squeeze_gradient_vs_fd() -> None:
    import jax
    import jax.numpy as jnp

    def objective(r: float) -> jnp.ndarray:
        S = S_two_mode_squeeze(2, r, 0, 1, backend="jax")
        return jnp.sum(S @ jnp.asarray(_VAC) @ S.T)

    r0 = 0.35
    g = float(jax.grad(objective)(r0))
    h = 1e-6
    fd = (objective(r0 + h) - objective(r0 - h)) / (2 * h)
    np.testing.assert_allclose(g, float(fd), atol=1e-6, rtol=1e-6)
