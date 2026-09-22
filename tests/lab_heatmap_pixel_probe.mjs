/* Heatmap pixel-parity probe — records and re-checks the exact pixels produced by
   the Wigner canvas and the colourbar (C2 09-17-lab-heatmap-redraw-cache).

   Why this exists: C2 R4 (static colourbar) and R6 (imageSmoothingQuality) are
   both *visual* changes. The parent task forbids changing what the user sees
   ("改视觉即越界"), so those two items need a pixel gate, not a judgement call.
   Hash equality is the gate: same scene + same viewport + same dpr must hash
   identically before and after.

   It also covers R1/R3 (offscreen cache, canvas size guard), because a cache that
   serves stale pixels or a size guard that skips a needed clear shows up here as a
   hash mismatch across a scene change.

   Modes:
     node tests/lab_heatmap_pixel_probe.mjs            # compare against the baseline
     node tests/lab_heatmap_pixel_probe.mjs --write     # (re)record the baseline

   `--write` is how the pre-change baseline was captured; it must be run on the
   unmodified code, otherwise the gate just blesses whatever the new code emits.

   Two scenes at two deviceScaleFactors, because:
     - the cache key must invalidate on a new W *and* on a dpr change (R1's
       "易漏点"), so a single dpr would not exercise it;
     - the colourbar is dpr-independent (fixed 8×128 backing store), so including
       it at both dprs proves R4's static draw is not dpr-sensitive. */

"use strict";

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";
import { EDGE, port, userDataDir, uvicornPath } from "./probe_env.mjs";

const PORT = port(8771, "PROBE_PORT");
const CDP_PORT = port(9229, "PROBE_CDP_PORT");
const BASELINE = "tests/lab_heatmap_pixels.json";
const WRITE = process.argv.includes("--write");

const failures = [];
function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
  if (!ok) failures.push(name);
}

async function waitHttp(url, timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try { const r = await fetch(url); if (r.ok) return r; } catch { /* not up yet */ }
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
  return send(ws, "Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })
    .then((m) => {
      if (m.result && m.result.exceptionDetails) {
        throw new Error("page exception: " + (m.result.exceptionDetails.exception?.description || "?"));
      }
      return m.result && m.result.result ? m.result.result.value : undefined;
    });
}
async function waitFor(ws, expr, timeoutMs = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    if (await evalJs(ws, expr)) return true;
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

/* Two scenes with DIFFERENT W grids, so a stale offscreen cache (R1) cannot hide:
   the second run must produce a different hash from the first. */
const SCENES = {
  displace: {
    schema: "circuit_v1", seed: 0, nmode: 2,
    ops: [
      { id: "d0", op: "displace", params: { alpha: 1 }, modes: [0] },
      { id: "d1", op: "displace", params: { alpha: 1 }, modes: [1] },
    ],
    view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: { staff: { d0: 0, d1: 0 } },
  },
  squeeze: {
    schema: "circuit_v1", seed: 0, nmode: 2,
    ops: [{ id: "s0", op: "squeeze", params: { r: 0.8, phi: 0 }, modes: [0] }],
    view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: { staff: { s0: 0 } },
  },
};

/* Same settle discipline as lab_wigner_layout_probe.mjs: the run button's busy
   toggle brackets the debounced request, and the colourbar max label must equal
   what the backend returns for THIS circuit (a repeated label value would
   otherwise let us read geometry/pixels from the previous run). */
async function injectAndSettle(ws, payload) {
  const expected = await evalJs(ws, `(async () => {
    const { wignerScale } = await import("/colormap.js");
    const { axisVal } = await import("/svg_kit.js");
    const r = await fetch("/run", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: ${JSON.stringify(JSON.stringify(payload))} });
    const j = await r.json();
    return axisVal(wignerScale(j.wigner.W));
  })()`);
  await inject(ws, payload);
  const state = await evalJs(ws, `(async () => {
    let sawBusy = false;
    for (let k = 0; k < 600; k++) {
      const btn = document.getElementById("run-btn");
      const st = document.getElementById("status");
      if (btn.disabled) sawBusy = true;
      if (st.dataset.state === "error") return "err:" + st.textContent;
      if (sawBusy && !btn.disabled
          && document.getElementById("colorbar-max").textContent === ${JSON.stringify(expected)}) return "ok";
      await new Promise((r) => setTimeout(r, 50));
    }
    return sawBusy ? "label-mismatch" : "timeout";
  })()`);
  if (state !== "ok") throw new Error(`scene never settled: ${state}`);
  /* one extra frame so any rAF-deferred redraw (C2 R5) has landed */
  await evalJs(ws, `new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))`);
}

/* Snapshot: the two data URLs plus the backing-store sizes. Sizes are recorded
   separately so a hash mismatch can be diagnosed (did the pixels change, or did
   the canvas just get resized?). */
async function snapshot(ws) {
  return evalJs(ws, `(() => {
    const c = document.getElementById("wigner-canvas");
    const cb = document.getElementById("colorbar-canvas");
    return {
      wigner: c.toDataURL(),
      colorbar: cb.toDataURL(),
      wignerSize: [c.width, c.height],
      wignerClient: [c.clientWidth, c.clientHeight],
      colorbarSize: [cb.width, cb.height],
    };
  })()`);
}

function sha(s) { return createHash("sha256").update(s).digest("hex").slice(0, 16); }

const server = spawn(uvicornPath(),
  ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"],
  { cwd: process.cwd(), stdio: "ignore" });
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--no-sandbox", "--disable-dev-shm-usage", "--remote-allow-origins=*",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + userDataDir(".probe-edge-pixel-profile"),
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
  if (!booted) throw new Error("page never booted");

  const observed = {};
  for (const dpr of [1, 2]) {
    await send(ws, "Emulation.setDeviceMetricsOverride",
      { width: 1440, height: 900, deviceScaleFactor: dpr, mobile: false });
    for (const [scene, payload] of Object.entries(SCENES)) {
      const key = `${scene}@dpr${dpr}`;
      await injectAndSettle(ws, payload);
      const s = await snapshot(ws);
      observed[key] = {
        wigner: sha(s.wigner), colorbar: sha(s.colorbar),
        wignerSize: s.wignerSize, wignerClient: s.wignerClient,
        colorbarSize: s.colorbarSize,
      };
      console.log(`  ${key.padEnd(20)} wigner=${observed[key].wigner} `
        + `colorbar=${observed[key].colorbar} canvas=${s.wignerSize.join("x")} `
        + `client=${s.wignerClient.join("x")} cb=${s.colorbarSize.join("x")}`);
    }
  }

  /* Internal sanity: the two scenes must differ, otherwise this probe would pass
     even if every draw served one frozen cached bitmap. */
  check("two different scenes produce different Wigner pixels",
    observed["displace@dpr1"].wigner !== observed["squeeze@dpr1"].wigner,
    `displace=${observed["displace@dpr1"].wigner} squeeze=${observed["squeeze@dpr1"].wigner}`);

  /* Internal sanity: dpr must change the backing store (else the dpr half of the
     cache key is untested). */
  check("dpr change resizes the Wigner backing store",
    observed["displace@dpr1"].wignerSize.join() !== observed["displace@dpr2"].wignerSize.join(),
    `dpr1=${observed["displace@dpr1"].wignerSize.join("x")} dpr2=${observed["displace@dpr2"].wignerSize.join("x")}`);

  if (WRITE) {
    writeFileSync(BASELINE, JSON.stringify(observed, null, 2) + "\n", "utf8");
    console.log(`\nbaseline written to ${BASELINE}`);
  } else if (!existsSync(BASELINE)) {
    check(`baseline ${BASELINE} exists`, false, "run with --write on unmodified code first");
  } else {
    const base = JSON.parse(readFileSync(BASELINE, "utf8"));
    for (const key of Object.keys(observed)) {
      const b = base[key];
      if (!b) { check(`${key} present in baseline`, false, "new case — re-record baseline"); continue; }
      check(`${key}: Wigner pixels unchanged`, observed[key].wigner === b.wigner,
        `${b.wigner} -> ${observed[key].wigner}`);
      check(`${key}: colourbar pixels unchanged`, observed[key].colorbar === b.colorbar,
        `${b.colorbar} -> ${observed[key].colorbar}`);
      check(`${key}: canvas geometry unchanged`,
        observed[key].wignerSize.join() === b.wignerSize.join()
        && observed[key].colorbarSize.join() === b.colorbarSize.join(),
        `${b.wignerSize.join("x")}/${b.colorbarSize.join("x")} -> `
        + `${observed[key].wignerSize.join("x")}/${observed[key].colorbarSize.join("x")}`);
    }
  }

  console.log(failures.length ? `\n${failures.length} check(s) FAILED` : "\nall pixel checks PASS");
} catch (e) {
  failures.push(e.message);
  console.error("PROBE ERROR:", e.message);
} finally {
  try { server.kill("SIGTERM"); } catch { /* ignore */ }
  try { edge.kill("SIGTERM"); } catch { /* ignore */ }
  await sleep(300);
}
process.exit(failures.length ? 1 : 0);
