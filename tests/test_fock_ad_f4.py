"""Phase F4: Fock differentiable designer — numpy/jax shared tests.

Vision F4 exit criteria:
1. Gradients agree with finite difference (squeeze/BS/Kerr) — Gaussian
   Phase 4 bar (h=1e-6, atol=1e-6).
2. Numpy and JAX paths share tests via the conftest ``backend`` fixture.

jax-less environments: all jax cases skip (fixture mark); numpy stays green.
"""

from __future__ import annotations

import numpy as np
import pytest

import cvsim.backend as be
import cvsim.fock as fock
from cvsim.fock_ad import (
    _cat_amps,
    _loss_superop,
    bs_overlap,
    bs_u,
    cat_fidelity,
    kerr_diag,
    squeeze_u,
)

JAX = pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")

# ---------------------------------------------------------------------------
# Exit 2: numpy/jax path identity (conftest `backend` fixture parametrizes)
# ---------------------------------------------------------------------------


def test_squeeze_u_identity(backend: str):
    """jax path == numpy path; numpy path reuses the gates source of truth."""
    U = np.asarray(squeeze_u(backend, 6, 0.4))
    np.testing.assert_allclose(U, squeeze_u("numpy", 6, 0.4), atol=1e-12)
    np.testing.assert_allclose(U, fock.gates._squeeze_U(6, 0.4), atol=1e-12)


def test_bs_u_identity(backend: str):
    """jax path == numpy path; numpy path matches gates.beamsplitter on |1,0⟩."""
    N = 6
    U = np.asarray(bs_u(backend, N, 0.3, 0.2))
    np.testing.assert_allclose(U, bs_u("numpy", N, 0.3, 0.2), atol=1e-12)
    vec10 = np.zeros(N * N, dtype=complex)
    vec10[N] = 1.0  # |1,0⟩ row-major index n0·N + n1
    ref = fock.beamsplitter(fock.FockState.fock2(1, 0, N), 0.3, 0.2).amps.reshape(N * N)
    np.testing.assert_allclose(U @ vec10, ref, atol=1e-12)


def test_kerr_diag_identity(backend: str):
    """jax path == numpy path; numpy path matches gates.kerr on a coherent state."""
    N = 6
    chi = 0.25
    D = np.asarray(kerr_diag(backend, N, chi))
    np.testing.assert_allclose(D, kerr_diag("numpy", N, chi), atol=1e-12)
    st = fock.FockState.coherent(N, 0.8 + 0.3j)
    np.testing.assert_allclose(D @ st.amps, fock.kerr(st, chi).amps, atol=1e-12)


@pytest.mark.parametrize("r,chi", [(0.3, 0.2), (0.7, 0.4), (1.1, 0.8)])
def test_cat_fidelity_identity(backend: str, r: float, chi: float):
    """Full chain (squeeze→Kerr→|0⟩→ρ→loss→cat fidelity) numpy == jax."""
    for T in (1.0, 0.85):
        f_np = float(cat_fidelity("numpy", r, chi, alpha=1.1, T=T, cutoff=12))
        f_jx = float(cat_fidelity(backend, r, chi, alpha=1.1, T=T, cutoff=12))
        assert abs(f_np - f_jx) < 1e-10
        assert 0.0 <= f_np <= 1.0


def test_cat_fidelity_loss_reduces(backend: str):
    """Loss can only reduce fidelity to the (lossless) cat target."""
    f0 = float(cat_fidelity(backend, 0.7, 0.4, alpha=1.1, T=1.0, cutoff=12))
    f1 = float(cat_fidelity(backend, 0.7, 0.4, alpha=1.1, T=0.7, cutoff=12))
    assert f1 < f0


@pytest.mark.parametrize("theta", [0.1, 0.4, 0.9])
def test_bs_overlap_identity(backend: str, theta: float):
    """|⟨0,1|BS(θ)|1,0⟩|² = sin²θ, numpy == jax."""
    o = float(bs_overlap(backend, theta, cutoff=8))
    np.testing.assert_allclose(o, np.sin(theta) ** 2, atol=1e-12)
    np.testing.assert_allclose(o, bs_overlap("numpy", theta, cutoff=8), atol=1e-12)


def test_cat_amps_match_factory():
    """Inlined cat amplitudes == FockState.cat (atol covers the factory's
    truncation renormalisation 1/√(1−tail))."""
    c = np.asarray(_cat_amps(np, 12, 1.1))
    np.testing.assert_allclose(c, fock.FockState.cat(12, 1.1, even=True).amps, atol=1e-6)


def test_loss_superop_matches_channel():
    """einsum loss superoperator == channels._apply_kraus_1mode (numpy)."""
    rng = np.random.default_rng(0)
    rho = rng.normal(size=(12, 12)) + 1j * rng.normal(size=(12, 12))
    rho = rho @ rho.conj().T
    rho /= np.trace(rho)
    np.testing.assert_allclose(
        np.asarray(_loss_superop(np, rho, 0.85)),
        fock.channels._apply_kraus_1mode(rho, 0.85),
        atol=1e-12,
    )


# ---------------------------------------------------------------------------
# Exit 1: gradients vs central finite difference (jax required)
# ---------------------------------------------------------------------------

H = 1e-6
ATOL = 1e-6


def _fd(f, x0: float) -> float:
    return (float(f(x0 + H)) - float(f(x0 - H))) / (2 * H)


@JAX
def test_grad_squeeze_vs_fd():
    """dF/dr through the full cat chain: jax.grad == central fd."""
    import jax

    chi0 = 0.2
    r0 = 0.3

    def f(r):
        return cat_fidelity("jax", r, chi0, alpha=1.1, T=0.85, cutoff=12)

    g = float(jax.grad(f)(r0))
    assert abs(g - _fd(f, r0)) < ATOL


@JAX
def test_grad_bs_vs_fd():
    """d|⟨0,1|BS(θ)|1,0⟩|²/dθ == 2 sinθ cosθ == central fd."""
    import jax

    th = 0.4

    def f(t):
        return bs_overlap("jax", t, cutoff=8)

    g = float(jax.grad(f)(th))
    assert abs(g - 2.0 * np.sin(th) * np.cos(th)) < ATOL
    assert abs(g - _fd(f, th)) < ATOL


@JAX
def test_grad_kerr_vs_fd():
    """dF/dχ through the full cat chain: jax.grad == central fd."""
    import jax

    r0 = 0.3
    chi0 = 0.2

    def f(chi):
        return cat_fidelity("jax", r0, chi, alpha=1.1, T=0.85, cutoff=12)

    g = float(jax.grad(f)(chi0))
    assert abs(g - _fd(f, chi0)) < ATOL
