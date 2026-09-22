/* §3.4 probe — does the fock 初始态 number input actually clamp to cutoff-1?

   The defect: `editor.js` `setInitial` wrote `next[i] = v` with no cutoff
   ceiling, while (a) `modeLabel` renders the value as `|v⟩` and (b) the server
   hard-rejects out-of-range initial (`cvsim/fock/ir.py`: "initial[i]=n must be
   in [0, c)"). Browsers do NOT clamp a typed value to `input.max`, so
   `cutoff=2` + typing `9` produced state `initial=[9]`, an on-screen `|9⟩`,
   and a 422 from /run. `clampInitial` existed but only in `fock.js`, reachable
   only from the cutoff *slider*, never from the initial *input box*.

   This probe drives the real page: inject a fock circuit with cutoff=2, type 9
   into the mode-0 initial input, and then assert
     - the state JSON written to the editor textarea carries initial 1 (not 9),
     - the mode label reads |1⟩ and never |9⟩,
     - /run produced no 422 for this circuit.

   Run: node tests/lab_initial_clamp_probe.mjs
   Exit 0 = PASS, 1 = FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { EDGE, port, userDataDir, uvicornPath } from "./probe_env.mjs";

const PORT = port(8771, "PROBE_PORT");
const CDP_PORT = port(9229, "PROBE_CDP_PORT");
const failures = [];

function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
  if (!ok) failures.push(name);
}

async function waitHttp(url, timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try { const r = await fetch(url); if (r.ok) return r; } catch { /* not up */ }
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
    setTimeout(() => { if (pending.delete(id)) reject(new Error(`CDP timeout: ${method}`)); }, 60000);
  });
}
function evalJs(ws, expression) {
  return send(ws, "Runtime.evaluate", {
    expression, returnByValue: true, awaitPromise: true,
  }).then((m) => {
    if (m.result && m.result.exceptionDetails) {
      throw new Error("page exception: "
        + JSON.stringify(m.result.exceptionDetails.exception?.description || m.result.exceptionDetails));
    }
    return m.result && m.result.result ? m.result.result.value : undefined;
  });
}
async function waitFor(ws, expression, timeoutMs = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if (await evalJs(ws, expression)) return true;
    await sleep(100);
  }
  return false;
}
async function inject(ws, payload) {
  await evalJs(ws, `(() => {
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, ${JSON.stringify(JSON.stringify(payload))});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
}

/* cutoff=2 so the legal fock range is only [0, 1]; initial 0 keeps the circuit
   itself valid, so any 422 afterwards is attributable to the typed value. */
const FOCK_CUT2 = {
  schema: "circuit_v1", seed: 0, nmode: 1, backend: "fock",
  initial: [0], cutoff: 2,
  ops: [{ id: "s0", op: "squeeze", params: { r: 0.4, phi: 0 }, modes: [0] }],
  view: { wigner_mode: 0, lim: 5.0, n: 64 },
  ui: { staff: { s0: 0 } },
};

const server = spawn(uvicornPath(),
  ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"],
  { cwd: process.cwd(), stdio: "ignore" });
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--no-sandbox", "--disable-dev-shm-usage", "--remote-allow-origins=*",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + userDataDir(".probe-edge-initialclamp-profile"),
  "about:blank",
], { stdio: "ignore" });

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

  const booted = await waitFor(ws, `!!document.querySelector(".palette__item")`, 30000);
  if (!booted) throw new Error("page never booted (no palette items — is /schema up?)");

  /* Record every /run status so a 422 is provable rather than inferred.
     Installed AFTER the reload — a hook set before it would be discarded. */
  await evalJs(ws, `(() => {
    window.__runs = [];
    const of = window.fetch;
    window.fetch = function (u, o) {
      const url = typeof u === "string" ? u : (u && u.url) || "";
      const p = of.apply(this, arguments);
      if (url.includes("/run")) {
        p.then((r) => window.__runs.push({ url, status: r.status })).catch(() => {});
      }
      return p;
    };
    return true;
  })()`);

  await inject(ws, FOCK_CUT2);
  const ready = await waitFor(ws, `(() => {
    const n = document.querySelectorAll("#initial-inputs input[type=number]").length;
    return n === 1 && !!document.querySelector("#cutoff-slider");
  })()`, 20000);
  if (!ready) throw new Error("fock cutoff=2 scene never rendered an initial number input");

  // confirm the premise: the input advertises max=1 but the browser won't enforce it
  const before = await evalJs(ws, `(() => {
    const inp = document.querySelector("#initial-inputs input[type=number]");
    return { max: inp.max, value: inp.value };
  })()`);
  check("premise: initial input advertises max=cutoff-1=1", String(before.max) === "1",
    `max=${JSON.stringify(before.max)} value=${JSON.stringify(before.value)}`);

  /* The actual bug: type 9 (a "valid non-negative integer", so the old handler
     accepted it) and read back both the serialized state and the mode label. */
  const after = await evalJs(ws, `(async () => {
    const inp = document.querySelector("#initial-inputs input[type=number]");
    inp.value = "9";
    inp.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 900));   // let the debounced /run land
    let doc = null, parseErr = null;
    try { doc = JSON.parse(document.getElementById("json-input").value); }
    catch (e) { parseErr = String(e); }
    const labels = [...document.querySelectorAll(".staff__mode-label")].map((e) => e.textContent);
    const inp2 = document.querySelector("#initial-inputs input[type=number]");
    return {
      initial: doc ? doc.initial : null,
      cutoff: doc ? doc.cutoff : null,
      parseErr,
      labels,
      inputValue: inp2 ? inp2.value : null,
      runs: window.__runs,
      status: document.getElementById("status").textContent,
      statusState: document.getElementById("status").dataset.state,
    };
  })()`);

  check("state JSON carries initial 1 (clamped to cutoff-1), never 9",
    Array.isArray(after.initial) && after.initial[0] === 1,
    `json.initial=${JSON.stringify(after.initial)} cutoff=${JSON.stringify(after.cutoff)}`
    + (after.parseErr ? ` PARSE-ERROR=${after.parseErr}` : ""));

  const sawBad = after.labels.some((t) => t.includes("|9"));
  check("mode label shows |1⟩ and never |9⟩",
    after.labels.some((t) => t.includes("|1")) && !sawBad,
    `labels=${JSON.stringify(after.labels)}${sawBad ? " [|9⟩ RENDERED]" : ""}`);

  check("input box snaps back to the clamped value",
    after.inputValue === "1",
    `input.value=${JSON.stringify(after.inputValue)}`);

  const runs = Array.isArray(after.runs) ? after.runs : [];
  const bad = runs.filter((r) => r.status >= 400);
  check("no /run request was rejected (no 422 from out-of-range initial)",
    runs.length > 0 && bad.length === 0,
    `runs=${JSON.stringify(runs)} status=${JSON.stringify(after.status)}`
    + ` state=${JSON.stringify(after.statusState)}`);

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
