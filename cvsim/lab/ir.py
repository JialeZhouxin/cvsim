"""Gaussian Lab `circuit_v0` IR: schema, validation, compile-and-run engine.

Public API only: ``cvsim.gaussian`` ``__all__`` + ``cvsim.wigner.wigner_grid``.
No fastapi dependency here (see ``server.py``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cvsim.gaussian import (
    GaussianState,
    beamsplitter,
    displace,
    fourier,
    heterodyne_condition,
    heterodyne_mean,
    log_negativity,
    loss,
    mean_photon,
    partial_trace,
    phase,
    purity,
    squeeze,
    two_mode_squeeze,
)
from cvsim.wigner import wigner_grid

SCHEMA = "circuit_v0"

#: vision-gaussian-lab-ui.md §4 whitelist (complete v0 set, frozen at L0).
SOURCE_OPS = frozenset({"vacuum", "coherent", "tmsv"})
SINGLE_MODE_OPS = frozenset(
    {"displace", "phase", "squeeze", "fourier", "loss", "homodyne", "heterodyne"}
)
TWO_MODE_OPS = frozenset({"beamsplitter", "two_mode_squeeze"})
WHITELIST = SOURCE_OPS | SINGLE_MODE_OPS | TWO_MODE_OPS


class CircuitV0Error(ValueError):
    """Invalid ``circuit_v0`` payload; message is UI-safe."""


@dataclass
class View:
    wigner_mode: int = 0
    lim: float = 5.0
    n: int = 64


@dataclass
class Node:
    id: str
    op: str
    params: dict[str, Any] = field(default_factory=dict)
    mode: int | None = None
    modes: list[int] | None = None


@dataclass
class CircuitV0:
    schema: str = SCHEMA
    seed: int = 0  # reserved for L3 sampling; unused by run (pure function)
    nodes: list[Node] = field(default_factory=list)
    edges: list[Any] = field(default_factory=list)  # ignored by run (UI-only)
    view: View = field(default_factory=View)
    ui: dict[str, Any] = field(default_factory=dict)  # ignored by run


@dataclass
class RunResult:
    nmode: int
    rbar: np.ndarray
    V: np.ndarray
    wigner: tuple[np.ndarray, np.ndarray, np.ndarray]  # (X, P, W) grids
    meters: dict[str, Any]
    measured: list[dict[str, Any]]


def _require(d: dict[str, Any], key: str, typ: type, where: str) -> Any:
    if key not in d:
        raise CircuitV0Error(f"{where}: missing field {key!r}")
    v = d[key]
    if not isinstance(v, typ):
        raise CircuitV0Error(
            f"{where}: field {key!r} must be {typ.__name__}, got {type(v).__name__}"
        )
    return v


def _as_complex(v: Any, where: str) -> complex:
    """JSON has no complex: accept float/int, [re, im], or {"re":..,"im":..}."""
    if isinstance(v, (int, float)):
        return complex(v)
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return complex(v[0], v[1])
    if isinstance(v, dict) and "re" in v and "im" in v:
        return complex(v["re"], v["im"])
    raise CircuitV0Error(f"{where}: alpha must be number, [re, im], or {{re, im}}")


def _as_pos_int(v: Any, where: str) -> int:
    if not isinstance(v, int) or isinstance(v, bool) or v < 0:
        raise CircuitV0Error(f"{where}: must be a non-negative int")
    return v


def load_circuit(data: dict[str, Any]) -> CircuitV0:
    """Parse + validate a raw JSON dict into a :class:`CircuitV0`."""
    if not isinstance(data, dict):
        raise CircuitV0Error("payload must be a JSON object")
    schema = _require(data, "schema", str, "root")
    if schema != SCHEMA:
        raise CircuitV0Error(f"unsupported schema {schema!r}; expected {SCHEMA!r}")

    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise CircuitV0Error("nodes must be a non-empty list")
    nodes: list[Node] = []
    for i, rn in enumerate(raw_nodes):
        where = f"nodes[{i}]"
        if not isinstance(rn, dict):
            raise CircuitV0Error(f"{where}: must be an object")
        nid = _require(rn, "id", str, where)
        if not nid:
            raise CircuitV0Error(f"{where}: id must be non-empty")
        op = _require(rn, "op", str, where)
        if op not in WHITELIST:
            raise CircuitV0Error(
                f"{where}: unknown op {op!r}; whitelist: {sorted(WHITELIST)}"
            )
        params = rn.get("params", {})
        if not isinstance(params, dict):
            raise CircuitV0Error(f"{where}: params must be an object")
        mode: int | None = None
        modes: list[int] | None = None
        # explicit mode routing: single-mode ops take `mode`, two-mode take `modes`
        if op in SINGLE_MODE_OPS:
            if "mode" not in rn:
                raise CircuitV0Error(f"{where}: op {op!r} requires field 'mode'")
            mode = _as_pos_int(rn["mode"], f"{where}.mode")
        elif op in TWO_MODE_OPS:
            if "modes" not in rn or not isinstance(rn["modes"], list) or len(rn["modes"]) != 2:
                raise CircuitV0Error(f"{where}: op {op!r} requires 'modes' of length 2")
            modes = [_as_pos_int(m, f"{where}.modes") for m in rn["modes"]]
        nodes.append(Node(id=nid, op=op, params=params, mode=mode, modes=modes))

    raw_view = data.get("view", {})
    if not isinstance(raw_view, dict):
        raise CircuitV0Error("view must be an object")
    wigner_mode = _as_pos_int(raw_view.get("wigner_mode", 0), "view.wigner_mode")
    lim = raw_view.get("lim", 5.0)
    if not isinstance(lim, (int, float)) or isinstance(lim, bool) or lim <= 0:
        raise CircuitV0Error("view.lim must be a positive number")
    n = raw_view.get("n", 64)
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        raise CircuitV0Error("view.n must be an int >= 2")
    view = View(wigner_mode=wigner_mode, lim=float(lim), n=n)

    edges = data.get("edges", [])
    if not isinstance(edges, list):
        raise CircuitV0Error("edges must be a list")
    ui = data.get("ui", {})
    if not isinstance(ui, dict):
        raise CircuitV0Error("ui must be an object")
    seed = data.get("seed", 0)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise CircuitV0Error("seed must be an int")
    return CircuitV0(schema=schema, seed=seed, nodes=nodes, edges=edges, view=view, ui=ui)


def _source(op: str, node: Node) -> GaussianState:
    p = node.params
    if op == "vacuum":
        nmode = p.get("nmode", 1)
        if not isinstance(nmode, int) or isinstance(nmode, bool) or nmode < 1:
            raise CircuitV0Error(f"nodes[{node.id}]: vacuum nmode must be an int >= 1")
        return GaussianState.vacuum(nmode)
    if op == "coherent":
        return GaussianState.coherent(_as_complex(p.get("alpha"), f"nodes[{node.id}]"))
    if op == "tmsv":
        r = p.get("r")
        if not isinstance(r, (int, float)) or isinstance(r, bool):
            raise CircuitV0Error(f"nodes[{node.id}]: tmsv r must be a number")
        return GaussianState.tmsv(float(r))
    raise CircuitV0Error(f"nodes[{node.id}]: unknown source {op!r}")  # pragma: no cover


def _check_mode(state: GaussianState, mode: int, where: str) -> None:
    if mode >= state.nmode:
        raise CircuitV0Error(
            f"{where}: mode {mode} out of range (nmode={state.nmode})"
        )


def _apply(node: Node, state: GaussianState) -> tuple[GaussianState, dict[str, Any] | None]:
    """Apply one non-source op. Returns (new_state, measured_entry or None)."""
    op, p, where = node.op, node.params, f"nodes[{node.id}]"
    if op in SINGLE_MODE_OPS:
        mode = node.mode
        assert mode is not None
        _check_mode(state, mode, where)
        if op == "displace":
            return displace(state, _as_complex(p.get("alpha"), where), mode), None
        if op == "phase":
            return phase(state, _num(p.get("phi"), where, "phi"), mode), None
        if op == "squeeze":
            r = _num(p.get("r"), where, "r")
            phi = _num(p.get("phi", 0.0), where, "phi")
            return squeeze(state, r, mode, phi), None
        if op == "fourier":
            return fourier(state, mode), None
        if op == "loss":
            T = _num(p.get("T"), where, "T")
            nbar = _num(p.get("nbar", 0.0), where, "nbar")
            return loss(state, T, mode, nbar), None
        if op == "homodyne":
            # v0: no sampling; condition semantics keep the mode, state unchanged.
            return state, {"op": "homodyne", "mode": mode, "outcome": None}
        if op == "heterodyne":
            outcome = heterodyne_mean(state, mode)
            st = heterodyne_condition(state, mode, outcome)
            entry: dict[str, Any] = {
                "op": "heterodyne",
                "mode": mode,
                "outcome": [outcome.real, outcome.imag],
            }
            return st, entry
        raise CircuitV0Error(f"{where}: unsupported single-mode op {op!r}")  # pragma: no cover
    if op in TWO_MODE_OPS:
        modes = node.modes
        assert modes is not None
        for m in modes:
            _check_mode(state, m, where)
        if op == "beamsplitter":
            theta = _num(p.get("theta"), where, "theta")
            phi = _num(p.get("phi", 0.0), where, "phi")
            return beamsplitter(state, modes[0], modes[1], theta, phi), None
        if op == "two_mode_squeeze":
            r = _num(p.get("r"), where, "r")
            return two_mode_squeeze(state, r, modes[0], modes[1]), None
        raise CircuitV0Error(f"{where}: unsupported two-mode op {op!r}")  # pragma: no cover
    raise CircuitV0Error(f"{where}: unsupported op {op!r}")  # pragma: no cover


def _num(v: Any, where: str, name: str) -> float:
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        raise CircuitV0Error(f"{where}: {name} must be a number")
    return float(v)


def run_circuit(circuit: CircuitV0) -> RunResult:
    """Compile + run: ordered nodes → final GaussianState, Wigner view, meters."""
    state: GaussianState | None = None
    measured: list[dict[str, Any]] = []
    for node in circuit.nodes:
        if node.op in SOURCE_OPS:
            if state is not None:
                raise CircuitV0Error(
                    f"nodes[{node.id}]: source op must be first (state already exists)"
                )
            state = _source(node.op, node)
        else:
            if state is None:
                raise CircuitV0Error(
                    f"nodes[{node.id}]: op {node.op!r} requires a source node first"
                )
            state, entry = _apply(node, state)
            if entry is not None:
                measured.append(entry)
    assert state is not None

    view = circuit.view
    if view.wigner_mode >= state.nmode:
        raise CircuitV0Error(
            f"view.wigner_mode {view.wigner_mode} out of range (nmode={state.nmode})"
        )
    keep = partial_trace(state, keep=[view.wigner_mode])
    X, P, W = wigner_grid(keep, lim=view.lim, n=view.n)

    m = state.nmode
    meters: dict[str, Any] = {"purity": purity(state), "mean_photon": mean_photon(state)}
    meters["mean_photon_per_mode"] = [mean_photon(state, mode=i) for i in range(m)]
    if m >= 2:
        meters["log_negativity"] = log_negativity(state, modes_A=[0])
    return RunResult(
        nmode=m, rbar=state.rbar, V=state.V, wigner=(X, P, W), meters=meters, measured=measured
    )
