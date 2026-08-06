/* Gaussian Lab L4 — op metadata (12 ops: whitelist subset, mirrors ir.py).
   `sweep: [min, max]` marks a real-numeric param as sweepable by /scan with
   an adaptive default range (mirrors ir.py SWEEPABLE_PARAMS); params without
   `sweep` (alpha, nmode…) are not sweepable. */
"use strict";

export const TAU = 2 * Math.PI;

export const OPS = {
  /* L5: 源重构 — tmsv 出托盘（palette:false，后端 IR 保留兼容，旧 JSON 仍可载入）;
     纠缠由 vacuum + two_mode_squeeze 门构建。 */
  vacuum: {
    label: "真空模",
    kind: "source",
    modes: 1,
    tip: "真空模：提供 nmode 个真空模式（零均值、单位协方差）",
    params: { nmode: { min: 1, max: 16, step: 1, def: 1, advanced: true } },
  },
  tmsv: {
    label: "TMSV",
    kind: "source",
    modes: 2,
    palette: false,
    tip: "TMSV：双模压缩真空，EPR 纠缠源（r 为压缩强度）",
    params: { r: { min: -3, max: 3, step: 0.01, def: 0.6, sweep: [0, 2] } },
  },
  coherent: {
    label: "相干态",
    kind: "source",
    modes: 1,
    palette: false, // L5.5: 统一为 vacuum + displace 门表达，保留定义以载入旧 JSON
    tip: "相干态：真空经位移 α 得到，经典振幅态",
    params: { alpha: { min: -5, max: 5, step: 0.05, def: 1.0 } },
  },
  squeeze: {
    label: "压缩",
    kind: "single",
    tip: "压缩：挤压正交涨落（r<0 压缩 x，r>0 压缩 p），产生低于真空噪声的涨落",
    params: {
      r: { min: -3, max: 3, step: 0.01, def: 0.4, sweep: [0, 2] },
      phi: { min: 0, max: TAU, step: 0.01, def: 0 },
    },
  },
  phase: {
    label: "相位",
    kind: "single",
    tip: "相位：对模式施加相移 φ，旋转相空间",
    params: { phi: { min: 0, max: TAU, step: 0.01, def: Math.PI / 2, sweep: [0, Math.PI] } },
  },
  fourier: {
    label: "傅里叶",
    kind: "single",
    tip: "傅里叶：90° 相空间旋转，位置 ↔ 动量互换",
    params: {},
  },
  displace: {
    label: "位移",
    kind: "single",
    tip: "位移：相空间平移 α，真空 + 位移即相干态",
    params: { alpha: { min: -5, max: 5, step: 0.05, def: 1.0 } },
  },
  loss: {
    label: "损耗",
    kind: "single",
    channel: true,
    tip: "损耗：透过率 T 的纯损耗通道（T=1 无损耗），耦合真空环境",
    params: {
      T: { min: 0.01, max: 1, step: 0.01, def: 0.8, sweep: [0, 1] },
      nbar: { min: 0, max: 5, step: 0.1, def: 0, advanced: true },
    },
  },
  amplifier: {
    label: "放大",
    kind: "single",
    channel: true,
    tip: "放大：增益 G 的相位不敏感放大（附带自发辐射噪声）",
    params: {
      G: { min: 1, max: 8, step: 0.05, def: 2, sweep: [1, 4] },
      nbar: { min: 0, max: 5, step: 0.1, def: 0, advanced: true },
    },
  },
  beamsplitter: {
    label: "分束器",
    kind: "two",
    tip: "分束器：θ 角分束耦合两模，产生干涉与纠缠",
    params: {
      theta: { min: 0, max: TAU, step: 0.01, def: Math.PI / 4, sweep: [0, Math.PI] },
      phi: { min: 0, max: TAU, step: 0.01, def: 0 },
    },
  },
  mz: {
    label: "马赫-曾德尔",
    kind: "two",
    tip: "马赫-曾德尔：两分束器夹相移，可编程干涉仪",
    params: {
      theta: { min: 0, max: Math.PI, step: 0.01, def: Math.PI / 4, sweep: [0, Math.PI] },
      phi: { min: 0, max: Math.PI, step: 0.01, def: Math.PI / 2, sweep: [0, Math.PI] },
    },
  },
  two_mode_squeeze: {
    label: "双模压缩",
    kind: "two",
    tip: "双模压缩：两模关联挤压，产生 EPR 型纠缠",
    params: { r: { min: -3, max: 3, step: 0.01, def: 0.4, sweep: [0, 2] } },
  },
  heterodyne: {
    label: "外差测量",
    kind: "single",
    measure: true,
    tip: "外差测量：投影到相干态 |β⟩，返回复振幅结果",
    params: {},
  },
  homodyne: {
    label: "零差测量",
    kind: "single",
    measure: true,
    tip: "零差测量：投影到正交分量 x_φ，返回实数结果",
    params: { phi: { min: 0, max: TAU, step: 0.01, def: 0, optional: true } },
  },
};

/** UX: palette grouping category — source / gate / channel / measure.
    null = hidden from the palette (palette:false or unknown). */
export function opGroup(op) {
  const m = OPS[op];
  if (!m || m.palette === false) return null;
  if (m.kind === "source") return "source";
  if (m.channel) return "channel";
  if (m.measure) return "measure";
  return "gate";
}

export const OP_NAMES = Object.keys(OPS);

/** Default params object for an op (advanced params included, for JSON fidelity). */
export function paramsFromOp(op) {
  if (!Object.hasOwn(OPS, op)) throw new TypeError(`Unknown op: ${op}`); // OCR guard
  const out = {};
  for (const [k, d] of Object.entries(OPS[op].params)) out[k] = d.def;
  return out;
}

/** Source modes contributed so far (vacuum nmode / coherent=1; tmsv=2 legacy). */
export function sourceModes(nodes) {
  let total = 0;
  for (const n of nodes) {
    const meta = OPS[n.op];
    if (!meta || meta.kind !== "source") continue;
    total += n.op === "vacuum" ? (n.params.nmode ?? 1) : meta.modes;
  }
  return total;
}

/* ── L5 staff ordering ─────────────────────────────── */
/** Horizontal x of a node (source = -Infinity: always leftmost). */
export function xOf(n) {
  if (OPS[n.op]?.kind === "source") return -Infinity;
  return n.ui && Number.isFinite(n.ui.x) ? n.ui.x : 0;
}

/** Sort key within one x column: mode ascending (two-mode uses modes[0]). */
export function modeKeyOf(n) {
  const meta = OPS[n.op];
  if (meta?.kind === "source") return -Infinity;
  return meta?.kind === "two" ? n.modes[0] : n.mode;
}

/** Execution order = array order = stable sort by (x, modeKey). */
export function sortNodes(nodes) {
  return [...nodes].sort((a, b) => xOf(a) - xOf(b) || modeKeyOf(a) - modeKeyOf(b));
}

/** Next id = max existing numeric id + 1 (OCR: importing n0 then adding
    must not produce a duplicate). */
function nextId(nodes) {
  let max = -1;
  for (const n of nodes) {
    const m = /^n(\d+)$/.exec(n.id);
    if (m) max = Math.max(max, Number(m[1]));
  }
  return "n" + (max + 1);
}

/** Append a node to the circuit tail (palette click fallback).
    x = max existing gate x + 1; mode defaults: 0 (single), [0,1] (two). */
export function addNode(nodes, op) {
  const node = { id: nextId(nodes), op, params: paramsFromOp(op) };
  if (OPS[op].kind === "single") node.mode = 0;
  if (OPS[op].kind === "two") node.modes = [0, 1];
  const maxX = nodes.reduce((m, n) => Math.max(m, n.ui?.x ?? -Infinity), -Infinity);
  if (OPS[op].kind !== "source") node.ui = { x: Number.isFinite(maxX) ? maxX + 1 : 0 };
  return sortNodes([...nodes, node]);
}

export function removeNode(nodes, id) {
  return nodes.filter((n) => n.id !== id);
}

/** L5.5: true if a gate occupies the cell (mode, round(x)). Sources never
    occupy cells. Two-mode gates lock both their lanes. excludeId lets a
    moving gate ignore its own cells. */
export function cellOccupied(nodes, mode, x, excludeId = null) {
  const cx = Math.round(x);
  for (const n of nodes) {
    if (n.id === excludeId) continue;
    const meta = OPS[n.op];
    if (!meta || meta.kind === "source") continue;
    if (Math.round(n.ui?.x ?? 0) !== cx) continue;
    if (meta.kind === "two") {
      if (n.modes[0] === mode || n.modes[1] === mode) return true;
    } else if (n.mode === mode) {
      return true;
    }
  }
  return false;
}

/** Place a single-mode gate on a lane at x (staff drag-drop).
    x snaps to the nearest integer column (round). */
export function placeSingle(nodes, op, mode, x) {
  const v = Number(mode);
  const p = Number(x);
  if (!Object.hasOwn(OPS, op) || OPS[op].kind !== "single") return nodes;
  if (!Number.isInteger(v) || v < 0 || !Number.isFinite(p)) return nodes;
  const node = { id: nextId(nodes), op, params: paramsFromOp(op), mode: v, ui: { x: Math.max(0, Math.round(p)) } };
  return sortNodes([...nodes, node]);
}

/** Finish a two-mode placement after the user picks lane B.
    Returns {ok:true, nodes} or {ok:false, reason}. L5.5: x rounds to the
    nearest column; the second lane's cell must be free (two-mode locks
    both cells once placed). */
export function completePlacing(nodes, placing, modeB) {
  const v = Number(modeB);
  if (!placing || !Object.hasOwn(OPS, placing.op) || OPS[placing.op].kind !== "two") {
    return { ok: false, reason: "非法放置状态" };
  }
  if (!Number.isInteger(v) || v < 0) return { ok: false, reason: "非法模式" };
  if (v === placing.modeA) return { ok: false, reason: "双模操作需要两个不同模式" };
  const cx = Math.max(0, Math.round(Number(placing.x) || 0));
  if (cellOccupied(nodes, v, cx)) return { ok: false, reason: `该格已被占用（mode ${v} @ x ${cx}）` };
  const node = {
    id: nextId(nodes), op: placing.op, params: paramsFromOp(placing.op),
    modes: [placing.modeA, v], ui: { x: cx },
  };
  return { ok: true, nodes: sortNodes([...nodes, node]) };
}

/** Drag an existing gate: change x (round to nearest column), re-sort
    (order follows (x, mode)). Caller checks cellOccupied with excludeId. */
export function moveNodeX(nodes, id, x) {
  const v = Number(x);
  if (!Number.isFinite(v)) return nodes;
  const out = nodes.map((n) => (n.id === id ? { ...n, ui: { ...n.ui, x: Math.max(0, Math.round(v)) } } : n));
  return sortNodes(out);
}

/** Source → lane mapping. Each row: {srcId, op, modeStart, modeEnd, params}.
    vacuum nmode>1 contributes n lanes (JSON-legacy); tmsv 2 lanes. */
export function sourceRows(nodes) {
  const rows = [];
  let m = 0;
  for (const n of nodes) {
    const meta = OPS[n.op];
    if (!meta || meta.kind !== "source") continue;
    const k = n.op === "vacuum" && Number.isInteger(n.params?.nmode) ? n.params.nmode : meta.modes;
    rows.push({ srcId: n.id, op: n.op, modeStart: m, modeEnd: m + k, params: n.params });
    m += k;
  }
  return rows;
}

/** Delete a source + all gates acting on its lanes (backend would reject
    out-of-range modes). Returns {nodes, removed}. */
export function removeSource(nodes, srcId) {
  const row = sourceRows(nodes).find((r) => r.srcId === srcId);
  if (!row) return { nodes, removed: [] };
  const removed = [srcId];
  const keep = [];
  for (const n of nodes) {
    const meta = OPS[n.op];
    if (n.id === srcId) continue;
    if (!meta || meta.kind === "source") { keep.push(n); continue; }
    const hits = meta.kind === "two"
      ? (n.modes[0] >= row.modeStart && n.modes[0] < row.modeEnd)
        || (n.modes[1] >= row.modeStart && n.modes[1] < row.modeEnd)
      : n.mode >= row.modeStart && n.mode < row.modeEnd;
    if (hits) removed.push(n.id); else keep.push(n);
  }
  return { nodes: keep, removed };
}

export function updateParam(node, key, value) {
  const d = OPS[node.op]?.params?.[key];
  const v = Number(value);
  if (!d || !Number.isFinite(v)) return node; // OCR: unknown key / NaN rejected
  return { ...node, params: { ...node.params, [key]: Math.min(Math.max(v, d.min), d.max) } };
}

export function updateMode(node, mode) {
  const v = Number(mode);
  if (!Number.isInteger(v) || v < 0) return node;
  return { ...node, mode: v };
}

/** Build the circuit_v0 payload the backend /run consumes (schema from L0). */
export function toCircuitJson(state) {
  return {
    schema: "circuit_v0",
    seed: Number.isInteger(state.seed) ? state.seed : 0,
    nodes: state.nodes.map((n) => {
      const out = { id: n.id, op: n.op, params: n.params };
      if (n.mode !== undefined) out.mode = n.mode;
      if (n.modes !== undefined) out.modes = n.modes;
      if (n.ui && Number.isFinite(n.ui.x)) out.ui = { x: n.ui.x }; // staff layout (backend ignores)
      return out;
    }),
    edges: [],
    view: state.view,
    ui: {},
  };
}
