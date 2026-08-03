"""F-LAB-STATIC: static page serving, key elements, offline guard."""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from cvsim.lab.server import app

client = TestClient(app)

STATIC_DIR = Path(__file__).resolve().parents[1] / "cvsim" / "lab" / "static"

_JS_KEYS = r"\b(?:schema|seed|nodes|id|op|params|r|modes|loss|T|mode|edges|view|"
_JS_KEYS += r"wigner_mode|lim|n|ui)\b"


def load_default_scene() -> dict:
    """Parse the shipped DEFAULT_JSON out of app.js so the test exercises
    exactly what the UI ships (single source of truth)."""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    m = re.search(r"const DEFAULT_JSON = (\{.*?\});\n", js, re.S)
    assert m, "DEFAULT_JSON not found in app.js"
    literal = re.sub(rf"({_JS_KEYS})(?=\s*:)", r'"\1"', m.group(1))
    # JS object literal → JSON: drop trailing commas
    literal = re.sub(r",(\s*[}\]])", r"\1", literal)
    return json.loads(literal)


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
    """Local workbench hard constraint: zero external network references.
    Case-insensitive schemes (no protocol-relative / URL() forms allowed).
    SVG namespace URI (http://www.w3.org/2000/svg) is a constant, not a
    network reference."""
    for name in ("index.html", "tokens.css", "style.css", "app.js"):
        src = (STATIC_DIR / name).read_text(encoding="utf-8")
        stripped = src.replace("http://www.w3.org/2000/svg", "")
        assert not re.search(r"(?i)https?://|@import", stripped), f"{name}: external ref"


def test_lut_clamp_guard():
    """Regression: buildLut must clamp anchor index (was reading [16] →
    undefined → top-level crash → blank page, no /run ever fired)."""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "Math.min(Math.floor(t), last)" in js


def test_default_scene_runs():
    """The exact scene shipped in app.js must be a valid circuit (A9-adjacent)."""
    payload = load_default_scene()
    r = client.post("/run", json=payload)
    assert r.status_code == 200
    assert len(r.json()["wigner"]["W"]) == 64


def test_view_bounds_enforced():
    """OCR review: view.n / view.lim must be bounded to prevent n² grid DoS."""
    base = load_default_scene()
    big = dict(base, view={**base["view"], "n": 10000})
    assert client.post("/run", json=big).status_code == 422
    wide = dict(base, view={**base["view"], "lim": 999})
    assert client.post("/run", json=wide).status_code == 422


def test_a3_logneg_freeze():
    """A3: T=1 TMSV log_negativity ≈ -log2(e^(-2r)) = 2r/ln(2).
    Editor slider range r∈[-3,3]; frontend displays this value."""
    import math

    r = 0.6
    payload = {
        "schema": "circuit_v0",
        "nodes": [{"id": "s", "op": "tmsv", "params": {"r": r}}],
        "edges": [],
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
    }
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    got = resp.json()["meters"]["log_negativity"]
    want = 2 * r / math.log(2)  # -log2(e^(-2r))
    assert abs(got - want) < 1e-3
