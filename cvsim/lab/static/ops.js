/* Gaussian Lab L2 — op metadata (8 ops: whitelist subset, mirrors ir.py). */
"use strict";

export const TAU = 2 * Math.PI;

export const OPS = {
  tmsv: {
    label: "TMSV",
    kind: "source",
    modes: 2,
    params: { r: { min: -3, max: 3, step: 0.01, def: 0.6 } },
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
      r: { min: -3, max: 3, step: 0.01, def: 0.4 },
      phi: { min: 0, max: TAU, step: 0.01, def: 0 },
    },
  },
  phase: {
    label: "相位",
    kind: "single",
    params: { phi: { min: 0, max: TAU, step: 0.01, def: Math.PI / 2 } },
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
      T: { min: 0.01, max: 1, step: 0.01, def: 0.8 },
      nbar: { min: 0, max: 5, step: 0.1, def: 0, advanced: true },
    },
  },
  beamsplitter: {
    label: "分束器",
    kind: "two",
    params: {
      theta: { min: 0, max: TAU, step: 0.01, def: Math.PI / 4 },
      phi: { min: 0, max: TAU, step: 0.01, def: 0 },
    },
  },
  heterodyne: {
    label: "外差测量",
    kind: "single",
    params: {},
  },
};

export const OP_NAMES = Object.keys(OPS);

/** Default params object for an op (advanced params included, for JSON fidelity). */
export function paramsFromOp(op) {
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

let _seq = 0;
function nextId() {
  return "n" + _seq++;
}

/** Append a node to the circuit list. mode defaults: 0 (single), [0,1] (two). */
export function addNode(nodes, op) {
  const node = { id: nextId(), op, params: paramsFromOp(op) };
  if (OPS[op].kind === "single") node.mode = 0;
  if (OPS[op].kind === "two") node.modes = [0, 1];
  return [...nodes, node];
}

export function removeNode(nodes, id) {
  return nodes.filter((n) => n.id !== id);
}

/** Move a node up (-1) or down (+1) within bounds. */
export function moveNode(nodes, id, dir) {
  const i = nodes.findIndex((n) => n.id === id);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= nodes.length) return nodes;
  const out = [...nodes];
  [out[i], out[j]] = [out[j], out[i]];
  return out;
}

export function updateParam(node, key, value) {
  return { ...node, params: { ...node.params, [key]: value } };
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
    seed: 0,
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
