/* Gaussian Lab workbench — L1 render pipeline + L2 editor wiring. */
"use strict";

import { initEditor, loadJson } from "./editor.js";
import { OPS, toV1Json } from "./ops.js";
import { meterKeys, publishSchema } from "./schema_store.js";
import { deriveOps } from "./ops_schema.js";
import { setInitialSchema } from "./initial.js";
import { setEditorSchema, deriveEditorTables } from "./editor.js";
import { initFockPanel } from "./fock.js";
import { createSeqGuard, requestLab, makeRefCountedBusy, REQUEST_KIND } from "./request.js";
import { buildLut, inspectWignerGrid, wignerT } from "./colormap.js";
import { finitePoints, plotDomain, makeScale, polylineSegments, svgPath } from "./curve.js";
import { el, fmt, axisVal, outcomeText } from "./svg_kit.js"; // SVG_NS 留在 leaf 内（app.js 不直用）
import { validateScanForm } from "./scan_form.js";
import { initStepState, stepLabel, stepDesc, stepMeters } from "./steps_slider.js";
import { DEFAULT_SCENE } from "./default_scene.js";

/* L5.5 默认场景字面量已迁居 default_scene.js（票3 单一事实源，ADR-0009）
   —— app.js 与 pytest 经同一 leaf 取值，测试不再正则读本文件。 */

const LUT = buildLut();

const $ = (id) => document.getElementById(id);
const canvas = $("wigner-canvas");
const wignerBox = document.querySelector(".wigner");
const wignerFrame = document.querySelector(".wigner__frame");
const wignerSide = $("wigner-side");
const wignerColorbar = document.querySelector(".wigner__colorbar");

/* frame 正方形 = min(可用宽, 可用高)：可用宽 = colorbar 左缘 - .wigner 左缘 - gap。
   CSS 无原生解（aspect-ratio 遇双 definite 失效、container-type 高度塌缩）→ JS 算。

   陷阱：必须用 getBoundingClientRect() 的**同一坐标系差值**量宽度，禁用 offsetLeft。
   .wigner__colorbar 的 offsetParent 是 BODY（.wigner 无 position），offsetLeft 含整页
   左偏移，用它当「距 .wigner 的距离」会把 frame 撑到列外、盖住 colorbar 与参数表。

   调用点契约：必须在所有会改 availW 的渲染**之后**调用。availW 有两个输入，都由
   render 管线改写：
    (1) colorbar 刻度标签宽度（auto 列）—— 在 drawHeatmap 内标签与画布像素之间调用；
    (2) 侧列（meters / r̄ 表）宽度，随 nmode 变 —— 在 render() 末尾补一次。
   漏掉任一处 frame 就按旧输入定尺寸：实测标签 0.5 → 0.00429 时倒欠 24px；
   nmode 1→2 侧列 155 → 186.34 时 frame 恒定 354.06 而列宽只有 322.72，与 colorbar
   重叠 3224px²。两种都不会被 .wigner 自身的 ResizeObserver 救回（它的 border-box
   没变，变的是内部 1fr 轨道宽度）。 */

/* C1 R5: 断点查询是**常量**——viewport 宽度在一次查询里不会变，故只建一次。
   原先每次 fit 都调 matchMedia（每次分配新 MediaQueryList 对象）；滑条路径上
   fit 每步都跑，实测 4 次 input = 4 次 matchMedia。 */
const WIDE_QUERY = window.matchMedia("(min-width: 80rem)");

function fitWignerFrame() {
  if (!wignerBox || !wignerFrame || !wignerColorbar) return;
  const gap = parseFloat(getComputedStyle(wignerBox).gap || "16");
  const availW = wignerColorbar.getBoundingClientRect().left
    - wignerBox.getBoundingClientRect().left - gap;
  const h = wignerBox.clientHeight;
  /* 单列（<80rem）页面流：高度无约束 → 画布 = 列宽；三列：min(宽, 高) */
  const s = WIDE_QUERY.matches
    ? Math.max(64, Math.min(availW, h))
    : Math.max(64, availW);
  wignerFrame.style.width = s + "px";
  wignerFrame.style.height = s + "px";
}
const colorbar = $("colorbar-canvas");
const statusEl = $("status");
const runBtn = $("run-btn");
const modeSelect = $("wigner-mode-select");
const saveBtn = $("save-btn");
const loadInput = $("load-input");
const seedInput = $("seed-input");
const sampleBtn = $("sample-btn");
const measurementPanel = $("measurement-panel");
const mSeed = $("m-seed");
const mOutcomes = $("m-outcomes");
const mSingularNote = $("m-singular-note");
const wignerNote = $("wigner-note");
const scanNode = $("scan-node");
const scanParam = $("scan-param");
const scanMin = $("scan-min");
const scanMax = $("scan-max");
const scanN = $("scan-n");
const scanModesA = $("scan-modes-a");
const scanBtn = $("scan-btn");
const scanSvg = $("scan-svg");
const scanNote = $("scan-note");

function setStatus(text, ok = true) {
  statusEl.textContent = text;
  statusEl.dataset.state = ok ? "ok" : "error";
}

/* 候选 2：统一 requestLab 错误渲染（深模块收敛 5 处重复的 catch/状态码文案
   为单函数）。validate → 文案直显；http → 状态码 + detail（缺省用站点
   fallback）；network → “网络错误: …”。 */
function reportError(e, fallback) {
  if (e.kind === REQUEST_KIND.VALIDATE) setStatus(e.detail, false);
  else if (e.kind === REQUEST_KIND.HTTP) setStatus(e.status + " · " + (e.detail || fallback), false);
  else setStatus("网络错误: " + e.detail, false);
}

/* 候选 2（P2a）：seed 前置校验（doSample/doBatch 共用，提取消重复）。
   返回非 null 表示非法，requestLab validate 会 abort 请求。 */
const validateSeed = (p) =>
  (Number.isInteger(p.seed) && p.seed >= 0) ? null : "seed 必须是非负整数";

function renderMatrix(table, rows, cols, head, cell) {
  let html = "<thead><tr><th></th>" + Array.from({ length: cols }, (_, c) => `<th class="mono">${head(c)}</th>`).join("") + "</tr></thead><tbody>";
  for (let r = 0; r < rows; r++) {
    html += "<tr><th class=\"mono mat__rowhead\">" + head(r) + "</th>";
    for (let c = 0; c < cols; c++) html += `<td class="mono">${cell(r, c)}</td>`;
    html += "</tr>";
  }
  table.innerHTML = html + "</tbody>";
}

/* 离屏缓存的单例状态（C2 R1）。缓存的是 **n×n 源位图**，不是目标 canvas：
   目标尺寸随容器变，源位图只随 W 网格变。
   cacheW 存 **W 的引用**（后端每次 /run 返回新数组对象 → 引用比较即"网格已换"），
   canvas.width/height 存像素尺寸（含 dpr）——dpr 变化时目标尺寸变、源位图不变，
   但仍须重算，因为 drawImage 的上采样目标变了。
   陷阱：只按 W 引用做键会漏掉 dpr，故键 = (W 引用, n)。 */
let offCanvas = null;
let offCtx = null;
let offWRef = null;   // 缓存对应的 W 引用
let offN = 0;         // 缓存对应的 n（W.length）
let colorbarDrawn = false; // C2 R4: 静态色带是否已画（清空处须复位）

function drawHeatmap(W) {
  /* C2 R2：校验 + 求尺度融为一次遍历（原先是两次 n² 扫描 + 逐格映射共三次） */
  const { scale } = inspectWignerGrid(W); // 非法网格抛 Invalid Wigner grid
  const n = W.length;
  /* 离屏 n×n LUT → 主画布按显示尺寸 × dpr 重绘（无马赛克） */
  if (offWRef === W && offN === n && offCanvas) {
    // 同一网格重绘（RO / dpr 路径）：源位图复用，只重做上采样
  } else {
    if (!offCanvas) {
      offCanvas = document.createElement("canvas");
      offCtx = offCanvas.getContext("2d");
    }
    offCanvas.width = n;
    offCanvas.height = n;
    const img = offCtx.createImageData(n, n);
    for (let j = 0; j < n; j++) {
      for (let i = 0; i < n; i++) {
        const t = wignerT(W[j][i], scale);
        const o = (j * n + i) * 4;
        img.data[o] = LUT[t * 3];
        img.data[o + 1] = LUT[t * 3 + 1];
        img.data[o + 2] = LUT[t * 3 + 2];
        img.data[o + 3] = 255;
      }
    }
    offCtx.putImageData(img, 0, 0);
    offWRef = W;
    offN = n;
  }
  /* Symmetric scale anchors the physical zero at LUT midpoint (black). */
  /* #6: symmetric colorbar ticks (axisVal format, matching axes). */
  $("colorbar-max").textContent = axisVal(scale);
  $("colorbar-zero").textContent = "0";
  $("colorbar-min").textContent = axisVal(-scale);
  /* 标签写完才 fit：标签宽度决定 colorbar 列宽，frame 的可用宽随之变（见 fitWignerFrame
     调用点契约）。此处是唯一「标签刚定、画布像素未定」的窗口。 */
  fitWignerFrame();
  /* 热图铺满 plot：宽高分别按 clientWidth/clientHeight × dpr（不再假设正方形） */
  const cw = Math.max(64, Math.round(canvas.clientWidth || 256));
  const ch = Math.max(64, Math.round(canvas.clientHeight || 256));
  const dpr = window.devicePixelRatio || 1;
  const pw = Math.min(1024, Math.round(cw * dpr));
  const ph = Math.min(1024, Math.round(ch * dpr));
  /* C2 R3：同值赋值也会重置位图与上下文状态，故加守卫省掉这次无谓重置。
     赋值后的 clearRect 仍保留——下面 clearRect 与 drawImage 覆盖整块画布。 */
  if (canvas.width !== pw) canvas.width = pw;
  if (canvas.height !== ph) canvas.height = ph;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, pw, ph);
  ctx.imageSmoothingEnabled = true;
  /* C2 R6：实测否决降到 "medium"。n=64 源位图 → 303² 目标（dpr1）/ 606²（dpr2）
     是 4.7×/9.5× 上采样，4 个场景 × 2 个 dpr 的 toDataURL 哈希**全部改变**
     （如 displace@dpr1 409c7ca0→95390307）。属"改视觉即越界"（parent Out of
     Scope），故保留 "high"。证据：tests/lab_heatmap_pixels.json 对拍。 */
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(offCanvas, 0, 0, pw, ph);
  /* colorbar（C2 R4：内容只依赖常量 LUT，与 W / 尺寸 / dpr 全无关
     —— 实测 4 个场景 × 2 个 dpr 的 toDataURL 哈希完全相同，故只画一次） */
  if (!colorbarDrawn) {
    const cb = colorbar.getContext("2d");
    for (let k = 0; k < 128; k++) {
      const t = Math.round((k / 127) * 255);
      cb.fillStyle = `rgb(${LUT[t * 3]},${LUT[t * 3 + 1]},${LUT[t * 3 + 2]})`;
      cb.fillRect(0, 127 - k, 8, 1);
    }
    colorbarDrawn = true;
  }
}

/* SVG overlay axes — drawn at display resolution (canvas is 64 physical px
   scaled up, so canvas strokes would blur/thicken). Solid 1px lines in
   ice-cyan (--color-axis, complementary to inferno), values in ink with a
   paper halo (paint-order: stroke) so they read on any heatmap region. */
let lastLim = 5;
let lastWigner = null; // latest W grid — ResizeObserver 重绘用（dpr）

function drawAxes(lim) {
  lastLim = lim;
  const svg = $("axis-svg");
  const w = canvas.clientWidth || 1;
  const h = canvas.clientHeight || 1;
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.replaceChildren();

  const style = getComputedStyle(document.documentElement);
  const axis = style.getPropertyValue("--color-axis").trim() || "#7fe0ff";
  const paper = style.getPropertyValue("--color-paper").trim();
  const cx = w / 2;
  const cy = h / 2;

  svg.append(
    el("line", { x1: cx, y1: 0, x2: cx, y2: h, stroke: axis, "stroke-width": 1 }),
    el("line", { x1: 0, y1: cy, x2: w, y2: cy, stroke: axis, "stroke-width": 1 }),
  );

  const vals = [-lim, -lim / 2, 0, lim / 2, lim];
  const frac = [0, 0.25, 0.5, 0.75, 1];
  for (let i = 0; i < 5; i++) {
    const x = frac[i] * w;
    const y = frac[i] * h;
    const label = vals[i] === 0 ? null : axisVal(vals[i]); // no label at origin
    const mkText = (tx, ty, anchor) => {
      const t = el("text", { x: tx, y: ty, "text-anchor": anchor, fill: axis });
      t.setAttribute("stroke", `${paper} / 0.92`);
      t.setAttribute("stroke-width", 3);
      t.textContent = label;
      return t;
    };
    /* x ticks on the horizontal center line, values below */
    svg.append(el("line", { x1: x, y1: cy - 3, x2: x, y2: cy + 3, stroke: axis, "stroke-width": 1 }));
    if (label !== null) svg.append(mkText(x, cy + 13, "middle"));
    /* y ticks on the vertical center line, values to the left */
    svg.append(el("line", { x1: cx - 3, y1: y, x2: cx + 3, y2: y, stroke: axis, "stroke-width": 1 }));
    if (label !== null) svg.append(mkText(cx - 7, y + 3.5, "end"));
  }
}

/* C2 R5: canvas RO 回调合并到一帧一次。RO 在一个批次里可能投递多条（拖窗口时
   宽度/高度各一次），每条都跑 drawHeatmap + drawAxes 会重复上采样与重建 SVG。
   rafPending 去重：一帧只跑一次，且读到的是**最新**的 lastWigner / lastLim。 */
let wignerRafPending = false;

new ResizeObserver(() => {
  if (wignerRafPending) return;
  wignerRafPending = true;
  requestAnimationFrame(() => {
    wignerRafPending = false;
    if (lastWigner) drawHeatmap(lastWigner.W);
    drawAxes(lastLim);
  });
}).observe(canvas);

/* 容器尺寸变化（窗口/面板/fock 切换）→ 重算正方形画布 */
new ResizeObserver(fitWignerFrame).observe(wignerBox);

/* colorbar 列宽由刻度标签内容决定（auto 列），侧列宽由 meters/r̄ 表决定：两者都是
   availW 的输入，字体延迟加载/标签变长/nmode 变化都会改它们。drawHeatmap 内与
   render() 末尾的显式 fit 覆盖绘制与渲染路径，此处兜底其余时机（如字体加载完成）。 */
new ResizeObserver(fitWignerFrame).observe(wignerColorbar);
if (wignerSide) new ResizeObserver(fitWignerFrame).observe(wignerSide);

/* R6 (ADR-0008 决策 3): meter 行标签 — 值消费者 (meter VALUE 读取口) 与
   渲染顺序的唯一前端声明处；键集来自 /schema meter 矩阵
   (schema_store.meterKeys，后端事实源 cvsim/lab/result.py)。 */
const METER_ROWS = {
  purity: { value: "m-purity", label: "纯度" },
  mean_photon: { value: "m-nbar", label: "平均光子数" },
  mean_photon_per_mode: { value: "m-permode", label: "各模式 ⟨n⟩" },
  log_negativity: { value: "m-logneg", label: "对数负度" },
};

/** meter 面板渲染 (gaussian/bosonic 共享)：矩阵定行可见性，值经 fmt
   (缺键/None → 诚实 "—")。矩阵外静态行隐藏 (防御：HTML 漂移时可见)；
   flag 型扩展键 (singular) 不占 meter 行 — 其专属消费者在
   showMeasurement (m-singular-note)。 */
function renderMetersPanel(backend, m) {
  const keys = meterKeys(backend);
  for (const [key, row] of Object.entries(METER_ROWS)) {
    const tr = $(`m-row-${key}`);
    if (!tr) continue; // HTML 漂移防御：矩阵键无静态行则跳过，不渲染
    tr.hidden = !keys.has(key);
    if (keys.has(key)) {
      const val = m[key];
      $(row.value).textContent = Array.isArray(val)
        ? val.map((v) => fmt(v)).join(" ")
        : fmt(val);
    }
  }
}

function render(result, mode) {
  /* #8: 新 run 使旧 scan 摘要失效——折叠摘要清空 */
  const scanSummary = $("scan-summary");
  scanSummary.hidden = true;
  scanSummary.textContent = "";
  if (result.backend === "fock") {
    renderFock(result, mode);
    fitWignerFrame(); // 见 fitWignerFrame 调用点契约：所有会改 availW 的渲染之后
    return;
  }
  if (result.backend === "bosonic") {
    renderBosonic(result, mode);
    fitWignerFrame();
    return;
  }
  drawWignerResult(result);
  $("rbar-block").hidden = false; // 均值表常驻侧列（有数据才显示）

  renderMetersPanel(result.backend, result.meters); // R6: 矩阵驱动（原隐式键缺席分派退役）

  $("nmode-tag").textContent = `nmode ${result.nmode}`;
  const nm = result.nmode;
  /* backend covariance layout is split: [x0..x_{m-1}, p0..p_{m-1}] —
     label rows/cols in that order (interleaved xpxpxp would mislabel m≥2) */
  const modeHead = (i) => `mode ${i < nm ? i : i - nm}·${i < nm ? "x" : "p"}`;
  renderMatrix($("rbar-table"), nm * 2, 1, modeHead, (r) => fmt(result.rbar[r]));
  renderMatrix($("v-table"), nm * 2, nm * 2, modeHead, (r, c) => fmt(result.V[r][c]));

  renderModeSelect(nm, mode);
  /* 侧列宽度（meters / r̄ 表的行标签）由 nmode 决定，是 availW 的输入；上面的 render*
     都会改它。放最后 → frame 与最终列宽一致。 */
  fitWignerFrame();
}

/** Shared Wigner draw (gaussian + fock paths). */
function drawWignerResult(result) {
  if (!result.wigner) {
    // singular conditional state: no finite Wigner, never fabricated
    lastWigner = null;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cb = colorbar.getContext("2d");
    cb.clearRect(0, 0, 8, 128);
    colorbarDrawn = false; // C2 R4: 已清空 → 下次 drawHeatmap 必须重画静态色带
    $("colorbar-max").textContent = "—";
    $("colorbar-zero").textContent = "—";
    $("colorbar-min").textContent = "—";
    $("axis-svg").replaceChildren();
    wignerNote.hidden = false;
  } else {
    wignerNote.hidden = true;
    const { x, p, W } = result.wigner;
    lastWigner = result.wigner;
    drawHeatmap(W);
    drawAxes(x[x.length - 1]); // lim = +x max
  }
}

/** mode selector: rebuild options to nmode (shared wigner/dist selector). */
function renderModeSelect(nm, mode) {
  modeSelect.replaceChildren();
  for (let k = 0; k < nm; k++) {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = `mode ${k}`;
    if (k === Number(mode)) opt.selected = true;
    modeSelect.appendChild(opt);
  }
}

/* F7: Fock 结果面板 — Wigner（复用）+ PNR 分布柱 + joint heatmap +
   截断护栏；gaussian-only 面板（meters/scan/state）隐藏。 */
function renderFock(result, mode) {
  drawWignerResult(result);
  renderModeSelect(result.nmode, mode);
  fockPanel.renderResult(result);
}

/* B6: Bosonic 结果面板 — Wigner（复用）+ meters（矩阵驱动，R6）+
   分步执行滑条（/run?detail=steps 断点快照；fidelity 曲线走独立 Sweep 按钮）。 */
function renderBosonic(result, mode) {
  drawWignerResult(result);
  renderMetersPanel(result.backend, result.meters || {}); // R6: 矩阵驱动（原 logneg 硬编码 "—" 退役）
  $("nmode-tag").textContent = `nmode ${result.nmode}`;
  renderModeSelect(result.nmode, mode);
  renderBosonicSteps(result.steps);
}

function renderBosonicSteps(steps) {
  const slider = $("bos-step");
  const tag = $("bos-step-tag");
  const info = $("bos-step-info");
  const meters = $("bos-step-meters");
  const st = initStepState(steps, slider.value); // 滑条模型出自 leaf（票C）
  if (st.disabled) {
    slider.disabled = true;
    slider.max = 0;
    tag.textContent = "—";
    info.textContent = "（仅含测量/通道断点快照；纯高斯段并入首步）";
    meters.textContent = "";
    return;
  }
  slider.disabled = false;
  slider.max = String(st.max);
  slider.value = String(st.value); // 保底已在 leaf 内（停在末尾选最后一步）
  const show = (k) => {
    const s = steps[Number(k)];
    tag.textContent = stepLabel(k, steps);
    info.textContent = `${stepDesc(s.op)} · nmode ${s.nmode}`;
    meters.textContent = stepMeters(s.meters, fmt);
    // Step slider drives Wigner evolution, not only text meters.
    if (s.wigner) drawWignerResult({ wigner: s.wigner });
  };
  slider.oninput = () => show(slider.value);
  show(slider.value);
}

/* B6: fidelity sweep — 自动找第一个 loss 节点，Post /fidelity（bosonic 专属；
   沿用后端中 ψ?fixed seed，前端 rounds 平均）。 */
function drawFidSvg(xs, ys) {
  const svg = $("bos-fidelity-svg");
  const note = $("bos-fidelity-note");
  // Truncated GKP can overshoot numerically; clamp display only (curve.js yClamp).
  const pts = finitePoints(xs, ys, { yClamp: [0, 1] });
  note.hidden = false;
  if (pts.length === 0) {
    note.textContent = "无有效保真度点（检查 loss 节点）";
    svg.replaceChildren();
    return;
  }
  const W = svg.clientWidth || 560;
  const H = 200;
  const pad = { l: 46, r: 14, t: 14, b: 26 };
  const { x0, x1, ylo: y0, yhi: y1 } = plotDomain({ xs, ys, baseline: 0 });
  const { X, Y } = makeScale({ x0, x1, ylo: y0, yhi: y1, W, H, pad });
  const path = svgPath(pts, X, Y);
  const cy = Y(0);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  /* C2 R8：改用 replaceChildren + el()（原先拼 innerHTML 字符串后整段解析）。
     class 名与元素顺序保持逐字一致（style.css 的 .bosonic__grid-line /
     .bosonic__line / .bosonic__label 依赖它们）。用 textContent 而非 innerHTML
     填文本，中文标签不再经 HTML 解析。 */
  const kids = [
    el("line", { x1: 0, y1: cy, x2: W, y2: cy, class: "bosonic__grid-line" }),
    el("path", { d: path, fill: "none", class: "bosonic__line" }),
  ];
  for (const p of pts) {
    kids.push(el("circle", { cx: X(p.x).toFixed(1), cy: Y(p.y).toFixed(1), r: 3 }));
  }
  const tX = el("text", { x: pad.l, y: H - 6, class: "bosonic__label" });
  tX.textContent = "loss 透射率 T";
  const tY = el("text", { x: 8, y: pad.t, class: "bosonic__label" });
  tY.textContent = "F";
  kids.push(tX, tY);
  svg.replaceChildren(...kids);
  note.textContent = `fidelity vs loss T · ${pts.length} 点 · rounds 平均（同 seed 三个投点色块为随机相位）`;
  note.hidden = false;
}

async function runBosonicFidelity() {
  const state = editor.getState();
  const nodes = state.nodes;
  const lossSeq = nodes.find((n) => n.op === "loss");
  if (!lossSeq) {
    $("bos-fidelity-note").textContent = "需先在电路加一个 loss 节点（透射率 T 被扫描）";
    $("bos-fidelity-note").hidden = false;
    return;
  }
  const payload = toV1Json(state);
  const rounds = Math.max(1, Math.min(100, Number($("bos-rounds").value) || 5));
  payload.sweep = { node_id: lossSeq.id, param: "T", min: 0.5, max: 1.0, n: 7,
                    target: { state: $("bos-target").value, mode: 0 } };
  payload.rounds = rounds;
  setStatus(`fidelity sweep · loss=${lossSeq.id} · rounds=${rounds}`);
  const seq = seqGuard.next(); // 候选 2：fidelity 此前完全不设防，纳入 seq guard
  await requestLab("/fidelity", {
    payload, seq, guard: seqGuard,
    busy: busyRunSample,
    onOk: (body) => {
      drawFidSvg(body.xs, body.ys);
      setStatus(`fidelity · ${body.ys.filter((y) => y !== null).length} 点`);
    },
    onError: (e) => {
      const detail = e.detail || "fidelity sweep 失败";
      $("bos-fidelity-note").textContent = detail + "（详情可用 /run）";
      $("bos-fidelity-note").hidden = false;
      reportError(e, "fidelity sweep 失败");
    },
  });
}

/* R7 (ADR-0008 follow-up): per-backend 面板可见性表 — 后端差异知识单点
   （NOTES.md 已知债务：backend 条件散布收口，方向 = per-backend 配置表）。
   syncBackendPanels 唯一消费者；新后端 = 一行，不添 if。 */
const BACKEND_PANELS = {
  gaussian: { "scan-panel": true, "state-grid": true, "fock-panel": false, "fock-charts": false, "bosonic-panel": false, "meters-panel": true, "wigner-side": true },
  fock: { "scan-panel": false, "state-grid": false, "fock-panel": true, "fock-charts": true, "bosonic-panel": false, "meters-panel": false, "wigner-side": false },
  bosonic: { "scan-panel": false, "state-grid": false, "fock-panel": false, "fock-charts": false, "bosonic-panel": true, "meters-panel": true, "wigner-side": true },
};

/* C1 R3: 后端未变则面板可见性不可能变，故早退——但首次调用必须放行。
   调用点有两个：hooks.onState（每次 render 都跑）与 init() 首次同步。
   首屏时 lastPanelsBackend 还是 null（没有前值可比），故首次必然放行；
   若改成只看「与 state.backend 是否相同」，首屏面板就不会显隐。 */
let lastPanelsBackend = null;

function syncBackendPanels(backend) {
  const panels = BACKEND_PANELS[backend];
  if (!panels) return; // 未知 backend：保持现状（schema 门已拦，防御不摸 DOM）
  if (backend === lastPanelsBackend) return; // 后端未变 → hidden 已是目标态
  lastPanelsBackend = backend;
  for (const [id, visible] of Object.entries(panels)) $(id).hidden = !visible;
  fitWignerFrame(); // side 显隐变化 → 重算正方形画布
}

/* ── run pipeline: debounce (120ms) + seq guard ────────── */
const seqGuard = createSeqGuard(); // 收敛 app.js 的 seqCounter/latestSeq 两口
let debounceTimer = null;

const busyRunSample = makeRefCountedBusy((on) => {
  runBtn.disabled = on;
  sampleBtn.disabled = on;
  runBtn.setAttribute("aria-busy", String(on));
  sampleBtn.setAttribute("aria-busy", String(on));
});

const busyScan = makeRefCountedBusy((on) => {
  if (on) scanBtn.disabled = true;
  else refreshScanModesA(); // 复原 = 重评估（nmode>=2 才可点），非简单 disabled=false
});

function hideMeasurement() {
  measurementPanel.hidden = true;
}

function showMeasurement(body) {
  mSeed.textContent = String(body.seed);
  mSingularNote.hidden = !(body.meters && body.meters.singular);
  mOutcomes.replaceChildren();
  for (const m of body.measured || []) {
    const li = document.createElement("li");
    li.textContent = outcomeText(m);
    mOutcomes.appendChild(li);
  }
  measurementPanel.hidden = false;
  measurementPanel.scrollIntoView({ block: "nearest" }); // panel sits below V table; bring it into view
}

/* R7: per-backend run 请求体扩展 — bosonic 一次拉全部分步快照
   （断点中间态）；gaussian/fock 无扩展。知识单点（原三元式散在 doRun）。 */
const RUN_BODY_EXTENSIONS = {
  bosonic: { detail: "steps" },
};

async function doRun(circuitJson, seq) {
  const t0 = performance.now();
  const payload = { ...circuitJson, ...(RUN_BODY_EXTENSIONS[circuitJson.backend] ?? {}) };
  await requestLab("/run", {
    payload, seq, guard: seqGuard,
    busy: busyRunSample,
    onOk: (body) => {
      render(body, circuitJson.view?.wigner_mode);
      hideMeasurement(); // analytic view: manual run / param change leaves sample view
      setStatus(`ok · ${(performance.now() - t0).toFixed(0)} ms`);
    },
    onError: (e) => reportError(e, "运行失败"),
  });
}

async function doSample(seq) {
  const t0 = performance.now();
  const payload = toV1Json(editor.getState());
  payload.view.wigner_mode = Number(modeSelect.value) || 0;
  payload.seed = Number(seedInput.value);
  await requestLab("/sample", {
    payload, seq, guard: seqGuard,
    busy: busyRunSample,
    validate: validateSeed,
    onOk: (body) => {
      render(body, payload.view.wigner_mode);
      showMeasurement(body);
      seedInput.value = body.seed;
      setStatus(`sampled · seed ${body.seed} · ${(performance.now() - t0).toFixed(0)} ms`);
    },
    onError: (e) => reportError(e, "抽样失败"),
  });
}

function scheduleRun(circuitJson) {
  const seq = seqGuard.next();
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => doRun(circuitJson, seq), 120);
}

/* ── scan panel (L4, F-LAB-SCAN) ──────────────────────── */
/* C1 R2: 脏键 = 「可 sweep 节点身份集合」+ nmode，**不是 nodes 数组引用**。
   引用比较不可能命中：onParam 用 state.nodes.map(...) 重构数组，map 无论元素
   是否变化都返回新数组，故每次滑条事件都是新引用 → 永不早退（实测：代码看似
   改了、行为完全没变）。这里只取列表真正依赖的东西——哪些节点可 sweep 即
   其 (id, op)，参数**值**不进列表。故拖滑条（id/op 不变）命中早退，
   增删节点 / 改 op / 增删模（都在键里）则重建。 */
let lastScanKey = null;

function scanNodeListKey() {
  const st = editor.getState();
  const sig = st.nodes
    .filter((n) => Object.values(OPS[n.op]?.params || {}).some((d) => Array.isArray(d.sweep)))
    .map((n) => `${n.id}:${n.op}`)
    .join(",");
  return `${st.nmode}|${sig}`;
}

function refreshScanNodes() {
  const key = scanNodeListKey();
  if (key === lastScanKey) return; // 列表输入未变 → <option> 已是目标态
  lastScanKey = key;
  const nodes = editor.getState().nodes.filter((n) =>
    Object.values(OPS[n.op]?.params || {}).some((d) => Array.isArray(d.sweep)));
  const prev = scanNode.value;
  scanNode.replaceChildren();
  for (const n of nodes) {
    const opt = document.createElement("option");
    opt.value = n.id;
    opt.textContent = `${n.id} · ${OPS[n.op].label}`;
    if (n.id === prev) opt.selected = true;
    scanNode.appendChild(opt);
  }
  if (nodes.length && !scanNode.value) scanNode.value = nodes[0].id;
  refreshScanParams();
  refreshScanModesA();
}

function refreshScanParams() {
  const node = editor.getState().nodes.find((n) => n.id === scanNode.value);
  const meta = node && OPS[node.op];
  const keys = meta
    ? Object.keys(meta.params).filter((k) => Array.isArray(meta.params[k].sweep))
    : [];
  const prev = scanParam.value;
  scanParam.replaceChildren();
  for (const k of keys) {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = k;
    if (k === prev) opt.selected = true;
    scanParam.appendChild(opt);
  }
  if (keys.length && !scanParam.value) scanParam.value = keys[0];
  if (scanParam.value !== prev) applyScanDefaults(); // (re)selected param → adaptive range
}

function applyScanDefaults() {
  const node = editor.getState().nodes.find((n) => n.id === scanNode.value);
  const d = node && OPS[node.op]?.params?.[scanParam.value];
  if (!d || !Array.isArray(d.sweep)) return;
  scanMin.value = d.sweep[0];
  scanMax.value = d.sweep[1];
  scanN.value = 50;
}

function refreshScanModesA() {
  const nmode = editor.getState().nmode;
  const prev = scanModesA.value;
  scanModesA.replaceChildren();
  for (let k = 1; k <= nmode - 1; k++) {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = `[0..${k - 1}]`;
    if (String(k) === prev) opt.selected = true;
    scanModesA.appendChild(opt);
  }
  if (!scanModesA.value && scanModesA.options.length) scanModesA.options[0].selected = true;
  scanNote.hidden = nmode >= 2;
  if (nmode < 2) scanNote.textContent = "E_N 需要至少 2 个模式（先点「＋模」加一个）";
  scanBtn.disabled = nmode < 2 || !scanNode.options.length;
}

function drawScanCurve(body) {
  const xs = body.xs;
  const ys = body.ys;
  const W = 320, H = 150, padL = 34, padR = 10, padT = 10, padB = 18;
  const finite = finitePoints(xs, ys); // scan 模式无钳制（E_N 无定义处 null → gap）
  if (!finite.length) {
    scanSvg.replaceChildren();
    scanNote.hidden = false;
    scanNote.textContent = "E_N 无定义（扫描范围内没有有限值）";
    const sum = $("scan-summary");
    sum.hidden = true;
    sum.textContent = "";
    return;
  }
  scanNote.hidden = true;
  const { x0, x1, ylo, yhi } = plotDomain({ xs, ys, yPad: 0.1 });
  const ymin = Math.min(...finite.map((p) => p.y)); // 摘要行仍要数据域（非绘图域）
  const ymax = Math.max(...finite.map((p) => p.y));
  /* #8: 折叠摘要一行结果（折叠后仍可见）。finitePoints 返回 {x,y} 对象
     （同 fidelity 路径 pts），勿按 pair 数组解构 —— 探针 lab_scan_probe 曾
     因此报 object is not iterable。 */
  const iMax = finite.findIndex((p) => p.y === ymax);
  const sum = $("scan-summary");
  // OCR: finite 非空已提前 return，ymax 取自同一数组 → findIndex 必命中，无 else 分支
  sum.hidden = false;
  sum.textContent = `E_N 最大 ${axisVal(ymax)} @ ${scanParam.value}=${axisVal(finite[iMax].x)}`;
  const { X, Y } = makeScale({ x0, x1, ylo, yhi, W, H, pad: { l: padL, r: padR, t: padT, b: padB } });
  const style = getComputedStyle(document.documentElement);
  const rule = style.getPropertyValue("--color-rule").trim();
  const ink = style.getPropertyValue("--color-ink").trim();
  const accent = style.getPropertyValue("--color-accent").trim();
  scanSvg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  scanSvg.replaceChildren();
  for (let i = 0; i <= 4; i++) { // grid
    const gx = padL + (i / 4) * (W - padL - padR);
    scanSvg.append(el("line", { x1: gx, y1: padT, x2: gx, y2: H - padB, stroke: rule, "stroke-width": 1 }));
    const gy = padT + (i / 4) * (H - padT - padB);
    scanSvg.append(el("line", { x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: rule, "stroke-width": 1 }));
  }
  const slots = xs.map((x, i) => (typeof ys[i] === "number" && Number.isFinite(ys[i]) ? [x, ys[i]] : null));
  for (const seg of polylineSegments(slots, X, Y, xs.length)) {
    scanSvg.append(el("polyline", { points: seg, fill: "none", stroke: accent, "stroke-width": 1.5 }));
  }
  const label = (tx, ty, anchor, text) => {
    const t = el("text", { x: tx, y: ty, "text-anchor": anchor, fill: ink });
    t.textContent = text;
    return t;
  };
  scanSvg.append(
    label(padL, H - 4, "start", axisVal(x0)),
    label(W - padR, H - 4, "end", axisVal(x1)),
    label(padL - 6, padT + 4, "end", axisVal(yhi)),
    label(padL - 6, H - padB, "end", axisVal(ylo)),
  );
}

async function doScan() {
  const seq = seqGuard.next(); // supersede pending run/sample/scan; stale responses dropped
  const state = editor.getState();
  const node = state.nodes.find((n) => n.id === scanNode.value);
  const param = scanParam.value;
  const d = node && OPS[node.op]?.params?.[param];
  const pmin = Number(scanMin.value);
  const pmax = Number(scanMax.value);
  const n = Number(scanN.value);
  const msg = validateScanForm({ hasSweepParam: !!(node && d && Array.isArray(d.sweep)), min: pmin, max: pmax, n });
  if (msg) {
    setStatus(msg, false);
    return;
  }
  const k = Number(scanModesA.value) || 1;
  const modesA = Array.from({ length: k }, (_, i) => i);
  const payload = toV1Json(state);
  payload.view.wigner_mode = Number(modeSelect.value) || 0;
  payload.sweep = { node_id: node.id, param, min: pmin, max: pmax, n, modes_A: modesA };
  /* #8: scan 前置为空（旧摘要失效） */
  const scanSummary = $("scan-summary");
  scanSummary.hidden = true;
  scanSummary.textContent = "";
  const t0 = performance.now();
  await requestLab("/scan", {
    payload, seq, guard: seqGuard,
    busy: busyScan,
    onOk: (body) => {
      drawScanCurve(body);
      scanSvg.scrollIntoView({ block: "nearest" }); // 曲线可能在折叠面板下方——滚到可见
      setStatus(`scan ok · ${body.ys.length} 点 · ${(performance.now() - t0).toFixed(0)} ms`);
    },
    onError: (e) => reportError(e, "扫描失败"),
  });
}

/* F7: Batch 1000（固定 shots，/batch 端点）— 双色叠画采样对照 */
async function doBatch() {
  const seq = seqGuard.next();
  const t0 = performance.now();
  const payload = toV1Json(editor.getState());
  payload.shots = 1000;
  payload.seed = Number(seedInput.value);
  await requestLab("/batch", {
    payload, seq, guard: seqGuard,
    busy: busyRunSample,
    validate: validateSeed,
    onOk: (body) => {
      fockPanel.renderBatch(body);
      setStatus(`batch ${body.shots} shots · seed ${body.seed} · ${(performance.now() - t0).toFixed(0)} ms`);
    },
    onError: (e) => reportError(e, "批量抽样失败"),
  });
}

/* ── editor wiring ─────────────────────────────────────── */
const fockPanel = initFockPanel(document, {
  getState: () => editor.getState(),
  setCircuit: (patch) => editor.setCircuit(patch),
  setJointModes: (modes) => editor.setView({ joint_modes: modes }),
  onBatch: doBatch,
  onStatus: setStatus,
});

const editor = initEditor(document.querySelector(".workbench"), {
  defaultScene: DEFAULT_SCENE,
  onRun: scheduleRun,
  onState: (state) => { refreshScanNodes(); syncBackendPanels(state.backend); }, // sweep selects mirror the graph
  onStatus: setStatus,
  onPickSweep: (id) => {
    // L5: opening a sweepable gate's param card syncs the scan target
    if (scanNode.querySelector(`option[value="${id}"]`)) {
      scanNode.value = id;
      refreshScanParams();
    }
  },
});

scanNode.addEventListener("change", refreshScanParams);
scanParam.addEventListener("change", applyScanDefaults);
scanBtn.addEventListener("click", doScan);

runBtn.addEventListener("click", () => {
  clearTimeout(debounceTimer); // manual run supersedes pending debounced payload
  debounceTimer = null;
  const payload = toV1Json(editor.getState());
  payload.view.wigner_mode = Number(modeSelect.value) || 0;
  doRun(payload, seqGuard.next()); // manual run: immediate, no debounce
});

sampleBtn.addEventListener("click", () => {
  clearTimeout(debounceTimer); // sample supersedes pending debounced run
  debounceTimer = null;
  doSample(seqGuard.next()); // Measure once: immediate
});

/* ── Save / Load (A5) ──────────────────────────────────── */
saveBtn.addEventListener("click", () => {
  const payload = toV1Json(editor.getState());
  payload.view.wigner_mode = Number(modeSelect.value) || 0;
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "circuit_v1.json";
  a.click();
  URL.revokeObjectURL(url);
  setStatus("已保存 circuit_v1.json");
});

loadInput.addEventListener("change", async () => {
  const file = loadInput.files && loadInput.files[0];
  if (!file) {
    setStatus("载入失败: 未选择文件", false);
    return;
  }
  let payload;
  try {
    payload = JSON.parse(await file.text());
  } catch {
    setStatus("载入失败: JSON 解析错误", false);
    loadInput.value = "";
    return;
  }
  const res = loadJson(payload);
  if (res.error) {
    setStatus("载入失败: " + res.error, false); // current circuit untouched
    loadInput.value = "";
    return;
  }
  seedInput.value = res.state.seed;
  modeSelect.value = String(res.state.view.wigner_mode);
  editor.setState(res.state); // renders + auto /run (debounced)
  loadInput.value = "";
  setStatus("载入成功，自动运行");
});

modeSelect.addEventListener("change", () => {
  // route through editor so JSON textarea stays in sync (OCR finding)
  editor.setView({ wigner_mode: Number(modeSelect.value) || 0 });
});

async function init() {
  /* 票3: 先拉 /schema —— 单一事实源注入（ops/initial/editor 合并层）。
     失败显式红条挡板（不静默降级，frozen-graph 纪律）：editor 不初始化
     palette，不 boot 运行按钮。schema 载荷 = 票2 assemble_schema() 输出。 */
  let schemaOk = false;
  try {
    const schema = await (await fetch("/schema")).json();
    // 单点注入（schema_store.js leaf）：各消费方派生自己的表（票3 seam）。
    // 单点注入（schema_store.js leaf）：三派生先全部成功再一次性
    // publish（review F3：若 setEditorSchema 在 publishSchema 后抛，
    // store 非 null 而 editor 回退 → 静默混用；全前置消陙窗口）。
    const dEt = deriveEditorTables(schema);
    setEditorSchema(schema);   // editor.js 校验边界派生（先派生+内验）
    setInitialSchema(schema);   // initial.js 名单派生
    // 票 4: palette 托盘也走派生表（deriveOps——ops.js 手写 backends
    // 字段已删；v0 退役后 backends 经 schema 单点收发，见 ADR-0011）。
    publishSchema(schema, {
      uiToOp: Object.fromEntries(Object.entries(dEt.irToUi).map(([ir, ui]) => [ui, ir])),
      uiToParam: dEt.v1ToUiParam,
      fockUiToParam: dEt.fockV1ToUiParam,
      ops: deriveOps(schema),
    });
    schemaOk = true;
  } catch {
    setStatus("后端 schema 不可用：/schema 拉取失败 — 请检查服务是否启动", false);
  }
  try {
    const h = await (await fetch("/health")).json();
    $("version-tag").textContent = "cvsim " + h.cvsim + " · " + h.schema;
  } catch { /* offline header keeps the — */ }
  if (schemaOk) {
    syncBackendPanels(editor.getState().backend);
    editor.render();
    refreshScanNodes();
    const bosFid = $("bos-fidelity-btn");
    if (bosFid) bosFid.addEventListener("click", runBosonicFidelity);
    const bosTrg = $("bos-target");
    if (bosTrg) bosTrg.addEventListener("change", runBosonicFidelity);
  } else {
    // 红条已挂：按钮全部禁用。恢复路径 = 手动刷新页面（重拉 /schema；
    // 页内无重试控件——init() 已返回，注入不可恢复，票 3 范围内诚实标注）
    for (const id of ["run-btn", "sample-btn", "scan-btn", "save-btn", "fidelity-btn", "bos-fidelity-btn"]) {
      const el = $(id);
      if (el) el.disabled = true;
    }
  }
}

init();
