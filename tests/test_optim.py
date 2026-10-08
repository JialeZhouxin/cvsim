"""Tests for :mod:`cvsim.optim` — the minimal optimiser.

Design notes for the reader
---------------------------
The point of this module is to replace three hand-rolled ascent loops.  So the
tests do three jobs, in increasing order of importance:

1. **Numerics** — Adam/SGD actually find the optimum (quadratic closed form;
   the TMSV design objective against a brute-force scan, mirroring
   ``tests/test_ad_objective.py``).
2. **Honest reporting** — ``converged`` / ``reason`` say what really happened.
3. **The criterion cannot lie** — the last group is the soul of the task.  A
   bool that is never questioned can silently always return ``True``; these
   tests construct problems where the answer is known and assert the flag
   agrees, including the cases where it must say *no*.

All tests need jax (the optimiser is jax-only, by design — see the module
docstring); the whole file skips cleanly without it.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import backend as be

pytestmark = pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")

pytest.importorskip("jax")


def _quad(x):
    """Convex quadratic, minimum at (3, -1) with f = 0.

    Hessian diag(2, 4) → the two directions converge at different rates,
    which is exactly what Adam's per-coordinate scaling is for.
    """
    return (x[0] - 3.0) ** 2 + 2.0 * (x[1] + 1.0) ** 2


# ---------------------------------------------------------------------------
# 1. Numerics — does it actually find the optimum?
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("optimiser", ["adam", "sgd"])
def test_quadratic_reaches_closed_form_minimum(optimiser: str) -> None:
    """Both optimisers land on the analytic minimum of a convex quadratic.

    A convex quadratic is the one objective whose answer is not in doubt, so
    it is the right first thing to pin: if the loop cannot descend this, the
    stop criteria below are questions about nothing.
    """
    import jax.numpy as jnp

    res = _run(_quad, jnp.zeros(2), optimiser=optimiser, lr=0.1, max_steps=3000)
    np.testing.assert_allclose(np.asarray(res.x), [3.0, -1.0], atol=1e-4)
    np.testing.assert_allclose(res.f, 0.0, atol=1e-6)


def test_sgd_step_is_the_textbook_formula() -> None:
    """One SGD step must be exactly ``x - lr·g``.

    This is the line the tutorials write by hand; the test pins the library
    version to the same arithmetic so the two cannot drift.
    """
    import jax.numpy as jnp

    from cvsim.optim import sgd_update

    params = {"r": jnp.float64(0.4)}
    grads = {"r": jnp.float64(2.0)}
    new, _ = sgd_update(params, grads, {}, lr={"r": 0.03})
    np.testing.assert_allclose(float(new["r"]), 0.4 - 0.03 * 2.0, atol=1e-15)


def test_per_parameter_learning_rate_is_honoured() -> None:
    """A pytree ``lr`` gives each parameter its own rate (the tutorial-07 shape).

    Two identical quadratics with different rates must end up at different
    distances from their common minimum — and the *faster* rate must be the
    one further along, otherwise ``lr`` is being read as something else.
    """
    import jax.numpy as jnp

    def f(p):
        return (p["a"] - 1.0) ** 2 + (p["b"] - 1.0) ** 2

    res = _run(f, {"a": jnp.float64(0.0), "b": jnp.float64(0.0)},
               optimiser="sgd", lr={"a": 0.2, "b": 0.01}, max_steps=5)
    res = _run(f, {"a": jnp.float64(0.0), "b": jnp.float64(0.0)},
               optimiser="sgd", lr={"a": 0.2, "b": 0.01}, max_steps=5)
    # Distance still to travel before reaching the common minimum at 1.0:
    # the 20× rate has almost arrived, the 1× rate has barely started.
    gap_a = abs(float(res.x["a"]) - 1.0)
    gap_b = abs(float(res.x["b"]) - 1.0)
    assert gap_a < 0.1, f"fast rate stalled: gap_a={gap_a}"
    assert gap_b > 0.8, f"slow rate raced: gap_b={gap_b}"


# ---------------------------------------------------------------------------
# 2. The TMSV design objective, against a brute-force scan
# ---------------------------------------------------------------------------

_LAM = 0.2


def _design_numpy(r: float) -> float:
    """``E_N(TMSV r) − λ·⟨n⟩`` on the numpy path — the scan oracle.

    Mirrors ``tests/test_ad_objective.py::_energy_objective``; the penalty is
    what makes the optimum interior instead of r → ∞.
    """
    from cvsim.ad import log_neg_loss
    from cvsim.symplectic import S_two_mode_squeeze

    S = np.asarray(S_two_mode_squeeze(2, r, 0, 1))
    V = S @ (np.eye(4) * 0.5) @ S.T
    return float(log_neg_loss("numpy", V, 0)) - _LAM * 2.0 * np.sinh(r) ** 2


def _design_jax(p):
    """Same objective on the jax path, negated so ``minimize`` maximises it."""
    import jax.numpy as jnp

    from cvsim.ad import apply_gaussian, log_neg_loss
    from cvsim.symplectic import S_two_mode_squeeze

    S = S_two_mode_squeeze(2, p["r"], 0, 1, backend="jax")
    V = apply_gaussian("jax", S, jnp.eye(4) * 0.5)
    return -(log_neg_loss("jax", V, 0) - _LAM * 2.0 * jnp.sinh(p["r"]) ** 2)


@pytest.mark.parametrize("optimiser", ["adam", "sgd"])
def test_design_objective_matches_brute_scan(optimiser: str) -> None:
    """The optimiser finds the same r* as a 2000-point brute-force scan."""
    import jax.numpy as jnp

    rs = np.linspace(0.01, 4.0, 2000)
    scan = [_design_numpy(float(r)) for r in rs]
    r_scan = float(rs[int(np.argmax(scan))])

    res = _run(_design_jax, {"r": jnp.float64(0.1)},
               optimiser=optimiser, lr=0.05, max_steps=800)
    r_opt = float(res.x["r"])
    np.testing.assert_allclose(r_opt, r_scan, atol=0.02)
    # and it beats where we started
    assert float(_design_numpy(r_opt)) > float(_design_numpy(0.1))


# ---------------------------------------------------------------------------
# 3. The criterion cannot lie
# ---------------------------------------------------------------------------


def test_converged_true_only_with_good_reason() -> None:
    """A run that satisfies ``grad_tol`` reports ``converged=True`` + why."""
    import jax.numpy as jnp

    res = _run(_quad, jnp.zeros(2), optimiser="adam", lr=0.1, max_steps=5000)
    assert res.converged is True
    assert res.reason == "grad_norm"
    # the claimed convergence is backed by the recorded gradient norm
    assert res.grad_norm_history[-1] <= 1e-6


def test_max_steps_does_not_claim_convergence() -> None:
    """Running out of steps must NOT be reported as convergence.

    This is the exact lie the hand-rolled loops used to tell implicitly: they
    always ran a fixed count and you could not tell whether that meant
    "arrived" or "gave up".
    """
    import jax.numpy as jnp

    res = _run(_quad, jnp.zeros(2), optimiser="sgd", lr=1e-4, max_steps=5)
    assert res.converged is False
    assert res.reason == "max_steps"
    assert res.n_steps == 5


def test_flat_objective_with_f_tol_off_does_not_stop_early() -> None:
    """``f_tol=0`` (the default) keeps going on a flat-topped objective.

    Rationale in the module docstring: near the design optimum the objective is
    flat, so a small Δf does not mean a small gradient.  The point here is that
    the flag follows the *configured* criterion, not a guess: on ``x**4`` at
    ``x=0.1`` one step moves f by ~4e-8 while the gradient is still 4e-3, so
    ``f_tol`` fires and ``grad_tol`` cannot.  (Starting at ``x=0`` would be a
    bad test — there the gradient is exactly 0 and ``grad_norm`` fires at step
    zero for reasons that have nothing to do with flatness.)
    """
    import jax.numpy as jnp

    def flat(p):
        return p["x"] ** 4

    x0 = {"x": jnp.float64(0.1)}
    off = _run(flat, x0, optimiser="sgd", lr=0.01, max_steps=50, f_tol=0.0)
    on = _run(flat, x0, optimiser="sgd", lr=0.01, max_steps=50, f_tol=1e-5)

    assert on.n_steps == 1
    assert on.reason == "f_change"
    assert on.converged is True
    assert off.n_steps == 50
    assert off.reason == "max_steps"
    assert off.converged is False


@pytest.mark.parametrize(
    "obj, x0, lr",
    [
        # runaway ascent: x ← x + 4x³ diverges to −inf in a few steps at lr=1
        (lambda t: -(t[0] ** 4), 2.0, 1.0),
        (lambda t: t[0] ** 0.5, 0.0, 0.01),   # inf gradient at the start point
        (lambda t: jnp_log_expr(t), -1.0, 0.01),  # NaN objective
    ],
)
def test_divergence_is_reported_not_swallowed(obj, x0: float, lr: float) -> None:
    """Non-finite value or gradient stops the run with ``reason="diverged"``.

    The old hand-rolled loops would carry a NaN through every remaining step
    and hand you a ``nan`` with no hint which step broke it.
    """
    import jax.numpy as jnp

    res = _run(obj, jnp.array([x0]), optimiser="sgd", lr=lr, max_steps=200)
    assert res.reason == "diverged"
    assert res.converged is False
    # the trace still shows where it went wrong, rather than a bare nan
    assert res.n_steps < 200


def jnp_log_expr(t):
    import jax.numpy as jnp

    return jnp.log(t[0])


# ---------------------------------------------------------------------------
# 4. Trace and validation
# ---------------------------------------------------------------------------


def test_history_lengths_are_consistent() -> None:
    """``history`` starts at the initial point; ``grad_norm_history`` matches steps."""
    import jax.numpy as jnp

    res = _run(_quad, jnp.zeros(2), optimiser="adam", lr=0.1, max_steps=20)
    assert len(res.history) == res.n_steps + 1
    assert len(res.grad_norm_history) == res.n_steps
    np.testing.assert_allclose(res.f, res.history[-1][1], atol=1e-15)


def test_rejects_unknown_optimiser() -> None:
    import jax.numpy as jnp

    from cvsim.optim import minimize

    with pytest.raises(ValueError, match="Unknown optimiser"):
        minimize(_quad, jnp.zeros(2), optimiser="rmsprop")


def test_rejects_bad_max_steps() -> None:
    import jax.numpy as jnp

    from cvsim.optim import minimize

    with pytest.raises(ValueError, match="max_steps"):
        minimize(_quad, jnp.zeros(2), max_steps=0)


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------


def _run(f, x0, **kw):
    """``minimize`` with a test-friendly default: never wander off in silence."""
    from cvsim.optim import minimize

    return minimize(f, x0, **kw)
