"""L4: F-LAB-SCAN — E_N(r) sweep (/scan) + amplifier + MZ whitelist ops (A7–A9)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from cvsim.gaussian import GaussianState, amplifier, beamsplitter, phase
from cvsim.lab import CircuitV0Error, load_circuit, run_circuit, scan_circuit
from cvsim.lab.server import app

client = TestClient(app)

TMSV = {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]}

_S0 = {"node_id": "s0", "param": "r", "min": 0.0, "max": 1.0, "n": 10, "modes_A": [0]}


def _mz(theta, phi=0.4):
    return {"id": "m", "op": "mz", "params": {"theta": theta, "phi": phi}, "modes": [0, 1]}


def _circuit(nodes, *, wigner_mode=0):
    return {
        "schema": "circuit_v0",
        "seed": 0,
        "nodes": nodes,
        "edges": [],
        "view": {"wigner_mode": wigner_mode, "lim": 4.0, "n": 32},
        "ui": {},
    }

# --- A9: mz ≡ bs + phase + bs ------------------------------------------------

def test_mz_equals_bs_phase_bs_ir():
    theta, phi = 0.37, 0.91
    mz = _circuit([TMSV, _mz(theta, phi)])
    ref = _circuit([
        TMSV,
        {"id": "b1", "op": "beamsplitter", "params": {"theta": theta}, "modes": [0, 1]},
        {"id": "p", "op": "phase", "params": {"phi": phi}, "mode": 0},
        {"id": "b2", "op": "beamsplitter", "params": {"theta": theta}, "modes": [0, 1]},
    ])
    a = run_circuit(load_circuit(mz))
    b = run_circuit(load_circuit(ref))
    np.testing.assert_allclose(a.rbar, b.rbar, atol=1e-12)
    np.testing.assert_allclose(a.V, b.V, atol=1e-12)
    assert a.meters == b.meters

def test_mz_matches_direct_gaussian_composition():
    theta, phi = 0.37, 0.91
    mz = _circuit([TMSV, _mz(theta, phi)])
    res = run_circuit(load_circuit(mz))
    st = GaussianState.tmsv(0.6)
    st = beamsplitter(st, 0, 1, theta, 0.0)
    st = phase(st, phi, 0)
    st = beamsplitter(st, 0, 1, theta, 0.0)
    np.testing.assert_allclose(res.V, st.V, atol=1e-12)
    np.testing.assert_allclose(res.rbar, st.rbar, atol=1e-12)

def test_mz_phi_defaults_zero():
    mz = _circuit([TMSV, {"id": "m", "op": "mz", "params": {"theta": 0.4}, "modes": [0, 1]}])
    res = run_circuit(load_circuit(mz))
    st = GaussianState.tmsv(0.6)
    st = beamsplitter(st, 0, 1, 0.4, 0.0)
    st = beamsplitter(st, 0, 1, 0.4, 0.0)  # phi=0 → phase is identity
    np.testing.assert_allclose(res.V, st.V, atol=1e-12)

def test_mz_local_phase_preserves_logneg():
    """theta=0 → MZ reduces to a local phase on mode 0; E_N invariant under
    LOCAL unitaries, so the TMSV freeze 2r/ln2 survives any phi."""
    mz = _circuit([TMSV, _mz(0.0, 1.2)])
    res = run_circuit(load_circuit(mz))
    assert res.meters["log_negativity"] == pytest.approx(2 * 0.6 / np.log(2), abs=1e-9)
    # sanity: the same node with a non-trivial theta is a GLOBAL unitary → E_N may change
    mz2 = _circuit([TMSV, _mz(0.6, 1.2)])
    en2 = run_circuit(load_circuit(mz2)).meters["log_negativity"]
    assert 0.0 <= en2 < 2 * 0.6 / np.log(2)  # mixing reduces entanglement here

def test_mz_422_non_numeric_theta():
    mz = _circuit([TMSV, {"id": "m", "op": "mz", "params": {"theta": "x"}, "modes": [0, 1]}])
    with pytest.raises(CircuitV0Error, match="must be a number"):
        run_circuit(load_circuit(mz))
    assert client.post("/run", json=mz).status_code == 422

def test_mz_422_requires_two_modes():
    data = _circuit([TMSV, _mz(0.4)], wigner_mode=0)
    del data["nodes"][1]["modes"]
    with pytest.raises(CircuitV0Error, match="requires 'modes'"):
        load_circuit(data)

# --- A8: amplifier -----------------------------------------------------------

def test_amplifier_op_matches_direct():
    data = _circuit([
        {"id": "s", "op": "vacuum", "params": {}},
        {"id": "a", "op": "amplifier", "params": {"G": 2.0}, "mode": 0},
    ])
    res = run_circuit(load_circuit(data))
    st = amplifier(GaussianState.vacuum(1), 2.0, 0, 0.0)
    np.testing.assert_allclose(res.rbar, st.rbar, atol=1e-12)
    np.testing.assert_allclose(res.V, st.V, atol=1e-12)

def test_amplifier_nbar_advanced_default_zero():
    """nbar absent → 0 (quantum-limited): amplified vacuum ⟨n⟩ = G−1."""
    data = _circuit([
        {"id": "s", "op": "vacuum", "params": {}},
        {"id": "a", "op": "amplifier", "params": {"G": 2.0}, "mode": 0},
    ])
    res = run_circuit(load_circuit(data))
    assert res.meters["mean_photon"] == pytest.approx(1.0, abs=1e-9)  # G−1

def test_amplifier_nbar_explicit_matches_direct():
    data = _circuit([
        {"id": "s", "op": "vacuum", "params": {}},
        {"id": "a", "op": "amplifier", "params": {"G": 3.0, "nbar": 0.5}, "mode": 0},
    ])
    res = run_circuit(load_circuit(data))
    st = amplifier(GaussianState.vacuum(1), 3.0, 0, 0.5)
    np.testing.assert_allclose(res.V, st.V, atol=1e-12)

def test_amplifier_422_g_lt_1():
    data = _circuit([
        {"id": "s", "op": "vacuum", "params": {}},
        {"id": "a", "op": "amplifier", "params": {"G": 0.5}, "mode": 0},
    ])
    with pytest.raises(ValueError, match="G must be >= 1"):  # library guard
        run_circuit(load_circuit(data))
    r = client.post("/run", json=data)
    assert r.status_code == 422

def test_amplifier_422_negative_nbar():
    data = _circuit([
        {"id": "s", "op": "vacuum", "params": {}},
        {"id": "a", "op": "amplifier", "params": {"G": 2.0, "nbar": -1}, "mode": 0},
    ])
    with pytest.raises(ValueError, match="nbar"):
        run_circuit(load_circuit(data))
    assert client.post("/run", json=data).status_code == 422

def test_amplifier_422_missing_G():
    data = _circuit([
        {"id": "s", "op": "vacuum", "params": {}},
        {"id": "a", "op": "amplifier", "params": {}, "mode": 0},
    ])
    with pytest.raises(CircuitV0Error, match="G must be a number"):
        run_circuit(load_circuit(data))
    assert client.post("/run", json=data).status_code == 422

# --- A7: /scan analytic E_N(r) ------------------------------------------------

def test_scan_tmsv_r_matches_analytic_2r_ln2():
    data = _circuit([TMSV])
    sweep = {"node_id": "s0", "param": "r", "min": 0.1, "max": 1.0, "n": 20, "modes_A": [0]}
    res = scan_circuit(load_circuit(data), sweep)
    assert res["node_id"] == "s0" and res["param"] == "r"
    assert res["min"] == 0.1 and res["max"] == 1.0 and res["n"] == 20
    assert res["modes_A"] == [0]
    xs, ys = np.asarray(res["xs"]), np.asarray(res["ys"])
    assert len(xs) == 20 and len(ys) == 20
    np.testing.assert_allclose(xs, np.linspace(0.1, 1.0, 20), atol=1e-12)
    np.testing.assert_allclose(ys, 2 * xs / np.log(2), atol=1e-6)  # A7 analytic

def test_scan_endpoint_tmsv():
    body = _circuit([TMSV])
    body["sweep"] = {"node_id": "s0", "param": "r", "min": 0.0, "max": 2.0, "n": 25, "modes_A": [0]}
    r = client.post("/scan", json=body)
    assert r.status_code == 200
    j = r.json()
    xs, ys = np.asarray(j["xs"]), np.asarray(j["ys"])
    np.testing.assert_allclose(ys, 2 * xs / np.log(2), atol=1e-6)

def test_scan_pure_deterministic_no_rng():
    data = _circuit([TMSV])
    sweep = {"node_id": "s0", "param": "r", "min": 0.1, "max": 1.0, "n": 10, "modes_A": [0]}
    c = load_circuit(data)
    a = scan_circuit(c, sweep)
    b = scan_circuit(c, sweep)
    assert a["xs"] == b["xs"]
    assert a["ys"] == b["ys"]

def test_scan_loss_t_endpoint_t1_identity():
    body = _circuit([TMSV, {"id": "l", "op": "loss", "params": {"T": 0.8}, "mode": 0}])
    body["sweep"] = {"node_id": "l", "param": "T", "min": 0.2, "max": 1.0, "n": 20, "modes_A": [0]}
    r = client.post("/scan", json=body)
    assert r.status_code == 200
    j = r.json()
    assert len(j["ys"]) == 20
    assert j["ys"][-1] == pytest.approx(2 * 0.6 / np.log(2), abs=1e-6)  # T=1 identity

def test_scan_mz_theta_endpoints_and_symmetry():
    """MZ(0)=identity / MZ(π)=global −I: endpoints keep E_N=2r/ln2; the curve
    is symmetric in theta→π−theta (BS(π−θ) = −BS(θ) up to a global phase)."""
    body = _circuit([TMSV, _mz(0.5, 0.8)])
    body["sweep"] = {"node_id": "m", "param": "theta",
                     "min": 0.0, "max": np.pi, "n": 16, "modes_A": [0]}
    r = client.post("/scan", json=body)
    assert r.status_code == 200
    ys = np.asarray(r.json()["ys"])
    assert ys[0] == pytest.approx(2 * 0.6 / np.log(2), abs=1e-6)  # theta=0 identity
    assert ys[-1] == pytest.approx(2 * 0.6 / np.log(2), abs=1e-6)  # theta=π global −I
    np.testing.assert_allclose(ys, ys[::-1], atol=1e-6)  # theta ↔ π−theta symmetry
    assert np.min(ys) < 2 * 0.6 / np.log(2)  # non-trivial mixing in between
    assert np.all(ys >= -1e-9)

def test_scan_amplifier_g_monotone():
    body = _circuit([
        TMSV,
        {"id": "a", "op": "amplifier", "params": {"G": 1.0}, "mode": 0},
    ])
    body["sweep"] = {"node_id": "a", "param": "G", "min": 1.0, "max": 3.0, "n": 10, "modes_A": [0]}
    r = client.post("/scan", json=body)
    assert r.status_code == 200
    ys = np.asarray(r.json()["ys"])
    assert ys[0] == pytest.approx(2 * 0.6 / np.log(2), abs=1e-6)  # G=1 identity
    assert np.all(np.diff(ys) <= 1e-9)  # local channel: E_N non-increasing in G

def test_scan_3mode_modes_a():
    body = _circuit([
        {"id": "s", "op": "vacuum", "params": {"nmode": 3}},
        {"id": "sq", "op": "squeeze", "params": {"r": 0.4}, "mode": 0},
    ])
    body["sweep"] = {"node_id": "sq", "param": "r",
                     "min": 0.1, "max": 1.0, "n": 8, "modes_A": [0, 1]}
    r = client.post("/scan", json=body)
    assert r.status_code == 200
    j = r.json()
    assert j["modes_A"] == [0, 1]
    ys = np.asarray(j["ys"])
    np.testing.assert_allclose(ys, 0.0, atol=1e-9)  # product state, cut {0,1}|{2}: E_N=0

def test_scan_1mode_circuit_rejected():
    body = _circuit([{"id": "s", "op": "vacuum", "params": {}}])
    body["sweep"] = {"node_id": "s", "param": "nmode", "min": 1, "max": 2, "n": 5, "modes_A": [0]}
    r = client.post("/scan", json=body)
    assert r.status_code == 422  # nmode not sweepable either way

# --- 422 validation matrix ----------------------------------------------------

@pytest.mark.parametrize("sweep,msg", [
    ({**_S0, "node_id": "nope"}, "unknown node_id"),
    ({**_S0, "param": "alpha"}, "not sweepable"),
    ({**_S0, "min": 1.0, "max": 0.0}, "min must be < max"),
    ({**_S0, "n": 1}, r"int in \[2, 200\]"),
    ({**_S0, "n": 201}, r"int in \[2, 200\]"),
    ({**_S0, "n": 10.5}, r"int in \[2, 200\]"),
    ({**_S0, "modes_A": []}, "non-empty"),
    ({**_S0, "modes_A": [0, 1]}, "at most nmode-1"),
    ({**_S0, "modes_A": [2]}, "out of range"),
    ({**_S0, "min": "x"}, "must be a number"),
    ({**_S0, "min": float("inf")}, "must be finite"),
    ({**_S0, "max": float("nan")}, "must be finite"),
])
def test_scan_422_matrix_ir(sweep, msg):
    data = _circuit([TMSV])
    with pytest.raises(CircuitV0Error, match=msg):
        scan_circuit(load_circuit(data), sweep)

def test_scan_422_duplicate_modes_a_3mode():
    data = _circuit([
        {"id": "s", "op": "vacuum", "params": {"nmode": 3}},
        {"id": "sq", "op": "squeeze", "params": {"r": 0.4}, "mode": 0},
    ])
    sweep = {"node_id": "sq", "param": "r", "min": 0.1, "max": 1.0, "n": 8, "modes_A": [0, 0]}
    with pytest.raises(CircuitV0Error, match="duplicate"):
        scan_circuit(load_circuit(data), sweep)

def test_scan_rejects_coherent_alpha():
    data = _circuit([{"id": "s", "op": "coherent", "params": {"alpha": 1.0}}])
    sweep = {"node_id": "s", "param": "alpha", "min": 0.0, "max": 1.0, "n": 10, "modes_A": [0]}
    with pytest.raises(CircuitV0Error, match="not sweepable"):
        scan_circuit(load_circuit(data), sweep)
    body = _circuit([{"id": "s", "op": "coherent", "params": {"alpha": 1.0}}])
    body["sweep"] = sweep
    assert client.post("/scan", json=body).status_code == 422

def test_scan_rejects_measurement_nodes():
    data = _circuit([
        TMSV,
        {"id": "h", "op": "homodyne", "params": {}, "mode": 0},
    ])
    sweep = {"node_id": "s0", "param": "r", "min": 0.0, "max": 1.0, "n": 10, "modes_A": [0]}
    with pytest.raises(CircuitV0Error, match="measurement node"):
        scan_circuit(load_circuit(data), sweep)
    data["sweep"] = sweep
    r = client.post("/scan", json=data)
    assert r.status_code == 422
    assert "measurement" in r.json()["detail"]

def test_scan_endpoint_422_missing_sweep():
    r = client.post("/scan", json=_circuit([TMSV]))
    assert r.status_code == 422
    assert "sweep" in r.json()["detail"]

def test_scan_endpoint_422_bad_circuit():
    body = {"schema": "circuit_v0", "nodes": [{"id": "x", "op": "cz", "params": {}}]}
    body["sweep"] = {"node_id": "x", "param": "r", "min": 0.0, "max": 1.0, "n": 10, "modes_A": [0]}
    assert client.post("/scan", json=body).status_code == 422

def test_scan_does_not_mutate_circuit():
    """Sweep config never writes back: /scan leaves the circuit unchanged."""
    data = _circuit([TMSV])
    c = load_circuit(data)
    before = {n.id: dict(n.params) for n in c.core.ops}
    sweep = {"node_id": "s0", "param": "r", "min": 0.1, "max": 1.0, "n": 5, "modes_A": [0]}
    scan_circuit(c, sweep)
    assert {n.id: dict(n.params) for n in c.core.ops} == before


def test_scan_extreme_g_never_leaks_nan():
    """Reviewer finding: non-finite logneg (e.g. G→1e300 noise) must become null,
    never NaN (NaN would 500 through Starlette's allow_nan=False)."""
    body = _circuit([
        TMSV,
        {"id": "a0", "op": "amplifier", "params": {"G": 1.0}, "mode": 0},
    ])
    body["sweep"] = {
        "node_id": "a0", "param": "G", "min": 1.0, "max": 1e300, "n": 5, "modes_A": [0]
    }
    r = client.post("/scan", json=body)
    assert r.status_code == 200
    for y in r.json()["ys"]:
        assert y is None or (isinstance(y, float) and math.isfinite(y))
