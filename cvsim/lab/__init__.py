"""Gaussian Lab: local workbench backend (circuit_v0 IR + thin API).

Vision: ``docs/vision-gaussian-lab-ui.md``. L0: IR + ``/run``; L2: frontend
editor; L3: save/load (A5) + ``/sample`` true sampling (A6).
"""

from cvsim.lab.ir import (
    SCHEMA,
    CircuitV0,
    CircuitV0Error,
    Node,
    RunResult,
    View,
    load_circuit,
    run_circuit,
    sample_circuit,
    scan_circuit,
)

__all__ = [
    "SCHEMA",
    "CircuitV0",
    "CircuitV0Error",
    "Node",
    "RunResult",
    "View",
    "load_circuit",
    "run_circuit",
    "sample_circuit",
    "scan_circuit",
]
