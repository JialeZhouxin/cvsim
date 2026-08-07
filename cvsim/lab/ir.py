"""Gaussian Lab circuit IR: `circuit_v1` engine + `circuit_v0` translation.

Public API only: ``cvsim.gaussian`` ``__all__`` + ``cvsim.wigner.wigner_grid``.
No fastapi dependency here (see ``server.py``).

Schema split (ADR-0003): core schema/validation live in ``cvsim.gaussian.ir``
(``circuit_v1``, full op set). This module owns Lab concerns: v0 file
compatibility (``translate_v0``), the Lab op whitelist, view/seed/ui
extension fields, and the mean/sample execution paths.

v1 semantics (design §0, intentional unification vs v0):
- mode indices are **logical** (runtime keeps a logical→physical map; a
  measured/removed mode is marked -1 and higher logical modes shift down).
- homodyne **removes** the measured mode in both mean and sample paths
  (matches ``GaussianCircuit`` / vision §4.4; v0 kept it in place).
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
    homodyne_condition,
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
from cvsim.gaussian.ir import IRNode, SCHEMA, CircuitV1, validate_ir
from cvsim.wigner import wigner_grid

SCHEMA_V0 = "circuit_v0"

#: Lab op whitelist (lab vision §4 + L4/L5 amendments). v1 files may carry
#: core-only ops (cz/cx/interferometer/phase_noise/gaussian_channel/
#: mach_zehnder); those are valid IR but not unlocked in the Lab UI — the
#: Lab loader rejects them (whitelist is a UI concept, ADR-0003 #3).
LAB_WHITELIST = frozenset(
    {
        "displace", "phase", "squeeze", "fourier", "loss", "amplifier",
        "beamsplitter", "two_mode_squeeze", "mz",
        "measure_homodyne", "measure_heterodyne",
    }
)
#: v0-only source ops — translated away by :func:`translate_v0` (no source
#: concept in v1: coherent ≡ displace, tmsv ≡ two_mode_squeeze).
SOURCE_V0 = frozenset({"vacuum", "coherent", "tmsv"})
#: v0 op names → core v1 names (builder 1:1, ADR-0003 #3):
#: homodyne/heterodyne → measure_homodyne/measure_heterodyne.
V0_TO_V1_OP = {"homodyne": "measure_homodyne", "heterodyne": "measure_heterodyne"}
#: v0 param names → v1 param names (phase used ``phi`` in the Lab UI;
#: core builder/IR speak ``theta``).
V0_TO_V1_PARAM = {"phase": {"phi": "theta"}}
SINGLE_MODE_V0 = frozenset(
    {"displace", "phase", "squeeze", "fourier", "loss", "amplifier",
     "homodyne", "heterodyne"}
)
TWO_MODE_V0 = frozenset({"beamsplitter", "two_mode_squeeze", "mz"})
MEASUREMENT_OPS = frozenset({"measure_homodyne", "measure_heterodyne"})

#: real-numeric params sweepable by /scan (mirrors ops.js `sweep` metadata).
#: complex params (alpha) and structural params (nmode) are excluded.
SWEEPABLE_PARAMS: dict[str, frozenset[str]] = {
    "squeeze": frozenset({"r"}),
    "phase": frozenset({"phi"}),
    "loss": frozenset({"T"}),
    "beamsplitter": frozenset({"theta"}),
    "two_mode_squeeze": frozenset({"r"}),
    "amplifier": frozenset({"G"}),
    "mz": frozenset({"theta", "phi"}),
}


class CircuitV0Error(ValueError):
    """Invalid circuit payload (v0 or v1); message is UI-safe."""


@dataclass
class View:
    wigner_mode: int = 0
    lim: float = 5.0
    n: int = 64


@dataclass
class LabCircuit:
    """Lab-loaded circuit: core :class:`CircuitV1` + UI extension fields.

    ``seed`` / ``view`` / ``ui`` are Lab concerns (core IR ignores them,
    ADR-0003 #8); they ride along in the JSON as extension fields.
    """

    core: CircuitV1
    seed: int = 0
    view: View = field(default_factory=View)
    ui: dict[str, Any] = field(default_factory=dict)


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


def _as_pos_int(v: Any, where: str) -> int:
    if not isinstance(v, int) or isinstance(v, bool) or v < 0:
        raise CircuitV0Error(f"{where}: must be a non-negative int")
    return v


def _num(v: Any, where: str, name: str) -> float:
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        raise CircuitV0Error(f"{where}: {name} must be a number")
    return float(v)


def _as_complex(v: Any, where: str) -> complex:
    """JSON has no complex: accept float/int, [re, im], or {"re":..,"im":..}."""
    if isinstance(v, (int, float)):
        return complex(v)
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return complex(v[0], v[1])
    if isinstance(v, dict) and "re" in v and "im" in v:
        return complex(v["re"], v["im"])
    raise CircuitV0Error(f"{where}: alpha must be number, [re, im], or {{re, im}}")


# -- circuit_v0 → circuit_v1 translation ------------------------------------

def translate_v0(data: dict[str, Any]) -> dict[str, Any]:
    """Pure ``circuit_v0`` JSON → ``circuit_v1`` dict.

    Sources become block-local gates on vacuum (exact equivalence, ADR-0003
    #2): ``coherent`` → ``displace``, ``tmsv`` → ``two_mode_squeeze``,
    ``vacuum`` contributes modes only. ``nmode`` = Σ source contributions.
    ``mode``/``modes`` → unified ``modes``; ``view``/``seed``/``ui`` copied as
    extension fields; ``edges`` dropped (v0 already ignored it).
    """
    if not isinstance(data, dict):
        raise CircuitV0Error("payload must be a JSON object")
    schema = data.get("schema")
    if schema != SCHEMA_V0:
        raise CircuitV0Error(f"unsupported schema {schema!r}; expected {SCHEMA_V0!r}")
    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise CircuitV0Error("nodes must be a non-empty list")

    nmode = 0
    ops: list[dict[str, Any]] = []
    seen_gate = False
    for i, rn in enumerate(raw_nodes):
        where = f"nodes[{i}]"
        if not isinstance(rn, dict):
            raise CircuitV0Error(f"{where}: must be an object")
        op = _require(rn, "op", str, where)
        params = rn.get("params", {})
        if not isinstance(params, dict):
            raise CircuitV0Error(f"{where}: params must be an object")
        if op in SOURCE_V0:
            if seen_gate:
                raise CircuitV0Error(
                    f"{where}: source op must be first (state already exists)"
                )
            if op == "vacuum":
                nm = params.get("nmode", 1)
                if not isinstance(nm, int) or isinstance(nm, bool) or nm < 1:
                    raise CircuitV0Error(
                        f"nodes[{i}]: vacuum nmode must be an int >= 1"
                    )
                nmode += nm
            else:
                src_node: dict[str, Any] = {}
                if "id" in rn:
                    src_node["id"] = rn["id"]  # scan/UI reference the source node
                if op == "coherent":
                    alpha = _as_complex(params.get("alpha"), where)
                    src_node.update({"op": "displace", "modes": [nmode],
                                     "params": {"alpha": [alpha.real, alpha.imag]}})
                    nmode += 1
                else:  # tmsv
                    r = _num(params.get("r"), where, "r")
                    src_node.update({"op": "two_mode_squeeze", "modes": [nmode, nmode + 1],
                                     "params": {"r": r}})
                    nmode += 2
                ops.append(src_node)
        else:
            seen_gate = True
            if op in SINGLE_MODE_V0:
                if "mode" not in rn:
                    raise CircuitV0Error(f"{where}: op {op!r} requires field 'mode'")
                modes = [_as_pos_int(rn["mode"], f"{where}.mode")]
            elif op in TWO_MODE_V0:
                if not isinstance(rn.get("modes"), list) or len(rn["modes"]) != 2:
                    raise CircuitV0Error(
                        f"{where}: op {op!r} requires 'modes' of length 2"
                    )
                modes = [_as_pos_int(m, f"{where}.modes") for m in rn["modes"]]
            else:
                raise CircuitV0Error(
                    f"{where}: unknown op {op!r}; whitelist: "
                    f"{sorted(SOURCE_V0 | SINGLE_MODE_V0 | TWO_MODE_V0)}"
                )
            node: dict[str, Any] = {"op": V0_TO_V1_OP.get(op, op), "modes": modes,
                                    "params": dict(params)}
            pnames = V0_TO_V1_PARAM.get(node["op"], {})
            if pnames:
                node["params"] = {pnames.get(k, k): v for k, v in params.items()}
            if node["op"] in MEASUREMENT_OPS and "name" not in node["params"]:
                # v1 measure ops carry a result name (builder 1:1); v0 files
                # may omit it (heterodyne never had one) — synthesize.
                node["params"]["name"] = rn.get("id") or f"m{i}"
            if "id" in rn:
                node["id"] = rn["id"]
            ops.append(node)

    out: dict[str, Any] = {"schema": SCHEMA, "nmode": nmode, "ops": ops}
    for k in ("view", "seed", "ui"):
        if k in data:
            out[k] = data[k]
    return out


def _parse_view(raw: Any) -> View:
    if not isinstance(raw, dict):
        raise CircuitV0Error("view must be an object")
    wigner_mode = _as_pos_int(raw.get("wigner_mode", 0), "view.wigner_mode")
    lim = raw.get("lim", 5.0)
    if not isinstance(lim, (int, float)) or isinstance(lim, bool) or lim <= 0 or lim > 50:
        raise CircuitV0Error("view.lim must be a positive number <= 50")
    n = raw.get("n", 64)
    if not isinstance(n, int) or isinstance(n, bool) or n < 2 or n > 512:
        raise CircuitV0Error("view.n must be an int in [2, 512]")
    return View(wigner_mode=wigner_mode, lim=float(lim), n=n)


def load_circuit(data: dict[str, Any]) -> LabCircuit:
    """Load + validate a circuit payload: v1 native, v0 via :func:`translate_v0`.

    Then enforce the Lab whitelist (UI concept; core-only ops → 422).
    """
    if not isinstance(data, dict):
        raise CircuitV0Error("payload must be a JSON object")
    if data.get("schema") == SCHEMA_V0:
        data = translate_v0(data)
    elif data.get("schema") != SCHEMA:
        raise CircuitV0Error(
            f"unsupported schema {data.get('schema')!r}; expected {SCHEMA!r} or "
            f"{SCHEMA_V0!r}"
        )
    try:
        core = validate_ir(data)
    except ValueError as e:
        # Lab error surface is uniformly CircuitV0Error (server 422 contract,
        # error-handling spec); core validation speaks plain ValueError.
        raise CircuitV0Error(str(e)) from e
    for node in core.ops:
        if node.op not in LAB_WHITELIST:
            raise CircuitV0Error(
                f"ops[{node.id or '?'}]: op {node.op!r} not in Lab whitelist: "
                f"{sorted(LAB_WHITELIST)}"
            )
    view = _parse_view(data.get("view", {}))
    seed = data.get("seed", 0)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise CircuitV0Error("seed must be a non-negative int")
    ui = data.get("ui", {})
    if not isinstance(ui, dict):
        raise CircuitV0Error("ui must be an object")
    return LabCircuit(core=core, seed=seed, view=view, ui=ui)


# -- execution --------------------------------------------------------------

def _logical_phys(mapping: list[int], node: IRNode) -> list[int]:
    """Logical mode indices → physical, rejecting measured/removed modes."""
    phys = [mapping[m] for m in node.modes]
    for m, p in zip(node.modes, phys):
        if p < 0:
            raise CircuitV0Error(
                f"op {node.op!r} references mode {m}, already measured/removed"
            )
    return phys


def _apply(
    node: IRNode,
    state: GaussianState,
    mapping: list[int],
    *,
    rng: np.random.Generator | None = None,
) -> tuple[GaussianState, dict[str, Any] | None]:
    """Apply one non-source op. Returns (new_state, measured_entry or None).

    ``rng is None`` → mean path (deterministic, no RNG); ``rng`` given → every
    measurement node is truly sampled (non-measurement ops never touch the
    generator). Measurements **remove** the mode (v1 semantics); ``mapping``
    is updated in place (logical → physical, removed = -1, higher shift down).
    """
    op, p, where = node.op, node.params, f"ops[{node.id or '?'}]"
    phys = _logical_phys(mapping, node)
    if op == "displace":
        return displace(state, _as_complex(p.get("alpha"), where), phys[0]), None
    if op == "phase":
        return phase(state, _num(p.get("theta"), where, "theta"), phys[0]), None
    if op == "squeeze":
        r = _num(p.get("r"), where, "r")
        phi = _num(p.get("phi", 0.0), where, "phi")
        return squeeze(state, r, phys[0], phi), None
    if op == "fourier":
        return fourier(state, phys[0]), None
    if op == "loss":
        T = _num(p.get("T"), where, "T")
        nbar = _num(p.get("nbar", 0.0), where, "nbar")
        return loss(state, T, phys[0], nbar), None
    if op == "amplifier":
        G = _num(p.get("G"), where, "G")
        nbar = _num(p.get("nbar", 0.0), where, "nbar")
        return amplifier(state, G, phys[0], nbar), None
    if op == "beamsplitter":
        theta = _num(p.get("theta"), where, "theta")
        phi = _num(p.get("phi", 0.0), where, "phi")
        return beamsplitter(state, phys[0], phys[1], theta, phi), None
    if op == "two_mode_squeeze":
        r = _num(p.get("r"), where, "r")
        return two_mode_squeeze(state, r, phys[0], phys[1]), None
    if op == "mz":
        # Mach–Zehnder as lab composition (lab vision §4): BS(θ) → phase(φ, m0) → BS(θ).
        theta = _num(p.get("theta"), where, "theta")
        phi = _num(p.get("phi", 0.0), where, "phi")
        st = beamsplitter(state, phys[0], phys[1], theta, 0.0)
        st = phase(st, phi, phys[0])
        return beamsplitter(st, phys[0], phys[1], theta, 0.0), None
    if op == "measure_homodyne":
        phi = _num(p.get("phi", 0.0), where, "phi")
        if rng is None:
            outcome = homodyne_mean(state, phys[0], phi)
            st = homodyne_condition(state, phys[0], phi, outcome)
        else:
            outcome, st = homodyne_sample_and_condition(
                state, phys[0], phi, rng=rng
            )
        _remove_phys(mapping, node.modes[0], phys[0])
        return st.remove_mode(phys[0]), {
            "op": "measure_homodyne", "mode": node.modes[0], "phi": phi,
            "outcome": outcome,
        }
    if op == "measure_heterodyne":
        if rng is None:
            outcome = heterodyne_mean(state, phys[0])
            st = heterodyne_condition(state, phys[0], outcome)
        else:
            outcome, st = heterodyne_sample_and_condition(
                state, phys[0], rng=rng
            )
        _remove_phys(mapping, node.modes[0], phys[0])
        entry: dict[str, Any] = {
            "op": "measure_heterodyne", "mode": node.modes[0],
            "outcome": [outcome.real, outcome.imag],
        }
        return st, entry
    raise CircuitV0Error(f"{where}: unsupported op {op!r}")  # pragma: no cover


def _remove_phys(mapping: list[int], logical: int, phys: int) -> None:
    """Mark logical mode removed; higher logical modes shift down (compile.py
    L147-152 semantics — v1 uses logical indices end to end)."""
    mapping[logical] = -1
    for i in range(len(mapping)):
        if mapping[i] > phys:
            mapping[i] -= 1


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
    wigner=None + meters.singular instead of fabricating data. All modes
    measured away (nmode==0) → empty result, no Wigner, honest zero meters."""
    if state.nmode == 0:
        return RunResult(
            nmode=0,
            rbar=np.zeros(0),
            V=np.zeros((0, 0)),
            wigner=None,
            meters={"purity": None, "mean_photon": 0.0,
                    "mean_photon_per_mode": [], "log_negativity": None,
                    "singular": False},
            measured=measured,
        )
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


def _execute(
    circuit: LabCircuit, *, rng: np.random.Generator | None = None
) -> RunResult:
    """Shared execution core: ordered ops → final GaussianState + result.
    rng=None → mean path (/run); rng given → sample every measurement node."""
    state = GaussianState.vacuum(circuit.core.nmode)
    mapping = list(range(circuit.core.nmode))
    measured: list[dict[str, Any]] = []
    for node in circuit.core.ops:
        state, entry = _apply(node, state, mapping, rng=rng)
        if entry is not None:
            measured.append(entry)
    return _build_result(state, circuit.view, measured)


def run_circuit(circuit: LabCircuit) -> RunResult:
    """Compile + run (mean path): ordered ops → result. Pure, no RNG."""
    return _execute(circuit, rng=None)


def sample_circuit(circuit: LabCircuit, rng: np.random.Generator) -> RunResult:
    """Compile + run with true sampling of every measurement node, in node
    order; each measurement conditions the state for the next one."""
    return _execute(circuit, rng=rng)


# -- scan -------------------------------------------------------------------

def _state_after(core: CircuitV1) -> GaussianState:
    """Final GaussianState for a circuit without measurement nodes (scan path)."""
    state = GaussianState.vacuum(core.nmode)
    mapping = list(range(core.nmode))
    for node in core.ops:
        state, _ = _apply(node, state, mapping, rng=None)
    return state


def _safe_logneg(state: GaussianState, modes_A: list[int]) -> float | None:
    """E_N on the current state; None when undefined (singular etc.), never fabricated."""
    try:
        v = float(log_negativity(state, modes_A=modes_A))
        return v if math.isfinite(v) else None
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        return None


def scan_circuit(circuit: LabCircuit, sweep: dict[str, Any]) -> dict[str, Any]:
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

    core = circuit.core
    node = next((nd for nd in core.ops if nd.id == node_id), None)
    if node is None:
        raise CircuitV0Error(f"sweep: unknown node_id {node_id!r}")
    if param not in SWEEPABLE_PARAMS.get(node.op, frozenset()):
        raise CircuitV0Error(
            f"sweep: param {param!r} is not sweepable for op {node.op!r}"
        )
    for nd in core.ops:
        if nd.op in MEASUREMENT_OPS:
            raise CircuitV0Error(
                f"sweep: measurement node {nd.id!r} ({nd.op}) — E_N undefined on "
                "conditional states"
            )

    nmode = _state_after(core).nmode  # also validates the circuit runs
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
        new_ops: list[IRNode] = []
        for nd in core.ops:
            params = dict(nd.params)
            if nd.id == node_id:
                params[param] = float(x)
            new_ops.append(IRNode(id=nd.id, op=nd.op, params=params, modes=nd.modes))
        st = _state_after(replace(core, ops=tuple(new_ops)))
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
