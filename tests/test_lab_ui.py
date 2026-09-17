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


def test_wigner_frame_sizing_is_css_only():
    """C4: the Wigner frame square is sized by CSS, not JS.

    `fitWignerFrame()` was JS solving a CSS circular dependency: the frame's edge is
    `min(available width, available height)`, and the available width is the `1fr`
    track, whose width depends on the colourbar (`auto`) and side (`auto`) tracks —
    which are themselves content-sized. Keeping that in JS required two call-site
    ordering invariants (labels written before the fit; side panel rendered before
    the fit), each guarded by its own source-order test. Measured permanent
    mis-sizes when the order slipped: labels 0.5 → 0.00429 left the frame 24px
    short; nmode 1→2 kept the frame at 354.06 while the column was 322.72, a
    3224px² colourbar overlap that `.wigner`'s own ResizeObserver never repaired
    (its border-box is unchanged — only the inner `1fr` track narrows).

    The replacement is a query container on `.wigner__fit`, which occupies the `1fr`
    track: `100cqw` **is** the available width, so no JS measurement is involved and
    the whole class of ordering bugs is gone. The geometric half of this contract
    lives in tests/lab_wigner_layout_probe.mjs (6 invariants, uvicorn + Edge), which
    is unchanged by this task and still the hard gate.
    """
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "fitWignerFrame" not in js.split("/*")[0], (
        "fitWignerFrame must be gone; the frame is sized by CSS now"
    )
    # the two names it used to measure with must not come back
    for gone in ("wignerColorbar", "wignerBox", "WIDE_QUERY"):
        assert gone not in js.replace("原 fitWignerFrame", ""), (
            f"{gone} was only used by fitWignerFrame; remove it"
        )
    # JS must never write inline sizing back onto the frame
    assert "wignerFrame.style.width" not in js and "wignerFrame.style.height" not in js

    css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
    import re
    decls = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    fit = decls.split(".wigner__fit {", 1)[1].split("}", 1)[0]
    assert "container-type: inline-size" in fit, (
        "narrow branch must be inline-size: under <80rem `.wigner` is in page flow "
        "and its height is content-driven, so a size container collapses to 0 "
        "height (the original 'container-type height collapse' note)"
    )
    # wide branch upgrades to a size container and must stretch to get a real cqh
    wide = decls.split("@media (min-width: 80rem) {", 1)[1]
    wide_fit = wide.split(".wigner__fit {", 1)[1].split("}", 1)[0]
    assert "container-type: size" in wide_fit
    assert "align-self: stretch" in wide_fit, (
        "`.wigner` is `align-items: center`, so without align-self: stretch the "
        "wrapper is content-height and 100cqh collapses"
    )
    # the frame rule appears twice: the narrow base rule first, then the wide
    # override inside the media block — the min(width, height) form is the wide one
    narrow_frame = decls.split(".wigner__frame {", 1)[1].split("}", 1)[0]
    wide_frame = wide.split(".wigner__frame {", 1)[1].split("}", 1)[0]
    assert "max(64px, 100cqw)" in narrow_frame, (
        "narrow branch must be width-only: under <80rem the height is unconstrained "
        "(page flow), so min(width, height) would have nothing to bind against"
    )
    assert "min(100cqw, 100cqh)" in wide_frame, "wide branch must be min(width, height)"
    assert "flex: none" in narrow_frame or "flex: none" in wide_frame, (
        "the frame is now a flex item: default flex-shrink: 1 compresses it below "
        "the max(64px, …) clamp when the column is narrower than 64px "
        "(measured 57.25px on fock@1280, defeating the clamp)"
    )
    assert "max(64px," in narrow_frame and "max(64px," in wide_frame, (
        "keep the 64px floor in both branches"
    )
    # reverse constraint (parent AC6): do not introduce contain / content-visibility
    assert "contain:" not in css and "content-visibility" not in css, (
        "container-type is a query container; `contain` / `content-visibility` are "
        "explicitly out of scope (hidden panels already cost zero layout)"
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


# ── C1 (09-17-lab-interaction-path-rerender) 源码级契约 ─────────────────────
# 这些是**廉价 grep**：几何 / DOM 身份那一半在 lab_interaction_probe.mjs
# （需 uvicorn + Edge）。这里锁「结构性前提」，使无 Edge 的 CI 也能守住回归。


def test_interaction_light_paths_reuse_sync_chrome():
    """轻量路径必须复用 `syncChrome()`，不得各自手抄副作用序列。

    改动前 `render()`、`setInitial()`、`onParam()` **三处各抄一遍**同一串
    副作用（renderJson / onState / emit）。手抄副本正是"轻量路径漏掉某个
    副作用"的成因——例如 undo/redo 的 disabled 若漏掉，撤销按钮会永久禁用
    （lab_undo_probe.mjs 直接断言该状态）。
    """
    js = (STATIC_DIR / "editor.js").read_text(encoding="utf-8")
    assert "function syncChrome()" in js, "syncChrome() 单一副作用点缺失"
    # render() 必须由三段组成，而不是再列一遍副作用
    render_body = js.split("function render() {", 1)[1].split("\n  }\n", 1)[0]
    assert "staff.render()" in render_body
    assert "renderPalette()" in render_body
    assert "syncChrome()" in render_body
    for fn in ("setView", "setCircuit"):
        body = js.split(f"{fn}: (patch) => {{", 1)[1].split("\n    },", 1)[0]
        assert "syncChrome()" in body, f"{fn} 未走轻量路径"


def test_staff_labels_resync_on_cutoff_path():
    """R1 的正确性前提（实测证伪原计划）。

    `modeLabel` 把 `state.initial` 的光子数渲进模行标签（`mode m · |n⟩`），
    而 `clampInitial` 把 initial 夹到 `cutoff - 1` —— 故拖 fock cutoff 会改标签。
    轻量路径**必须**补标签，否则屏幕停在旧值（实测 |5⟩ → |2⟩）。
    """
    js = (STATIC_DIR / "editor.js").read_text(encoding="utf-8")
    assert "staff.syncLabels()" in js, "轻量路径没有补模行标签 → 拖 cutoff 会留陈旧标签"
    staff = (STATIC_DIR / "staff.js").read_text(encoding="utf-8")
    assert "function syncLabels()" in staff
    assert "syncLabels," in staff, "syncLabels 未从 initStaff 导出"
    # 结构变化的兜底：patch 触及结构键时仍须走完整 render
    assert '"nodes" in patch' in js, "setCircuit 缺少结构键防御"


def test_scan_dirty_key_is_node_identity_not_array_ref():
    """R2 的正确性前提（实测证伪原计划）。

    `onParam` 用 `state.nodes.map(...)` 重构数组，map 无论元素是否变化都返回
    **新数组** → 用 `nodes` 引用当脏键**永不命中**，规划中的修复会是静默空操作。
    故脏键必须是节点身份（id/op）而非数组引用。
    """
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "function scanNodeListKey()" in js, "脏键函数缺失"
    body = js.split("function scanNodeListKey() {", 1)[1].split("\n}\n", 1)[0]
    assert "${n.id}:${n.op}" in body, "脏键未取节点身份（id/op）"
    assert "state.nodes ===" not in body and "nodes === lastScanKey" not in body, (
        "脏键不能用 nodes 数组引用：map() 恒返回新数组，永不命中"
    )


# C1 的 `test_wigner_breakpoint_query_is_a_singleton` 已随 C4 退役：
# 它断言的 `const WIDE_QUERY = window.matchMedia("(min-width: 80rem)")` 是
# `fitWignerFrame` 的输入，而该函数已被删除 —— 断点判断现在由 CSS 的
# `@media (min-width: 80rem)` 承担，不再有 JS 侧 matchMedia 可缓存。
# 取代它的是 `test_wigner_frame_sizing_is_css_only`（含"WIDE_QUERY 不得复活"断言）。


# ── C2 (09-17-lab-heatmap-redraw-cache) 源码级契约 ──────────────────────────


def test_heatmap_cache_key_covers_grid_not_size():
    """R1: 离屏缓存键必须含 W **引用**与 n。

    键若只用数组引用会漏 dpr 变化；若做深比较则每次都是"新网格"（无效）。
    实测 dpr 1→2 时目标位图 303² → 606²，源位图仍是 64²。
    """
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    for name in ("offCanvas", "offCtx", "offWRef", "offN"):
        assert f"let {name}" in js, f"缓存状态 {name} 缺失"
    draw = js.split("function drawHeatmap(W)", 1)[1]
    assert "offWRef === W" in draw, "缓存键未用 W 引用比较（须为引用，非深比较）"
    assert "offN === n" in draw, "缓存键未含 n"


def test_canvas_size_guard_and_static_colorbar():
    """R3 同值不同赋值；R4 静态色带只画一次（且清空处复位）。

    colorbar 内容只依赖常量 LUT——实测 4 场景 × 2 dpr 的 toDataURL 哈希完全
    相同，故可只画一次。但 drawWignerResult 的 singular 分支会 clearRect，
    那里必须把标志复位，否则奇异态之后再无正常态色带。
    """
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert "if (canvas.width !== pw) canvas.width = pw;" in js
    assert "if (canvas.height !== ph) canvas.height = ph;" in js
    assert "if (!colorbarDrawn)" in js, "色带未改为一次性绘制"
    singular = js.split("if (!result.wigner)", 1)[1].split("} else {", 1)[0]
    assert "colorbarDrawn = false" in singular, (
        "singular 分支 clearRect 后必须复位 colorbarDrawn，否则色带永久留白"
    )


def test_r6_kept_high_smoothing():
    """R6 实测否决降到 "medium"：4 场景 × 2 dpr 的像素哈希全部改变。

    父任务明令"改视觉即越界"，故保留 "high"。本断言防止有人"顺手"降质。
    """
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert 'ctx.imageSmoothingQuality = "high";' in js


def test_fock_heat_rects_reused_not_rebuilt():
    """R7: joint 热图 rect 复用（原每格 6 次 setAttribute × 900 格）。

    复用必须按 SVG 分键：jointSvg 与 batchSvg 是两个不同 SVG，且采样侧可能
    不画。形状变化须重建（x/y 写死），故缓存须同时记 rows/cols/color。
    """
    js = (STATIC_DIR / "fock.js").read_text(encoding="utf-8")
    assert "const HEAT_CACHE = new WeakMap()" in js, "缺少按 SVG 分键的 rect 缓存"
    heat = js.split("function drawHeat(svg, data, color)", 1)[1].split("\n}\n", 1)[0]
    assert "cached.rows === rows" in heat and "cached.cols === cols" in heat, (
        "形状变化时必须重建 rect（x/y 按格坐标写死）"
    )
    assert "cached.color === color" in heat, "颜色变化时必须重建 rect"
    assert "getAttribute(\"fill-opacity\") !== want" in heat, (
        "透明度未变时应跳过 DOM 写入"
    )


# ── C5 (09-17-lab-redundant-work-cleanup) 源码级契约 ────────────────────────


def test_renames_hoisted_out_of_node_loop():
    """R1: renames() 必须在节点循环**外**调用一次。

    它读模块级 schemaTables()，在一次 toV1Json 调用内不会变，原先每个节点
    重算一次（与 §3.6 同源）。注意**不能**提到模块顶层：schema 注入发生在
    import 之后，顶层取值会拿到注入前的回退常量。
    """
    js = (STATIC_DIR / "ops.js").read_text(encoding="utf-8")
    assert "export function toV1Json(state) {" in js
    # scope to the loop itself: from the `for` up to the `outDoc` assembly that
    # follows it (the body has nested braces, so `\n}\n` would cut it short)
    tail = js.split("export function toV1Json(state) {", 1)[1]
    before_loop, after_loop = tail.split("for (const n of state.nodes) {", 1)
    loop_body = after_loop.split("const outDoc = {", 1)[0]
    assert "const R = renames();" in before_loop, "renames() 未提到循环外"
    assert "renames()" not in loop_body, "renames() 仍在节点循环内重复调用"
    # must not be hoisted to module scope: schema is injected after import, so a
    # top-level read would capture the pre-injection fallback constants.
    # Check only *top-level* lines (zero indentation) that actually CALL it —
    # the `function renames()` declaration is itself top-level, and other
    # functions such as visibleParams() legitimately call it inside their body.
    top_level_calls = [
        ln for ln in js.split("\n")
        if ln and not ln.startswith((" ", "\t"))
        and "renames()" in ln and "function renames()" not in ln
    ]
    assert not top_level_calls, (
        f"renames() 不得在模块顶层调用 —— schema 注入在 import 之后，"
        f"顶层取值会拿到注入前的回退常量：{top_level_calls}"
    )


def test_one_to_v1_json_per_mutation():
    """R2: 同一次 mutation 只算一次 toV1Json。

    原先 syncChrome()（renderJson + emit）与 onParam()（renderJson + emit）
    都在同一次状态变更里调两次，而 toV1Json 会遍历全部节点重建 ops 数组。
    修法是让 renderJson(doc) 接收**已算好的** doc（参数必填），
    使"算两遍"在结构上不可能发生。
    """
    js = (STATIC_DIR / "editor.js").read_text(encoding="utf-8")
    assert "function renderJson(doc) {" in js, "renderJson 必须接收已算好的 doc"
    assert "JSON.stringify(doc, null, 2)" in js, "JSON 文本仍须 2 空格缩进"
    # renderJson must no longer compute the doc itself
    rj = js.split("function renderJson(doc) {", 1)[1].split("\n  }\n", 1)[0]
    assert "toV1Json(" not in rj, "renderJson 不得自己再算一遍 toV1Json"

    sc = js.split("function syncChrome() {", 1)[1].split("\n  }\n", 1)[0]
    assert sc.count("toV1Json(") == 1, "syncChrome 内 toV1Json 必须只出现一次"
    assert "const doc = toV1Json(state);" in sc
    assert "renderJson(doc)" in sc, "renderJson 应复用同一个 doc"
    assert "emit(doc)" in sc, "emit 应复用同一个 doc 对象"

    op = js.split("onParam: (id, key, value) => {", 1)[1].split("\n    },", 1)[0]
    assert op.count("toV1Json(") == 1, "onParam 内 toV1Json 必须只出现一次"
    assert "emit(doc)" in op and "renderJson(doc)" in op


def test_fock_theme_vars_read_in_one_pass():
    """R4: fock 的 CSS 变量批量读取。

    原先 `cssVar()` 每读一个变量都调一次 `getComputedStyle(document.documentElement)`：
    `drawBars` 4 次 + `drawJointPair` 2 次 = 每帧 6 次样式解析入口。
    改为 `readThemeVars(names)` 单次读取。缓存假设已记在函数注释里：
    项目无主题切换 UI（tokens.css 静态 :root），故不得把它提到模块顶层。
    """
    js = (STATIC_DIR / "fock.js").read_text(encoding="utf-8")
    assert "function readThemeVars(names)" in js, "缺少批量读取函数"
    assert "function cssVar(" not in js, "旧 cssVar 应已被 readThemeVars 取代"
    # exactly one getComputedStyle, inside readThemeVars
    assert js.count("getComputedStyle(") == 1, "getComputedStyle 应只剩 readThemeVars 内那一处"
    rtv = js.split("function readThemeVars(names) {", 1)[1].split("\n}\n", 1)[0]
    assert "getComputedStyle(document.documentElement)" in rtv
    # both draw paths must go through the batched reader
    assert js.count("readThemeVars(") == 3, "两个调用点 + 定义处 = 3 次命中"
    # fallbacks preserved verbatim
    for fb in ('"#2e63d1"', '"#c33"', '"#ccc"', '"#333"'):
        assert fb in js, f"缺回退色 {fb}"
    # pure-function exports must be untouched (可测性未破坏)
    for name in ("histBars", "reshapeCounts", "marginalOf", "overlayHeat", "leakInfo",
                 "slowCutoff", "clampInitial", "batchMeasRows"):
        assert f"export function {name}" in js or f"export const {name}" in js, (
            f"纯函数导出 {name} 被破坏"
        )


# ── C6 (09-17-lab-css-a11y-misc) 源码级契约 ─────────────────────────────────


def test_scrollbar_rule_stays_universal_not_root():
    """R1 **实测否决** → 反向约束：滚动条规则必须留在 `*`，不得改 `:root`。

    原计划的理由是「`scrollbar-width` / `scrollbar-color` 都是可继承属性」。
    实测（Edge 153）**只有 `scrollbar-color` 可继承**；`:root { scrollbar-width:
    thin }` 只让 `<html>` 算得 `thin`，`<body>` 与所有后代回落 `auto`
    → 每个滚动容器滚动条从 12px 槽变 17px 槽，**5/5 容器外观全变**。

    这是「改视觉即越界」的直接违反，故保留 `*`。
    守卫方式与 C4 的 `container-type` 反向断言同型：断言那个"看起来更优雅的
    改法"**没有被重新引入**。
    证据：`.scratch/c6-gutter-{before,after}.json`、`.scratch/c6-ab.mjs`。
    """
    css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
    # the universal rule must be present
    assert "* {\n  scrollbar-width: thin;" in css, (
        "滚动条规则被移出 `*` —— 实测会让 5/5 容器滚动条变宽（见 docstring）"
    )
    assert "scrollbar-color: var(--color-rule) transparent;" in css
    # and the rejected variant must NOT be reintroduced
    assert ":root {\n  scrollbar-width: thin;" not in css, (
        "`scrollbar-width` 不可继承，不得挂在 `:root` 上"
    )
    # WebKit pseudo-element rules preserved verbatim
    for sel in ("::-webkit-scrollbar {", "::-webkit-scrollbar-track {",
                "::-webkit-scrollbar-thumb {", "::-webkit-scrollbar-thumb:hover {",
                "::-webkit-scrollbar-corner {"):
        assert sel in css, f"WebKit 滚动条规则 {sel} 被误删"


def test_staff_is_not_a_live_region():
    """R2: `#staff` 不得是 live region；`#status` 必须**仍是**。

    `#staff` 子树任何编辑都走 `replaceChildren()`，对 live region 反复整树
    重建会让 a11y 树反复 diff 并产生播报噪音。正确的播报口是 `#status`
    （`setStatus` 写它，`role="status"` + `aria-live="polite"`）。
    """
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    staff_line = next(ln for ln in html.split("\n") if 'id="staff"' in ln)
    assert "aria-live" not in staff_line, "#staff 仍是 live region"
    assert 'aria-label="五线谱电路编辑区"' in staff_line, "aria-label 被误删"
    assert 'class="staff"' in staff_line, "class 被误删"
    # #status must keep BOTH role and aria-live
    status_line = next(ln for ln in html.split("\n") if 'id="status"' in ln)
    assert 'role="status"' in status_line, "#status 丢了 role=status"
    assert 'aria-live="polite"' in status_line, "#status 丢了 aria-live（唯一播报口）"


def test_scroll_into_view_runs_in_animation_frame():
    """R3: 两处 `scrollIntoView` 都必须在 rAF 内。

    `scrollIntoView` 紧跟 DOM 写入会强制同步布局（前面的 `hidden = false`
    或绘制已让布局失效）。延后一帧不影响"滚到可见"的目的。
    """
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    assert js.count("scrollIntoView(") == 2, "应恰好两处 scrollIntoView"
    assert js.count("requestAnimationFrame(() => measurementPanel.scrollIntoView(") == 1
    assert js.count("requestAnimationFrame(() => scanSvg.scrollIntoView(") == 1
    # no bare (unwrapped) call remains
    for ln in js.split("\n"):
        if "scrollIntoView(" in ln:
            assert "requestAnimationFrame" in ln, f"仍有裸 scrollIntoView 调用：{ln.strip()}"


def test_health_does_not_gate_editor_boot():
    """R4: `/health` 不得阻塞 `schemaOk` 分支（门控只有 `/schema`）。

    `/health` 只填页眉版本号，与门控正交；串行 await 会让首个
    `editor.render()` 多等一个 RTT。**不**断言耗时改进 —— 本地
    `127.0.0.1` 上收益不可测（审查 §8），AC 只要求门控行为不变。
    """
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    init = js.split("async function init() {", 1)[1]
    assert 'await (await fetch("/health"))' not in init, "`/health` 仍在阻塞 await"
    assert 'await fetch("/health")' not in init, "`/health` 仍在阻塞 await"
    assert 'fetch("/health")' in init, "`/health` 调用被误删（版本号仍须填）"
    assert "version-tag" in init, "版本号写入被误删"
    # /schema must still be the awaited gate, and the failure branch must survive
    assert 'await (await fetch("/schema")).json()' in init, "/schema 门控被改"
    assert "schemaOk = true" in init
    assert "后端 schema 不可用" in init, "/schema 失败的红条被删"
    for bid in ("run-btn", "sample-btn", "scan-btn", "save-btn", "fidelity-btn", "bos-fidelity-btn"):
        assert f'"{bid}"' in init, f"失败禁用清单缺 {bid}"
    # ordering: /health must not sit between the /schema gate and editor.render()
    health_at = init.index('fetch("/health")')
    render_at = init.index("editor.render()")
    gate_at = init.index("if (schemaOk) {")
    assert health_at < gate_at or health_at > render_at, (
        "`/health` 仍夹在门控与 editor.render() 之间"
    )



