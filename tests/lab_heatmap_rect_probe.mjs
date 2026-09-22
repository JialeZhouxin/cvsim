/* Joint heatmap rect-reuse probe (C2 R7, 09-17-lab-heatmap-redraw-cache).

   `drawHeat` used to `replaceChildren()` and build one `<rect>` per cell on every
   render — up to 30×30 = 900 rects × 6 `setAttribute` each. It now reuses the rect
   nodes and only rewrites `fill-opacity` when the value actually changed.

   Reuse is only safe with the right invalidation, so this probe checks BOTH
   directions — a cache that never invalidates is worse than no cache:

     1. cutoff 10 → 100 joint rects (10×10, viewBox matches);
     2. cutoff 25 → REBUILDS to 625 rects (25×25): rect x/y are written from the
        cell coordinates, so a shape change must not reuse the old nodes;
        asserted by DOM identity, not by count alone;
     3. a same-shape re-render KEEPS the existing node (the actual optimisation);
        asserted by a surviving `__mark2` property, which `replaceChildren()` would
        have destroyed.

   The upper bound is the backend's cutoff ceiling of 30 (`cvsim/lab/schema.py:139`),
   not a frontend constant — so 900 cells is reachable through the UI.

   Run: node tests/lab_heatmap_rect_probe.mjs */

"use strict";
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { EDGE, port, userDataDir, uvicornPath } from "./probe_env.mjs";

const PORT = port(8772, "PROBE_PORT"), CDP_PORT = port(9230, "PROBE_CDP_PORT");

async function waitHttp(url, t = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < t) {
    try { const r = await fetch(url); if (r.ok) return r; } catch {}
    await sleep(200);
  }
  throw new Error("timeout " + url);
}
let id = 0; const pending = new Map();
function send(ws, method, params = {}) {
  const i = ++id; ws.send(JSON.stringify({ id: i, method, params }));
  return new Promise((res, rej) => {
    pending.set(i, { res, rej });
    setTimeout(() => { if (pending.delete(i)) rej(new Error("cdp timeout " + method)); }, 60000);
  });
}
function ev(ws, expression) {
  return send(ws, "Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true })
    .then((m) => {
      if (m.result?.exceptionDetails) throw new Error(m.result.exceptionDetails.exception?.description || "exc");
      return m.result?.result?.value;
    });
}
async function waitFor(ws, expr, t = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < t) { if (await ev(ws, expr)) return true; await sleep(100); }
  return false;
}

const server = spawn(uvicornPath(),
  ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"],
  { cwd: process.cwd(), stdio: "ignore" });
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--no-first-run",
  "--no-default-browser-check", "--no-sandbox", "--disable-dev-shm-usage",
  "--remote-allow-origins=*", `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + userDataDir(".probe-edge-r7-profile"), "about:blank"],
  { stdio: "ignore" });
const fails = [];
function check(n, ok, d = "") { console.log(`${ok ? "PASS" : "FAIL"}  ${n}${d ? " — " + d : ""}`); if (!ok) fails.push(n); }

try {
  await waitHttp(`http://127.0.0.1:${PORT}/health`);
  await waitHttp(`http://127.0.0.1:${CDP_PORT}/json/version`);
  const t = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(`http://127.0.0.1:${PORT}/`)}`, { method: "PUT" }).then((r) => r.json());
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id).res(m); pending.delete(m.id); } };
  await send(ws, "Runtime.enable");
  /* Cache discipline — same as the 8 sibling probes. The persistent
     --user-data-dir keeps Edge's HTTP cache across probe runs, and this probe
     originally lacked the guard the others got in 6b994a9. That commit hit it for
     real: a newly added colormap.js export was not seen, so the page threw
     "does not provide an export named ..." and the probe timed out.
     诚实标注：本次修复时**未能复现**陈旧读取 —— 单进程重载与跨进程（持久 profile）
     两种情形下，Edge 都按 ETag 重新校验并取到了新内容（实测 V1→V2 均返回 V2），
     而这两个 CDP 方法本身确实成功。故保留此纪律是为了与其余探针一致 + 防御该
     已知缺陷，而不是因为本地能观察到差异。 */
  await send(ws, "Network.enable");
  await send(ws, "Network.clearBrowserCache");
  await send(ws, "Page.reload");
  await send(ws, "Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  if (!await waitFor(ws, `!!document.querySelector(".palette__item")`, 30000)) throw new Error("no boot");

  /* switch to fock + HOM circuit via JSON path */
  const HOM = {
    schema: "circuit_v1", seed: 0, nmode: 2, backend: "fock", cutoff: 10,
    ops: [{ id: "h0", op: "two_mode_squeeze", params: { r: 0.6 }, modes: [0, 1] }],
    view: { wigner_mode: 0, lim: 5.0, n: 64, joint_modes: [0, 1] },
    ui: { staff: { h0: 0 } },
  };
  await ev(ws, `(() => {
    const i = document.getElementById("json-input");
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set
      .call(i, ${JSON.stringify(JSON.stringify(HOM))});
    i.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  await waitFor(ws, `document.querySelectorAll("#fock-joint-svg rect").length > 0`, 25000);

  const a = await ev(ws, `(() => {
    const svg = document.getElementById("fock-joint-svg");
    const rects = [...svg.querySelectorAll("rect")];
    rects[0].__mark = "r7";
    return { count: rects.length, viewBox: svg.getAttribute("viewBox"),
             firstOpacity: rects[0].getAttribute("fill-opacity") };
  })()`);
  check("cutoff 10 → 100 joint rects", a.count === 100, `count=${a.count} viewBox=${a.viewBox}`);

  /* change cutoff to 25 → shape 25x25 must REBUILD (stale x/y otherwise) */
  const b = await ev(ws, `(() => {
    const svg = document.getElementById("fock-joint-svg");
    const before = svg.querySelector("rect");
    const slider = document.getElementById("cutoff-slider");
    slider.value = "25";
    slider.dispatchEvent(new Event("input", { bubbles: true }));
    return { beforeMark: before.__mark || null };
  })()`);
  await waitFor(ws, `document.querySelectorAll("#fock-joint-svg rect").length > 100`, 25000);
  const c = await ev(ws, `(() => {
    const svg = document.getElementById("fock-joint-svg");
    const rects = [...svg.querySelectorAll("rect")];
    return { count: rects.length, mark: rects[0].__mark || null,
             viewBox: svg.getAttribute("viewBox") };
  })()`);
  check("cutoff 25 → rebuild to 625 rects (shape change)",
    c.count === 625 && c.viewBox === "0 0 25 25",
    `count=${c.count} viewBox=${c.viewBox} oldNodeSurvived=${c.mark === "r7"}`);
  check("shape change did NOT reuse the old first rect",
    c.mark !== "r7", c.mark === "r7" ? "STALE NODE REUSED (x/y would be wrong)" : "rebuilt");

  /* same shape, same values → node identity preserved on a re-render */
  const d = await ev(ws, `(async () => {
    const svg = document.getElementById("fock-joint-svg");
    const first = svg.querySelector("rect");
    first.__mark2 = "keep";
    const btn = document.getElementById("bos-sample-btn") || document.getElementById("sample-btn");
    if (btn) { btn.click(); }
    await new Promise((r) => setTimeout(r, 1500));
    const again = svg.querySelector("rect");
    return { kept: !!again && again.__mark2 === "keep",
             count: svg.querySelectorAll("rect").length,
             opacity: first.getAttribute("fill-opacity") };
  })()`);
  check("same-shape re-render reuses rect nodes (R7 hit)",
    d.kept, `kept=${d.kept} count=${d.count} opacity=${d.opacity}`);

  console.log(fails.length ? `\n${fails.length} FAILED` : "\nall R7 checks PASS");
} catch (e) {
  fails.push(e.message);
  console.error("ERROR:", e.message);
} finally {
  try { server.kill("SIGTERM"); } catch {}
  try { edge.kill("SIGTERM"); } catch {}
  await sleep(300);
}
process.exit(fails.length ? 1 : 0);
