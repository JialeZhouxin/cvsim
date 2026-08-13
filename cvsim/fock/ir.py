"""circuit_v1 IR for FockCircuit (ADR-0003: single schema, shared encoding).

Same JSON-native value encoding as ``cvsim.gaussian.ir`` (complex as
``[re, im]``, matrices as nested lists, symbolic ``$param``, feedforward
``$ref``) plus a top-level ``cutoff`` extension (int or per-mode list).
The module is self-contained — ``cvsim.fock`` must not import ``cvsim.gaussian``
(ADR-0001), so the ~40 lines of value codecs are mirrored with the
convention documented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from cvsim.circuit_common import ParamRef
from cvsim.fock.circuit import FockCircuit

SCHEMA = "circuit_v1"

#: Top-level fields carried through by the Lab (view/seed/ui are UI concerns,
#: ADR-0003 #8; ``backend`` selects the representation, ``initial`` is parsed
#: below as a real field). ``cutoff`` is handled separately (not ignored).
EXTENSION_FIELDS = frozenset({"view", "seed", "ui", "backend"})


@dataclass(frozen=True)
class OpMeta:
    arity: str  # 'one' | 'two' | 'all' | 'any' | 'none'
    value_kind: dict[str, str]  # 'num' | 'complex' | 'matrix' | 'str' | 'kraus'
    defaults: dict[str, Any]


OP_META: dict[str, OpMeta] = {
    "squeeze": OpMeta("one", {"r": "num"}, {"r": 0.0}),
    "displace": OpMeta("one", {"alpha": "complex"}, {"alpha": 0.0}),
    "phase": OpMeta("one", {"theta": "num"}, {"theta": 0.0}),
    "kerr": OpMeta("one", {"chi": "num"}, {"chi": 0.0}),
    "beamsplitter": OpMeta(
        "two", {"theta": "num", "phi": "num"}, {"theta": np.pi / 4, "phi": 0.0}
    ),
    "two_mode_squeeze": OpMeta("two", {"r": "num"}, {"r": 0.0}),
    "cz": OpMeta("two", {"weight": "num"}, {"weight": 1.0}),
    "cx": OpMeta("two", {"weight": "num"}, {"weight": 1.0}),
    "mach_zehnder": OpMeta(
        "two", {"theta": "num", "phi": "num"}, {"theta": np.pi / 4, "phi": 0.0}
    ),
    "interferometer": OpMeta("all", {"U": "matrix"}, {}),
    "apply_unitary": OpMeta("any", {"U": "matrix"}, {}),
    "loss": OpMeta("one", {"eta": "num"}, {"eta": 1.0}),
    "amplifier": OpMeta("one", {"G": "num", "nbar": "num"}, {"G": 1.0, "nbar": 0.0}),
    "phase_noise": OpMeta("one", {"sigma": "num"}, {"sigma": 0.0}),
    "apply_kraus": OpMeta("one", {"kraus_ops": "kraus"}, {}),
    "measure_pnr": OpMeta("one", {"name": "str"}, {}),
    "measure_homodyne": OpMeta("one", {"phi": "num", "name": "str"}, {"phi": 0.0}),
    "measure_heterodyne": OpMeta("one", {"name": "str"}, {}),
}

_ARITY_MAX = {"one": 1, "two": 2}


def _encode(v: Any) -> Any:
    """Python value → JSON-native (complex → [re, im], ndarray → nested)."""
    if isinstance(v, complex):
        return [v.real, v.imag]
    if isinstance(v, np.ndarray):
        return _encode(v.tolist())
    if isinstance(v, list):
        return [_encode(x) for x in v]
    if isinstance(v, (np.integer, np.floating)):
        return v.item()
    return v


def _decode(v: Any, kind: str) -> Any:
    """JSON-native value → Python value (structural sanity assumed)."""
    if isinstance(v, dict):
        if "$param" in v:
            return v["$param"]
        if "$ref" in v:
            return ParamRef(v["$ref"], v.get("gain", 1.0))
    if isinstance(v, list):
        if kind == "complex":
            return complex(v[0], v[1])
        if kind == "kraus":
            return [
                np.array([[complex(x[0], x[1]) for x in row] for row in k])
                for k in v
            ]
        if v and isinstance(v[0], list) and v[0] and isinstance(v[0][0], list):
            return np.array(
                [[complex(x[0], x[1]) for x in row] for row in v], dtype=complex
            )
        return np.asarray(v, dtype=float)
    if kind == "complex":
        return complex(v)
    return v


def validate_ir(data: dict[str, Any]) -> None:
    """Structural validation of a Fock circuit_v1 dict (mirror of gaussian)."""
    if not isinstance(data, dict):
        raise ValueError(f"payload must be a JSON object, got {type(data).__name__}")
    if data.get("schema") != SCHEMA:
        raise ValueError(f"unsupported schema {data.get('schema')!r}, expected {SCHEMA!r}")
    nmode = data.get("nmode")
    if not isinstance(nmode, int) or isinstance(nmode, bool) or nmode < 1:
        raise ValueError(f"nmode must be an int >= 1, got {nmode!r}")
    for key in data:
        if key in ("schema", "nmode", "ops", "cutoff", "initial") or key in EXTENSION_FIELDS:
            continue
        raise ValueError(f"unknown top-level field {key!r}")
    cutoff = data.get("cutoff")
    if cutoff is not None:
        if isinstance(cutoff, int) and cutoff >= 1:
            pass  # uniform across modes
        elif (
            isinstance(cutoff, list)
            and len(cutoff) == nmode
            and all(isinstance(c, int) and c >= 1 for c in cutoff)
        ):
            pass
        else:
            raise ValueError(
                f"cutoff must be an int >= 1 or a list of nmode ints, got {cutoff!r}"
            )
    cutoffs = (
        [cutoff] * nmode
        if isinstance(cutoff, int)
        else (cutoff if isinstance(cutoff, list) else [10] * nmode)
    )
    initial = data.get("initial")
    if initial is not None:
        if (
            not isinstance(initial, list)
            or len(initial) != nmode
            or not all(isinstance(n, int) and not isinstance(n, bool) for n in initial)
        ):
            raise ValueError(
                f"initial must be a list of nmode={nmode} ints, got {initial!r}"
            )
        for i, (n, c) in enumerate(zip(initial, cutoffs, strict=True)):
            if not 0 <= n < c:
                raise ValueError(f"initial[{i}]={n} must be in [0, {c})")
    if not isinstance(data.get("ops"), list):
        raise ValueError("ops must be a list")
    for op in data["ops"]:
        if not isinstance(op, dict) or "op" not in op:
            raise ValueError("each op must be an object with 'op'")
        name = op["op"]
        if name not in OP_META:
            raise ValueError(f"unsupported op {name!r}")
        meta = OP_META[name]
        modes = op.get("modes", [])
        if not isinstance(modes, list) or not all(isinstance(m, int) for m in modes):
            raise ValueError(f"op {name}: modes must be a list of ints")
        if meta.arity in ("one", "two") and len(modes) != _ARITY_MAX[meta.arity]:
            raise ValueError(f"op {name}: expected {meta.arity} mode(s), got {len(modes)}")
        for k in op.get("params", {}):
            if k not in meta.value_kind:
                raise ValueError(f"op {name}: unknown param {k!r}")


def to_ir(circuit: FockCircuit) -> dict[str, Any]:
    """Serialize a FockCircuit to a circuit_v1 dict (with ``cutoff``)."""
    ops: list[dict[str, Any]] = []
    for op_name, modes, fixed, pnames, refs in circuit._ops:
        params: dict[str, Any] = {}
        for k, v in fixed.items():
            if v is None:
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
    uniform = len(set(circuit.cutoffs)) == 1
    cutoff: Any = circuit.cutoffs[0] if uniform else circuit.cutoffs
    doc: dict[str, Any] = {"schema": SCHEMA, "nmode": circuit.nmode, "ops": ops}
    if cutoff != 10:
        doc["cutoff"] = cutoff
    if circuit.initial is not None and any(n != 0 for n in circuit.initial):
        doc["initial"] = list(circuit.initial)
    return doc


def _build_op(circuit: FockCircuit, op: str, modes: tuple[int, ...], kw: dict) -> None:
    m0 = modes[0] if modes else None
    m1 = modes[1] if len(modes) > 1 else None
    if op == "squeeze":
        circuit.squeeze(m0, r=kw["r"])
    elif op == "displace":
        circuit.displace(m0, alpha=kw["alpha"])
    elif op == "phase":
        circuit.phase(m0, theta=kw["theta"])
    elif op == "kerr":
        circuit.kerr(m0, chi=kw["chi"])
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
    elif op == "apply_unitary":
        circuit.apply_unitary(kw["U"], modes=list(modes))
    elif op == "loss":
        circuit.loss(m0, eta=kw["eta"])
    elif op == "amplifier":
        circuit.amplifier(m0, G=kw["G"], nbar=kw["nbar"])
    elif op == "phase_noise":
        circuit.phase_noise(m0, sigma=kw["sigma"])
    elif op == "apply_kraus":
        circuit.apply_kraus(m0, kw["kraus_ops"])
    elif op == "measure_pnr":
        circuit.measure_pnr(m0, kw["name"])
    elif op == "measure_homodyne":
        circuit.measure_homodyne(m0, kw["phi"], kw["name"])
    elif op == "measure_heterodyne":
        circuit.measure_heterodyne(m0, kw["name"])
    else:  # pragma: no cover
        raise ValueError(f"unsupported op {op!r}")


def from_ir(data: dict[str, Any]) -> FockCircuit:
    """Rebuild a FockCircuit from a circuit_v1 dict (with cutoff/initial)."""
    validate_ir(data)
    cutoff = data.get("cutoff", 10)
    circuit = FockCircuit(
        data["nmode"], cutoff=cutoff, initial=data.get("initial")
    )
    for node in data["ops"]:
        meta = OP_META[node["op"]]
        kw = dict(meta.defaults)
        for k, v in node.get("params", {}).items():
            kw[k] = _decode(v, meta.value_kind[k])
        _build_op(circuit, node["op"], tuple(node.get("modes", [])), kw)
    return circuit
