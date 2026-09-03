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

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cvsim.bosonic.ir import validate_ir as validate_bosonic_ir
from cvsim.fock.ir import validate_ir as validate_fock_ir
from cvsim.gaussian import (
    GaussianCircuit,
    GaussianState,
    heterodyne_condition,
    heterodyne_mean,
    heterodyne_sample_and_condition,
    homodyne_condition,
    homodyne_mean,
    homodyne_sample_and_condition,
)
from cvsim.gaussian.ir import SCHEMA as SCHEMA
from cvsim.gaussian.ir import CircuitV1, validate_ir

#: Bosonic backend op whitelist (B6, same-shell third backend). Mirrors the
#: F7 unlock: the Bosonic builder exposes the full gate/channel/measure set
#: including cz/cx/interferometer/gaussian_channel/measure_threshold — valid
#: core ops not in the Gaussian whitelist, unlocked wholesale for the new
#: backend (no historical v0 UI restriction to honor).
BOSONIC_WHITELIST = frozenset(
    {
        "squeeze",
        "displace",
        "phase",
        "fourier",
        "beamsplitter",
        "two_mode_squeeze",
        "mach_zehnder",
        "cz",
        "cx",
        "interferometer",
        "loss",
        "amplifier",
        "phase_noise",
        "gaussian_channel",
        "measure_homodyne",
        "measure_heterodyne",
        "measure_threshold",
    }
)
SCHEMA_V0 = "circuit_v0"

#: Lab op whitelist (lab vision §4 + L4/L5 amendments). v1 files may carry
#: core-only ops (cz/cx/interferometer/phase_noise/gaussian_channel/
#: mach_zehnder); those are valid IR but not unlocked in the Lab UI — the
#: Lab loader rejects them (whitelist is a UI concept, ADR-0003 #3).
LAB_WHITELIST = frozenset(
    {
        "displace",
        "phase",
        "squeeze",
        "fourier",
        "loss",
        "amplifier",
        "beamsplitter",
        "two_mode_squeeze",
        "mz",
        "measure_homodyne",
        "measure_heterodyne",
    }
)
#: Fock backend op whitelist (vision-gaussian-lab-ui §4.7, F7). Core Fock IR
#: also carries interferometer/apply_unitary/apply_kraus — valid IR, not
#: unlocked in the Fock Lab UI (matrix editor deferred, anti-whitelist creed).
FOCK_WHITELIST = frozenset(
    {
        "displace",
        "phase",
        "squeeze",
        "kerr",
        "beamsplitter",
        "two_mode_squeeze",
        "mach_zehnder",
        "cz",
        "cx",
        "loss",
        "amplifier",
        "phase_noise",
        "measure_pnr",
        "measure_homodyne",
        "measure_heterodyne",
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
    {"displace", "phase", "squeeze", "fourier", "loss", "amplifier", "homodyne", "heterodyne"}
)
TWO_MODE_V0 = frozenset({"beamsplitter", "two_mode_squeeze", "mz"})
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
    """Invalid circuit payload (v0 or v1); message is UI-safe."""


@dataclass
class View:
    wigner_mode: int = 0
    lim: float = 5.0
    n: int = 64
    joint_modes: list[int] | None = None  # Fock: 2-mode joint heatmap modes


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
                raise CircuitV0Error(f"{where}: source op must be first (state already exists)")
            if op == "vacuum":
                nm = params.get("nmode", 1)
                if not isinstance(nm, int) or isinstance(nm, bool) or nm < 1:
                    raise CircuitV0Error(f"nodes[{i}]: vacuum nmode must be an int >= 1")
                nmode += nm
            else:
                src_node: dict[str, Any] = {}
                if "id" in rn:
                    src_node["id"] = rn["id"]  # scan/UI reference the source node
                if op == "coherent":
                    alpha = _as_complex(params.get("alpha"), where)
                    src_node.update(
                        {
                            "op": "displace",
                            "modes": [nmode],
                            "params": {"alpha": [alpha.real, alpha.imag]},
                        }
                    )
                    nmode += 1
                else:  # tmsv
                    r = _num(params.get("r"), where, "r")
                    src_node.update(
                        {"op": "two_mode_squeeze", "modes": [nmode, nmode + 1], "params": {"r": r}}
                    )
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
                    raise CircuitV0Error(f"{where}: op {op!r} requires 'modes' of length 2")
                modes = [_as_pos_int(m, f"{where}.modes") for m in rn["modes"]]
            else:
                raise CircuitV0Error(
                    f"{where}: unknown op {op!r}; whitelist: "
                    f"{sorted(SOURCE_V0 | SINGLE_MODE_V0 | TWO_MODE_V0)}"
                )
            node: dict[str, Any] = {
                "op": V0_TO_V1_OP.get(op, op),
                "modes": modes,
                "params": dict(params),
            }
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
    jm = raw.get("joint_modes")
    if jm is not None and (
        not isinstance(jm, list)
        or len(jm) != 2
        or jm[0] == jm[1]
        or not all(isinstance(m, int) and not isinstance(m, bool) and m >= 0 for m in jm)
    ):
        raise CircuitV0Error("view.joint_modes must be a list of two distinct non-negative ints")
    return View(
        wigner_mode=wigner_mode,
        lim=float(lim),
        n=n,
        joint_modes=None if jm is None else list(jm),
    )


def load_circuit(data: dict[str, Any]) -> LabCircuit:
    """Load + validate a circuit payload: v1 native, v0 via :func:`translate_v0`.

    Routes by ``backend`` (default ``gaussian`` — old files unchanged): the
    Fock path validates against ``cvsim.fock.ir`` + FOCK_WHITELIST and keeps
    the raw dict; the Gaussian path enforces LAB_WHITELIST as before.
    """
    if not isinstance(data, dict):
        raise CircuitV0Error("payload must be a JSON object")
    if data.get("schema") == SCHEMA_V0:
        data = translate_v0(data)
    elif data.get("schema") != SCHEMA:
        raise CircuitV0Error(
            f"unsupported schema {data.get('schema')!r}; expected {SCHEMA!r} or {SCHEMA_V0!r}"
        )
    backend = data.get("backend", "gaussian")
    if backend not in ("gaussian", "fock", "bosonic"):
        raise CircuitV0Error(f"backend must be 'gaussian', 'fock' or 'bosonic', got {backend!r}")
    view = _parse_view(data.get("view", {}))
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
            raise CircuitV0Error(
                f"ops[{node.id or '?'}]: op {node.op!r} not in Lab whitelist: "
                f"{sorted(LAB_WHITELIST)}"
            )
    return LabCircuit(core=core, seed=seed, view=view, ui=ui, raw=data)


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
            raise CircuitV0Error(
                f"ops[{nid or '?'}]: op {op!r} not in Fock Lab whitelist: {sorted(FOCK_WHITELIST)}"
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
            raise CircuitV0Error(
                f"ops[{nid or '?'}]: op {op!r} not in Bosonic Lab "
                f"whitelist: {sorted(BOSONIC_WHITELIST)}"
            )
    try:
        validate_bosonic_ir(data)
    except ValueError as e:
        raise CircuitV0Error(str(e)) from e
    initial = data.get("initial")
    if initial is not None:
        if not isinstance(initial, list) or not all(
            item is None or item in ("gkp0", "gkp1", "gkp0_2d", "gkp1_2d")
            for item in initial
        ):
            # 整数项 = Fock 语义的 initial 跨到了 bosonic（GUI 切换 bug 的典型
            # 现场），给出可诊断的提示而不是让用户猜白名单。
            if isinstance(initial, list) and all(
                isinstance(item, int) and not isinstance(item, bool)
                for item in initial
            ):
                raise CircuitV0Error(
                    "initial looks like Fock photon numbers (ints) but backend is "
                    "'bosonic': bosonic takes GKP source names per mode "
                    "(null/'gkp0'/'gkp1'/'gkp0_2d'/'gkp1_2d')"
                )
            raise CircuitV0Error(
                "initial must be a list of null/'gkp0'/'gkp1'/'gkp0_2d'/'gkp1_2d' per mode"
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
    )


# -- execution --------------------------------------------------------------


def _apply_measure(
    op_name: str,
    state: GaussianState,
    phys_modes: tuple[int, ...],
    logical_mode: int,
    fixed: dict[str, Any],
    where: str,
    *,
    rng: np.random.Generator | None = None,
) -> tuple[GaussianState, dict[str, Any]]:
    """Apply one measurement op (Lab break-point segment). Returns (new_state, entry).

    ``rng is None`` → mean path (deterministic, uses homodyne/heterodyne_mean);
    ``rng`` given → true sampling. Semantics match the pre-unify ``_apply``:
    homodyne removes the measured mode; heterodyne does not (mirrors
    ``gaussian/compile.py:_run_op`` which also skips remove_mode for heterodyne).
    threshold is rejected (Q6=C: Gaussian Lab never supported it).
    """
    outcome: float | complex
    if op_name == "measure_homodyne":
        phi = _num(fixed.get("phi", 0.0), where, "phi")
        if rng is None:
            outcome = homodyne_mean(state, phys_modes[0], phi)
            st = homodyne_condition(state, phys_modes[0], phi, outcome)
        else:
            outcome, st = homodyne_sample_and_condition(state, phys_modes[0], phi, rng=rng)
        return st.remove_mode(phys_modes[0]), {
            "op": "measure_homodyne",
            "mode": logical_mode,
            "phi": phi,
            "outcome": outcome,
        }
    if op_name == "measure_heterodyne":
        if rng is None:
            outcome = heterodyne_mean(state, phys_modes[0])
            st = heterodyne_condition(state, phys_modes[0], outcome)
        else:
            outcome, st = heterodyne_sample_and_condition(state, phys_modes[0], rng=rng)
        return st, {
            "op": "measure_heterodyne",
            "mode": logical_mode,
            "outcome": [outcome.real, outcome.imag],
        }
    raise CircuitV0Error(f"{where}: unsupported measurement op {op_name!r} in Lab")


def _execute(circuit: LabCircuit, *, rng: np.random.Generator | None = None) -> RunResult:
    """Shared execution core: ordered ops → final GaussianState + result.

    Non-measurement ops are delegated to ``GaussianCircuit.from_ir().compile()``
    merged segments (``_apply_merged``) — the Lab no longer keeps its own
    13-branch op dispatch. Measurement break-point segments run via Lab's own
    ``_apply_measure`` to preserve the mean/sample path split + ``measured``
    entry contract (op/mode/phi/outcome).

    ``rng=None`` → mean path (/run); ``rng`` given → sample every measurement.
    Mode-removal mapping is handled by ``compile_segments`` (circuit_common);
    Lab only tracks logical mode indices (from IR nodes) for ``measured``
    entries, since segment ops already carry physical coords.
    """
    try:
        compiled = GaussianCircuit.from_ir(circuit.raw).compile()
    except ValueError as e:
        # compile_segments raises plain ValueError on mode-reference errors
        # (e.g. displace after measured mode); Lab error surface is
        # CircuitV0Error (server 422 contract).
        raise CircuitV0Error(str(e)) from e
    state = compiled._init_state()
    measured: list[dict[str, Any]] = []
    # IR node pointer aligned with segment order: merged segments consume
    # len(ops) IR nodes, break-point op segments consume 1.
    core = circuit.core
    assert core is not None  # execution path is Gaussian (Fock uses run_circuit)
    ir_nodes = core.ops
    ir_idx = 0
    run_results: dict[str, float] = {}  # ParamRef sources for feedforward ops
    for seg in compiled._segments:
        if seg[0] == "merged":
            _, nmode, ops = seg
            state = compiled._apply_merged(ops, nmode, {}, state)
            ir_idx += len(ops)
            continue
        op_name, phys_modes, fixed, pnames, refs = seg[1]
        node = ir_nodes[ir_idx]
        ir_idx += 1
        if op_name in MEASUREMENT_OPS:
            # Measurements: Lab owns the path (mean/sample split + entry).
            state, entry = _apply_measure(
                op_name,
                state,
                phys_modes,
                node.modes[0],
                fixed,
                f"ops[{node.id or '?'}]",
                rng=rng,
            )
            # feedforward: record outcome under the measurement's name for
            # later ParamRef resolution by _run_op.
            name = fixed.get("name")
            if name is not None:
                run_results[name] = entry["outcome"]
            measured.append(entry)
        else:
            # Channels (loss/amplifier/phase_noise/gaussian_channel) and any
            # ParamRef-bearing op: delegate to the compiled dispatcher. No
            # measured entry; values already bound (no symbolic params here).
            # Lab-specific guard: amplifier with modes=[] means all modes in
            # core semantics, but the Lab workbench always emits an explicit
            # mode — reject instead of 500 (preserves pre-unify behavior).
            if op_name == "amplifier" and not phys_modes:
                raise CircuitV0Error(
                    f"ops[{node.id or '?'}]: amplifier requires an explicit mode in Lab"
                )
            # Lab requires explicit numeric params (no core defaults): the
            # pre-unify _apply validated each param via _num; core from_ir
            # silently fills OpMeta defaults, so Lab re-checks presence on
            # the original IR node params for the channel ops that have them.
            if op_name in _LAB_REQUIRED_PARAMS:
                for pname in _LAB_REQUIRED_PARAMS[op_name]:
                    if pname not in node.params:
                        raise CircuitV0Error(f"ops[{node.id or '?'}]: {pname} must be a number")
            state, run_results = compiled._run_op(
                seg[1],
                state,
                run_results,
                {},
                rng=rng,
            )
    from cvsim.lab.gaussian_backend import _build_result  # D1-A: local import

    return _build_result(state, circuit.view, measured)


def run_circuit(circuit: LabCircuit) -> RunResult:
    """Compile + run (mean path): ordered ops → result. Pure, no RNG."""
    return _execute(circuit, rng=None)


def sample_circuit(circuit: LabCircuit, rng: np.random.Generator) -> RunResult:
    """Compile + run with true sampling of every measurement node, in node
    order; each measurement conditions the state for the next one."""
    return _execute(circuit, rng=rng)
