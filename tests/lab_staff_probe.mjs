/* Gaussian Lab L5 — headless CDP probe (staff editor: render, DnD placing,
   two-mode two-step flow, move/delete, JSON sync, legacy load).
   Zero-dep: Node >= 22 native fetch + WebSocket; Edge headless.

   Usage: node tests/lab_staff_probe.mjs
   Exit code 0 = all probes PASS, 1 = any FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const PORT = 8766;
const CDP_PORT = 9224;
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const failures = [];
const checks = [];

function check(name, ok, detail = "") {
  checks.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
  if (!ok) failures.push(name);
}

async function waitHttp(url, timeoutMs = 20000) {
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

async function waitEval(ws, expression, timeoutMs = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const v = await evalJs(ws, expression);
    if (v) return v;
    await sleep(200);
  }
  throw new Error(`timeout waiting for: ${expression}`);
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
    }, 30000);
  });
}
function evalJs(ws, expression) {
  return send(ws, "Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  }).then((m) => {
    if (m.result && m.result.exceptionDetails) {
      throw new Error("page exception: " + JSON.stringify(m.result.exceptionDetails.exception?.description || m.result.exceptionDetails));
    }
    return m.result && m.result.result ? m.result.result.value : undefined;
  });
}

/* synthetic HTML5 DnD: drag a palette card onto a lane (or an existing gate
   to a new spot). clientX drives the x computation in the staff drop handler. */
async function drag(ws, { from, to, dx = 0 }) {
  return evalJs(ws, `(async () => {
    const src = ${JSON.stringify(from)};
    const dst = ${JSON.stringify(to)};
    const el = document.querySelector(src);
    const target = document.querySelector(dst);
    if (!el || !target) return "missing: " + src + " / " + dst;
    const rect = target.getBoundingClientRect();
    const dt = new DataTransfer();
    el.dispatchEvent(new DragEvent("dragstart", { dataTransfer: dt, bubbles: true }));
    const data = dt.getData("text/plain");
    const ok = target.dispatchEvent(new DragEvent("dragover", { dataTransfer: dt, bubbles: true, cancelable: true, clientX: rect.left + rect.width / 2 + ${dx}, clientY: rect.top + 10 }));
    const dropped = target.dispatchEvent(new DragEvent("drop", { dataTransfer: dt, bubbles: true, cancelable: true, clientX: rect.left + rect.width / 2 + ${dx}, clientY: rect.top + 10 }));
    return JSON.stringify({ data, ok, dropped });
  })()`);
}

async function click(ws, sel) {
  return evalJs(ws, `(() => {
    const el = document.querySelector(${JSON.stringify(sel)});
    if (!el) return false;
    el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    return true;
  })()`);
}

const server = spawn(process.cwd() + "/.venv/Scripts/uvicorn.exe", ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"], {
  cwd: process.cwd(), stdio: "ignore",
});
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + process.cwd() + "/.probe-edge-profile-l5",
  "about:blank",
], { stdio: "ignore" });

let ws;
try {
  await waitHttp(`http://127.0.0.1:${PORT}/health`);
  await waitHttp(`http://127.0.0.1:${CDP_PORT}/json/version`);
  const target = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(`http://127.0.0.1:${PORT}/`)}`, { method: "PUT" }).then((r) => r.json());
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      pending.get(m.id).resolve(m);
      pending.delete(m.id);
    }
  };
  await send(ws, "Runtime.enable");
  await evalJs(ws, `(async () => { while (!document.getElementById("staff")) await new Promise((r) => setTimeout(r, 50)); return true; })()`);

  /* 1. default scene (tmsv legacy + 2 loss) renders as staff */
  const staff = await waitEval(ws, `(() => {
    const s = document.getElementById("staff");
    if (!s || !s.querySelector(".staff__row")) return null;
    return {
      rows: s.querySelectorAll(".staff__row").length,
      gates: s.querySelectorAll(".gate:not(.gate--preview)").length,
      srcLabels: [...s.querySelectorAll(".staff__source")].map((e) => e.textContent).filter(Boolean),
      palette: [...document.querySelectorAll(".palette__item")].map((e) => e.dataset.op),
      jsonHasLoss: document.getElementById("json-input").value.includes('"op": "loss"'),
    };
  })()`);
  check("staff: default scene = 2 lanes (tmsv legacy)", staff.rows === 2, JSON.stringify(staff));
  check("staff: 2 gates rendered", staff.gates === 2, String(staff.gates));
  check("staff: tmsv source label on lane 0", staff.srcLabels.length === 1 && staff.srcLabels[0].startsWith("TMSV"), JSON.stringify(staff.srcLabels));
  check("palette: tmsv hidden, vacuum present", staff.palette.includes("vacuum") && !staff.palette.includes("tmsv"), JSON.stringify(staff.palette));
  check("JSON: graph→json sync intact", staff.jsonHasLoss);

  /* 2. single-mode placement: drag 相位 onto lane 1 at offset +150px */
  const single = await drag(ws, { from: '[data-op="phase"]', to: '.staff__row[data-mode="1"] .staff__lane', dx: 150 });
  await waitEval(ws, `(() => {
    const g = document.querySelector('.gate[data-id]');
    return [...document.querySelectorAll(".gate:not(.gate--preview)")].length === 3;
  })()`);
  const singleCheck = await evalJs(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    const p = j.nodes.find((n) => n.op === "phase");
    return p ? { mode: p.mode, x: p.ui.x, n: j.nodes.length } : null;
  })()`);
  check("place single: phase on mode 1, x≈2.6 (150px/72)", singleCheck && singleCheck.mode === 1 && Math.abs(singleCheck.x - (150 + 66) / 72) < 0.2, JSON.stringify(singleCheck));

  /* 3. two-mode two-step: drag beamsplitter onto lane 0 → preview + hint → click lane 1 */
  const bs = await drag(ws, { from: '[data-op="beamsplitter"]', to: '.staff__row[data-mode="0"] .staff__lane', dx: 250 });
  await waitEval(ws, `document.querySelector(".gate--preview")`);
  const placing = await evalJs(ws, `(() => ({
    preview: !!document.querySelector(".gate--preview"),
    armRows: document.querySelectorAll(".staff__lane--arm").length,
    status: document.getElementById("status").textContent,
  }))()`);
  check("two-mode: preview + armed lane + hint", placing.preview && placing.armRows === 1 && /选择第二个模式/.test(placing.status), JSON.stringify(placing));

  /* same-lane click rejected, placing kept */
  await click(ws, '.staff__row[data-mode="0"] .staff__lane');
  const same = await evalJs(ws, `(() => ({
    still: !!document.querySelector(".gate--preview"),
    status: document.getElementById("status").textContent,
  }))()`);
  check("two-mode: same-lane rejected, placing kept", same.still && /不同模式/.test(same.status), JSON.stringify(same));

  /* click lane 1 → placed */
  await click(ws, '.staff__row[data-mode="1"] .staff__lane');
  await waitEval(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    return j.nodes.some((n) => n.op === "beamsplitter");
  })()`);
  const placed = await evalJs(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    const b = j.nodes.find((n) => n.op === "beamsplitter");
    return b ? { modes: b.modes, x: b.ui.x, preview: !!document.querySelector(".gate--preview") } : null;
  })()`);
  check("two-mode: placed modes=[0,1], preview gone", placed && JSON.stringify(placed.modes) === "[0,1]" && !placed.preview, JSON.stringify(placed));

  /* 4. Esc cancels placing */
  const bs2 = await drag(ws, { from: '[data-op="mz"]', to: '.staff__row[data-mode="0"] .staff__lane', dx: 350 });
  await waitEval(ws, `document.querySelector(".gate--preview")`);
  await evalJs(ws, `document.getElementById("staff").dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))`);
  const esc = await evalJs(ws, `(() => ({
    preview: !!document.querySelector(".gate--preview"),
    mz: JSON.parse(document.getElementById("json-input").value).nodes.some((n) => n.op === "mz"),
  }))()`);
  check("two-mode: Esc cancels, no node added", !esc.preview && !esc.mz, JSON.stringify(esc));

  /* 5. move existing gate: drag loss (lane 0) further right */
  const lossBefore = await evalJs(ws, `(() => JSON.parse(document.getElementById("json-input").value).nodes.find((n) => n.id === "l0").ui.x)()`);
  const moved = await drag(ws, { from: '.gate[data-id="l0"]', to: '.staff__row[data-mode="0"] .staff__lane', dx: 400 });
  await waitEval(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    return j.nodes.find((n) => n.id === "l0").ui.x > ${lossBefore};
  })()`);
  const lossAfter = await evalJs(ws, `(() => JSON.parse(document.getElementById("json-input").value).nodes.find((n) => n.id === "l0").ui.x)()`);
  check("move gate: l0 x increased, JSON synced", lossAfter > lossBefore, `${lossBefore} → ${lossAfter}`);

  /* 6. delete via hover × */
  const delClick = await evalJs(ws, `(async () => {
    const g = document.querySelector('.gate[data-id="l1"]');
    g.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
    const btn = g.querySelector(".gate__del");
    btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 100));
    const j = JSON.parse(document.getElementById("json-input").value);
    return !j.nodes.some((n) => n.id === "l1");
  })()`);
  check("delete gate: l1 removed, JSON synced", delClick);

  /* 7. legacy JSON without ui.x loads and renders as grid columns */
  const legacy = await evalJs(ws, `(async () => {
    const payload = {
      schema: "circuit_v0", seed: 0,
      nodes: [
        { id: "v", op: "vacuum", params: { nmode: 2 } },
        { id: "p", op: "phase", params: { phi: 1.2 }, mode: 0 },
        { id: "d", op: "displace", params: { alpha: 1 }, mode: 1 },
      ],
      edges: [], view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {},
    };
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, JSON.stringify(payload));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 600)); // 400ms debounce
    const s = document.getElementById("staff");
    const j = JSON.parse(input.value);
    const ok = s.querySelectorAll(".staff__row").length === 2
      && s.querySelectorAll(".gate:not(.gate--preview)").length === 2
      && j.nodes.filter((n) => n.op !== "vacuum").every((n) => Number.isFinite(n.ui.x));
    return ok;
  })()`);
  check("legacy JSON: loads, renders 2 lanes + 2 gates, ui.x assigned", legacy);

  /* 8. source click opens the param card (vacuum: no knobs, info shown) */
  await click(ws, '.staff__source[data-src-id="v"]');
  await waitEval(ws, `document.querySelector(".gate-card")`);
  const srcCard = await evalJs(ws, `(() => {
    const c = document.querySelector(".gate-card");
    return {
      head: c.querySelector(".gate-card__head").textContent,
      none: !!c.querySelector(".gate-card__none"),
    };
  })()`);
  check("source click: param card with vacuum info", /真空模/.test(srcCard.head) && srcCard.none, JSON.stringify(srcCard));

  /* 9. gate click opens param card; slider edit propagates to JSON */
  await click(ws, '.gate[data-id="p"]');
  await waitEval(ws, `document.querySelector(".gate-card__params .param input[type=range]")`);
  const cardEdit = await evalJs(ws, `(async () => {
    const range = document.querySelector(".gate-card__params .param input[type=range]");
    range.value = "2.5";
    range.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 150));
    const j = JSON.parse(document.getElementById("json-input").value);
    const p = j.nodes.find((n) => n.op === "phase");
    return { phi: p.params.phi, cardStillOpen: !!document.querySelector(".gate-card") };
  })()`);
  check("gate card: slider edit → JSON sync, card stays open", cardEdit.phi === 2.5 && cardEdit.cardStillOpen, JSON.stringify(cardEdit));

  /* 10. sweepable card auto-syncs the scan panel target (synced in step 9) */
  const scanSync = await evalJs(ws, `(() => ({
    target: document.getElementById("scan-node").value,
  }))()`);
  check("scan sync: phase card targets scan node", scanSync.target === "p", JSON.stringify(scanSync));

  console.log(`\n${checks.filter((c) => c.ok).length}/${checks.length} probes PASS`);
} finally {
  try { ws && ws.close(); } catch { /* ignore */ }
  edge.kill();
  server.kill();
}
if (failures.length) {
  console.log(`FAILED: ${failures.join(", ")}`);
  process.exit(1);
}
