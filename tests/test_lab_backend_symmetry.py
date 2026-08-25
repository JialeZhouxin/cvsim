"""Lab backend symmetry structural guards (08-25-lab-backend-symmetry).

Pure structural/boundary tests — behavior is covered by test_lab_ir.py etc.
Mirrors fock_backend.py / bosonic_backend.py: per-representation result-assembly
glue (meters + Wigner view) lives in its own backend module. ir.py keeps the
Gaussian execution dispatch (_execute); gaussian_backend.py owns only
state→RunResult assembly.

Guards:
1. gaussian_backend exists with _build_result + _meters.
2. ir.py no longer defines _meters / _build_result (migrated out).
3. ir.py __dict__ has no dead private re-exports
   (_fock_*/_bosonic_*/_LEAKAGE_DIM_CAP/_fidelity_target).
4. ir.py module source has zero `import cvsim.lab.{fock,bosonic,gaussian}_backend`
   (M2: includes gaussian_backend — D1-A invariant; removes pre-existing cycle).
5. lab.__all__ is exactly the 11 frozen public names (top-level verbs only;
   per-backend execution is imported from backend modules, not re-exported).
6. C1: CircuitV0Error resolvable in gaussian_backend namespace (wigner_mode guard).
7. import order smoke: gaussian_backend then ir both importable (no cycle).
"""

from __future__ import annotations

import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IR_SRC = (ROOT / "cvsim/lab/ir.py").read_text(encoding="utf-8")

EXPECTED_ALL = {
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
}


def test_gaussian_backend_exists():
    """R1: gaussian_backend.py exists with _build_result + _meters."""
    mod = importlib.import_module("cvsim.lab.gaussian_backend")
    assert hasattr(mod, "_build_result"), "gaussian_backend must define _build_result"
    assert hasattr(mod, "_meters"), "gaussian_backend must define _meters"


def test_ir_no_longer_defines_build_result():
    """R1: _meters / _build_result migrated out of ir.py."""
    import cvsim.lab.ir as ir

    assert not hasattr(ir, "_meters"), "ir.py must not define _meters (moved to gaussian_backend)"
    assert not hasattr(ir, "_build_result"), (
        "ir.py must not define _build_result (moved to gaussian_backend)"
    )


def test_ir_no_private_backend_reexports():
    """R2: dead backward-compat private re-export block deleted from ir.py."""
    import cvsim.lab.ir as ir

    dead = {
        "_fock_meters",
        "_bosonic_meters",
        "_LEAKAGE_DIM_CAP",
        "_fidelity_target",
        "_fock_joint",
        "_fock_leakage",
        "_fock_mean_photon",
        "_fock_measured",
        "_fock_mode_probs",
        "_fock_purity",
        "_fock_wigner",
        "_bosonic_adaptive_n",
        "_bosonic_reduce_to_mode",
        "_bosonic_single_wigner",
        "_bosonic_wigner_payload",
    }
    leaked = dead & set(ir.__dict__)
    assert not leaked, f"ir.py still re-exports dead private names: {leaked}"


def test_ir_no_module_import_of_backends():
    """D1-A: ir.py module-level (no function-local) source has zero import of any backend.

    Includes gaussian_backend (M2) — the D1-A invariant that ir.py never
    module-imports any backend, removing the pre-existing ir↔backends cycle.
    Function-local imports (inside _execute) are allowed (that's the D1-A
    pattern). Checked via AST: only Module-body Import/ImportFrom nodes, not
    those nested inside FunctionDef.
    """
    import ast

    tree = ast.parse(IR_SRC)
    module_level_imports: set[str] = set()
    for node in tree.body:  # top-level only, not nested in functions
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_level_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            module_level_imports.add(node.module)
    for backend in ("fock_backend", "bosonic_backend", "gaussian_backend"):
        full = f"cvsim.lab.{backend}"
        assert full not in module_level_imports, (
            f"ir.py module-level imports {backend} (must not — D1-A cycle-free)"
        )


def test_init_all_names():
    """R2: lab.__all__ frozen at exactly 11 public names (verbs only)."""
    import cvsim.lab as lab

    assert set(lab.__all__) == EXPECTED_ALL, (
        f"lab.__all__ drift: got {set(lab.__all__)} expected {EXPECTED_ALL}"
    )
    assert len(lab.__all__) == 11


def test_gaussian_backend_imports_circuitv0error():
    """C1: CircuitV0Error resolvable in gaussian_backend (wigner_mode guard).

    _build_result raises CircuitV0Error when view.wigner_mode >= state.nmode;
    the import block must include it or the guard NameErrors at runtime.
    test_run_422_bad_view covers the behavior path.
    """
    import cvsim.lab.gaussian_backend as gb

    assert "CircuitV0Error" in dir(gb), (
        "gaussian_backend must import CircuitV0Error (raised by _build_result "
        "wigner_mode guard; omitting it NameErrors)"
    )
    from cvsim.lab.ir import CircuitV0Error

    assert gb.CircuitV0Error is CircuitV0Error


def test_no_circular_import():
    """D1-A smoke: gaussian_backend and ir both importable, no cycle."""
    importlib.import_module("cvsim.lab.gaussian_backend")
    importlib.import_module("cvsim.lab.ir")
    # also via the package to exercise __init__.py import-source split
    importlib.reload(importlib.import_module("cvsim.lab"))
