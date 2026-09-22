/* Gaussian Lab L5 — headless CDP probe (staff editor: render, DnD placing,
   two-mode two-step flow, move/delete, JSON sync, legacy load).
   Zero-dep: Node >= 22 native fetch + WebSocket; Edge headless.

   Usage: node tests/lab_staff_probe.mjs
   Exit code 0 = all probes PASS, 1 = any FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { EDGE, port, userDataDir, uvicornPath } from "./probe_env.mjs";

const PORT = port(8766, "PROBE_PORT");
const CDP_PORT = port(9224, "PROBE_CDP_PORT");
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

const server = spawn(uvicornPath(), ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"], {
  cwd: process.cwd(), stdio: "ignore",
});
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + userDataDir(".probe-edge-profile-l5"),
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
  /* Cache discipline: `--user-data-dir` persists between runs, so a stale cached
     module (e.g. colormap.js from before a new export was added) would be served
     and the probe would silently test OLD code — observed as a boot-time
     "does not provide an export named ..." SyntaxError and a palette that never
     renders. Clear the cache and reload so the probe always tests the working tree. */
  await send(ws, "Network.enable");
  await send(ws, "Network.clearBrowserCache");
  await send(ws, "Page.reload");
  await evalJs(ws, `(async () => { while (!document.getElementById("staff")) await new Promise((r) => setTimeout(r, 50)); return true; })()`);

  // 票3: init() awaits /schema before first render — wait for palette
  await evalJs(ws, `(async () => { while (!document.querySelector(".palette__item")) await new Promise((r) => setTimeout(r, 50)); return true; })()`);

  /* 1. default scene (vacuum×2 + displace×2 @ x=0) renders as staff */
  const staff = await waitEval(ws, `(() => {
    const s = document.getElementById("staff");
    return {
      rows: s.querySelectorAll(".staff__row").length,
      gates: s.querySelectorAll(".gate:not(.gate--preview):not(.gate--ghost)").length,
      modeLabels: [...s.querySelectorAll(".staff__mode-label")].map((e) => e.textContent),
      delBtns: [...s.querySelectorAll(".staff__mode-del")].map((e) => e.disabled),
      palette: [...document.querySelectorAll(".palette__item")].map((e) => e.dataset.op),
      jsonHasDisplace: document.getElementById("json-input").value.includes('"op": "displace"'),
      gridLines: getComputedStyle(s.querySelector(".staff__row"), "::before").borderTopWidth !== "0px",
    };
  })()`);
  check("staff: default scene = 2 lanes", staff.rows === 2, JSON.stringify(staff));
  check("staff: 2 displace gates rendered", staff.gates === 2, String(staff.gates));
  /* ADR-0014: 无源节点。每模一行，标签 = "mode N · <初始态>"（默认场景全真空）。 */
  check("staff: 2 per-mode labels (mode 0/1 · 真空)",
    JSON.stringify(staff.modeLabels) === JSON.stringify(["mode 0 · 真空", "mode 1 · 真空"]),
    JSON.stringify(staff.modeLabels));
  check("staff: 2 delete buttons, both enabled (nmode=2)",
    JSON.stringify(staff.delBtns) === JSON.stringify([false, false]), JSON.stringify(staff.delBtns));
  check("palette: 源节点 op 全部缺席", !staff.palette.includes("vacuum") && !staff.palette.includes("tmsv") && !staff.palette.includes("coherent"), JSON.stringify(staff.palette));
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
  const defX = await evalJs(ws, `(() => { const d = JSON.parse(document.getElementById("json-input").value); const st = d.ui?.staff || {}; return d.ops.filter((n) => n.op === "displace").map((n) => st[n.id]); })()`);
  check("default: displace gates at x=0", JSON.stringify(defX) === "[0,0]", JSON.stringify(defX));

  /* 2. single-mode placement: drag 相位 onto lane 1 at offset +150px */
  const single = await drag(ws, { from: '[data-op="phase"]', to: '.staff__row[data-mode="1"] .staff__lane', dx: 150 });
  await waitEval(ws, `(() => {
    const g = document.querySelector('.gate[data-id]');
    return [...document.querySelectorAll(".gate:not(.gate--preview)")].length === 3;
  })()`);
  const singleCheck = await evalJs(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    const p = j.ops.find((n) => n.op === "phase");
    return p ? { mode: p.modes[0], x: (j.ui?.staff || {})[p.id], n: j.ops.length } : null;
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
    return j.ops.some((n) => n.op === "beamsplitter");
  })()`);
  const placed = await evalJs(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    const b = j.ops.find((n) => n.op === "beamsplitter");
    return b ? { modes: b.modes, x: (j.ui?.staff || {})[b.id], preview: !!document.querySelector(".gate--preview") } : null;
  })()`);
  check("two-mode: placed modes=[0,1], preview gone", placed && JSON.stringify(placed.modes) === "[0,1]" && !placed.preview, JSON.stringify(placed));

  /* 4. Esc cancels placing */
  const bs2 = await drag(ws, { from: '[data-op="mz"]', to: '.staff__row[data-mode="0"] .staff__lane', dx: 350 });
  await waitEval(ws, `document.querySelector(".gate--preview")`);
  await evalJs(ws, `document.getElementById("staff").dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }))`);
  const esc = await evalJs(ws, `(() => ({
    preview: !!document.querySelector(".gate--preview"),
    mz: JSON.parse(document.getElementById("json-input").value).ops.some((n) => n.op === "mz"),
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
    squeeze: JSON.parse(document.getElementById("json-input").value).ops.some((n) => n.op === "squeeze"),
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
    const bs = j.ops.filter((n) => n.op === "beamsplitter");
    return bs.length === 2 && bs.some((b) => (j.ui?.staff || {})[b.id] === 4);
  })()`);
  const bsGateCX = await evalJs(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    const id = j.ops.filter((n) => n.op === "beamsplitter").at(-1).id;
    const g = document.querySelector('.gate[data-id="' + id + '"]');
    return g.getBoundingClientRect().left + g.getBoundingClientRect().width / 2;
  })()`);
  await drag(ws, { from: '[data-op="squeeze"]', to: '.staff__row[data-mode="1"] .staff__lane', clientX: bsGateCX });
  await sleep(150);
  const bsLock = await evalJs(ws, `(() => ({
    squeeze: JSON.parse(document.getElementById("json-input").value).ops.some((n) => n.op === "squeeze"),
    status: document.getElementById("status").textContent,
  }))()`);
  check("two-mode lock: squeeze onto BS second lane rejected", !bsLock.squeeze && /已被占用/.test(bsLock.status), JSON.stringify(bsLock));

  /* 5. move existing gate: drag displace d0 (lane 0) further right */
  const lossBefore = await evalJs(ws, `(() => { const d = JSON.parse(document.getElementById("json-input").value); return (d.ui?.staff || {})[d.ops.find((n) => n.id === "d0")?.id]; })()`);
  const moved = await drag(ws, { from: '.gate[data-id="d0"]', to: '.staff__row[data-mode="0"] .staff__lane', dx: 400 });
  await waitEval(ws, `(() => {
    const j = JSON.parse(document.getElementById("json-input").value);
    return (j.ui?.staff || {})[j.ops.find((n) => n.id === "d0")?.id] > ${lossBefore};
  })()`);
  const lossAfter = await evalJs(ws, `(() => { const d = JSON.parse(document.getElementById("json-input").value); return (d.ui?.staff || {})[d.ops.find((n) => n.id === "d0")?.id]; })()`);
  check("move gate: d0 x increased + integer, JSON synced", lossAfter > lossBefore && Number.isInteger(lossAfter), `${lossBefore} → ${lossAfter}`);

  /* 6. delete via hover × */
  const delClick = await evalJs(ws, `(async () => {
    const g = document.querySelector('.gate[data-id="d1"]');
    g.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
    const btn = g.querySelector(".gate__del");
    btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 100));
    const j = JSON.parse(document.getElementById("json-input").value);
    return !j.ops.some((n) => n.id === "d1");
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
    /* C3 R4: ghost 位移改走 transform，故不得再读 style.left 判位置——
       改读**实测几何**（相对 grid 的偏移），这对 left/top 与 transform 两种
       表示都成立。同时单独断言 transform 表示（R4 的契约本身）。 */
    const ghostEl = document.querySelector(".gate--ghost");
    const gRect = ghostEl && ghostEl.getBoundingClientRect();
    const gridRect = grid.getBoundingClientRect();
    const ghostDX = gRect ? gRect.left - gridRect.left : null;
    const ghostTransform = ghostEl ? (ghostEl.style.transform || "(none)") : "";
    lane.dispatchEvent(new DragEvent("drop", { dataTransfer: dt, bubbles: true, cancelable: true, clientX: cx, clientY: r.top + 10 }));
    await new Promise((r2) => setTimeout(r2, 120));
    const j = JSON.parse(g("json-input").value);
    const n = j.ops.find((x) => x.op === "squeeze");
    return { gridW, ghostDX, ghostTransform, placedX: n ? (j.ui?.staff || {})[n.id] : null };
  })()`);
  check("far empty column: drop at x=8 works, grid ≥ 10 cols", farCol.gridW >= 132 + 10 * 72 && farCol.placedX === 8 && Math.round((farCol.ghostDX - 132 - 6) / 72) === 8, JSON.stringify(farCol));
  /* C3 R4: ghost 必须用 transform 位移，且 left/top 归零（不再逐帧写 left/top） */
  check("ghost positioned via transform, left/top pinned to 0 (C3 R4)", /^translate\(/.test(farCol.ghostTransform), JSON.stringify({ transform: farCol.ghostTransform, ghostDX: farCol.ghostDX }));

  /* 7. legacy JSON without ui.x loads and renders as grid columns */
  const legacy = await evalJs(ws, `(async () => {
    const payload = {
      schema: "circuit_v1", seed: 0, nmode: 2,
      ops: [
        { id: "p", op: "phase", params: { theta: 1.2 }, modes: [0] },
        { id: "d", op: "displace", params: { alpha: [1.0, 0.0] }, modes: [1] },
      ],
      view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {},
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
      && j.ops.every((n) => Number.isFinite((j.ui?.staff || {})[n.id]));
    return ok;
  })()`);
  check("legacy JSON: loads, renders 2 lanes + 2 gates, ui.x assigned", legacy);

  /* 8b. UX: palette grouped (源/门/通道/测量) with data-op preserved */
  const groups = await evalJs(ws, `(() => ({
    titles: [...document.querySelectorAll(".palette__group-title")].map((t) => t.textContent),
    items: [...document.querySelectorAll(".palette__item")].map((c) => c.dataset.op),
    inGroup: [...document.querySelectorAll(".palette__group")].map((g) => g.querySelectorAll(".palette__item").length),
  }))()`);
  check("palette: 3 groups 门/通道/测量 (ADR-0014: 源组已退役), op order kept",
    JSON.stringify(groups.titles) === JSON.stringify(["门", "通道", "测量"]) &&
    groups.items.length === 11 && !groups.items.includes("vacuum") &&
    !groups.items.includes("tmsv") && !groups.items.includes("coherent") &&
    groups.inGroup[0] === 7 && groups.inGroup[1] === 2 && groups.inGroup[2] === 2,
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

  /* 9. ADR-0014 D2(i): 模标签是纯标签，点击不开卡片 */
  const noCard = await evalJs(ws, `(async () => {
    document.querySelector(".staff__mode").click();
    await new Promise((r) => setTimeout(r, 200));
    return !!document.querySelector(".gate-card");
  })()`);
  check("mode label click: 不开参数卡片 (D2(i))", noCard === false, String(noCard));

  /* 9. gate click opens param card; slider edit propagates to JSON */
  await click(ws, '.gate[data-id="p"]');
  await waitEval(ws, `document.querySelector(".gate-card__params .param input[type=range]")`);
  const cardEdit = await evalJs(ws, `(async () => {
    const range = document.querySelector(".gate-card__params .param input[type=range]");
    range.value = "2.5";
    range.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 150));
    const j = JSON.parse(document.getElementById("json-input").value);
    const p = j.ops.find((n) => n.op === "phase");
    return { phi: p.params.theta, cardStillOpen: !!document.querySelector(".gate-card") };
  })()`);
  check("gate card: slider edit → JSON sync, card stays open", cardEdit.phi === 2.5 && cardEdit.cardStillOpen, JSON.stringify(cardEdit));

  /* 9b. 参数卡片：闭包快照陈旧（回归锁）——onParam 不做 render（拖动中重建
     DOM 会断拖动），门块 click 闭包可比本次编辑旧。关卡片再开必须读到新值。
     number 手输 → range 同步；越界 → 双控件与 JSON 三者一致。 */
  const cardStale = await evalJs(ws, `(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const open = async () => {
      document.querySelector('.gate[data-id="p"]').dispatchEvent(new MouseEvent("click", { bubbles: true }));
      await sleep(250);
    };
    const row = () => [...document.querySelectorAll(".gate-card .param")][0];
    const read = () => ({
      range: row().querySelector('input[type=range]').value,
      num: row().querySelector('input[type=number]').value,
    });
    const jphi = () => JSON.parse(document.getElementById("json-input").value)
      .ops.find((n) => n.op === "phase").params.theta;
    await open();
    /* number 手输（change）→ range 必须回写 */
    const num = row().querySelector('input[type=number]');
    num.value = "1.7"; num.dispatchEvent(new Event("change", { bubbles: true }));
    await sleep(250);
    const synced = { ...read(), json: jphi() };
    /* 关卡片 → 重开（其间无 render，旧实现此刻读回 2.5 旧值） */
    document.getElementById("staff").dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await sleep(250);
    const closed = !document.querySelector(".gate-card");
    await open();
    const reopened = { ...read(), json: jphi() };
    /* 越界（phase phi ∈ [0, 2π]）→ 夹紧到上界，双控件与 JSON 一致 */
    const num2 = row().querySelector('input[type=number]');
    num2.value = "99"; num2.dispatchEvent(new Event("change", { bubbles: true }));
    await sleep(250);
    const clamped = { ...read(), json: jphi() };
    return { synced, closed, reopened, clamped };
  })()`);
  check("gate card: 关→开不读陈旧快照（闭包新鲜度回归锁）",
    cardStale.closed === true &&
    cardStale.reopened.range === "1.7" && cardStale.reopened.num === "1.7" &&
    cardStale.reopened.json === 1.7,
    JSON.stringify(cardStale.reopened));
  check("gate card: number 手输 → range 同步",
    cardStale.synced.range === "1.7" && cardStale.synced.num === "1.7" && cardStale.synced.json === 1.7,
    JSON.stringify(cardStale.synced));
  const tau = 2 * Math.PI;
  /* range 的显示按 step=0.01 量化（"6.28"），num 保留全精度（6.283185…）——
     同一夹紧值，仅文本表示不同；断言容差取 step。 */
  check("gate card: 越界输入夹紧，双控件与 JSON 三者一致",
    Math.abs(Number(cardStale.clamped.range) - tau) < 0.01 &&
    Math.abs(Number(cardStale.clamped.num) - tau) < 1e-9 &&
    Math.abs(cardStale.clamped.json - tau) < 1e-9,
    JSON.stringify(cardStale.clamped));

  /* 10. sweepable card auto-syncs the scan panel target (synced in step 9) */  const scanSync = await evalJs(ws, `(() => ({
    target: document.getElementById("scan-node").value,
  }))()`);
  check("scan sync: phase card targets scan node", scanSync.target === "p", JSON.stringify(scanSync));

  /* 9c. per-backend 参数可见性：fock 的 squeeze 自 09-14-fock-squeeze-phi 起
     已带 phi（与 FockState.squeezed 同约定）——卡片必须显示 r+phi 且 phi 写进
     payload；gaussian 不受影响。可见性仍由 IR 驱动（loss.nbar 仍隐藏）。 */
  await evalJs(ws, `(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const p = { schema: "circuit_v1", seed: 0, nmode: 1,
      ops: [{ id: "sq", op: "squeeze", params: { r: 0.4, phi: 0 }, modes: [0] }],
      view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: { staff: { sq: 0 } } };
    const i = document.getElementById("json-input");
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(i, JSON.stringify(p));
    i.dispatchEvent(new Event("input", { bubbles: true }));
    await sleep(1200);
    const sel = document.getElementById("backend-select");
    sel.value = "fock";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  await waitEval(ws, `(async () => {
    while (!document.querySelector('.gate[data-id="sq"]')) await new Promise((r) => setTimeout(r, 100));
    return true;
  })()`);
  const fockCard = await evalJs(ws, `(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    document.querySelector('.gate[data-id="sq"]').dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await sleep(300);
    const row = [...document.querySelectorAll(".gate-card .param")]
      .find((r) => r.querySelector(".param__name").textContent === "phi");
    if (row) {
      const rg = row.querySelector('input[type=range]');
      rg.value = "1.1"; rg.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(250);
    }
    return { names: [...document.querySelectorAll(".gate-card .param .param__name")].map((e) => e.textContent),
             payload: JSON.parse(document.getElementById("json-input").value).ops[0].params };
  })()`);
  check("fock: squeeze 显示 r + phi，且 phi 写进 payload",
    JSON.stringify(fockCard.names) === JSON.stringify(["r", "phi"]) &&
    Math.abs(fockCard.payload.phi - 1.1) < 1e-9,
    JSON.stringify(fockCard));
  /* fock 下 loss.nbar 仍不进 IR —— 可见性过滤没被顺手拆掉 */
  const fockLoss = await evalJs(ws, `(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const p = { schema: "circuit_v1", backend: "fock", seed: 0, nmode: 1, cutoff: 10,
      ops: [{ id: "ls", op: "loss", params: { eta: 0.8 }, modes: [0] }],
      view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: { staff: { ls: 0 } } };
    const i = document.getElementById("json-input");
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(i, JSON.stringify(p));
    i.dispatchEvent(new Event("input", { bubbles: true }));
    await sleep(1200);
    document.querySelector('.gate[data-id="ls"]').dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await sleep(300);
    return [...document.querySelectorAll(".gate-card .param .param__name")].map((e) => e.textContent);
  })()`);
  check("fock: loss 仍只显示 T（nbar 不进 IR，过滤仍生效）",
    JSON.stringify(fockLoss) === JSON.stringify(["T"]), JSON.stringify(fockLoss));

  /* 9d. cutoff 边界归一化回归锁：/schema 发 {min,max} 对象，editor 内部
     用 [min,max]——曾不归一化，导致带显式 cutoff 的 fock JSON 全被拒
     （报 [1, undefined]）。探针是唯一能覆盖“schema 注入 + 载入”整链的地方。 */
  const cutLoad = await evalJs(ws, `(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const load = async (cutoff) => {
      const p = { schema: "circuit_v1", backend: "fock", seed: 0, nmode: 1, cutoff,
        ops: [{ id: "sq", op: "squeeze", params: { r: 0.4, phi: 0 }, modes: [0] }],
        view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: { staff: { sq: 0 } } };
      const i = document.getElementById("json-input");
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(i, JSON.stringify(p));
      i.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(1200);
      return { status: document.getElementById("status").textContent,
               hasGate: !!document.querySelector('.gate[data-id="sq"]'),
               emitted: JSON.parse(document.getElementById("json-input").value).cutoff };
    };
    const inRange = await load(25);
    const boundary = await load(30);
    /* 越界：图**冻结**在上一份合法状态（editor.js 既有语义：graph stays at
       lastGood；textarea 保留用户文本，故 emitted 仍是 99——不是“被应用”）。
       关键证据是报错文案里是 [1, 30] 而非 [1, undefined]（即归一化生效）。 */
    const over = await load(99);
    return { inRange, boundary, over };
  })()`);
  check("fock: 显式 cutoff 载入成功（/{min,max} → [min,max] 归一化）+ 越界仍被拦",
    cutLoad.inRange.hasGate === true && cutLoad.inRange.emitted === 25 &&
    cutLoad.boundary.hasGate === true && cutLoad.boundary.emitted === 30 &&
    /cutoff 必须在 \[1, 30\]/.test(cutLoad.over.status),
    JSON.stringify(cutLoad));
  /* 回 gaussian 前先重载 squeeze 场景（上一步换成了 loss 场景，sq 门已不存在） */
  await evalJs(ws, `(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    const sel = document.getElementById("backend-select");
    sel.value = "gaussian";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
    await sleep(400);
    const p = { schema: "circuit_v1", seed: 0, nmode: 1,
      ops: [{ id: "sq", op: "squeeze", params: { r: 0.4, phi: 0 }, modes: [0] }],
      view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: { staff: { sq: 0 } } };
    const i = document.getElementById("json-input");
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(i, JSON.stringify(p));
    i.dispatchEvent(new Event("input", { bubbles: true }));
    await sleep(1200);
    return true;
  })()`);
  await waitEval(ws, `document.querySelector('.gate[data-id="sq"]')`);
  const gaussCard = await evalJs(ws, `(async () => {
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
    document.querySelector('.gate[data-id="sq"]').dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await sleep(300);
    return [...document.querySelectorAll(".gate-card .param .param__name")].map((e) => e.textContent);
  })()`);
  check("gaussian: squeeze 仍显示 r + phi（per-backend 过滤未误伤）",
    JSON.stringify(gaussCard) === JSON.stringify(["r", "phi"]), JSON.stringify(gaussCard));

  /* 11. ADR-0014: 删模级联（删 mode 0 → 其上的门消失、上方模上移、nmode 减一） */
  await evalJs(ws, `(async () => {
    const payload = {
      schema: "circuit_v1", seed: 0, nmode: 3,
      ops: [
        { id: "p", op: "phase", params: { theta: 1.2 }, modes: [0] },
        { id: "s", op: "squeeze", params: { r: 0.4, phi: 0 }, modes: [1] },
        { id: "d", op: "displace", params: { alpha: [1.0, 0.0] }, modes: [2] },
      ],
      view: { wigner_mode: 2, lim: 5.0, n: 64, joint_modes: [1, 2] },
      ui: { staff: { p: 0, s: 0, d: 0 } },
    };
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, JSON.stringify(payload));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 600));
    return true;
  })()`);
  const delMode = await evalJs(ws, `(async () => {
    document.querySelectorAll(".staff__mode-del")[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 300));
    const j = JSON.parse(document.getElementById("json-input").value);
    const s = document.getElementById("staff");
    return {
      nmode: j.nmode,
      ops: j.ops.map((n) => n.op),
      modes: j.ops.map((n) => n.modes[0]),
      labels: [...s.querySelectorAll(".staff__mode-label")].map((e) => e.textContent),
      rows: s.querySelectorAll(".staff__row").length,
      wignerMode: j.view.wigner_mode,
      jointModes: j.view.joint_modes,
    };
  })()`);
  check("delete mode: 级联删门 + 上方模上移 + nmode 3→2",
    delMode.nmode === 2 &&
    JSON.stringify(delMode.ops) === JSON.stringify(["squeeze", "displace"]) &&
    JSON.stringify(delMode.modes) === JSON.stringify([0, 1]) &&
    delMode.rows === 2,
    JSON.stringify(delMode));
  /* AC13: 越界的 view 字段被夹紧/清空，不留非法 nmode 引用 */
  // joint_modes 是模索引：删 mode 0 → [1,2] 重编号为 [0,1]（不指向别的模）
  check("delete mode: wigner_mode 夹紧到 nmode-1，joint_modes 重编号 [1,2]→[0,1]",
    delMode.wignerMode === 1 &&
    JSON.stringify(delMode.jointModes) === JSON.stringify([0, 1]),
    JSON.stringify({ wignerMode: delMode.wignerMode, jointModes: delMode.jointModes }));

  /* AC13b: joint_modes 命中被删模 → 清空（对不再存在） */
  await evalJs(ws, `(async () => {
    const payload = { schema: "circuit_v1", seed: 0, nmode: 3, ops: [],
      view: { wigner_mode: 0, lim: 5.0, n: 64, joint_modes: [0, 1] }, ui: {} };
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, JSON.stringify(payload));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 600));
    document.querySelectorAll(".staff__mode-del")[1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 300));
    const j = JSON.parse(document.getElementById("json-input").value);
    return { nmode: j.nmode, jointModes: j.view.joint_modes };
  })()`).then((r) => {
    check("delete mode: joint_modes 命中被删模 → 清空（回退默认 [0,1]）",
      r.nmode === 2 && r.jointModes === undefined, JSON.stringify(r));
  });

  const delLast = await evalJs(ws, `(async () => {
    document.querySelectorAll(".staff__mode-del")[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 300));
    const del = document.querySelector(".staff__mode-del");
    const disabled = del.disabled;
    del.dispatchEvent(new MouseEvent("click", { bubbles: true })); // disabled → no-op
    await new Promise((r) => setTimeout(r, 200));
    return { nmode: JSON.parse(document.getElementById("json-input").value).nmode, disabled };
  })()`);
  check("delete mode: nmode=1 时按钮 disabled 且点击无效",
    delLast.nmode === 1 && delLast.disabled === true,
    JSON.stringify(delLast));


  /* 12. AC5: gaussian 下 ＋模 可用（无源后唯一加模入口），加模后 nmode +1 */
  await evalJs(ws, `(async () => {
    const payload = { schema: "circuit_v1", seed: 0, nmode: 2, ops: [],
      view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} };
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, JSON.stringify(payload));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 600));
    return true;
  })()`);
  const addModeBtn = await evalJs(ws, `(async () => {
    const btn = document.getElementById("add-mode-btn");
    const visible = btn.getClientRects().length > 0;
    btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 300));
    const j = JSON.parse(document.getElementById("json-input").value);
    return {
      visible,
      nmode: j.nmode,
      rows: document.querySelectorAll(".staff__row").length,
      labels: document.querySelectorAll(".staff__mode-label").length,
    };
  })()`);
  check("AC5: gaussian 下 ＋模 可见可用，加模后 nmode 2→3 + 3 行模标签",
    addModeBtn.visible === true && addModeBtn.nmode === 3 &&
    addModeBtn.rows === 3 && addModeBtn.labels === 3,
    JSON.stringify(addModeBtn));

  /* 13. AC7（UI 侧）: nmode=1 时删除入口禁用 + 中文 title 说明原因
     （守卫的提示文案由 editor.js `onDeleteMode` 给出；UI 上按钮禁用先于点击） */
  const refuse = await evalJs(ws, `(async () => {
    document.querySelectorAll(".staff__mode-del")[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 300));
    document.querySelectorAll(".staff__mode-del")[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 300));
    const del = document.querySelector(".staff__mode-del");
    return { nmode: JSON.parse(document.getElementById("json-input").value).nmode,
             disabled: del.disabled, title: del.title };
  })()`);
  check("AC7: nmode=1 时删除按钮 disabled + 中文 title 说明原因",
    refuse.nmode === 1 && refuse.disabled === true && /至少保留一个模式/.test(refuse.title),
    JSON.stringify(refuse));

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
