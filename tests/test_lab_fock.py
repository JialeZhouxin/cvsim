"""F7 S4: Fock Lab backend — golden HOM, sample seed repro, batch stats,
422 guards, leakage meter, gaussian default regression."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from cvsim.fock import FockCircuit
from cvsim.lab.server import app

client = TestClient(app)

TOL = 1e-12


def _hom_v1(**over):
    """HOM scene: nmode=2, initial [1,1], BS(π/4), cutoff 10 (A1 main scene)."""
    data = {
        "schema": "circuit_v1",
        "backend": "fock",
        "nmode": 2,
        "cutoff": 10,
        "initial": [1, 1],
        "seed": 0,
        "ops": [
            {"id": "bs", "op": "beamsplitter", "modes": [0, 1], "params": {"theta": np.pi / 4}},
        ],
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 64, "joint_modes": [0, 1]},
        "ui": {},
    }
    data.update(over)
    return data


def _script_hom():
    """Equivalent hand-written FockCircuit (golden reference)."""
    c = FockCircuit(2, cutoff=10, initial=[1, 1])
    c.beamsplitter(0, 1, theta=np.pi / 4)
    return c.run()


# --- golden equivalence (A1) -------------------------------------------------


def test_hom_run_matches_script_and_bunching():
    r = client.post("/run", json=_hom_v1())
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "fock"
    assert body["nmode"] == 2
    assert body["cutoffs"] == [10, 10]
    st = _script_hom()
    joint = np.array(body["joint"]["grid"], dtype=float)
    assert np.allclose(joint, np.abs(st.amps) ** 2, atol=TOL)
    # A1: P(1,1) ≈ 0 — two-photon bunching
    assert joint[1, 1] < TOL
    # single-mode marginal: P(1) = 0 too (|2,0⟩/|0,2⟩ superposition)
    dist = np.array(body["dist"]["probs"], dtype=float)
    assert dist[1] < TOL
    assert body["dist"]["mode"] == 0
    # joint heatmap cap: ≤ 30×30
    assert len(joint) <= 30 and len(joint[0]) <= 30


def test_hom_wigner_nonnull_and_grid():
    body = client.post("/run", json=_hom_v1()).json()
    w = body["wigner"]
    assert w is not None
    assert len(w["x"]) == len(w["p"]) == len(w["W"]) == 64
    assert np.all(np.isfinite(w["W"]))


def test_hom_meters_mean_photon_and_purity():
    body = client.post("/run", json=_hom_v1()).json()
    m = body["meters"]
    assert abs(m["mean_photon"] - 2.0) < TOL  # two photons conserved by BS
    assert m["mean_photon_per_mode"] == pytest.approx([1.0, 1.0], abs=TOL)
    assert m["purity"] == 1.0  # pure state
    assert m["leakage"] == 0.0  # |1,1⟩ confined: no truncation error


def test_leakage_analytic_for_displaced_coherent():
    """displace α=1 → coherent tail = 1 − Γ(N,|α|²) (factory analytic)."""
    from scipy.special import gammainc

    data = {
        "schema": "circuit_v1",
        "backend": "fock",
        "nmode": 1,
        "cutoff": 10,
        "ops": [{"id": "d", "op": "displace", "modes": [0], "params": {"alpha": [1.0, 0.0]}}],
        "view": {"wigner_mode": 0},
    }
    body = client.post("/run", json=data).json()
    leak = body["meters"]["leakage"]
    # circuit state carries no factory tail → higher-cutoff comparison estimate
    # (displace is a gate, not a factory) — must agree with the analytic tail.
    # Regularized LOWER incomplete gamma gammainc(10, |α|²) IS the tail mass
    # Σ_{n≥10} e^{−|α|²}|α|^{2n}/n! for a coherent state.
    expected = float(gammainc(10, 1.0))
    assert leak == pytest.approx(expected, rel=1e-6)
    # cutoff 20 → leakage shrinks (meter responds to cutoff)
    data2 = {**data, "cutoff": 20}
    leak2 = client.post("/run", json=data2).json()["meters"]["leakage"]
    assert leak2 < leak


def test_leakage_null_for_density_states():
    """Channels → density: leakage honestly null (never fabricated)."""
    data = {
        "schema": "circuit_v1",
        "backend": "fock",
        "nmode": 1,
        "cutoff": 10,
        "ops": [{"id": "l", "op": "loss", "modes": [0], "params": {"eta": 0.8}}],
        "view": {"wigner_mode": 0},
    }
    body = client.post("/run", json=data).json()
    assert body["meters"]["leakage"] is None


def test_kerr_cat_scene_runs():
    """A2: displace(√2) + kerr(π/2) → bimodal cat; Wigner computed."""
    data = {
        "schema": "circuit_v1",
        "backend": "fock",
        "nmode": 1,
        "cutoff": 12,
        "ops": [
            {"id": "d", "op": "displace", "modes": [0], "params": {"alpha": [np.sqrt(2.0), 0.0]}},
            {"id": "k", "op": "kerr", "modes": [0], "params": {"chi": np.pi / 2}},
        ],
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 32},
    }
    r = client.post("/run", json=data)
    assert r.status_code == 200
    body = r.json()
    assert body["wigner"] is not None
    # Diagonal unitary: K(χ) does NOT change the photon-number distribution —
    # P(0) = e^{−|α|²} = e^{−2} exactly as for the input coherent state.
    # The cat lives in the Wigner function (interference negativity).
    dist = np.array(body["dist"]["probs"], dtype=float)
    assert dist[0] == pytest.approx(np.exp(-2.0), rel=1e-3)
    W = np.array(body["wigner"]["W"], dtype=float)
    assert np.min(W) < 0  # even-cat interference: Wigner goes negative


# --- sampling (A3, R4) -------------------------------------------------------


def test_sample_seed_reproduction():
    data = _hom_v1(
        ops=[
            {"id": "m", "op": "measure_pnr", "modes": [0], "params": {"name": "n0"}},
        ],
        seed=42,
    )
    r1 = client.post("/sample", json=data)
    r2 = client.post("/sample", json=data)
    assert r1.status_code == 200 and r2.status_code == 200
    b1, b2 = r1.json(), r2.json()
    assert b1["seed"] == 42 and b1["sampled"] is True
    assert b1["measured"] == b2["measured"]  # same seed → same outcomes
    assert len(b1["measured"]) == 1
    assert b1["measured"][0]["op"] == "measure_pnr"
    assert isinstance(b1["measured"][0]["outcome"], int)


def test_run_deterministic_for_same_payload():
    data = _hom_v1(
        ops=[
            {"id": "m", "op": "measure_pnr", "modes": [0], "params": {"name": "n0"}},
        ],
    )
    b1 = client.post("/run", json=data).json()
    b2 = client.post("/run", json=data).json()
    assert b1["measured"] == b2["measured"]


# --- batch (R4) --------------------------------------------------------------


def test_batch_counts_match_theory_statistically():
    body = client.post("/batch", json={**_hom_v1(), "shots": 1000})
    assert body.status_code == 200
    b = body.json()
    assert b["shots"] == 1000 and b["seed"] == 0
    assert b["modes"] == [0, 1]
    assert sum(b["counts"]) == 1000
    st = _script_hom()
    theory = np.abs(st.amps) ** 2
    counts = np.array(b["counts"], dtype=float).reshape(b["shape"])
    freq = counts / counts.sum()
    # 1000 shots: |freq − p| well within 5σ (σ ≤ 0.5/√1000 ≈ 0.0158)
    assert np.max(np.abs(freq - theory)) < 0.06


def test_batch_single_mode_when_no_joint_modes():
    data = _hom_v1(view={"wigner_mode": 0, "lim": 5.0, "n": 64})
    b = client.post("/batch", json={**data, "shots": 1000}).json()
    assert b["modes"] == [0]
    assert len(b["counts"]) == 10
    p = np.abs(_script_hom().amps) ** 2
    theory = p.sum(axis=1)
    freq = np.array(b["counts"], dtype=float) / 1000
    assert np.max(np.abs(freq - theory)) < 0.06


def test_batch_with_measurement_chain():
    data = _hom_v1(
        ops=[
            {"id": "m", "op": "measure_pnr", "modes": [0], "params": {"name": "n0"}},
        ],
    )
    b = client.post("/batch", json={**data, "shots": 50})
    assert b.status_code == 200
    body = b.json()
    assert body["shots"] == 50
    assert body["measured_names"] == ["n0"]
    assert sum(body["counts"].values()) == 50


# --- 422 guards --------------------------------------------------------------


def test_422_bad_initial():
    cases = [
        {**_hom_v1(), "initial": [1, 10]},  # n >= cutoff
        {**_hom_v1(), "initial": [1]},  # wrong length
        {**_hom_v1(), "initial": [1, -1]},  # negative
        {**_hom_v1(), "initial": "11"},  # not a list
        {**_hom_v1(), "initial": [1.5, 0]},  # non-int
    ]
    for data in cases:
        r = client.post("/run", json=data)
        assert r.status_code == 422, r.json()
        assert "initial" in r.json()["detail"]


def test_422_op_outside_fock_whitelist():
    for op, params, modes in [
        ("interferometer", {"U": [[1, 0], [0, 1]]}, [0, 1]),
        ("apply_unitary", {"U": [[1]]}, [0]),
        ("apply_kraus", {"kraus_ops": [[[[1, 0], [0, 0]]]]}, [0]),
        ("fourier", {}, [0]),
    ]:
        data = {
            "schema": "circuit_v1",
            "backend": "fock",
            "nmode": 2,
            "ops": [{"id": "x", "op": op, "modes": modes, "params": params}],
        }
        r = client.post("/run", json=data)
        assert r.status_code == 422, r.json()
        assert "whitelist" in r.json()["detail"]


def test_422_bad_cutoff_and_batch_shots():
    r = client.post("/run", json={**_hom_v1(), "cutoff": 0})
    assert r.status_code == 422
    r = client.post("/batch", json={**_hom_v1(), "shots": 0})
    assert r.status_code == 422
    r = client.post("/batch", json={**_hom_v1(), "shots": 1000001})
    assert r.status_code == 422


def test_422_scan_on_fock():
    r = client.post(
        "/scan",
        json={
            **_hom_v1(),
            "sweep": {
                "node_id": "bs",
                "param": "theta",
                "min": 0,
                "max": 1,
                "n": 5,
            },
        },
    )
    assert r.status_code == 422
    assert "fock" in r.json()["detail"]


def test_422_batch_on_gaussian():
    data = {
        "schema": "circuit_v1",
        "nmode": 2,
        "ops": [{"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.4, "phi": 0.0}}],
    }
    r = client.post("/batch", json=data)
    assert r.status_code == 422
    assert "fock" in r.json()["detail"]


# --- gaussian default regression (A4) ----------------------------------------


def test_backend_default_gaussian_regression():
    """Old gaussian JSON (no backend field) behaves exactly as before."""
    data = {
        "schema": "circuit_v1",
        "nmode": 2,
        "seed": 0,
        "ops": [
            {"id": "s", "op": "two_mode_squeeze", "modes": [0, 1], "params": {"r": 0.6}},
            {"id": "l", "op": "loss", "modes": [0], "params": {"T": 0.8, "nbar": 0.0}},
            {
                "id": "bs",
                "op": "beamsplitter",
                "modes": [0, 1],
                "params": {"theta": np.pi / 4, "phi": 0.0},
            },
        ],
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
    }
    r = client.post("/run", json=data)
    assert r.status_code == 200
    body = r.json()
    assert "backend" not in body  # gaussian payload unchanged
    assert body["nmode"] == 2
    assert len(body["V"]) == 4
    assert body["wigner"] is not None


def test_backend_gaussian_ignores_initial_field():
    data = {
        "schema": "circuit_v1",
        "backend": "gaussian",
        "initial": [1, 1],
        "nmode": 2,
        "ops": [{"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1, "phi": 0.0}}],
        "view": {"wigner_mode": 0},
    }
    assert client.post("/run", json=data).status_code == 200


def test_gaussian_backend_rejects_measure_pnr():
    data = {
        "schema": "circuit_v1",
        "nmode": 1,
        "ops": [{"id": "m", "op": "measure_pnr", "modes": [0], "params": {"name": "n"}}],
    }
    assert client.post("/run", json=data).status_code == 422


def test_measure_heterodyne_fock_conditions_and_keeps_state():
    """Fock heterodyne: outcome vector in payload, conditioned state honest."""
    data = {
        "schema": "circuit_v1",
        "backend": "fock",
        "nmode": 1,
        "cutoff": 10,
        "seed": 7,
        "ops": [
            {"id": "d", "op": "displace", "modes": [0], "params": {"alpha": [1.0, 0.0]}},
            {"id": "m", "op": "measure_heterodyne", "modes": [0], "params": {"name": "b"}},
        ],
        "view": {"wigner_mode": 0},
    }
    r = client.post("/sample", json=data)
    assert r.status_code == 200
    body = r.json()
    assert body["measured"][0]["op"] == "measure_heterodyne"
    assert isinstance(body["measured"][0]["outcome"], list)
    assert len(body["measured"][0]["outcome"]) == 2


def test_fock_loss_and_squeeze_run():
    """UI-shaped fock path: loss speaks eta, squeeze has only r (ops.js maps
    T→eta and drops nbar/phi before sending — guard the backend contract)."""
    data = {
        "schema": "circuit_v1",
        "backend": "fock",
        "nmode": 2,
        "cutoff": 10,
        "initial": [1, 0],
        "ops": [
            {"id": "l", "op": "loss", "modes": [0], "params": {"eta": 0.8}},
            {"id": "s", "op": "squeeze", "modes": [1], "params": {"r": 0.3}},
        ],
        "view": {"wigner_mode": 0, "joint_modes": [0, 1]},
    }
    r = client.post("/run", json=data)
    assert r.status_code == 200, r.json()
    body = r.json()
    assert body["meters"]["leakage"] is None  # channels → density: honest null
    assert body["joint"] is not None


def test_422_malformed_ops_list_not_500():
    """Non-dict op entries → 422 whitelist message, never a 500 traceback."""
    data = {
        "schema": "circuit_v1",
        "backend": "fock",
        "nmode": 2,
        "ops": ["garbage"],
    }
    r = client.post("/run", json=data)
    assert r.status_code == 422
    assert "whitelist" in r.json()["detail"]


def test_batch_non_dict_body_422_not_500():
    # FastAPI rejects a non-object body at the framework layer (dict_type 422);
    # the server-side isinstance guard keeps direct calls honest too.
    r = client.post("/batch", json=["garbage"])
    assert r.status_code == 422
