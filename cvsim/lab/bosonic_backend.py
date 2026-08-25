"""Bosonic backend execution for the Lab workbench (B6).

Extracted from ``lab/ir.py``. Bosonic run + Wigner/meters assembly, plus the
``fidelity_sweep`` (GKP QEC target comparison). Imports shared types/helpers
from ``cvsim.lab.ir`` (no circular import: ir.py does not import this module).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from cvsim.bosonic import (
    BosonicCircuit,
    BosonicState,
    pure_fidelity,
)
from cvsim.bosonic import (
    mean_photon as bosonic_mean_photon,
)
from cvsim.bosonic import (
    purity as bosonic_purity,
)
from cvsim.lab.fock_backend import _fock_measured
from cvsim.lab.ir import SCHEMA, CircuitV0Error, LabCircuit, View, _num, _require
from cvsim.wigner import wigner_grid


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
    if not isinstance(n, int) or isinstance(n, bool) or not 2 <= n <= 200:
        raise CircuitV0Error("sweep.n must be an int in [2, 200]")
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


def _bosonic_adaptive_n(state: BosonicState, n: int) -> int:
    """Adaptive Wigner grid size: many components → coarser grid.

    Bosonic GKP states carry K~O(10-100) Gaussian components; a full
    n=64 grid on each is O(seconds per point). Cap the grid for large K
    (aligns Fock F7 slowCutoff spirit — teaching view, not science grid).
    """
    k = state.n_components
    if k > 32:
        return min(n, 20)
    if k > 8:
        return min(n, 32)
    return n



def _bosonic_single_wigner(
    state: BosonicState, mode: int, view: View
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Wigner of the reduced single-mode state (partial trace via remove_mode)."""
    if state.nmode == 0 or not state.components:
        return None
    s = state
    for i in range(state.nmode - 1, -1, -1):
        if i != mode:
            s = s.remove_mode(i)
    if s.nmode != 1:
        return None
    try:
        return wigner_grid(s, lim=view.lim, n=_bosonic_adaptive_n(s, view.n))
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        return None



def _bosonic_meters(state: BosonicState) -> dict[str, Any]:
    """Bosonic result meters: purity + per-mode/mean photon (B4/B1 closed forms)."""
    if state.nmode == 0 or not state.components:
        return {"purity": None, "mean_photon": 0.0, "mean_photon_per_mode": []}
    modes = range(state.nmode)
    mean_list = [float(bosonic_mean_photon(state, i)) for i in modes]
    try:
        pur = float(bosonic_purity(state))
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        pur = None
    return {
        "purity": pur,
        "mean_photon": float(sum(mean_list)),
        "mean_photon_per_mode": mean_list,
    }



def run_bosonic_circuit(
    circuit: LabCircuit, rng: np.random.Generator | None = None, *, steps: bool = False
) -> dict[str, Any]:
    """Bosonic /run + /sample shared path: from_ir → compile → run(rng).

    Deterministic per circuit when rng is a seeded Generator (B6 aligns Fock
    F7: seed field drives reproducibility). ``steps=True`` (detail="steps")
    adds per-break-point intermediate snapshots for the GUI evolution view.
    """
    bc = BosonicCircuit.from_ir(circuit.raw)
    if steps:
        state, results, raw_steps = bc.compile().run_steps(rng=rng)
    else:
        out = bc.run(rng=rng)
        if isinstance(out, tuple):
            state, results = out
        else:
            state, results = out, {}
    measured = _fock_measured(circuit.raw, results)
    wmode = circuit.view.wigner_mode
    if state.nmode > 0 and wmode >= state.nmode:
        raise CircuitV0Error(
            f"view.wigner_mode {wmode} out of range (nmode={state.nmode})"
        )
    wigner = None
    if state.nmode > 0:
        wigner = _bosonic_single_wigner(state, wmode, circuit.view)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "backend": "bosonic",
        "nmode": state.nmode,
        "wigner": (
            {"x": wigner[0][0].tolist(), "p": wigner[1][:, 0].tolist(),
             "W": wigner[2].tolist()}
            if wigner is not None
            else None
        ),
        "dist": {"mode": wmode, "probs": None},
        "meters": _bosonic_meters(state),
        "measured": measured,
    }
    if steps:
        payload["steps"] = [
            {
                "step": i,
                "op": op_name,
                "nmode": s.nmode,
                "meters": _bosonic_meters(s),
                "wigner": _bosonic_wigner_payload(s, circuit.view),
            }
            for i, (op_name, s) in enumerate(raw_steps)
        ]
    return payload



def _bosonic_wigner_payload(
    state: BosonicState, view: View
) -> dict[str, Any] | None:
    """Wigner payload for a step state (view.wigner_mode reduced single-mode)."""
    if state.nmode == 0:
        return None
    wmode = view.wigner_mode
    if wmode >= state.nmode:
        return None
    w = _bosonic_single_wigner(state, wmode, view)
    if w is None:
        return None
    return {"x": w[0][0].tolist(), "p": w[1][:, 0].tolist(), "W": w[2].tolist()}



