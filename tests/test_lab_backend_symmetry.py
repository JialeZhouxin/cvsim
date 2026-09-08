"""Lab backend symmetry structural guards (08-25-lab-backend-symmetry),
extended by the payload-unification ticket (ADR-0008).

Pure structural/boundary tests — behavior is covered by test_lab_ir.py etc.
ADR-0008: all three backends assemble LabResult snapshots (cvsim/lab/result.py
owns the contract); ir.py keeps the Gaussian execution dispatch (_execute);
gaussian_backend.py owns only state→LabResult assembly.

Guards:
1. gaussian_backend exists with _build_result + _meters.
2. ir.py no longer defines _meters / _build_result (migrated out).
3. ir.py __dict__ has no dead private re-exports
   (_fock_*/_bosonic_*/_LEAKAGE_DIM_CAP/_fidelity_target).
4. ir.py module source has zero `import cvsim.lab.{fock,bosonic,gaussian}_backend`
   (M2: includes gaussian_backend — D1-A invariant; removes pre-existing cycle).
5. lab.__all__ is exactly the 11 frozen public names (top-level verbs only;
   per-backend execution is imported from backend modules, not re-exported).
   ADR-0008: RunResult removed, LabResult takes its slot (still 11).
6. C1: CircuitV0Error resolvable in gaussian_backend namespace (wigner_mode guard).
7. import order smoke: gaussian_backend then ir both importable (no cycle).
8. ADR-0008: all three backend runners return LabResult instances.
9. ADR-0008: no hand-built payload dicts — wigner slicing/`"backend":` dict
   literals live only in result.py; backend modules never emit schema keys.
10. ADR-0008: meters keys of every runner ⊆ the declared meter support matrix
    (guard fires at runtime; here we lock the declared rows themselves).
11. ADR-0008: the wigner `{x,p,W}` slice exists exactly once in cvsim/lab
    (result.py) — the 4× duplication is gone and cannot regrow silently.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IR_SRC = (ROOT / "cvsim/lab/ir.py").read_text(encoding="utf-8")

EXPECTED_ALL = {
    "SCHEMA",
    "CircuitV0Error",
    "DOMAIN_ERRORS",  # ADR-0010 #6: 422 policy single point
    "LabCircuit",
    "LabResult",
    "View",
    "load_circuit",
    "run_circuit",
    "sample_circuit",
    "batch_circuit",  # /batch verb via dispatch (was fock_backend direct import)
    "scan_circuit",
    "fidelity_sweep",
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
    """R2/ADR-0008: lab.__all__ frozen public verb list (12 names).

    RunResult was removed with the unified LabResult contract; LabResult (the
    response snapshot type) occupies its slot. ADR-0011 removed
    ``translate_v0``. 2026-09: ``batch_circuit`` joined as the fourth verb —
    /batch existed since R4 but its runner import bypassed dispatch
    (ADR-0010 #8 AST guard was false-green, fixed with the same change).
    """
    import cvsim.lab as lab

    assert set(lab.__all__) == EXPECTED_ALL, (
        f"lab.__all__ drift: got {set(lab.__all__)} expected {EXPECTED_ALL}"
    )
    assert len(lab.__all__) == 12
    assert "RunResult" not in lab.__all__, "RunResult deleted (ADR-0008)"
    assert not hasattr(lab, "RunResult"), "RunResult must be gone from the public surface"


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


# --- ADR-0008 payload-unification guards ------------------------------------


def test_runners_return_lab_result():
    """ADR-0008 Q1.a: all three runners assemble LabResult snapshots."""
    import numpy as np

    from cvsim.lab.bosonic_backend import run_bosonic_circuit
    from cvsim.lab.dispatch import run_circuit
    from cvsim.lab.fock_backend import run_fock_circuit
    from cvsim.lab.ir import load_circuit
    from cvsim.lab.result import LabResult

    g = run_circuit(
        load_circuit(
            {
                "schema": "circuit_v1",
                "nmode": 1,
                "ops": [
                    {"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1, "phi": 0.0}}
                ],
                "view": {"wigner_mode": 0, "lim": 4.0, "n": 16},
            }
        )
    )
    assert isinstance(g, LabResult) and g.backend == "gaussian"

    fock_body = {
        "schema": "circuit_v1",
        "backend": "fock",
        "nmode": 1,
        "cutoff": 6,
        "seed": 0,
        "ops": [{"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1}}],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 16},
    }
    f = run_fock_circuit(load_circuit(fock_body))
    assert isinstance(f, LabResult) and f.backend == "fock"

    bos_body = dict(fock_body, backend="bosonic", initial=[None])
    bos_body.pop("cutoff")
    b = run_bosonic_circuit(load_circuit(bos_body))
    assert isinstance(b, LabResult) and b.backend == "bosonic"
    assert np is np  # numpy imported for the (unused) array-typed guards above


def test_no_handbuilt_payload_dicts():
    """ADR-0008 R7b: backend modules never hand-assemble response payloads.

    Grep-guard: the response-shape knowledge (wigner slicing, LabResult core
    key emission, seed/sampled patching) may appear only in result.py. The
    /batch histogram dicts are deliberately excluded (Q5: single producer,
    no mirror, not a LabResult shape). A new hand-built payload dict in a
    backend is exactly the drift this ticket killed — this guard keeps it dead.
    """
    forbidden = {
        "cvsim/lab/gaussian_backend.py": ['"schema"', '"wigner": (', "payload[", '"measured"'],
        "cvsim/lab/fock_backend.py": ['"schema"', "wigner[0][0]", '"wigner": (', "payload["],
        "cvsim/lab/bosonic_backend.py": ['"schema"', "wigner[0][0]", '"wigner": (', "payload["],
        # ir.py: response payload keys must not appear there (result assembly
        # lives in the per-backend runner modules, ADR-0010).
        "cvsim/lab/ir.py": ['"wigner"', '"meters"', '"measured"'],
    }
    for rel, needles in forbidden.items():
        src = (ROOT / rel).read_text(encoding="utf-8")
        for needle in needles:
            assert needle not in src, f"{rel}: hand-built payload knowledge '{needle}' regressed"


def test_wigner_slice_single_point():
    """ADR-0008 acceptance: the wigner {x,p,W} slice exists exactly once in
    cvsim/lab (result.py). Previously duplicated 4× (server._payload, fock,
    bosonic ×2) — this grep keeps it single-source."""
    hits: list[str] = []
    for p in (ROOT / "cvsim/lab").glob("*.py"):
        if p.name == "result.py":
            continue
        if "tolist()" in p.read_text(encoding="utf-8") and "W" in p.read_text(encoding="utf-8"):
            src = p.read_text(encoding="utf-8")
            if '"x":' in src and '"p":' in src and '"W":' in src:
                hits.append(p.name)
    assert hits == [], f"wigner {chr(123)}x,p,W{chr(125)} slicing regressed into: {hits}"


def test_meters_within_declared_matrix():
    """ADR-0008 R5: the declared matrix rows and the runtime ⊆ guard.

    Rows: core trio + per-representation extensions; every runner calls
    check_meters (guard fires at assembly), so here we lock the declared
    rows themselves — a change here must be a conscious matrix edit.
    """
    from cvsim.lab.result import METER_CORE, METER_EXTENSIONS, METER_SUPPORT

    assert frozenset({"purity", "mean_photon", "mean_photon_per_mode"}) == METER_CORE
    assert {
        "gaussian": frozenset({"log_negativity", "singular"}),
        "fock": frozenset({"leakage"}),
        "bosonic": frozenset(),
    } == METER_EXTENSIONS
    for backend, ext in METER_EXTENSIONS.items():
        assert METER_SUPPORT[backend] == METER_CORE | ext


def test_check_meters_rejects_undeclared():
    """The ⊆ guard screams on an undeclared key (never silently widens)."""
    import pytest as _pytest

    from cvsim.lab.result import check_meters

    with _pytest.raises(RuntimeError, match="meter support matrix"):
        check_meters("fock", {"purity": 1.0, "log_negativity": 0.5})  # gaussian-only key


def test_result_py_dependency_bottom():
    """R1: result.py imports only numpy/stdlib — dependency graph bottom."""
    src = (ROOT / "cvsim/lab/result.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("cvsim"), (
                f"result.py must not import cvsim modules (found {node.module})"
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("cvsim"), (
                    f"result.py must not import cvsim modules (found {alias.name})"
                )


def test_bosonic_no_fock_private_import():
    """ADR-0008 Q3: the cross-package private break (bosonic importing fock's
    _fock_measured) is gone — the shared collector lives in result.py.

    ADR-0010 #5 bends this once, deliberately: bosonic imports fock's
    ``_wigner_mode_guard_fail`` (the single-point 422 message template).
    That is shared *message* knowledge, not fock execution knowledge —
    ADR-0010 #5 registers the exception here so this guard stays honest."""
    src = (ROOT / "cvsim/lab/bosonic_backend.py").read_text(encoding="utf-8")
    assert "from cvsim.lab.fock_backend import run_" not in src, (
        "bosonic_backend must not import fock execution"
    )
    allowed = "from cvsim.lab.fock_backend import _wigner_mode_guard_fail"
    stripped = src.replace(allowed, "")
    assert "fock_backend" not in stripped.replace(
        "previously this module imported fock's private ``_fock_measured``", ""
    ), "bosonic_backend must not import fock_backend (beyond the ADR-0010 template)"
