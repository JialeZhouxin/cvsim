"""F-LAB-API + F-LAB-WIGNER: FastAPI /run, /health, A4 + A8 guards."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from cvsim.gaussian import GaussianState
from cvsim.lab.server import app
from cvsim.wigner import wigner_grid

client = TestClient(app)

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
    "ui": {},
}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["schema"] == "circuit_v0"


def test_run_main_scene():
    r = client.post("/run", json=MAIN_SCENE)
    assert r.status_code == 200
    body = r.json()
    assert body["nmode"] == 2
    assert len(body["V"]) == 4
    w = body["wigner"]
    assert len(w["x"]) == 64 and len(w["p"]) == 64 and len(w["W"]) == 64
    expected_meters = {"purity", "mean_photon", "mean_photon_per_mode", "log_negativity"}
    assert set(body["meters"]) >= expected_meters
    assert body["measured"] == []


def test_run_422_unknown_op():
    data = {
        "schema": "circuit_v0",
        "nodes": [{"id": "x", "op": "cz", "params": {}}],
    }
    r = client.post("/run", json=data)
    assert r.status_code == 422
    assert "unknown op" in r.json()["detail"]


def test_run_422_bad_view():
    data = dict(MAIN_SCENE, view={"wigner_mode": 2, "lim": 5.0, "n": 64})
    r = client.post("/run", json=data)
    assert r.status_code == 422
    assert "wigner_mode" in r.json()["detail"]


def test_run_422_library_guard_value_error():
    """Library-side guards (loss T out of range) must map to 422, not 500."""
    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "s", "op": "vacuum", "params": {}},
            {"id": "l", "op": "loss", "params": {"T": 1.5}, "mode": 0},
        ],
        "edges": [],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 32},
    }
    r = client.post("/run", json=data)
    assert r.status_code == 422


def test_wigner_vacuum_matches_direct():  # A4: Wigner(vacuum) == direct wigner_grid
    data = {
        "schema": "circuit_v0",
        "nodes": [{"id": "s", "op": "vacuum", "params": {}}],
        "edges": [],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 48},
    }
    r = client.post("/run", json=data)
    assert r.status_code == 200
    body = r.json()
    _, _, W_direct = wigner_grid(GaussianState.vacuum(1), lim=4.0, n=48)
    np.testing.assert_allclose(np.asarray(body["wigner"]["W"]), W_direct, atol=1e-10)


def test_run_heterodyne_removes_mode_and_remaps_view():
    data = {
        "schema": "circuit_v0",
        "nodes": [
            {"id": "s", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
            {"id": "h", "op": "heterodyne", "params": {}, "mode": 0},
        ],
        "edges": [],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 32},
    }
    r = client.post("/run", json=data)
    assert r.status_code == 200
    body = r.json()
    assert body["nmode"] == 1
    assert len(body["V"]) == 2
    assert body["measured"][0]["op"] == "heterodyne"


def test_a8_no_private_or_other_rep_imports():
    """Vision §6.2 hard boundary: no private / Fock / Bosonic imports in lab."""
    root = Path(__file__).resolve().parents[1]
    banned = [
        "gaussian._",
        "from cvsim.fock",
        "from cvsim.bosonic",
        "import cvsim.fock",
        "import cvsim.bosonic",
    ]
    for rel in ["cvsim/lab/ir.py", "cvsim/lab/server.py", "cvsim/lab/__init__.py"]:
        src = (root / rel).read_text(encoding="utf-8")
        for b in banned:
            assert b not in src, f"{rel}: banned import pattern {b!r}"
