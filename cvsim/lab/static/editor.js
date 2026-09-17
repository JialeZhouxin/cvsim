/* Gaussian Lab L2 — editor state (pure) + DOM wiring (initEditor).
   Pure helpers are ESM-exported for node --test; DOM work lives only
   inside initEditor. */
"use strict";

import { OPS, addNode, cellOccupied, completePlacing, moveNodeX, opGroup, paramsFromOp, placeSingle, removeMode, removeNode, toV1Json, updateParam } from "./ops.js";
import { dropMode, initialCacheKey, parseInitial, remapForBackend, vacuumDefault, bosonicSourceOptions } from "./initial.js";
import { opsForBackend, schemaTables } from "./schema_store.js";
import { initStaff } from "./staff.js";

/* ── state ─────────────────────────────────────────────── */
const defaultState = () => ({
  seed: 0,
  nmode: 1,            // ADR-0014: 模数唯一事实源（前端一等字段）
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
    circuit_v1 only (ADR-0011: v0 read path removed). Returns {state} or
    {error}. Unknown ops / malformed shapes are errors (frozen-graph
    policy). */
export function stateFromJson(payload) {
  if (!payload || typeof payload !== "object") return { error: "circuit 必须是对象" };
  if (payload.schema !== "circuit_v1") return { error: "schema 必须是 circuit_v1" };
  return stateFromV1(payload);
}

/** F7: backend/initial/cutoff extension fields (v1 load path; the v0
    path was removed by ADR-0011).
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
    const cutMax = tables().cutoff[1];
    const okInt = Number.isInteger(payload.cutoff) && payload.cutoff >= 1
      && payload.cutoff <= cutMax;
    const okArr = Array.isArray(payload.cutoff) && payload.cutoff.length === nmode
      && payload.cutoff.every((c) => Number.isInteger(c) && c >= 1 && c <= cutMax);
    if (okInt) {
      cutoffs = Array(nmode).fill(payload.cutoff);
    } else if (okArr) {
      cutoffs = [...payload.cutoff];
    } else {
      return { error: `cutoff 必须在 [1, ${cutMax}]（整数或长度为 ${nmode} 的数组）` };
    }
  }
  return { backend, initial, cutoffs };
}

//: v1 IR op → UI op (票3: 改查 schema uiName 派生表；未注入 = 回退常量).
const V1_TO_UI_OP = {
  measure_homodyne: "homodyne",
  measure_heterodyne: "heterodyne",
};

//: 票3: editor 层 schema 注入（app.js init() 成功后调用一次）。
//: 消费 extensions (view/cutoff/shots 边界) + ops[].uiName 改名派生。
let EDITOR_SCHEMA = null;
let EDITOR_DERIVED = null;
export function setEditorSchema(doc) {
  if (!doc || typeof doc !== "object" || !doc.ops || !doc.extensions) {
    throw new TypeError("/schema 载荷非法（缺 ops/extensions）");
  }
  EDITOR_SCHEMA = doc;
  EDITOR_DERIVED = deriveEditorTables(doc);
}
export function currentEditorSchema() {
  return EDITOR_SCHEMA;
}

/** schema → editor 校验表（纯函数，票3）。view/seed/cutoff 边界 + 改名。 */
export function deriveEditorTables(schema) {
  const ext = schema.extensions;
  const irToUi = {};
  for (const [ir, entry] of Object.entries(schema.ops)) {
    if (entry.uiName) irToUi[ir] = entry.uiName;
  }
  // UI键→IR名 查找表（pnames 消费形；与回退常量同形）。schema 无参数级
  // uiName 字段：phase theta↔phi 规则定案于 spec；其余同名直译（无键）。
  // 两张表（票3）：v1ToUiParam = UI键→IR名 改名；fockV1ToUiParam = fock
  // 表示级差异（loss T→eta/nbar 丢）——schema 单份 meta 表达不了（meta =
  // 首白名单包 = gaussian 视角），镜像 fock ir_schema 表示级事实，常量
  // 保留（票3 PRD「2 张保留」；票4 或 schema 扩 per-backend meta 时再收编）。
  // gaussian 路径只读前者（drops 不得外溢）。
  // 注：squeeze.phi 曾经也丢（fock 仅实 r），09-14-fock-squeeze-phi 已补——
  // 现在 fock IR 带 phi（与 FockState.squeezed 同约定）。
  const v1ToUiParam = schema.ops.phase ? { phase: { phi: "theta" } } : {};
  const fockV1ToUiParam = {
    loss: { T: "eta", nbar: null },
  };
  // /schema 的 cutoff 是 **{min,max} 对象**（schema.py ``_EXTENSIONS``，
  // test_lab_schema.py 锁定），而 editor 内部要 [min,max] 二元组
  // （``cutMax = tables().cutoff[1]``）。不归一化 → cutMax=undefined →
  // 任何带显式 cutoff 的 fock JSON 都被拒。
  const cutExt = ext.cutoff ?? { min: 1, max: 30 };
  const cutoff = Array.isArray(cutExt) ? cutExt : [cutExt.min, cutExt.max];
  return {
    viewN: ext.view?.n ?? [2, 512],
    viewLimMax: ext.view?.lim_max ?? 50,
    viewLimMinExcl: ext.view?.lim_min_exclusive ?? 0,
    cutoff,
    shots: ext.shots ?? [0, 100000],
    irToUi,
    v1ToUiParam,
    fockV1ToUiParam,
  };
}

/** 生效表（schema 注入后派生，未注入 = 旧常量回退，仅 node --test 旧路径）。 */
//: UI param → v1 IR param (inverse of UI_TO_V1_PARAM in ops.js).
const V1_TO_UI_PARAM = { phase: { phi: "theta" } };
//: Fock IR param → UI param (inverse of FOCK_UI_TO_V1_PARAM in ops.js;
//  key = UI param, value = fock IR param).
const FOCK_V1_TO_UI_PARAM = { loss: { T: "eta", nbar: null } };

function tables() {
  if (EDITOR_DERIVED) return EDITOR_DERIVED;
  const s = schemaTables();
  if (s) {
    return {
      viewN: [2, 512],
      viewLimMax: 50,
      viewLimMinExcl: 0,
      cutoff: [1, 30],
      shots: [0, 100000],
      irToUi: { ...s.irToUiOp },
      v1ToUiParam: { ...s.v1ToUiParam },
      fockV1ToUiParam: { ...s.fockV1ToUiParam },
    };
  }
  return {
    viewN: [2, 512],
    viewLimMax: 50,
    viewLimMinExcl: 0,
    cutoff: [1, 30],
    shots: [0, 100000],
    irToUi: { ...V1_TO_UI_OP },
    v1ToUiParam: { ...V1_TO_UI_PARAM },
    fockV1ToUiParam: { ...FOCK_V1_TO_UI_PARAM },
  };
}

function nextFreeV1Id(i, seenIds) {
  // auto ids must never collide with explicit ids (n0 + explicit "n0")
  let id = `n${i}`;
  for (let k = 1; seenIds.has(id); k++) id = `n${i}_${k}`;
  return id;
}

/** circuit_v1 → graph model (inverse of toV1Json). v1 has no source
    concept: the top-level `nmode` is the mode count (ADR-0014); ops map 1:1
    to UI nodes; phase ``theta`` maps back to the UI ``phi`` param.
    Core-only ops (cz/cx/interferometer/…) are rejected — same whitelist
    the backend load enforces. */
function stateFromV1(payload) {
  if (!Array.isArray(payload.ops)) return { error: "ops 必须是数组" };
  if (!Number.isInteger(payload.nmode) || payload.nmode < 1) {
    return { error: "nmode 必须是不小于 1 的整数" };
  }
  const seed = payload.seed === undefined ? 0 : payload.seed;
  // 票3 review F4：seed 无上界（server ir.py 只查非负 int；shots 是采样
  // 次数非 seed 域）——不耦合 extensions.shots。
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
    const uiOp = tables().irToUi[o.op] || o.op;
    if (!Object.hasOwn(OPS, uiOp)) return { error: `ops[${i}]: op ${o.op} 不在 Lab 白名单` };
    const meta = OPS[uiOp];
    const id = o.id !== undefined ? o.id : nextFreeV1Id(i, assigned);
    if (typeof id !== "string" || id.length === 0 || (assigned.has(id) && id !== o.id)) {
      return { error: `ops[${i}]: id 必须是非空唯一字符串` };
    }
    assigned.add(id);
    const node = { id, op: uiOp, params: {} };
    const isFock = payload.backend === "fock";
    const T = tables();
    const pnames = isFock
      ? { ...(T.v1ToUiParam[uiOp] || {}), ...(T.fockV1ToUiParam[uiOp] || {}) }
      : (T.v1ToUiParam[uiOp] || {});
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
      const irKey = pnames[k] !== undefined ? pnames[k] : k;
      // fock drop-table (null value): param absent from the fock IR
      // (loss nbar) — optional with base default
      const droppedOnFock = isFock && pnames[k] === null;
      const v = droppedOnFock ? undefined : params[irKey];
      // fock 作用域的可选参数：存量档案不带 squeeze.phi（fock 曾只吃实 r，
      // phi 进过 drop 表），必填会让它们 422。**只对 fock 生效** —— 
      // gaussian/bosonic 的 phi 仍必填（不改这两个后端的契约）。
      const optionalOnFock = (isFock && uiOp === "squeeze" && k === "phi") || droppedOnFock;
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
  const rawView = payload.view && typeof payload.view === "object" ? payload.view : {};
  if (!Number.isInteger(rawView.wigner_mode) || rawView.wigner_mode < 0) {
    return { error: "view.wigner_mode 必须是非负整数" };
  }
  const T = tables();
  if (typeof rawView.lim !== "number" || !Number.isFinite(rawView.lim)
      || rawView.lim <= T.viewLimMinExcl || rawView.lim > T.viewLimMax) {
    return { error: `view.lim 必须是 (${T.viewLimMinExcl}, ${T.viewLimMax}] 的数值` };
  }
  if (typeof rawView.n !== "number" || !Number.isFinite(rawView.n)
      || rawView.n < T.viewN[0] || rawView.n > T.viewN[1]) {
    return { error: `view.n 必须在 [${T.viewN[0]}, ${T.viewN[1]}]` };
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
  return { state: { seed, nmode: payload.nmode, nodes, view, ui: {}, ...ext } };
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

  function emit(circuitJson) {
    hooks.onRun(circuitJson);
  }

  /* C5 R2: 接收**已算好的** doc，而不是自己再算一次。原先 syncChrome() 与 onParam()
     都在同一次 mutation 里调 toV1Json 两次（renderJson 一次、emit 一次），而
     toV1Json 会遍历全部节点并重建 ops 数组。把参数改成必填后，"同一次 mutation
     算两遍"在结构上不可能再发生——两个调用点都必须显式提供同一个对象。
     形态差异仍保持：这里 stringify 成 2 空格缩进字符串给 #json-input，
     emit 传的是**对象**本身（hooks.onRun 的契约）。 */
  function renderJson(doc) {
    suppress = true;
    dom.json.value = JSON.stringify(doc, null, 2);
    suppress = false;
  }

  /** 非 staff / 非 palette 的副作用集合：JSON 文本、fock 控件、onState 钩子、
      undo/redo 按钮态、debounced emit。`render()` 与滑条/视图的轻量路径共用它，
      故「轻量路径漏了某个副作用」在结构上不可能发生——新增副作用只需改这一处。
      注意 undo/redo 的 disabled 也在这里（lab_undo_probe.mjs 直接断言该状态）。
      C5 R2: toV1Json 只算一次，JSON 文本与 emit 共用同一个 doc 对象。 */
  function syncChrome() {
    const doc = toV1Json(state);
    renderJson(doc);
    renderFockControls();
    hooks.onState(state);
    if (dom.undoBtn) dom.undoBtn.disabled = !hist.canUndo();
    if (dom.redoBtn) dom.redoBtn.disabled = !hist.canRedo();
    if (!suppressEmit) emit(doc);
  }

  function render() {
    staff.render();
    renderPalette();
    syncChrome();
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
      if (n && meta) {
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
      pushHistory();
      state = { ...state, nodes: removeNode(state.nodes, id) };
      render();
    },
    /* ADR-0014: 逐模删除 — 级联删该模上的门 + 上方模索引下移。
       per-mode 数组必须先按**索引**删除（dropMode），再补齐（padTo/remap 只做截尾/补位）。 */
    onDeleteMode: (mode) => {
      if (state.nmode <= 1) {
        hooks.onStatus("至少保留一个模式", false);
        return;
      }
      pushHistory();
      const nmode = state.nmode - 1;
      // joint_modes 是**模索引**：命中被删模或删后 < 2 模（无对）→ 清空回退默认；
      // 否则 > mode 的索引整体 −1（不重编号就会指向别的模）。
      const jm0 = state.view.joint_modes;
      const jointModes = !Array.isArray(jm0) || nmode < 2 || jm0.includes(mode)
        ? null
        : jm0.map((m) => (m > mode ? m - 1 : m));
      state = { ...state,
        nodes: removeMode(state.nodes, mode),
        nmode,
        initial: remapForBackend(state.backend, state.backend,
          dropMode(state.initial, mode), nmode).initial,
        cutoffs: padTo(dropMode(state.cutoffs, mode), nmode, 10),
        view: { ...state.view,
          wigner_mode: Math.max(0, Math.min(state.view.wigner_mode, nmode - 1)),
          joint_modes: jointModes } };
      render();
    },
    onParam: (id, key, value) => {
      pushHistory(); // one entry per slider step; createHistory(50) caps growth (ponytail: coalesce consecutive slider drags when the history gets noisy)
      state = { ...state, nodes: state.nodes.map((x) => (x.id === id ? updateParam(x, key, value) : x)) };
      /* C5 R2: 同一次 mutation 只算一次 toV1Json（原先 renderJson + emit 各算一次）。
         本路径有意**不**改走 syncChrome()：那样会顺带改动本路径的副作用集合
         （新增 renderFockControls 与 undo/redo disabled 的写入），而 C5 的范围只是
         「同一状态算两遍」。副作用集合与改动前逐项一致，只少算一次 doc。
         （已知且**未改动**：本路径不写 undo/redo 的 disabled —— 实测拖参数滑条后
         undo 按钮会保持 disabled。该缺陷**改动前就存在**，属「轻量路径漏写副作用」
         的另一类问题，记录在 review §9.1，需独立任务，不在 C5 范围内。） */
      const doc = toV1Json(state);
      renderJson(doc);
      hooks.onState(state);
      emit(doc);
    },
    onPickSweep: (id) => hooks.onPickSweep?.(id),
    onStatus: (msg, ok) => hooks.onStatus(msg, ok),
    /* #13: drag window — suppress per-move emits; drop/cancel emits once */
    onDragStart: () => { suppressEmit = true; },
    onDragEnd: () => {
      suppressEmit = false;
      emit(toV1Json(state));
    },
  });

  /* palette: DnD + click fallback, grouped by category（palette:false 的 op 不出托盘）。
     F7: per-backend 过滤 — OPS.backends 不含当前 backend 的 op 不出托盘。 */
  const PALETTE_GROUPS = [
    ["gate", "门"],
    ["channel", "通道"],
    ["measure", "测量"],
  ];
  /* C1 R6: 托盘内容只由 backend 决定（opsForBackend(state.backend)），故后端未变
     则重建是纯浪费——实测 setView / cutoff 滑条路径上托盘每次都被整个重建。
     键写成 dataset 而非闭包变量：托盘 DOM 与键同源，若外部换掉 #palette 内容，
     键不会撒谎。**不是裸早退**：与 renderFockControls 的同名先例（editor.js
     `initialInputs.dataset.nmode`）一样，先确认没有需要补的副作用才发现可以退。
     这里托盘是无状态纯列表（无输入框、无焦点值），故无需补写——已逐项确认。 */
  function renderPalette() {
    if (dom.palette.dataset.backend === state.backend) return;
    dom.palette.dataset.backend = state.backend;
    dom.palette.replaceChildren();
    for (const [gid, title] of PALETTE_GROUPS) {
      const ops = opsForBackend(state.backend).filter((op) => opGroup(op) === gid);
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
          if (meta.kind === "two" && state.nmode < 2) {
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
          emit(toV1Json(state)); // drop/取消后单次 emit
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
    let view = state.view;
    let cutoffs = state.cutoffs;
    // 模数与源无关（ADR-0014）：不再造源节点
    if (next === "fock") {
      const nm = state.nmode;
      cutoffs = padTo(cutoffs, nm, 10);
      if (nm >= 2 && !Array.isArray(view.joint_modes)) {
        view = { ...view, joint_modes: [0, 1] }; // HOM 剧本：joint 卡默认开
      }
    }
    // B6/F7: initial 跨后端语义重映射（单点在 initial.js）。真空对应项保留
    // （fock 0 ↔ bosonic null），非真空项重置 + UI 提示，永不静默截断。
    const nm = state.nmode;
    const remap = remapForBackend(state.backend, next, state.initial, nm);
    if (remap.reset > 0) {
      hooks.onStatus(`${remap.reset} 项初始态因后端切换被重置为真空`, false);
    }
    state = { ...state, backend: next, view, initial: remap.initial, cutoffs };
    render();
  }

  function addMode() {
    pushHistory();
    const nm = state.nmode + 1;
    // B6/F7: initial 补长也走单点重映射（from === to 同后端：原值保留 + 真空补位）
    const remap = remapForBackend(state.backend, state.backend, state.initial, nm);
    state = { ...state, nmode: nm,
      initial: remap.initial, cutoffs: padTo(state.cutoffs, nm, 10) };
    render();
  }

  function setInitial(i, v) {
    const nm = state.nmode;
    const fill = vacuumDefault(state.backend);
    const next = Array(nm).fill(fill).map((_, k) =>
      (state.initial ? state.initial[k] : fill));
    next[i] = v;
    pushHistory();
    state = { ...state, initial: next };
    // 初始态也进模行标签（`mode m · |v⟩`），故同样定点补标签而非重建 staff
    if (!staff.syncLabels()) render();
    else syncChrome();
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
      for (const [val, text] of bosonicSourceOptions()) {
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

  /* R7: per-backend 初始态输入配置表 — 差异知识单点（NOTES.md 债务收口）。
     int = fock 光子数输入（cutoff 上限联动，syncFockInputValues）；
     enum = bosonic 源名下拉（renderBosonicInitial）；null = 无 initial
     字段（gaussian——卡片隐藏）。新后端加 initial 类型 = 添一行 + render* 分支。 */
  const INITIAL_INPUT_KIND = { fock: "int", bosonic: "enum" };

  function renderFockControls() {
    const kind = INITIAL_INPUT_KIND[state.backend];
    // ADR-0014: ＋模 恒可见（gaussian 无源节点后，这是唯一的加模入口）
    if (!kind) { // 无 initial 字段（gaussian）：卡片隐藏
      if (dom.backendSelect) dom.backendSelect.value = state.backend;
      if (dom.initialCard) { dom.initialCard.hidden = true; dom.initialInputs.dataset.nmode = ""; dom.initialInputs.replaceChildren(); }
      return;
    }
    if (dom.backendSelect) dom.backendSelect.value = state.backend;
    if (!dom.initialCard) return;
    dom.initialCard.hidden = false;
    const nm = state.nmode;
    // 缓存键含 backend（initialCacheKey）：切换后端必重建控件，
    // 防止 bosonic 下残留 fock 数字输入框（模数不变早退 bug）。
    if (dom.initialInputs.dataset.nmode === initialCacheKey(state.backend, nm)) {
      // 同键仍需同步 fock 数字输入值（cutoff 变化等场景）
      if (kind === "int") syncFockInputValues();
      return;
    }
    if (kind === "enum") { renderBosonicInitial(nm); return; }
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
      // 只影响 view（wigner_mode / joint_modes / lim / n）：staff 几何与托盘与
      // view 无关，故跳过两次全量重建——只走 syncChrome（其中 renderFockControls
      // 会同步 joint 选择与数字输入，故 joint_modes 也在这条路径上正确落地）。
      state = { ...state, view: { ...state.view, ...patch } };
      syncChrome();
    },
    setCircuit: (patch) => {
      // F7: cutoff/initial patches from the Fock guard panel.
      // 这条路径只改 cutoffs / initial，不改 nodes/nmode → staff 树无需重建；
      // 但 modeLabel 内嵌 initial 的光子数（clampInitial 把 initial 夹到
      // cutoff-1），故标签必须定点补写，否则屏幕停在旧值。
      pushHistory();
      state = { ...state, ...patch };
      // 防御：patch 若触及结构键，轻量路径不再成立（门几何 / 托盘都可能变）
      const structural = "nodes" in patch || "nmode" in patch || "backend" in patch;
      if (structural || !staff.syncLabels()) render(); // 结构变了 → 完整重建
      else syncChrome();
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
