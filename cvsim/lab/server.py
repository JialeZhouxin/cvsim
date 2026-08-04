"""Thin FastAPI backend for the Gaussian Lab.

Import boundary (vision §6.2): only ``cvsim.lab`` (which itself only imports
``cvsim.gaussian`` public ``__all__`` + ``cvsim.wigner``). No private imports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from cvsim.lab import (
    SCHEMA,
    CircuitV0Error,
    RunResult,
    load_circuit,
    run_circuit,
    sample_circuit,
    scan_circuit,
)

app = FastAPI(title="cvsim Gaussian Lab", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    from importlib.metadata import PackageNotFoundError, version

    try:
        cvsim_version = version("cvsim")
    except PackageNotFoundError:
        cvsim_version = "unknown"
    return {"status": "ok", "schema": SCHEMA, "cvsim": cvsim_version}


def _payload(
    result: RunResult, *, seed: int | None = None, sampled: bool = False
) -> dict[str, Any]:
    if result.wigner is None:
        wigner: Any = None  # singular conditional state: no finite Wigner
    else:
        X, P, W = result.wigner
        wigner = {
            "x": X[0].tolist(),
            "p": P[:, 0].tolist(),
            "W": W.tolist(),
        }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "nmode": result.nmode,
        "rbar": result.rbar.tolist(),
        "V": result.V.tolist(),
        "wigner": wigner,
        "meters": result.meters,
        "measured": result.measured,
    }
    if seed is not None:
        payload["seed"] = seed
    if sampled:
        payload["sampled"] = True
    return payload


@app.post("/run")
def run(body: dict[str, Any]) -> dict[str, Any]:
    try:
        circuit = load_circuit(body)
        result = run_circuit(circuit)
    except (CircuitV0Error, ValueError) as e:
        # ValueError covers library-side guards (loss T range, wigner_grid,
        # np.linalg.LinAlgError is a ValueError subclass) → user-error 422.
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _payload(result)


@app.post("/sample")
def sample(body: dict[str, Any]) -> dict[str, Any]:
    """Measure once: explicit seed → true sampling of all measurement nodes."""
    try:
        circuit = load_circuit(body)
        result = sample_circuit(circuit, np.random.default_rng(circuit.seed))
    except (CircuitV0Error, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _payload(result, seed=circuit.seed, sampled=True)


@app.post("/scan")
def scan(body: dict[str, Any]) -> dict[str, Any]:
    """F-LAB-SCAN: single-param sweep → E_N curve (pure, no RNG).

    Body = circuit_v0 + ``sweep`` segment (UI-session config, not part of the
    circuit_v0 schema). All domain errors → 422 with a UI-safe detail.
    (Note: LinAlgError is NOT a ValueError subclass — always list it explicitly
    in except tuples.)
    """
    try:
        circuit = load_circuit(body)
        sweep = body.get("sweep")
        if not isinstance(sweep, dict):
            raise CircuitV0Error("sweep must be an object")
        return scan_circuit(circuit, sweep)
    except (CircuitV0Error, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


_STATIC_DIR = Path(__file__).resolve().parent / "static"
if not _STATIC_DIR.is_dir():
    raise RuntimeError(f"Missing packaged lab assets: {_STATIC_DIR}")
# Mount last so API routes keep precedence (FastAPI prefix swallowing).
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
