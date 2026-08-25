"""Gaussian Lab: local workbench backend (circuit_v1 IR + v0 translation).

Vision: ``docs/vision-gaussian-lab-ui.md``. L0: IR + ``/run``; L2: frontend
editor; L3: save/load (A5) + ``/sample`` true sampling (A6); ADR-0003:
core ``circuit_v1`` schema, v0 files translated on load; F7: Fock dual
backend (``backend`` extension field + ``/batch``).

Public surface = top-level verbs only (schema/translate/run/sample/scan).
Per-backend execution lives in the backend modules and is imported from there
directly by consumers that need it (server.py); it is not re-exported here.
"""

from cvsim.lab.ir import (
    SCHEMA,
    CircuitV0Error,
    LabCircuit,
    RunResult,
    View,
    load_circuit,
    run_circuit,
    sample_circuit,
    translate_v0,
)
from cvsim.lab.scan import fidelity_sweep, scan_circuit

__all__ = [
    "SCHEMA",
    "CircuitV0Error",
    "LabCircuit",
    "RunResult",
    "View",
    "load_circuit",
    "run_circuit",
    "sample_circuit",
    "scan_circuit",
    "fidelity_sweep",
    "translate_v0",
]
