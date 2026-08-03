"""Thin FastAPI backend for the Gaussian Lab.

Import boundary (vision §6.2): only ``cvsim.lab`` (which itself only imports
``cvsim.gaussian`` public ``__all__`` + ``cvsim.wigner``). No private imports.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException

from cvsim.lab import SCHEMA, CircuitV0Error, RunResult, load_circuit, run_circuit

app = FastAPI(title="cvsim Gaussian Lab", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    from importlib.metadata import PackageNotFoundError, version

    try:
        cvsim_version = version("cvsim")
    except PackageNotFoundError:
        cvsim_version = "unknown"
    return {"status": "ok", "schema": SCHEMA, "cvsim": cvsim_version}


def _payload(result: RunResult) -> dict[str, Any]:
    X, P, W = result.wigner
    return {
        "schema": SCHEMA,
        "nmode": result.nmode,
        "rbar": result.rbar.tolist(),
        "V": result.V.tolist(),
        "wigner": {
            "x": X[0].tolist(),
            "p": P[:, 0].tolist(),
            "W": W.tolist(),
        },
        "meters": result.meters,
        "measured": result.measured,
    }


@app.post("/run")
def run(body: dict[str, Any]) -> dict[str, Any]:
    try:
        circuit = load_circuit(body)
        result = run_circuit(circuit)
    except CircuitV0Error as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return _payload(result)
