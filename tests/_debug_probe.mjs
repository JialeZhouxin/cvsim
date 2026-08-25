/* debug: Fock backend smoke (backend switch, palette, HOM run, batch) */
"use strict";
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const PORT = 8765, CDP_PORT = 9224;
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const server = spawn(".venv/Scripts/uvicorn.exe", ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"], { stdio: "ignore" });
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  `--remote-debugging-port=${CDP_PORT}`, "--user-data-dir=" + process.env.TEMP + "/edge-debug-probe",
  "--window-size=1920,1200", `http://127.0.0.1:${PORT}/`,
], { stdio: "ignore" });

async function waitHttp(url, t = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < t) {
    try { const r = await fetch(url); if (r.ok) return r; } catch {}
    await sleep(200);
  }
  throw new Error("timeout " + url);
}

await waitHttp(`http://127.0.0.1:${PORT}/health`);
await waitHttp(`http://127.0.0.1:${CDP_PORT}/json/version`);
const target = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(`http://127.0.0.1:${PORT}/`)}`, { method: "PUT" }).then((r) => r.json());
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let id = 0; const pending = new Map();
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") {
    console.log("EXC:", m.params.exceptionDetails.exception?.description?.slice(0, 300));
  }
};
const send = (method, params) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const evalJs = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) return { __exc: r.result.exceptionDetails.exception?.description?.slice(0, 200) };
  return r.result?.result?.value;
};

await send("Runtime.enable");
await send("Page.enable");
await sleep(4000);

const r1 = await evalJs(`(async () => {
  const g = (id) => document.getElementById(id);
  g("backend-select").value = "fock";
  g("backend-select").dispatchEvent(new Event("change", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 800));
  const jv = g("json-input").value;
  const jd = JSON.parse(jv);
  const rr = await fetch("/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: jv });
  const rj = await rr.json();
  return {
    palette: [...document.querySelectorAll(".palette__item")].map((x) => x.dataset.op),
    addModeVisible: !g("add-mode-btn").hidden,
    initialVisible: !g("initial-card").hidden,
    fockPanelVisible: !g("fock-panel").hidden,
    scanHidden: g("scan-panel").hidden,
    metersHidden: g("meters-panel").hidden,
    jsonBackend: jd.backend, jsonTail: jv.slice(-180),
    runBackend: rj.backend, runHasDist: !!rj.dist, runHasJoint: !!rj.joint,
  };
})()`);
console.log("switch →", JSON.stringify(r1, null, 1));

// A1 HOM: nmode=2, initial=[1,1], BS π/4
const r2 = await evalJs(`(async () => {
  const g = (id) => document.getElementById(id);
  const input = g("json-input");
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
  const payload = {
    schema: "circuit_v1", nmode: 2, seed: 0, backend: "fock",
    initial: [1, 1],
    ops: [{ id: "bs", op: "beamsplitter", modes: [0, 1], params: { theta: Math.PI / 4, phi: 0 } }],
    view: { wigner_mode: 0, lim: 5.0, n: 64, joint_modes: [0, 1] }, ui: {},
  };
  setter.call(input, JSON.stringify(payload));
  input.dispatchEvent(new Event("input", { bubbles: true }));
  const t0 = Date.now();
  while (Date.now() - t0 < 10000 && g("fock-dist-mode").textContent === "—") await new Promise((r) => setTimeout(r, 100));
  const distMode = g("fock-dist-mode").textContent;
  const leak = g("fock-leak").textContent;
  const slowHidden = g("fock-slow-note").hidden;
  const jointRects = document.querySelectorAll("#fock-joint-svg rect").length;
  const status = g("status").textContent;
  return { status, distMode, leak, slowHidden, jointRects,
    jointModes: [g("joint-m0").value, g("joint-m1").value],
    cutoffs: g("cutoff-val").textContent };
})()`);
console.log("HOM run →", JSON.stringify(r2, null, 1));

// joint grid P(1,1) check via /run payload directly
const r3 = await evalJs(`(async () => {
  const payload = {
    schema: "circuit_v1", nmode: 2, seed: 0, backend: "fock", initial: [1, 1],
    ops: [{ op: "beamsplitter", modes: [0, 1], params: { theta: Math.PI / 4, phi: 0 } }],
    view: { wigner_mode: 0, lim: 5.0, n: 64, joint_modes: [0, 1] },
  };
  const r = await fetch("/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  const j = await r.json();
  return { status: r.status, p11: j.joint?.grid[1]?.[1], p20: j.joint?.grid[2]?.[0],
    dist: j.dist?.probs?.slice(0, 4), leakage: j.meters?.leakage };
})()`);
console.log("P(1,1) →", JSON.stringify(r3));

// batch
const r4 = await evalJs(`(async () => {
  const g = (id) => document.getElementById(id);
  g("batch-btn").click();
  const t0 = Date.now();
  while (Date.now() - t0 < 15000 && !/^batch/.test(g("status").textContent)) await new Promise((r) => setTimeout(r, 100));
  const batchRects = document.querySelectorAll("#fock-batch-svg rect").length;
  const batchSeed = g("batch-seed").textContent;
  return { status: g("status").textContent, batchRects, batchSeed };
})()`);
console.log("batch →", JSON.stringify(r4));

// cutoff slider 25 → slow note + JSON cutoff field
const r5 = await evalJs(`(async () => {
  const g = (id) => document.getElementById(id);
  const slider = g("cutoff-slider");
  slider.value = "25";
  slider.dispatchEvent(new Event("input", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 900));
  const json = JSON.parse(g("json-input").value);
  return { cutoff: json.cutoff, slowVisible: !g("fock-slow-note").hidden, leak: g("fock-leak").textContent };
})()`);
console.log("cutoff 25 →", JSON.stringify(r5));

// measure once with measure_pnr
const r6 = await evalJs(`(async () => {
  const g = (id) => document.getElementById(id);
  const input = g("json-input");
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
  const payload = {
    schema: "circuit_v1", nmode: 2, seed: 7, backend: "fock", initial: [1, 1],
    ops: [
      { id: "bs", op: "beamsplitter", modes: [0, 1], params: { theta: Math.PI / 4, phi: 0 } },
      { id: "mp", op: "measure_pnr", modes: [0], params: { name: "mp" } },
    ],
    view: { wigner_mode: 1, lim: 5.0, n: 64 }, ui: {},
  };
  setter.call(input, JSON.stringify(payload));
  input.dispatchEvent(new Event("input", { bubbles: true }));
  const t0 = Date.now();
  while (Date.now() - t0 < 10000 && !/^ok/.test(g("status").textContent)) await new Promise((r) => setTimeout(r, 100));
  const outcomes = [...document.querySelectorAll("#m-outcomes li")].map((li) => li.textContent);
  return { outcomes, status: g("status").textContent, jointHidden: g("joint-note").hidden };
})()`);
console.log("measure_pnr →", JSON.stringify(r6));

process.exit(0);
