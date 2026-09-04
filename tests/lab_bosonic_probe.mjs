/* Bosonic Lab B6 — headless CDP probe (B6 exit 1: GKP QEC GUI flow).
   Zero-dep: Node >= 22 native fetch + WebSocket; Edge headless as the browser.

   Usage: node tests/lab_bosonic_probe.mjs
   Spawns uvicorn (lab server) + headless Edge, injects the GKP QEC
   circuit via the JSON editor (backend=bosonic, initial=[gkp0,gkp1]).
   Verifies: bosonic backend accepted, initial card (selects), run → Wigner +
   meters + steps slider, Sweep loss → fidelity curve svg, slider drives step tag.
   Exit code 0 = all probes PASS, 1 = any FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const PORT = 8860;
const CDP_PORT = 9224;
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
    }, 30000);
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
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + process.cwd() + "/.probe-bosonic-profile",
  "about:blank",
], { stdio: "ignore" });

const QEC_JSON = {
  schema: "circuit_v1", nmode: 2, backend: "bosonic", seed: 0,
  initial: ["gkp0", "gkp1"],
  ops: [
    { id: "cz0", op: "cz", modes: [0, 1], params: { weight: 1.0 } },
    { id: "l0", op: "loss", modes: [0], params: { T: 0.9, nbar: 0 } },
    { id: "h0", op: "measure_homodyne", modes: [1], params: { phi: Math.PI / 2, name: "m_p" } },
    { id: "d0", op: "displace", modes: [0], params: { alpha: { $ref: "m_p", gain: 1 } } },
  ],
  view: { wigner_mode: 0, lim: 5, n: 64 },
  ui: {},
};

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

  await evalJs(ws, `(async () => { while (!document.getElementById("json-input")) await new Promise((r) => setTimeout(r, 50)); return true; })()`);
  // 票3: init() now awaits /schema before first render — wait for the
  // palette (post-schema) instead of the first staff row, else the inject
  // below races an empty OPS merge and the scene silently no-ops.
  await evalJs(ws, `(async () => { while (!document.querySelector(".palette__item")) await new Promise((r) => setTimeout(r, 50)); return true; })()`);


  /* inject the GKP QEC scene through the JSON editor (v1 path) */
  await evalJs(ws, `(() => {
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, ${JSON.stringify(JSON.stringify(QEC_JSON))});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);

  /* wait for rebuild + this bosonic auto-run to land. Status alone can be
     stale from the default scene, so require the expected steps snapshot. */
  await evalJs(ws, `(async () => {
    for (let k = 0; k < 400; k++) {
      const st = document.getElementById("status").textContent;
      const panel = document.getElementById("bosonic-panel");
      const step = document.getElementById("bos-step");
      if (!panel.hidden && !step.disabled && Number(step.max) === 2 && st.includes("ok")) return true;
      if (st.startsWith("422") || st.startsWith("5") || st.startsWith("网络")) return true;
      await new Promise((r) => setTimeout(r, 150));
    }
    return "timeout";
  })()`);

  check("bosonic backend label active",
    await evalJs(ws, `document.getElementById("backend-select").value === "bosonic"`));
  check("initial card visible with GKP selects",
    await evalJs(ws, `!document.getElementById("initial-card").hidden
      && document.querySelectorAll("#initial-inputs select").length === 2`));
  check("initial values gkp0/gkp1",
    await evalJs(ws, `(() => { const s = [...document.querySelectorAll("#initial-inputs select")];
      return s[0].value === "gkp0" && s[1].value === "gkp1"; })()`));
  check("bosonic panel visible",
    await evalJs(ws, `!document.getElementById("bosonic-panel").hidden`));
  check("run status ok",
    await evalJs(ws, `document.getElementById("status").textContent.includes("ok")`));
  const wigner = await evalJs(ws, `document.getElementById("wigner-canvas").toDataURL().length`);
  check("Wigner canvas rendered", wigner > 1500, `bytes=${wigner}`);

  check("steps slider enabled with 3 steps",
    await evalJs(ws, `(() => { const s = document.getElementById("bos-step");
      return !s.disabled && Number(s.max) === 2; })()`));
  check("step tag shows snapshot",
    await evalJs(ws, `document.getElementById("bos-step-tag").textContent.startsWith("step")`));

  /* sweep loss — button present + click yields curve in the svg */
  await evalJs(ws, `document.getElementById("bos-fidelity-btn").click()`);
  await evalJs(ws, `(async () => {
    for (let k = 0; k < 160; k++) {
      const n = document.getElementById("bos-fidelity-note");
      if (!n.hidden && n.textContent.includes("fidelity")) break;
      await new Promise((r) => setTimeout(r, 150));
    }
    return true;
  })()`);
  const fidSvg = await evalJs(ws, `document.querySelector("#bos-fidelity-svg polyline, #bos-fidelity-svg path") ? true : false`);
  check("fidelity curve drawn after Sweep loss", fidSvg);
  const fidNote = await evalJs(ws, `document.getElementById("bos-fidelity-note").textContent`);
  check("fidelity note non-empty", typeof fidNote === "string" && fidNote.length > 0, fidNote.slice(0, 60));

  /* slider drive: step to 0 → tag changes to step 0 */
  await evalJs(ws, `(() => { const s = document.getElementById("bos-step");
    s.value = "0"; s.dispatchEvent(new Event("input")); return true; })()`);
  check("slider to step 0 updates tag",
    await evalJs(ws, `document.getElementById("bos-step-tag").textContent.startsWith("step 0")`));

  check("scan panel hidden for bosonic",
    await evalJs(ws, `document.getElementById("scan-panel").hidden`));
  check("state grid hidden for bosonic",
    await evalJs(ws, `document.getElementById("state-grid").hidden`));
} catch (e) {
  check("probe run without exception", false, String(e));
} finally {
  try { server.kill(); } catch { /* already dead */ }
  try { edge.kill(); } catch { /* already dead */ }
}

console.log(failures.length ? `\n${failures.length} FAILURES: ${failures.join(", ")}` : "\nall bosonic probes PASS");
process.exit(failures.length ? 1 : 0);
