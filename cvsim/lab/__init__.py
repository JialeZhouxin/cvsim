"""Gaussian Lab: local workbench backend (``circuit_v1`` IR).

Vision: ``docs/vision-gaussian-lab-ui.md``. L0: IR + ``/run``; L2: frontend
editor; L3: save/load (A5) + ``/sample`` true sampling (A6); ADR-0003 named
the core ``circuit_v1`` schema; ADR-0011 retired the v0 translator (v1
only). F7: Fock dual backend (``backend`` extension field + ``/batch``);
ADR-0010: run/sample dispatch single point.

Public surface = top-level verbs only (schema/run/sample/scan).
The three runner modules stay importable for direct consumers that need
them, but server.py goes through dispatch — never around it.
"""

from cvsim.lab.dispatch import batch_circuit, run_circuit, sample_circuit
from cvsim.lab.ir import (
    SCHEMA,
    CircuitV0Error,
    LabCircuit,
    View,
    load_circuit,
)
from cvsim.lab.result import LabResult
from cvsim.lab.scan import fidelity_sweep, scan_circuit

#: Domain errors that map to a user-error 422 (ADR-0010 #6, single point).
#: CircuitV0Error is the Lab error surface; plain ValueError covers library-side
#: guards (loss T range, wigner_grid; np.linalg.LinAlgError subclasses ValueError).
DOMAIN_ERRORS: tuple[type[BaseException], ...] = (CircuitV0Error, ValueError)

__all__ = [
    "SCHEMA",
    "CircuitV0Error",
    "DOMAIN_ERRORS",
    "LabCircuit",
    "LabResult",
    "View",
    "load_circuit",
    "run_circuit",
    "sample_circuit",
    "batch_circuit",
    "scan_circuit",
    "fidelity_sweep",
]
