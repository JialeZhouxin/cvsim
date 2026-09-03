/* Gaussian Lab L2 — editor state (pure) + DOM wiring (initEditor).
   Pure helpers are ESM-exported for node --test; DOM work lives only
   inside initEditor. */
"use strict";

import { OPS, addNode, backendOps, cellOccupied, completePlacing, moveNodeX, opGroup, paramsFromOp, placeSingle, removeNode, removeSource, sourceModes, toV1Json, updateParam } from "./ops.js";
import { BOSONIC_SOURCE_OPTIONS, initialCacheKey, parseInitial, remapForBackend, vacuumDefault } from "./initial.js";
import { initStaff } from "./staff.js";

/* ── state ─────────────────────────────────────────────── */
const defaultState = () => ({
  seed: 0,
  nodes: [],
  view: { wigner_mode: 0, lim: 5.0, n: 64, joint_modes: null },
  ui: {},
  backend: "gaussian", // F7: representation backend (缺省 gaussian = 旧 JSON 零破坏)
  initial: null,       // F7/B6: per-mode 初始态，语义按 backend 二分（见 initial.js）
  cutoffs: [],         // F7: per-mode cutoffs（缺省全 10，均匀时 JSON 写 int）
});

/** F7: pad/truncate an array to length n (default value v). */
function padTo(arr, n, v) {
  const base = Array.isArray(arr) ? arr.slice(0, n) : [];
  return [...base, ...Array(Math.max(0, n - base.length)).fill(v)];
}

/* ── JSON ↔ graph two-way sync (pure parts) ────────────── */
/** Parse + validate a circuit JSON payload into editor state.
    circuit_v1 (ADR-0003, native) is inverted back to the graph model:
    implicit vacuum source, op name/param remapping (measure_*, phase theta).
    circuit_v0 files keep the legacy path. Returns {state} or {error}.
    Unknown ops / malformed shapes are errors (frozen-graph policy). */
export function stateFromJson(payload) {
  if (!payload || typeof payload !== "object") return { error: "circuit 必须是对象" };
  if (payload.schema === "circuit_v1") return stateFromV1(payload);
  if (payload.schema !== "circuit_v0") return { error: "schema 必须是 circuit_v0 或 circuit_v1" };
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
  const view = { wigner_mode: rawView.wigner_mode, lim: rawView.lim, n: rawView.n, joint_modes: null };
  if (rawView.joint_modes !== undefined && rawView.joint_modes !== null) {
    if (!Array.isArray(rawView.joint_modes) || rawView.joint_modes.length !== 2
        || rawView.joint_modes[0] === rawView.joint_modes[1]
        || rawView.joint_modes.some((m) => !Number.isInteger(m) || m < 0)) {
      return { error: "view.joint_modes 必须是两个不同的非负整数" };
    }
    view.joint_modes = [...rawView.joint_modes];
  }
  const ext = parseExtensions(payload, sourceModes(nodes));
  if (ext.error) return ext;
  return { state: { seed, nodes, view, ui: {}, ...ext } };
}

/** F7: backend/initial/cutoff extension fields (shared by v0 + v1 paths).
    nmode must be the resolved mode count of the loaded circuit.
    initial 语义在 initial.js 单点维护（F7 fock 整数 / B6 bosonic 源名）。 */
function parseExtensions(payload, nmode) {
  let backend = "gaussian";
  if (payload.backend !== undefined) {
    if (payload.backend !== "gaussian" && payload.backend !== "fock"
        && payload.backend !== "bosonic") {
      return { error: "backend 必须是 gaussian、fock 或 bosonic" };
    }
    backend = payload.backend;
  }
  const parsed = parseInitial(backend, payload.initial, nmode);
  if (parsed.error) return { error: parsed.error };
  const initial = parsed.initial;
  let cutoffs = Array(nmode).fill(10);
  if (payload.cutoff !== undefined) {
    if (Number.isInteger(payload.cutoff) && payload.cutoff >= 1) {
      cutoffs = Array(nmode).fill(payload.cutoff);
    } else if (Array.isArray(payload.cutoff) && payload.cutoff.length === nmode
        && payload.cutoff.every((c) => Number.isInteger(c) && c >= 1)) {
      cutoffs = [...payload.cutoff];
    } else {
      return { error: `cutoff 必须是 ≥1 的整数或长度为 ${nmode} 的数组` };
    }
  }
  return { backend, initial, cutoffs };
}

//: v1 IR op → UI op (mirror of cvsim.lab.ir V0_TO_V1_OP, inverted).
const V1_TO_UI_OP = {
  measure_homodyne: "homodyne",
  measure_heterodyne: "heterodyne",
};

//: UI param → v1 IR param (inverse of UI_TO_V1_PARAM in ops.js).
const V1_TO_UI_PARAM = { phase: { phi: "theta" } };
//: Fock IR param → UI param (inverse of FOCK_UI_TO_V1_PARAM in ops.js;
//  key = UI param, value = fock IR param).
const FOCK_V1_TO_UI_PARAM = { loss: { T: "eta" } };

function nextFreeV1Id(i, seenIds) {
  // auto ids must never collide with explicit ids (n0 + explicit "n0")
  let id = `n${i}`;
  for (let k = 1; seenIds.has(id); k++) id = `n${i}_${k}`;
  return id;
}

/** circuit_v1 → graph model (inverse of toV1Json). v1 has no source
    concept: an implicit vacuum source (nmode) is prepended; ops map 1:1
    to UI nodes; phase ``theta`` maps back to the UI ``phi`` param.
    Core-only ops (cz/cx/interferometer/…) are rejected — same whitelist
    the backend load enforces. */
function stateFromV1(payload) {
  if (!Array.isArray(payload.ops)) return { error: "ops 必须是数组" };
  if (!Number.isInteger(payload.nmode) || payload.nmode < 1) {
    return { error: "nmode 必须是不小于 1 的整数" };
  }
  const seed = payload.seed === undefined ? 0 : payload.seed;
  if (!Number.isInteger(seed) || seed < 0) return { error: "seed 必须是非负整数" };
  const nodes = [];
  const staff = payload.ui && typeof payload.ui === "object" ? payload.ui.staff : undefined;
  let gateIdx = 0;
  // pass 1: collect explicit ids — auto ids (n${i}) must defer to them
  const explicit = new Set();
  for (let i = 0; i < payload.ops.length; i++) {
    const o = payload.ops[i];
    if (o && typeof o === "object" && typeof o.id === "string") {
      if (o.id.length === 0 || explicit.has(o.id)) {
        return { error: `ops[${i}]: id 必须是非空唯一字符串` };
      }
      explicit.add(o.id);
    }
  }
  const assigned = new Set(explicit);
  for (let i = 0; i < payload.ops.length; i++) {
    const o = payload.ops[i];
    if (!o || typeof o !== "object") return { error: `ops[${i}] 非法` };
    const uiOp = V1_TO_UI_OP[o.op] || o.op;
    if (!Object.hasOwn(OPS, uiOp)) return { error: `ops[${i}]: op ${o.op} 不在 Lab 白名单` };
    const meta = OPS[uiOp];
    const id = o.id !== undefined ? o.id : nextFreeV1Id(i, assigned);
    if (typeof id !== "string" || id.length === 0 || (assigned.has(id) && id !== o.id)) {
      return { error: `ops[${i}]: id 必须是非空唯一字符串` };
    }
    assigned.add(id);
    const node = { id, op: uiOp, params: {} };
    const isFock = payload.backend === "fock";
    const pnames = isFock
      ? { ...(V1_TO_UI_PARAM[uiOp] || {}), ...(FOCK_V1_TO_UI_PARAM[uiOp] || {}) }
      : (V1_TO_UI_PARAM[uiOp] || {});
    const params = { ...o.params };
    const isBosonic = payload.backend === "bosonic";
    if (uiOp === "displace" && isBosonic && params.alpha
        && typeof params.alpha === "object" && !Array.isArray(params.alpha)) {
      // B6: bosonic feedforward — alpha is {$ref, gain} object, kept verbatim
      node.params.alpha = { ...params.alpha };
    } else if (uiOp === "displace" && Array.isArray(params.alpha)) {
      // v1 alpha is [re, im]; the UI slider controls the real part only
      params.alpha = typeof params.alpha[0] === "number" ? params.alpha[0] : NaN;
    }
    for (const [k, d] of Object.entries(meta.params)) {
      // phase: IR speaks theta, UI speaks phi
      const v = params[pnames[k] !== undefined ? pnames[k] : k];
      // fock squeeze has no phi in the IR: optional on the fock path
      const optionalOnFock = isFock && uiOp === "squeeze" && k === "phi";
      if (d.advanced || d.optional || optionalOnFock) {
        if (d.string) {
          // string params (measure result names): preserve explicit names
          node.params[k] = typeof v === "string" && v.length ? v : d.def;
          continue;
        }
        node.params[k] = typeof v === "number" && Number.isFinite(v) ? v : d.def;
        continue;
      }
      if (isBosonic && uiOp === "displace" && k === "alpha"
          && node.params.alpha && typeof node.params.alpha === "object") {
        continue; // feedforward object already preserved above
      }
      if (typeof v !== "number" || !Number.isFinite(v)) {
        return { error: `ops[${i}].params.${k} 必须是有限数值` };
      }
      node.params[k] = v;
    }
    if (meta.kind === "two") {
      if (!Array.isArray(o.modes) || o.modes.length !== 2 || o.modes.some((m) => !Number.isInteger(m) || m < 0)) {
        return { error: `ops[${i}].modes 必须是两个非负整数` };
      }
      node.modes = [...o.modes];
      node.ui = { x: staff && Number.isFinite(staff[id]) ? staff[id] : gateIdx++ };
    } else {
      if (!Array.isArray(o.modes) || o.modes.length !== 1 || !Number.isInteger(o.modes[0]) || o.modes[0] < 0) {
        return { error: `ops[${i}].modes 必须是一个非负整数` };
      }
      node.mode = o.modes[0];
      node.ui = { x: staff && Number.isFinite(staff[id]) ? staff[id] : gateIdx++ };
    }
    nodes.push(node);
  }
  // implicit vacuum source covering all modes (v1 has no source concept)
  let vid = "vac0";
  while (assigned.has(vid)) vid = "vac" + (Number(vid.slice(3)) + 1);
  nodes.unshift({
    id: vid,
    op: "vacuum",
    params: { nmode: payload.nmode },
    ui: undefined,
  });
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
  const view = { wigner_mode: rawView.wigner_mode, lim: rawView.lim, n: rawView.n, joint_modes: null };
  if (rawView.joint_modes !== undefined && rawView.joint_modes !== null) {
    if (!Array.isArray(rawView.joint_modes) || rawView.joint_modes.length !== 2
        || rawView.joint_modes[0] === rawView.joint_modes[1]
        || rawView.joint_modes.some((m) => !Number.isInteger(m) || m < 0)) {
      return { error: "view.joint_modes 必须是两个不同的非负整数" };
    }
    view.joint_modes = [...rawView.joint_modes];
  }
  const ext = parseExtensions(payload, payload.nmode);
  if (ext.error) return ext;
  return { state: { seed, nodes, view, ui: {}, ...ext } };
}

/** Load entry: validate a saved JSON file into editor state (pure).
    Never mutates the current state; failures return {error} only. */
export function loadJson(payload) {
  const res = stateFromJson(payload);
  return res.error ? { error: res.error } : { state: res.state };
}

/** Immutable-state history factory (pure): stores state references, so it
    is O(1) per edit and safe because every editor mutation builds a new
    state object (the old one is never touched again).
    - push(state): record the current state before a mutation; clears redo
    - undo(current): returns the previous state, or null when empty
    - redo(current): returns the state that was undone, or null when empty
    - clear(): drop everything (e.g. after direct JSON editing) */
export function createHistory(max = 50) {
  const stack = [];
  const redoStack = [];
  return {
    push(state) {
      stack.push(state);
      if (stack.length > max) stack.shift();
      redoStack.length = 0; // new edit invalidates redo
    },
    undo(current) {
      if (!stack.length) return null;
      redoStack.push(current);
      return stack.pop();
    },
    redo(current) {
      if (!redoStack.length) return null;
      stack.push(current);
      return redoStack.pop();
    },
    clear() { stack.length = 0; redoStack.length = 0; },
    canUndo: () => stack.length > 0,
    canRedo: () => redoStack.length > 0,
  };
}

/* ── DOM wiring (browser only) ─────────────────────────── */
export function initEditor(root, hooks) {
  const dom = {
    palette: root.querySelector("#palette"),
    staff: root.querySelector("#staff"),
    json: root.querySelector("#json-input"),
    runBtn: root.querySelector("#run-btn"),
    resetBtn: root.querySelector("#reset-btn"),
    undoBtn: root.querySelector("#undo-btn"),
    redoBtn: root.querySelector("#redo-btn"),
    status: root.querySelector("#status"),
    backendSelect: root.querySelector("#backend-select"),
    addModeBtn: root.querySelector("#add-mode-btn"),
    initialCard: root.querySelector("#initial-card"),
    initialInputs: root.querySelector("#initial-inputs"),
  };
  dom.undoBtn?.addEventListener("click", undo);
  dom.redoBtn?.addEventListener("click", redo);
  let state = hooks.defaultScene
    ? (stateFromJson(hooks.defaultScene).state ?? defaultState())
    : defaultState();
  let lastGood = JSON.stringify(toV1Json(state)); // frozen-graph policy
  let suppress = false; // graph→JSON writes don't echo-trigger rebuild
  let suppressEmit = false; // #13: dragstart→dragend 期间抑制 emit，drop/取消后单次
  let seq = 0; // stale-response guard

  /* ── undo/redo: state is immutable (every mutation builds a new object),
     so the stacks can hold plain state references — zero copies ── */
  const hist = createHistory(50);

  function pushHistory() {
    hist.push(state);
  }

  function undo() {
    const prev = hist.undo(state);
    if (prev !== null) { state = prev; render(); }
  }

  function redo() {
    const next = hist.redo(state);
    if (next !== null) { state = next; render(); }
  }

  /* Ctrl+Z / Ctrl+Shift+Z / Ctrl+Y, but never inside form controls (JSON
     textarea / seed input keep browser-native edit undo) */
  document.addEventListener("keydown", (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    if (e.target?.closest?.("input, textarea, select")) return;
    const k = e.key.toLowerCase();
    if (k === "z" && !e.shiftKey) { e.preventDefault(); undo(); }
    else if (k === "z" && e.shiftKey) { e.preventDefault(); redo(); }
    else if (k === "y") { e.preventDefault(); redo(); }
  });

  function emit(circuitJson, source) {
    hooks.onRun(circuitJson, ++seq, source);
  }

  function renderJson() {
    suppress = true;
    dom.json.value = JSON.stringify(toV1Json(state), null, 2);
    suppress = false;
  }

  function render() {
    staff.render();
    renderPalette();
    renderJson();
    renderFockControls();
    hooks.onState(state);
    if (dom.undoBtn) dom.undoBtn.disabled = !hist.canUndo();
    if (dom.redoBtn) dom.redoBtn.disabled = !hist.canRedo();
    if (!suppressEmit) emit(toV1Json(state), "graph");
  }

  const staff = initStaff(dom.staff, {
    getState: () => state,
    onPlace: (op, mode, x) => {
      if (cellOccupied(state.nodes, mode, x)) {
        hooks.onStatus(`该格已被占用（mode ${mode} @ x ${Math.round(x)}）`, false);
        return;
      }
      pushHistory();
      state = { ...state, nodes: placeSingle(state.nodes, op, mode, x) };
      render();
    },
    onCompletePlacing: (placing, modeB) => {
      const res = completePlacing(state.nodes, placing, modeB);
      if (res.ok) {
        pushHistory();
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
      pushHistory();
      state = { ...state, nodes: moveNodeX(state.nodes, id, x) };
      render();
    },
    onDelete: (id) => {
      const n = state.nodes.find((y) => y.id === id);
      if (n && OPS[n.op] && OPS[n.op].kind === "source") {
        // 删源级联（removeSource）：至少留一个源；删后钳住 wigner_mode 防越界
        const nSources = state.nodes.filter((y) => OPS[y.op].kind === "source").length;
        if (nSources <= 1) {
          hooks.onStatus("至少保留一个源节点", false);
          return;
        }
        pushHistory();
        const res = removeSource(state.nodes, id);
        const nm = sourceModes(res.nodes);
        state = { ...state, nodes: res.nodes,
          view: { ...state.view, wigner_mode: Math.max(0, Math.min(state.view.wigner_mode, nm - 1)) } };
      } else {
        pushHistory();
        state = { ...state, nodes: removeNode(state.nodes, id) };
      }
      render();
    },
    onParam: (id, key, value) => {
      pushHistory(); // one entry per slider step; createHistory(50) caps growth (ponytail: coalesce consecutive slider drags when the history gets noisy)
      state = { ...state, nodes: state.nodes.map((x) => (x.id === id ? updateParam(x, key, value) : x)) };
      renderJson();
      hooks.onState(state);
      emit(toV1Json(state), "graph");
    },
    onPickSweep: (id) => hooks.onPickSweep?.(id),
    onStatus: (msg, ok) => hooks.onStatus(msg, ok),
    /* #13: drag window — suppress per-move emits; drop/cancel emits once */
    onDragStart: () => { suppressEmit = true; },
    onDragEnd: () => {
      suppressEmit = false;
      emit(toV1Json(state), "graph");
    },
  });

  /* palette: DnD + click fallback, grouped by category（palette:false 的 op 不出托盘）。
     F7: per-backend 过滤 — OPS.backends 不含当前 backend 的 op 不出托盘。 */
  const PALETTE_GROUPS = [
    ["source", "源"],
    ["gate", "门"],
    ["channel", "通道"],
    ["measure", "测量"],
  ];
  function renderPalette() {
    dom.palette.replaceChildren();
    for (const [gid, title] of PALETTE_GROUPS) {
      const ops = backendOps(state.backend).filter((op) => opGroup(op) === gid);
      if (!ops.length) continue;
      const group = document.createElement("details");
      group.className = "palette__group";
      group.open = true; // L5: collapsible group, default expanded
      const h = document.createElement("summary");
      h.className = "palette__group-title";
      h.textContent = title;
      group.appendChild(h);
      const items = document.createElement("div");
      items.className = "palette__grid";
      for (const op of ops) {
        const card = document.createElement("div");
        card.className = "palette__item";
        card.draggable = true;
        card.dataset.op = op;
        card.textContent = OPS[op].label;
        card.title = OPS[op].tip || ""; // #3: hover 提示物理含义
        const tryAdd = () => {
          const meta = OPS[op];
          if (meta.kind === "two" && sourceModes(state.nodes) < 2) {
            hooks.onStatus("双模操作需要至少 2 个模式（先添加模式）", false);
            return;
          }
          pushHistory();
          state = { ...state, nodes: addNode(state.nodes, op) };
          render();
        };
        card.addEventListener("dragstart", (e) => {
          suppressEmit = true;
          e.dataTransfer.setData("text/plain", op);
          e.dataTransfer.effectAllowed = "copy";
          e.dataTransfer.dropEffect = "copy";
          card.classList.add("is-dragging");
          staff.setDragPayload({ kind: "op", op });
        });
        card.addEventListener("dragend", () => {
          card.classList.remove("is-dragging");
          staff.setDragPayload(null);
          suppressEmit = false;
          emit(toV1Json(state), "graph"); // drop/取消后单次 emit
        });
        card.addEventListener("click", tryAdd);
        items.appendChild(card);
      }
      group.appendChild(items);
      dom.palette.appendChild(group);
    }
  }

  /* ── F7: backend 切换 + Fock 模式控制（＋模 / initial 卡）─── */
  function setBackend(next) {
    if (next === state.backend) return;
    pushHistory();
    let nodes = state.nodes;
    let view = state.view;
    let cutoffs = state.cutoffs;
    if (next === "fock") {
      if (!nodes.some((n) => n.op === "vacuum")) {
        let vid = "vac0";
        for (let k = 1; nodes.some((n) => n.id === vid); k++) vid = "vac" + k;
        nodes = [{ id: vid, op: "vacuum", params: { nmode: 1 } }, ...nodes];
      }
      const nm = sourceModes(nodes);
      cutoffs = padTo(cutoffs, nm, 10);
      if (nm >= 2 && !Array.isArray(view.joint_modes)) {
        view = { ...view, joint_modes: [0, 1] }; // HOM 剧本：joint 卡默认开
      }
    } else if (next === "bosonic") {
      if (!nodes.some((n) => n.op === "vacuum")) {
        let vid = "vac0";
        for (let k = 1; nodes.some((n) => n.id === vid); k++) vid = "vac" + k;
        nodes = [{ id: vid, op: "vacuum", params: { nmode: 1 } }, ...nodes];
      }
    }
    // B6/F7: initial 跨后端语义重映射（单点在 initial.js）。真空对应项保留
    // （fock 0 ↔ bosonic null），非真空项重置 + UI 提示，永不静默截断。
    const nm = sourceModes(nodes);
    const remap = remapForBackend(state.backend, next, state.initial, nm);
    if (remap.reset > 0) {
      hooks.onStatus(`${remap.reset} 项初始态因后端切换被重置为真空`, false);
    }
    state = { ...state, backend: next, nodes, view, initial: remap.initial, cutoffs };
    render();
  }

  function addMode() {
    pushHistory();
    let nodes = state.nodes;
    const vac = nodes.find((n) => n.op === "vacuum");
    if (vac) {
      nodes = nodes.map((n) => (n.id === vac.id
        ? { ...n, params: { ...n.params, nmode: (n.params.nmode ?? 1) + 1 } }
        : n));
    } else {
      let vid = "vac0";
      for (let k = 1; nodes.some((n) => n.id === vid); k++) vid = "vac" + k;
      nodes = [{ id: vid, op: "vacuum", params: { nmode: 1 } }, ...nodes];
    }
    const nm = sourceModes(nodes);
    // B6/F7: initial 补长也走单点重映射（from === to 同后端：原值保留 + 真空补位）
    const remap = remapForBackend(state.backend, state.backend, state.initial, nm);
    state = { ...state, nodes,
      initial: remap.initial, cutoffs: padTo(state.cutoffs, nm, 10) };
    render();
  }

  function setInitial(i, v) {
    const nm = sourceModes(state.nodes);
    const fill = vacuumDefault(state.backend);
    const next = Array(nm).fill(fill).map((_, k) =>
      (state.initial ? state.initial[k] : fill));
    next[i] = v;
    pushHistory();
    state = { ...state, initial: next };
    renderJson();
    hooks.onState(state);
    emit(toV1Json(state), "graph");
  }

  /* B6: bosonic 初始态 = 每模 GKP 源选择（真空/gkp0/gkp1/2d；选项表在 initial.js） */
  function renderBosonicInitial(nm) {
    const initial = state.initial;
    dom.initialInputs.dataset.nmode = initialCacheKey("bosonic", nm);
    dom.initialInputs.replaceChildren();
    for (let i = 0; i < nm; i++) {
      const wrap = document.createElement("label");
      wrap.className = "param";
      const lab = document.createElement("span");
      lab.className = "param__name mono";
      lab.textContent = `mode ${i}`;
      const sel = document.createElement("select");
      sel.className = "select mono";
      const cur = initial ? initial[i] : null;
      for (const [val, text] of BOSONIC_SOURCE_OPTIONS) {
        const opt = document.createElement("option");
        opt.value = val === null ? "" : val;
        opt.textContent = text;
        if (val === cur) opt.selected = true;
        sel.appendChild(opt);
      }
      sel.addEventListener("change", () => {
        const v = sel.value === "" ? null : sel.value;
        setInitial(i, v);
      });
      wrap.append(lab, sel);
      dom.initialInputs.appendChild(wrap);
    }
  }

  function renderFockControls() {
    const fock = state.backend === "fock";
    const bosonic = state.backend === "bosonic";
    if (dom.addModeBtn) dom.addModeBtn.hidden = !fock;
    if (fock === bosonic && !fock) { // neither
      if (dom.backendSelect) dom.backendSelect.value = state.backend;
      if (dom.initialCard) { dom.initialCard.hidden = true; dom.initialInputs.dataset.nmode = ""; dom.initialInputs.replaceChildren(); }
      return;
    }
    if (dom.backendSelect) dom.backendSelect.value = state.backend;
    if (!dom.initialCard) return;
    dom.initialCard.hidden = false;
    const nm = sourceModes(state.nodes);
    // 缓存键含 backend（initialCacheKey）：切换后端必重建控件，
    // 防止 bosonic 下残留 fock 数字输入框（模数不变早退 bug）。
    if (dom.initialInputs.dataset.nmode === initialCacheKey(state.backend, nm)) {
      // 同键仍需同步 fock 数字输入值（cutoff 变化等场景）
      if (!bosonic) syncFockInputValues();
      return;
    }
    if (bosonic) { renderBosonicInitial(nm); return; }
    const cutoffs = state.cutoffs;
    const initial = state.initial;
    dom.initialInputs.dataset.nmode = initialCacheKey("fock", nm);
    dom.initialInputs.replaceChildren();
    for (let i = 0; i < nm; i++) {
      const wrap = document.createElement("label");
      wrap.className = "param";
      const lab = document.createElement("span");
      lab.className = "param__name mono";
      lab.textContent = `mode ${i}`;
      const inp = document.createElement("input");
      inp.type = "number";
      inp.className = "param__num mono";
      inp.min = 0;
      inp.max = (cutoffs[i] ?? 10) - 1;
      inp.step = 1;
      inp.value = initial ? initial[i] : 0;
      inp.addEventListener("change", () => {
        const v = Number(inp.value);
        if (!Number.isInteger(v) || v < 0) {
          hooks.onStatus("初始态光子数必须是非负整数", false);
          inp.value = state.initial ? state.initial[i] : 0;
          return;
        }
        setInitial(i, v);
      });
      wrap.append(lab, inp);
      dom.initialInputs.appendChild(wrap);
    }
  }

  /** fock 数字输入值同步（控件已存在、仅值/上限可能变化的场景）。 */
  function syncFockInputValues() {
    const cutoffs = state.cutoffs;
    const initial = state.initial;
    [...dom.initialInputs.children].forEach((wrap, i) => {
      const inp = wrap.querySelector("input");
      if (!inp) return;
      inp.max = (cutoffs[i] ?? 10) - 1;
      const want = initial ? initial[i] : 0;
      if (inp.value !== String(want)) inp.value = want;
    });
  }

  if (dom.backendSelect) {
    dom.backendSelect.addEventListener("change", () => setBackend(dom.backendSelect.value));
  }
  if (dom.addModeBtn) dom.addModeBtn.addEventListener("click", addMode);

  dom.resetBtn.addEventListener("click", () => {
    const parsed = hooks.defaultScene ? stateFromJson(hooks.defaultScene) : null;
    pushHistory();
    state = parsed && parsed.state ? parsed.state : defaultState();
    lastGood = JSON.stringify(toV1Json(state));
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
      lastGood = JSON.stringify(toV1Json(state));
      hist.clear(); // JSON is the edit source: graphic history no longer maps
      render(); // re-render staff + JSON (OCR: import left rows stale)
    }, 400);
  });

  return {
    getState: () => state,
    setView: (patch) => {
      state = { ...state, view: { ...state.view, ...patch } };
      render(); // syncs JSON textarea + staff + emits debounced run
    },
    setCircuit: (patch) => {
      // F7: cutoff/initial patches from the Fock guard panel
      pushHistory();
      state = { ...state, ...patch };
      render();
    },
    setState: (next) => {
      // Load success: replace whole state, freeze, re-render (auto-run via emit)
      pushHistory();
      state = next;
      lastGood = JSON.stringify(toV1Json(state));
      render();
    },
    render,
    isPlacing: () => staff.isPlacing(),
    undo,
    redo,
  };
}
