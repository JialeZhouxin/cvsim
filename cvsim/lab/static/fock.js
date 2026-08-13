/* Gaussian Lab F7 — Fock result panel: PNR 分布柱 + joint 2D heatmap +
   Batch 1000 采样对照 + 截断护栏 + outcomes。
   Pure helpers (histBars/overlayHeat/leakInfo/…) are ESM-exported for
   node --test; DOM work lives only inside initFockPanel. */
"use strict";

import { sourceModes } from "./ops.js";

/* ── pure logic ─────────────────────────────────────────── */

/** Bar data: theory probs vs sample frequencies, capped at 30 entries.
    counts=null → sample bars 0 (theory-only view). */
export function histBars(probs, counts, shots) {
  const n = Math.min(30, Math.max(probs.length, counts ? counts.length : 0));
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      n: i,
      theory: probs[i] ?? 0,
      sample: counts && shots > 0 ? (counts[i] ?? 0) / shots : 0,
    });
  }
  return out;
}

/** Flat counts → 2D row-major grid (backend grid.ravel() order). null on
    length mismatch. */
export function reshapeCounts(counts, shape) {
  if (!Array.isArray(counts) || !Array.isArray(shape) || shape.length !== 2) return null;
  const [r, c] = shape;
  if (counts.length !== r * c) return null;
  const out = [];
  for (let i = 0; i < r; i++) out.push(counts.slice(i * c, (i + 1) * c).map(Number));
  return out;
}

/** 2D marginal of flat counts: keepRow=true → sum over columns (row sums),
    else column sums. */
export function marginalOf(counts, shape, keepRow) {
  const g = reshapeCounts(counts, shape);
  if (!g) return null;
  const [r, c] = shape;
  if (keepRow) return Array.from({ length: r }, (_, i) => g[i].reduce((a, b) => a + b, 0));
  return Array.from({ length: c }, (_, j) => {
    let s = 0;
    for (let i = 0; i < r; i++) s += g[i][j];
    return s;
  });
}

/** Heatmap overlay cells: theory grid vs sample frequency per cell. */
export function overlayHeat(grid, counts, shots) {
  if (!Array.isArray(grid) || !grid.length || !Array.isArray(grid[0])) return null;
  const rows = grid.length, cols = grid[0].length;
  const sample = counts && counts.length ? reshapeCounts(counts, [rows, cols]) : null;
  const cells = [];
  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      cells.push({
        i, j,
        theory: grid[i][j],
        sample: sample && shots > 0 ? sample[i][j] / shots : 0,
      });
    }
  }
  return { rows, cols, cells };
}

/** Truncation-leakage meter state: null (density/conditional) → no pct;
    warn when leakage > 1% (design §3.3 yellow gate). */
export function leakInfo(leakage) {
  if (typeof leakage !== "number" || !Number.isFinite(leakage)) {
    return { pct: null, warn: false };
  }
  return { pct: leakage * 100, warn: leakage > 0.01 };
}

/** cutoff > 20 → Wigner 慢速提示（design §2.4: 网格自动降 N=48）. */
export function slowCutoff(cutoffs) {
  return Array.isArray(cutoffs) && cutoffs.length > 0 && cutoffs.some((c) => c > 20);
}

/** Clamp per-mode initial photon numbers into [0, cutoffs[i]-1]. */
export function clampInitial(initial, cutoffs, nmode) {
  const out = Array(nmode).fill(0);
  for (let i = 0; i < nmode; i++) {
    const n = initial && initial[i] !== undefined ? initial[i] : 0;
    out[i] = Math.min(Math.max(0, Math.round(n)), (cutoffs[i] ?? 10) - 1);
  }
  return out;
}

/** Measured-batch histogram {key: count} → sorted rows (desc frequency). */
export function batchMeasRows(counts) {
  return Object.entries(counts || {})
    .sort((a, b) => b[1] - a[1])
    .map(([key, count]) => ({ key, count }));
}

/** Sample series for the dist bars: 1D counts on this mode, or the 2D joint
    marginal over the complementary axis. null = no overlay available. */
export function sampleSeries(distMode, batch) {
  if (!batch || !Array.isArray(batch.counts) || batch.measured_names) return null;
  if (batch.shape && batch.shape.length === 1 && batch.modes?.[0] === distMode) {
    return { counts: batch.counts, shots: batch.shots };
  }
  if (batch.shape && batch.shape.length === 2 && batch.modes?.includes(distMode)) {
    const keepRow = batch.modes[0] === distMode;
    const marg = marginalOf(batch.counts, batch.shape, keepRow);
    return marg ? { counts: marg, shots: batch.shots } : null;
  }
  return null;
}

/* ── DOM wiring (browser only) ──────────────────────────── */

const SVG_NS = "http://www.w3.org/2000/svg";

function el(tag, attrs) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

function fmt(x, digits = 5) {
  if (typeof x !== "number" || !Number.isFinite(x)) return "—";
  return x.toPrecision(digits);
}

function cssVar(name, fallback) {
  return (getComputedStyle(document.documentElement).getPropertyValue(name) || "").trim() || fallback;
}

/** Grouped bars: theory (accent) + sample (error) side by side. */
function drawBars(svg, bars) {
  const W = 320, H = 150, padL = 22, padR = 8, padT = 8, padB = 18;
  const vmax = Math.max(1e-12, ...bars.map((b) => Math.max(b.theory, b.sample)));
  const accent = cssVar("--color-accent", "#2e63d1");
  const error = cssVar("--color-error", "#c33");
  const rule = cssVar("--color-rule", "#ccc");
  const ink = cssVar("--color-ink", "#333");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.replaceChildren();
  // baseline
  svg.append(el("line", { x1: padL, y1: H - padB, x2: W - padR, y2: H - padB, stroke: rule, "stroke-width": 1 }));
  const n = Math.max(1, bars.length);
  const slot = (W - padL - padR) / n;
  const barW = Math.max(1, Math.min(8, slot * 0.34));
  const hOf = (v) => (v / vmax) * (H - padT - padB);
  for (const b of bars) {
    const x = padL + b.n * slot + slot * 0.14;
    if (b.theory > 0) {
      svg.append(el("rect", {
        x: x.toFixed(2), y: (H - padB - hOf(b.theory)).toFixed(2),
        width: barW, height: hOf(b.theory).toFixed(2),
        fill: accent, opacity: 0.85,
      }));
    }
    if (b.sample > 0) {
      svg.append(el("rect", {
        x: (x + barW).toFixed(2), y: (H - padB - hOf(b.sample)).toFixed(2),
        width: barW, height: hOf(b.sample).toFixed(2),
        fill: error, opacity: 0.9,
      }));
    }
    if (n <= 16) {
      const t = el("text", { x: (x + barW).toFixed(2), y: H - 5, "text-anchor": "middle", fill: ink });
      t.textContent = b.n;
      svg.append(t);
    }
  }
}

/** Cell heatmap: one 1×1 rect per cell, opacity ∝ value/max. */
function drawHeat(svg, data, color) {
  const { rows, cols, cells } = data;
  svg.setAttribute("viewBox", `0 0 ${cols} ${rows}`);
  svg.replaceChildren();
  const vmax = Math.max(1e-12, ...cells.map((c) => Math.max(c.theory, c.sample)));
  for (const c of cells) {
    const v = Math.max(0, c.theory);
    svg.append(el("rect", {
      x: c.j, y: c.i, width: 1, height: 1, fill: color,
      "fill-opacity": v <= 0 ? "0" : Math.max(0.06, v / vmax).toFixed(3),
    }));
  }
}

/** Joint theory grid + (optional) batch sample grid side by side. */
function drawJointPair(body, batch) {
  const jointSvg = document.querySelector("#fock-joint-svg");
  const batchSvg = document.querySelector("#fock-batch-svg");
  if (!jointSvg || !batchSvg) return;
  const accent = cssVar("--color-accent", "#2e63d1");
  const error = cssVar("--color-error", "#c33");
  const joint = body.joint;
  if (!joint || !Array.isArray(joint.grid) || !joint.grid.length) {
    jointSvg.replaceChildren();
    batchSvg.replaceChildren();
    return;
  }
  drawHeat(jointSvg, overlayHeat(joint.grid, [], 0), accent);
  const sc = batch && !batch.measured_names && batch.shape && batch.shape.length === 2
    && batch.modes?.[0] === joint.modes[0] && batch.modes?.[1] === joint.modes[1]
    ? overlayHeat(joint.grid, batch.counts, batch.shots)
    : null;
  if (sc) drawHeat(batchSvg, sc, error);
  else batchSvg.replaceChildren();
}

/** Fock panel init (wires events + returns render API). hooks:
    { getState, setCircuit, setJointModes, onBatch, onStatus }. */
export function initFockPanel(root, hooks) {
  const dom = {
    distSvg: root.querySelector("#fock-dist-svg"),
    distMode: root.querySelector("#fock-dist-mode"),
    batchBtn: root.querySelector("#batch-btn"),
    batchSeed: root.querySelector("#batch-seed"),
    batchMeas: root.querySelector("#fock-batch-meas"),
    jointSvg: root.querySelector("#fock-joint-svg"),
    batchSvg: root.querySelector("#fock-batch-svg"),
    jointM0: root.querySelector("#joint-m0"),
    jointM1: root.querySelector("#joint-m1"),
    jointNote: root.querySelector("#joint-note"),
    cutoffSlider: root.querySelector("#cutoff-slider"),
    cutoffVal: root.querySelector("#cutoff-val"),
    overrides: root.querySelector("#cutoff-overrides"),
    leak: root.querySelector("#fock-leak"),
    nbar: root.querySelector("#fock-nbar"),
    purity: root.querySelector("#fock-purity"),
    slowNote: root.querySelector("#fock-slow-note"),
  };
  let lastResult = null; // latest /run or /sample body
  let lastBatch = null;  // latest /batch body

  function nmodeOfState() {
    return Math.max(1, sourceModes(hooks.getState().nodes));
  }

  function cutoffsOfState(body) {
    const st = hooks.getState();
    const nm = nmodeOfState();
    if (Array.isArray(st.cutoffs) && st.cutoffs.length >= nm) return st.cutoffs.slice(0, nm);
    return (body.cutoffs || Array(nm).fill(10)).slice(0, nm);
  }

  function refreshJointSelects(body) {
    const nm = body.nmode;
    const sel = body.joint ? body.joint.modes : (hooks.getState().view?.joint_modes || [0, 1]);
    for (const [select, val] of [[dom.jointM0, sel[0]], [dom.jointM1, sel[1]]]) {
      select.replaceChildren();
      for (let k = 0; k < nm; k++) {
        const opt = document.createElement("option");
        opt.value = k;
        opt.textContent = `mode ${k}`;
        if (k === val) opt.selected = true;
        select.appendChild(opt);
      }
      select.disabled = nm < 2;
    }
  }

  function refreshGuard(body) {
    const cutoffs = cutoffsOfState(body);
    const uniform = cutoffs.every((c) => c === cutoffs[0]);
    dom.cutoffVal.textContent = uniform ? String(cutoffs[0] ?? 10) : "混合";
    if (uniform) dom.cutoffSlider.value = String(cutoffs[0] ?? 10);
    // per-mode overrides (cutoff + ⟨n⟩ readout), rebuilt only on count change
    const nm = cutoffs.length;
    if (dom.overrides.dataset.nmode !== String(nm)) {
      dom.overrides.dataset.nmode = String(nm);
      dom.overrides.replaceChildren();
      const perMode = body.meters?.mean_photon_per_mode || [];
      for (let i = 0; i < nm; i++) {
        const wrap = document.createElement("label");
        wrap.className = "param";
        const lab = document.createElement("span");
        lab.className = "param__name mono";
        lab.textContent = `mode ${i}`;
        const inp = document.createElement("input");
        inp.type = "number";
        inp.className = "param__num mono";
        inp.min = 1;
        inp.max = 30;
        inp.step = 1;
        inp.value = cutoffs[i] ?? 10;
        const nbar = document.createElement("span");
        nbar.className = "hint mono";
        nbar.textContent = `⟨n⟩ ${fmt(perMode[i])}`;
        inp.addEventListener("change", () => {
          const v = Math.min(30, Math.max(1, Number(inp.value)));
          if (!Number.isInteger(v)) { inp.value = cutoffs[i] ?? 10; return; }
          const nm2 = nmodeOfState();
          const next = Array(nm2).fill(10).map((_, k) => cutoffs[k] ?? 10);
          next[i] = v;
          hooks.setCircuit({
            cutoffs: next,
            initial: clampInitial(hooks.getState().initial, next, nm2),
          });
        });
        wrap.append(lab, inp, nbar);
        dom.overrides.appendChild(wrap);
      }
    } else {
      const perMode = body.meters?.mean_photon_per_mode || [];
      [...dom.overrides.children].forEach((wrap, i) => {
        const inp = wrap.querySelector("input");
        const nbar = wrap.querySelector(".hint");
        if (inp && inp.value !== String(cutoffs[i] ?? 10)) inp.value = String(cutoffs[i] ?? 10);
        if (nbar) nbar.textContent = `⟨n⟩ ${fmt(perMode[i])}`;
      });
    }
    // leakage meter (density/conditional → honest —)
    const li = leakInfo(body.meters?.leakage);
    dom.leak.textContent = li.pct === null ? "—" : li.pct.toFixed(3) + "%";
    dom.leak.classList.toggle("fock__leak--warn", li.warn);
    dom.nbar.textContent = fmt(body.meters?.mean_photon);
    dom.purity.textContent = fmt(body.meters?.purity);
    dom.slowNote.hidden = !slowCutoff(cutoffs);
  }

  function renderDist() {
    if (!lastResult) return;
    const series = sampleSeries(lastResult.dist?.mode, lastBatch);
    drawBars(dom.distSvg, histBars(lastResult.dist?.probs || [], series?.counts, series?.shots));
    dom.distMode.textContent = String(lastResult.dist?.mode ?? "—");
  }

  function renderMeas() {
    if (!lastBatch || !lastBatch.measured_names) {
      dom.batchMeas.hidden = true;
      dom.batchMeas.replaceChildren();
      return;
    }
    dom.batchMeas.hidden = false;
    dom.batchMeas.replaceChildren();
    for (const row of batchMeasRows(lastBatch.counts)) {
      const li = document.createElement("li");
      li.textContent = `${row.key} × ${row.count}`;
      dom.batchMeas.appendChild(li);
    }
  }

  /* event wiring */
  dom.batchBtn?.addEventListener("click", () => hooks.onBatch());
  dom.cutoffSlider?.addEventListener("input", () => {
    const nm = nmodeOfState();
    const cut = Array(nm).fill(Number(dom.cutoffSlider.value));
    hooks.setCircuit({
      cutoffs: cut,
      initial: clampInitial(hooks.getState().initial, cut, nm),
    });
    dom.cutoffVal.textContent = String(dom.cutoffSlider.value);
  });
  const onJointChange = () => {
    const a = Number(dom.jointM0.value);
    const b = Number(dom.jointM1.value);
    if (a === b) { hooks.onStatus?.("joint 需要两个不同的模式", false); return; }
    hooks.setJointModes([a, b]);
  };
  dom.jointM0?.addEventListener("change", onJointChange);
  dom.jointM1?.addEventListener("change", onJointChange);

  return {
    renderResult(body) {
      lastResult = body;
      renderDist();
      dom.jointNote.hidden = !!body.joint;
      refreshJointSelects(body);
      drawJointPair(body, lastBatch);
      refreshGuard(body);
    },
    renderBatch(body) {
      lastBatch = body;
      dom.batchSeed.textContent = `seed ${body.seed}`;
      renderMeas();
      renderDist();
      if (lastResult) drawJointPair(lastResult, body);
    },
  };
}
