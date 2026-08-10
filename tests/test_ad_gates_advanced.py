"""Backend-parameterised gate tests — Phase 4 F-AD child 3 (advanced gates).

Covers ``S_CZ`` / ``S_CX`` / ``U_beamsplitter`` / ``embed_U_2mode`` /
``S_from_unitary`` / ``S_mach_zehnder`` backend= paths:

- numpy path regression vs hard-coded known values
- jax path element-wise identical to numpy path (exit 2)
- ``S_mach_zehnder`` must propagate backend to inner gates (jax path is
  fully jnp — numpy leakage would raise TypeError)
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import backend as be
from cvsim.symplectic import (
    S_CX,
    S_CZ,
    S_from_unitary,
    S_mach_zehnder,
    U_beamsplitter,
    embed_U_2mode,
)

THETA = 0.45
PHI = 0.2
W = 0.7
"""CZ/CX weight."""


# ---------------------------------------------------------------------------
# S_CZ / S_CX
# ---------------------------------------------------------------------------


def test_s_cz_backend(backend: str) -> None:
    S = np.asarray(S_CZ(2, W, 0, 1, backend=backend))
    # xxpp: p1 += w x2, p2 += w x1 → indices (2,1) and (3,0)
    expected = np.eye(4)
    expected[2, 1] = W
    expected[3, 0] = W
    np.testing.assert_allclose(S, expected, atol=1e-12)


def test_s_cx_backend(backend: str) -> None:
    S = np.asarray(S_CX(2, W, 0, 1, backend=backend))
    # xxpp: x2 += w x1 → (1,0); p1 -= w p2 → (2,3)
    expected = np.eye(4)
    expected[1, 0] = W
    expected[2, 3] = -W
    np.testing.assert_allclose(S, expected, atol=1e-12)


def test_s_cz_cx_same_mode_error(backend: str) -> None:
    with pytest.raises(ValueError):
        S_CZ(2, W, 0, 0, backend=backend)
    with pytest.raises(ValueError):
        S_CX(2, W, 0, 0, backend=backend)


# ---------------------------------------------------------------------------
# U_beamsplitter
# ---------------------------------------------------------------------------


def test_u_beamsplitter_backend(backend: str) -> None:
    U = np.asarray(U_beamsplitter(THETA, PHI, backend=backend))
    c, s = np.cos(THETA), np.sin(THETA)
    eip = np.exp(1j * PHI)
    expected = np.array([[c, eip * s], [-np.conj(eip) * s, c]], dtype=complex)
    np.testing.assert_allclose(U, expected, atol=1e-12)


# ---------------------------------------------------------------------------
# embed_U_2mode
# ---------------------------------------------------------------------------


def test_embed_u_2mode_backend(backend: str) -> None:
    U2 = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)  # swap
    U = np.asarray(embed_U_2mode(3, 0, 2, U2, backend=backend))
    expected = np.zeros((3, 3), dtype=complex)
    expected[0, 2] = 1.0
    expected[1, 1] = 1.0
    expected[2, 0] = 1.0
    np.testing.assert_allclose(U, expected, atol=1e-12)


# ---------------------------------------------------------------------------
# S_from_unitary
# ---------------------------------------------------------------------------


def test_s_from_unitary_backend(backend: str) -> None:
    U = U_beamsplitter(THETA, PHI)
    S = np.asarray(S_from_unitary(U, backend=backend))
    expected = np.block([[U.real, -U.imag], [U.imag, U.real]])
    np.testing.assert_allclose(S, expected, atol=1e-12)


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_s_from_unitary_jit_compatible() -> None:
    # OCR finding b91d771: validate must not run on JAX tracers (jit/grad).
    import jax
    import jax.numpy as jnp

    U = jnp.asarray(U_beamsplitter(THETA, PHI))

    @jax.jit
    def build(u):
        return S_from_unitary(u, backend="jax")

    S = np.asarray(build(U))
    expected = np.block([[np.asarray(U).real, -np.asarray(U).imag], [np.asarray(U).imag, np.asarray(U).real]])
    np.testing.assert_allclose(S, expected, atol=1e-12)


def test_s_from_unitary_non_square_backend(backend: str) -> None:
    with pytest.raises(ValueError, match="square"):
        S_from_unitary(np.eye(3, dtype=complex)[:, :2], backend=backend)


# ---------------------------------------------------------------------------
# S_mach_zehnder — backend must propagate to inner S_beamsplitter/S_phase
# ---------------------------------------------------------------------------


def test_s_mach_zehnder_backend(backend: str) -> None:
    S = np.asarray(S_mach_zehnder(2, 0, 1, THETA, PHI, backend=backend))
    assert S.shape == (4, 4)
    # BS chains are symplectic: S Ω Sᵀ = Ω
    from cvsim.conventions import omega

    Om = omega(2)
    np.testing.assert_allclose(S @ Om @ S.T, Om, atol=1e-10)


def test_s_mach_zehnder_matches_numpy_composition(backend: str) -> None:
    # jax path must equal the numpy composition of the fixed decomposition
    S = np.asarray(S_mach_zehnder(2, 0, 1, THETA, PHI, backend=backend))
    from cvsim.symplectic import S_beamsplitter, S_phase

    S1 = S_beamsplitter(2, 0, 1, THETA, 0.0)
    S2 = S_phase(2, PHI, 0)
    S3 = S_beamsplitter(2, 0, 1, np.pi / 4, 0.0)
    np.testing.assert_allclose(S, S3 @ S2 @ S1, atol=1e-12)


# ---------------------------------------------------------------------------
# Gradient spot check (CZ weight is a legitimate optimisation parameter)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_cz_gradient_vs_fd() -> None:
    import jax
    import jax.numpy as jnp

    V0 = jnp.eye(4) * 0.5

    def objective(w: float) -> jnp.ndarray:
        S = S_CZ(2, w, 0, 1, backend="jax")
        return jnp.sum(S @ V0 @ S.T)

    w0 = 0.5
    g = float(jax.grad(objective)(w0))
    h = 1e-6
    fd = (objective(w0 + h) - objective(w0 - h)) / (2 * h)
    np.testing.assert_allclose(g, float(fd), atol=1e-6, rtol=1e-6)
