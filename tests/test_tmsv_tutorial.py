"""Physics freezes from tutorials/04_tmsv_analyse.ipynb (Phase 2 teach)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianState,
    entropy_vn,
    heterodyne_condition,
    log_negativity,
    loss,
    partial_trace,
    purity,
    symplectic_eigenvalues,
)

ATOL = 1e-10
NB = Path(__file__).resolve().parents[1] / "tutorials" / "04_tmsv_analyse.ipynb"


def test_tmsv_notebook_exists():
    assert NB.is_file(), f"missing {NB}; run python tutorials/_build_notebooks.py"


def test_tmsv_notebook_mentions_key_apis():
    if not NB.is_file():
        pytest.skip(f"{NB} not found; run python tutorials/_build_notebooks.py")
    text = NB.read_text(encoding="utf-8")
    for token in (
        "log_negativity",
        "partial_trace",
        "entropy_vn",
        "heterodyne_condition",
        "purity",
        "T4 TMSV analyse self-check OK",
        "nbar > 0",
    ):
        assert token in text, f"notebook missing token: {token}"


def test_tmsv_tutorial_physics_self_check():
    """Same asserts as the notebook final cell (no Jupyter needed)."""
    r = 0.6
    st = GaussianState.tmsv(r, nmode=2)
    assert abs(purity(st) - 1.0) < ATOL
    assert abs(entropy_vn(st)) < ATOL
    nu = symplectic_eigenvalues(st)
    assert nu.shape == (2,) and np.allclose(nu, 0.5, atol=ATOL)

    nbar = float(np.sinh(r) ** 2)
    red = partial_trace(st, [0])
    assert abs(purity(red) - 1.0 / (2 * nbar + 1)) < ATOL
    # nbar=0 → S=0 by continuity (avoid 0*log0 NaN)
    S_closed = (nbar + 1) * np.log(nbar + 1) - nbar * np.log(nbar) if nbar > 0.0 else 0.0
    assert abs(entropy_vn(red) - S_closed) < ATOL
    assert abs(entropy_vn(partial_trace(st, [1])) - entropy_vn(red)) < ATOL

    EN = log_negativity(st, 0)
    assert abs(EN - (-np.log2(np.exp(-2 * r)))) < ATOL
    assert abs(log_negativity(st, 1) - EN) < ATOL

    beta = 0.4 + 0.2j
    red_h = heterodyne_condition(st, 0, beta)
    assert abs(purity(red_h) - 1.0) < ATOL
    beta_B = (red_h.rbar[0] + 1j * red_h.rbar[1]) / np.sqrt(2.0)
    assert abs(beta_B - np.tanh(r) * np.conjugate(beta)) < ATOL

    assert log_negativity(loss(st, 0.5), 0) < EN


@pytest.mark.parametrize("r", [0.3, 0.6, 1.0])
def test_tmsv_logneg_curve_freeze(r):
    st = GaussianState.tmsv(r, nmode=2)
    assert log_negativity(st, 0) == pytest.approx(-np.log2(np.exp(-2 * r)), abs=1e-9)


def test_tmsv_r0_reduced_entropy_closed_no_nan():
    """OCR: hand formula must not NaN at nbar=0 (r=0 → vacuum product)."""
    r = 0.0
    st = GaussianState.tmsv(r, nmode=2)
    nbar = float(np.sinh(r) ** 2)
    assert nbar == 0.0
    red = partial_trace(st, [0])
    S_closed = (nbar + 1) * np.log(nbar + 1) - nbar * np.log(nbar) if nbar > 0.0 else 0.0
    assert np.isfinite(S_closed)
    assert abs(entropy_vn(red) - S_closed) < ATOL
