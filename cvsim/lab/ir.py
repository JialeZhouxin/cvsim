"""Gaussian Lab `circuit_v0` IR: schema, validation, compile-and-run engine.

Public API only: ``cvsim.gaussian`` ``__all__`` + ``cvsim.wigner.wigner_grid``.
No fastapi dependency here (see ``server.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from cvsim.gaussian import (
    GaussianState,
    amplifier,
    beamsplitter,
    displace,
    fourier,
    heterodyne_condition,
    heterodyne_mean,
    heterodyne_sample_and_condition,
    homodyne_mean,
    homodyne_sample_and_condition,
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

#: vision-gaussian-lab-ui.md §4 whitelist (frozen L0, amended L4: amplifier + mz).
SOURCE_OPS = frozenset({"vacuum", "coherent", "tmsv"})
SINGLE_MODE_OPS = frozenset(
    {"displace", "phase", "squeeze", "fourier", "loss", "amplifier", "homodyne", "heterodyne"}
)
TWO_MODE_OPS = frozenset({"beamsplitter", "two_mode_squeeze", "mz"})
MEASUREMENT_OPS = frozenset({"homodyne", "heterodyne"})
WHITELIST = SOURCE_OPS | SINGLE_MODE_OPS | TWO_MODE_OPS

#: real-numeric params sweepable by /scan (mirrors ops.js `sweep` metadata).
#: complex params (alpha) and structural params (nmode) are excluded.
SWEEPABLE_PARAMS: dict[str, frozenset[str]] = {
    "tmsv": frozenset({"r"}),
    "squeeze": frozenset({"r"}),
    "phase": frozenset({"phi"}),
    "loss": frozenset({"T"}),
    "beamsplitter": frozenset({"theta"}),
    "two_mode_squeeze": frozenset({"r"}),
    "amplifier": frozenset({"G"}),
    "mz": frozenset({"theta", "phi"}),
}


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
    wigner: tuple[np.ndarray, np.ndarray, np.ndarray] | None  # None: singular view
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
    if not isinstance(lim, (int, float)) or isinstance(lim, bool) or lim <= 0 or lim > 50:
        raise CircuitV0Error("view.lim must be a positive number <= 50")
    n = raw_view.get("n", 64)
    if not isinstance(n, int) or isinstance(n, bool) or n < 2 or n > 512:
        raise CircuitV0Error("view.n must be an int in [2, 512]")
    view = View(wigner_mode=wigner_mode, lim=float(lim), n=n)

    edges = data.get("edges", [])
    if not isinstance(edges, list):
        raise CircuitV0Error("edges must be a list")
    ui = data.get("ui", {})
    if not isinstance(ui, dict):
        raise CircuitV0Error("ui must be an object")
    seed = data.get("seed", 0)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise CircuitV0Error("seed must be a non-negative int")
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


def _apply(
    node: Node, state: GaussianState, *, rng: np.random.Generator | None = None
) -> tuple[GaussianState, dict[str, Any] | None]:
    """Apply one non-source op. Returns (new_state, measured_entry or None).

    ``rng is None`` → mean path (deterministic, no RNG); ``rng`` given → every
    measurement node is truly sampled (non-measurement ops never touch the
    generator).
    """
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
        if op == "amplifier":
            G = _num(p.get("G"), where, "G")
            nbar = _num(p.get("nbar", 0.0), where, "nbar")
            # G<1 / nbar<0: library ValueError → 422 at the API boundary.
            return amplifier(state, G, mode, nbar), None
        if op == "homodyne":
            phi = _num(p.get("phi", 0.0), where, "phi")
            if rng is None:
                # mean path: record edge mean, do NOT condition / delete mode
                return state, {"op": "homodyne", "mode": mode, "phi": phi,
                               "outcome": homodyne_mean(state, mode, phi)}
            o, st = homodyne_sample_and_condition(state, mode, phi, rng=rng)
            return st, {"op": "homodyne", "mode": mode, "phi": phi, "outcome": o}
        if op == "heterodyne":
            if rng is None:
                outcome = heterodyne_mean(state, mode)
                st = heterodyne_condition(state, mode, outcome)
            else:
                outcome, st = heterodyne_sample_and_condition(state, mode, rng=rng)
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
        if op == "mz":
            # Mach–Zehnder as lab composition (vision §4): BS(θ) → phase(φ, m0) → BS(θ).
            theta = _num(p.get("theta"), where, "theta")
            phi = _num(p.get("phi", 0.0), where, "phi")
            st = beamsplitter(state, modes[0], modes[1], theta, 0.0)
            st = phase(st, phi, modes[0])
            return beamsplitter(st, modes[0], modes[1], theta, 0.0), None
        raise CircuitV0Error(f"{where}: unsupported two-mode op {op!r}")  # pragma: no cover
    raise CircuitV0Error(f"{where}: unsupported op {op!r}")  # pragma: no cover


def _num(v: Any, where: str, name: str) -> float:
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        raise CircuitV0Error(f"{where}: {name} must be a number")
    return float(v)


def _meters(state: GaussianState, singular: bool) -> dict[str, Any]:
    """meters; purity/log_neg are undefined on singular conditional states
    (det V = 0) → None, never fabricated. mean_photon stays (computable;
    negative values shown honestly)."""
    m = state.nmode

    def safe(fn):
        try:
            return fn()
        except (ValueError, FloatingPointError, ZeroDivisionError, np.linalg.LinAlgError):
            return None

    meters: dict[str, Any] = {
        "purity": safe(lambda: purity(state)),
        "mean_photon": mean_photon(state),
    }
    meters["mean_photon_per_mode"] = [mean_photon(state, mode=i) for i in range(m)]
    if m >= 2:
        meters["log_negativity"] = safe(lambda: log_negativity(state, modes_A=[0]))
    meters["singular"] = singular
    return meters


def _build_result(
    state: GaussianState, view: View, measured: list[dict[str, Any]]
) -> RunResult:
    """Assemble RunResult: Wigner view + meters. A singular conditional state
    (homodyne-conditioned mode, det(2V)=0) has no finite Wigner: report
    wigner=None + meters.singular instead of fabricating data."""
    if view.wigner_mode >= state.nmode:
        raise CircuitV0Error(
            f"view.wigner_mode {view.wigner_mode} out of range (nmode={state.nmode})"
        )
    wigner: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    singular = False
    try:
        keep = partial_trace(state, keep=[view.wigner_mode])
        X, P, W = wigner_grid(keep, lim=view.lim, n=view.n)
        wigner = (X, P, W)
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):  # singular view
        singular = True
    return RunResult(
        nmode=state.nmode,
        rbar=state.rbar,
        V=state.V,
        wigner=wigner,
        meters=_meters(state, singular),
        measured=measured,
    )


def _state_after(circuit: CircuitV0) -> GaussianState:
    """Final GaussianState for a circuit without measurement nodes (scan path)."""
    state: GaussianState | None = None
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
            state, _ = _apply(node, state, rng=None)
    assert state is not None
    return state

def _safe_logneg(state: GaussianState, modes_A: list[int]) -> float | None:
    """E_N on the current state; None when undefined (singular etc.), never fabricated."""
    try:
        v = float(log_negativity(state, modes_A=modes_A))
        return v if math.isfinite(v) else None
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        return None

def scan_circuit(circuit: CircuitV0, sweep: dict[str, Any]) -> dict[str, Any]:
    """F-LAB-SCAN: single-param sweep of one node's real-numeric param → E_N curve.

    Pure function (no RNG): same request → same response. Each point rebuilds
    the circuit with ``param`` replaced and evaluates ``log_negativity`` with
    the requested ``modes_A``; undefined (singular) points are ``None`` (curve
    break, frontend skips). Measurement nodes anywhere in the circuit → 422
    (E_N is not defined on conditional states; honest rejection).
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

    node = next((nd for nd in circuit.nodes if nd.id == node_id), None)
    if node is None:
        raise CircuitV0Error(f"sweep: unknown node_id {node_id!r}")
    if param not in SWEEPABLE_PARAMS.get(node.op, frozenset()):
        raise CircuitV0Error(
            f"sweep: param {param!r} is not sweepable for op {node.op!r}"
        )
    for nd in circuit.nodes:
        if nd.op in MEASUREMENT_OPS:
            raise CircuitV0Error(
                f"sweep: measurement node {nd.id!r} ({nd.op}) — E_N undefined on "
                "conditional states"
            )

    nmode = _state_after(circuit).nmode  # also validates the circuit runs
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
        nodes = []
        for nd in circuit.nodes:
            params = dict(nd.params)
            if nd.id == node_id:
                params[param] = float(x)
            nodes.append(
                Node(id=nd.id, op=nd.op, params=params, mode=nd.mode, modes=nd.modes)
            )
        st = _state_after(replace(circuit, nodes=nodes))
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


def _execute(
    circuit: CircuitV0, *, rng: np.random.Generator | None = None
) -> RunResult:
    """Shared execution core: ordered nodes → final GaussianState + result.
    rng=None → mean path (/run); rng given → sample every measurement node."""
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
            state, entry = _apply(node, state, rng=rng)
            if entry is not None:
                measured.append(entry)
    assert state is not None
    return _build_result(state, circuit.view, measured)


def run_circuit(circuit: CircuitV0) -> RunResult:
    """Compile + run (mean path): ordered nodes → result. Pure, no RNG."""
    return _execute(circuit, rng=None)


def sample_circuit(circuit: CircuitV0, rng: np.random.Generator) -> RunResult:
    """Compile + run with true sampling of every measurement node, in node
    order; each measurement conditions the state for the next one."""
    return _execute(circuit, rng=rng)
