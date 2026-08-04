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

const server = spawn("uv", ["run", "uvicorn", "cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"], {
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

  /* 1. panel renders with adaptive defaults for the default TMSV scene */
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
    const rows = [...document.querySelectorAll(".node-row__title")].map((t) => t.textContent);
    g("run-btn").click();
    const t0 = Date.now();
    while (Date.now() - t0 < 10000) {
      const st = g("status");
      if (/^ok ·/.test(st.textContent) && st.dataset.state === "ok") return { rows, status: st.textContent };
      if (st.dataset.state === "error") return { rows, status: st.textContent };
      await new Promise((r) => setTimeout(r, 100));
    }
    return { rows, status: "timeout" };
  })()`);
  check("amplifier + mz palette cards add nodes", pal.rows.some((t) => t.includes("放大")) && pal.rows.some((t) => t.includes("马赫-曾德尔")), JSON.stringify(pal.rows));
  check("/run ok with amplifier + mz circuit", pal.status.includes("ok") && !pal.status.includes("timeout"), pal.status);

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
