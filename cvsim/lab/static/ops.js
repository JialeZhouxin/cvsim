/* Gaussian Lab L4 — op metadata (11 ops: whitelist subset, mirrors ir.py).
   `sweep: [min, max]` marks a real-numeric param as sweepable by /scan with
   an adaptive default range (mirrors ir.py SWEEPABLE_PARAMS); params without
   `sweep` (alpha, nmode…) are not sweepable. */
"use strict";

export const TAU = 2 * Math.PI;

export const OPS = {
  tmsv: {
    label: "TMSV",
    kind: "source",
    modes: 2,
    params: { r: { min: -3, max: 3, step: 0.01, def: 0.6, sweep: [0, 2] } },
  },
  coherent: {
    label: "相干态",
    kind: "source",
    modes: 1,
    params: { alpha: { min: -5, max: 5, step: 0.05, def: 1.0 } },
  },
  squeeze: {
    label: "压缩",
    kind: "single",
    params: {
      r: { min: -3, max: 3, step: 0.01, def: 0.4, sweep: [0, 2] },
      phi: { min: 0, max: TAU, step: 0.01, def: 0 },
    },
  },
  phase: {
    label: "相位",
    kind: "single",
    params: { phi: { min: 0, max: TAU, step: 0.01, def: Math.PI / 2, sweep: [0, Math.PI] } },
  },
  displace: {
    label: "位移",
    kind: "single",
    params: { alpha: { min: -5, max: 5, step: 0.05, def: 1.0 } },
  },
  loss: {
    label: "损耗",
    kind: "single",
    params: {
      T: { min: 0.01, max: 1, step: 0.01, def: 0.8, sweep: [0, 1] },
      nbar: { min: 0, max: 5, step: 0.1, def: 0, advanced: true },
    },
  },
  amplifier: {
    label: "放大",
    kind: "single",
    params: {
      G: { min: 1, max: 8, step: 0.05, def: 2, sweep: [1, 4] },
      nbar: { min: 0, max: 5, step: 0.1, def: 0, advanced: true },
    },
  },
  beamsplitter: {
    label: "分束器",
    kind: "two",
    params: {
      theta: { min: 0, max: TAU, step: 0.01, def: Math.PI / 4, sweep: [0, Math.PI] },
      phi: { min: 0, max: TAU, step: 0.01, def: 0 },
    },
  },
  mz: {
    label: "马赫-曾德尔",
    kind: "two",
    params: {
      theta: { min: 0, max: Math.PI, step: 0.01, def: Math.PI / 4, sweep: [0, Math.PI] },
      phi: { min: 0, max: Math.PI, step: 0.01, def: Math.PI / 2, sweep: [0, Math.PI] },
    },
  },
  two_mode_squeeze: {
    label: "双模压缩",
    kind: "two",
    params: { r: { min: -3, max: 3, step: 0.01, def: 0.4, sweep: [0, 2] } },
  },
  heterodyne: {
    label: "外差测量",
    kind: "single",
    params: {},
  },
  homodyne: {
    label: "零差测量",
    kind: "single",
    params: { phi: { min: 0, max: TAU, step: 0.01, def: 0, optional: true } },
  },
};

export const OP_NAMES = Object.keys(OPS);

/** Default params object for an op (advanced params included, for JSON fidelity). */
export function paramsFromOp(op) {
  if (!Object.hasOwn(OPS, op)) throw new TypeError(`Unknown op: ${op}`); // OCR guard
  const out = {};
  for (const [k, d] of Object.entries(OPS[op].params)) out[k] = d.def;
  return out;
}

/** Source modes contributed so far (tmsv=2, coherent=1). */
export function sourceModes(nodes) {
  let total = 0;
  for (const n of nodes) {
    const meta = OPS[n.op];
    if (meta && meta.kind === "source") total += meta.modes;
  }
  return total;
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

/** Append a node to the circuit list. mode defaults: 0 (single), [0,1] (two). */
export function addNode(nodes, op) {
  const node = { id: nextId(nodes), op, params: paramsFromOp(op) };
  if (OPS[op].kind === "single") node.mode = 0;
  if (OPS[op].kind === "two") node.modes = [0, 1];
  return [...nodes, node];
}

export function removeNode(nodes, id) {
  return nodes.filter((n) => n.id !== id);
}

/** Move a node up (-1) or down (+1) within bounds. Non-integer steps rejected. */
export function moveNode(nodes, id, dir) {
  const step = Number(dir);
  if (!Number.isInteger(step) || Math.abs(step) !== 1) return nodes; // OCR guard
  const i = nodes.findIndex((n) => n.id === id);
  const j = i + step;
  if (i < 0 || j < 0 || j >= nodes.length) return nodes;
  const out = [...nodes];
  [out[i], out[j]] = [out[j], out[i]];
  return out;
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
      return out;
    }),
    edges: [],
    view: state.view,
    ui: {},
  };
}
