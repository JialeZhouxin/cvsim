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
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from cvsim.gaussian import (
    GaussianCircuit,
    GaussianState,
    heterodyne_condition,
    heterodyne_mean,
    heterodyne_sample_and_condition,
    homodyne_condition,
    homodyne_mean,
    homodyne_sample_and_condition,
    log_negativity,
    mean_photon,
    partial_trace,
    purity,
)
from cvsim.gaussian.ir import SCHEMA, CircuitV1, validate_ir
from cvsim.fock import (
    FockCircuit,
    FockDensity,
    FockState,
    mean_photon as fock_mean_photon,
    partial_trace as fock_partial_trace,
    pnrd_probs,
)
from cvsim.fock.ir import validate_ir as validate_fock_ir
from cvsim.bosonic import (
    BosonicCircuit,
    BosonicState,
    mean_photon as bosonic_mean_photon,
    pure_fidelity,
    purity as bosonic_purity,
)
from cvsim.bosonic.ir import validate_ir as validate_bosonic_ir
from cvsim.wigner import wigner_grid

#: Bosonic backend op whitelist (B6, same-shell third backend). Mirrors the
#: F7 unlock: the Bosonic builder exposes the full gate/channel/measure set
#: including cz/cx/interferometer/gaussian_channel/measure_threshold — valid
#: core ops not in the Gaussian whitelist, unlocked wholesale for the new
#: backend (no historical v0 UI restriction to honor).
BOSONIC_WHITELIST = frozenset(
    {
        "squeeze", "displace", "phase", "fourier", "beamsplitter",
        "two_mode_squeeze", "mach_zehnder", "cz", "cx", "interferometer",
        "loss", "amplifier", "phase_noise", "gaussian_channel",
        "measure_homodyne", "measure_heterodyne", "measure_threshold",
    }
)
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
#: Fock backend op whitelist (vision-gaussian-lab-ui §4.7, F7). Core Fock IR
#: also carries interferometer/apply_unitary/apply_kraus — valid IR, not
#: unlocked in the Fock Lab UI (matrix editor deferred, anti-whitelist creed).
FOCK_WHITELIST = frozenset(
    {
        "displace", "phase", "squeeze", "kerr", "beamsplitter",
        "two_mode_squeeze", "mach_zehnder", "cz", "cx",
        "loss", "amplifier", "phase_noise",
        "measure_pnr", "measure_homodyne", "measure_heterodyne",
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
    jm = raw.get("joint_modes")
    if jm is not None and (
        not isinstance(jm, list)
        or len(jm) != 2
        or jm[0] == jm[1]
        or not all(isinstance(m, int) and not isinstance(m, bool) and m >= 0 for m in jm)
    ):
        raise CircuitV0Error(
            "view.joint_modes must be a list of two distinct non-negative ints"
        )
    return View(
        wigner_mode=wigner_mode, lim=float(lim), n=n,
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
            f"unsupported schema {data.get('schema')!r}; expected {SCHEMA!r} or "
            f"{SCHEMA_V0!r}"
        )
    backend = data.get("backend", "gaussian")
    if backend not in ("gaussian", "fock", "bosonic"):
        raise CircuitV0Error(
            f"backend must be 'gaussian', 'fock' or 'bosonic', got {backend!r}"
        )
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

def _load_fock(
    data: dict[str, Any], seed: int, view: View, ui: dict[str, Any]
) -> LabCircuit:
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
                f"ops[{nid or '?'}]: op {op!r} not in Fock Lab "
                f"whitelist: {sorted(FOCK_WHITELIST)}"
            )
    try:
        validate_fock_ir(data)
    except ValueError as e:
        raise CircuitV0Error(str(e)) from e
    initial = data.get("initial")
    if initial is not None and (
        not isinstance(initial, list)
        or not all(
            isinstance(n, int) and not isinstance(n, bool) and n >= 0
            for n in initial
        )
    ):
        raise CircuitV0Error("initial must be a list of non-negative ints")
    return LabCircuit(
        core=None, backend="fock", seed=seed, view=view, ui=ui,
        raw=data, initial=initial,
    )


def _load_bosonic(
    data: dict[str, Any], seed: int, view: View, ui: dict[str, Any]
) -> LabCircuit:
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
            item is None or item in ("gkp0", "gkp1") for item in initial
        ):
            raise CircuitV0Error(
                "initial must be a list of null/'gkp0'/'gkp1' per mode"
            )
        if len(initial) != data.get("nmode"):
            raise CircuitV0Error(
                f"initial list length {len(initial)} != nmode {data.get('nmode')}"
            )
    return LabCircuit(
        core=None, backend="bosonic", seed=seed, view=view, ui=ui,
        raw=data,
    )


# -- execution --------------------------------------------------------------

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
    if op_name == "measure_homodyne":
        phi = _num(fixed.get("phi", 0.0), where, "phi")
        if rng is None:
            outcome = homodyne_mean(state, phys_modes[0], phi)
            st = homodyne_condition(state, phys_modes[0], phi, outcome)
        else:
            outcome, st = homodyne_sample_and_condition(
                state, phys_modes[0], phi, rng=rng
            )
        return st.remove_mode(phys_modes[0]), {
            "op": "measure_homodyne", "mode": logical_mode, "phi": phi,
            "outcome": outcome,
        }
    if op_name == "measure_heterodyne":
        if rng is None:
            outcome = heterodyne_mean(state, phys_modes[0])
            st = heterodyne_condition(state, phys_modes[0], outcome)
        else:
            outcome, st = heterodyne_sample_and_condition(
                state, phys_modes[0], rng=rng
            )
        return st, {
            "op": "measure_heterodyne", "mode": logical_mode,
            "outcome": [outcome.real, outcome.imag],
        }
    raise CircuitV0Error(f"{where}: unsupported measurement op {op_name!r} in Lab")

def _execute(
    circuit: LabCircuit, *, rng: np.random.Generator | None = None
) -> RunResult:
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
    ir_nodes = circuit.core.ops
    ir_idx = 0
    run_results: dict[str, float] = {}  # ParamRef sources for feedforward ops
    for seg in compiled._segments:
        if seg[0] == 'merged':
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
                op_name, state, phys_modes, node.modes[0],
                fixed, f"ops[{node.id or '?'}]", rng=rng,
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
                        raise CircuitV0Error(
                            f"ops[{node.id or '?'}]: {pname} must be a number"
                        )
            state, run_results = compiled._run_op(
                seg[1], state, run_results, {}, rng=rng,
            )
    return _build_result(state, circuit.view, measured)


def run_circuit(circuit: LabCircuit) -> RunResult:
    """Compile + run (mean path): ordered ops → result. Pure, no RNG."""
    return _execute(circuit, rng=None)


def sample_circuit(circuit: LabCircuit, rng: np.random.Generator) -> RunResult:
    """Compile + run with true sampling of every measurement node, in node
    order; each measurement conditions the state for the next one."""
    return _execute(circuit, rng=rng)


# -- scan -------------------------------------------------------------------

def _safe_logneg(state: GaussianState, modes_A: list[int]) -> float | None:
    """E_N on the current state; None when undefined (singular etc.), never fabricated."""
    try:
        v = float(log_negativity(state, modes_A=modes_A))
        return v if math.isfinite(v) else None
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        return None

def _inject_symbolic_param(
    raw: dict[str, Any], node_id: str, param: str
) -> dict[str, Any]:
    """Return a deep copy of ``raw`` with ``node_id``'s ``param`` replaced by
    a symbolic ``{"$param": "sweep_x"}`` reference (ADR-0002 value binding).

    Lets ``scan_circuit`` compile once and bind per sweep point instead of
    rebuilding+recompiling the IR each time.
    """
    import copy
    out = copy.deepcopy(raw)
    for node in out.get("ops", []):
        if node.get("id") == node_id:
            node["params"][param] = {"$param": "sweep_x"}
            return out
    raise CircuitV0Error(f"sweep: unknown node_id {node_id!r}")  # pragma: no cover

def scan_circuit(circuit: LabCircuit, sweep: dict[str, Any]) -> dict[str, Any]:
    """F-LAB-SCAN: single-param sweep of one node's real-numeric param → E_N curve.

    Pure function (no RNG): same request → same response. The swept param is
    injected as a symbolic ``$param`` (ADR-0002): the circuit is compiled once,
    then each sweep point binds the value via ``compiled.run(sweep_x=x)`` — no
    per-point IR rebuild or recompile. Undefined (singular) points are ``None``
    (curve break, frontend skips). Measurement nodes anywhere → 422 (E_N is
    not defined on conditional states; honest rejection).
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

    # Compile once with the swept param as a symbolic $param; bind per point.
    swept_raw = _inject_symbolic_param(circuit.raw, node_id, param)
    compiled = GaussianCircuit.from_ir(swept_raw).compile()
    nmode = compiled.nmode
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
        st = compiled.run(sweep_x=float(x))  # type: ignore[no-untyped-call]
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

# -- Fock backend execution (F7) ---------------------------------------------

#: Cap on the higher-cutoff comparison tensor for the leakage estimate
#: (vision-fock §7 memory budget; honest null above it).
_LEAKAGE_DIM_CAP = 2_000_000

def _fock_mode_probs(state: FockState | FockDensity, mode: int) -> np.ndarray:
    """Single-mode photon-number marginal via public ``pnrd_probs``;
    m>2 states fall back to direct amplitude/diagonal marginalization
    (``partial_trace`` is documented dense m≤2)."""
    try:
        keep = fock_partial_trace(state, keep=[mode])
        return np.asarray(pnrd_probs(keep), dtype=float)
    except (IndexError, ValueError, NotImplementedError):
        if isinstance(state, FockState):
            p = np.abs(state.amps) ** 2
            axes = tuple(i for i in range(state.nmode) if i != mode)
            return np.asarray(p.sum(axis=axes), dtype=float)
        p = np.real(np.diag(state.rho)).reshape((state.cutoff,) * state.nmode)
        axes = tuple(i for i in range(state.nmode) if i != mode)
        return np.asarray(p.sum(axis=axes), dtype=float)

def _fock_mean_photon(state: FockState | FockDensity, mode: int) -> float:
    try:
        return float(fock_mean_photon(state, mode=mode))
    except IndexError:  # m>2: marginal × n (arithmetic on public pnrd_probs)
        p = _fock_mode_probs(state, mode)
        return float(np.sum(np.arange(p.size) * p))

def _fock_purity(state: FockState | FockDensity) -> float | None:
    if isinstance(state, FockState):
        return 1.0
    try:
        return float(np.trace(state.rho @ state.rho).real)
    except (ValueError, np.linalg.LinAlgError):
        return None

def _fock_leakage(raw: dict[str, Any], state: FockState | FockDensity) -> float | None:
    """Truncation leakage meter: analytic tail for factory states; otherwise
    a higher-cutoff re-run comparison (vision-fock §5 rule 1). Density
    (post-channel) and conditional states → honest None (never fabricated)."""
    if not isinstance(state, FockState):
        return None
    if state.tail is not None:
        return float(state.tail)
    cutoffs = list(state.amps.shape)
    cut2 = [min(2 * c, 60) for c in cutoffs]
    if cut2 == cutoffs:
        return None
    if int(np.prod(cut2)) > _LEAKAGE_DIM_CAP:
        return None
    if any(
        n.get("op", "").startswith("measure_") for n in raw.get("ops", [])
    ):
        return None
    try:
        fc2 = FockCircuit.from_ir({**raw, "cutoff": cut2})
        st2 = fc2.run()
        sl = tuple(slice(0, c) for c in cutoffs)
        return float(1.0 - np.sum(np.abs(st2.amps[sl]) ** 2))
    except (ValueError, AttributeError, np.linalg.LinAlgError):
        return None

def _fock_wigner(
    state: FockState | FockDensity, view: View
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Single-mode Wigner via partial_trace + wigner_grid (Fock branch).
    cutoff > 20 degrades the grid to N=48 (design §2.4 perf budget)."""
    mode = view.wigner_mode
    if mode >= state.nmode:
        raise CircuitV0Error(
            f"view.wigner_mode {mode} out of range (nmode={state.nmode})"
        )
    try:
        keep = fock_partial_trace(state, keep=[mode])
        max_c = (
            max(state.amps.shape)
            if isinstance(state, FockState)
            else state.cutoff
        )
        n = min(view.n, 48) if max_c > 20 else view.n
        return wigner_grid(keep, lim=view.lim, n=n)
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        return None  # singular conditional state: honest null

def _fock_joint(
    state: FockState | FockDensity, view: View, measured: list
) -> dict[str, Any] | None:
    """2-mode joint photon-number grid (≤30×30, design §2.3). null when no
    joint_modes / <2 modes / measurement collapse ambiguity."""
    jm = view.joint_modes
    if (
        not jm
        or len(jm) != 2
        or state.nmode < 2
        or jm[0] == jm[1]
        or measured
        or not all(0 <= m < state.nmode for m in jm)
    ):
        return None
    try:
        keep2 = fock_partial_trace(state, keep=list(jm))
        g = np.asarray(pnrd_probs(keep2), dtype=float)
        return {"modes": list(jm), "grid": g[:30, :30].tolist()}
    except (IndexError, ValueError, NotImplementedError, np.linalg.LinAlgError):
        return None

def _fock_measured(raw: dict[str, Any], results: dict) -> list[dict[str, Any]]:
    """Measurement outcomes in node order (name-keyed results dict → list)."""
    out: list[dict[str, Any]] = []
    for node in raw.get("ops", []):
        if not isinstance(node, dict) or not node.get("op", "").startswith("measure_"):
            continue
        params = node.get("params") or {}
        name = params.get("name")
        if name is None or name not in results:
            continue
        val = results[name]
        if isinstance(val, complex):
            val = [val.real, val.imag]
        elif isinstance(val, np.generic):
            val = val.item()
        out.append(
            {"op": node["op"], "mode": node["modes"][0],
             "name": name, "outcome": val}
        )
    return out

def run_fock_circuit(
    circuit: LabCircuit, rng: np.random.Generator | None = None
) -> dict[str, Any]:
    """Fock /run + /sample shared path: FockCircuit.from_ir → run(rng).

    Deterministic per circuit when rng is None (seed field, default 0);
    every measurement node conditions the state (FockCircuit semantics).
    """
    fc = FockCircuit.from_ir(circuit.raw)
    out = fc.run(rng=rng)
    if isinstance(out, tuple):
        state, results = out
    else:
        state, results = out, {}
    measured = _fock_measured(circuit.raw, results)
    wigner = _fock_wigner(state, circuit.view) if state.nmode > 0 else None
    dist_mode = circuit.view.wigner_mode
    if dist_mode >= state.nmode:
        raise CircuitV0Error(
            f"view.wigner_mode {dist_mode} out of range (nmode={state.nmode})"
        )
    probs = _fock_mode_probs(state, dist_mode)
    joint = _fock_joint(state, circuit.view, measured)
    mean_list = [_fock_mean_photon(state, i) for i in range(state.nmode)]
    cutoffs = (
        list(state.amps.shape)
        if isinstance(state, FockState)
        else [state.cutoff] * state.nmode
    )
    return {
        "schema": SCHEMA,
        "backend": "fock",
        "nmode": state.nmode,
        "cutoffs": cutoffs,
        "wigner": (
            {"x": wigner[0][0].tolist(), "p": wigner[1][:, 0].tolist(),
             "W": wigner[2].tolist()}
            if wigner is not None
            else None
        ),
        "dist": {"mode": dist_mode, "probs": probs.tolist()},
        "joint": joint,
        "meters": {
            "mean_photon": float(np.sum(mean_list)),
            "mean_photon_per_mode": mean_list,
            "purity": _fock_purity(state),
            "leakage": _fock_leakage(circuit.raw, state),
        },
        "measured": measured,
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


def batch_fock_circuit(
    circuit: LabCircuit, shots: int, seed: int
) -> dict[str, Any]:
    """Fock /batch: PNR batch sampling vs the exact distribution.

    No measurement nodes: multinomial draw on the selected view (joint
    grid when view.joint_modes is set, else the wigner_mode marginal) —
    same draw ``pnr_sample_batch`` performs. Measurement nodes: per-shot
    condition-chain runs, outcome-vector histogram (honest, unoptimized).
    """
    rng = np.random.default_rng(seed)
    fc = FockCircuit.from_ir(circuit.raw)
    has_measure = any(
        n.get("op", "").startswith("measure_")
        for n in circuit.raw.get("ops", [])
    )
    if has_measure:
        names = [
            (n.get("params") or {}).get("name")
            for n in circuit.raw.get("ops", [])
            if n.get("op", "").startswith("measure_")
        ]
        counts: dict[str, int] = {}
        for _ in range(shots):
            _, results = fc.run(rng=rng)
            key = str(tuple(results.get(n) for n in names))
            counts[key] = counts.get(key, 0) + 1
        return {
            "backend": "fock", "shots": shots, "seed": seed,
            "measured_names": names, "counts": counts,
        }
    state = fc.run()
    jm = circuit.view.joint_modes
    if (
        jm
        and len(jm) == 2
        and state.nmode >= 2
        and jm[0] != jm[1]
        and all(0 <= m < state.nmode for m in jm)
    ):
        try:
            keep2 = fock_partial_trace(state, keep=list(jm))
            g = np.asarray(pnrd_probs(keep2), dtype=float)[:30, :30]
        except (IndexError, ValueError, NotImplementedError, np.linalg.LinAlgError):
            raise CircuitV0Error(
                f"batch: joint modes {jm} unsupported on this state"
            ) from None
        flat = g.ravel()
        idx = rng.choice(flat.size, size=shots, p=flat)
        return {
            "backend": "fock", "shots": shots, "seed": seed,
            "modes": list(jm), "shape": list(g.shape),
            "counts": np.bincount(idx, minlength=flat.size).tolist(),
        }
    mode = circuit.view.wigner_mode
    if mode >= state.nmode:
        raise CircuitV0Error(
            f"view.wigner_mode {mode} out of range (nmode={state.nmode})"
        )
    p = _fock_mode_probs(state, mode)
    idx = rng.choice(p.size, size=shots, p=p)
    return {
        "backend": "fock", "shots": shots, "seed": seed,
        "modes": [mode], "shape": [int(p.size)],
        "counts": np.bincount(idx, minlength=p.size).tolist(),
    }
