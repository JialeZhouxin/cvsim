/* Gaussian Lab L2 — editor state (pure) + DOM wiring (initEditor).
   Pure helpers are ESM-exported for node --test; DOM work lives only
   inside initEditor. */
"use strict";

import { OPS, addNode, cellOccupied, completePlacing, moveNodeX, paramsFromOp, placeSingle, removeNode, sourceModes, toCircuitJson, updateParam } from "./ops.js";
import { initStaff } from "./staff.js";

/* ── state ─────────────────────────────────────────────── */
const defaultState = () => ({
  seed: 0,
  nodes: [],
  view: { wigner_mode: 0, lim: 5.0, n: 64 },
  ui: {},
});

/* ── JSON ↔ graph two-way sync (pure parts) ────────────── */
/** Parse + validate a circuit_v0 JSON payload into editor state.
    Returns {state} or {error}. Unknown ops / malformed shapes are
    errors (frozen-graph policy handles the UI side). */
export function stateFromJson(payload) {
  if (!payload || typeof payload !== "object") return { error: "circuit 必须是对象" };
  if (payload.schema !== "circuit_v0") return { error: "schema 必须是 circuit_v0" };
  if (!Array.isArray(payload.nodes)) return { error: "nodes 必须是数组" };
  const seed = payload.seed === undefined ? 0 : payload.seed;
  if (!Number.isInteger(seed) || seed < 0) return { error: "seed 必须是非负整数" };
  const nodes = [];
  const seenIds = new Set();
  let gateIdx = 0; // legacy layout: gates get grid columns in array order, sources excluded
  for (let i = 0; i < payload.nodes.length; i++) {
    const n = payload.nodes[i];
    if (!n || typeof n !== "object") return { error: `nodes[${i}] 非法` };
    // Object.hasOwn: __proto__/constructor are inherited OPS keys (OCR)
    if (!Object.hasOwn(OPS, n.op)) return { error: `nodes[${i}]: 未知 op ${n.op}` };
    const meta = OPS[n.op];
    if (typeof n.id !== "string" || n.id.length === 0 || seenIds.has(n.id)) {
      return { error: `nodes[${i}]: id 必须是非空唯一字符串` };
    }
    seenIds.add(n.id);
    const node = { id: n.id, op: n.op, params: {} };
    for (const [k, d] of Object.entries(meta.params)) {
      const v = n.params?.[k];
      if (d.advanced || d.optional) {
        // optional param (loss nbar / homodyne phi): fill default when absent
        node.params[k] = typeof v === "number" && Number.isFinite(v) ? v : d.def;
        continue;
      }
      // malformed values freeze the graph instead of silently defaulting (OCR)
      if (typeof v !== "number" || !Number.isFinite(v)) {
        return { error: `nodes[${i}].params.${k} 必须是有限数值` };
      }
      node.params[k] = v;
    }
    if (meta.kind === "single") {
      if (!Number.isInteger(n.mode) || n.mode < 0) {
        return { error: `nodes[${i}].mode 必须是非负整数` };
      }
      node.mode = n.mode;
    }
    if (meta.kind === "two") {
      if (!Array.isArray(n.modes) || n.modes.length !== 2 || n.modes.some((m) => !Number.isInteger(m) || m < 0)) {
        return { error: `nodes[${i}].modes 必须是两个非负整数` };
      }
      node.modes = [...n.modes];
    }
    // L5.5 staff layout x — honor ui.x when present (snapped to integer
    // column), else array index (legacy/hand-written JSON falls back to grid
    // columns, never errors). Sources stay layout-free.
    const rawUi = n.ui && typeof n.ui === "object" ? n.ui : {};
    if (meta.kind === "source") {
      node.ui = Number.isFinite(rawUi.x) ? { x: Math.round(rawUi.x) } : undefined;
    } else {
      node.ui = Number.isFinite(rawUi.x) ? { x: Math.round(rawUi.x) } : { x: gateIdx++ };
    }
    nodes.push(node);
  }
  const rawView = payload.view && typeof payload.view === "object" ? payload.view : {};
  if (!Number.isInteger(rawView.wigner_mode) || rawView.wigner_mode < 0) {
    return { error: "view.wigner_mode 必须是非负整数" };
  }
  if (typeof rawView.lim !== "number" || !Number.isFinite(rawView.lim) || rawView.lim <= 0 || rawView.lim > 50) {
    return { error: "view.lim 必须是 (0, 50] 的数值" };
  }
  if (typeof rawView.n !== "number" || !Number.isFinite(rawView.n) || rawView.n < 2 || rawView.n > 512) {
    return { error: "view.n 必须在 [2, 512]" };
  }
  const view = { wigner_mode: rawView.wigner_mode, lim: rawView.lim, n: rawView.n };
  return { state: { seed, nodes, view, ui: {} } };
}

/** Load entry: validate a saved JSON file into editor state (pure).
    Never mutates the current state; failures return {error} only. */
export function loadJson(payload) {
  const res = stateFromJson(payload);
  return res.error ? { error: res.error } : { state: res.state };
}

/* ── DOM wiring (browser only) ─────────────────────────── */
export function initEditor(root, hooks) {
  const dom = {
    palette: root.querySelector("#palette"),
    staff: root.querySelector("#staff"),
    json: root.querySelector("#json-input"),
    runBtn: root.querySelector("#run-btn"),
    resetBtn: root.querySelector("#reset-btn"),
    status: root.querySelector("#status"),
  };
  let state = hooks.defaultScene
    ? (stateFromJson(hooks.defaultScene).state ?? defaultState())
    : defaultState();
  let lastGood = JSON.stringify(toCircuitJson(state)); // frozen-graph policy
  let suppress = false; // graph→JSON writes don't echo-trigger rebuild
  let seq = 0; // stale-response guard

  function emit(circuitJson, source) {
    hooks.onRun(circuitJson, ++seq, source);
  }

  function renderJson() {
    suppress = true;
    dom.json.value = JSON.stringify(toCircuitJson(state), null, 2);
    suppress = false;
  }

  function render() {
    staff.render();
    renderJson();
    hooks.onState(state);
    emit(toCircuitJson(state), "graph");
  }

  const staff = initStaff(dom.staff, {
    getState: () => state,
    onPlace: (op, mode, x) => {
      if (cellOccupied(state.nodes, mode, x)) {
        hooks.onStatus(`该格已被占用（mode ${mode} @ x ${Math.round(x)}）`, false);
        return;
      }
      state = { ...state, nodes: placeSingle(state.nodes, op, mode, x) };
      render();
    },
    onCompletePlacing: (placing, modeB) => {
      const res = completePlacing(state.nodes, placing, modeB);
      if (res.ok) {
        state = { ...state, nodes: res.nodes };
        render();
      }
      return res;
    },
    onMove: (id, x) => {
      const n = state.nodes.find((y) => y.id === id);
      const meta = n && OPS[n.op];
      if (n && meta && meta.kind !== "source") {
        const cells = meta.kind === "two"
          ? [[n.modes[0], x], [n.modes[1], x]]
          : [[n.mode, x]];
        if (cells.some(([m, cx]) => cellOccupied(state.nodes, m, cx, id))) {
          hooks.onStatus(`该格已被占用（x ${Math.round(x)}）`, false);
          return;
        }
      }
      state = { ...state, nodes: moveNodeX(state.nodes, id, x) };
      render();
    },
    onDelete: (id) => {
      state = { ...state, nodes: removeNode(state.nodes, id) };
      render();
    },
    onParam: (id, key, value) => {
      state = { ...state, nodes: state.nodes.map((x) => (x.id === id ? updateParam(x, key, value) : x)) };
      renderJson();
      hooks.onState(state);
      emit(toCircuitJson(state), "graph");
    },
    onPickSweep: (id) => hooks.onPickSweep?.(id),
    onStatus: (msg, ok) => hooks.onStatus(msg, ok),
  });

  /* palette: DnD + click fallback（palette:false 的 op 不出托盘，如 legacy tmsv） */
  for (const op of Object.keys(OPS)) {
    if (OPS[op].palette === false) continue;
    const card = document.createElement("div");
    card.className = "palette__item";
    card.draggable = true;
    card.dataset.op = op;
    card.textContent = OPS[op].label;
    const tryAdd = () => {
      const meta = OPS[op];
      if (meta.kind === "two" && sourceModes(state.nodes) < 2) {
        hooks.onStatus("分束器需要至少 2 个模式（先添加 TMSV 或多源）", false);
        return;
      }
      state = { ...state, nodes: addNode(state.nodes, op) };
      render();
    };
    card.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/plain", op));
    card.addEventListener("click", tryAdd);
    dom.palette.appendChild(card);
  }

  dom.resetBtn.addEventListener("click", () => {
    const parsed = hooks.defaultScene ? stateFromJson(hooks.defaultScene) : null;
    state = parsed && parsed.state ? parsed.state : defaultState();
    lastGood = JSON.stringify(toCircuitJson(state));
    render();
  });

  /* JSON → graph: 400ms debounce, frozen-graph on invalid */
  let rebuildTimer = null;
  dom.json.addEventListener("input", () => {
    if (suppress) return;
    clearTimeout(rebuildTimer);
    rebuildTimer = setTimeout(() => {
      let parsed;
      try {
        parsed = stateFromJson(JSON.parse(dom.json.value));
      } catch {
        hooks.onStatus("JSON 语法错误：图形已冻结", false);
        return;
      }
      if (parsed.error) {
        hooks.onStatus(parsed.error, false);
        return; // graph stays at lastGood
      }
      state = parsed.state;
      lastGood = JSON.stringify(toCircuitJson(state));
      render(); // re-render staff + JSON (OCR: import left rows stale)
    }, 400);
  });

  return {
    getState: () => state,
    setView: (patch) => {
      state = { ...state, view: { ...state.view, ...patch } };
      render(); // syncs JSON textarea + staff + emits debounced run
    },
    setState: (next) => {
      // Load success: replace whole state, freeze, re-render (auto-run via emit)
      state = next;
      lastGood = JSON.stringify(toCircuitJson(state));
      render();
    },
    render,
    isPlacing: () => staff.isPlacing(),
  };
}
