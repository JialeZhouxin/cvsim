"""Gaussian backend result assembly for the Lab workbench.

Extracted from ``lab/ir.py`` to mirror ``fock_backend.py``/``bosonic_backend.py``:
per-representation result-assembly glue (meters + Wigner view) lives in its
own backend module. ir.py keeps the Gaussian execution dispatch (_execute);
this module owns only state→RunResult assembly. Imports shared types from
``cvsim.lab.ir`` (no circular import: ir.py does not module-import this file;
_execute uses a function-local import to call _build_result).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from cvsim.gaussian import (
    GaussianState,
    log_negativity,
    mean_photon,
    partial_trace,
    purity,
)
from cvsim.lab.ir import CircuitV0Error, RunResult, View
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
    return meters


def _build_result(state: GaussianState, view: View, measured: list[dict[str, Any]]) -> RunResult:
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
            meters={
                "purity": None,
                "mean_photon": 0.0,
                "mean_photon_per_mode": [],
                "log_negativity": None,
                "singular": False,
            },
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
