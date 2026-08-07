"""Gaussian Lab: local workbench backend (circuit_v1 IR + v0 translation).

Vision: ``docs/vision-gaussian-lab-ui.md``. L0: IR + ``/run``; L2: frontend
editor; L3: save/load (A5) + ``/sample`` true sampling (A6); ADR-0003:
core ``circuit_v1`` schema, v0 files translated on load.
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
    scan_circuit,
    translate_v0,
)

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
    "translate_v0",
]
