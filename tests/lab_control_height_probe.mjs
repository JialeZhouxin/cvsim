/* Control-height probe — Dark Scope 仪器槽位一致性护栏。
   Zero-dep: Node >= 22 native fetch + WebSocket; Edge headless as the browser.
   Usage: node tests/lab_control_height_probe.mjs
   断言：页面上所有可见 .btn / .select / .input 计算高度一致（--control-h）。
   Exit code 0 = PASS, 1 = FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { writeFileSync } from "node:fs";

const PORT = 8860;
const CDP_PORT = 9224;
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const CWD = process.cwd();

const server = spawn(CWD + "/.venv/Scripts/uvicorn.exe",
  ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"],
  { cwd: CWD, stdio: "ignore" });
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + CWD + "/.probe-height-profile",
  "about:blank",
], { stdio: "ignore" });

async function waitHttp(url, timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try { const r = await fetch(url); if (r.ok) return r; } catch {}
    await sleep(300);
  }
  throw new Error(`timeout waiting for ${url}`);
}

async function waitJson(url, timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try { return await (await fetch(url)).json(); } catch {}
    await sleep(300);
  }
  throw new Error(`timeout waiting for ${url}`);
}

let msgId = 0; const pending = new Map();
function send(ws, method, params = {}) {
  const id = ++msgId;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    setTimeout(() => { if (pending.delete(id)) reject(new Error(`timeout: ${method}`)); }, 30000);
  });
}
function evalJs(ws, expression) {
  return send(ws, "Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })
    .then(m => {
      if (m.result?.exceptionDetails) throw new Error("page exception: " + JSON.stringify(m.result.exceptionDetails.exception?.description || m.result.exceptionDetails));
      return m.result?.result?.value;
    });
}

let exitCode = 1;
try {
  await waitHttp(`http://127.0.0.1:${PORT}/`);
  const tabs = await waitJson(`http://127.0.0.1:${CDP_PORT}/json`);
  const t = tabs.find(x => x.type === "page");
  if (!t) throw new Error("no page tab");
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id).resolve(m); pending.delete(m.id); } };

  await send(ws, "Page.enable");
  await send(ws, "Page.navigate", { url: `http://127.0.0.1:${PORT}/` });
  await sleep(2000);
  await send(ws, "Emulation.setDeviceMetricsOverride", { width: 1440, height: 960, deviceScaleFactor: 2, mobile: false });
  await sleep(500);

  const r = await evalJs(ws, `
    (() => {
      const els = [...document.querySelectorAll('.btn, .select, .input')]
        .filter(el => el.getClientRects().length > 0);
      const heights = els.map(el => getComputedStyle(el).height);
      const unique = [...new Set(heights)];
      return { count: els.length, unique, sample: heights[0] };
    })()
  `);

  const okCount = r.count >= 5;
  const okHeights = r.unique.length === 1;
  console.log(`${okCount ? "PASS" : "FAIL"}  visible control count = ${r.count} (need >= 5)`);
  console.log(`${okHeights ? "PASS" : "FAIL"}  uniform control height — values: ${JSON.stringify(r.unique)} (sample ${r.sample})`);

  const shot = await send(ws, "Page.captureScreenshot", { format: "png" });
  writeFileSync(CWD + "/.control-height.png", Buffer.from(shot.result.data, "base64"));
  console.log("screenshot .control-height.png");

  exitCode = okCount && okHeights ? 0 : 1;
} catch (e) {
  console.error("ERR", e.message);
} finally {
  server.kill(); edge.kill();
  process.exit(exitCode);
}
