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


def test_wigner_frame_fit_contract():
    """Wigner frame sizing contract (regression lock).

    `fitWignerFrame()` used `wignerColorbar.offsetLeft`, whose reference frame is
    the element's offsetParent — BODY here, because `.wigner` is not positioned.
    The measured width therefore included the whole page's left offset, so the
    frame was sized far wider than its own grid column and covered the colourbar
    and the parameter side panel.

    Two invariants, both cheap greps (the geometric half lives in
    tests/lab_wigner_layout_probe.mjs, which needs uvicorn + Edge):
      1. the width must come from a getBoundingClientRect() difference;
      2. it must be measured from `.wigner`, not from the page.
    """
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    fit = js.split("function fitWignerFrame()", 1)
    assert len(fit) == 2, "fitWignerFrame() not found in app.js"
    body = fit[1].split("\n}\n", 1)[0]
    assert "offsetLeft" not in body, (
        "fitWignerFrame must not use offsetLeft: its reference frame is the "
        "offsetParent (BODY), not .wigner — use getBoundingClientRect() deltas"
    )
    assert "wignerColorbar.getBoundingClientRect().left" in body
    assert "wignerBox.getBoundingClientRect().left" in body


def test_wigner_fit_runs_after_colorbar_labels():
    """Call-site contract (a): colourbar tick labels decide the colourbar column
    width (an `auto` grid track), so `fitWignerFrame()` must run after the labels
    are written inside `drawHeatmap` and before the canvas pixel size is read.

    With the wrong order the frame is sized from the *previous* circuit's labels:
    measured slack went to 0 / -6 / -12 / -18px as labels widened, i.e. the frame
    ate the 12px gap and overlapped the colourbar. The page's ResizeObserver
    self-heals this a frame later, so a purely geometric probe cannot catch it —
    hence this source-order assertion."""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    draw = js.split("function drawHeatmap(W)", 1)
    assert len(draw) == 2, "drawHeatmap() not found in app.js"
    body = draw[1]
    i_labels = body.find('$("colorbar-min").textContent')
    i_fit = body.find("fitWignerFrame()")
    i_canvas = body.find("canvas.clientWidth")
    assert i_labels != -1 and i_fit != -1 and i_canvas != -1, (
        "drawHeatmap must write colourbar labels, call fitWignerFrame(), and size "
        "the canvas from canvas.clientWidth"
    )
    assert i_labels < i_fit < i_canvas, (
        f"fitWignerFrame() must sit between the colourbar label writes and the "
        f"canvas sizing (labels@{i_labels} fit@{i_fit} canvas@{i_canvas})"
    )


def test_wigner_fit_runs_after_side_panel_render():
    """Call-site contract (b): the side panel (meters / r̄ table) is the other
    input to `availW` — nmode 1→2 widens it 155 → 186.34px at 1440, shrinking
    availW by 31.34px. `render()` must therefore fit the frame *after* the last
    call that touches those tables.

    Measured with the fit hoisted too early: frame stayed 354.06px while the
    column was already 322.72px → 3224px² of colourbar overlap, and `.wigner`'s own
    ResizeObserver never fired because its border-box is unchanged (only the inner
    `1fr` track narrows). That makes this stale state permanent, not self-healing."""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    body = js.split("function render(result, mode)", 1)
    assert len(body) == 2, "render() not found in app.js"
    # scope to the render() body only — other functions also call fitWignerFrame()
    body = body[1].split("/** Shared Wigner draw", 1)[0]
    # gaussian path: the fits inside the fock/bosonic branches come earlier in the
    # source, so anchor on the gaussian path's own trailing render call.
    i_mode = body.find("renderModeSelect(nm, mode);")
    assert i_mode != -1, "render() must call renderModeSelect(nm, mode)"
    gaussian_tail = body[i_mode:]
    assert "fitWignerFrame();" in gaussian_tail, (
        "render() must fit the frame after the gaussian path's last render call "
        "(renderModeSelect), because that path renders the side panel"
    )
    # every backend path must reach a fit: 3 render paths, one fit each
    assert body.count("fitWignerFrame();") == 3, (
        "each render path (gaussian / bosonic / fock) must fit the frame; "
        f"found {body.count('fitWignerFrame();')}"
    )


def test_wigner_side_column_is_width_capped():
    """The third `.wigner` track is `auto` (content-sized), so the side column's
    width is subtracted from the `1fr` frame track. The "各模式 ⟨n⟩" meter prints
    one 4-decimal group per mode, so without a cap the column grows with nmode and
    crushes the frame: at 1440 folded, nmode 4 → side 350.4 / frame 158.7;
    nmode 8 → side 509.1 / frame 64, where 64 is the `max(64, …)` floor, so the
    frame covered the colourbar by 2304px² and `.result` overflowed (774/727).

    The cap must be `max-width` on the item, *not* `minmax(0, 12rem)` on the track:
    once `.wigner__side` is a scroll container a `minmax` max pins the track to
    12rem even when the content is narrow — measured on fock, whose narrow side
    content kept occupying 192px and pushed the frame back into the 64px clamp."""
    css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
    side = css.split(".wigner__side {", 1)
    assert len(side) == 2, ".wigner__side rule not found in style.css"
    block = side[1].split("}", 1)[0]
    assert "max-width:" in block, (
        ".wigner__side needs a max-width cap — without it the auto track sizes to "
        "the 各模式 ⟨n⟩ value and crushes the 1fr Wigner frame track"
    )
    assert "overflow-y: auto" in block, (
        ".wigner__side needs overflow-y: auto: the capped value wraps to more lines "
        "as nmode grows (2/4/8 → 1/4/8 lines), and the overflow would otherwise "
        "inflate the .wigner row and push .result past its column (measured 834/727)"
    )
    # strip comments first: the rules' own comments name the rejected alternatives
    import re
    decls = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    wigner = decls.split(".wigner {", 1)[1].split("}", 1)[0]
    assert "minmax(0, 12rem)" not in wigner, (
        "cap the side item with max-width, not the grid track: a minmax max pins "
        "the track to 12rem even for narrow content (fock), re-crushing the frame"
    )
    # `overflow-wrap` is the tempting-but-wrong fix: it changes min-content, not
    # max-content, and the value already breaks at its spaces
    meter = decls.split(".meter__value {", 1)[1].split("}", 1)[0]
    assert "overflow-wrap" not in meter, (
        "overflow-wrap on .meter__value does not cap the auto track — measured "
        "byte-identical geometry at every nmode; the cap is what fixes it"
    )


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

def test_default_scene_to_v1_byte_frozen():
    """AC4 回归锁（ADR-0014）：默认场景经真实导入路径 (loadJson → toV1Json)
    的导出字节恒定。前端唯一产出 circuit_v1 的路径，退役源节点不得改其输出
    （core IR 零扰动）。"""
    golden = (
        '{"schema":"circuit_v1","nmode":2,"seed":0,"ops":['
        '{"id":"d0","op":"displace","params":{"alpha":1},"modes":[0]},'
        '{"id":"d1","op":"displace","params":{"alpha":1},"modes":[1]}],'
        '"view":{"wigner_mode":0,"lim":5,"n":64},"ui":{"staff":{"d0":0,"d1":0}}}'
    )
    try:
        proc = subprocess.run(
            ["node", "--input-type=module", "-e",
             'import { loadJson } from "./editor.js";'
             'import { toV1Json } from "./ops.js";'
             'import { DEFAULT_SCENE } from "./default_scene.js";'
             'const r = loadJson(DEFAULT_SCENE);'
             'console.log(r.error || JSON.stringify(toV1Json(r.state)))'],
            capture_output=True, text=True, cwd=STATIC_DIR,
        )
    except FileNotFoundError as e:
        raise AssertionError("node 不可用 —— node 是前端测试链硬依赖") from e
    assert proc.returncode == 0, proc.stderr[:500]
    assert proc.stdout.strip() == golden
