"""circuit_v0 → circuit_v1 translation goldens (ADR-0003 / serialize-ir PRD).

Coverage: main-script scene, multi-source, coherent source, param rename
(phase phi→theta), measurement name synthesis, v1 logical-index semantics
(measurement removes modes; referencing a measured mode is an error).
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import GaussianState
from cvsim.lab import (
    CircuitV0Error,
    load_circuit,
    run_circuit,
    sample_circuit,
    translate_v0,
)
from cvsim.gaussian.ir import validate_ir


def _v0(nodes, **extra):
    out = {"schema": "circuit_v0", "nodes": nodes}
    out.update(extra)
    return out


def test_translate_main_scene_structure():
    """Main script: tmsv → two_mode_squeeze with source id, mode→modes."""
    v1 = translate_v0(_v0([
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "l0", "op": "loss", "params": {"T": 0.8}, "mode": 0},
        {"id": "h0", "op": "heterodyne", "params": {}, "mode": 0},
    ]))
    assert v1["schema"] == "circuit_v1"
    assert v1["nmode"] == 2
    assert [(o["op"], list(o["modes"])) for o in v1["ops"]] == [
        ("two_mode_squeeze", [0, 1]),
        ("loss", [0]),
        ("measure_heterodyne", [0]),
    ]
    assert v1["ops"][0]["id"] == "s0"
    # measurement name synthesized from v0 id
    assert v1["ops"][2]["params"]["name"] == "h0"
    validate_ir(v1)  # translated output is valid v1


def test_translate_phase_phi_to_theta():
    v1 = translate_v0(_v0([
        {"id": "s", "op": "vacuum", "params": {"nmode": 2}},
        {"id": "p", "op": "phase", "params": {"phi": 1.3}, "mode": 0},
    ]))
    assert v1["ops"][0]["params"] == {"theta": 1.3}


def test_translate_coherent_source_to_displace():
    v1 = translate_v0(_v0([
        {"id": "c", "op": "coherent", "params": {"alpha": [0.3, -0.4]}},
    ]))
    assert v1["nmode"] == 1
    assert v1["ops"] == [{
        "id": "c", "op": "displace", "modes": [0],
        "params": {"alpha": [0.3, -0.4]},
    }]


def test_translate_multi_source_vacuum_and_tmsv():
    """vacuum + tmsv appended → 3 modes; tmsv pair block-local at [1,2]."""
    v1 = translate_v0(_v0([
        {"id": "a", "op": "vacuum", "params": {}},
        {"id": "b", "op": "tmsv", "params": {"r": 0.5}, "modes": [1, 2]},
    ]))
    assert v1["nmode"] == 3
    assert v1["ops"] == [{
        "id": "b", "op": "two_mode_squeeze", "modes": [1, 2], "params": {"r": 0.5},
    }]
    res = run_circuit(load_circuit(_v0([
        {"id": "a", "op": "vacuum", "params": {}},
        {"id": "b", "op": "tmsv", "params": {"r": 0.5}, "modes": [1, 2]},
    ])))
    assert res.nmode == 3
    assert abs(res.V[1, 2]) > 0  # x1·x2 entangled (tmsv pair)
    assert np.abs(res.V[0, 1:]).max() < 1e-12  # vacuum mode uncorrelated


def test_translate_seed_view_ui_passthrough_edges_dropped():
    v1 = translate_v0(_v0(
        [{"id": "s", "op": "vacuum", "params": {}}],
        seed=42,
        view={"wigner_mode": 0, "lim": 4.0, "n": 32},
        ui={"pixels": [1, 2]},
        edges=[{"from": "a", "to": "b"}],
    ))
    assert v1["seed"] == 42
    assert v1["view"] == {"wigner_mode": 0, "lim": 4.0, "n": 32}
    assert v1["ui"] == {"pixels": [1, 2]}
    assert "edges" not in v1


def test_golden_main_scene_logneg_freeze():
    """A3 freeze: T=1 TMSV E_N = -log2(e^{-2r}) = 2r/ln2; loss 0.8 lowers it."""
    c = load_circuit(_v0([
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "l0", "op": "loss", "params": {"T": 1.0}, "mode": 0},
        {"id": "l1", "op": "loss", "params": {"T": 1.0}, "mode": 1},
    ]))
    res = run_circuit(c)
    assert res.meters["log_negativity"] == pytest.approx(
        2 * 0.6 / np.log(2), abs=1e-9
    )
    c2 = load_circuit(_v0([
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "l0", "op": "loss", "params": {"T": 0.8}, "mode": 0},
    ]))
    en2 = run_circuit(c2).meters["log_negativity"]
    assert 0.0 < en2 < 2 * 0.6 / np.log(2)


def test_v1_logical_index_semantics_after_heterodyne():
    """v1 (design §0): after heterodyne removes mode 0, a later op on logical
    mode 1 acts on the remaining physical mode 0 (compile.py semantics)."""
    data = _v0([
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "h0", "op": "heterodyne", "params": {}, "mode": 0},
        {"id": "d1", "op": "displace", "params": {"alpha": 1.0}, "mode": 1},
    ])
    res = run_circuit(load_circuit(data))
    assert res.nmode == 1
    # displace on logical 1 (the survivor) → rbar nonzero
    assert np.abs(res.rbar).max() > 0.1


def test_reference_measured_mode_rejected():
    """Op referencing an already-measured logical mode → CircuitV0Error."""
    data = _v0([
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "h0", "op": "heterodyne", "params": {}, "mode": 0},
        {"id": "d0", "op": "displace", "params": {"alpha": 1.0}, "mode": 0},
    ])
    with pytest.raises(CircuitV0Error, match="already measured/removed"):
        run_circuit(load_circuit(data))


def test_homodyne_translated_removes_mode():
    """v1 semantic unification: homodyne removes its mode (was kept in v0)."""
    data = _v0([
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "h0", "op": "homodyne", "params": {"phi": 0.0}, "mode": 0},
    ])
    res = run_circuit(load_circuit(data))
    assert res.nmode == 1
    assert res.measured[0]["op"] == "measure_homodyne"
    # remaining mode regular → Wigner viewable
    assert res.wigner is not None


def test_v1_native_roundtrip_via_core():
    """v1 JSON → validate → run equals a v0 file with the same physics."""
    v1 = {
        "schema": "circuit_v1", "nmode": 2, "seed": 0,
        "ops": [
            {"id": "s0", "op": "two_mode_squeeze", "modes": [0, 1], "params": {"r": 0.6}},
            {"id": "l0", "op": "loss", "modes": [0], "params": {"T": 0.8}},
            {"id": "l1", "op": "loss", "modes": [1], "params": {"T": 0.8}},
            {"id": "bs", "op": "beamsplitter", "modes": [0, 1],
             "params": {"theta": np.pi / 4}},
        ],
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
        "ui": {},
    }
    a = run_circuit(load_circuit(v1))
    v0 = _v0([
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "l0", "op": "loss", "params": {"T": 0.8}, "mode": 0},
        {"id": "l1", "op": "loss", "params": {"T": 0.8}, "mode": 1},
        {"id": "bs", "op": "beamsplitter", "params": {"theta": np.pi / 4}, "modes": [0, 1]},
    ])
    b = run_circuit(load_circuit(v0))
    np.testing.assert_allclose(a.V, b.V, atol=1e-12)
    np.testing.assert_allclose(a.rbar, b.rbar, atol=1e-12)
    assert a.meters["log_negativity"] == pytest.approx(
        b.meters["log_negativity"], abs=1e-12
    )


def test_lab_whitelist_rejects_core_only_ops():
    """v1 files may carry core ops; Lab UI rejects them (whitelist = UI)."""
    v1 = {
        "schema": "circuit_v1", "nmode": 2,
        "ops": [{"op": "cz", "modes": [0, 1], "params": {"weight": 0.5}}],
    }
    with pytest.raises(CircuitV0Error, match="not in Lab whitelist"):
        load_circuit(v1)


def test_sample_conditioning_chain_translated():
    """Translated measurement chain samples in order with conditioning."""
    data = _v0([
        {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
        {"id": "h0", "op": "heterodyne", "params": {}, "mode": 0},
    ])
    c = load_circuit(data)
    r1 = sample_circuit(c, np.random.default_rng(7))
    r2 = sample_circuit(c, np.random.default_rng(7))
    assert r1.measured == r2.measured
    assert r1.nmode == 1
    assert r1.meters["singular"] is False
