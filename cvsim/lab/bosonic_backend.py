"""Bosonic backend execution for the Lab workbench (B6).

Extracted from ``lab/ir.py``. Bosonic run + Wigner/meters assembly. Results
are LabResult snapshots (ADR-0008) — the wigner slice and the
measured-outcome collector are shared knowledge in ``cvsim.lab.result``
(previously this module imported fock's private ``_fock_measured``
cross-package; the function is representation-agnostic and now lives at the
result layer).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from cvsim.bosonic import (
    BosonicCircuit,
    BosonicState,
)
from cvsim.bosonic import (
    mean_photon as bosonic_mean_photon,
)
from cvsim.bosonic import (
    purity as bosonic_purity,
)
from cvsim.lab.ir import CircuitV0Error, LabCircuit, View
from cvsim.lab.result import LabResult, _measured_from_results, _wigner_slice, check_meters
from cvsim.wigner import wigner_grid


def _bosonic_adaptive_n(state: BosonicState, n: int) -> int:
    """Adaptive Wigner grid size: many components → coarser grid.

    Bosonic GKP states carry K~O(10-100) Gaussian components; a full
    n=64 grid on each is O(seconds per point). Cap the grid for large K
    (same spirit as Fock F7 slowCutoff: bounded cost, documented error).
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
        meters: dict[str, Any] = {"purity": None, "mean_photon": 0.0, "mean_photon_per_mode": []}
        check_meters("bosonic", meters)
        return meters
    modes = range(state.nmode)
    mean_list = [float(bosonic_mean_photon(state, i)) for i in modes]
    try:
        pur = float(bosonic_purity(state))
    except (ValueError, FloatingPointError, np.linalg.LinAlgError):
        pur = None
    meters = {
        "purity": pur,
        "mean_photon": float(sum(mean_list)),
        "mean_photon_per_mode": mean_list,
    }
    check_meters("bosonic", meters)
    return meters


def _bosonic_wigner_payload(state: BosonicState, view: View) -> dict[str, Any] | None:
    """Wigner payload for a step state (view.wigner_mode reduced single-mode)."""
    if state.nmode == 0:
        return None
    wmode = view.wigner_mode
    if wmode >= state.nmode:
        return None
    w = _bosonic_single_wigner(state, wmode, view)
    return _wigner_slice(w)


def run_bosonic_circuit(
    circuit: LabCircuit,
    rng: np.random.Generator | None = None,
    *,
    steps: bool = False,
    sampled: bool = False,
) -> LabResult:
    """Bosonic /run + /sample shared path: from_ir → compile → run(rng).

    Deterministic per circuit when rng is a seeded Generator (B6 aligns Fock
    F7: seed field drives reproducibility). ``steps=True`` (detail="steps")
    adds per-break-point intermediate snapshots for the GUI evolution view;
    ``sampled=True`` (/sample path) carries the seed + sampled flag in the
    LabResult contract instead of the server patching the payload dict.
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
    measured = _measured_from_results(circuit.raw, results)
    wmode = circuit.view.wigner_mode
    if state.nmode > 0 and wmode >= state.nmode:
        raise CircuitV0Error(f"view.wigner_mode {wmode} out of range (nmode={state.nmode})")
    wigner = None
    if state.nmode > 0:
        wigner = _bosonic_single_wigner(state, wmode, circuit.view)
    extensions: dict[str, Any] = {"dist": {"mode": wmode, "probs": None}}
    if steps:
        extensions["steps"] = [
            {
                "step": i,
                "op": op_name,
                "nmode": s.nmode,
                "meters": _bosonic_meters(s),
                "wigner": _bosonic_wigner_payload(s, circuit.view),
            }
            for i, (op_name, s) in enumerate(raw_steps)
        ]
    return LabResult(
        backend="bosonic",
        nmode=state.nmode,
        wigner=_wigner_slice(wigner),
        meters=_bosonic_meters(state),
        measured=measured,
        seed=circuit.seed if sampled else None,
        sampled=sampled,
        extensions=extensions,
    )
