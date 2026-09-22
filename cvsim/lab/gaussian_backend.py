"""Gaussian backend execution + result assembly for the Lab workbench.

Owns the full gaussian runner (ADR-0010 #3): ``run_gaussian_circuit`` =
``_execute`` (compile + segment loop + measurement break-points) +
``_build_result`` (meters + Wigner view → LabResult) — same shape as
``fock_backend`` / ``bosonic_backend``. Extracted from ``lab/ir.py``, which
keeps only load/translate/schema; the D1-A function-local import hack is
gone (ir.py no longer imports this module).
"""

from __future__ import annotations

from collections.abc import Callable
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
from cvsim.lab.ir import (
    _LAB_REQUIRED_PARAMS,
    MEASUREMENT_OPS,
    CircuitV0Error,
    LabCircuit,
    View,
    _num,
    check_wigner_mode,
)
from cvsim.lab.result import LabResult, _wigner_slice, check_meters
from cvsim.wigner import wigner_grid


def _meters(state: GaussianState, singular: bool) -> dict[str, Any]:
    """meters; purity/log_neg are undefined on singular conditional states
    (det V = 0) → None, never fabricated. mean_photon stays (computable;
    negative values shown honestly)."""
    m = state.nmode

    def safe(fn: Callable[[], Any]) -> Any:
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
    check_meters("gaussian", meters)
    return meters


def _build_result(state: GaussianState, view: View, measured: list[dict[str, Any]]) -> LabResult:
    """Assemble LabResult: Wigner view + meters. A singular conditional state
    (homodyne-conditioned mode, det(2V)=0) has no finite Wigner: report
    wigner=None + meters.singular instead of fabricating data. All modes
    measured away (nmode==0) → empty result, no Wigner, honest zero meters."""
    if state.nmode == 0:
        meters: dict[str, Any] = {
            "purity": None,
            "mean_photon": 0.0,
            "mean_photon_per_mode": [],
            "log_negativity": None,
            "singular": False,
        }
        check_meters("gaussian", meters)
        return LabResult(
            backend="gaussian",
            nmode=0,
            wigner=None,
            meters=meters,
            measured=measured,
            extensions={"rbar": np.zeros(0).tolist(), "V": np.zeros((0, 0)).tolist()},
        )
    check_wigner_mode(view.wigner_mode, state.nmode)
    wigner: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    singular = False
    try:
        keep = partial_trace(state, keep=[view.wigner_mode])
        X, P, W = wigner_grid(keep, lim=view.lim, n=view.n)
        wigner = (X, P, W)
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):  # singular view
        singular = True
    return LabResult(
        backend="gaussian",
        nmode=state.nmode,
        wigner=_wigner_slice(wigner),
        meters=_meters(state, singular),
        measured=measured,
        extensions={"rbar": state.rbar.tolist(), "V": state.V.tolist()},
    )


# -- execution (ADR-0010 #3: moved from lab/ir.py, D1-A hack retired) --------

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


def _execute(circuit: LabCircuit, *, rng: np.random.Generator | None = None) -> LabResult:
    """Shared execution core: ordered ops → final GaussianState + result.

    Non-measurement ops are delegated to ``GaussianCircuit.from_ir().compile()``
    merged segments — the Lab no longer keeps its own 13-branch op dispatch.
    Measurement break-point segments run via Lab's own ``_apply_measure`` to
    preserve the mean/sample path split + ``measured`` entry contract
    (op/mode/phi/outcome).

    ``rng=None`` → mean path (/run); ``rng`` given → sample every measurement.
    Mode-removal mapping is handled by ``compile_segments`` (circuit_common);
    Lab only tracks logical mode indices (from IR nodes) for ``measured``
    entries, since segment ops already carry physical coords.

    The traversal itself lives in ``CompiledCircuit.run_breaks``: Lab supplies
    the break-point callback and receives the IR-node index, so it never reads
    the compiled object's segment layout (CONTEXT.md: 不暴露段布局).
    """
    try:
        compiled = GaussianCircuit.from_ir(circuit.raw).compile()
    except ValueError as e:
        # compile_segments raises plain ValueError on mode-reference errors
        # (e.g. displace after measured mode); Lab error surface is
        # CircuitV0Error (server 422 contract).
        raise CircuitV0Error(str(e)) from e
    measured: list[dict[str, Any]] = []
    core = circuit.core
    assert core is not None  # execution path is Gaussian (Fock uses run_fock_circuit)
    ir_nodes = core.ops

    def on_break(
        op: tuple[Any, ...],
        state: GaussianState,
        run_results: dict[str, float],
        ir_idx: int,
    ) -> tuple[GaussianState, dict[str, float]]:
        """One break-point op: Lab's measurement path or the core dispatcher."""
        op_name, phys_modes, fixed, _pnames, _refs = op
        node = ir_nodes[ir_idx]
        where = f"ops[{node.id or '?'}]"
        if op_name in MEASUREMENT_OPS:
            # Measurements: Lab owns the path (mean/sample split + entry).
            state, entry = _apply_measure(
                op_name,
                state,
                phys_modes,
                node.modes[0],
                fixed,
                where,
                rng=rng,
            )
            # feedforward: record outcome under the measurement's name for
            # later ParamRef resolution by run_op.
            name = fixed.get("name")
            if name is not None:
                run_results[name] = entry["outcome"]
            measured.append(entry)
            return state, run_results
        # Channels (loss/amplifier/phase_noise/gaussian_channel) and any
        # ParamRef-bearing op: delegate to the compiled dispatcher. No
        # measured entry; values already bound (no symbolic params here).
        # Lab-specific guard: amplifier with modes=[] means all modes in
        # core semantics, but the Lab workbench always emits an explicit
        # mode — reject instead of 500 (preserves pre-unify behavior).
        if op_name == "amplifier" and not phys_modes:
            raise CircuitV0Error(f"{where}: amplifier requires an explicit mode in Lab")
        # Lab requires explicit numeric params (no core defaults): the
        # pre-unify _apply validated each param via _num; core from_ir
        # silently fills OpMeta defaults, so Lab re-checks presence on
        # the original IR node params for the channel ops that have them.
        if op_name in _LAB_REQUIRED_PARAMS:
            for pname in _LAB_REQUIRED_PARAMS[op_name]:
                if pname not in node.params:
                    raise CircuitV0Error(f"{where}: {pname} must be a number")
        state, run_results = compiled.run_op(op, state, run_results, rng=rng)
        return state, run_results

    state, _ = compiled.run_breaks(on_break)
    return _build_result(state, circuit.view, measured)


def run_gaussian_circuit(
    circuit: LabCircuit,
    rng: np.random.Generator | None = None,
    *,
    sampled: bool = False,
    steps: bool = False,
) -> LabResult:
    """Gaussian runner (ADR-0010 #1 shape alignment with fock/bosonic).

    ``rng=None`` → mean path (/run); ``rng`` given → sample every measurement.
    ``sampled=True`` (sample path) sets seed + sampled on the LabResult
    contract — regardless of rng, so a caller passing an explicit Generator
    still gets the sampled contract keys (L3 tests drive it this way).
    ``steps`` is bosonic-only (per-break-point snapshots) — accepted and
    ignored so the dispatch registry needs no per-backend signature branches.
    """
    result = _execute(circuit, rng=rng)
    if sampled:
        result.seed = circuit.seed
        result.sampled = True
    return result
