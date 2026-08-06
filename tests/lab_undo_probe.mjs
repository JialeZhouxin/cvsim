/* Gaussian Lab — headless CDP probe: undo/redo (撤销/重做).
   Zero-dep: Node >= 22 native fetch + WebSocket; Edge headless.

   Usage: node tests/lab_undo_probe.mjs
   Exit code 0 = all probes PASS, 1 = any FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const PORT = 8767;
const CDP_PORT = 9225;
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

async function click(ws, sel) {
  return evalJs(ws, `(() => {
    const el = document.querySelector(${JSON.stringify(sel)});
    if (!el) return false;
    el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    return true;
  })()`);
}

async function key(ws, key, { ctrl = false, shift = false } = {}) {
  return evalJs(ws, `(() => {
    const ev = new KeyboardEvent("keydown", { key: ${JSON.stringify(key)}, ctrlKey: ${ctrl}, shiftKey: ${shift}, bubbles: true, cancelable: true });
    document.body.dispatchEvent(ev);
    return !ev.defaultPrevented;
  })()`);
}

const gateCount = `document.querySelectorAll("#staff .gate:not(.gate--preview):not(.gate--ghost)").length`;
const undoDisabled = `document.getElementById("undo-btn").disabled`;
const redoDisabled = `document.getElementById("redo-btn").disabled`;
const jsonHas = (n) => `document.getElementById("json-input").value.includes(${JSON.stringify(n)})`;

const server = spawn(process.cwd() + "/.venv/Scripts/uvicorn.exe", ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"], {
  cwd: process.cwd(), stdio: "ignore",
});
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + process.cwd() + "/.probe-edge-profile-undo",
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
  await evalJs(ws, `(async () => { while (!document.querySelectorAll("#palette [data-op]").length) await new Promise((r) => setTimeout(r, 50)); return true; })()`);

  /* default scene: vacuum×2 + displace×2 → 2 gates; history empty.
     First Runtime.evaluate after connect may need a warm-up round (headless
     cold start) — evaluate once before asserting. */
  await evalJs(ws, `(() => ({ gates: ${gateCount} }))()`);
  check("初始: 2 gates, undo 禁用", await waitEval(ws, `(() => ${gateCount} === 2 && ${undoDisabled})()`), await evalJs(ws, `"gates=" + ${gateCount}`));

  /* 1. palette click adds a gate → 3 gates, undo enabled */
  await click(ws, `#palette [data-op="displace"]`);
  check("托盘点击添加后: 3 gates, undo 可用", await waitEval(ws, `(() => ${gateCount} === 3 && !${undoDisabled})()`));

  /* 2. undo button → back to 2, redo enabled */
  await click(ws, `#undo-btn`);
  check("撤销按钮: 2 gates, redo 可用", await waitEval(ws, `(() => ${gateCount} === 2 && !${redoDisabled})()`));

  /* 3. redo button → 3 again */
  await click(ws, `#redo-btn`);
  check("重做按钮: 3 gates", await waitEval(ws, `(() => ${gateCount} === 3)()`));

  /* 4. keyboard Ctrl+Z / Ctrl+Shift+Z */
  await key(ws, "z", { ctrl: true });
  check("Ctrl+Z: 2 gates", await waitEval(ws, `(() => ${gateCount} === 2)()`));
  await key(ws, "z", { ctrl: true, shift: true });
  check("Ctrl+Shift+Z: 3 gates", await waitEval(ws, `(() => ${gateCount} === 3)()`));

  /* 5. delete + undo restores the node */
  await click(ws, `#staff .gate__del`);
  check("删除后: 2 gates", await waitEval(ws, `(() => ${gateCount} === 2)()`));
  await key(ws, "z", { ctrl: true });
  check("删除后 Ctrl+Z: 3 gates", await waitEval(ws, `(() => ${gateCount} === 3)()`));

  /* 6. undo to the very bottom: undo disabled (redo still holds 2 steps) */
  await key(ws, "z", { ctrl: true });
  await key(ws, "z", { ctrl: true });
  check("撤到空栈: 2 gates, undo 禁用, redo 仍可用", await waitEval(ws, `(() => ${gateCount} === 2 && ${undoDisabled} && !${redoDisabled})()`));

  /* 6b. redo to the top: restores the last-undone state (2 gates, the
     post-delete state), then redo disables */
  await key(ws, "z", { ctrl: true, shift: true });
  await key(ws, "z", { ctrl: true, shift: true });
  check("重做到顶: 2 gates, undo 可用, redo 禁用", await waitEval(ws, `(() => ${gateCount} === 2 && !${undoDisabled} && ${redoDisabled})()`));

  /* 7. JSON direct edit clears history (undo disabled) */
  await evalJs(ws, `(() => {
    const t = document.getElementById("json-input");
    const v = JSON.parse(t.value);
    v.nodes.push({ id: "xf", op: "fourier", params: {}, mode: 0, ui: { x: 5 } });
    t.value = JSON.stringify(v, null, 2);
    t.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  await sleep(1200);
  console.log("JSON-after:", await evalJs(ws, `(() => ({ hasXf: ${jsonHas("xf")}, ud: ${undoDisabled}, jsonLen: document.getElementById("json-input").value.length }))()`));
  check("JSON 编辑后: fourier 入图, undo 清空禁用", await waitEval(ws, `(() => ${jsonHas("xf")} && ${undoDisabled})()`));

  console.log(failures.length ? `\n${failures.length}/${checks.length} FAIL` : `\n${checks.length}/${checks.length} probes PASS`);
  process.exitCode = failures.length ? 1 : 0;
} finally {
  ws?.close();
  edge.kill();
  server.kill();
}
