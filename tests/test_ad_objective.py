"""Differentiable objective tests — Phase 4 F-AD child 6.

Covers ``cvsim.ad``:

- ``apply_gaussian`` on both backends
- ``log_neg_loss`` numpy path == ``analyse.log_negativity`` (TMSV freeze)
- jax path == numpy path (exit 2)
- **gradient vs finite difference on TMSV squeeze parameter** (exit 1 close)
- **optimisation converges to the numerically-optimal r under loss**
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import backend as be
from cvsim.ad import apply_gaussian, log_neg_loss
from cvsim.gaussian import GaussianState, log_negativity
from cvsim.symplectic import S_squeeze, S_two_mode_squeeze


def _tmsv_cov(r: float) -> np.ndarray:
    """Bare 2-mode TMSV covariance at squeezing r (xxpp)."""
    S = np.asarray(S_two_mode_squeeze(2, r, 0, 1))
    return S @ (np.eye(4) * 0.5) @ S.T


def _loss_channel(T: float, nbar: float = 0.0):
    """Bare-V loss channel (X, Y) on mode 0, mirroring channels.loss."""
    X = np.eye(4, dtype=float)
    Y = np.zeros((4, 4), dtype=float)
    sT = np.sqrt(T)
    y = (1.0 - T) * (nbar + 0.5)
    X[0, 0] = sT
    X[2, 2] = sT
    Y[0, 0] = y
    Y[2, 2] = y
    return X, Y


# ---------------------------------------------------------------------------
# apply_gaussian
# ---------------------------------------------------------------------------


def test_apply_gaussian_backend(backend: str) -> None:
    S = S_squeeze(2, 0.3, 0, backend=backend)
    V0 = np.eye(4) * 0.5
    V = apply_gaussian(backend, S, V0)
    V = np.asarray(V)
    expected = S_squeeze(2, 0.3, 0) @ V0 @ S_squeeze(2, 0.3, 0).T
    np.testing.assert_allclose(V, expected, atol=1e-12)


# ---------------------------------------------------------------------------
# log_neg_loss == analyse.log_negativity (numpy path)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("r", [0.2, 0.5, 0.9])
def test_log_neg_matches_analyse(r: float) -> None:
    V = _tmsv_cov(r)
    state = GaussianState(V=V, rbar=np.zeros(4))
    expected = log_negativity(state, modes_A=0)  # party A = mode 0
    got = float(log_neg_loss("numpy", V, 0))
    np.testing.assert_allclose(got, expected, atol=1e-10)
    # TMSV freeze: E_N = 2r / ln 2 (bits)
    np.testing.assert_allclose(got, 2 * r / np.log(2), atol=1e-10)


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
@pytest.mark.parametrize("r", [0.2, 0.5, 0.9])
def test_log_neg_jax_matches_numpy(r: float) -> None:
    V = _tmsv_cov(r)
    got = float(log_neg_loss("jax", V, 0))
    np.testing.assert_allclose(got, float(log_neg_loss("numpy", V, 0)), atol=1e-10)


def test_log_neg_mode_out_of_range() -> None:
    with pytest.raises(IndexError):
        log_neg_loss("numpy", _tmsv_cov(0.5), 5)


# ---------------------------------------------------------------------------
# Gradient vs finite difference (exit 1 close)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_log_neg_gradient_vs_fd() -> None:
    import jax
    import jax.numpy as jnp

    def objective(r: float) -> jnp.ndarray:
        S = S_two_mode_squeeze(2, r, 0, 1, backend="jax")
        V = apply_gaussian("jax", S, jnp.eye(4) * 0.5)
        return log_neg_loss("jax", V, 0)

    r0 = 0.5
    g = float(jax.grad(objective)(r0))
    h = 1e-6
    fd = (objective(r0 + h) - objective(r0 - h)) / (2 * h)
    np.testing.assert_allclose(g, float(fd), atol=1e-5, rtol=1e-5)


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_log_neg_gradient_analytic_freeze() -> None:
    # dE_N/dr = 2/ln 2 on TMSV (E_N = 2r/ln 2 before any loss)
    import jax

    def objective(r: float):
        S = S_two_mode_squeeze(2, r, 0, 1, backend="jax")
        V = apply_gaussian("jax", S, np.eye(4) * 0.5)
        return log_neg_loss("jax", V, 0)

    g = float(jax.grad(objective)(0.7))
    np.testing.assert_allclose(g, 2.0 / np.log(2.0), atol=1e-5)


# ---------------------------------------------------------------------------
# Optimisation: TMSV → loss η → max [E_N(r) − λ·2sinh²r] over r
# ---------------------------------------------------------------------------
# Physics note (child 6 planning): E_N(r) *saturates* under loss (no interior
# maximum in r alone), so the raw "max E_N under loss" has its optimum at
# r→∞. Adding an energy penalty λ·⟨n⟩ (⟨n⟩ = 2sinh²r for TMSV) makes the
# objective "entanglement is not free" — an interior optimum r*(λ, η) that
# gradient ascent must find. This is the notebook's story.


def _entangled_after_loss(r: float, eta: float) -> float:
    """E_N of TMSV(r) with mode 0 passing a loss channel of transmittance η."""
    S = np.asarray(S_two_mode_squeeze(2, r, 0, 1))
    V = S @ (np.eye(4) * 0.5) @ S.T
    X, Y = _loss_channel(eta)
    V_l = X @ V @ X.T + Y
    return float(log_neg_loss("numpy", V_l, 0))


def _energy_objective(r: float, eta: float, lam: float) -> float:
    """E_N(r; η) − λ·⟨n⟩ with ⟨n⟩ = 2sinh²r (TMSV total photon number)."""
    return _entangled_after_loss(r, eta) - lam * 2.0 * np.sinh(r) ** 2


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
@pytest.mark.parametrize("eta,lam", [(0.3, 0.5), (0.7, 0.2)])
def test_optimisation_converges_to_scan_optimum(eta: float, lam: float) -> None:
    import jax
    import jax.numpy as jnp

    def objective(r: float) -> jnp.ndarray:
        S = S_two_mode_squeeze(2, r, 0, 1, backend="jax")
        V = apply_gaussian("jax", S, jnp.eye(4) * 0.5)
        X, Y = _loss_channel(eta)
        V_l = jnp.asarray(X) @ V @ jnp.asarray(X).T + jnp.asarray(Y)
        e = log_neg_loss("jax", V_l, 0)
        return e - lam * 2.0 * jnp.sinh(r) ** 2

    # reference: brute-force 1D scan
    rs = np.linspace(0.01, 4.0, 400)
    objs = [_energy_objective(r, eta, lam) for r in rs]
    r_opt_scan = rs[int(np.argmax(objs))]

    # gradient ascent (maximise objective), 150 steps
    r = 0.1
    lr = 0.03
    for _ in range(150):
        g = jax.grad(objective)(r)
        r += lr * float(g)
        r = min(max(r, 0.01), 4.0)  # clamp to scan range
    np.testing.assert_allclose(r, r_opt_scan, atol=0.05)
    # and the optimised value beats the start
    assert float(objective(r)) > float(objective(0.1))
