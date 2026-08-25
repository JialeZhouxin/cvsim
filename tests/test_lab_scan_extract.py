"""Lab scan extract structural guards (08-25-lab-scan-extract).

Pure structural/boundary tests — behavior is covered by test_lab_l4.py etc.
scan_circuit + its private helpers (_safe_logneg / _inject_symbolic_param)
and the SWEEPABLE_PARAMS constant move from lab/ir.py to lab/scan.py so
ir.py keeps only schema + translate + Gaussian execution.

Guards:
1. scan.py exists with scan_circuit + SWEEPABLE_PARAMS.
2. ir.py no longer defines scan_circuit / _safe_logneg / _inject_symbolic_param / SWEEPABLE_PARAMS.
3. ir.py top-level imports no `math` (only scan used it).
4. ir.py module-level source has zero `cvsim.lab.scan` import (D1: ir.py never imports scan).
5. scan.py module-level imports cvsim.lab.ir (single-direction constraint).
6. lab.scan_circuit is lab.scan.scan_circuit (__init__.py forwards from new source).
7. import order smoke: scan then ir both importable (no cycle).
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IR_SRC = (ROOT / "cvsim/lab/ir.py").read_text(encoding="utf-8")


def test_scan_module_exists():
    """R1: scan.py exists with scan_circuit + SWEEPABLE_PARAMS."""
    mod = importlib.import_module("cvsim.lab.scan")
    assert hasattr(mod, "scan_circuit"), "scan.py must define scan_circuit"
    assert hasattr(mod, "SWEEPABLE_PARAMS"), "scan.py must define SWEEPABLE_PARAMS"
    assert hasattr(mod, "_safe_logneg"), "scan.py must define _safe_logneg"
    assert hasattr(mod, "_inject_symbolic_param"), "scan.py must define _inject_symbolic_param"


def test_ir_no_longer_defines_scan():
    """R2: scan symbols migrated out of ir.py."""
    import cvsim.lab.ir as ir
    moved = {"scan_circuit", "_safe_logneg", "_inject_symbolic_param", "SWEEPABLE_PARAMS"}
    leaked = moved & set(ir.__dict__)
    assert not leaked, f"ir.py still defines scan symbols: {leaked}"


def test_ir_no_import_math():
    """R2: ir.py top-level imports no `math` (only scan used it)."""
    tree = ast.parse(IR_SRC)
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "math", "ir.py must not import math (moved to scan)"


def test_ir_no_module_import_of_scan():
    """D1: ir.py module-level source has zero import of cvsim.lab.scan.

    AST check (Module body only, not function-local). ir.py never imports scan.py
    — single-direction, no cycle (mirrors gaussian_backend.py pattern).
    """
    tree = ast.parse(IR_SRC)
    module_level_modules: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_level_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            module_level_modules.add(node.module)
    assert "cvsim.lab.scan" not in module_level_modules, "ir.py module-imports scan (must not — D1)"


def test_scan_imports_ir_types():
    """D1: scan.py module-level imports cvsim.lab.ir (single-direction)."""
    import cvsim.lab.scan as scan
    assert "cvsim.lab.ir" in dir(scan) or any(
        "cvsim.lab.ir" in str(getattr(scan, n))
        for n in dir(scan)
    ), "scan.py must import cvsim.lab.ir"
    # direct: scan imports the shared helpers it needs from ir
    from cvsim.lab.ir import MEASUREMENT_OPS, _num, _require
    assert scan._require is _require, "scan._require must be ir._require"
    assert scan._num is _num, "scan._num must be ir._num"
    assert scan.MEASUREMENT_OPS is MEASUREMENT_OPS, (
        "scan.MEASUREMENT_OPS must be ir.MEASUREMENT_OPS"
    )


def test_init_scan_import_source():
    """R3: lab.scan_circuit is lab.scan.scan_circuit (__init__ forwards from scan)."""
    import cvsim.lab as lab
    import cvsim.lab.scan as scan
    assert lab.scan_circuit is scan.scan_circuit, (
        "lab.scan_circuit must come from cvsim.lab.scan (got different object)"
    )


def test_no_circular_import():
    """D1 smoke: scan and ir both importable, no cycle."""
    importlib.import_module("cvsim.lab.scan")
    importlib.import_module("cvsim.lab.ir")
    importlib.reload(importlib.import_module("cvsim.lab"))
