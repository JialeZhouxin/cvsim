/* Gaussian Lab L4 — headless CDP probe (A10: scan panel + curve + palette).
   Zero-dep: Node >= 22 native fetch + WebSocket; Edge headless as the browser.

   Usage: node tests/lab_scan_probe.mjs
   Spawns uvicorn (lab server) + headless Edge, drives the scan panel via CDP,
   cross-checks the E_N curve against the analytic 2r/ln2 via the page itself.
   Exit code 0 = all probes PASS, 1 = any FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const PORT = 8765;
const CDP_PORT = 9223;
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

const server = spawn(process.cwd() + "/.venv/Scripts/uvicorn.exe", ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"], {
  cwd: process.cwd(), stdio: "ignore",
});
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + process.cwd() + "/.probe-edge-profile",
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
  /* stale-cache guard: the persistent Edge profile may serve a cached
     index.html from an earlier run — clear the HTTP cache and reload so
     the probe always exercises the current static files (lab UI polish #6/#8) */
  await send(ws, "Network.enable");
  await send(ws, "Network.clearBrowserCache");
  await send(ws, "Page.reload");

  /* folds start collapsed (above-the-fold design); open scan for the scan flow */
  await evalJs(ws, `(async () => { while (!document.getElementById("scan-panel")) await new Promise((r) => setTimeout(r, 50)); document.getElementById("scan-panel").open = true; return true; })()`);

  /* wait for the editor to finish initial render before injecting (input
     events fired earlier are lost — no listener bound yet) */
  await evalJs(ws, `(async () => { while (!document.querySelector(".staff__row")) await new Promise((r) => setTimeout(r, 50)); return true; })()`);

  /* 1. panel renders with adaptive defaults for a sweepable scene (L5.5:
     the new default scene has no sweepable params, so inject a TMSV+loss
     scene first — the scan panel is a feature test, not a scene test) */
  await evalJs(ws, `(async () => {
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    const payload = {
      schema: "circuit_v0", seed: 0,
      nodes: [
        { id: "s0", op: "tmsv", params: { r: 0.6 }, modes: [0, 1] },
        { id: "l0", op: "loss", params: { T: 0.8 }, mode: 0 },
        { id: "l1", op: "loss", params: { T: 0.8 }, mode: 1 },
      ],
      edges: [], view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {},
    };
    setter.call(input, JSON.stringify(payload));
    input.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 600)); // 400ms debounce
    return true;
  })()`);
  const panel = await waitEval(ws, `(() => {
    const g = (id) => document.getElementById(id);
    if (!g("scan-node") || !g("scan-node").options.length) return null;
    return {
      nodes: [...g("scan-node").options].map((o) => o.value),
      param: g("scan-param").value,
      min: g("scan-min").value, max: g("scan-max").value, n: g("scan-n").value,
      modesA: [...g("scan-modes-a").options].map((o) => o.value + ":" + o.textContent),
      modesAVal: g("scan-modes-a").value,
      btnDisabled: g("scan-btn").disabled,
      noteHidden: g("scan-note").hidden,
    };
  })()`);
  check("scan node select lists all sweepable nodes", JSON.stringify(panel.nodes) === JSON.stringify(["s0", "l0", "l1"]), JSON.stringify(panel.nodes));
  check("scan param defaults to r", panel.param === "r", panel.param);
  check("adaptive defaults r: min=0 max=2 n=50", panel.min === "0" && panel.max === "2" && panel.n === "50", `${panel.min}..${panel.max} n=${panel.n}`);
  check("modes_A dropdown: 2-mode default [0]", panel.modesAVal === "1" && JSON.stringify(panel.modesA) === JSON.stringify(["1:[0..0]"]), JSON.stringify(panel.modesA));
  check("scan button enabled, note hidden", !panel.btnDisabled && panel.noteHidden);

  /* 2. run a scan → SVG polyline with n=20 finite points */
  const scan = await evalJs(ws, `(async () => {
    const g = (id) => document.getElementById(id);
    // wait for the initial auto-run so its status cannot overwrite the scan status
    const tWait = Date.now();
    while (Date.now() - tWait < 10000 && !/^(ok|scan ok) ·/.test(g("status").textContent)) {
      await new Promise((r) => setTimeout(r, 100));
    }
    g("scan-min").value = "0.2";
    g("scan-max").value = "1.2";
    g("scan-n").value = "20";
    g("scan-btn").click();
    const t0 = Date.now();
    while (Date.now() - t0 < 10000) {
      const st = g("status");
      if (st.textContent.includes("scan ok") && st.dataset.state === "ok") {
        const pl = document.querySelectorAll("#scan-svg polyline");
        const pts = pl.length ? pl[0].getAttribute("points").split(" ").length : 0;
        return { ok: true, status: st.textContent, polylines: pl.length, points: pts };
      }
      if (st.dataset.state === "error") return { ok: false, status: st.textContent };
      await new Promise((r) => setTimeout(r, 100));
    }
    return { ok: false, status: "timeout" };
  })()`);
  check("scan completes with ok status", scan.ok, scan.status);
  check("SVG curve drawn (1 polyline, 20 points)", scan.ok && scan.polylines === 1 && scan.points === 20, `polylines=${scan.polylines} points=${scan.points}`);

  /* 2b. #8: fold-title scan summary — one line with the max E_N value */
  const summary = await evalJs(ws, `(() => {
    const s = document.getElementById("scan-summary");
    const m = /^E_N 最大 (.+) @ r=/.exec(s.textContent || "");
    return { hidden: s.hidden, text: s.textContent, ok: !s.hidden && !!m && Number.isFinite(Number(m[1])) && Number(m[1]) > 0 };
  })()`);
  check("scan summary: E_N 最大 value in fold title (#8)", summary.ok, JSON.stringify(summary));

  /* 3. E_N curve vs analytic 2r/ln2 (page-side fetch, mirrors A7) */
  const analytic = await evalJs(ws, `(async () => {
    const state = { schema: "circuit_v0", seed: 0,
      nodes: [{ id: "s0", op: "tmsv", params: { r: 0.6 }, modes: [0, 1] }],
      edges: [], view: { wigner_mode: 0, lim: 4, n: 32 }, ui: {} };
    state.sweep = { node_id: "s0", param: "r", min: 0.1, max: 1.1, n: 20, modes_A: [0] };
    const r = await fetch("/scan", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state) });
    const j = await r.json();
    let maxErr = 0;
    for (let i = 0; i < j.ys.length; i++) maxErr = Math.max(maxErr, Math.abs(j.ys[i] - (2 * j.xs[i]) / Math.LN2));
    return { status: r.status, maxErr, n: j.ys.length, nulls: j.ys.filter((y) => y === null).length };
  })()`);
  check("E_N(r) matches analytic 2r/ln2 atol 1e-6", analytic.status === 200 && analytic.maxErr < 1e-6 && analytic.n === 20, `status=${analytic.status} maxErr=${analytic.maxErr.toExponential(2)} nulls=${analytic.nulls}`);

  /* 4. palette: amplifier + mz cards add nodes, /run stays green */
  const pal = await evalJs(ws, `(async () => {
    const g = (id) => document.getElementById(id);
    document.querySelector('[data-op="amplifier"]').click();
    document.querySelector('[data-op="mz"]').click();
    await new Promise((r) => setTimeout(r, 400));
    const gates = document.querySelectorAll(".gate:not(.gate--preview):not(.gate--ghost)").length;
    g("run-btn").click();
    const t0 = Date.now();
    while (Date.now() - t0 < 10000) {
      const st = g("status");
      if (/^ok ·/.test(st.textContent) && st.dataset.state === "ok") return { gates, status: st.textContent };
      if (st.dataset.state === "error") return { gates, status: st.textContent };
      await new Promise((r) => setTimeout(r, 100));
    }
    return { gates, status: "timeout" };
  })()`);
  check("amplifier + mz palette cards add gates (L5 staff)", pal.gates >= 2, JSON.stringify(pal));
  check("/run ok with amplifier + mz circuit", pal.status.includes("ok") && !pal.status.includes("timeout"), pal.status);

  /* 4b. #8: a new run invalidates the stale scan summary */
  const stale = await evalJs(ws, `(() => { const s = document.getElementById("scan-summary"); return { hidden: s.hidden, text: s.textContent }; })()`);
  check("new run clears stale scan summary (#8)", stale.hidden && stale.text === "", JSON.stringify(stale));

  /* 4c. #6: colorbar min/max tick labels render finite numbers (max >= min) */
  const cb = await evalJs(ws, `(() => {
    const g = (id) => document.getElementById(id);
    const hi = Number(g("colorbar-max").textContent);
    const lo = Number(g("colorbar-min").textContent);
    return { max: g("colorbar-max").textContent, min: g("colorbar-min").textContent,
             ok: Number.isFinite(hi) && Number.isFinite(lo) && hi >= lo };
  })()`);
  check("colorbar min/max tick labels rendered (#6)", cb.ok, JSON.stringify(cb));

  /* 5. hit-test every interactive control across viewport widths — no element
        may be covered by another (e.g. the Wigner canvas overlapping toolbar
        buttons when the 3-column grid makes the seq panel too narrow). */
  const HIT = `(() => {
    const els = [...document.querySelectorAll("button, select, input:not(.sr-only), label.btn")];
    const bad = [];
    for (const el of els) {
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      const cx = Math.round(r.left + r.width / 2), cy = Math.round(r.top + r.height / 2);
      if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) continue;
      const hit = document.elementFromPoint(cx, cy);
      if (!(hit === el || el.contains(hit) || (hit && hit.contains(el))))
        bad.push((el.id || el.textContent || "").trim() + "@" + cx + "," + cy + " hit " + (hit ? hit.id || hit.tagName : "null"));
    }
    return bad;
  })()`;
  const hitFailures = [];
  const scrollFailures = [];
  const barFailures = [];
  for (const w of [1920, 1280, 640]) {
    await send(ws, "Emulation.setDeviceMetricsOverride", { width: w, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(300);
    // reset any leftover column scroll; collapse folds to the default view
    await evalJs(ws, `window.scrollTo(0, 0); document.querySelectorAll(".panel").forEach((p) => (p.scrollTop = 0)); document.querySelectorAll(".fold").forEach((f) => (f.open = false))`);
    if (w >= 1280) {
      // user-visible scrollbars must not exist in the default (folded) view
      const bars = await evalJs(ws, `[...document.querySelectorAll(".panel")].filter((p) => p.scrollHeight > p.clientHeight + 1).map((p) => p.className + " sh=" + p.scrollHeight + " ch=" + p.clientHeight)`);
      if (bars.length) barFailures.push(w + "px: " + bars.join(" | "));
    }
    const bad = await evalJs(ws, HIT);
    if (bad.length) hitFailures.push(w + "px: " + bad.join(" | "));
    if (w >= 1280) {
      // Real user behavior: a wheel event must not move the page (scrollTo can
      // programmatically scroll even overflow:hidden containers — wrong proxy).
      await evalJs(ws, `window.scrollTo(0, 0)`);
      await send(ws, "Input.dispatchMouseEvent", { type: "mouseWheel", x: 600, y: 450, deltaX: 0, deltaY: 2000 });
      await sleep(200);
      const sy = await evalJs(ws, `Math.round(window.scrollY)`);
      if (sy !== 0) scrollFailures.push(w + "px: wheel scrolled " + sy + "px (columns must scroll internally)");
    }
  }
  check("no control covered by another element (1920/1280/640 hit-test)", hitFailures.length === 0, hitFailures.join(" ; "));
  check("3-column page fits one viewport, no page scroll (1920/1280)", scrollFailures.length === 0, scrollFailures.join(" ; "));
  check("no column scrollbar in folded default view (1920/1280)", barFailures.length === 0, barFailures.join(" ; "));

  /* 5b. #14: palette groups are <details> — collapse/expand works in the
      single-column layout too (loop above ends at 640px < 80rem) */
  const fold = await evalJs(ws, `(async () => {
    const g = document.querySelector(".palette__group");
    if (!g) return { ok: false, reason: "no group" };
    const sum = g.querySelector("summary");
    const grid = g.querySelector(".palette__grid");
    const items = g.querySelectorAll(".palette__item").length;
    const disp = () => getComputedStyle(grid).display;
    const open0 = g.open, d0 = disp();
    sum.click(); await new Promise((r) => setTimeout(r, 60));
    const open1 = g.open, d1 = disp();
    sum.click(); await new Promise((r) => setTimeout(r, 60));
    return { ok: open0 && d0 === "grid" && !open1 && d1 === "none" && g.open, d0, d1, items, w: innerWidth };
  })()`);
  check("palette group details collapse/expand at 640px (#14)", fold.ok, JSON.stringify(fold));

  console.log(failures.length ? `\n${failures.length} probe(s) FAILED` : "\nall probes PASS");
} catch (e) {
  failures.push(e.message);
  console.error("PROBE ERROR:", e.message);
} finally {
  if (ws) { try { ws.close(); } catch { /* ignore */ } }
  server.kill("SIGTERM");
  edge.kill("SIGTERM");
  await sleep(300);
}
process.exit(failures.length ? 1 : 0);
