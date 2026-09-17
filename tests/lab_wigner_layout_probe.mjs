/* Wigner layout probe — the parameter panel / colourbar must never be covered by
   the Wigner heatmap. Zero-dep: Node >= 22 native fetch + WebSocket; Edge headless.

   Usage: node tests/lab_wigner_layout_probe.mjs
   Spawns uvicorn (lab server) + headless Edge, runs gaussian/bosonic/fock at
   1440/1280/1920, and asserts geometric non-overlap:

   1. zero intersection area between the Wigner frame (and its canvas) and every
      colourbar label, the parameter side panel (meters / r̄ table), and every
      backend result panel;
   2. the frame stays inside its own grid column — it must never eat the gap that
      separates it from the colourbar. This is the invariant that broke:
      `fitWignerFrame` measured the colourbar with `offsetLeft`, whose reference
      frame is the offsetParent (BODY, since `.wigner` is not positioned), so the
      frame was sized to the distance from the *page* left edge and spilled over
      the colourbar and the parameter panel;
   3. the frame tracks the colourbar column: a circuit whose tick label is wider
      must yield a narrower frame (guards the call-site contract — `fitWignerFrame()`
      runs after the labels are written, inside `drawHeatmap`). The page's own
      ResizeObserver self-heals a wrong ordering a frame or two later, so this
      check is paired with the source-order assertion in tests/test_lab_ui.py;
   4. the frame follows the side column when nmode changes its width;
   5. high nmode (4 and 8) at every viewport: the side column is the third `auto`
      track and its "各模式 ⟨n⟩" value grows with nmode, so the 1fr frame track used
      to be crushed flat — at 1440/nmode=8 the side column reached 509px, the frame
      bottomed out on the `max(64, …)` clamp and covered the colourbar by 2304px²
      while `.result` overflowed its column (774/727). Guarding only the default
      nmode=2 scene missed it entirely, which is why this check exists.

   Fock is capped at nmode 2 by the backend — `fock/analyse.py` `partial_trace`
   raises `NotImplementedError("partial_trace: nmode=3 not supported (dense m≤2;
   sparse F3)")`, surfacing as HTTP 500 — so high-nmode coverage is
   gaussian + bosonic. Bosonic GKP initial states at nmode≥4 also time out
   (>45s), so those cases use the default vacuum initial state (~1s).

   Exit code 0 = all probes PASS, 1 = any FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const PORT = 8768;
const CDP_PORT = 9226;
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const failures = [];
const checks = [];

function check(name, ok, detail = "") {
  checks.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
  if (!ok) failures.push(name);
}

async function waitHttp(url, timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try {
      const r = await fetch(url);
      if (r.ok) return r;
    } catch { /* not up yet */ }
    await sleep(200);
  }
  throw new Error(`timeout waiting for ${url}`);
}

let msgId = 0;
const pending = new Map();
function send(ws, method, params = {}) {
  const id = ++msgId;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    setTimeout(() => {
      if (pending.delete(id)) reject(new Error(`CDP timeout: ${method}`));
    }, 60000);
  });
}
function evalJs(ws, expression) {
  return send(ws, "Runtime.evaluate", {
    expression, returnByValue: true, awaitPromise: true,
  }).then((m) => {
    if (m.result && m.result.exceptionDetails) {
      throw new Error("page exception: " + JSON.stringify(m.result.exceptionDetails.exception?.description || m.result.exceptionDetails));
    }
    return m.result && m.result.result ? m.result.result.value : undefined;
  });
}

const server = spawn(process.cwd() + "/.venv/Scripts/uvicorn.exe",
  ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"],
  { cwd: process.cwd(), stdio: "ignore" });
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--no-sandbox", "--disable-dev-shm-usage", "--remote-allow-origins=*",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + process.cwd() + "/.probe-edge-layout-profile",
  "about:blank",
], { stdio: "ignore" });

/* One page-side geometry reader, so every width/backend is measured identically.
   `expect` recomputes the fit contract independently of the page's own function. */
const INSTALL = `
window.__snap = () => {
  const rect = (el) => { const b = el.getBoundingClientRect();
    return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width, h: b.height }; };
  const inter = (a, b) => (!a || !b) ? 0 : Math.round(
    Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) *
    Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t)));
  const vis = (el) => !!el && !el.hidden && getComputedStyle(el).display !== "none";

  const box = document.querySelector(".wigner");
  const frameEl = document.querySelector(".wigner__frame");
  const cbEl = document.querySelector(".wigner__colorbar");
  const F = rect(frameEl), C = rect(document.getElementById("wigner-canvas"));

  const targets = [
    ["colorbar", cbEl],
    ["colorbar-max", document.getElementById("colorbar-max")],
    ["colorbar-zero", document.getElementById("colorbar-zero")],
    ["colorbar-min", document.getElementById("colorbar-min")],
    ["side", document.getElementById("wigner-side")],
    ["meters", document.getElementById("meters-panel")],
    ["rbar", document.getElementById("rbar-block")],
    ["purity", document.getElementById("m-purity")],
    ["nbar", document.getElementById("m-nbar")],
    ["permode", document.getElementById("m-permode")],
    ["logneg", document.getElementById("m-logneg")],
    ["bosonic", document.getElementById("bosonic-panel")],
    ["fock", document.getElementById("fock-panel")],
    ["scan", document.getElementById("scan-panel")],
    ["vgrid", document.getElementById("state-grid")],
    ["meas", document.getElementById("measurement-panel")],
  ];
  const hits = [];
  for (const [name, el] of targets) {
    if (!vis(el)) continue;
    const r = rect(el);
    const a = inter(r, F), b = inter(r, C);
    if (a > 0 || b > 0) hits.push(name + "(frame=" + a + ",canvas=" + b + ")");
  }

  const gap = parseFloat(getComputedStyle(box).gap || "16");
  const availW = cbEl.getBoundingClientRect().left - box.getBoundingClientRect().left - gap;
  const boxH = box.clientHeight;
  const wide = window.matchMedia("(min-width: 80rem)").matches;
  const expect = wide ? Math.max(64, Math.min(availW, boxH)) : Math.max(64, availW);

  return { hits, availW: +availW.toFixed(2), boxH, expect: +expect.toFixed(2),
    frameW: +F.w.toFixed(2), frameH: +F.h.toFixed(2), expectError: +(F.w - expect).toFixed(2),
    gap, labelMax: document.getElementById("colorbar-max").textContent, wide, vw: innerWidth };
};
1`;

/* Then wait until the layout stops moving. The size chain is .wigner →
   fitWignerFrame → frame → (frame is a grid item of .wigner) → .wigner again, so a
   single sample can land mid-convergence; require six identical consecutive reads. */
async function waitStableGeom(ws) {
  return evalJs(ws, `(async () => {
    let last = null, same = 0;
    for (let k = 0; k < 100; k++) {
      await new Promise((r) => setTimeout(r, 120));
      const g = window.__snap();
      const key = g.frameW + "|" + g.frameH + "|" + g.boxH + "|" + g.availW + "|" + g.labelMax;
      if (key === last) { same++; if (same >= 6) return "ok"; } else { same = 0; last = key; }
    }
    return "unstable";
  })()`);
}

/* Wait until the run triggered by a click has finished. The status *text* is not
   a reliable signal: re-running the same circuit can produce an identical duration
   string ("ok · 246 ms"), so a text-change wait times out. The run button's
   disabled flag is driven by the ref-counted busy wrapper, so waiting for
   true → false brackets the request exactly. */
async function runAndSettle(ws) {
  await evalJs(ws, `document.getElementById("run-btn").click()`);
  const state = await evalJs(ws, `(async () => {
    let sawBusy = false;
    for (let k = 0; k < 600; k++) {
      const btn = document.getElementById("run-btn");
      const s = document.getElementById("status");
      if (btn.disabled) sawBusy = true;
      if (s.dataset.state === "error") return "err:" + s.textContent;
      if (sawBusy && !btn.disabled && s.dataset.state === "ok") return "ok";
      await new Promise((r) => setTimeout(r, 50));
    }
    return "timeout";
  })()`);
  if (state !== "ok") return state;
  return waitStableGeom(ws);
}

/* Inject through the JSON editor (the UI path) and wait for the new run.
   The wait needs two independent signals — neither alone is sufficient:
     - the run button's busy toggle brackets the debounced request (the status
       *text* is not usable: re-running the same circuit can produce an identical
       duration string, e.g. "ok · 246 ms", so a text-change wait times out);
     - the displayed tick label must equal the one the backend actually returns for
       this circuit (computed here from the page's own wignerScale/axisVal leaves).
   During development, trusting the label alone produced a false "does not track the
   label" failure: the default scene's label is also "0.315", so a case producing
   "0.315" matched the *previous* run and the geometry was read too early. */
async function injectAndSettle(ws, payload) {
  const expected = await evalJs(ws, `(async () => {
    const { wignerScale } = await import("/colormap.js");
    const { axisVal } = await import("/svg_kit.js");
    const r = await fetch("/run", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: ${JSON.stringify(JSON.stringify(payload))} });
    const j = await r.json();
    return axisVal(wignerScale(j.wigner.W));
  })()`);
  await evalJs(ws, `(() => {
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, ${JSON.stringify(JSON.stringify(payload))});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  const state = await evalJs(ws, `(async () => {
    let sawBusy = false;
    for (let k = 0; k < 600; k++) {
      const btn = document.getElementById("run-btn");
      const st = document.getElementById("status");
      if (btn.disabled) sawBusy = true;
      if (st.dataset.state === "error") return "err:" + st.textContent;
      /* 400ms editor debounce + request + render, then the label must have landed */
      if (sawBusy && !btn.disabled && document.getElementById("colorbar-max").textContent === ${JSON.stringify(expected)}) return "ok";
      await new Promise((r) => setTimeout(r, 50));
    }
    return sawBusy ? "label-mismatch(expected " + ${JSON.stringify(expected)} + ")" : "timeout";
  })()`);
  if (state !== "ok") return { state, expected };
  return { state: await waitStableGeom(ws), expected };
}

/* Both circuits keep nmode=1 so the side-panel width is constant — the colourbar
   tick label is then the only variable behind availW. */
const LABEL_CASES = [
  ["narrow-label", { schema: "circuit_v1", seed: 0, nmode: 1,
    ops: [{ id: "d0", op: "displace", params: { alpha: 1 }, modes: [0] }],
    view: { wigner_mode: 0, lim: 5.0, n: 64 } }],
  ["wide-label", { schema: "circuit_v1", seed: 0, nmode: 1,
    ops: [{ id: "s0", op: "squeeze", params: { r: 3, phi: 0 }, modes: [0] }],
    view: { wigner_mode: 0, lim: 5.0, n: 64 } }],
];

/* The side panel (meters / r̄ table) is the *other* input to availW, and it is
   resized by nmode: 1 → 2 widens it 155 → 186.34px at 1440, shrinking availW by
   31.34px. `render()` used to fit the frame before rendering those tables, so the
   frame kept the pre-switch width and overlapped the colourbar by 3224px² — and
   `.wigner`'s own ResizeObserver never fired, because its border-box is unchanged
   (only the inner `1fr` track narrows). Both orderings are exercised: widening is
   the dangerous direction, narrowing only wastes space. */
const nm1 = { schema: "circuit_v1", seed: 0, nmode: 1,
  ops: [{ id: "d0", op: "displace", params: { alpha: 1 }, modes: [0] }],
  view: { wigner_mode: 0, lim: 5.0, n: 64 } };
const nm2 = { schema: "circuit_v1", seed: 0, nmode: 2,
  ops: [{ id: "d0", op: "displace", params: { alpha: 1 }, modes: [0] },
        { id: "d1", op: "displace", params: { alpha: 1 }, modes: [1] }],
  view: { wigner_mode: 0, lim: 5.0, n: 64 } };
const SIDE_CASES = [["nmode2-narrow-side", nm2], ["nmode1-wide-avail", nm1], ["nmode2-again", nm2]];

/* High-nmode cases: the side column is the third `auto` grid track, so its width
   follows the "各模式 ⟨n⟩" value, which grows one 4-decimal group per mode. Nothing
   capped that track, so it ate the `1fr` frame track: at 1440, nmode 4 → side 350.4
   / frame 158.7; nmode 8 → side 509.1 / frame 64 (the `max(64, …)` floor), covering
   the colourbar by 2304px² and overflowing `.result` 774/727.
   Fock cannot appear here — the backend rejects nmode≥3 (see the header). Bosonic
   uses the default vacuum initial state: GKP at nmode≥4 exceeds the 45s budget. */
const hiGaussian = (n) => ({ schema: "circuit_v1", seed: 0, nmode: n, backend: "gaussian",
  ops: Array.from({ length: n }, (_, i) => ({ id: "d" + i, op: "displace", params: { alpha: 1 }, modes: [i] })),
  view: { wigner_mode: 0, lim: 5.0, n: 64 } });
const hiBosonic = (n) => ({ schema: "circuit_v1", seed: 0, nmode: n, backend: "bosonic",
  ops: Array.from({ length: n }, (_, i) => ({ id: "d" + i, op: "displace", params: { alpha: 1 }, modes: [i] })),
  view: { wigner_mode: 0, lim: 5.0, n: 64 } });
const HI_CASES = [
  ["gaussian-nmode4", hiGaussian(4)], ["gaussian-nmode8", hiGaussian(8)],
  ["bosonic-nmode4", hiBosonic(4)], ["bosonic-nmode8", hiBosonic(8)],
];

const BACKENDS = ["gaussian", "bosonic", "fock"];
const WIDTHS = [1440, 1280, 1920];
const HEIGHT = 900;

try {
  await waitHttp(`http://127.0.0.1:${PORT}/health`);
  await waitHttp(`http://127.0.0.1:${CDP_PORT}/json/version`);
  const target = await fetch(
    `http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(`http://127.0.0.1:${PORT}/`)}`,
    { method: "PUT" }).then((r) => r.json());
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id).resolve(m); pending.delete(m.id); }
  };
  await send(ws, "Runtime.enable");
  await send(ws, "Network.enable");
  await send(ws, "Network.clearBrowserCache");
  await send(ws, "Page.reload");
  await evalJs(ws, `(async () => { while (!document.querySelector(".palette__item")) await new Promise((r) => setTimeout(r, 50)); return true; })()`);
  await evalJs(ws, INSTALL);

  const hitLines = [];
  const budgetLines = [];
  const measured = [];

  for (const backend of BACKENDS) {
    await evalJs(ws, `(async () => {
      const s = document.getElementById("backend-select");
      s.value = ${JSON.stringify(backend)};
      s.dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise((r) => setTimeout(r, 600));
      return s.value;
    })()`);

    for (const w of WIDTHS) {
      await send(ws, "Emulation.setDeviceMetricsOverride",
        { width: w, height: HEIGHT, deviceScaleFactor: 1, mobile: false });
      await sleep(350);
      /* default view, matching the scan probe's folded baseline */
      await evalJs(ws, `document.querySelectorAll(".fold").forEach((f) => (f.open = false)); document.querySelectorAll(".panel").forEach((p) => (p.scrollTop = 0))`);
      const state = await runAndSettle(ws);
      if (state !== "ok") { hitLines.push(`${backend}@${w}: run did not settle (${state})`); continue; }

      const g = await evalJs(ws, `window.__snap()`);
      if (g.hits.length) hitLines.push(`${backend}@${w}: ${g.hits.join(" ")}`);
      if (Math.abs(g.expectError) > 0.51) {
        budgetLines.push(`${backend}@${w}: frame=${g.frameW} expect=${g.expect} (err ${g.expectError}) availW=${g.availW} boxH=${g.boxH}`);
      }
      measured.push({ backend, w, label: g.labelMax, frameW: g.frameW, expect: g.expect, hits: g.hits.length });
    }
  }

  check("no element covered by the Wigner frame/canvas (3 backends x 1440/1280/1920)",
    hitLines.length === 0, hitLines.join(" ; "));
  check("frame stays inside its grid column (never eats the gap before the colourbar)",
    budgetLines.length === 0, budgetLines.join(" ; "));

  /* Back to gaussian for the colourbar-tracking check. */
  await evalJs(ws, `(async () => {
    const s = document.getElementById("backend-select");
    s.value = "gaussian";
    s.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 500));
    return true;
  })()`);
  await send(ws, "Emulation.setDeviceMetricsOverride",
    { width: 1440, height: HEIGHT, deviceScaleFactor: 1, mobile: false });
  await sleep(350);

  const tracking = [];
  for (const [name, payload] of LABEL_CASES) {
    const { state, expected } = await injectAndSettle(ws, payload);
    if (state !== "ok") {
      tracking.push({ name, error: `did not settle (${state}, expected label ${JSON.stringify(expected)})` });
      continue;
    }
    const g = await evalJs(ws, `window.__snap()`);
    tracking.push({ name, label: g.labelMax, frameW: g.frameW, availW: g.availW,
      expect: g.expect, expectError: g.expectError, hits: g.hits });
  }

  const okTracking = tracking.length === 2 && tracking.every((t) => !t.error);
  if (okTracking) {
    const [a, b] = tracking;
    const labelsDiffer = a.label !== b.label;
    const framesDiffer = Math.abs(a.frameW - b.frameW) > 1;
    const errorsOk = tracking.every((t) => Math.abs(t.expectError) <= 0.51 && t.hits.length === 0);
    /* the wider label makes the colourbar column wider, so the frame must shrink */
    const direction = (a.label.length < b.label.length) === (a.frameW > b.frameW);
    check("frame width tracks the colourbar tick-label width",
      labelsDiffer && framesDiffer && errorsOk && direction,
      tracking.map((t) => `${t.name}: "${t.label}" frame=${t.frameW} availW=${t.availW} expect=${t.expect} hits=${t.hits.length}`).join(" ; "));
  } else {
    check("frame width tracks the colourbar tick-label width", false,
      tracking.map((t) => `${t.name}: ${t.error || JSON.stringify(t)}`).join(" ; "));
  }

  /* Side-panel (nmode) transitions in both directions, same 1440 viewport. */
  const sideTrack = [];
  for (const [name, payload] of SIDE_CASES) {
    const { state } = await injectAndSettle(ws, payload);
    if (state !== "ok") { sideTrack.push({ name, error: `did not settle (${state})` }); continue; }
    const g = await evalJs(ws, `window.__snap()`);
    /* sideW is not part of the snapshot contract; read it directly */
    const sideW = await evalJs(ws, `(() => { const s = document.getElementById("wigner-side");
      return s.hidden ? null : +s.getBoundingClientRect().width.toFixed(2); })()`);
    sideTrack.push({ name, sideW, frameW: g.frameW, availW: g.availW,
      expect: g.expect, expectError: g.expectError, hits: g.hits });
  }
  const sideOk = sideTrack.length === 3 && sideTrack.every((t) => !t.error
    && Math.abs(t.expectError) <= 0.51 && t.hits.length === 0);
  const sideWidened = sideOk && sideTrack[0].sideW !== sideTrack[1].sideW;
  const sideAvailChanged = sideOk && sideTrack[0].availW !== sideTrack[1].availW;
  check("frame follows the side panel when nmode changes the column widths",
    sideOk && sideWidened && sideAvailChanged,
    sideTrack.map((t) => `${t.name}: sideW=${t.sideW} availW=${t.availW} frame=${t.frameW} expect=${t.expect} hits=${t.hits.length}`).join(" ; "));

  /* High-nmode sweep: the third `auto` track must not crush the frame. Runs at all
     three viewports because the failure was width-dependent (at 1920 availW stayed
     above the 64px clamp, so the frame merely shrank instead of overlapping). */
  const hiTrack = [];
  for (const w of WIDTHS) {
    await send(ws, "Emulation.setDeviceMetricsOverride",
      { width: w, height: HEIGHT, deviceScaleFactor: 1, mobile: false });
    await sleep(350);
    await evalJs(ws, `document.querySelectorAll(".fold").forEach((f) => (f.open = false)); document.querySelectorAll(".panel").forEach((p) => (p.scrollTop = 0))`);
    for (const [name, payload] of HI_CASES) {
      const { state, expected } = await injectAndSettle(ws, payload);
      if (state !== "ok") { hiTrack.push({ name, w, error: `did not settle (${state}, expected label ${JSON.stringify(expected)})` }); continue; }
      const g = await evalJs(ws, `window.__snap()`);
      const extra = await evalJs(ws, `(() => {
        const s = document.getElementById("wigner-side");
        const overflow = [...document.querySelectorAll(".panel")]
          .filter((p) => p.scrollHeight > p.clientHeight + 1)
          .map((p) => (p.className || "").split(" ")[0] + " " + p.scrollHeight + "/" + p.clientHeight);
        const per = document.getElementById("m-permode");
        return { sideW: s.hidden ? null : +s.getBoundingClientRect().width.toFixed(2),
          overflow, permode: per.textContent };
      })()`);
      hiTrack.push({ name, w, frameW: g.frameW, availW: g.availW, expect: g.expect,
        expectError: g.expectError, hits: g.hits, sideW: extra.sideW,
        overflow: extra.overflow, permode: extra.permode });
    }
  }
  const hiErr = hiTrack.filter((t) => t.error);
  const hiBudget = hiTrack.filter((t) => !t.error && Math.abs(t.expectError) > 0.51);
  /* the frame is a square inside its column: a sub-96px frame in the 3-column layout
     means the side track ate the space, even when the 64px clamp keeps it legal */
  const hiSqueezed = hiTrack.filter((t) => !t.error && t.w >= 1280 && t.frameW < 96);
  const hiOverflow = hiTrack.filter((t) => !t.error && t.overflow.length);
  const hiBlocked = hiTrack.filter((t) => !t.error && t.hits.length);
  check("high nmode does not crush the Wigner frame (gaussian/bosonic x nmode 4/8 x 1440/1280/1920)",
    hiTrack.length === 4 * WIDTHS.length && hiErr.length === 0 && hiBudget.length === 0
      && hiSqueezed.length === 0,
    (hiErr.length || hiBudget.length || hiSqueezed.length)
      ? [...hiErr, ...hiBudget, ...hiSqueezed].map((t) =>
          `${t.name}@${t.w}: ${t.error || `frame=${t.frameW} availW=${t.availW} expect=${t.expect} (err ${t.expectError})`}`).join(" ; ")
      : `min frame ${Math.min(...hiTrack.map((t) => t.frameW))}px`);
  check("high nmode keeps every panel inside its column and covers nothing (1440/1280/1920)",
    hiTrack.length === 4 * WIDTHS.length && hiOverflow.length === 0 && hiBlocked.length === 0,
    [...hiOverflow.map((t) => `${t.name}@${t.w}: panel overflow [${t.overflow.join(", ")}]`),
     ...hiBlocked.map((t) => `${t.name}@${t.w}: ${t.hits.join(" ")}`)].join(" ; ")
      || `"${hiTrack[0] ? hiTrack[0].permode : ""}" sideW max ${Math.max(...hiTrack.map((t) => t.sideW || 0))}px`);

  console.log("\nmeasured frame widths (default view, folded):");
  for (const r of measured) {
    console.log(`  ${r.backend.padEnd(8)} ${String(r.w).padStart(4)}px  label="${r.label}"  frame=${r.frameW}  expect=${r.expect}  hits=${r.hits}`);
  }

  console.log("\nmeasured high-nmode geometry (default view, folded):");
  for (const t of hiTrack) {
    console.log(`  ${(t.name || "").padEnd(16)} ${String(t.w).padStart(4)}px  ` + (t.error
      ? `ERROR ${t.error}`
      : `frame=${String(t.frameW).padStart(7)}  side=${String(t.sideW).padStart(6)}  "${t.permode}"  overflow=${t.overflow.length ? t.overflow.join(",") : "none"}  hits=${t.hits.length}`));
  }

  console.log(failures.length ? `\n${failures.length} probe(s) FAILED` : "\nall probes PASS");
} catch (e) {
  failures.push(e.message);
  console.error("PROBE ERROR:", e.message);
} finally {
  try { server.kill("SIGTERM"); } catch { /* ignore */ }
  try { edge.kill("SIGTERM"); } catch { /* ignore */ }
  await sleep(300);
}
process.exit(failures.length ? 1 : 0);
