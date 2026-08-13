/* Gaussian Lab workbench — L1 render pipeline + L2 editor wiring. */
"use strict";

import { initEditor, loadJson } from "./editor.js";
import { OPS, sourceModes, toV1Json } from "./ops.js";
import { initFockPanel } from "./fock.js";

/* L5.5 默认场景：两个真空模 + 两个位移器（coherent 态两路）@ x=0 */
const DEFAULT_JSON = {
  schema: "circuit_v0",
  seed: 0,
  nodes: [
    { id: "s0", op: "vacuum", params: { nmode: 1 } },
    { id: "s1", op: "vacuum", params: { nmode: 1 } },
    { id: "d0", op: "displace", params: { alpha: 1.0 }, mode: 0, ui: { x: 0 } },
    { id: "d1", op: "displace", params: { alpha: 1.0 }, mode: 1, ui: { x: 0 } },
  ],
  edges: [],
  view: { wigner_mode: 0, lim: 5.0, n: 64 },
  ui: {},
};

/* inferno-style LUT anchors (matplotlib inferno, 16 samples) — physics-data
   convention, independent of theme tokens. Interpolated to 256 in JS. */
const LUT_ANCHORS = [
  [0, 0, 4], [31, 4, 55], [63, 8, 104], [96, 13, 128],
  [129, 20, 138], [161, 28, 133], [189, 38, 113], [213, 48, 89],
  [233, 59, 66], [250, 75, 47], [253, 100, 36], [252, 128, 34],
  [246, 158, 42], [231, 189, 58], [207, 221, 79], [164, 252, 105],
];

function buildLut() {
  const lut = new Uint8Array(256 * 3);
  const last = LUT_ANCHORS.length - 2;
  for (let i = 0; i < 256; i++) {
    // scale over len-1 so the final sample reaches the last anchor (f = 1)
    const t = (i / 255) * (LUT_ANCHORS.length - 1);
    const k = Math.min(Math.floor(t), last);
    const f = t - k;
    for (let c = 0; c < 3; c++) {
      lut[i * 3 + c] = Math.round(LUT_ANCHORS[k][c] + f * (LUT_ANCHORS[k + 1][c] - LUT_ANCHORS[k][c]));
    }
  }
  return lut;
}
const LUT = buildLut();

const $ = (id) => document.getElementById(id);
const canvas = $("wigner-canvas");
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

function fmt(x, digits = 5) {
  if (typeof x !== "number" || !Number.isFinite(x)) return "—";
  return x.toPrecision(digits);
}

function renderMatrix(table, rows, cols, head, cell) {
  let html = "<thead><tr><th></th>" + Array.from({ length: cols }, (_, c) => `<th class="mono">${head(c)}</th>`).join("") + "</tr></thead><tbody>";
  for (let r = 0; r < rows; r++) {
    html += "<tr><th class=\"mono mat__rowhead\">" + head(r) + "</th>";
    for (let c = 0; c < cols; c++) html += `<td class="mono">${cell(r, c)}</td>`;
    html += "</tr>";
  }
  table.innerHTML = html + "</tbody>";
}

function drawHeatmap(W) {
  if (!Array.isArray(W) || W.length < 2 || W.length > 512 ||
      W.some((row) => !Array.isArray(row) || row.length !== W.length ||
        row.some((v) => !Number.isFinite(v)))) {
    throw new Error("Invalid Wigner grid");
  }
  const n = W.length;
  canvas.width = n;
  canvas.height = n;
  const ctx = canvas.getContext("2d");
  let wmin = Infinity, wmax = -Infinity;
  for (const row of W) for (const v of row) { if (v < wmin) wmin = v; if (v > wmax) wmax = v; }
  const span = wmax - wmin || 1;
  /* #6: colorbar min/max 刻度（axisVal 格式，与坐标轴一致） */
  $("colorbar-max").textContent = axisVal(wmax);
  $("colorbar-min").textContent = axisVal(wmin);
  const img = ctx.createImageData(n, n);
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const t = Math.min(255, Math.max(0, Math.round(((W[j][i] - wmin) / span) * 255)));
      const o = (j * n + i) * 4;
      img.data[o] = LUT[t * 3];
      img.data[o + 1] = LUT[t * 3 + 1];
      img.data[o + 2] = LUT[t * 3 + 2];
      img.data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  /* colorbar */
  const cb = colorbar.getContext("2d");
  for (let k = 0; k < 128; k++) {
    const t = Math.round((k / 127) * 255);
    cb.fillStyle = `rgb(${LUT[t * 3]},${LUT[t * 3 + 1]},${LUT[t * 3 + 2]})`;
    cb.fillRect(0, 127 - k, 8, 1);
  }
}

/* SVG overlay axes — drawn at display resolution (canvas is 64 physical px
   scaled up, so canvas strokes would blur/thicken). Solid 1px lines in
   ice-cyan (--color-axis, complementary to inferno), values in ink with a
   paper halo (paint-order: stroke) so they read on any heatmap region. */
const SVG_NS = "http://www.w3.org/2000/svg";
let lastLim = 5;

function el(tag, attrs) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

function axisVal(v) {
  if (!Number.isFinite(v)) return "—";
  let s = v.toPrecision(3);
  if (s.includes(".")) s = s.replace(/\.?0+$/, "");
  return s;
}

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

new ResizeObserver(() => drawAxes(lastLim)).observe(canvas);

function render(result, mode) {
  /* #8: 新 run 使旧 scan 摘要失效——折叠摘要清空 */
  const scanSummary = $("scan-summary");
  scanSummary.hidden = true;
  scanSummary.textContent = "";
  if (result.backend === "fock") {
    renderFock(result, mode);
    return;
  }
  drawWignerResult(result);

  const m = result.meters;
  $("m-purity").textContent = fmt(m.purity);
  $("m-nbar").textContent = fmt(m.mean_photon);
  $("m-logneg").textContent = m.log_negativity === undefined ? "—" : fmt(m.log_negativity);

  $("nmode-tag").textContent = `nmode ${result.nmode}`;
  const nm = result.nmode;
  /* backend covariance layout is split: [x0..x_{m-1}, p0..p_{m-1}] —
     label rows/cols in that order (interleaved xpxpxp would mislabel m≥2) */
  const modeHead = (i) => `mode ${i < nm ? i : i - nm}·${i < nm ? "x" : "p"}`;
  renderMatrix($("rbar-table"), nm * 2, 1, modeHead, (r) => fmt(result.rbar[r]));
  renderMatrix($("v-table"), nm * 2, nm * 2, modeHead, (r, c) => fmt(result.V[r][c]));

  renderModeSelect(nm, mode);
}

/** Shared Wigner draw (gaussian + fock paths). */
function drawWignerResult(result) {
  if (!result.wigner) {
    // singular conditional state: no finite Wigner, never fabricated
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cb = colorbar.getContext("2d");
    cb.clearRect(0, 0, 8, 128);
    $("colorbar-max").textContent = "—";
    $("colorbar-min").textContent = "—";
    $("axis-svg").replaceChildren();
    wignerNote.hidden = false;
  } else {
    wignerNote.hidden = true;
    const { x, p, W } = result.wigner;
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

function syncBackendPanels(backend) {
  const fock = backend === "fock";
  $("scan-panel").hidden = fock;   // v0 无 Fock scan（/scan+fock → 422）
  $("state-grid").hidden = fock;   // Fock 无 r̄/V 表（态摘要走护栏卡）
  $("meters-panel").hidden = fock; // Fock meters 在护栏卡
  $("fock-panel").hidden = !fock;
}

/* ── run pipeline: debounce (120ms) + seq guard ────────── */
let seqCounter = 0; // sole sequence source (OCR: editor's own seq was colliding)
let latestSeq = 0;
let debounceTimer = null;
let busy = false;

function setBusy(b) {
  busy = b;
  runBtn.disabled = b;
  sampleBtn.disabled = b;
  runBtn.setAttribute("aria-busy", String(b));
  sampleBtn.setAttribute("aria-busy", String(b));
}

function hideMeasurement() {
  measurementPanel.hidden = true;
}

function showMeasurement(body) {
  mSeed.textContent = String(body.seed);
  mSingularNote.hidden = !(body.meters && body.meters.singular);
  mOutcomes.replaceChildren();
  for (const m of body.measured || []) {
    const li = document.createElement("li");
    const out = Array.isArray(m.outcome)
      ? `(${m.outcome.map((v) => Number(v).toFixed(4)).join(", ")})`
      : (Number.isInteger(m.outcome) ? String(m.outcome) : Number(m.outcome).toFixed(4));
    const phi = m.phi !== undefined ? ` φ=${Number(m.phi).toFixed(3)}` : "";
    const nm = m.name !== undefined ? ` ${m.name}` : "";
    li.textContent = `${m.op}${nm} · mode ${m.mode}${phi} → ${out}`;
    mOutcomes.appendChild(li);
  }
  measurementPanel.hidden = false;
  measurementPanel.scrollIntoView({ block: "nearest" }); // panel sits below V table; bring it into view
}

async function doRun(circuitJson, seq) {
  setBusy(true);
  const t0 = performance.now();
  try {
    const resp = await fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(circuitJson),
    });
    const body = await resp.json();
    if (seq !== latestSeq) return; // stale response: drop
    if (!resp.ok) {
      setStatus(resp.status + " · " + (body.detail || "运行失败"), false);
      return;
    }
    render(body, circuitJson.view?.wigner_mode);
    hideMeasurement(); // analytic view: manual run / param change leaves sample view
    setStatus(`ok · ${(performance.now() - t0).toFixed(0)} ms`);
  } catch (e) {
    if (seq !== latestSeq) return;
    setStatus("网络错误: " + e.message, false);
  } finally {
    if (seq === latestSeq) setBusy(false); // stale request must not clear busy
  }
}

async function doSample(seq) {
  setBusy(true);
  const t0 = performance.now();
  try {
    const payload = toV1Json(editor.getState());
    payload.view.wigner_mode = Number(modeSelect.value) || 0;
    payload.seed = Number(seedInput.value);
    if (!Number.isInteger(payload.seed) || payload.seed < 0) {
      if (seq !== latestSeq) return;
      setStatus("seed 必须是非负整数", false);
      return;
    }
    const resp = await fetch("/sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await resp.json();
    if (seq !== latestSeq) return; // stale response: drop
    if (!resp.ok) {
      setStatus(resp.status + " · " + (body.detail || "抽样失败"), false);
      return;
    }
    render(body, payload.view.wigner_mode);
    showMeasurement(body);
    seedInput.value = body.seed;
    setStatus(`sampled · seed ${body.seed} · ${(performance.now() - t0).toFixed(0)} ms`);
  } catch (e) {
    if (seq !== latestSeq) return;
    setStatus("网络错误: " + e.message, false);
  } finally {
    if (seq === latestSeq) setBusy(false); // stale request must not clear busy
  }
}

function scheduleRun(circuitJson) {
  latestSeq = ++seqCounter;
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => doRun(circuitJson, latestSeq), 120);
}

/* ── scan panel (L4, F-LAB-SCAN) ──────────────────────── */
function refreshScanNodes() {
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
  const nmode = sourceModes(editor.getState().nodes);
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
  if (nmode < 2) scanNote.textContent = "E_N 需要至少 2 个模式（先添加 TMSV 或多模源）";
  scanBtn.disabled = nmode < 2 || !scanNode.options.length;
}

function drawScanCurve(body) {
  const xs = body.xs;
  const ys = body.ys;
  const W = 320, H = 150, padL = 34, padR = 10, padT = 10, padB = 18;
  const finite = [];
  for (let i = 0; i < ys.length; i++) {
    if (typeof ys[i] === "number" && Number.isFinite(ys[i])) finite.push([xs[i], ys[i]]);
  }
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
  const ymin = Math.min(...finite.map(([, y]) => y));
  const ymax = Math.max(...finite.map(([, y]) => y));
  /* #8: 折叠摘要一行结果（折叠后仍可见） */
  const iMax = finite.findIndex(([, y]) => y === ymax);
  const sum = $("scan-summary");
  // OCR: finite 非空已提前 return，ymax 取自同一数组 → findIndex 必命中，无 else 分支
  sum.hidden = false;
  sum.textContent = `E_N 最大 ${axisVal(ymax)} @ ${scanParam.value}=${axisVal(finite[iMax][0])}`;
  const ylo = ymin === ymax ? ymin - 0.5 : ymin - (ymax - ymin) * 0.1;
  const yhi = ymin === ymax ? ymin + 0.5 : ymax + (ymax - ymin) * 0.1;
  const x0 = xs[0], x1 = xs[xs.length - 1];
  const X = (x) => padL + ((x - x0) / (x1 - x0)) * (W - padL - padR);
  const Y = (y) => padT + (1 - (y - ylo) / (yhi - ylo)) * (H - padT - padB);
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
  let seg = ""; // null ys → break the polyline (curve gap)
  for (let i = 0; i < ys.length; i++) {
    if (typeof ys[i] !== "number" || !Number.isFinite(ys[i])) {
      if (seg) { scanSvg.append(el("polyline", { points: seg, fill: "none", stroke: accent, "stroke-width": 1.5 })); seg = ""; }
      continue;
    }
    seg += (seg ? " " : "") + X(xs[i]).toFixed(2) + "," + Y(ys[i]).toFixed(2);
  }
  if (seg) scanSvg.append(el("polyline", { points: seg, fill: "none", stroke: accent, "stroke-width": 1.5 }));
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
  latestSeq = ++seqCounter; // supersede pending run/sample/scan; stale responses dropped
  const seq = latestSeq;
  const state = editor.getState();
  const node = state.nodes.find((n) => n.id === scanNode.value);
  const param = scanParam.value;
  const d = node && OPS[node.op]?.params?.[param];
  if (!node || !d || !Array.isArray(d.sweep)) {
    setStatus("扫参：请先选择有可扫参数的节点", false);
    return;
  }
  const pmin = Number(scanMin.value);
  const pmax = Number(scanMax.value);
  const n = Number(scanN.value);
  if (!Number.isFinite(pmin) || !Number.isFinite(pmax) || pmin >= pmax) {
    setStatus("扫参：min 必须是有限数且 < max", false);
    return;
  }
  if (!Number.isInteger(n) || n < 2 || n > 200) {
    setStatus("扫参：n 必须是 2–200 的整数", false);
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
  scanBtn.disabled = true;
  const t0 = performance.now();
  try {
    const resp = await fetch("/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await resp.json();
    if (seq !== latestSeq) return; // stale scan response: drop
    if (!resp.ok) {
      setStatus(resp.status + " · " + (body.detail || "扫描失败"), false);
      return;
    }
    drawScanCurve(body);
    scanSvg.scrollIntoView({ block: "nearest" }); // 曲线可能在折叠面板下方——滚到可见
    setStatus(`scan ok · ${body.ys.length} 点 · ${(performance.now() - t0).toFixed(0)} ms`);
  } catch (e) {
    setStatus("网络错误: " + e.message, false);
  } finally {
    if (seq === latestSeq) refreshScanModesA(); // stale request must not touch UI
  }
}

/* F7: Batch 1000（固定 shots，/batch 端点）— 双色叠画采样对照 */
async function doBatch() {
  latestSeq = ++seqCounter;
  const seq = latestSeq;
  setBusy(true);
  const t0 = performance.now();
  try {
    const payload = toV1Json(editor.getState());
    payload.shots = 1000;
    const resp = await fetch("/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await resp.json();
    if (seq !== latestSeq) return; // stale response: drop
    if (!resp.ok) {
      setStatus(resp.status + " · " + (body.detail || "批量抽样失败"), false);
      return;
    }
    fockPanel.renderBatch(body);
    setStatus(`batch ${body.shots} shots · seed ${body.seed} · ${(performance.now() - t0).toFixed(0)} ms`);
  } catch (e) {
    if (seq !== latestSeq) return;
    setStatus("网络错误: " + e.message, false);
  } finally {
    if (seq === latestSeq) setBusy(false); // stale request must not clear busy
  }
}

/* ── editor wiring ─────────────────────────────────────── */
const fockPanel = initFockPanel($("fock-panel"), {
  getState: () => editor.getState(),
  setCircuit: (patch) => editor.setCircuit(patch),
  setJointModes: (modes) => editor.setView({ joint_modes: modes }),
  onBatch: doBatch,
  onStatus: setStatus,
});

const editor = initEditor(document.querySelector(".workbench"), {
  defaultScene: DEFAULT_JSON,
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
  latestSeq = ++seqCounter;
  doRun(payload, latestSeq); // manual run: immediate, no debounce
});

sampleBtn.addEventListener("click", () => {
  clearTimeout(debounceTimer); // sample supersedes pending debounced run
  debounceTimer = null;
  latestSeq = ++seqCounter;
  doSample(latestSeq); // Measure once: immediate
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
  try {
    const h = await (await fetch("/health")).json();
    $("version-tag").textContent = "cvsim " + h.cvsim + " · " + h.schema;
  } catch { /* offline header keeps the — */ }
  syncBackendPanels(editor.getState().backend);
  editor.render();
  refreshScanNodes();
}

init();
