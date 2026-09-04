"""circuit_v1 IR for BosonicCircuit (B5, ADR-0003 third consumer).

Mirrors the Gaussian IR path: structural validation, value encoding,
``BosonicCircuit`` serialization. No representation-specific extension
fields (vacuum start, K=1 constant). Lab extension fields (view/seed/ui/
backend/cutoff/initial) are accepted and ignored at this layer.

Value encoding is JSON-native and identical to the Gaussian path (complex
→ ``[re, im]``, matrix → nested arrays, symbolic → ``$param``, feedforward
→ ``$ref``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

from cvsim.bosonic.circuit import BosonicCircuit
from cvsim.bosonic.circuit import ParamRef as ParamRef
from cvsim.bosonic.state import BosonicState

SCHEMA = "circuit_v1"

#: Top-level extension fields (Lab/UI concepts; ignored at this layer).
EXTENSION_FIELDS = frozenset({"view", "seed", "ui", "cutoff", "backend", "initial"})

#: ``gaussian_channel`` execution-control flag stored in ``_ops.fixed``;
#: not physics, not part of the IR (from_ir re-defaults validate=True).
_EXECUTION_ONLY_PARAMS = frozenset({"validate"})

#: Core-enforced parameter ranges (Q6: only ranges the library functions
#: actually raise on — spec `.scratch/schema-single-source/spec.md`).
CORE_PARAM_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "loss": {"T": (0.0, 1.0)},
}

#: Initial-state source registry (schema snapshot, Q4+C: single authority).
#
#  Name → zero-arg factory returning a 1-mode BosonicState. Factories import
#  lazily inside the call so this module stays free of gkp/state runtime
#  imports (circuit.py imports state.py; gkp.py imports state.py — no cycles).
#
#  ``None`` = vacuum is a registry-level constant (INITIAL_VACUUM), not an
#  entry here: vacuum is state.vacuum, not a named source.
#
#  This dict is the ONLY place a new initial source is declared — the
#  circuit loader resolves through it and ``ir_schema()`` publishes it
#  (the gkp0_2d incident, e907db9, was a missed mirror of exactly this).
INITIAL_VACUUM: None = None

INITIAL_SOURCES: dict[str, Callable[[], BosonicState]] = {
    "gkp0": lambda: _initial_gkp(lattice="1d"),
    "gkp1": lambda: _initial_gkp(lattice="1d", logical=1),
    "gkp0_2d": lambda: _initial_gkp(lattice="2d", cross="full"),
    "gkp1_2d": lambda: _initial_gkp(lattice="2d", logical=1, cross="full"),
}

def _initial_gkp(
    lattice: str, logical: int = 0, cross: str | None = None
) -> BosonicState:
    """Lazily-importing GKP factory bridging source names → gkp.py kwargs."""
    from cvsim.bosonic.gkp import gkp0, gkp1

    builder = gkp1 if logical == 1 else gkp0
    kwargs: dict[str, Any] = {"lattice": lattice}
    if cross is not None:
        kwargs["cross"] = cross
    return builder(**kwargs)

def resolve_initial_state(name: str) -> BosonicState:
    """Resolve one initial-source name to a 1-mode BosonicState.

    Raises ValueError listing every legal name (registry-derived, so the
    message can never drift from the table).
    """
    factory = INITIAL_SOURCES.get(name)
    if factory is None:
        raise ValueError(
            f"initial: unknown state source {name!r} "
            f"(None|{'|'.join(repr(s) for s in INITIAL_SOURCES)})"
        )
    return factory()



@dataclass(frozen=True)
class OpMeta:
    """Per-op IR contract: mode arity, param value kinds, omitted-param defaults."""

    arity: str  # 'one' | 'two' | 'all' | 'any' | 'none'
    value_kind: dict[str, str]  # param name -> 'num' | 'complex' | 'matrix' | 'str'
    defaults: dict[str, Any]  # omitted params = library builder defaults


OP_META: dict[str, OpMeta] = {
    "squeeze": OpMeta("one", {"r": "num", "phi": "num"}, {"r": 0.0, "phi": 0.0}),
    "displace": OpMeta("one", {"alpha": "complex"}, {"alpha": 0.0}),
    "phase": OpMeta("one", {"theta": "num"}, {"theta": 0.0}),
    "fourier": OpMeta("one", {}, {}),
    "beamsplitter": OpMeta("two", {"theta": "num", "phi": "num"}, {"theta": np.pi / 4, "phi": 0.0}),
    "two_mode_squeeze": OpMeta("two", {"r": "num"}, {"r": 0.0}),
    "cz": OpMeta("two", {"weight": "num"}, {"weight": 0.0}),
    "cx": OpMeta("two", {"weight": "num"}, {"weight": 0.0}),
    "mach_zehnder": OpMeta("two", {"theta": "num", "phi": "num"}, {"theta": np.pi / 4, "phi": 0.0}),
    "interferometer": OpMeta("all", {"U": "matrix"}, {}),
    "loss": OpMeta("one", {"T": "num", "nbar": "num"}, {"T": 1.0, "nbar": 0.0}),
    "amplifier": OpMeta("any", {"G": "num", "nbar": "num"}, {"G": 1.0, "nbar": 0.0}),
    "phase_noise": OpMeta("any", {"sigma": "num"}, {"sigma": 0.0}),
    "gaussian_channel": OpMeta("none", {"X": "matrix", "Y": "matrix", "d": "matrix"}, {"d": None}),
    "measure_homodyne": OpMeta("one", {"phi": "num", "name": "str"}, {"phi": 0.0}),
    "measure_heterodyne": OpMeta("one", {"name": "str"}, {}),
    "measure_threshold": OpMeta("one", {"name": "str"}, {}),
}


@dataclass(frozen=True)
class IRNode:
    """One op of a circuit_v1 document. ``id`` is optional (core ignores it)."""

    id: str | None
    op: str
    params: dict[str, Any]
    modes: tuple[int, ...]


@dataclass(frozen=True)
class CircuitV1:
    """Validated circuit_v1 document (core model; no seed/view/ui)."""

    schema: str
    nmode: int
    ops: tuple[IRNode, ...]


# -- value checks -----------------------------------------------------------


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)


def _is_leaf_pair(v: Any) -> bool:
    return isinstance(v, list) and len(v) == 2 and _is_num(v[0]) and _is_num(v[1])


def _check_matrix(v: Any, where: str) -> None:
    if not isinstance(v, list) or not v:
        raise ValueError(f"{where}: must be a non-empty array, got {v!r}")
    if all(_is_num(x) for x in v):
        return  # flat real vector (e.g. d)
    style: str | None = None
    ncols: int | None = None
    for row in v:
        if not isinstance(row, list) or not row:
            raise ValueError(f"{where}: array rows must be non-empty lists, got {row!r}")
        if ncols is None:
            ncols = len(row)
        elif len(row) != ncols:
            raise ValueError(f"{where}: ragged array (row length {len(row)} != {ncols})")
        if all(_is_num(x) for x in row):
            row_style = "real"
        elif all(_is_leaf_pair(x) for x in row):
            row_style = "complex"
        else:
            raise ValueError(f"{where}: entries must be numbers or [re, im] pairs, got {row!r}")
        if style is None:
            style = row_style
        elif style != row_style:
            raise ValueError(f"{where}: mixed real/complex entries ({style} vs {row_style})")


def _check_value(v: Any, kind: str, where: str) -> None:
    if isinstance(v, dict):
        if "$param" in v:
            if kind not in ("num", "complex"):
                raise ValueError(f"{where}: $param not allowed for {kind} param")
            if set(v) != {"$param"}:
                raise ValueError(f"{where}: $param must be the only key, got {sorted(v)}")
            name = v["$param"]
            if not isinstance(name, str) or not name:
                raise ValueError(f"{where}: $param must be a non-empty string, got {name!r}")
            return
        if "$ref" in v:
            if kind not in ("num", "complex"):
                raise ValueError(f"{where}: $ref not allowed for {kind} param")
            if not set(v) <= {"$ref", "gain"}:
                raise ValueError(f"{where}: $ref allows only 'gain', got {sorted(v)}")
            src = v["$ref"]
            if not isinstance(src, str) or not src:
                raise ValueError(f"{where}: $ref source must be a non-empty string, got {src!r}")
            gain = v.get("gain", 1.0)
            if not _is_num(gain):
                raise ValueError(f"{where}: $ref gain must be a number, got {gain!r}")
            return
        raise ValueError(
            f"{where}: unknown value form (expected $param/$ref or bare JSON), got {v!r}"
        )
    if kind == "num":
        if not _is_num(v):
            raise ValueError(f"{where}: must be a number, got {v!r}")
    elif kind == "complex":
        if _is_num(v):
            return
        if isinstance(v, list) and len(v) == 2 and _is_num(v[0]) and _is_num(v[1]):
            return
        raise ValueError(f"{where}: must be a number or [re, im], got {v!r}")
    elif kind == "matrix":
        _check_matrix(v, where)
    elif kind == "str":
        if not isinstance(v, str) or not v:
            raise ValueError(f"{where}: must be a non-empty string, got {v!r}")
    else:  # pragma: no cover — OP_META is static
        raise ValueError(f"{where}: unknown value kind {kind!r}")


def validate_ir(data: dict[str, Any]) -> CircuitV1:
    """Structural validation of a circuit_v1 JSON dict (ADR-0003 #6)."""
    if not isinstance(data, dict):
        raise ValueError(f"payload must be a JSON object, got {type(data).__name__}")
    schema = data.get("schema")
    if schema != SCHEMA:
        raise ValueError(f"unsupported schema {schema!r}, expected {SCHEMA!r}")
    nmode = data.get("nmode")
    if not isinstance(nmode, int) or isinstance(nmode, bool) or nmode < 1:
        raise ValueError(f"nmode must be an int >= 1, got {nmode!r}")
    for key in data:
        if key in ("schema", "nmode", "ops") or key in EXTENSION_FIELDS:
            continue
        raise ValueError(f"unknown top-level field {key!r}")
    if "view" in data and not isinstance(data["view"], dict):
        raise ValueError(f"view must be an object, got {type(data['view']).__name__}")
    if "seed" in data and (
        not isinstance(data["seed"], int) or isinstance(data["seed"], bool) or data["seed"] < 0
    ):
        raise ValueError(f"seed must be a non-negative int, got {data['seed']!r}")
    if "ui" in data and not isinstance(data["ui"], dict):
        raise ValueError(f"ui must be an object, got {type(data['ui']).__name__}")
    raw_ops = data.get("ops")
    if not isinstance(raw_ops, list):
        raise ValueError(f"ops must be a list, got {type(raw_ops).__name__}")
    ops: list[IRNode] = []
    seen_ids: set[str] = set()
    for i, rn in enumerate(raw_ops):
        where = f"ops[{i}]"
        if not isinstance(rn, dict):
            raise ValueError(f"{where}: must be an object, got {type(rn).__name__}")
        op = rn.get("op")
        if not isinstance(op, str) or op not in OP_META:
            raise ValueError(f"{where}: unknown op {op!r}")
        meta = OP_META[op]
        nid = rn.get("id")
        if nid is not None:
            if not isinstance(nid, str) or not nid:
                raise ValueError(f"{where}: id must be a non-empty string, got {nid!r}")
            if nid in seen_ids:
                raise ValueError(f"{where}: duplicate id {nid!r}")
            seen_ids.add(nid)
        modes = rn.get("modes")
        if not isinstance(modes, list):
            raise ValueError(f"{where}: modes must be a list, got {type(modes).__name__}")
        if meta.arity == "one" and len(modes) != 1:
            raise ValueError(f"{where}: op {op!r} requires exactly 1 mode, got {len(modes)}")
        if meta.arity == "two" and len(modes) != 2:
            raise ValueError(f"{where}: op {op!r} requires exactly 2 modes, got {len(modes)}")
        if meta.arity == "all" and modes != list(range(nmode)):
            raise ValueError(
                f"{where}: op {op!r} requires modes == list(range(nmode)), got {modes!r}"
            )
        if meta.arity == "any" and len(modes) > 1:
            raise ValueError(
                f"{where}: op {op!r} takes at most 1 mode ([] = all), got {len(modes)}"
            )
        if meta.arity == "none" and modes:
            raise ValueError(f"{where}: op {op!r} takes no modes, got {modes!r}")
        for m in modes:
            if not isinstance(m, int) or isinstance(m, bool) or m < 0:
                raise ValueError(f"{where}: mode index must be a non-negative int, got {m!r}")
            if m >= nmode:
                raise ValueError(f"{where}: mode {m} out of range (nmode={nmode})")
        params = rn.get("params")
        if not isinstance(params, dict):
            raise ValueError(f"{where}: params must be an object, got {type(params).__name__}")
        for k, v in params.items():
            if k not in meta.value_kind:
                raise ValueError(f"{where}: unknown param {k!r} for op {op!r}")
            _check_value(v, meta.value_kind[k], f"{where}.params.{k}")
        for k in meta.value_kind:
            if k not in meta.defaults and k not in params:
                raise ValueError(f"{where}: op {op!r} requires param {k!r} (no default)")
        ops.append(IRNode(id=nid, op=op, params=dict(params), modes=tuple(modes)))
    return CircuitV1(schema=SCHEMA, nmode=nmode, ops=tuple(ops))


# -- value encoding ---------------------------------------------------------


def _encode(v: Any) -> Any:
    if isinstance(v, ParamRef):
        return {"$ref": v.source, "gain": v.gain}
    if isinstance(v, complex):
        return [v.real, v.imag]
    if isinstance(v, np.ndarray):
        if v.dtype.kind == "c":
            if v.ndim != 2:  # pragma: no cover — builders only store 2-D U
                raise ValueError(f"complex array encoding requires 2-D, got shape {v.shape}")
            return [[[z.real, z.imag] for z in row] for row in v]
        return v.tolist()
    if isinstance(v, np.generic):
        return v.item()
    return v


def _decode(v: Any, kind: str) -> Any:
    if isinstance(v, dict):
        if "$param" in v:
            return v["$param"]
        if "$ref" in v:
            return ParamRef(v["$ref"], v.get("gain", 1.0))
    if isinstance(v, list):
        if kind == "complex":
            return complex(v[0], v[1])
        if v and isinstance(v[0], list) and v[0] and isinstance(v[0][0], list):
            return np.array([[complex(x[0], x[1]) for x in row] for row in v], dtype=complex)
        return np.asarray(v, dtype=float)
    if kind == "complex":
        return complex(v)
    return v


# -- serialization ----------------------------------------------------------


def to_ir(circuit: BosonicCircuit) -> dict[str, Any]:
    """Serialize a :class:`BosonicCircuit` to a circuit_v1 dict."""
    ops: list[dict[str, Any]] = []
    for op_name, modes, fixed, pnames, refs in circuit._ops:
        params: dict[str, Any] = {}
        for k, v in fixed.items():
            if k in _EXECUTION_ONLY_PARAMS or v is None:
                continue
            if isinstance(v, str):
                params[k] = v
            else:
                params[k] = _encode(v)
        for k, name in pnames.items():
            params[k] = {"$param": name}
        for k, ref in refs.items():
            params[k] = {"$ref": ref.source, "gain": ref.gain}
        ops.append({"op": op_name, "modes": list(modes), "params": params})
    out: dict[str, Any] = {"schema": SCHEMA, "nmode": circuit.nmode, "ops": ops}
    # B6 R1: serialize the per-mode name-list initial (custom BosonicState
    # initials are not IR-expressible; omitted → vacuum default on rebuild).
    if circuit._initial_spec is not None:
        out["initial"] = circuit._initial_spec
    return out


def _build_op(circuit: BosonicCircuit, op: str, modes: tuple[int, ...], kw: dict[str, Any]) -> None:
    # OpMeta arity: 'none' ops carry no modes; 'one'/'two' carry 1/2.
    m0 = modes[0] if modes else 0
    m1 = modes[1] if len(modes) > 1 else m0
    if op == "squeeze":
        circuit.squeeze(m0, r=kw["r"], phi=kw["phi"])
    elif op == "displace":
        circuit.displace(m0, alpha=kw["alpha"])
    elif op == "phase":
        circuit.phase(m0, theta=kw["theta"])
    elif op == "fourier":
        circuit.fourier(m0)
    elif op == "beamsplitter":
        circuit.beamsplitter(m0, m1, theta=kw["theta"], phi=kw["phi"])
    elif op == "two_mode_squeeze":
        circuit.two_mode_squeeze(m0, m1, r=kw["r"])
    elif op == "cz":
        circuit.cz(m0, m1, weight=kw["weight"])
    elif op == "cx":
        circuit.cx(m0, m1, weight=kw["weight"])
    elif op == "mach_zehnder":
        circuit.mach_zehnder(m0, m1, theta=kw["theta"], phi=kw["phi"])
    elif op == "interferometer":
        circuit.interferometer(kw["U"])
    elif op == "loss":
        circuit.loss(m0, T=kw["T"], nbar=kw["nbar"])
    elif op == "amplifier":
        circuit.amplifier(None if not modes else m0, G=kw["G"], nbar=kw["nbar"])
    elif op == "phase_noise":
        circuit.phase_noise(None if not modes else m0, sigma=kw["sigma"])
    elif op == "gaussian_channel":
        circuit.gaussian_channel(kw["X"], kw["Y"], kw.get("d"))
    elif op == "measure_homodyne":
        circuit.measure_homodyne(m0, kw["phi"], kw["name"])
    elif op == "measure_heterodyne":
        circuit.measure_heterodyne(m0, kw["name"])
    elif op == "measure_threshold":
        circuit.measure_threshold(m0, kw["name"])
    else:  # pragma: no cover — validate_ir gates OP_META
        raise ValueError(f"unsupported op {op!r}")


def from_ir(data: dict[str, Any]) -> BosonicCircuit:
    """Rebuild a :class:`BosonicCircuit` from a circuit_v1 dict."""
    doc = validate_ir(data)
    circuit = BosonicCircuit(doc.nmode, initial=data.get("initial"))
    for node in doc.ops:
        meta = OP_META[node.op]
        kw = dict(meta.defaults)
        for k, v in node.params.items():
            kw[k] = _decode(v, meta.value_kind[k])
        _build_op(circuit, node.op, node.modes, kw)
    return circuit

def ir_schema() -> dict[str, Any]:
    """Read-only schema snapshot: op shapes + initial registry (schema snapshot).

    Pure-data dict — the authoritative entry point for circuit_v1 schema
    knowledge of this package (ADR-0003; spec ticket 1). ``OpMeta`` stays
    private; callers get plain JSON-native data only::

        {"ops": {op: {"arity", "value_kind", "defaults"}},
         "initial": {"kind": "enum", "sources": [...], "vacuum": None},
         "core_ranges": {op: {param: [lo, hi]}}}

    Bosonic initial semantics (CONTEXT: 初始态字段): per-mode source names
    from ``INITIAL_SOURCES`` (``None`` = vacuum). Returns a fresh deep copy
    per call — mutating the payload cannot affect package state.
    """
    return {
        "ops": {
            name: {
                "arity": meta.arity,
                "value_kind": dict(meta.value_kind),
                "defaults": _json_defaults(meta.defaults),
            }
            for name, meta in OP_META.items()
        },
        "initial": {
            "kind": "enum",
            "sources": list(INITIAL_SOURCES),
            "vacuum": INITIAL_VACUUM,
        },
        "core_ranges": {
            op: {p: list(r) for p, r in params.items()}
            for op, params in CORE_PARAM_RANGES.items()
        },
    }

def _json_defaults(defaults: dict[str, Any]) -> dict[str, Any]:
    """JSON-native defaults: numpy floats/arrays out, plain scalars/lists in."""
    out: dict[str, Any] = {}
    for k, v in defaults.items():
        if isinstance(v, np.generic):
            out[k] = v.item()
        elif isinstance(v, np.ndarray):
            out[k] = v.tolist()
        else:
            out[k] = v
    return out
