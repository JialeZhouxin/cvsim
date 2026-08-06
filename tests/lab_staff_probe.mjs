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
   to a new spot). clientX drives the x computation in the staff drop handler.
   Pass absolute clientX to pin the drop column (lane-relative dx drifts when
   the staff grid width changes between renders). */
async function drag(ws, { from, to, dx = 0, clientX } = {}) {
  const cxExpr = clientX !== undefined ? JSON.stringify(clientX) : `rect.left + rect.width / 2 + ${dx}`;
  return evalJs(ws, `(async () => {
    const src = ${JSON.stringify(from)};
    const dst = ${JSON.stringify(to)};
    const el = document.querySelector(src);
    const target = document.querySelector(dst);
    if (!el || !target) return "missing: " + src + " / " + dst;
    const rect = target.getBoundingClientRect();
    const cx = ${cxExpr};
    const dtStart = new DataTransfer();
    el.dispatchEvent(new DragEvent("dragstart", { dataTransfer: dtStart, bubbles: true }));
    const data = dtStart.getData("text/plain");
    // real browsers keep getData empty during dragover/drop; use a fresh empty
    // DataTransfer so the page must rely on its closure drag payload
    const dt = new DataTransfer();
    const ok = target.dispatchEvent(new DragEvent("dragover", { dataTransfer: dt, bubbles: true, cancelable: true, clientX: cx, clientY: rect.top + 10 }));
    const dropped = target.dispatchEvent(new DragEvent("drop", { dataTransfer: dt, bubbles: true, cancelable: true, clientX: cx, clientY: rect.top + 10 }));
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

  /* 1. default scene (vacuum×2 + displace×2 @ x=0) renders as staff */
  const staff = await waitEval(ws, `(() => {
    const s = document.getElementById("staff");
    if (!s || !s.querySelector(".staff__row")) return null;
    return {
      rows: s.querySelectorAll(".staff__row").length,
      gates: s.querySelectorAll(".gate:not(.gate--preview):not(.gate--ghost)").length,
      srcLabels: [...s.querySelectorAll(".staff__source")].map((e) => e.textContent).filter(Boolean),
      palette: [...document.querySelectorAll(".palette__item")].map((e) => e.dataset.op),
      jsonHasDisplace: document.getElementById("json-input").value.includes('"op": "displace"'),
      gridLines: getComputedStyle(s.querySelector(".staff__grid")).backgroundImage !== "none",
    };
  })()`);
  check("staff: default scene = 2 lanes (2 vacuum sources)", staff.rows === 2, JSON.stringify(staff));
  check("staff: 2 displace gates rendered", staff.gates === 2, String(staff.gates));
  check("staff: 2 vacuum source labels", staff.srcLabels.length === 2 && staff.srcLabels.every((t) => t.startsWith("真空模")), JSON.stringify(staff.srcLabels));
  check("palette: tmsv+coherent hidden, vacuum present", staff.palette.includes("vacuum") && !staff.palette.includes("tmsv") && !staff.palette.includes("coherent"), JSON.stringify(staff.palette));
  check("JSON: graph→json sync intact (displace)", staff.jsonHasDisplace);
  check("grid: cell column rules rendered", staff.gridLines);
  /* covariance tables: split layout labels (x0,x1,…,p0,p1,…) + displaced
     means land on the x rows (√2·α≈1.414) not the p rows */
  const cov = await evalJs(ws, `(async () => {
    const t0 = Date.now();
    while (Date.now() - t0 < 8000 && !/^ok ·/.test(document.getElementById("status").textContent)) await new Promise((r) => setTimeout(r, 100));
    const heads = [...document.querySelectorAll("#v-table thead th")].slice(1).map((h) => h.textContent);
    const rbar = [...document.querySelectorAll("#rbar-table tbody tr")].map((tr) => tr.textContent);
    return { heads, rbar };
  })()`);
  check("cov: split labels x0,x1,p0,p1; x-mean 1.414 on x rows, 0 on p rows",
    JSON.stringify(cov.heads) === JSON.stringify(["mode 0·x", "mode 1·x", "mode 0·p", "mode 1·p"]) &&
    cov.rbar[0].includes("1.414") && cov.rbar[1].includes("1.414") &&
    cov.rbar[2].includes("0") && cov.rbar[3].includes("0"),
    JSON.stringify(cov));
  /* default scene gates snap to column 0 */
  const defX = await evalJs(ws, `(() => JSON.parse(document.getElementById("json-input").value).nodes.filter((n) => n.op === "displace").map((n) => n.ui.x))()`);
  check("default: displace gates at x=0", JSON.stringify(defX) === "[0,0]", JSON.stringify(defX));

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
  check("place single: phase on mode 1, x snapped to integer col", singleCheck && singleCheck.mode === 1 && Number.isInteger(singleCheck.x) && singleCheck.x >= 0, JSON.stringify(singleCheck));

  /* 3. two-mode two-step: drag beamsplitter onto lane 0 → preview + hint → click lane 1 */
  const bs = await drag(ws, { from: '[data-op="beamsplitter"]', to: '.staff__row[data-mode="0"] .staff__lane', dx: 250 });
  await waitEval(ws, `document.querySelector(".gate--preview")`);
  const placing = await evalJs(ws, `(() => ({
    preview: !!document.querySelector(".gate--preview"),
    armRows: document.querySelectorAll(".staff__lane--arm").length,
    hints: document.querySelectorAll(".staff__lane-hint").length,
    hintText: document.querySelector(".staff__lane-hint")?.textContent || "",
    status: document.getElementById("status").textContent,
  }))()`);
  check("two-mode: preview + armed lane + hint", placing.preview && placing.armRows === 1 && placing.hints === 1 && placing.hintText === "→ 点击" && /选择第二个模式/.test(placing.status), JSON.stringify(placing));

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

  /* 4b. L5.5 conflict rejection: drop squeeze onto occupied cell (d0 @ (0,0)) */
  const gridL = await evalJs(ws, `document.querySelector(".staff__grid").getBoundingClientRect().left`);
  const cell0CX = gridL + 132 + 0.3 * 72; // column 0 (off .5 boundary: round(0.3)=0)
  /* hover preview: conflict cell turns red + ghost shows */
  const hoverPreview = await evalJs(ws, `(async () => {
    const el = document.querySelector('[data-op="squeeze"]');
    const lane = document.querySelector('.staff__row[data-mode="0"] .staff__lane');
    const r = lane.getBoundingClientRect();
    const dtStart = new DataTransfer();
    el.dispatchEvent(new DragEvent("dragstart", { dataTransfer: dtStart, bubbles: true }));
    // real-browser behaviour: no payload readable via getData during dragover
    const dt = new DataTransfer();
    lane.dispatchEvent(new DragEvent("dragover", { dataTransfer: dt, bubbles: true, cancelable: true, clientX: ${cell0CX}, clientY: r.top + 10 }));
    const ghost = document.querySelector(".gate--ghost");
    const out = {
      conflict: lane.classList.contains("staff__lane--conflict"),
      ghost: !!ghost,
      ghostConflict: !!(ghost && ghost.classList.contains("gate--conflict")),
      ghostText: ghost ? ghost.textContent : "",
    };
    lane.dispatchEvent(new DragEvent("dragleave", { dataTransfer: dt, bubbles: true, relatedTarget: document.body }));
    return out;
  })()`);
  check("hover preview: occupied cell → red conflict + ghost", hoverPreview.conflict && hoverPreview.ghost && hoverPreview.ghostConflict && /压缩/.test(hoverPreview.ghostText), JSON.stringify(hoverPreview));
  await drag(ws, { from: '[data-op="squeeze"]', to: '.staff__row[data-mode="0"] .staff__lane', clientX: cell0CX });
  await sleep(150);
  const conflict = await evalJs(ws, `(() => ({
    squeeze: JSON.parse(document.getElementById("json-input").value).nodes.some((n) => n.op === "squeeze"),
    status: document.getElementById("status").textContent,
  }))()`);
  check("conflict: squeeze onto (0,0) rejected + hint", !conflict.squeeze && /已被占用/.test(conflict.status), JSON.stringify(conflict));

  /* 4c. L5.5 two-mode locks both cells: BS @ [0,1] x4, then squeeze onto (1,4) rejected */
  const cell4CX = gridL + 132 + 4.3 * 72; // column 4 (off .5 boundary: round(4.3)=4)
  await drag(ws, { from: '[data-op="beamsplitter"]', to: '.staff__row[data-mode="0"] .staff__lane', clientX: cell4CX });
  await waitEval(ws, `document.querySelector(".gate--preview")`);
  await click(ws, '.staff__row[data-mode="1"] .staff__lane');
  await waitEval(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    const bs = j.nodes.filter((n) => n.op === "beamsplitter");
    return bs.length === 2 && bs.some((b) => b.ui.x === 4);
  })()`);
  const bsGateCX = await evalJs(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    const id = j.nodes.filter((n) => n.op === "beamsplitter").at(-1).id;
    const g = document.querySelector('.gate[data-id="' + id + '"]');
    return g.getBoundingClientRect().left + g.getBoundingClientRect().width / 2;
  })()`);
  await drag(ws, { from: '[data-op="squeeze"]', to: '.staff__row[data-mode="1"] .staff__lane', clientX: bsGateCX });
  await sleep(150);
  const bsLock = await evalJs(ws, `(() => ({
    squeeze: JSON.parse(document.getElementById("json-input").value).nodes.some((n) => n.op === "squeeze"),
    status: document.getElementById("status").textContent,
  }))()`);
  check("two-mode lock: squeeze onto BS second lane rejected", !bsLock.squeeze && /已被占用/.test(bsLock.status), JSON.stringify(bsLock));

  /* 5. move existing gate: drag displace d0 (lane 0) further right */
  const lossBefore = await evalJs(ws, `(() => JSON.parse(document.getElementById("json-input").value).nodes.find((n) => n.id === "d0").ui.x)()`);
  const moved = await drag(ws, { from: '.gate[data-id="d0"]', to: '.staff__row[data-mode="0"] .staff__lane', dx: 400 });
  await waitEval(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    return j.nodes.find((n) => n.id === "d0").ui.x > ${lossBefore};
  })()`);
  const lossAfter = await evalJs(ws, `(() => JSON.parse(document.getElementById("json-input").value).nodes.find((n) => n.id === "d0").ui.x)()`);
  check("move gate: d0 x increased + integer, JSON synced", lossAfter > lossBefore && Number.isInteger(lossAfter), `${lossBefore} → ${lossAfter}`);

  /* 6. delete via hover × */
  const delClick = await evalJs(ws, `(async () => {
    const g = document.querySelector('.gate[data-id="d1"]');
    g.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
    const btn = g.querySelector(".gate__del");
    btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 100));
    const j = JSON.parse(document.getElementById("json-input").value);
    return !j.nodes.some((n) => n.id === "d1");
  })()`);
  check("delete gate: d1 removed, JSON synced", delClick);

  /* 6b. L5.5 empty columns: grid must have spare cells ahead of the last gate
     (initial width covers 10+ columns) so drops land far beyond current gates */
  const farCol = await evalJs(ws, `(async () => {
    const g = (id) => document.getElementById(id);
    const grid = document.querySelector(".staff__grid");
    const gridW = grid.getBoundingClientRect().width;
    const lane = document.querySelector('.staff__row[data-mode="0"] .staff__lane');
    const r = lane.getBoundingClientRect();
    const cx = grid.getBoundingClientRect().left + 132 + 8.3 * 72; // column 8
    const dtStart = new DataTransfer();
    const el = document.querySelector('[data-op="squeeze"]');
    el.dispatchEvent(new DragEvent("dragstart", { dataTransfer: dtStart, bubbles: true }));
    const dt = new DataTransfer();
    lane.dispatchEvent(new DragEvent("dragover", { dataTransfer: dt, bubbles: true, cancelable: true, clientX: cx, clientY: r.top + 10 }));
    const ghostX = document.querySelector(".gate--ghost")?.style.left || "";
    lane.dispatchEvent(new DragEvent("drop", { dataTransfer: dt, bubbles: true, cancelable: true, clientX: cx, clientY: r.top + 10 }));
    await new Promise((r2) => setTimeout(r2, 120));
    const j = JSON.parse(g("json-input").value);
    const n = j.nodes.find((x) => x.op === "squeeze");
    return { gridW, ghostX, placedX: n ? n.ui.x : null };
  })()`);
  check("far empty column: drop at x=8 works, grid ≥ 10 cols", farCol.gridW >= 132 + 10 * 72 && farCol.placedX === 8 && Math.round((parseFloat(farCol.ghostX) - 132) / 72) === 8, JSON.stringify(farCol));

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

  /* 8b. UX: palette grouped (源/门/通道/测量) with data-op preserved */
  const groups = await evalJs(ws, `(() => ({
    titles: [...document.querySelectorAll(".palette__group-title")].map((t) => t.textContent),
    items: [...document.querySelectorAll(".palette__item")].map((c) => c.dataset.op),
    inGroup: [...document.querySelectorAll(".palette__group")].map((g) => g.querySelectorAll(".palette__item").length),
  }))()`);
  check("palette: 4 groups 源/门/通道/测量, op order kept, palette:false hidden",
    JSON.stringify(groups.titles) === JSON.stringify(["源", "门", "通道", "测量"]) &&
    groups.items.length === 11 && !groups.items.includes("tmsv") && !groups.items.includes("coherent") &&
    groups.inGroup[0] === 1 && groups.inGroup[1] === 6 && groups.inGroup[2] === 2 && groups.inGroup[3] === 2,
    JSON.stringify(groups));

  /* 8c. Fitts: delete button ≥ 24px hit area (visual 18px circle drawn
        inside the 24px transparent hit box) */
  const delHit = await evalJs(ws, `(() => {
    const g = document.querySelector(".gate");
    g.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
    const del = g.querySelector(".gate__del");
    const r = del.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) };
  })()`);
  check("delete hit area ≥ 24×24", delHit.w >= 24 && delHit.h >= 24, JSON.stringify(delHit));

  /* 9. source click opens the param card (vacuum: no knobs, info shown) */
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
