"""Fock backend execution for the Lab workbench (F7).

Extracted from ``lab/ir.py`` to keep ir.py focused on the Gaussian path +
schema. Pure Fock run/sample/batch + meters/wigner/joint/leakage assembly.
Imports shared types/helpers from ``cvsim.lab.ir`` (no circular import: ir.py
does not import this module).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from cvsim.fock import (
    FockCircuit,
    FockDensity,
    FockState,
    pnrd_probs,
)
from cvsim.fock import (
    mean_photon as fock_mean_photon,
)
from cvsim.fock import (
    partial_trace as fock_partial_trace,
)
from cvsim.lab.ir import SCHEMA, CircuitV0Error, LabCircuit, View
from cvsim.wigner import wigner_grid

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
    if any(n.get("op", "").startswith("measure_") for n in raw.get("ops", [])):
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
        raise CircuitV0Error(f"view.wigner_mode {mode} out of range (nmode={state.nmode})")
    try:
        keep = fock_partial_trace(state, keep=[mode])
        max_c = max(state.amps.shape) if isinstance(state, FockState) else state.cutoff
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
        out.append({"op": node["op"], "mode": node["modes"][0], "name": name, "outcome": val})
    return out


def run_fock_circuit(circuit: LabCircuit, rng: np.random.Generator | None = None) -> dict[str, Any]:
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
        raise CircuitV0Error(f"view.wigner_mode {dist_mode} out of range (nmode={state.nmode})")
    probs = _fock_mode_probs(state, dist_mode)
    joint = _fock_joint(state, circuit.view, measured)
    mean_list = [_fock_mean_photon(state, i) for i in range(state.nmode)]
    cutoffs = (
        list(state.amps.shape) if isinstance(state, FockState) else [state.cutoff] * state.nmode
    )
    return {
        "schema": SCHEMA,
        "backend": "fock",
        "nmode": state.nmode,
        "cutoffs": cutoffs,
        "wigner": (
            {"x": wigner[0][0].tolist(), "p": wigner[1][:, 0].tolist(), "W": wigner[2].tolist()}
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


def batch_fock_circuit(circuit: LabCircuit, shots: int, seed: int) -> dict[str, Any]:
    """Fock /batch: PNR batch sampling vs the exact distribution.

    No measurement nodes: multinomial draw on the selected view (joint
    grid when view.joint_modes is set, else the wigner_mode marginal) —
    same draw ``pnr_sample_batch`` performs. Measurement nodes: per-shot
    condition-chain runs, outcome-vector histogram (honest, unoptimized).
    """
    rng = np.random.default_rng(seed)
    fc = FockCircuit.from_ir(circuit.raw)
    has_measure = any(n.get("op", "").startswith("measure_") for n in circuit.raw.get("ops", []))
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
            "backend": "fock",
            "shots": shots,
            "seed": seed,
            "measured_names": names,
            "counts": counts,
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
            raise CircuitV0Error(f"batch: joint modes {jm} unsupported on this state") from None
        flat = g.ravel()
        idx = rng.choice(flat.size, size=shots, p=flat)
        return {
            "backend": "fock",
            "shots": shots,
            "seed": seed,
            "modes": list(jm),
            "shape": list(g.shape),
            "counts": np.bincount(idx, minlength=flat.size).tolist(),
        }
    mode = circuit.view.wigner_mode
    if mode >= state.nmode:
        raise CircuitV0Error(f"view.wigner_mode {mode} out of range (nmode={state.nmode})")
    p = _fock_mode_probs(state, mode)
    idx = rng.choice(p.size, size=shots, p=p)
    return {
        "backend": "fock",
        "shots": shots,
        "seed": seed,
        "modes": [mode],
        "shape": [int(p.size)],
        "counts": np.bincount(idx, minlength=p.size).tolist(),
    }
