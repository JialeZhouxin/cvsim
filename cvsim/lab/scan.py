"""Lab sweep capabilities: /scan (E_N curve) + /fidelity (fidelity curve).

Both are analysis queries over one swept param of one node. Extracted from
``lab/ir.py`` so ir.py keeps only schema + translate + execution dispatch.
scan_circuit + its private helpers (_safe_logneg / _inject_symbolic_param)
and the sweepable-params table live here; fidelity_sweep (+ its GKP
target/reduce helpers) moved here from ``bosonic_backend.py``. Imports
shared types/helpers from ``cvsim.lab.ir`` (no circular import: ir.py does
not module-import this file; mirrors gaussian_backend.py pattern).

Ticket 4: ``SWEEPABLE_PARAMS`` is *declared* in ``cvsim.lab.schema``
(single declaration point, next to the ``/schema`` ``sweepable``
extension it feeds) and imported back here as a derived view.
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

from cvsim.bosonic import BosonicCircuit, BosonicState, pure_fidelity
from cvsim.gaussian import GaussianCircuit, GaussianState, log_negativity
from cvsim.lab.ir import (  # noqa: F401 — re-exported derived views
    MEASUREMENT_OPS,
    CircuitV0Error,
    LabCircuit,
    _num,
    _require,
)
from cvsim.lab.schema import _EXTENSIONS, SWEEPABLE_PARAMS  # noqa: F401


def _safe_logneg(state: GaussianState, modes_A: list[int]) -> float | None:
    """E_N on the current state; None when undefined (singular etc.), never fabricated."""
    try:
        v = float(log_negativity(state, modes_A=modes_A))
        return v if math.isfinite(v) else None
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        return None


def _inject_symbolic_param(raw: dict[str, Any], node_id: str, param: str) -> dict[str, Any]:
    """Return a deep copy of ``raw`` with ``node_id``'s ``param`` replaced by
    a symbolic ``{"$param": "sweep_x"}`` reference (ADR-0002 value binding).

    Lets ``scan_circuit`` compile once and bind per sweep point instead of
    rebuilding+recompiling the IR each time.
    """
    out = copy.deepcopy(raw)
    for node in out.get("ops", []):
        if node.get("id") == node_id:
            node["params"][param] = {"$param": "sweep_x"}
            return out
    raise CircuitV0Error(f"sweep: unknown node_id {node_id!r}")  # pragma: no cover


def scan_circuit(circuit: LabCircuit, sweep: dict[str, Any]) -> dict[str, Any]:
    """F-LAB-SCAN: single-param sweep of one node's real-numeric param → E_N curve.

    Pure function (no RNG): same request → same response. The swept param is
    injected as a symbolic ``$param`` (ADR-0002): the circuit is compiled once,
    then each sweep point binds the value via ``compiled.run(sweep_x=x)`` — no
    per-point IR rebuild or recompile. Undefined (singular) points are ``None``
    (curve break, frontend skips). Measurement nodes anywhere → 422 (E_N is
    not defined on conditional states; honest rejection).
    """
    node_id = _require(sweep, "node_id", str, "sweep")
    param = _require(sweep, "param", str, "sweep")
    pmin = _num(sweep.get("min"), "sweep.min", "min")
    pmax = _num(sweep.get("max"), "sweep.max", "max")
    if not (math.isfinite(pmin) and math.isfinite(pmax)):
        raise CircuitV0Error(f"sweep: min/max must be finite (got {pmin}, {pmax})")
    if not pmin < pmax:
        raise CircuitV0Error(f"sweep: min must be < max (got {pmin}, {pmax})")
    n = sweep.get("n")
    _sn = _EXTENSIONS["sweep"]["n"]
    if not isinstance(n, int) or isinstance(n, bool) or not _sn[0] <= n <= _sn[1]:
        raise CircuitV0Error(
            f"sweep.n must be an int in [{_sn[0]}, {_sn[1]}]"
        )

    core = circuit.core
    assert core is not None  # scan is Gaussian-path only (Fock has core=None)
    node = next((nd for nd in core.ops if nd.id == node_id), None)
    if node is None:
        raise CircuitV0Error(f"sweep: unknown node_id {node_id!r}")
    if param not in SWEEPABLE_PARAMS.get(node.op, frozenset()):
        raise CircuitV0Error(f"sweep: param {param!r} is not sweepable for op {node.op!r}")
    for nd in core.ops:
        if nd.op in MEASUREMENT_OPS:
            raise CircuitV0Error(
                f"sweep: measurement node {nd.id!r} ({nd.op}) — E_N undefined on conditional states"
            )

    # Compile once with the swept param as a symbolic $param; bind per point.
    swept_raw = _inject_symbolic_param(circuit.raw, node_id, param)
    compiled = GaussianCircuit.from_ir(swept_raw).compile()
    nmode = compiled.nmode
    modes_A = sweep.get("modes_A", [0])
    if not isinstance(modes_A, list) or not modes_A:
        raise CircuitV0Error("sweep.modes_A must be a non-empty list of ints")
    if len(modes_A) > nmode - 1:
        raise CircuitV0Error(
            f"sweep.modes_A: at most nmode-1={nmode - 1} modes (got {len(modes_A)})"
        )
    if len(set(modes_A)) != len(modes_A):
        raise CircuitV0Error("sweep.modes_A: duplicate mode indices")
    for m in modes_A:
        if not isinstance(m, int) or isinstance(m, bool) or m < 0 or m >= nmode:
            raise CircuitV0Error(f"sweep.modes_A: mode {m} out of range (nmode={nmode})")

    xs = np.linspace(pmin, pmax, n)
    ys: list[float | None] = []
    for x in xs:
        st = compiled.run(sweep_x=float(x))
        ys.append(_safe_logneg(st, list(modes_A)))
    return {
        "node_id": node_id,
        "param": param,
        "min": float(pmin),
        "max": float(pmax),
        "n": n,
        "modes_A": list(modes_A),
        "xs": xs.tolist(),
        "ys": ys,
    }


def _fidelity_target(target: dict[str, Any], mode: int) -> BosonicState:
    """Resolve the fidelity target state name (B6 R2: GKP QEC vs gkp0)."""
    name = _require(target, "state", str, "target")
    if name == "gkp0":
        from cvsim.bosonic import gkp0

        return gkp0()
    if name == "gkp1":
        from cvsim.bosonic import gkp1

        return gkp1()
    raise CircuitV0Error(f"target.state: unknown state source {name!r} (gkp0|gkp1)")


def _bosonic_reduce_to_mode(state: BosonicState, mode: int) -> BosonicState:
    """Reduce ``state`` to a single mode via remove_mode (B6 target mode)."""
    if state.nmode == 1:
        return state
    s = state
    for i in range(state.nmode - 1, -1, -1):
        if i != mode:
            s = s.remove_mode(i)
    return s


def fidelity_sweep(
    circuit: LabCircuit, sweep: dict[str, Any], seed: int = 0, rounds: int = 1
) -> dict[str, Any]:
    """/fidelity: single-param sweep → fidelity-vs-param curve (B6 A-item).

    Unlike ``scan_circuit`` (pure E_N, no RNG) the Bosonic fidelity path is
    stochastic — the targeted run draws a homodyne outcome and feeds forward,
    so each point is evaluated with a seeded (deterministic) run and
    optionally averaged over ``rounds`` seeds (``default_rng(seed+i)``).
    Swept param is replaced on the named node each point.
    """
    node_id = _require(sweep, "node_id", str, "sweep")
    param = _require(sweep, "param", str, "sweep")
    pmin = _num(sweep.get("min"), "sweep.min", "min")
    pmax = _num(sweep.get("max"), "sweep.max", "max")
    if not (math.isfinite(pmin) and math.isfinite(pmax)):
        raise CircuitV0Error(f"sweep: min/max must be finite (got {pmin}, {pmax})")
    if not pmin < pmax:
        raise CircuitV0Error(f"sweep: min must be < max (got {pmin}, {pmax})")
    n = sweep.get("n")
    _sn = _EXTENSIONS["sweep"]["n"]
    if not isinstance(n, int) or isinstance(n, bool) or not _sn[0] <= n <= _sn[1]:
        raise CircuitV0Error(
            f"sweep.n must be an int in [{_sn[0]}, {_sn[1]}]"
        )
    if not isinstance(rounds, int) or isinstance(rounds, bool) or not 1 <= rounds <= 100:
        raise CircuitV0Error("rounds must be an int in [1, 100]")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise CircuitV0Error("seed must be a non-negative int")
    target_dict = sweep.get("target")
    if not isinstance(target_dict, dict):
        raise CircuitV0Error("sweep.target must be an object {state, mode}")
    target_mode = target_dict.get("mode", 0)
    if not isinstance(target_mode, int) or isinstance(target_mode, bool) or target_mode < 0:
        raise CircuitV0Error("target.mode must be a non-negative int")
    target = _fidelity_target(target_dict, target_mode)

    raw_ops = circuit.raw.get("ops", [])
    if not any(nd.get("id") == node_id for nd in raw_ops):
        raise CircuitV0Error(f"sweep: unknown node_id {node_id!r}")
    raw = dict(circuit.raw)
    xs = np.linspace(pmin, pmax, n)
    ys: list[list[float]] = []
    for x in xs:
        ops = []
        for nd in raw_ops:
            node = dict(nd)
            if node.get("id") == node_id:
                params = dict(node.get("params", {}))
                params[param] = float(x)
                node["params"] = params
            ops.append(node)
        raw["ops"] = ops
        bc = BosonicCircuit.from_ir(raw)
        point: list[float] = []
        for r in range(int(rounds)):
            out = bc.run(rng=np.random.default_rng(seed + r))
            state, _ = out if isinstance(out, tuple) else (out, {})
            if state.nmode == 0 or not state.components:
                point.append(float("nan"))
                continue
            red = _bosonic_reduce_to_mode(state, target_mode)
            val = pure_fidelity(red, target)
            point.append(float(val))
        ys.append(point)
    ys_avg: list[float | None] = []
    for point in ys:
        vals = [v for v in point if not math.isnan(v)]
        ys_avg.append(float(np.mean(vals)) if vals else None)
    return {
        "node_id": node_id,
        "param": param,
        "min": float(pmin),
        "max": float(pmax),
        "n": n,
        "seed": seed,
        "rounds": int(rounds),
        "target": {"state": target_dict.get("state"), "mode": target_mode},
        "xs": xs.tolist(),
        "ys": ys_avg,
    }
