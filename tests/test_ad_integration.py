"""Phase 4 F-AD integration tests — end-to-end verification of the dual-backend chain.

Complements the per-function suites (test_ad_gates_* / test_ad_validate /
test_ad_objective) with whole-chain checks that no single-function test can
catch:

- **multi-parameter gradient** (squeeze r + beamsplitter θ jointly) vs 2-D
  central finite difference — catches parameter-coupling errors that 1-D
  gradient tests miss;
- **jitted gradient** ``jax.jit(jax.grad)`` over the full chain equals the
  eager gradient — proves the traced (compiled) path computes the same
  derivative (tracer/`numpy`-validate compatibility, cf. child 3 jit fix);
- **physical sanity** of the scene: TMSV(r) → BS(θ) → E_N(0|1) hits the
  analytic endpoints θ=0 → 2r/ln2 and θ=π/4 → 0 (pure-squeeze limit).

Scene physics (xxpp): two-mode squeezed vacuum at r, then a beamsplitter
mixing modes 0↔1. θ=0 leaves the TMSV intact (E_N = 2r/ln2); θ=π/4 splits the
squeezing equally into two single-mode squeezes (no entanglement, E_N = 0).
Both endpoints are verified, and the interior (θ=0.3, r=0.6) is used for the
gradient checks — well inside the smooth region (no max-kink at ν̃=1/2).
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import backend as be
from cvsim.ad import apply_gaussian, log_neg_loss
from cvsim.symplectic import S_beamsplitter, S_two_mode_squeeze


def _scene(r: float, th: float, backend: str):
    """TMSV(r) → BS(θ) covariance on the requested backend."""
    xp = be._get_xp(backend)
    S2 = S_two_mode_squeeze(2, r, 0, 1, backend=backend)
    V = apply_gaussian(backend, S2, xp.eye(4) * 0.5)
    Sbs = S_beamsplitter(2, 0, 1, th, 0.0, backend=backend)
    return apply_gaussian(backend, Sbs, V)


def _scene_en(backend: str, r: float, th: float):
    """E_N(0|1) of the scene, as a float."""
    return float(log_neg_loss(backend, _scene(r, th, backend), 0))


# ---------------------------------------------------------------------------
# Analytic endpoints of the scene (physical sanity, both backends)
# ---------------------------------------------------------------------------

# jax 参数在无 jax 环境必须干净跳过（Phase 4 exit #2），不能裸用 be.BACKENDS。
_BACKENDS = [
    pytest.param(b, marks=pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed"))
    if b == "jax"
    else b
    for b in be.BACKENDS
]


@pytest.mark.parametrize("backend", _BACKENDS)
@pytest.mark.parametrize("r", [0.3, 0.6])
def test_scene_endpoints(backend: str, r: float) -> None:
    # θ=0: TMSV intact → E_N = 2r/ln2
    np.testing.assert_allclose(_scene_en(backend, r, 0.0), 2 * r / np.log(2), atol=1e-9)
    # θ=π/4: equal split → two single-mode squeezes → E_N = 0
    np.testing.assert_allclose(_scene_en(backend, r, np.pi / 4), 0.0, atol=1e-9)


# ---------------------------------------------------------------------------
# Multi-parameter gradient: (r, θ) jointly vs 2-D central finite difference
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_multiparameter_gradient_vs_fd() -> None:
    import jax

    def objective(r: float, th: float):
        return log_neg_loss("jax", _scene(r, th, "jax"), 0)

    r0, th0 = 0.6, 0.3
    g_r, g_th = map(float, jax.grad(objective, argnums=(0, 1))(r0, th0))

    h = 1e-6
    fd_r = (objective(r0 + h, th0) - objective(r0 - h, th0)) / (2 * h)
    fd_th = (objective(r0, th0 + h) - objective(r0, th0 - h)) / (2 * h)

    np.testing.assert_allclose(g_r, float(fd_r), atol=1e-5, rtol=1e-5)
    np.testing.assert_allclose(g_th, float(fd_th), atol=1e-5, rtol=1e-5)
    # sanity: both gradients are meaningfully non-zero (catches a chain that
    # silently froze one parameter path)
    assert abs(g_r) > 0.5 and abs(g_th) > 0.1


# ---------------------------------------------------------------------------
# jitted gradient over the full chain == eager gradient
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_jitted_gradient_matches_eager() -> None:
    import jax

    def objective(r: float, th: float):
        return log_neg_loss("jax", _scene(r, th, "jax"), 0)

    eager = jax.grad(objective)(0.6, 0.3)
    compiled = jax.jit(jax.grad(objective))(0.6, 0.3)
    np.testing.assert_allclose(np.asarray(compiled), np.asarray(eager), atol=1e-8, rtol=1e-8)


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_jitted_full_objective_matches_numpy() -> None:
    """jit 编译后的整条可微链（含 S_two_mode_squeeze/S_beamsplitter/PT/谱）数值 == numpy。"""
    import jax

    def objective(r: float, th: float):
        return log_neg_loss("jax", _scene(r, th, "jax"), 0)

    for r, th in [(0.4, 0.2), (0.7, 0.5), (0.9, 1.0)]:
        got = float(jax.jit(objective)(r, th))
        np.testing.assert_allclose(got, _scene_en("numpy", r, th), atol=1e-9)
