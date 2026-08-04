/* Gaussian Lab L2 — editor state (pure) + DOM wiring (initEditor).
   Pure helpers are ESM-exported for node --test; DOM work lives only
   inside initEditor. */
"use strict";

import { OPS, addNode, moveNode, paramsFromOp, removeNode, sourceModes, toCircuitJson, updateMode, updateParam } from "./ops.js";

/* ── state ─────────────────────────────────────────────── */
const defaultState = () => ({
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
  const nodes = [];
  const seenIds = new Set();
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
      if (d.advanced) {
        // optional param (e.g. loss nbar): fill default when absent
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
  return { state: { nodes, view, ui: {} } };
}

/* ── DOM wiring (browser only) ─────────────────────────── */
export function initEditor(root, hooks) {
  const dom = {
    palette: root.querySelector("#palette"),
    list: root.querySelector("#node-list"),
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
    renderRows();
    renderJson();
    hooks.onState(state);
    emit(toCircuitJson(state), "graph");
  }

  /* palette: DnD + click fallback */
  for (const op of Object.keys(OPS)) {
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

  dom.list.addEventListener("dragover", (e) => e.preventDefault());
  dom.list.addEventListener("drop", (e) => {
    e.preventDefault();
    const op = e.dataTransfer.getData("text/plain");
    if (Object.hasOwn(OPS, op)) {
      const meta = OPS[op];
      if (meta.kind === "two" && sourceModes(state.nodes) < 2) {
        hooks.onStatus("分束器需要至少 2 个模式（先添加 TMSV 或多源）", false);
        return;
      }
      state = { ...state, nodes: addNode(state.nodes, op) };
      render();
    }
  });

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
      render(); // re-render node rows too (OCR: import left rows stale)
    }, 400);
  });

  /* node list: rows with param sliders + move/delete */
  function renderRows() {
    dom.list.replaceChildren();
    state.nodes.forEach((n, i) => {
      const meta = OPS[n.op];
      const row = document.createElement("div");
      row.className = "node-row";
      row.dataset.id = n.id;

      const head = document.createElement("div");
      head.className = "node-row__head";

      const title = document.createElement("span");
      title.className = "node-row__title";
      title.textContent = `${i + 1}. ${meta.label}`;
      const mode = document.createElement("span");
      mode.className = "node-row__mode mono";
      if (meta.kind === "source") mode.textContent = `+${meta.modes} 模`;
      else if (meta.kind === "single") mode.textContent = `mode ${n.mode}`;
      else mode.textContent = `modes ${n.modes.join(",")}`;
      head.append(title, mode);

      const params = document.createElement("div");
      params.className = "node-row__params";
      for (const [k, d] of Object.entries(meta.params)) {
        if (d.advanced) continue; // nbar: advanced, JSON-only for now
        const wrap = document.createElement("label");
        wrap.className = "param";
        const lab = document.createElement("span");
        lab.className = "param__name mono";
        lab.textContent = k;
        const range = document.createElement("input");
        range.type = "range";
        range.min = d.min;
        range.max = d.max;
        range.step = d.step;
        range.value = n.params[k];
        const num = document.createElement("input");
        num.type = "number";
        num.className = "param__num mono";
        num.step = d.step;
        num.value = n.params[k];
        range.addEventListener("input", () => {
          num.value = range.value;
          state = { ...state, nodes: state.nodes.map((x) => (x.id === n.id ? updateParam(x, k, Number(range.value)) : x)) };
          renderJson();
          hooks.onState(state);
          emit(toCircuitJson(state), "graph");
        });
        num.addEventListener("change", () => {
          range.value = num.value;
          state = { ...state, nodes: state.nodes.map((x) => (x.id === n.id ? updateParam(x, k, Number(num.value)) : x)) };
          render();
        });
        wrap.append(lab, range, num);
        params.appendChild(wrap);
      }

      const controls = document.createElement("div");
      controls.className = "node-row__controls";
      const mk = (label, fn) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "btn btn--ghost btn--sm";
        b.textContent = label;
        b.addEventListener("click", () => {
          state = fn(state);
          render();
        });
        return b;
      };
      const up = mk("↑", (s) => ({ ...s, nodes: moveNode(s.nodes, n.id, -1) }));
      const down = mk("↓", (s) => ({ ...s, nodes: moveNode(s.nodes, n.id, +1) }));
      const del = mk("删除", (s) => ({ ...s, nodes: removeNode(s.nodes, n.id) }));
      up.disabled = i === 0;
      down.disabled = i === state.nodes.length - 1;
      controls.append(up, down, del);

      row.append(head, params, controls);
      dom.list.appendChild(row);
    });
  }

  return {
    getState: () => state,
    setView: (patch) => {
      state = { ...state, view: { ...state.view, ...patch } };
      render(); // syncs JSON textarea + rows + emits debounced run
    },
    render,
  };
}
