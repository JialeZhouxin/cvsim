/* Gaussian Lab workbench — state flow, zero deps. */
"use strict";

const DEFAULT_JSON = {
  schema: "circuit_v0",
  seed: 0,
  nodes: [
    { id: "s0", op: "tmsv", params: { r: 0.6 }, modes: [0, 1] },
    { id: "l0", op: "loss", params: { T: 0.8 }, mode: 0 },
    { id: "l1", op: "loss", params: { T: 0.8 }, mode: 1 },
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
const jsonInput = $("json-input");
const runBtn = $("run-btn");
const resetBtn = $("reset-btn");
const canvas = $("wigner-canvas");
const colorbar = $("colorbar-canvas");
const statusEl = $("status");

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

function render(result, mode) {
  const { x, p, W } = result.wigner;
  drawHeatmap(W);
  $("axis-x-min").textContent = fmt(x[0], 3);
  $("axis-x-max").textContent = fmt(x[x.length - 1], 3);
  $("axis-y-min").textContent = fmt(p[0], 3);
  $("axis-y-max").textContent = fmt(p[p.length - 1], 3);
  $("wigner-mode-label").textContent = "mode " + (mode ?? "—");

  const m = result.meters;
  $("m-purity").textContent = fmt(m.purity);
  $("m-nbar").textContent = fmt(m.mean_photon);
  $("m-logneg").textContent = m.log_negativity === undefined ? "—" : fmt(m.log_negativity);

  $("nmode-tag").textContent = `nmode ${result.nmode}`;
  const nm = result.nmode;
  const modeHead = (i) => `mode ${Math.floor(i / 2)}·${i % 2 === 0 ? "x" : "p"}`;
  renderMatrix($("rbar-table"), nm * 2, 1, modeHead, (r) => fmt(result.rbar[r]));
  renderMatrix($("v-table"), nm * 2, nm * 2, modeHead, (r, c) => fmt(result.V[r][c]));
}

async function run() {
  let circuit;
  try {
    circuit = JSON.parse(jsonInput.value);
  } catch (e) {
    setStatus("JSON 语法错误: " + e.message, false);
    return;
  }
  runBtn.disabled = true;
  resetBtn.disabled = true;
  runBtn.setAttribute("aria-busy", "true");
  const t0 = performance.now();
  try {
    const resp = await fetch("/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(circuit),
    });
    const body = await resp.json();
    if (!resp.ok) {
      setStatus(resp.status + " · " + (body.detail || "运行失败"), false);
      return;
    }
    render(body, circuit.view?.wigner_mode);
    setStatus(`ok · ${(performance.now() - t0).toFixed(0)} ms`);
  } catch (e) {
    setStatus("网络错误: " + e.message, false);
  } finally {
    runBtn.disabled = false;
    resetBtn.disabled = false;
    runBtn.removeAttribute("aria-busy");
  }
}

function reset() {
  jsonInput.value = JSON.stringify(DEFAULT_JSON, null, 2);
  run();
}

async function init() {
  try {
    const h = await (await fetch("/health")).json();
    $("version-tag").textContent = "cvsim " + h.cvsim + " · " + h.schema;
  } catch { /* offline header keeps the — */ }
  resetBtn.addEventListener("click", reset);
  runBtn.addEventListener("click", run);
  reset();
}

init();
