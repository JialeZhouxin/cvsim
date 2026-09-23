/* R8 (09-22-lab-wigner-plane) AC13 手工验收的自动化替身 —— 真实页面 + 真实 /run。

   验的是"用户看到什么"，不是后端数字（后者已由 tests/test_lab_plane.py 覆盖）：
   1. 选 plane=xx/pp/epr 后**画布像素确实变了**（不是静默回落 single）；
   2. xx 与 pp 是镜像椭圆（TMSV 关联方向）；
   3. 坐标轴**出现轴名**（单模时没有）；
   4. pair 控件可见性随 (backend, plane, nmode) 变化；
   5. meters 面板 duan_sum 行：有 pair 显示数值、无 pair 显示 honest "—"；
   6. plane=epr 的长轴名**不影响** frame 几何（轴名在 SVG 里，不参与布局）——
      这是把轴名放进 SVG 而不是 DOM 旁栏的理由，必须被锁住。

   Zero-dep: node >= 22 fetch + WebSocket; Edge headless. */
"use strict";

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { setTimeout as sleep } from "node:timers/promises";
import { EDGE, port, userDataDir, uvicornPath } from "./probe_env.mjs";

const PORT = port(8773, "PROBE_PORT");
const CDP_PORT = port(9231, "PROBE_CDP_PORT");
const failures = [];
const checks = [];

function check(name, ok, detail = "") {
  checks.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
  if (!ok) failures.push(name);
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
        throw new Error("page exception: "
          + (m.result.exceptionDetails.exception?.description || "?"));
      }
      return m.result && m.result.result ? m.result.result.value : undefined;
    });
}
async function waitHttp(url, timeoutMs = 60000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    try { const r = await fetch(url); if (r.ok) return r; } catch { /* not up */ }
    await sleep(200);
  }
  throw new Error(`timeout waiting for ${url}`);
}

/* TMSV r=0.8 的两模场景：唯一能同时体现 xx/pp 关联与 EPR 压缩的场景。 */
const TMSV_OPS = [
  { id: "t", op: "two_mode_squeeze", params: { r: 0.8 }, modes: [0, 1] },
];
const scene = (plane, extra = {}) => ({
  schema: "circuit_v1", seed: 0, nmode: 2, ops: TMSV_OPS,
  view: {
    wigner_mode: 0, lim: 5.0, n: 64, ...(plane === "single" ? {} : { plane, joint_modes: [0, 1] }),
    ...extra,
  },
  ui: { staff: { t: 0 } },
});

const server = spawn(uvicornPath(),
  ["cvsim.lab.server:app", "--port", String(PORT), "--log-level", "warning"],
  { cwd: process.cwd(), stdio: "ignore" });
const edge = spawn(EDGE, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--no-sandbox", "--disable-dev-shm-usage", "--remote-allow-origins=*",
  `--remote-debugging-port=${CDP_PORT}`,
  "--user-data-dir=" + userDataDir(".probe-edge-plane-profile"),
  "--window-size=1440,900",
  "about:blank",
], { stdio: "ignore" });

/* 载入 JSON 并等真实 /run 落地。settle 判据是**电平**（包一层 fetch 计数）：
   busy 边沿只有几毫秒，50ms 轮询会整段漏掉（见 implement.md S0b）。 */
async function loadAndSettle(ws, payload) {
  await evalJs(ws, `(() => {
    if (!window.__probeFetchCount) {
      window.__probeFetchCount = 0;
      const orig = window.fetch;
      window.fetch = (...a) => { window.__probeFetchCount++; return orig(...a); };
    }
    window.__probeFetchMark = window.__probeFetchCount;
    return true;
  })()`);
  await evalJs(ws, `(() => {
    const input = document.getElementById("json-input");
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
    setter.call(input, ${JSON.stringify(JSON.stringify(payload))});
    input.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  })()`);
  let sawBusy = false;
  for (let k = 0; k < 200; k++) {
    const st = await evalJs(ws, `(() => {
      const btn = document.getElementById("run-btn");
      const s = document.getElementById("status");
      return { busy: btn.disabled, state: s.dataset.state,
               fired: window.__probeFetchCount > window.__probeFetchMark,
               label: document.getElementById("colorbar-max").textContent };
    })()`);
    if (st.busy || st.fired) sawBusy = true;
    if (st.state === "error") throw new Error("run failed: " + st.label);
    if (sawBusy && !st.busy) {
      await evalJs(ws, `new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))`);
      return st;
    }
    await sleep(50);
  }
  throw new Error("load never settled");
}

function sha(s) { return createHash("sha256").update(s).digest("hex").slice(0, 16); }

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
  await send(ws, "Page.reload");
  if (!(await (async () => {
    for (let k = 0; k < 60; k++) {
      if (await evalJs(ws, `!!document.querySelector(".palette__item")`)) return true;
      await sleep(500);
    }
    return false;
  })())) throw new Error("page never booted");

  /* ── 1. 四个 plane 的像素与轴名 ───────────────────────────── */
  const observed = {};
  for (const plane of ["single", "xx", "pp", "epr"]) {
    await loadAndSettle(ws, scene(plane));
    observed[plane] = await evalJs(ws, `(() => {
      const c = document.getElementById("wigner-canvas");
      const svg = document.getElementById("axis-svg");
      const row = document.getElementById("m-row-duan_sum");
      return {
        hash: null,
        data: c.toDataURL(),
        axisTexts: [...svg.querySelectorAll("text")].map((t) => t.textContent),
        pairHidden: document.getElementById("plane-pair").hidden,
        planeValue: document.getElementById("wigner-plane-select").value,
        duanRowHidden: row ? row.hidden : null,
        duanText: document.getElementById("m-duan")?.textContent ?? null,
        logneg: document.getElementById("m-logneg")?.textContent ?? null,
      };
    })()`);
    observed[plane].hash = sha(observed[plane].data);
  }

  const hashes = Object.fromEntries(Object.entries(observed).map(([k, v]) => [k, v.hash]));
  check("plane selector reflects the loaded payload",
    ["single", "xx", "pp", "epr"].every((p) => observed[p].planeValue === p),
    JSON.stringify(Object.fromEntries(Object.entries(observed).map(([k, v]) => [k, v.planeValue]))));

  /* AC13: 选项**来自 /schema**，不是前端镜像常量。直接对拍下拉的 value 序列与
     `/schema` 的 `extensions.view.planes` —— 若前端另有一份表，后端加预设时
     下拉会静默不同步。 */
  const schemaPlanes = await evalJs(ws, `(async () => {
    const r = await fetch("/schema");
    const s = await r.json();
    return {
      planes: s.extensions.view.planes,
      options: [...document.getElementById("wigner-plane-select").options].map((o) => o.value),
      labels: [...document.getElementById("wigner-plane-select").options].map((o) => o.textContent),
    };
  })()`);
  check("plane dropdown options equal /schema extensions.view.planes (single source)",
    JSON.stringify(schemaPlanes.options) === JSON.stringify(schemaPlanes.planes)
    && schemaPlanes.options.length === 4,
    JSON.stringify(schemaPlanes));

  check("plane=xx/pp/epr change the drawn pixels (no silent fallback to single)",
    hashes.xx !== hashes.single && hashes.pp !== hashes.single && hashes.epr !== hashes.single,
    JSON.stringify(hashes));

  /* 轴名是 **额外**的 text；单模只有刻度数字。断言"多出两个"而不是"没有 text"
     —— 刻度数字一直存在（那是既有的 x/p 数值标注）。 */
  const tickOnly = (texts) => texts.filter((t) => !["x0", "x1", "(x0−x1)/√2", "(p0+p1)/√2"].includes(t));
  check("axis names appear exactly for a cross-mode plane (single has none)",
    observed.single.axisTexts.length === 8 && observed.xx.axisTexts.length === 10
    && observed.epr.axisTexts.length === 10
    && !observed.single.axisTexts.includes("x0"),
    JSON.stringify({ single: observed.single.axisTexts.length, xx: observed.xx.axisTexts.length,
                     tickOnly: tickOnly(observed.xx.axisTexts).length }));

  check("axis names match the preset (xx → x0/x1, epr → the (x−, p+) pair)",
    JSON.stringify(observed.xx.axisTexts.slice(-2)) === JSON.stringify(["x0", "x1"])
    && JSON.stringify(observed.epr.axisTexts.slice(-2)) === JSON.stringify(["(x0−x1)/√2", "(p0+p1)/√2"]),
    JSON.stringify({ xx: observed.xx.axisTexts, epr: observed.epr.axisTexts }));

  /* 1b. 轴名要挂在**自己那根轴**上（曾经两个都转 90°：横轴名挂竖轴头顶、
      竖轴名挂横轴左端）。判据来自后端语义 + 位移实验：
      `labels[0]` 是网格**第一**个自变量（水平轴，位移 mode0 时峰值沿列走），
      `labels[1]` 是第二个（垂直轴）。故 labels[0] 该在横线右端、labels[1] 在竖线顶端。
      同时断言不与刻度数字撞位：横轴刻度在线**下**方（cy+13），竖轴刻度在线**左**侧（cx−7）。 */
  await loadAndSettle(ws, scene("epr"));
  const placement = await evalJs(ws, `(async () => {
    const svg = document.getElementById("axis-svg");
    const vb = svg.getAttribute("viewBox").split(" ").map(Number);
    const w = vb[2], h = vb[3], cx = w / 2, cy = h / 2;
    const texts = [...svg.querySelectorAll("text")];
    const names = texts.filter((t) => /√2/.test(t.textContent));
    const ticks = texts.filter((t) => /^-?\\d/.test(t.textContent));
    const at = (e) => ({ text: e.textContent, x: +e.getAttribute("x"), y: +e.getAttribute("y"),
                         anchor: e.getAttribute("text-anchor") });
    const r = await fetch("/run", { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(${JSON.stringify(scene("epr"))}) });
    const j = await r.json();
    return { labels: j.wigner.axes.labels, w, h, cx, cy,
             names: names.map(at), ticks: ticks.map(at) };
  })()`);
  const [n0, n1] = placement.names;
  check("axis names sit on their own axis (horizontal name right, vertical name top)",
    placement.labels[0] === n0.text && placement.labels[1] === n1.text
    /* labels[0] → 横轴右端：贴右边界、位于横线上方、右对齐 */
    && n0.x === placement.w - 6 && n0.y === placement.cy - 6 && n0.anchor === "end"
    /* labels[1] → 竖轴顶端：贴顶边、位于竖线右侧、左对齐 */
    && n1.y === 12 && n1.x === placement.cx + 8 && n1.anchor === "start",
    JSON.stringify(placement));
  check("axis names do not collide with the tick numbers",
    /* 横轴名在横线上方 → 与线下方的横轴刻度分离 */
    n0.y < placement.cy
    /* 竖轴名在竖线右侧 → 与线左侧的竖轴刻度分离 */
    && n1.x > placement.cx
    /* 逐对实算：名字盒与任一刻度盒不得有交集（名字是单行小字，按 x/y 估 10px 高） */
    && !placement.ticks.some((t) => Math.abs(t.x - n0.x) < 14 && Math.abs(t.y - n0.y) < 14)
    && !placement.ticks.some((t) => Math.abs(t.x - n1.x) < 14 && Math.abs(t.y - n1.y) < 14),
    JSON.stringify({ names: placement.names, tickCount: placement.ticks.length,
                     cx: placement.cx, cy: placement.cy }));

  /* ── 2. pair 控件可见性 ───────────────────────────────────── */
  check("pair controls hidden for single, shown for a cross-mode plane",
    observed.single.pairHidden === true
    && observed.xx.pairHidden === false
    && observed.epr.pairHidden === false,
    JSON.stringify(Object.fromEntries(Object.entries(observed).map(([k, v]) => [k, v.pairHidden]))));

  /* ── 3. duan_sum 行（按需出键 + honest "—"） ───────────────── */
  const duan = Object.fromEntries(Object.entries(observed).map(([k, v]) => [k, v.duanText]));
  /* 行**始终可见**（它是 METER_ROWS 的静态行）；没有 pair 时后端不发该键，
     行渲染 honest "—"。区别在**值**，不在行可见性。 */
  check("duan_sum shows the number with a pair, honest — without one",
    observed.single.duanRowHidden === false && observed.single.duanText === "—"
    && observed.xx.duanRowHidden === false
    && Math.abs(Number(observed.xx.duanText) - 0.40379) < 1e-4,
    JSON.stringify(duan));

  check("log_negativity still renders (2.3083 for TMSV r=0.8)",
    Math.abs(Number(observed.xx.logneg) - 2.3083) < 1e-3,
    observed.xx.logneg);

  /* ── 4. 轴名不得影响 frame 几何（轴名在绝对定位的 SVG 内，不参与布局） ──
     直接证法：量一次 frame 宽，再从 SVG 里删掉轴名 text，再量一次 —— 必须逐位相等。
     （**不要**拿 single 与 epr 的 frame 宽对比：那两者本就不同，因为色带标签的
     数字宽度是 frame 宽的自变量，lab_wigner_layout_probe 的既有不变量。） */
  await loadAndSettle(ws, scene("epr"));
  const geom = await evalJs(ws, `(() => {
    const f = document.querySelector(".wigner__frame").getBoundingClientRect();
    const c = document.querySelector(".wigner__colorbar").getBoundingClientRect();
    const svg = document.getElementById("axis-svg");
    const before = f.width;
    const overlap = Math.max(0, Math.min(f.right, c.right) - Math.max(f.left, c.left))
      * Math.max(0, Math.min(f.bottom, c.bottom) - Math.max(f.top, c.top));
    const named = [...svg.querySelectorAll("text")].filter((t) => /[xp]/.test(t.textContent));
    named.forEach((t) => t.remove());
    const after = document.querySelector(".wigner__frame").getBoundingClientRect().width;
    return { before: Math.round(before * 100) / 100, after: Math.round(after * 100) / 100,
             overlap: Math.round(overlap), removed: named.length,
             texts: [...svg.querySelectorAll("text")].length };
  })()`);
  check("plane axis names are layout-inert (removing them cannot move the frame)",
    geom.removed === 2 && geom.before === geom.after && geom.overlap === 0,
    JSON.stringify(geom));

  /* ── 5. 切到 fock → plane 回落 single（后端只支持 gaussian） ──
     走**真实控件** #backend-select，且断言 editor 的**导出**（不是 textarea 里
     我自己的输入 —— 那是回读输入，不证明状态变了）。 */
  await loadAndSettle(ws, scene("xx"));
  const afterBackend = await evalJs(ws, `(async () => {
    const sel = document.getElementById("backend-select");
    sel.value = "fock";
    sel.dispatchEvent(new Event("change", { bubbles: true }));
    /* 状态行读**同步**快照：setBackend 立刻 onStatus，但紧随的 debounce /run
       会在 ~120ms 后用 "ok · N ms" 覆盖掉 —— 那不是"消息没发出"。 */
    const said = document.getElementById("status").textContent;
    await new Promise((r) => setTimeout(r, 900));
    const j = JSON.parse(document.getElementById("json-input").value);
    return {
      backend: sel.value, plane: j.view.plane, jointModes: j.view.joint_modes,
      pairHidden: document.getElementById("plane-pair").hidden,
      planeValue: document.getElementById("wigner-plane-select").value,
      said,
    };
  })()`);
  check("switching to fock clears the plane (gaussian-only) and hides the pair",
    afterBackend.backend === "fock" && afterBackend.plane === undefined
    && afterBackend.pairHidden === true && afterBackend.planeValue === "single"
    && /仅 gaussian/.test(afterBackend.said),
    JSON.stringify(afterBackend));

  console.log(failures.length ? `\n${failures.length} check(s) FAILED` : "\nall plane checks PASS");
} catch (e) {
  failures.push(e.message);
  console.error("PROBE ERROR:", e.message);
} finally {
  try { server.kill("SIGTERM"); } catch { /* ignore */ }
  try { edge.kill("SIGTERM"); } catch { /* ignore */ }
  await sleep(300);
}
process.exit(failures.length ? 1 : 0);
