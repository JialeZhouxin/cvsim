"""Representation-agnostic circuit DSL core (ADR-0004).

Shared by ``cvsim.gaussian`` and ``cvsim.fock``: op-list 5-tuples,
parameter partitioning, segment compilation skeleton, and the compiled
runner base class. Physics is injected per representation via registries
(factor/dispatch tables) — see ADR-0004 §1.

Also the single home of the circuit_v1 **value checks** (num/complex/
matrix/str/kraus): the three ``*.ir`` validators used to carry their own
copies, which drifted (fock silently lacked them entirely). Messages are
part of the Lab's 422 contract and are frozen byte-for-byte by
``tests/test_lab_schema.py``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ParamRef:
    """Reference to a measurement outcome, scaled by gain.

    Used in circuit builder methods where a gate parameter depends on
    a prior measurement result.

    Usage::

        c.measure_homodyne(1, phi=0, name='m_x')
        c.displace(0, alpha=ParamRef('m_x', gain=0.5))
    """

    source: str
    gain: float = 1.0


def partition(
    op_name: str,
    modes: list[int],
    *,
    _fixed_str_keys: frozenset[str] = frozenset(),
    **kwargs: object,
) -> tuple[str, tuple[int, ...], dict[str, object], dict[str, str], dict[str, ParamRef]]:
    """Split builder kwargs into a 5-tuple (name, modes, fixed, params, refs).

    ``ParamRef`` values go to ``refs``; strings (symbolic parameters) to
    ``params`` unless the key is in ``_fixed_str_keys`` (e.g. measurement
    ``name``); everything else to ``fixed``.
    """
    fixed: dict[str, object] = {}
    params: dict[str, str] = {}
    refs: dict[str, ParamRef] = {}
    for k, v in kwargs.items():
        if isinstance(v, ParamRef):
            refs[k] = v
        elif isinstance(v, str) and k not in _fixed_str_keys:
            params[k] = v
        else:
            fixed[k] = v
    return (op_name, tuple(modes), fixed, params, refs)


def compile_segments(
    ops: list[tuple[Any, ...]],
    nmode: int,
    *,
    break_ops: frozenset[str],
    remove_mode_ops: frozenset[str],
) -> tuple[list[tuple[Any, ...]], frozenset[str]]:
    """Static segmentation with mode mapping resolved to physical coords.

    ``break_ops`` split a compile segment (channels / measurements / any op
    that cannot merge); ``remove_mode_ops`` additionally remove their target
    mode from the physical mapping (measurements that drop the mode).

    Returns ``(segments, params)`` where params = union of bindable
    parameter names (strings in ``pnames``). Segment entries are
    ``('merged', nmode, ops)`` or ``('op', op)``.
    """
    # ops from Circuit._ops: (name, orig_modes, fixed, pnames, refs)
    mapping: list[int] = list(range(nmode))
    segments: list[tuple[Any, ...]] = []
    merged: list[tuple[Any, ...]] = []
    params: set[str] = set()
    merged_nmode = nmode

    def flush() -> None:
        nonlocal merged
        if merged:
            segments.append(("merged", merged_nmode, merged))
            merged = []

    for op in ops:
        op_name, modes, fixed, pnames, refs = op
        params.update(pnames.values())
        if op_name in break_ops or refs:
            flush()
            if modes:
                phys = [mapping[m] for m in modes]
                if any(p < 0 for p in phys):
                    raise ValueError(f"{op_name} references a mode already measured/removed")
            else:
                phys = []
            segments.append(("op", (op_name, tuple(phys), fixed, pnames, refs)))
            if op_name in remove_mode_ops:
                phys_mode = mapping[modes[0]]
                nmode -= 1
                for i in range(len(mapping)):
                    if mapping[i] > phys_mode:
                        mapping[i] -= 1
                mapping[modes[0]] = -1
            continue
        # mergeable op
        if not merged:
            merged_nmode = nmode
        if modes:
            phys = [mapping[m] for m in modes]
            if any(p < 0 for p in phys):
                raise ValueError(f"{op_name} references a mode already measured/removed")
        else:
            phys = []
        merged.append((op_name, tuple(phys), fixed, pnames, refs))
    flush()
    return segments, frozenset(params)


class CompiledCircuit:
    """Compiled circuit: immutable segment snapshot; run() instantiates.

    Physics is representation-specific: subclasses implement
    ``_init_state`` / ``_apply_merged`` / ``_run_op`` (ADR-0004 §1).
    Public surface: ``nmode``, ``params``, ``run(**values)``,
    ``run_breaks(on_break, **values)``, ``run_op(op, st, results)``.

    ``run_breaks`` is the escape hatch for a caller that must inject its own
    break-point semantics (the Lab workbench: mean/sample split + ``measured``
    entries). It hands over the op tuple and its IR-node index, so the caller
    never reads the segment layout — that stays private (CONTEXT.md).
    """

    def __init__(self, nmode: int, segments: list[tuple[Any, ...]], params: frozenset[str]) -> None:
        self.nmode = nmode
        self.params = params
        self._segments = list(segments)

    def run(self, *, rng: Any = None, **values: Any) -> Any:
        """Execute compiled segments. Semantics per subclass (see Circuit.run)."""

        def _call(op: tuple[Any, ...], st: Any, results: dict[str, Any], _idx: int) -> Any:
            return self._run_op(op, st, results, values, rng=rng)

        st, results = self.run_breaks(_call, **values)
        if results:
            return st, results
        return st

    def run_op(
        self,
        op: tuple[Any, ...],
        st: Any,
        results: dict[str, Any],
        *,
        rng: Any = None,
        **values: Any,
    ) -> Any:
        """Execute one break-point op via this representation's dispatcher.

        Public wrapper over ``_run_op`` for callers that drive the traversal
        themselves through ``run_breaks``.
        """
        return self._run_op(op, st, results, values, rng=rng)

    def run_breaks(
        self,
        on_break: Callable[[tuple[Any, ...], Any, dict[str, Any], int], Any],
        **values: Any,
    ) -> tuple[Any, dict[str, Any]]:
        """Execute segments, delegating every break point to ``on_break``.

        ``on_break(op, state, results, ir_idx)`` returns ``(state, results)``.
        Merged segments are applied here (they carry no caller-visible
        semantics); ``ir_idx`` counts source ops consumed so far, so a caller
        can align each break point with its IR node without reading the
        segment layout.
        """
        st = self._init_state()
        results: dict[str, Any] = {}
        ir_idx = 0
        for seg in self._segments:
            if seg[0] == "merged":
                _, nmode, ops = seg
                st = self._apply_merged(ops, nmode, values, st)
                ir_idx += len(ops)
                continue
            st, results = on_break(seg[1], st, results, ir_idx)
            ir_idx += 1
        return st, results

    # -- representation-specific (subclass) ------------------------------

    def _init_state(self) -> Any:
        raise NotImplementedError

    def _apply_merged(
        self, ops: list[tuple[Any, ...]], nmode: int, values: dict[str, Any], st: Any
    ) -> Any:
        raise NotImplementedError

    def _run_op(
        self,
        op: tuple[Any, ...],
        st: Any,
        results: dict[str, Any],
        values: dict[str, Any],
        *,
        rng: Any = None,
    ) -> Any:
        raise NotImplementedError

    def __repr__(self) -> str:
        lines = [f"{type(self).__name__}({self.nmode})"]
        for seg in self._segments:
            if seg[0] == "merged":
                lines.append(f"  merged({len(seg[2])} ops)")
            else:
                op_name, modes, fixed, pnames, refs = seg[1]
                args = [str(m) for m in modes]
                args += [f"{k}={v}" for k, v in fixed.items()]
                args += [f"{k}=${{{v}}}" for k, v in pnames.items()]
                args += [f"{k}=${{{v.source}}}*{v.gain}" for k, v in refs.items()]
                lines.append(f"  .{op_name}({', '.join(args)})")
        return "\n".join(lines)


# -- circuit_v1 value checks (single source; ADR-0003 #6) -------------------
#
# The three representation validators share these verbatim. They lived as
# per-package copies and drifted: ``cvsim.fock.ir`` lost ``_check_value``
# entirely, so fock accepted payloads gaussian/bosonic reject (negative mode
# indices silently wrapped, bad param kinds slipped through as symbolic
# params). Message text is part of the Lab 422 contract — treat it as frozen
# (``tests/test_lab_schema.py`` locks some of it byte-for-byte).
#
# The dict forms ``$param`` / ``$ref`` are validated here even though a
# ``str`` param (measurement ``name``) cannot carry them: the kind gate runs
# first, so ``$param`` on a ``str`` param is rejected as misuse.

#: Value kinds understood by :func:`check_value`. ``kraus`` is fock-only;
#: the other packages simply never declare it.
VALUE_KINDS = ("num", "complex", "matrix", "str", "kraus")


def is_num(v: Any) -> bool:
    """JSON number (``bool`` is excluded — it is an ``int`` subclass)."""
    return isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)


def is_leaf_pair(v: Any) -> bool:
    """``[re, im]`` complex leaf inside a matrix."""
    return isinstance(v, list) and len(v) == 2 and is_num(v[0]) and is_num(v[1])


def check_matrix(v: Any, where: str) -> None:
    """Nested-array matrix: flat real vector, or rows of reals / ``[re, im]``."""
    if not isinstance(v, list) or not v:
        raise ValueError(f"{where}: must be a non-empty array, got {v!r}")
    if all(is_num(x) for x in v):
        return  # flat real vector (e.g. d)
    style: str | None = None  # 'real' | 'complex'
    ncols: int | None = None
    for row in v:
        if not isinstance(row, list) or not row:
            raise ValueError(f"{where}: array rows must be non-empty lists, got {row!r}")
        if ncols is None:
            ncols = len(row)
        elif len(row) != ncols:
            raise ValueError(f"{where}: ragged array (row length {len(row)} != {ncols})")
        if all(is_num(x) for x in row):
            row_style = "real"
        elif all(is_leaf_pair(x) for x in row):
            row_style = "complex"
        else:
            raise ValueError(f"{where}: entries must be numbers or [re, im] pairs, got {row!r}")
        if style is None:
            style = row_style
        elif style != row_style:
            raise ValueError(f"{where}: mixed real/complex entries ({style} vs {row_style})")


def check_kraus(v: Any, where: str) -> None:
    """``kraus`` value: non-empty list of 2-D matrices.

    Each matrix follows the same encoding as the ``matrix`` kind (nested
    reals, or ``[re, im]`` pairs) because ``to_ir`` emits whichever the
    operator's dtype actually is — a purely real Kraus operator (e.g. the
    sqrt(T) loss decomposition) encodes as plain reals. Requiring pairs
    unconditionally would reject this package's own serializer output.
    """
    if not isinstance(v, list) or not v:
        raise ValueError(f"{where}: must be a non-empty array of matrices, got {v!r}")
    for i, k in enumerate(v):
        if not isinstance(k, list) or not k:
            raise ValueError(f"{where}[{i}]: must be a non-empty matrix, got {k!r}")
        if all(is_num(x) for x in k):
            raise ValueError(f"{where}[{i}]: must be 2-D (rows), got a flat vector {k!r}")
        check_matrix(k, f"{where}[{i}]")


def check_value(v: Any, kind: str, where: str) -> None:
    """Validate one op param value against its declared ``kind``.

    A ``dict`` must be exactly ``{"$param": name}`` or ``{"$ref": name[,
    "gain": g]}``; anything else is rejected (only ``num``/``complex``
    params may be symbolic / feedforward).
    """
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
            if not is_num(gain):
                raise ValueError(f"{where}: $ref gain must be a number, got {gain!r}")
            return
        raise ValueError(
            f"{where}: unknown value form (expected $param/$ref or bare JSON), got {v!r}"
        )
    if kind == "num":
        if not is_num(v):
            raise ValueError(f"{where}: must be a number, got {v!r}")
    elif kind == "complex":
        if is_num(v):
            return
        if isinstance(v, list) and len(v) == 2 and is_num(v[0]) and is_num(v[1]):
            return
        raise ValueError(f"{where}: must be a number or [re, im], got {v!r}")
    elif kind == "matrix":
        check_matrix(v, where)
    elif kind == "kraus":
        check_kraus(v, where)
    elif kind == "str":
        if not isinstance(v, str) or not v:
            raise ValueError(f"{where}: must be a non-empty string, got {v!r}")
    else:  # pragma: no cover — OP_META is static
        raise ValueError(f"{where}: unknown value kind {kind!r}")


def json_defaults(defaults: dict[str, Any]) -> dict[str, Any]:
    """JSON-native op defaults: numpy scalars/arrays out, plain values in.

    ``ir_schema()`` advertises a JSON-native payload end to end, so every
    representation must normalise here — a bare ``dict(defaults)`` would leak
    ``np.float64`` into the Lab's schema response.
    """
    out: dict[str, Any] = {}
    for k, v in defaults.items():
        if isinstance(v, np.generic):
            out[k] = v.item()
        elif isinstance(v, np.ndarray):
            out[k] = v.tolist()
        else:
            out[k] = v
    return out

