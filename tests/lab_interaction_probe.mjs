/* Lab interaction-path probe — guards that slider / setView interactions stop
   rebuilding the whole workbench (C1 09-17-lab-interaction-path-rerender).

   What it locks, and why each form was chosen:

     1. a gate-param slider performs ZERO `getBoundingClientRect` /
        `getComputedStyle` / `matchMedia` calls. Measured by patching those three
        globals for the duration of the dispatch only (patch -> dispatch -> read ->
        restore, all inside one evaluate), so the probe's own geometry reads are
        never counted.
     2. a gate-param slider leaves the scan `<select>` options in place. `__mark`
        identity, not a length check: `refreshScanNodes` calls
        `replaceChildren()`, so a surviving marker proves the options were never
        rebuilt.
     3. a real node-set change still rebuilds those options — the dirty key must
        not be so coarse that the scan panel stops tracking the graph.
     4. `setView` (Wigner mode) leaves staff + palette in place.
     5. the fock `cutoff` slider leaves staff + palette in place.
     6. the fock `cutoff` slider still writes state AND resyncs the mode label.

   Identity is the right instrument for 2/4/5: `staff.render()` and
   `renderPalette()` both start with `replaceChildren()`, which destroys the
   marked nodes. A marker that survives proves the subtree was never rebuilt —
   a call count could be gamed by calling the function and bailing early, but a
   surviving DOM node cannot.

   Caveat (honest boundary): the counters patch the SYNCHRONOUS handler path.
   Work deferred to rAF or to a ResizeObserver callback after the dispatch is not
   counted. That is deliberate — heatmap redraw deferral belongs to C2
   (09-17-lab-heatmap-redraw-cache) and is measured by C0's CDP Performance probe.

   Run: node tests/lab_interaction_probe.mjs
   Exit code 0 = all probes PASS, 1 = any FAIL. */

"use strict";

import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { EDGE, port, userDataDir, uvicornPath } from "./probe_env.mjs";

const PORT = port(8770, "PROBE_PORT");
const CDP_PORT = port(9228, "PROBE_CDP_PORT");
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
    }, 60000);
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

async function waitFor(ws, expression, timeoutMs = 15000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if (await evalJs(ws, expression)) return true;
    await sleep(100);
  }
  return false;
}

/* Inject a circuit through the real JSON textarea path (same technique as
   lab_wigner_layout_probe.mjs): the native value setter, then an `input` event,
   so the editor's own 400ms-debounced parse runs. */
async function inject(ws, payload) {
  await evalJs(ws, `(() => {
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, ${JSON.stringify(JSON.stringify(payload))});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
}

/* Gaussian scene with one squeeze gate: `squeeze.r` carries `sweep: [0, 2]`, so
   it is the node the scan panel lists and the gate whose card has a slider. */
const GAUSS_SWEEP = {
  schema: "circuit_v1", seed: 0, nmode: 2,
  ops: [{ id: "s0", op: "squeeze", params: { r: 0.4, phi: 0 }, modes: [0] }],
  view: { wigner_mode: 0, lim: 5.0, n: 64 },
  ui: { staff: { s0: 0 } },
};

/* Fock scene with NON-ZERO per-mode initial photon numbers. This is what makes
   check 6 meaningful: `clampInitial` squeezes `initial` to `cutoff - 1`, and
   `modeLabel` renders that value, so dragging cutoff 10 -> 3 with initial 5 must
   turn "mode 0 · |5⟩" into "mode 0 · |2⟩". A lightened `setCircuit` that skipped
   the staff update entirely would leave the stale |5⟩ label on screen. */
const FOCK_CLAMP = {
  schema: "circuit_v1", seed: 0, nmode: 2, backend: "fock",
  initial: [5, 3], cutoff: 10,
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
  "--user-data-dir=" + userDataDir(".probe-edge-interaction-profile"),
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
  await send(ws, "Emulation.setDeviceMetricsOverride",
    { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

  const booted = await waitFor(ws, `!!document.querySelector(".palette__item")`, 30000);
  if (!booted) throw new Error("page never booted (no palette items — is /schema up?)");

  /* ── scenario 1/2/3: gate-param slider ─────────────────────────────── */
  await inject(ws, GAUSS_SWEEP);
  const haveGate = await waitFor(ws,
    `!!document.querySelector(".staff__gates .gate[data-id]")`);
  if (!haveGate) throw new Error("gaussian sweep scene never produced a staff gate");
  await waitFor(ws, `document.querySelectorAll("#scan-node option").length > 0`);

  /* open the gate's param card so a slider exists */
  await evalJs(ws, `(() => {
    const g = document.querySelector(".staff__gates .gate[data-id]");
    g.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    return true;
  })()`);
  const cardOpen = await waitFor(ws, `!!document.querySelector(".gate-card__params input[type=range]")`);
  if (!cardOpen) throw new Error("param card never opened (no range slider found)");

  const drag = await evalJs(ws, `(() => {
    const c = { rect: 0, cs: 0, mm: 0 };
    const oRect = Element.prototype.getBoundingClientRect;
    const oCS = window.getComputedStyle;
    const oMM = window.matchMedia;
    Element.prototype.getBoundingClientRect = function (...a) { c.rect++; return oRect.apply(this, a); };
    window.getComputedStyle = function (...a) { c.cs++; return oCS.apply(this, a); };
    window.matchMedia = function (...a) { c.mm++; return oMM.apply(this, a); };
    const optBefore = document.querySelector("#scan-node option");
    if (optBefore) optBefore.__mark = "scan";
    const paramBefore = document.querySelector("#scan-param option");
    if (paramBefore) paramBefore.__mark = "param";
    try {
      const range = document.querySelector(".gate-card__params input[type=range]");
      for (let i = 0; i < 4; i++) {
        range.value = String(0.5 + i * 0.05);
        range.dispatchEvent(new Event("input", { bubbles: true }));
      }
    } finally {
      Element.prototype.getBoundingClientRect = oRect;
      window.getComputedStyle = oCS;
      window.matchMedia = oMM;
    }
    const optAfter = document.querySelector("#scan-node option");
    const paramAfter = document.querySelector("#scan-param option");
    return {
      c,
      scanSurvived: !!optAfter && optAfter.__mark === "scan",
      paramSurvived: !!paramAfter && paramAfter.__mark === "param",
      scanOptionCount: document.querySelectorAll("#scan-node option").length,
      cardStillOpen: !!document.querySelector(".gate-card__params input[type=range]"),
    };
  })()`);

  check("param slider performs zero layout reads (getBoundingClientRect/getComputedStyle/matchMedia)",
    drag.c.rect === 0 && drag.c.cs === 0 && drag.c.mm === 0,
    `rect=${drag.c.rect} computedStyle=${drag.c.cs} matchMedia=${drag.c.mm}`);

  check("param slider leaves the scan <select> options in place (dirty key hit)",
    drag.scanSurvived && drag.paramSurvived,
    `scanNode=${drag.scanSurvived ? "kept" : "REBUILT"} scanParam=${drag.paramSurvived ? "kept" : "REBUILT"} (${drag.scanOptionCount} options)`);

  /* the param card must survive the drag too — rebuilding it would interrupt the
     drag itself (this is the documented reason onParam never re-rendered DOM) */
  check("param card stays open across the drag",
    drag.cardStillOpen,
    drag.cardStillOpen ? "card kept" : "card was closed/rebuilt");

  /* ── scenario 3b: a real node-set change must still refresh the options ── */
  const structural = await evalJs(ws, `(() => {
    const before = document.querySelector("#scan-node option");
    if (before) before.__mark = "structural";
    const card = document.querySelector('.palette__item[data-op="squeeze"]');
    if (!card) return { error: "no squeeze palette card" };
    card.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    return { clicked: true };
  })()`);
  let structuralOk = false;
  let structuralDetail = structural.error || "";
  if (!structural.error) {
    await waitFor(ws, `document.querySelectorAll(".staff__gates .gate[data-id]").length > 1`);
    const after = await evalJs(ws, `(() => {
      const o = document.querySelector("#scan-node option");
      return { survived: !!o && o.__mark === "structural",
               count: document.querySelectorAll("#scan-node option").length };
    })()`);
    structuralOk = !after.survived && after.count > 1;
    structuralDetail = `options=${after.count} ${after.survived ? "NOT rebuilt" : "rebuilt"}`;
  }
  check("a real node-set change still rebuilds the scan <select> options",
    structuralOk, structuralDetail);

  /* ── scenario 4: setView (Wigner mode) ─────────────────────────────── */
  const viewRes = await evalJs(ws, `(async () => {
    const gate = document.querySelector(".staff__gates .gate[data-id]");
    const pal = document.querySelector(".palette__item");
    if (!gate || !pal) return { error: "missing gate or palette card" };
    gate.__mark = "sv"; pal.__mark = "sv";
    const sel = document.getElementById("wigner-mode-select");
    const next = sel.value === "0" ? "1" : "0";
    sel.value = next;
    sel.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 250));
    const g2 = document.querySelector(".staff__gates .gate[data-id]");
    const p2 = document.querySelector(".palette__item");
    return { gate: !!g2 && g2.__mark === "sv", pal: !!p2 && p2.__mark === "sv",
             mode: sel.value };
  })()`);
  check("setView (Wigner mode) leaves staff + palette in place",
    !viewRes.error && viewRes.gate && viewRes.pal,
    viewRes.error || `staff=${viewRes.gate ? "kept" : "REBUILT"} palette=${viewRes.pal ? "kept" : "REBUILT"} mode=${viewRes.mode}`);

  /* ── scenario 5/6: fock cutoff slider ──────────────────────────────── */
  await inject(ws, FOCK_CLAMP);
  const fockReady = await waitFor(ws, `(() => {
    const labels = [...document.querySelectorAll(".staff__mode-label")].map((e) => e.textContent);
    return labels.length === 2 && labels.some((t) => t.includes("|5")) 
      && !!document.querySelector(".staff__gates .gate[data-id]");
  })()`, 20000);
  if (!fockReady) throw new Error("fock clamp scene never showed the |5⟩ label");

  const cutoff = await evalJs(ws, `(() => {
    const gate = document.querySelector(".staff__gates .gate[data-id]");
    const pal = document.querySelector(".palette__item");
    gate.__mark = "co"; if (pal) pal.__mark = "co";
    const before = [...document.querySelectorAll(".staff__mode-label")].map((e) => e.textContent);
    const slider = document.getElementById("cutoff-slider");
    slider.value = "3";
    slider.dispatchEvent(new Event("input", { bubbles: true }));
    const g2 = document.querySelector(".staff__gates .gate[data-id]");
    const p2 = document.querySelector(".palette__item");
    let jsonCutoff = null;
    try { jsonCutoff = JSON.parse(document.getElementById("json-input").value).cutoff ?? null; }
    catch { jsonCutoff = "PARSE-ERROR"; }
    return {
      gate: !!g2 && g2.__mark === "co",
      pal: !!p2 && p2.__mark === "co",
      before,
      after: [...document.querySelectorAll(".staff__mode-label")].map((e) => e.textContent),
      jsonCutoff,
      cutoffVal: document.getElementById("cutoff-val").textContent,
    };
  })()`);

  check("fock cutoff slider leaves staff + palette in place",
    cutoff.gate && cutoff.pal,
    `staff=${cutoff.gate ? "kept" : "REBUILT"} palette=${cutoff.pal ? "kept" : "REBUILT"}`);

  /* R7 (prd.md:106-113): `staff.render()` starts with `closeCard()`, so before the
     lightweight path any action routed through `render()` dismissed an open gate
     param card. Asserting it here makes the behaviour change explicit rather than
     implied — the PRD asks for this to be *confirmed*, not assumed. */
  const cardSurvivesCutoff = await evalJs(ws, `(() => {
    const g = document.querySelector(".staff__gates .gate[data-id]");
    if (!g) return { error: "no gate" };
    g.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    if (!document.querySelector(".gate-card__params")) return { error: "card did not open" };
    const slider = document.getElementById("cutoff-slider");
    slider.value = "5";
    slider.dispatchEvent(new Event("input", { bubbles: true }));
    return { open: !!document.querySelector(".gate-card__params") };
  })()`);
  check("fock cutoff slider no longer dismisses an open param card (R7)",
    !cardSurvivesCutoff.error && cardSurvivesCutoff.open,
    cardSurvivesCutoff.error || (cardSurvivesCutoff.open ? "card kept" : "card DISMISSED"));

  const labelSynced = cutoff.after.some((t) => t.includes("|2"));
  const stillStale = cutoff.after.some((t) => t.includes("|5"));
  check("fock cutoff slider still writes state and resyncs the mode label",
    String(cutoff.jsonCutoff) === "3" && cutoff.cutoffVal === "3" && labelSynced && !stillStale,
    `json.cutoff=${JSON.stringify(cutoff.jsonCutoff)} cutoff-val=${cutoff.cutoffVal} `
    + `labels ${JSON.stringify(cutoff.before)} -> ${JSON.stringify(cutoff.after)}`
    + (stillStale ? " [STALE |5⟩ LEFT BEHIND]" : ""));

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
