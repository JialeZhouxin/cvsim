"""Freeze public export surface (API stability policy).

See docs/api-stability.md. Removing/renaming an entry is a MAJOR bump.
"""

from __future__ import annotations

import cvsim.gaussian as g
from cvsim.conventions import HBAR, QUAD_ORDER, omega, vacuum_cov, vacuum_mean

# Snapshot at Phase 2 API-stability freeze (2026-07-30).
GAUSSIAN_PUBLIC = {
    "GaussianState",
    "apply_symplectic",
    "squeeze",
    "displace",
    "phase",
    "fourier",
    "beamsplitter",
    "mach_zehnder",
    "two_mode_squeeze",
    "cz",
    "cx",
    "interferometer",
    "apply_interferometer",
    "apply_mesh",
    "loss",
    "amplifier",
    "phase_noise",
    "apply_gaussian_channel",
    "is_cp_channel",
    "validate_channel",
    "det_cov",
    "mean_photon",
    "homodyne_mean",
    "homodyne_var",
    "homodyne_sample",
    "homodyne_sample_and_condition",
    "homodyne_sample_batch",
    "homodyne_condition",
    "heterodyne_mean",
    "heterodyne_cov_xp",
    "heterodyne_sample",
    "heterodyne_sample_and_condition",
    "heterodyne_sample_batch",
    "heterodyne_condition",
    "is_physical",
    "validate_state",
    "symplectic_eigenvalues",
    "purity",
    "entropy_vn",
    "partial_trace",
    "log_negativity",
    "fidelity",
    "GaussianCircuit",
    "ParamRef",
}


def test_gaussian_all_matches_freeze():
    assert set(g.__all__) == GAUSSIAN_PUBLIC


def test_gaussian_all_importable():
    for name in g.__all__:
        obj = getattr(g, name)
        assert obj is not None


def test_conventions_frozen():
    assert HBAR == 1.0
    assert QUAD_ORDER == "xxpp"
    assert vacuum_cov(1).shape == (2, 2)
    assert float(vacuum_cov(1)[0, 0]) == 0.5
    assert vacuum_mean(2).shape == (4,)
    om = omega(1)
    assert om.shape == (2, 2)
    assert float(om[0, 1]) == 1.0 and float(om[1, 0]) == -1.0


def test_examples_phase1_imports_public_only():
    """Phase 1 exit demo must not rely on private analyse helpers."""
    import ast
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "examples" / "phase1_exit_demo.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        # from cvsim... import _private
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(
            "cvsim"
        ):
            if any(part.startswith("_") for part in node.module.split(".")):
                raise AssertionError(f"private module import: from {node.module}")
            for alias in node.names:
                assert not alias.name.startswith(
                    "_"
                ), f"private import {alias.name} from {node.module}"
        # import cvsim._private  /  import cvsim.gaussian._x as y
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts and parts[0] == "cvsim":
                    assert not any(
                        p.startswith("_") for p in parts[1:]
                    ), f"private import {alias.name}"
