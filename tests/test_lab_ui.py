"""F-LAB-STATIC: static page serving, key elements, offline guard."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from cvsim.lab.server import app

client = TestClient(app)

STATIC_DIR = Path(__file__).resolve().parents[1] / "cvsim" / "lab" / "static"


def load_default_scene() -> dict:
    """The shipped default scene (票3: 单一事实源 default_scene.js leaf).
    经 node 子进程取值 —— pytest 第一次硬依赖 node；缺失/失败 = 明确红，
    不静默 skip（ADR-0009 决策 4：不做 golden JSON 副本兜底）。"""
    try:
        proc = subprocess.run(
            ["node", "--input-type=module", "-e",
             'import { DEFAULT_SCENE } from "./default_scene.js";'
             'console.log(JSON.stringify(DEFAULT_SCENE))'],
            capture_output=True, text=True, cwd=STATIC_DIR,
        )
    except FileNotFoundError as e:
        raise AssertionError(
            "node 不可用 —— node 是前端测试链硬依赖"
            "（CONTEXT.md 环境约定），不静默 skip。"
        ) from e
    if proc.returncode != 0:
        raise AssertionError(
            "node 取默认场景失败（node 是前端测试链硬依赖，"
            "见 CONTEXT.md 环境约定）。"
            f"stderr: {proc.stderr.strip()[:500]}"
        )
    return json.loads(proc.stdout.strip())


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
        "save-btn",
        "load-input",
        "seed-input",
        "sample-btn",
        "measurement-panel",
        "scan-panel",
        "scan-node",
        "scan-param",
        "scan-min",
        "scan-max",
        "scan-n",
        "scan-modes-a",
        "scan-btn",
        "scan-svg",
    ):
        assert f'id="{el}"' in html, el


def test_l3_homodyne_in_palette_contract():
    """ops.js ↔ ir.py contract: homodyne present, phi default 0."""
    ops = (STATIC_DIR / "ops.js").read_text(encoding="utf-8")
    assert "homodyne:" in ops
    assert "零差测量" in ops
    assert "def: 0" in ops and "max: TAU" in ops


def test_l4_amp_mz_in_palette_contract():
    """ops.js ↔ ir.py contract (L4): amplifier + mz present with sweep metadata;
    alpha stays sweep-less."""
    ops = (STATIC_DIR / "ops.js").read_text(encoding="utf-8")
    assert "amplifier:" in ops and "放大" in ops
    assert "mz:" in ops and "马赫-曾德尔" in ops
    assert "sweep: [1, 4]" in ops
    assert "advanced: true" in ops  # nbar advanced (loss + amplifier)
    # ticket 4: the ir.py whitelist-literal grep retired — the whitelist is
    # derived in cvsim.lab.schema (core ir_schema - UI-hidden), and the
    # data-level contract (per-op membership) is the golden /schema tests
    # in test_lab_schema.py. UI metadata grep above stays (Q2/Q6 teaching
    # scales remain in ops.js by design).


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
    undefined → top-level crash → blank page, no /run ever fired).
    票1 后 clamp 语义迁居 colormap leaf（ADR-0009），测试随知识走；
    同时锁 app.js 仍从 leaf 取 LUT（消费边不断）。"""
    cm = (STATIC_DIR / "colormap.js").read_text(encoding="utf-8")
    assert "Math.min(Math.floor(t), last)" in cm
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert 'from "./colormap.js"' in js


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
        "schema": "circuit_v1",
        "nmode": 2,
        "ops": [{"id": "s", "op": "two_mode_squeeze", "modes": [0, 1], "params": {"r": r}}],
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
    }
    resp = client.post("/run", json=payload)
    assert resp.status_code == 200
    got = resp.json()["meters"]["log_negativity"]
    want = 2 * r / math.log(2)  # -log2(e^(-2r))
    assert abs(got - want) < 1e-3
