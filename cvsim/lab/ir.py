"""Gaussian Lab circuit IR: `circuit_v1` load + extension fields.

Public API only: ``cvsim.gaussian`` ``__all__`` + ``cvsim.wigner.wigner_grid``.
No fastapi dependency here (see ``server.py``).

Schema split (ADR-0003): core schema/validation live in ``cvsim.gaussian.ir``
(``circuit_v1``, full op set). This module owns Lab concerns: the Lab op
whitelist and the view/seed/ui/initial/detail extension fields. Execution
lives in the per-backend runner modules (dispatch routes, ADR-0010) — this
module no longer imports any gaussian execution symbol.

v0 read compatibility was removed (ADR-0011): only ``circuit_v1`` loads.

v1 semantics (design §0, intentional unification vs v0):
- mode indices are **logical** (runtime keeps a logical→physical map; a
  measured/removed mode is marked -1 and higher logical modes shift down).
- homodyne **removes** the measured mode in both mean and sample paths
  (matches ``GaussianCircuit`` / vision §4.4; v0 kept it in place).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cvsim.bosonic.ir import validate_ir as validate_bosonic_ir
from cvsim.fock.ir import validate_ir as validate_fock_ir
from cvsim.gaussian.ir import SCHEMA as SCHEMA
from cvsim.gaussian.ir import CircuitV1, validate_ir
from cvsim.lab.schema import (
    _EXTENSIONS,
    BOSONIC_SOURCES,
    BOSONIC_WHITELIST,
    FOCK_WHITELIST,
    LAB_WHITELIST,
)

#: Lab op whitelists — **derived views** over the Lab schema assembly
#: layer (ticket 4): declared once in ``cvsim.lab.schema`` as core
#: `ir_schema()` ops minus an explicit UI-hidden set, imported back here.
#: The loader texts below are byte-identical to the pre-ticket hand-written
#: sets (golden 422 tests lock them). B6/F7 unlock history now lives in
#: `schema._UI_HIDDEN`.
MEASUREMENT_OPS = frozenset({"measure_homodyne", "measure_heterodyne"})

#: Lab-required params for break-point channel ops (core fills OpMeta
#: defaults silently; Lab rejects defaults to keep the workbench explicit,
#: mirroring the pre-unify ``_apply`` ``_num`` guards). Merged (unitary) ops
#: are type-checked by ``validate_ir`` and accept defaults — not listed here.
_LAB_REQUIRED_PARAMS: dict[str, tuple[str, ...]] = {
    "loss": ("T",),
    "amplifier": ("G",),
    "phase_noise": ("sigma",),
}


class CircuitV0Error(ValueError):
    """Invalid circuit payload; message is UI-safe. (Name predates ADR-0011:
    kept for import stability; v0 parsing has been removed.)

    Structured form (Q8, schema ticket 2): whitelist/initial rejections also
    carry ``code`` (error class), ``where`` (rendered prefix, verbatim from
    the raise site), ``op`` (offending op name or None) and ``allowed`` (the
    legal set, JSON-native) so the server can render one shared message
    template from single-source data. The default ``str(e)`` text stays
    authoritative and unchanged (golden 422 tests lock it byte-for-byte);
    the frontend does not consume ``code`` yet (extension space).
    """

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        where: str | None = None,
        op: str | None = None,
        allowed: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.where = where
        self.op = op
        self.allowed = allowed

    @property
    def structured(self) -> dict[str, Any] | None:
        """``{code, where, op, allowed}`` when this error carries structure."""
        if self.code is None:
            return None
        return {
            "code": self.code,
            "where": self.where,
            "op": self.op,
            "allowed": self.allowed,
        }


@dataclass
class View:
    wigner_mode: int = 0
    lim: float = 5.0
    n: int = 64
    plane: str = "single"  # gaussian: cross-mode quadrature plane (R8)
    joint_modes: list[int] | None = None  # Fock: 2-mode joint heatmap modes


def check_wigner_mode(mode: int, nmode: int) -> None:
    """Guard: post-run ``wigner_mode`` must index a mode that still exists.

    Single point for the 422 message template (ADR-0010 #5), and for the
    comparison itself — every call site tested exactly ``mode >= nmode``.

    Why the guard is *post*-run and not in :func:`_parse_view`: load time does
    not know ``nmode``. Measurements remove modes, so the surviving mode count
    is only known after execution — that is the one part that is genuinely
    per-backend (gaussian/fock raise from their assembly paths, bosonic also
    from its runner). The wording is not per-backend, and lived in three
    places: two byte-identical definitions plus a cross-package import from
    bosonic into fock (the ADR-0010 #5 registered exception).

    Callers with an extra precondition keep it locally: bosonic skips the
    guard when ``nmode == 0``, which cannot be folded in here because
    ``mode >= 0`` is true for every non-negative mode.

    Note the name: ADR-0010 #5 already called this ``check_wigner_mode``; the
    code had drifted to a private ``_wigner_mode_guard_fail`` whose name said
    "fail" but whose body did not check anything (callers did the compare).
    """
    if mode >= nmode:
        raise CircuitV0Error(f"view.wigner_mode {mode} out of range (nmode={nmode})")


def check_plane(modes: tuple[int, ...], nmode: int) -> None:
    """Guard: a cross-mode plane's two modes must exist and be distinct.

    Single point for the plane's 422 message template (ADR-0010 #5, same shape
    as :func:`check_wigner_mode`). Post-run, because measurements remove modes:
    ``joint_modes=[0,1]`` is a legal *load-time* request that stops being legal
    once a measurement leaves one mode behind.

    Fock's ``_fock_joint`` silently returns ``None`` for an out-of-range pair.
    That is not copied here: on the Gaussian side the pair *is* the definition
    of the plot's coordinates, so a missing mode must be an honest 422 rather
    than an empty picture.
    """
    for mode in modes:
        if mode < 0 or mode >= nmode:
            raise CircuitV0Error(
                f"view.joint_modes {list(modes)} out of range (nmode={nmode})"
            )
    if modes[0] == modes[1]:
        raise CircuitV0Error(
            f"view.joint_modes {list(modes)} must be two distinct modes"
        )


def _plane_axes(view: View, nmode: int) -> np.ndarray | None:
    """The (2, 2m) quadrature-combination matrix ``A`` for ``view.plane``.

    ``None`` means "single mode" — the caller keeps the legacy
    ``partial_trace(keep=[wigner_mode]) + wigner_grid`` path. Otherwise ``A``'s
    two rows are the plane's two axes in the full 2m xxpp space:
    ``xx`` → (x_k, x_j), ``pp`` → (p_k, p_j), ``epr`` → ((x_k−x_j)/√2,
    (p_k+p_j)/√2).

    The EPR rows carry 1/√2 so the plane stays a *vacuum-referenced* phase-space
    picture: a TMSV then shows an ellipse of variance e^{-2r}/2 against the
    vacuum 1/2, instead of a raw sum that would be twice as large. Callers
    validate the modes post-run via :func:`check_plane`.
    """
    if view.plane == "single":
        return None
    if view.joint_modes is None:
        # Load-time rejection already covers this; kept as a belt-and-braces
        # assert so a directly-constructed View cannot reach the grid as an
        # unlabeled (and therefore unreadable) plane.
        raise CircuitV0Error(f"view.plane {view.plane!r} requires view.joint_modes")
    if nmode < 2:
        raise CircuitV0Error(f"view.plane {view.plane!r} requires nmode >= 2 (nmode={nmode})")
    check_plane(tuple(view.joint_modes), nmode)
    k, j = view.joint_modes
    A = np.zeros((2, 2 * nmode))
    if view.plane == "xx":
        A[0, k], A[1, j] = 1.0, 1.0
    elif view.plane == "pp":
        A[0, nmode + k], A[1, nmode + j] = 1.0, 1.0
    elif view.plane == "epr":
        s = 1.0 / np.sqrt(2.0)
        A[0, k], A[0, j] = s, -s
        A[1, nmode + k], A[1, nmode + j] = s, s
    else:  # pragma: no cover - _parse_view rejects unknown presets first
        raise CircuitV0Error(f"view.plane {view.plane!r} is not a known preset")
    return A


@dataclass
class LabCircuit:
    """Lab-loaded circuit: core :class:`CircuitV1` + UI extension fields.

    ``seed`` / ``view`` / ``ui`` / ``backend`` / ``initial`` are Lab
    concerns (core IR ignores or carries them, ADR-0003 #8). Fock backend:
    ``core`` is None and ``raw`` holds the validated JSON dict (Fock
    execution rebuilds via ``FockCircuit.from_ir``).
    """

    core: CircuitV1 | None = None
    backend: str = "gaussian"
    seed: int = 0
    view: View = field(default_factory=View)
    ui: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    initial: list[int] | None = None
    detail: str | None = None  # bosonic-only: "steps" → per-break-point snapshots (ADR-0010 #4)


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


def _parse_view(raw: Any) -> View:
    if not isinstance(raw, dict):
        raise CircuitV0Error("view must be an object")
    wigner_mode = _as_pos_int(raw.get("wigner_mode", 0), "view.wigner_mode")
    lim = raw.get("lim", 5.0)
    _vlim = _EXTENSIONS["view"]["lim_max"]
    _vmin = _EXTENSIONS["view"]["lim_min_exclusive"]
    if not isinstance(lim, (int, float)) or isinstance(lim, bool) or lim <= _vmin or lim > _vlim:
        raise CircuitV0Error(f"view.lim must be a positive number <= {int(_vlim)}")
    n = raw.get("n", 64)
    _vn = _EXTENSIONS["view"]["n"]
    if not isinstance(n, int) or isinstance(n, bool) or n < _vn[0] or n > _vn[1]:
        raise CircuitV0Error(f"view.n must be an int in [{_vn[0]}, {_vn[1]}]")
    jm = raw.get("joint_modes")
    if jm is not None and (
        not isinstance(jm, list)
        or len(jm) != 2
        or jm[0] == jm[1]
        or not all(isinstance(m, int) and not isinstance(m, bool) and m >= 0 for m in jm)
    ):
        raise CircuitV0Error("view.joint_modes must be a list of two distinct non-negative ints")
    plane = raw.get("plane", "single")
    _planes = _EXTENSIONS["view"]["planes"]
    if plane not in _planes:
        raise CircuitV0Error(f"view.plane must be one of {_planes!r}, got {plane!r}")
    if plane != "single" and jm is None:
        # Load-time fact, independent of nmode: a plane with no pair of modes
        # cannot be labeled, so refusing here saves a full execution.
        raise CircuitV0Error(f"view.plane {plane!r} requires view.joint_modes")
    return View(
        wigner_mode=wigner_mode,
        lim=float(lim),
        n=n,
        plane=plane,
        joint_modes=None if jm is None else list(jm),
    )


def load_circuit(data: dict[str, Any]) -> LabCircuit:
    """Load + validate a circuit payload. ``circuit_v1`` only (ADR-0011:
    circuit_v0 read-compat removed).

    Routes by ``backend``: the Fock/Bosonic path validates against
    ``cvsim.fock.ir``/``cvsim.bosonic.ir`` + whitelist and keeps the raw
    dict; the Gaussian path enforces LAB_WHITELIST as before.
    """
    if not isinstance(data, dict):
        raise CircuitV0Error("payload must be a JSON object")
    if data.get("schema") != SCHEMA:
        raise CircuitV0Error(
            f"unsupported schema {data.get('schema')!r}; expected {SCHEMA!r}"
        )
    backend = data.get("backend", "gaussian")
    if backend not in ("gaussian", "fock", "bosonic"):
        raise CircuitV0Error(f"backend must be 'gaussian', 'fock' or 'bosonic', got {backend!r}")
    view = _parse_view(data.get("view", {}))
    if view.plane != "single" and backend != "gaussian":
        # R8 is gaussian-only. _parse_view is shared by all backends and runs
        # before the dispatch below, so without this the other two would
        # validate the plane, execute normally, and silently ignore it.
        raise CircuitV0Error(
            f"view.plane {view.plane!r} is only supported by the gaussian backend"
        )
    seed = data.get("seed", 0)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise CircuitV0Error("seed must be a non-negative int")
    ui = data.get("ui", {})
    if not isinstance(ui, dict):
        raise CircuitV0Error("ui must be an object")
    if backend == "fock":
        return _load_fock(data, seed, view, ui)
    if backend == "bosonic":
        return _load_bosonic(data, seed, view, ui)
    try:
        core = validate_ir(data)
    except ValueError as e:
        # Lab error surface is uniformly CircuitV0Error (server 422 contract,
        # error-handling spec); core validation speaks plain ValueError.
        raise CircuitV0Error(str(e)) from e
    for node in core.ops:
        if node.op not in LAB_WHITELIST:
            where = f"ops[{node.id or '?'}]"
            raise CircuitV0Error(
                f"{where}: op {node.op!r} not in Lab whitelist: {sorted(LAB_WHITELIST)}",
                code="op_not_whitelisted",
                where=where,
                op=node.op,
                allowed=sorted(LAB_WHITELIST),
            )
    return LabCircuit(core=core, seed=seed, view=view, ui=ui, raw=data, detail=data.get("detail"))


def _load_fock(data: dict[str, Any], seed: int, view: View, ui: dict[str, Any]) -> LabCircuit:
    """Fock backend load: FOCK_WHITELIST first, then fock IR validation.

    Whitelist is a UI concept (ADR-0003 #3): ops outside it are rejected
    with a whitelist message even when they are valid core Fock IR ops
    (interferometer / apply_unitary / apply_kraus). Checking before
    validate_fock_ir also gives the whitelist message for ops that are
    not Fock core ops at all (e.g. fourier).
    """
    for node in data.get("ops", []):
        op = node.get("op") if isinstance(node, dict) else None
        if op not in FOCK_WHITELIST:
            nid = node.get("id") if isinstance(node, dict) else "?"
            where = f"ops[{nid or '?'}]"
            raise CircuitV0Error(
                f"{where}: op {op!r} not in Fock Lab whitelist: {sorted(FOCK_WHITELIST)}",
                code="op_not_whitelisted",
                where=where,
                op=op,
                allowed=sorted(FOCK_WHITELIST),
            )
    try:
        validate_fock_ir(data)
    except ValueError as e:
        raise CircuitV0Error(str(e)) from e
    initial = data.get("initial")
    if initial is not None and (
        not isinstance(initial, list)
        or not all(isinstance(n, int) and not isinstance(n, bool) and n >= 0 for n in initial)
    ):
        raise CircuitV0Error("initial must be a list of non-negative ints")
    return LabCircuit(
        core=None,
        backend="fock",
        seed=seed,
        view=view,
        ui=ui,
        raw=data,
        initial=initial,
        detail=data.get("detail"),
    )


def _load_bosonic(data: dict[str, Any], seed: int, view: View, ui: dict[str, Any]) -> LabCircuit:
    """Bosonic backend load: BOSONIC_WHITELIST first, then bosonic IR validation.

    Mirrors the Fock path: whitelist is a UI concept (ADR-0003 #3); ops
    outside it are rejected with a whitelist message even when they are
    valid core Bosonic IR ops. Core is None — Bosonic execution rebuilds via
    ``BosonicCircuit.from_ir`` (initial field consumed there, B6).
    """
    for node in data.get("ops", []):
        op = node.get("op") if isinstance(node, dict) else None
        if op not in BOSONIC_WHITELIST:
            nid = node.get("id") if isinstance(node, dict) else "?"
            where = f"ops[{nid or '?'}]"
            raise CircuitV0Error(
                f"{where}: op {op!r} not in Bosonic Lab whitelist: {sorted(BOSONIC_WHITELIST)}",
                code="op_not_whitelisted",
                where=where,
                op=op,
                allowed=sorted(BOSONIC_WHITELIST),
            )
    try:
        validate_bosonic_ir(data)
    except ValueError as e:
        raise CircuitV0Error(str(e)) from e
    initial = data.get("initial")
    if initial is not None:
        # derived from the core initial registry (schema.BOSONIC_SOURCES,
        # ticket 4) — no hand-written mirror; text below stays byte-identical
        # (golden tests lock it).
        _bosonic_sources = list(BOSONIC_SOURCES)
        if not isinstance(initial, list) or not all(
            item is None or item in _bosonic_sources for item in initial
        ):
            # 整数项 = Fock 语义的 initial 跨到了 bosonic（GUI 切换 bug 的典型
            # 现场），给出可诊断的提示而不是让用户猜白名单。
            if isinstance(initial, list) and all(
                isinstance(item, int) and not isinstance(item, bool) for item in initial
            ):
                raise CircuitV0Error(
                    "initial looks like Fock photon numbers (ints) but backend is "
                    "'bosonic': bosonic takes GKP source names per mode "
                    "(null/'gkp0'/'gkp1'/'gkp0_2d'/'gkp1_2d')",
                    code="initial_semantics_mismatch",
                    op=None,
                    allowed=_bosonic_sources,
                )
            raise CircuitV0Error(
                "initial must be a list of null/'gkp0'/'gkp1'/'gkp0_2d'/'gkp1_2d' per mode",
                code="initial_invalid_item",
                op=None,
                allowed=_bosonic_sources,
            )
        if len(initial) != data.get("nmode"):
            raise CircuitV0Error(f"initial list length {len(initial)} != nmode {data.get('nmode')}")
    return LabCircuit(
        core=None,
        backend="bosonic",
        seed=seed,
        view=view,
        ui=ui,
        raw=data,
        detail=data.get("detail"),
    )


# -- execution moved to gaussian_backend.py / dispatch.py (ADR-0010) --
