"""F-LAB-IR: circuit_v0 schema validation + golden equivalence (A9)."""

from __future__ import annotations

import numpy as np
import pytest

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
    "schema": "circuit_v0",
    "seed": 0,
    "nodes": [
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "l0", "op": "loss", "params": {"T": 0.8}, "mode": 0},
        {"id": "l1", "op": "loss", "params": {"T": 0.8}, "mode": 1},
        {"id": "bs", "op": "beamsplitter", "params": {"theta": np.pi / 4}, "modes": [0, 1]},
    ],
    "edges": [],
    "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
    "ui": {"position": "ignored"},
}


def _hand_main_scene() -> GaussianState:
    st = GaussianState.tmsv(0.6)
    st = loss(st, 0.8, 0)
    st = loss(st, 0.8, 1)
    return beamsplitter(st, 0, 1, np.pi / 4)


# --- schema validation -------------------------------------------------------


def test_rejects_wrong_schema_version():
    """schema v1 but v0 shape (nodes key, no nmode): v1 path rejects."""
    data = dict(MAIN_SCENE, schema="circuit_v1")
    with pytest.raises(CircuitV0Error, match="nmode"):
        load_circuit(data)


def test_rejects_unknown_op():
    data = {"schema": "circuit_v0", "nodes": [{"id": "x", "op": "cz", "params": {}}]}
    with pytest.raises(CircuitV0Error, match="unknown op"):
        load_circuit(data)


def test_rejects_missing_mode_on_single_mode_op():
    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "s", "op": "vacuum", "params": {}},
            {"id": "g", "op": "squeeze", "params": {"r": 0.5}},
        ],
    }
    with pytest.raises(CircuitV0Error, match="requires field 'mode'"):
        load_circuit(data)


def test_rejects_two_mode_op_with_single_mode_list():
    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "s", "op": "vacuum", "params": {"nmode": 2}},
            {"id": "b", "op": "beamsplitter", "params": {"theta": 0.5}, "modes": [0]},
        ],
    }
    with pytest.raises(CircuitV0Error, match="length 2"):
        load_circuit(data)


def test_rejects_empty_nodes():
    with pytest.raises(CircuitV0Error, match="non-empty"):
        load_circuit({"schema": "circuit_v0", "nodes": []})


def test_rejects_bad_view():
    data = dict(MAIN_SCENE, view={"wigner_mode": 0, "lim": 0.0, "n": 64})
    with pytest.raises(CircuitV0Error, match="lim"):
        load_circuit(data)


def test_rejects_negative_seed():
    data = dict(MAIN_SCENE, seed=-1)
    with pytest.raises(CircuitV0Error, match="seed"):
        load_circuit(data)


def test_source_must_be_first():
    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "g", "op": "squeeze", "params": {"r": 0.5}, "mode": 0},
            {"id": "s", "op": "vacuum", "params": {}},
        ],
    }
    with pytest.raises(CircuitV0Error, match="source op must be first"):
        load_circuit(data)


def test_two_sources_rejected_when_gate_in_between():
    """L5.5: sources may repeat (direct-product append), but a gate between
    sources is still illegal (sources must lead the node list)."""
    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "a", "op": "vacuum", "params": {}},
            {"id": "p", "op": "phase", "params": {"phi": 1.0}, "mode": 0},
            {"id": "b", "op": "vacuum", "params": {}},
        ],
    }
    with pytest.raises(CircuitV0Error, match="source op must be first"):
        run_circuit(load_circuit(data))


def test_multi_source_vacuum_equiv_single_nmode():
    """L5.5: vacuum×2 + displace×2 ≡ vacuum nmode=2 (direct product)."""
    def scene(multi: bool) -> dict:
        nodes = [{"id": "s0", "op": "vacuum", "params": {"nmode": 1 if multi else 2}}]
        if multi:
            nodes.append({"id": "s1", "op": "vacuum", "params": {"nmode": 1}})
        return {
            "schema": "circuit_v0",
            "nodes": nodes
            + [
                {"id": "d0", "op": "displace", "params": {"alpha": 1.0}, "mode": 0},
                {"id": "d1", "op": "displace", "params": {"alpha": 1.0}, "mode": 1},
            ],
        }
    r1 = run_circuit(load_circuit(scene(True)))   # two vacuum sources
    r2 = run_circuit(load_circuit(scene(False)))  # single vacuum nmode=2
    assert r1.nmode == 2 and r2.nmode == 2
    assert np.allclose(r1.rbar, r2.rbar)
    assert np.allclose(r1.V, r2.V)


def test_multi_source_tmsv_append_third_mode():
    """L5.5: vacuum + tmsv appended → 3 modes, tmsv block entangled only within
    its own pair (V block diagonal across source groups)."""
    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "a", "op": "vacuum", "params": {}},
            {"id": "b", "op": "tmsv", "params": {"r": 0.5}, "modes": [1, 2]},
        ],
    }
    res = run_circuit(load_circuit(data))
    assert res.nmode == 3
    # xxpp split layout: rows = [x0,x1,x2,p0,p1,p2]
    # tmsv pair (modes 1,2) entangled: x1-x2 and p1-p2 cross terms nonzero
    assert abs(res.V[1, 2]) > 0  # x1·x2
    assert abs(res.V[4, 5]) > 0  # p1·p2
    # vacuum mode 0 uncorrelated with the pair: x0/p0 rows empty off-diagonal
    assert np.abs(res.V[0, 1:]).max() < 1e-12                      # x0 row
    assert np.abs(np.concatenate([res.V[3, :3], res.V[3, 4:]])).max() < 1e-12  # p0 row


def test_mode_out_of_range():
    """v1 trust boundary: modes >= nmode rejected at load (not at run)."""
    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "s", "op": "vacuum", "params": {}},
            {"id": "g", "op": "squeeze", "params": {"r": 0.5}, "mode": 3},
        ],
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
    np.testing.assert_allclose(res.V, hand.V, atol=1e-10)
    np.testing.assert_allclose(res.rbar, hand.rbar, atol=1e-10)
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
        "schema": "circuit_v0",
        "nodes": [
            {"id": "s", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
            {"id": "h", "op": "heterodyne", "params": {}, "mode": 0},
        ],
        "edges": [],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 32},
    }
    res = run_circuit(load_circuit(data))
    assert res.nmode == 1
    assert res.meters["mean_photon_per_mode"] == [pytest.approx(res.meters["mean_photon"])]

    hand = GaussianState.tmsv(0.6)
    outcome = heterodyne_mean(hand, 0)
    hand = heterodyne_condition(hand, 0, outcome)
    np.testing.assert_allclose(res.V, hand.V, atol=1e-10)
    np.testing.assert_allclose(res.rbar, hand.rbar, atol=1e-10)
    assert len(res.measured) == 1
    assert res.measured[0]["op"] == "measure_heterodyne"
    assert res.measured[0]["mode"] == 0


def test_homodyne_removes_mode():
    """v1 semantics (design §0): homodyne removes the measured mode — same as
    GaussianCircuit; v0 kept it in place. Guided state = condition + remove."""
    from cvsim.gaussian import homodyne_condition, homodyne_mean

    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "s", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
            {"id": "h", "op": "homodyne", "params": {"phi": 0.0}, "mode": 0},
        ],
        "edges": [],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 32},
    }
    res = run_circuit(load_circuit(data))
    assert res.nmode == 1
    hand = GaussianState.tmsv(0.6)
    o = homodyne_mean(hand, 0, 0.0)
    hand = homodyne_condition(hand, 0, 0.0, o).remove_mode(0)
    np.testing.assert_allclose(res.V, hand.V, atol=1e-10)
    np.testing.assert_allclose(res.rbar, hand.rbar, atol=1e-10)
    assert res.measured[0]["op"] == "measure_homodyne"


def test_wigner_matches_direct_partial_trace_grid():
    res = run_circuit(load_circuit(MAIN_SCENE))
    hand = _hand_main_scene()
    # wigner_mode=0 → partial_trace(keep=[0]) → mode-0 block (top-left 2×2)
    keep = GaussianState(V=hand.V[:2, :2], rbar=hand.rbar[:2])
    X, P, W = wigner_grid(keep, lim=5.0, n=64)
    np.testing.assert_allclose(res.wigner[2], W, atol=1e-10)
    np.testing.assert_allclose(res.wigner[0], X, atol=0.0)
    np.testing.assert_allclose(res.wigner[1], P, atol=0.0)


def test_ui_and_edges_are_ignored_by_run():
    data = dict(MAIN_SCENE, ui={"pixels": {"s0": [1, 2]}}, edges=[{"from": "x", "to": "y"}])
    res = run_circuit(load_circuit(data))
    hand = _hand_main_scene()
    np.testing.assert_allclose(res.V, hand.V, atol=1e-10)


def test_coherent_source_alpha_forms():
    cases = [
        (0.5, complex(0.5)),
        ([0.3, -0.4], complex(0.3, -0.4)),
        ({"re": 0.3, "im": -0.4}, complex(0.3, -0.4)),
    ]
    for alpha, expected in cases:
        data = {
            "schema": "circuit_v0",
            "nodes": [{"id": "s", "op": "coherent", "params": {"alpha": alpha}}],
            "edges": [],
            "view": {"wigner_mode": 0, "lim": 4.0, "n": 32},
        }
        res = run_circuit(load_circuit(data))
        hand = GaussianState.coherent(expected)
        np.testing.assert_allclose(res.rbar, hand.rbar, atol=1e-10)
        np.testing.assert_allclose(res.V, hand.V, atol=1e-10)
