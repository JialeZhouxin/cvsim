"""F-LAB-IR: circuit_v1 schema validation + golden equivalence (A9).

ADR-0011: circuit_v0 read compatibility removed. These tests now pin the
v1-only loader path; v0 payloads are rejected (one negative case below).
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import gaussian_rbar, gaussian_V, wigner_result

from cvsim.gaussian import (
    GaussianState,
    beamsplitter,
    heterodyne_condition,
    heterodyne_mean,
    log_negativity,
    loss,
    purity,
)
from cvsim.lab import CircuitV0Error, load_circuit, run_circuit
from cvsim.wigner import wigner_grid

MAIN_SCENE = {
    "schema": "circuit_v1",
    "seed": 0,
    "nmode": 2,
    "ops": [
        {"id": "s0", "op": "two_mode_squeeze", "modes": [0, 1], "params": {"r": 0.6}},
        {"id": "l0", "op": "loss", "modes": [0], "params": {"T": 0.8}},
        {"id": "l1", "op": "loss", "modes": [1], "params": {"T": 0.8}},
        {"id": "bs", "op": "beamsplitter", "modes": [0, 1], "params": {"theta": np.pi / 4}},
    ],
    "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
    "ui": {"position": "ignored"},
}


def _hand_main_scene() -> GaussianState:
    st = GaussianState.tmsv(0.6)
    st = loss(st, 0.8, 0)
    st = loss(st, 0.8, 1)
    return beamsplitter(st, 0, 1, np.pi / 4)


# --- schema validation -------------------------------------------------------


def test_rejects_v0_schema():
    with pytest.raises(CircuitV0Error, match="unsupported schema"):
        load_circuit({"schema": "circuit_v0", "nodes": []})


def test_rejects_unknown_op():
    data = {
        "schema": "circuit_v1",
        "nmode": 1,
        "ops": [{"id": "x", "op": "nonsense_op", "modes": [0], "params": {}}],
    }
    with pytest.raises(CircuitV0Error, match="unknown op"):
        load_circuit(data)


def test_rejects_missing_modes_field():
    data = {
        "schema": "circuit_v1",
        "nmode": 1,
        "ops": [{"id": "g", "op": "squeeze", "params": {"r": 0.5}}],
    }
    with pytest.raises(CircuitV0Error, match="modes"):
        load_circuit(data)


def test_rejects_two_mode_op_with_single_mode_list():
    data = {
        "schema": "circuit_v1",
        "nmode": 2,
        "ops": [{"id": "b", "op": "beamsplitter", "modes": [0], "params": {"theta": 0.5}}],
    }
    with pytest.raises(CircuitV0Error, match="exactly 2 modes"):
        load_circuit(data)


def test_rejects_bad_view():
    data = dict(MAIN_SCENE, view={"wigner_mode": 0, "lim": 0.0, "n": 64})
    with pytest.raises(CircuitV0Error, match="lim"):
        load_circuit(data)


def test_rejects_negative_seed():
    data = dict(MAIN_SCENE, seed=-1)
    with pytest.raises(CircuitV0Error, match="seed"):
        load_circuit(data)


def test_mode_out_of_range():
    """v1 trust boundary: modes >= nmode rejected at load (not at run)."""
    data = {
        "schema": "circuit_v1",
        "nmode": 1,
        "ops": [{"id": "g", "op": "squeeze", "modes": [3], "params": {"r": 0.5}}],
    }
    with pytest.raises(CircuitV0Error, match="out of range"):
        load_circuit(data)


def test_wigner_mode_out_of_range():
    data = dict(MAIN_SCENE, view={"wigner_mode": 2, "lim": 5.0, "n": 64})
    with pytest.raises(CircuitV0Error, match="wigner_mode"):
        run_circuit(load_circuit(data))


# --- golden equivalence (A9) --------------------------------------------------


def test_golden_tmsv_loss_bs_matches_hand_written():
    res = run_circuit(load_circuit(MAIN_SCENE))
    hand = _hand_main_scene()
    np.testing.assert_allclose(gaussian_V(res), hand.V, atol=1e-10)
    np.testing.assert_allclose(gaussian_rbar(res), hand.rbar, atol=1e-10)
    assert res.nmode == 2
    assert res.measured == []


def test_golden_meters_match_direct_calls():
    res = run_circuit(load_circuit(MAIN_SCENE))
    hand = _hand_main_scene()
    np.testing.assert_allclose(res.meters["purity"], purity(hand), atol=1e-12)
    np.testing.assert_allclose(
        res.meters["log_negativity"], log_negativity(hand, modes_A=[0]), atol=1e-10
    )


def test_heterodyne_removes_mode():
    data = {
        "schema": "circuit_v1",
        "seed": 0,
        "nmode": 2,
        "ops": [
            {"id": "s", "op": "two_mode_squeeze", "modes": [0, 1], "params": {"r": 0.6}},
            {"id": "h", "op": "measure_heterodyne", "modes": [0], "params": {"name": "h"}},
        ],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 32},
    }
    res = run_circuit(load_circuit(data))
    assert res.nmode == 1
    assert res.meters["mean_photon_per_mode"] == [pytest.approx(res.meters["mean_photon"])]

    hand = GaussianState.tmsv(0.6)
    outcome = heterodyne_mean(hand, 0)
    hand = heterodyne_condition(hand, 0, outcome)
    np.testing.assert_allclose(gaussian_V(res), hand.V, atol=1e-10)
    np.testing.assert_allclose(gaussian_rbar(res), hand.rbar, atol=1e-10)
    assert len(res.measured) == 1
    assert res.measured[0]["op"] == "measure_heterodyne"
    assert res.measured[0]["mode"] == 0


def test_homodyne_removes_mode():
    """v1 semantics (design §0): homodyne removes the measured mode — same as
    GaussianCircuit. Guided state = condition + remove."""
    from cvsim.gaussian import homodyne_condition, homodyne_mean

    data = {
        "schema": "circuit_v1",
        "seed": 0,
        "nmode": 2,
        "ops": [
            {"id": "s", "op": "two_mode_squeeze", "modes": [0, 1], "params": {"r": 0.6}},
            {
                "id": "h",
                "op": "measure_homodyne",
                "modes": [0],
                "params": {"phi": 0.0, "name": "h"},
            },
        ],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 32},
    }
    res = run_circuit(load_circuit(data))
    assert res.nmode == 1
    hand = GaussianState.tmsv(0.6)
    o = homodyne_mean(hand, 0, 0.0)
    hand = homodyne_condition(hand, 0, 0.0, o).remove_mode(0)
    np.testing.assert_allclose(gaussian_V(res), hand.V, atol=1e-10)
    np.testing.assert_allclose(gaussian_rbar(res), hand.rbar, atol=1e-10)
    assert res.measured[0]["op"] == "measure_homodyne"


def test_wigner_matches_direct_partial_trace_grid():
    res = run_circuit(load_circuit(MAIN_SCENE))
    hand = _hand_main_scene()
    # wigner_mode=0 → partial_trace(keep=[0]) → mode-0 block (top-left 2×2)
    keep = GaussianState(V=hand.V[:2, :2], rbar=hand.rbar[:2])
    X, P, W = wigner_grid(keep, lim=5.0, n=64)
    wx, wp, wW = wigner_result(res)
    np.testing.assert_allclose(wW, W, atol=1e-10)
    np.testing.assert_allclose(wx, X[0], atol=0.0)
    np.testing.assert_allclose(wp, P[:, 0], atol=0.0)


def test_ui_extra_keys_ignored_by_run():
    data = dict(MAIN_SCENE, ui={"pixels": {"s0": [1, 2]}})
    res = run_circuit(load_circuit(data))
    hand = _hand_main_scene()
    np.testing.assert_allclose(gaussian_V(res), hand.V, atol=1e-10)


def test_displace_complex_alpha_forms():
    """v1 displace alpha = [re, im] complex literal; gaussian runs match coherent."""
    for alpha in ([0.5, 0.0], [0.3, -0.4]):
        data = {
            "schema": "circuit_v1",
            "seed": 0,
            "nmode": 1,
            "ops": [{"id": "d", "op": "displace", "modes": [0], "params": {"alpha": alpha}}],
            "view": {"wigner_mode": 0, "lim": 4.0, "n": 32},
        }
        res = run_circuit(load_circuit(data))
        hand = GaussianState.coherent(complex(alpha[0], alpha[1]))
        np.testing.assert_allclose(gaussian_rbar(res), hand.rbar, atol=1e-10)
        np.testing.assert_allclose(gaussian_V(res), hand.V, atol=1e-10)
