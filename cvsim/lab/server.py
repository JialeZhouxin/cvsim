"""Thin FastAPI backend for the Gaussian/Fock Lab (dual backend, F7).

Import boundary (vision §6.2): only ``cvsim.lab`` (which itself only imports
``cvsim.gaussian`` public ``__all__`` + ``cvsim.wigner`` + ``cvsim.fock``
public). No private imports.
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
    fidelity_sweep,
    load_circuit,
    run_circuit,
    sample_circuit,
    scan_circuit,
)
from cvsim.lab.bosonic_backend import run_bosonic_circuit
from cvsim.lab.fock_backend import batch_fock_circuit, run_fock_circuit

app = FastAPI(title="cvsim Lab (Gaussian/Fock)", version="0.2.0")


def _whitelist_label(allowed: list[str]) -> str:
    """Whitelist label from the rejected-with set (single template input):
    'Fock Lab' / 'Bosonic Lab'; anything else = the gaussian legacy 'Lab'.
    """
    from cvsim.lab.schema import BOSONIC_WHITELIST, FOCK_WHITELIST

    allowed_set = set(allowed)
    if allowed_set == set(FOCK_WHITELIST):
        return "Fock Lab"
    if allowed_set == set(BOSONIC_WHITELIST):
        return "Bosonic Lab"
    return "Lab"


@app.get("/health")
def health() -> dict[str, Any]:
    from importlib.metadata import PackageNotFoundError, version

    try:
        cvsim_version = version("cvsim")
    except PackageNotFoundError:
        cvsim_version = "unknown"
    return {"status": "ok", "schema": SCHEMA, "cvsim": cvsim_version}

@app.get("/schema")
def schema() -> dict[str, Any]:
    """Schema snapshot (single-source ticket 2): core ``ir_schema()`` data
    assembled with the Lab whitelists + extension-field boundaries.

    Static per process (same package, same process — Q7: no version
    negotiation); consumers fetch once at startup (ticket 3+).
    """
    from cvsim.lab.schema import assemble_schema

    return assemble_schema()


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


def _422(e: Exception) -> HTTPException:
    """422 from a domain error: structured whitelist errors render the single
    shared message template from their {code, where, op, allowed} data (Q8)
    — byte-identical to the ir.py golden text (golden 422 tests lock it);
    everything else keeps the original str(e) text verbatim."""
    structured = getattr(e, "structured", None)
    if structured is not None:
        code = structured["code"]
        if code == "op_not_whitelisted":
            detail = (
                f"{structured['where']}: op {structured['op']!r} not in "
                f"{_whitelist_label(structured['allowed'])} whitelist: "
                f"{structured['allowed']}"
            )
            return HTTPException(status_code=422, detail=detail)
    return HTTPException(status_code=422, detail=str(e))

@app.post("/run")
def run(body: dict[str, Any]) -> dict[str, Any]:
    try:
        detail = body.pop("detail", None) if isinstance(body, dict) else None
        circuit = load_circuit(body)
        if circuit.backend == "fock":
            # deterministic per circuit (seed field, default 0): same JSON
            # → same run (incl. measured outcomes) — reproducible meters
            return run_fock_circuit(circuit, np.random.default_rng(circuit.seed))
        if circuit.backend == "bosonic":
            return run_bosonic_circuit(
                circuit,
                np.random.default_rng(circuit.seed),
                steps=(detail == "steps"),
            )
        result = run_circuit(circuit)
    except (CircuitV0Error, ValueError) as e:
        # ValueError covers library-side guards (loss T range, wigner_grid,
        # np.linalg.LinAlgError is a ValueError subclass) → user-error 422.
        raise _422(e) from e
    return _payload(result)


@app.post("/sample")
def sample(body: dict[str, Any]) -> dict[str, Any]:
    """Measure once: explicit seed → true sampling of all measurement nodes."""
    try:
        circuit = load_circuit(body)
        if circuit.backend == "fock":
            payload = run_fock_circuit(circuit, np.random.default_rng(circuit.seed))
            payload["seed"] = circuit.seed
            payload["sampled"] = True
            return payload
        if circuit.backend == "bosonic":
            payload = run_bosonic_circuit(circuit, np.random.default_rng(circuit.seed))
            payload["seed"] = circuit.seed
            payload["sampled"] = True
            return payload
        result = sample_circuit(circuit, np.random.default_rng(circuit.seed))
    except (CircuitV0Error, ValueError) as e:
        raise _422(e) from e
    return _payload(result, seed=circuit.seed, sampled=True)


@app.post("/batch")
def batch(body: dict[str, Any]) -> dict[str, Any]:
    """Fock batch sampling (F7): UI default 1000 shots; shots validated 1..1e5.

    Gaussian backend → 422 (v0 has no Gaussian batch).
    """
    try:
        if not isinstance(body, dict):
            raise CircuitV0Error("payload must be a JSON object")
        shots = body.pop("shots", 1000)
        circuit = load_circuit(body)
        if circuit.backend != "fock":
            raise CircuitV0Error("batch requires backend='fock' (v0 has no Gaussian batch)")
        if not isinstance(shots, int) or isinstance(shots, bool) or not 1 <= shots <= 100_000:
            raise CircuitV0Error("shots must be an int in [1, 100000]")
        return batch_fock_circuit(circuit, shots, circuit.seed)
    except (CircuitV0Error, ValueError) as e:
        raise _422(e) from e


@app.post("/scan")
def scan(body: dict[str, Any]) -> dict[str, Any]:
    """F-LAB-SCAN: single-param sweep → E_N curve (pure, no RNG).

    Body = circuit_v0 + ``sweep`` segment (UI-session config, not part of the
    circuit_v0 schema). All domain errors → 422 with a UI-safe detail.
    (Note: LinAlgError is NOT a ValueError subclass — always list it explicitly
    in except tuples.)
    """
    try:
        sweep = body.pop("sweep", None)
        circuit = load_circuit(body)
        if circuit.backend == "fock":
            raise CircuitV0Error("scan is not available for the fock backend (v0)")
        if not isinstance(sweep, dict):
            raise CircuitV0Error("sweep must be an object")
        return scan_circuit(circuit, sweep)
    except (CircuitV0Error, ValueError) as e:
        raise _422(e) from e


@app.post("/fidelity")
def fidelity(body: dict[str, Any]) -> dict[str, Any]:
    """B6: Bosonic fidelity-vs-param sweep (GKP QEC γ curve).

    Body = circuit (bosonic) + ``sweep`` segment + ``seed`` + ``rounds``. Unlike
    ``/scan`` (pure E_N), this path is stochastic (homodyne + feedforward), so
    each point is a seeded run; ``rounds>1`` averages seeds. Gaussian/Fock
    backend → 422.
    """
    try:
        sweep = body.pop("sweep", None)
        rounds = body.pop("rounds", 1)
        circuit = load_circuit(body)
        if circuit.backend != "bosonic":
            raise CircuitV0Error("fidelity sweep requires backend='bosonic'")
        if not isinstance(sweep, dict):
            raise CircuitV0Error("sweep must be an object")
        return fidelity_sweep(circuit, sweep, seed=circuit.seed, rounds=rounds)
    except (CircuitV0Error, ValueError) as e:
        raise _422(e) from e


_STATIC_DIR = Path(__file__).resolve().parent / "static"
if not _STATIC_DIR.is_dir():
    raise RuntimeError(f"Missing packaged lab assets: {_STATIC_DIR}")
# Mount last so API routes keep precedence (FastAPI prefix swallowing).
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
