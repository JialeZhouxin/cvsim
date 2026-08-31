"""Representation-agnostic circuit DSL core (ADR-0004).

Shared by ``cvsim.gaussian`` and ``cvsim.fock``: op-list 5-tuples,
parameter partitioning, segment compilation skeleton, and the compiled
runner base class. Physics is injected per representation via registries
(factor/dispatch tables) — see ADR-0004 §1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    Public surface: ``nmode``, ``params``, ``run(**values)``.
    """

    def __init__(self, nmode: int, segments: list[tuple[Any, ...]], params: frozenset[str]) -> None:
        self.nmode = nmode
        self.params = params
        self._segments = list(segments)

    def run(self, *, rng: Any = None, **values: Any) -> Any:
        """Execute compiled segments. Semantics per subclass (see Circuit.run)."""
        st = self._init_state()
        results: dict[str, Any] = {}
        for seg in self._segments:
            if seg[0] == "merged":
                _, nmode, ops = seg
                st = self._apply_merged(ops, nmode, values, st)
                continue
            st, results = self._run_op(seg[1], st, results, values, rng=rng)
        if results:
            return st, results
        return st

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
