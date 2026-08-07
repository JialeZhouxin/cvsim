"""L3: Save/Load + Measure once — /sample, homodyne phi, conditioning chain,
singular conditional-state handling (A5/A6)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.lab import CircuitV0Error, load_circuit, run_circuit, sample_circuit

TMSV = {"id": "s", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]}


def _circuit(nodes, *, seed=7, wigner_mode=0):
    return {
        "schema": "circuit_v0",
        "seed": seed,
        "nodes": nodes,
        "edges": [],
        "view": {"wigner_mode": wigner_mode, "lim": 4.0, "n": 32},
        "ui": {},
    }


# --- S1a: homodyne phi ------------------------------------------------------

def test_load_homodyne_phi_default_zero():
    data = _circuit([TMSV, {"id": "h", "op": "homodyne", "params": {}, "mode": 0}])
    res = run_circuit(load_circuit(data))
    assert len(res.measured) == 1
    entry = res.measured[0]
    assert entry["op"] == "measure_homodyne"
    assert entry["phi"] == 0.0
    assert isinstance(entry["outcome"], float)

def test_load_homodyne_phi_kept():
    data = _circuit([TMSV, {"id": "h", "op": "homodyne", "params": {"phi": 1.5}, "mode": 0}])
    res = run_circuit(load_circuit(data))
    assert res.measured[0]["phi"] == 1.5

# --- S1b: sample_circuit core ------------------------------------------------

def test_sample_heterodyne_removes_mode():
    data = _circuit([TMSV, {"id": "h", "op": "heterodyne", "params": {}, "mode": 0}])
    res = sample_circuit(load_circuit(data), np.random.default_rng(7))
    assert len(res.measured) == 1
    entry = res.measured[0]
    assert entry["op"] == "measure_heterodyne"
    assert isinstance(entry["outcome"], list) and len(entry["outcome"]) == 2
    assert res.nmode == 1


def test_sample_homodyne_removes_mode():
    """v1 semantics (design §0): homodyne removes the measured mode."""
    data = _circuit([TMSV, {"id": "h", "op": "homodyne", "params": {}, "mode": 0}])
    res = sample_circuit(load_circuit(data), np.random.default_rng(7))
    assert res.nmode == 1
    entry = res.measured[0]
    assert entry["op"] == "measure_homodyne"
    assert isinstance(entry["outcome"], float)

def test_sample_same_seed_reproducible():
    data = _circuit([TMSV, {"id": "h", "op": "heterodyne", "params": {}, "mode": 0}])
    c = load_circuit(data)
    r1 = sample_circuit(c, np.random.default_rng(42))
    r2 = sample_circuit(c, np.random.default_rng(42))
    assert r1.measured == r2.measured
    np.testing.assert_allclose(r1.rbar, r2.rbar, atol=0.0)
    np.testing.assert_allclose(r1.V, r2.V, atol=0.0)

def test_sample_multi_measurement_chain():
    """homodyne(mode0) → heterodyne(mode1): ordered conditioning chain; each
    measurement removes its mode (v1 semantics) → all modes gone."""
    data = _circuit([
        TMSV,
        {"id": "a", "op": "homodyne", "params": {}, "mode": 0},
        {"id": "b", "op": "heterodyne", "params": {}, "mode": 1},
    ])
    res = sample_circuit(load_circuit(data), np.random.default_rng(7))
    assert [m["op"] for m in res.measured] == ["measure_homodyne", "measure_heterodyne"]
    assert isinstance(res.measured[0]["outcome"], float)
    assert isinstance(res.measured[1]["outcome"], list)
    assert res.nmode == 0  # both measured modes removed
    assert res.wigner is None  # no mode left to view — honest empty result

def test_run_no_rng_deterministic():
    """/run stays pure: no RNG anywhere; /sample does not perturb it."""
    data = _circuit([TMSV, {"id": "l", "op": "loss", "params": {"T": 0.8}, "mode": 0}])
    c = load_circuit(data)
    a = run_circuit(c)
    b = run_circuit(c)
    np.testing.assert_allclose(a.V, b.V, atol=0.0)
    assert a.measured == b.measured
    sample_circuit(c, np.random.default_rng(1))  # must not affect run
    c2 = run_circuit(c)
    np.testing.assert_allclose(c2.V, b.V, atol=0.0)

# --- S1d: singular conditional-state view -----------------------------------

def test_sample_homodyne_removed_mode_not_viewable():
    """v1: homodyne removes the measured mode — no singular state remains.
    The remaining mode is regular and viewable; the measured mode is gone."""
    data = _circuit(
        [TMSV, {"id": "h", "op": "homodyne", "params": {}, "mode": 0}],
        wigner_mode=0,
    )
    res = sample_circuit(load_circuit(data), np.random.default_rng(7))
    assert res.nmode == 1
    assert res.wigner is not None  # remaining mode is regular
    assert res.meters["singular"] is False
    assert res.meters["purity"] is not None
    assert isinstance(res.meters["mean_photon"], float)


def test_sample_homodyne_other_mode_wigner_ok():
    """Unmeasured mode stays positive definite → normal Wigner grid."""
    data = _circuit(
        [TMSV, {"id": "h", "op": "homodyne", "params": {}, "mode": 0}],
        wigner_mode=0,
    )
    res = sample_circuit(load_circuit(data), np.random.default_rng(7))
    assert res.wigner is not None
    assert res.wigner[2].shape == (32, 32)
    assert res.meters["singular"] is False

def test_sample_heterodyne_view_mode_valid():
    data = _circuit([TMSV, {"id": "h", "op": "heterodyne", "params": {}, "mode": 0}])
    res = sample_circuit(load_circuit(data), np.random.default_rng(7))
    assert res.nmode == 1
    assert res.wigner is not None
    assert res.wigner[2].shape == (32, 32)

def test_sample_heterodyne_conditioned_removes_mode_and_keeps_meters():
    """After heterodyne the conditioned state is regular: purity/meters fine."""
    data = _circuit([TMSV, {"id": "h", "op": "heterodyne", "params": {}, "mode": 0}])
    res = sample_circuit(load_circuit(data), np.random.default_rng(7))
    assert res.meters["singular"] is False
    assert res.meters["purity"] is not None


def test_sample_homodyne_phi_controls_variance():
    """PRD §4 #6: squeezed vacuum, homodyne along x vs p — empirical
    outcome variance follows the analytic ½e^{∓2r} (squeeze phi=0:
    V_xx=½e⁻²ʳ, V_pp=½e²ʳ). Sampling must actually use phi.
    (Single-mode homodyne circuit ends with 0 modes — honest empty result.)"""
    from cvsim.gaussian import GaussianState, homodyne_var, squeeze

    r = 0.6
    st = squeeze(GaussianState.vacuum(1), r, 0, 0.0)
    vx_analytic = homodyne_var(st, 0, 0.0)
    vp_analytic = homodyne_var(st, 0, np.pi / 2)
    assert abs(vp_analytic - 0.5 * np.exp(2 * r)) < 1e-12
    assert vp_analytic > vx_analytic

    def shots(phi, n=4000):
        circuit = load_circuit(_circuit([
            {"id": "s", "op": "vacuum", "params": {}},
            {"id": "sq", "op": "squeeze", "params": {"r": r, "phi": 0.0}, "mode": 0},
            {"id": "h", "op": "homodyne", "params": {"phi": phi}, "mode": 0},
        ]))
        out = []
        for k in range(n):
            res = sample_circuit(circuit, np.random.default_rng(k))
            out.append(res.measured[0]["outcome"])
        return np.array(out)

    vx = shots(0.0).var()
    vp = shots(np.pi / 2).var()
    assert abs(vx - vx_analytic) < 0.1 * vx_analytic
    assert abs(vp - vp_analytic) < 0.1 * vp_analytic
    assert vp > vx
