"""Gaussian Lab: local workbench backend (circuit_v0 IR + thin API).

Vision: ``docs/vision-gaussian-lab-ui.md``. L0 scope only — IR + ``/run``;
frontend/editor (L2), save/load and sampling (L3) are later slices.
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
]
