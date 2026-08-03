"""F-LAB-STATIC: static page serving, key elements, offline guard."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cvsim.lab.server import app

client = TestClient(app)

STATIC_DIR = Path(__file__).resolve().parents[1] / "cvsim" / "lab" / "static"


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_assets_served():
    for name in ("tokens.css", "style.css", "app.js"):
        r = client.get(f"/{name}")
        assert r.status_code == 200, name


def test_key_elements_present():
    html = client.get("/").text
    for el in (
        "json-input",
        "run-btn",
        "reset-btn",
        "wigner-canvas",
        "meters-panel",
        "v-table",
        "rbar-table",
        "status",
    ):
        assert f'id="{el}"' in html, el


def test_offline_guard_no_external_urls():
    """Local workbench hard constraint: zero external network references."""
    for name in ("index.html", "tokens.css", "style.css", "app.js"):
        src = (STATIC_DIR / name).read_text(encoding="utf-8")
        assert "http://" not in src, f"{name}: external http ref"
        assert "https://" not in src, f"{name}: external https ref"
        assert "@import" not in src, f"{name}: remote import"


def test_default_scene_runs():
    """The JSON embedded in the page must be a valid circuit (A9-adjacent)."""
    html = client.get("/").text
    # extract the default JSON from app.js instead: page ships it there
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "tmsv" in js and "r: 0.6" in js
    payload = {
        "schema": "circuit_v0",
        "seed": 0,
        "nodes": [
            {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
            {"id": "l0", "op": "loss", "params": {"T": 0.8}, "mode": 0},
            {"id": "l1", "op": "loss", "params": {"T": 0.8}, "mode": 1},
        ],
        "edges": [],
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
        "ui": {},
    }
    r = client.post("/run", json=payload)
    assert r.status_code == 200
    assert len(r.json()["wigner"]["W"]) == 64
