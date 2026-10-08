"""Minimal differentiable-parameter optimiser (hand-written; zero new deps).

Why this module exists
----------------------
``cvsim/ad.py`` and ``cvsim/fock_ad.py`` give you *gradients*; they do not give
you a *loop*.  Before this module, every consumer hand-rolled the same ascent::

    r += 0.03 * float(jax.grad(objective)(r))   # 60 steps in tutorial 05,
                                                # 150 steps in tutorial 07,
                                                # 150 steps in test_ad_objective

with three hard-coded learning rates (0.03 / 0.05 / 0.02), fixed step counts,
manual ``np.clip`` box projections, and no way to say *whether* a run
converged.  This module collapses those copies into one tested entry point.

Scope (deliberately not more)
-----------------------------
Two optimisers (Adam; plain SGD with optional momentum), three stop criteria,
and a trace-returning result.  **No callback, no objective base class, no
logging framework, no optax.**  The tutorials plot *after* the run, so
returning the trace is enough — and a trace can be asserted on in tests, where
a callback cannot.

Why this is top-level, not inside a representation package
----------------------------------------------------------
ADR-0001 forbids ``cvsim.gaussian`` / ``cvsim.fock`` / ``cvsim.bosonic`` from
importing anything but ``conventions`` and ``symplectic``.  Same reason
``cvsim/ad.py`` and ``cvsim/bridge.py`` are top-level.

Why there is no ``backend=`` keyword
------------------------------------
Optimisation *needs* ``jax.grad``; numpy alone cannot supply a gradient.  A
``backend="numpy"`` option would be fake symmetry, so this module is jax-only
and imports it lazily (the core import path stays jax-free, per vision: "No AD
in core import path").
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Result:
    """Outcome of :func:`minimize` — a trace you can plot *and* assert on.

    Attributes:
        x: Final parameters, same pytree structure as the input.
        f: Final objective value.
        n_steps: Number of update steps actually taken.
        converged: ``True`` only when a stop criterion fired for a *good*
            reason (gradient norm or objective change).  ``False`` when the run
            merely hit ``max_steps`` or diverged — never fabricated.
        reason: Why the loop stopped: ``"grad_norm"`` / ``"f_change"`` /
            ``"max_steps"`` / ``"diverged"``.
        history: Per-step ``(x, f)`` pairs, starting at the initial point.
        grad_norm_history: Per-step gradient inf-norm, so "is the gradient
            actually falling?" is plottable.
    """

    x: Any
    f: float
    n_steps: int
    converged: bool
    reason: str
    history: list[tuple[Any, float]] = field(default_factory=list)
    grad_norm_history: list[float] = field(default_factory=list)


def _require_jax() -> Any:
    """Lazy ``import jax`` with the house install hint.

    Delegates to :func:`cvsim.backend.require_jax` first: that is the one
    place that turns on ``jax_enable_x64``, and this module's stop criteria
    compare gradient norms against tolerances like ``1e-6`` — in float32 the
    whole loop would be running on a different floating-point contract than
    the rest of cvsim.
    """
    from cvsim import backend

    try:
        backend.require_jax()  # side effect: forces jax_enable_x64
    except ImportError:
        raise ImportError(
            "cvsim.optim requires jax; run `pip install -e '.[jax]'` "
            "(or `pip install jax[cpu]`)"
        ) from None
    import jax

    return jax


def _leaves(tree: Any) -> list[np.ndarray]:
    """Flatten a pytree to a list of numpy arrays (host-side view)."""
    jax = _require_jax()
    return [np.asarray(leaf) for leaf in jax.tree_util.tree_leaves(tree)]


def _grad_norm(grads: Any) -> float:
    """Inf-norm over a pytree: ``max`` over leaves of ``max|leaf|``."""
    worst = 0.0
    for leaf in _leaves(grads):
        if leaf.size:
            worst = max(worst, float(np.max(np.abs(leaf))))
    return worst


def _lr_tree(x0: Any, lr: Any) -> Any:
    """Normalise ``lr`` (scalar or pytree) to a pytree shaped like ``x0``."""
    jax = _require_jax()

    if isinstance(lr, (int, float)):
        return jax.tree_util.tree_map(lambda _leaf: float(lr), x0)
    return jax.tree_util.tree_map(float, lr)


def adam_update(
    params: Any,
    grads: Any,
    state: dict[str, Any],
    *,
    lr: Any,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
) -> tuple[Any, dict[str, Any]]:
    """One Adam step (``lr`` is a pytree shaped like ``params``).

    ``m ← β₁m + (1−β₁)g``, ``v ← β₂v + (1−β₂)g²``, then the bias-corrected
    ``x ← x − lr·m̂ / (√v̂ + eps)``.  Textbook formulas; nothing invented.
    """
    jax = _require_jax()
    t = state["t"] + 1
    m = jax.tree_util.tree_map(lambda mi, g: beta1 * mi + (1 - beta1) * g, state["m"], grads)
    v = jax.tree_util.tree_map(lambda vi, g: beta2 * vi + (1 - beta2) * g**2, state["v"], grads)
    bc1 = 1.0 - beta1**t
    bc2 = 1.0 - beta2**t
    new = jax.tree_util.tree_map(
        lambda x, mi, vi, rate: x - rate * (mi / bc1) / (jax.numpy.sqrt(vi / bc2) + eps),
        params,
        m,
        v,
        lr,
    )
    return new, {"m": m, "v": v, "t": t}


def sgd_update(
    params: Any,
    grads: Any,
    state: dict[str, Any],
    *,
    lr: Any,
    momentum: float = 0.0,
) -> tuple[Any, dict[str, Any]]:
    """One SGD step (``lr`` is a pytree shaped like ``params``).

    With ``momentum=0`` this is ``x ← x − lr·g`` — the executable form of the
    formula the tutorials write by hand.  Otherwise heavy-ball:
    ``vel ← μ·vel + g``, ``x ← x − lr·vel``.
    """
    jax = _require_jax()
    if momentum == 0.0:
        new = jax.tree_util.tree_map(lambda x, g, rate: x - rate * g, params, grads, lr)
        return new, {}
    vel = jax.tree_util.tree_map(
        lambda vi, g: momentum * vi + g,
        state.get("velocity", jax.tree_util.tree_map(lambda leaf: leaf * 0.0, grads)),
        grads,
    )
    new = jax.tree_util.tree_map(lambda x, vi, rate: x - rate * vi, params, vel, lr)
    return new, {"velocity": vel}


def minimize(
    f: Callable[[Any], Any],
    x0: Any,
    *,
    optimiser: str = "adam",
    lr: Any = 0.01,
    max_steps: int = 500,
    grad_tol: float = 1e-6,
    f_tol: float = 0.0,
    momentum: float = 0.0,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
) -> Result:
    """Descend ``f`` from ``x0`` and return a :class:`Result`.

    To *maximise* (what the design notebooks do), negate: ``minimize(lambda r:
    -objective(r), ...)``.

    Args:
        f: Objective, pytree in → scalar out.  Must be ``jax.grad``-traceable,
            i.e. built from the ``backend="jax"`` maths of ``cvsim.ad`` /
            ``cvsim.fock_ad``.
        x0: Initial parameters — any pytree; a bare array is the
            one-parameter case.
        optimiser: ``"adam"`` or ``"sgd"``.
        lr: Learning rate, scalar or a pytree matching ``x0`` (per-parameter
            rates, e.g. ``{"r": 0.05, "chi": 0.02}``).
        max_steps: Hard iteration cap, always enforced.
        grad_tol: Stop when the gradient inf-norm reaches this.  ``0.0``
            disables it.
        f_tol: Stop when ``|Δf|`` reaches this.  **Default ``0.0`` (off) on
            purpose**: the design objectives are flat-topped near the optimum,
            so a small ``Δf`` does not imply a small gradient — enabling this
            by default would stop early and report a wrong optimum.  Turn it on
            only for objectives with a genuine sharp minimum.
        momentum: Heavy-ball coefficient for ``optimiser="sgd"`` (0 = plain).
        beta1, beta2, eps: Adam hyperparameters (standard defaults).

    Returns:
        Result: ``converged`` distinguishes "a criterion was satisfied" from
        "we ran out of steps" and never claims the former falsely.
    """
    jax = _require_jax()

    if optimiser not in ("adam", "sgd"):
        raise ValueError(f"Unknown optimiser {optimiser!r}; expected 'adam' or 'sgd'")
    if max_steps < 1:
        raise ValueError(f"max_steps must be >= 1, got {max_steps}")

    lr_tree = _lr_tree(x0, lr)
    x = jax.tree_util.tree_map(jax.numpy.asarray, x0)
    grad_fn = jax.grad(f)

    f_val = float(f(x))
    history: list[tuple[Any, float]] = [(x, f_val)]
    grad_norms: list[float] = []
    state: dict[str, Any] = (
        {"m": jax.tree_util.tree_map(lambda leaf: leaf * 0.0, x),
         "v": jax.tree_util.tree_map(lambda leaf: leaf * 0.0, x),
         "t": 0}
        if optimiser == "adam"
        else {}
    )

    n_steps = 0
    reason = "max_steps"
    converged = False

    for _ in range(max_steps):
        grads = grad_fn(x)
        gnorm = _grad_norm(grads)
        grad_norms.append(gnorm)

        if not np.isfinite(gnorm) or not np.isfinite(f_val):
            reason = "diverged"
            break
        if grad_tol > 0.0 and gnorm <= grad_tol:
            reason, converged = "grad_norm", True
            break

        if optimiser == "adam":
            x, state = adam_update(
                x, grads, state, lr=lr_tree, beta1=beta1, beta2=beta2, eps=eps
            )
        else:
            x, state = sgd_update(x, grads, state, lr=lr_tree, momentum=momentum)

        f_new = float(f(x))
        n_steps += 1
        history.append((x, f_new))

        if f_tol > 0.0 and abs(f_new - f_val) <= f_tol:
            f_val = f_new
            reason, converged = "f_change", True
            break
        f_val = f_new

    return Result(
        x=x,
        f=f_val,
        n_steps=n_steps,
        converged=converged,
        reason=reason,
        history=history,
        grad_norm_history=grad_norms,
    )
