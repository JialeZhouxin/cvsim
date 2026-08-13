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
    "export_cov_for_walrus",
    "pnr_probs",
    "gbs_sample",
    "threshold_sample",
    "p_click",
    "sample_threshold",
}


def test_gaussian_all_matches_freeze():
    assert set(g.__all__) == GAUSSIAN_PUBLIC


def test_gaussian_all_importable():
    for name in g.__all__:
        obj = getattr(g, name)
        assert obj is not None


def test_gaussian_methods_frozen():
    """Methods are not in ``__all__``; freeze the ones the stability policy
    covers explicitly (F-SAMPLE batch: ``sample_quadratures``)."""
    assert callable(g.GaussianState.sample_quadratures)


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


# -- FOCK (F2 exit: freeze the export surface, mirror of GAUSSIAN_PUBLIC) ----

import cvsim.fock as fock

FOCK_PUBLIC = {
    # states + factories
    "FockState",
    "FockDensity",
    "FockSparse",
    "FockCircuit",  # F7: circuit DSL + initial (per-mode number-state initial)
    # leakage trio (F1)
    "truncation_leakage",
    "check_leakage",
    "estimate_leakage",
    # gates (F1)
    "squeeze",
    "displace",
    "phase",
    "beamsplitter",
    "mach_zehnder",
    "two_mode_squeeze",
    "cz",
    "cx",
    "kerr",
    "interferometer",
    "apply_unitary",
    # channels (F1)
    "loss",
    "amplifier",
    "phase_noise",
    "apply_kraus",
    # observables (F1/F2)
    "norm",
    "trace",
    "mean_photon",
    "pnrd_probs",
    "homodyne_mean",
    "homodyne_var",
    "homodyne_sample",
    "homodyne_condition",
    "homodyne_sample_and_condition",
    "pnr_sample",
    "pnr_sample_batch",
    "pnr_condition",
    "pnr_sample_and_condition",
    "heterodyne_sample",
    "heterodyne_condition",
    "heterodyne_sample_and_condition",
    # analyse (F2)
    "entropy_vn",
    "partial_trace",
    "log_negativity",
    "fidelity",
}


def test_fock_all_matches_freeze():
    assert set(fock.__all__) == FOCK_PUBLIC


def test_fock_all_importable():
    for name in fock.__all__:
        assert getattr(fock, name) is not None


def test_fock_methods_frozen():
    """Classmethods (factories) live on the classes, not in ``__all__``."""
    assert callable(fock.FockState.coherent)
    assert callable(fock.FockState.squeezed)
    assert callable(fock.FockState.cat)
    assert callable(fock.FockDensity.thermal)
