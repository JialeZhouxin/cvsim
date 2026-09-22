/* Lab 前端渲染性能基线探针（C0 / 09-17-lab-perf-probe-baseline）。
 *
 * 用 CDP `Performance` 域读 LayoutCount / RecalcStyleCount / LayoutDuration /
 * RecalcStyleDuration 的**差值**，量化审查文档 §2.1 / §2.2 / §2.4 三条路径。
 *
 * 骨架与 tests/lab_wigner_layout_probe.mjs 同风格（零依赖：Node >=22 原生
 * fetch + WebSocket，headless Edge）。选择**复制**而非提取共享模块的理由：
 * 探针是测试资产，独立性 > DRY —— 提取会让一个探针的改动影响另一个，
 * 而它们各自守不同的不变量（本探针只测计数，那个守几何）。
 *
 * 用法：
 *   node tests/lab_render_perf_probe.mjs                 # 采集并打印 JSON
 *   node tests/lab_render_perf_probe.mjs --runs=3        # 多次采样（报方差）
 *   node tests/lab_render_perf_probe.mjs --out=f.json    # 写文件（供对拍）
 *   node tests/lab_render_perf_probe.mjs --compare=base.json  # 与基线对拍
 *
 * 退出码：0 = 采集成功；1 = 失败（沿用既有探针约定）。
 */
"use strict";
import { spawn, execSync } from "node:child_process";
import { writeFileSync, readFileSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";
import { EDGE, port, userDataDir, uvicornPath } from "./probe_env.mjs";

const PORT = port(8773, "PROBE_PORT");        // 与既有探针错开（8765-8772 / 8860 已占用）
const CDP_PORT = port(9231, "PROBE_CDP_PORT");    // 与既有探针错开（9223-9230 已占用）

const ARGS = process.argv.slice(2);
const argVal = (name, dflt) => {
  const hit = ARGS.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.split("=").slice(1).join("=") : dflt;
};
const RUNS = Math.max(1, Number(argVal("runs", "1")) || 1);
const OUT = argVal("out", null);
const COMPARE = argVal("compare", null);
const QUIET = ARGS.includes("--quiet");

const checks = [];
const failures = [];
function check(name, ok, detail) {
  checks.push({ name, ok });
  if (!QUIET) console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
  if (!ok) failures.push(`${name}${detail ? " — " + detail : ""}`);
}

async function waitHttp(url, timeoutMs = 60000) {
  const t0 = Date.now();
  let lastErr = null;
  while (Date.now() - t0 < timeoutMs) {
    try {
      const r = await fetch(url);
      if (r.ok) return r;
      lastErr = new Error(`HTTP ${r.status}`);
    } catch (e) { lastErr = e; }
    await sleep(200);
  }
  throw new Error(`timeout waiting for ${url} (${lastErr ? lastErr.message : "no response"})`);
}

let msgId = 0;
const pending = new Map();
function send(ws, method, params = {}, timeoutMs = 30000) {
  const id = ++msgId;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    const t = setTimeout(() => {
      if (pending.delete(id)) reject(new Error(`CDP timeout: ${method}`));
    }, timeoutMs);
    t.unref?.();
  });
}
async function evalJs(ws, expression) {
  /* A Page.reload invalidates the execution context; a single retry after a
     short wait makes the multi-run path robust instead of intermittently
     failing with "CDP timeout: Runtime.evaluate". */
  let lastErr = null;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const r = await send(ws, "Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, 20000);
      if (r.result?.exceptionDetails) {
        throw new Error("evalJs threw: " + (r.result.exceptionDetails.text || "") + " " +
          (r.result.exceptionDetails.exception?.description || ""));
      }
      return r.result?.result?.value;
    } catch (e) {
      lastErr = e;
      /* only retry on transport-level timeouts, not on a genuine JS throw */
      if (!/timeout/i.test(e.message)) throw e;
      await sleep(500);
    }
  }
  throw lastErr;
}

/* ── Performance 域差值采集 ───────────────────────────────────────────── */

const METRIC_KEYS = ["LayoutCount", "RecalcStyleCount", "LayoutDuration", "RecalcStyleDuration"];
async function metrics(ws) {
  const r = await send(ws, "Performance.getMetrics");
  const out = {};
  for (const { name, value } of r.result.metrics) out[name] = value;
  return out;
}
function metricDelta(before, after) {
  const d = {};
  for (const k of METRIC_KEYS) d[k] = +((after[k] || 0) - (before[k] || 0)).toFixed(6);
  return d;
}
/** Run `fn` and return the Performance-metric delta it caused. */
async function measure(ws, fn) {
  const before = await metrics(ws);
  await fn();
  /* let the browser finish any pending rAF/style work before sampling */
  await evalJs(ws, `new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))`);
  const after = await metrics(ws);
  return metricDelta(before, after);
}

/* ── scenarios ───────────────────────────────────────────────────────── */

/** S1: fock cutoff slider, N synthetic-but-trusted `input` events via real input. */
async function scenarioS1(ws, N) {
  /* switch to fock so #cutoff-slider exists and is enabled */
  await evalJs(ws, `(async () => {
    const sel = document.getElementById("backend-select");
    sel.value = "fock";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
    await new Promise((r) => setTimeout(r, 500));
    return sel.value;
  })()`);
  const s = await evalJs(ws, `(() => {
    const r = document.getElementById("cutoff-slider");
    if (!r) return null;
    const b = r.getBoundingClientRect();
    return { left: b.left, top: b.top, w: b.width, h: b.height, min: +r.min, max: +r.max, value: r.value };
  })()`);
  if (!s) return { error: "no #cutoff-slider after switching to fock" };
  const y = s.top + s.h / 2;
  return measure(ws, async () => {
    /* one press, then N moves along the track: each move fires a real `input` */
    await send(ws, "Input.dispatchMouseEvent", { type: "mousePressed", x: s.left + 2, y, button: "left", buttons: 1, clickCount: 1 });
    for (let i = 0; i < N; i++) {
      const px = s.left + (s.w * (i + 1)) / N - 1;
      await send(ws, "Input.dispatchMouseEvent", { type: "mouseMoved", x: px, y, button: "left", buttons: 1 });
    }
    await send(ws, "Input.dispatchMouseEvent", { type: "mouseReleased", x: s.left + s.w - 1, y, button: "left", buttons: 0, clickCount: 1 });
  });
}

/** S2: gate param slider — place a gate, open its card, drive the range input. */
async function scenarioS2(ws, N) {
  /* add a displace gate by clicking the palette card (click fallback = addNode) */
  await evalJs(ws, `(async () => {
    const card = document.querySelector('.palette__item');
    if (card) card.click();
    await new Promise((r) => setTimeout(r, 400));
    return true;
  })()`);
  /* open the first gate's param card */
  const opened = await evalJs(ws, `(async () => {
    const g = document.querySelector(".staff__gates .gate:not(.gate--ghost):not(.gate--preview)");
    if (!g) return "no gate";
    g.click();
    await new Promise((r) => setTimeout(r, 500));
    return document.querySelector(".gate-card input[type=range]") ? "ok" : "no range";
  })()`);
  if (opened !== "ok") return { error: `param card not opened: ${opened}` };
  const s = await evalJs(ws, `(() => {
    const r = document.querySelector(".gate-card input[type=range]");
    const b = r.getBoundingClientRect();
    return { left: b.left, top: b.top, w: b.width, h: b.height };
  })()`);
  const y = s.top + s.h / 2;
  return measure(ws, async () => {
    await send(ws, "Input.dispatchMouseEvent", { type: "mousePressed", x: s.left + 2, y, button: "left", buttons: 1, clickCount: 1 });
    for (let i = 0; i < N; i++) {
      const px = s.left + (s.w * (i + 1)) / N - 1;
      await send(ws, "Input.dispatchMouseEvent", { type: "mouseMoved", x: px, y, button: "left", buttons: 1 });
    }
    await send(ws, "Input.dispatchMouseEvent", { type: "mouseReleased", x: s.left + s.w - 1, y, button: "left", buttons: 0, clickCount: 1 });
  });
}

/** S3: dragover — real HTML5 drag from a palette card across a staff lane. */
async function scenarioS3(ws, N) {
  const geo = await evalJs(ws, `(() => {
    const card = document.querySelector('.palette__item');
    const lane = document.querySelector('.staff__lane');
    const grid = document.querySelector('.staff__grid');
    if (!card || !lane || !grid) return null;
    const c = card.getBoundingClientRect(), l = lane.getBoundingClientRect();
    return {
      card: { x: c.left + c.width / 2, y: c.top + c.height / 2 },
      /* land on the lane, away from the 56px auto-scroll bands */
      lane: { x: l.left + 40, y: l.top + l.height / 2 },
      laneSpan: l.width,
      /* how many dragover events actually reached the page (instrumented below) */
    };
  })()`);
  if (!geo) return { error: "no palette card / staff lane" };

  /* instrument the production dragover handler's event count */
  await evalJs(ws, `(() => {
    window.__perfRec = { dragover: 0, ghostWrites: 0 };
    document.addEventListener("dragover", () => { window.__perfRec.dragover++; }, true);
    return true;
  })()`);

  const delta = await measure(ws, async () => {
    await send(ws, "Input.dispatchMouseEvent", { type: "mousePressed", x: geo.card.x, y: geo.card.y, button: "left", buttons: 1, clickCount: 1 });
    /* first move far enough to trigger the browser's drag threshold */
    await send(ws, "Input.dispatchMouseEvent", { type: "mouseMoved", x: geo.card.x + 30, y: geo.card.y + 10, button: "left", buttons: 1 });
    await sleep(120);
    const x0 = geo.lane.x, x1 = geo.lane.x + Math.min(geo.laneSpan - 60, 300);
    for (let i = 1; i <= N; i++) {
      const px = x0 + ((x1 - x0) * i) / N;
      await send(ws, "Input.dispatchMouseEvent", { type: "mouseMoved", x: px, y: geo.lane.y, button: "left", buttons: 1 });
    }
    await send(ws, "Input.dispatchMouseEvent", { type: "mouseReleased", x: x1, y: geo.lane.y, button: "left", buttons: 0, clickCount: 1 });
    await sleep(150);
  });
  const rec = await evalJs(ws, `window.__perfRec`);
  await evalJs(ws, `(async () => {
    /* clean up the placed gate so the next run starts fresh */
    return true;
  })()`);
  return { ...delta, observedDragover: rec.dragover };
}

/* ── driver ──────────────────────────────────────────────────────────── */

const S1_N = 100, S2_N = 100, S3_N = 20;

const server = spawn(uvicornPath(),
  ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"],
  { cwd: process.cwd(), stdio: "ignore" });
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--remote-allow-origins=*", "--window-size=1440,900",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + userDataDir(".probe-edge-perf"),
  "about:blank",
], { stdio: "ignore" });

let ws;
let report = null;
try {
  await waitHttp(`http://127.0.0.1:${PORT}/health`);
  await waitHttp(`http://127.0.0.1:${CDP_PORT}/json/version`);
  const target = await fetch(`http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(`http://127.0.0.1:${PORT}/`)}`,
    { method: "PUT" }).then((r) => r.json());
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) reject(new Error(m.error.message || JSON.stringify(m.error)));
      else resolve(m);
    }
  };
  await send(ws, "Runtime.enable");
  await send(ws, "Network.enable");
  await send(ws, "Network.clearBrowserCache");   // persistent --user-data-dir: avoid stale modules
  await send(ws, "Performance.enable");
  await send(ws, "Page.reload");
  await sleep(3500);

  /* sanity: the page actually booted (a stale cache would silently test old code) */
  const boot = await evalJs(ws, `(() => ({
    palette: document.getElementById("palette")?.children.length ?? -1,
    runDisabled: document.getElementById("run-btn")?.disabled ?? null,
  }))()`);
  check("page booted (palette rendered, run enabled)", boot.palette > 0 && boot.runDisabled === false,
    JSON.stringify(boot));

  const runs = [];
  for (let i = 0; i < RUNS; i++) {
    if (i > 0) {
      /* reload between runs so each starts from the same state; then WAIT for
         the page to be booted again (a fixed sleep races the reload) */
      await send(ws, "Page.reload");
      let ready = false;
      for (let t = 0; t < 60; t++) {
        await sleep(250);
        try {
          const s = await evalJs(ws, `(() => {
            const p = document.getElementById("palette");
            const r = document.getElementById("run-btn");
            return { palette: p ? p.children.length : -1, runDisabled: r ? r.disabled : null };
          })()`);
          if (s && s.palette > 0 && s.runDisabled === false) { ready = true; break; }
        } catch { /* context mid-reload; keep waiting */ }
      }
      if (!ready) throw new Error(`page did not re-boot after reload (run ${i + 1})`);
    }
    const s1 = await scenarioS1(ws, S1_N);
    const s2 = await scenarioS2(ws, S2_N);
    const s3 = await scenarioS3(ws, S3_N);
    runs.push({ s1, s2, s3 });
    if (!QUIET) console.log(`run ${i + 1}/${RUNS}: s1=${JSON.stringify(s1)} s2=${JSON.stringify(s2)} s3=${JSON.stringify(s3)}`);
  }

  /* aggregate: mean + spread (never silently pick the minimum) */
  const KEYS = ["LayoutCount", "RecalcStyleCount", "LayoutDuration", "RecalcStyleDuration"];
  const aggregate = (pick) => {
    const vals = runs.map(pick);
    if (vals.some((v) => !v || v.error)) return { error: vals.find((v) => v && v.error)?.error || "missing" };
    const out = {};
    for (const k of KEYS) {
      const xs = vals.map((v) => v[k] ?? 0);
      const mean = xs.reduce((a, b) => a + b, 0) / xs.length;
      out[k] = +mean.toFixed(6);
      if (RUNS > 1) out[k + "_min"] = +Math.min(...xs).toFixed(6), out[k + "_max"] = +Math.max(...xs).toFixed(6);
    }
    if (vals[0].observedDragover !== undefined) out.observedDragover = vals[0].observedDragover;
    return out;
  };

  const commit = execSync("git rev-parse --short HEAD", { encoding: "utf8" }).trim();
  /* `commit` alone is misleading when the working tree carries different
     static files than HEAD (e.g. measuring a pre-fix baseline by checking out
     an older revision of cvsim/lab/static). Record the dirty scope so a
     comparison can never silently attribute numbers to the wrong revision. */
  let dirtyStatic = "";
  try {
    dirtyStatic = execSync("git status --porcelain -- cvsim/lab/static", { encoding: "utf8" }).trim();
  } catch { /* not a git repo / detached: leave empty */ }
  report = {
    commit,
    staticDirty: dirtyStatic.length > 0,
    staticDirtyEntries: dirtyStatic ? dirtyStatic.split("\n").length : 0,
    runs: RUNS,
    scenarios: {
      s1_cutoff_slider: { events: S1_N, ...aggregate((r) => r.s1) },
      s2_param_slider: { events: S2_N, ...aggregate((r) => r.s2) },
      s3_dragover: { events: S3_N, ...aggregate((r) => r.s3) },
    },
    /* AC3: record the dispatch path actually used per scenario — numbers from
       different paths are NOT comparable (isTrusted differs). */
    dispatch: {
      s1: "Input.dispatchMouseEvent (real input pipeline, trusted)",
      s2: "Input.dispatchMouseEvent (real input pipeline, trusted)",
      s3: "Input.dispatchMouseEvent (real HTML5 DnD via mouse press+move, trusted)",
    },
    note: "差值为 Performance.getMetrics 的 after-before；每个场景前后各取一次并等两帧 rAF。" +
          "S1/S2 的 N 次 mouseMoved 各触发一次真实 `input`；S3 的真实 dragover 次数见 observedDragover。",
  };

  /* AC1 checks */
  check("S1 produced a LayoutCount delta", report.scenarios.s1_cutoff_slider.LayoutCount !== undefined && !report.scenarios.s1_cutoff_slider.error,
    JSON.stringify(report.scenarios.s1_cutoff_slider).slice(0, 160));
  check("S2 produced a LayoutCount delta", report.scenarios.s2_param_slider.LayoutCount !== undefined && !report.scenarios.s2_param_slider.error,
    JSON.stringify(report.scenarios.s2_param_slider).slice(0, 160));
  check("S3 produced a LayoutCount delta", report.scenarios.s3_dragover.LayoutCount !== undefined && !report.scenarios.s3_dragover.error,
    JSON.stringify(report.scenarios.s3_dragover).slice(0, 160));
  check("S3 was driven by the REAL DnD pipeline (dragover observed)",
    (report.scenarios.s3_dragover.observedDragover || 0) > 0,
    `observedDragover=${report.scenarios.s3_dragover.observedDragover}`);

  if (COMPARE) {
    const base = JSON.parse(readFileSync(COMPARE, "utf8"));
    const rows = [];
    for (const sc of Object.keys(report.scenarios)) {
      for (const k of KEYS) {
        const a = base.scenarios?.[sc]?.[k], b = report.scenarios[sc][k];
        if (a === undefined || b === undefined) continue;
        rows.push({ scenario: sc, metric: k, baseline: a, now: b, delta: +(b - a).toFixed(6),
                    changePct: a !== 0 ? +(((b - a) / a) * 100).toFixed(1) : null });
      }
    }
    report.comparison = { baselineCommit: base.commit, baselineFile: COMPARE, rows };
    if (!QUIET) {
      console.log("\ncomparison vs", COMPARE, `(baseline commit ${base.commit}):`);
      for (const r of rows) {
        console.log(`  ${r.scenario.padEnd(18)} ${r.metric.padEnd(18)} ${String(r.baseline).padStart(10)} -> ${String(r.now).padStart(10)}  (${r.changePct === null ? "n/a" : (r.changePct > 0 ? "+" : "") + r.changePct + "%"})`);
      }
    }
  }

  if (!QUIET) console.log("\n" + JSON.stringify(report, null, 2));
  if (OUT) { writeFileSync(OUT, JSON.stringify(report, null, 2)); console.log("wrote", OUT); }
} catch (e) {
  check("probe ran to completion", false, e.message);
} finally {
  try { ws?.close(); } catch {}
  try { server.kill("SIGTERM"); } catch {}
  try { edge.kill("SIGTERM"); } catch {}
  await sleep(300);
}

if (!QUIET) console.log(`\n${checks.filter((c) => c.ok).length}/${checks.length} checks PASS`);
if (failures.length) { console.error("FAILED: " + failures.join(" ; ")); process.exit(1); }
process.exit(0);
