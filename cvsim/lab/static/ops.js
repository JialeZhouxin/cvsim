/* Gaussian Lab F7 — op metadata (whitelist subset, mirrors ir.py).
   `sweep: [min, max]` marks a real-numeric param as sweepable by /scan with
   an adaptive default range (mirrors ir.py SWEEPABLE_PARAMS); params without
   `sweep` (alpha, nmode…) are not sweepable.
   `backends: ["gaussian"|"fock"]` = per-backend palette table (F7 双后端;
   mirrors ir.py LAB_WHITELIST / FOCK_WHITELIST). `string: true` params
   (measure result names) never get sliders — JSON/id-managed. */
"use strict";

export const TAU = 2 * Math.PI;

export const OPS = {
  /* L5: 源重构 — tmsv 出托盘（palette:false，后端 IR 保留兼容，旧 JSON 仍可载入）;
     纠缠由 vacuum + two_mode_squeeze 门构建。 */
  vacuum: {
    label: "真空模",
    kind: "source",
    modes: 1,
    backends: ["gaussian"], // Fock 无源托盘：nmode 由「＋模」按钮管理（内部仍用 vacuum 计模）
    tip: "真空模：提供 nmode 个真空模式（零均值、单位协方差）",
    params: { nmode: { min: 1, max: 16, step: 1, def: 1, advanced: true } },
  },
  tmsv: {
    label: "TMSV",
    kind: "source",
    modes: 2,
    palette: false,
    backends: ["gaussian"],
    tip: "TMSV：双模压缩真空，EPR 纠缠源（r 为压缩强度）",
    params: { r: { min: -3, max: 3, step: 0.01, def: 0.6, sweep: [0, 2] } },
  },
  coherent: {
    label: "相干态",
    kind: "source",
    modes: 1,
    palette: false, // L5.5: 统一为 vacuum + displace 门表达，保留定义以载入旧 JSON
    backends: ["gaussian"],
    tip: "相干态：真空经位移 α 得到，经典振幅态",
    params: { alpha: { min: -5, max: 5, step: 0.05, def: 1.0 } },
  },
  squeeze: {
    label: "压缩",
    kind: "single",
    backends: ["gaussian", "fock", "bosonic"],
    tip: "压缩：挤压正交涨落（r<0 压缩 x，r>0 压缩 p），产生低于真空噪声的涨落",
    params: {
      r: { min: -3, max: 3, step: 0.01, def: 0.4, sweep: [0, 2] },
      phi: { min: 0, max: TAU, step: 0.01, def: 0 },
    },
  },
  phase: {
    label: "相位",
    kind: "single",
    backends: ["gaussian", "fock", "bosonic"],
    tip: "相位：对模式施加相移 φ，旋转相空间",
    params: { phi: { min: 0, max: TAU, step: 0.01, def: Math.PI / 2, sweep: [0, Math.PI] } },
  },
  fourier: {
    label: "傅里叶",
    kind: "single",
    backends: ["gaussian", "bosonic"], // gaussian 名 + b6 门全集
    tip: "傅里叶：90° 相空间旋转，位置 ↔ 动量互换",
    params: {},
  },
  displace: {
    label: "位移",
    kind: "single",
    backends: ["gaussian", "fock", "bosonic"],
    tip: "位移：相空间平移 α，真空 + 位移即相干态",
    params: { alpha: { min: -5, max: 5, step: 0.05, def: 1.0 } },
  },
  loss: {
    label: "损耗",
    kind: "single",
    channel: true,
    backends: ["gaussian", "fock", "bosonic"],
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
    backends: ["gaussian", "fock", "bosonic"],
    tip: "放大：增益 G 的相位不敏感放大（附带自发辐射噪声）",
    params: {
      G: { min: 1, max: 8, step: 0.05, def: 2, sweep: [1, 4] },
      nbar: { min: 0, max: 5, step: 0.1, def: 0, advanced: true },
    },
  },
  beamsplitter: {
    label: "分束器",
    kind: "two",
    backends: ["gaussian", "fock", "bosonic"],
    tip: "分束器：θ 角分束耦合两模，产生干涉与纠缠",
    params: {
      theta: { min: 0, max: TAU, step: 0.01, def: Math.PI / 4, sweep: [0, Math.PI] },
      phi: { min: 0, max: TAU, step: 0.01, def: 0 },
    },
  },
  mz: {
    label: "马赫-曾德尔",
    kind: "two",
    backends: ["gaussian"], // gaussian 组合名 mz；fock 用 mach_zehnder（IR 名不同）
    tip: "马赫-曾德尔：两分束器夹相移，可编程干涉仪",
    params: {
      theta: { min: 0, max: Math.PI, step: 0.01, def: Math.PI / 4, sweep: [0, Math.PI] },
      phi: { min: 0, max: Math.PI, step: 0.01, def: Math.PI / 2, sweep: [0, Math.PI] },
    },
  },
  two_mode_squeeze: {
    label: "双模压缩",
    kind: "two",
    backends: ["gaussian", "fock", "bosonic"],
    tip: "双模压缩：两模关联挤压，产生 EPR 型纠缠",
    params: { r: { min: -3, max: 3, step: 0.01, def: 0.4, sweep: [0, 2] } },
  },
  heterodyne: {
    label: "外差测量",
    kind: "single",
    measure: true,
    backends: ["gaussian", "fock", "bosonic"],
    tip: "外差测量：投影到相干态 |β⟩，返回复振幅结果",
    params: { name: { string: true, def: "", optional: true } },
  },
  homodyne: {
    label: "零差测量",
    kind: "single",
    measure: true,
    backends: ["gaussian", "fock", "bosonic"],
    tip: "零差测量：投影到正交分量 x_φ，返回实数结果；name 供后续 feedforward $ref 引用",
    params: {
      phi: { min: 0, max: TAU, step: 0.01, def: 0, optional: true },
      name: { string: true, def: "", optional: true },
    },
  },
  /* ── Fock-only (F7, mirrors ir.py FOCK_WHITELIST) ─────────── */
  kerr: {
    label: "Kerr",
    kind: "single",
    backends: ["fock"],
    tip: "Kerr：非线性相位 χ·n²（光子数依赖相位），猫态协议 displace+Kerr(π/2) 的关键门",
    params: { chi: { min: 0, max: TAU, step: 0.01, def: Math.PI / 2 } },
  },
  cz: {
    label: "CZ",
    kind: "two",
    backends: ["fock", "bosonic"],
    tip: "CZ：受控相位门（Fock qudit 编码），weight 为耦合强度",
    params: { weight: { min: -2, max: 2, step: 0.01, def: 1 } },
  },
  cx: {
    label: "CX",
    kind: "two",
    backends: ["fock", "bosonic"],
    tip: "CX：受控 X 门（Fock qudit 编码），weight 为耦合强度",
    params: { weight: { min: -2, max: 2, step: 0.01, def: 1 } },
  },
  mach_zehnder: {
    label: "马赫-曾德尔",
    kind: "two",
    backends: ["fock", "bosonic"],
    tip: "马赫-曾德尔：两分束器夹相移，可编程干涉仪（Fock IR 名 mach_zehnder）",
    params: {
      theta: { min: 0, max: Math.PI, step: 0.01, def: Math.PI / 4 },
      phi: { min: 0, max: Math.PI, step: 0.01, def: Math.PI / 2 },
    },
  },
  phase_noise: {
    label: "相位噪声",
    kind: "single",
    channel: true,
    backends: ["fock", "bosonic"],
    tip: "相位噪声：σ 强度的高斯相位噪声通道（转密度态）",
    params: { sigma: { min: 0, max: 5, step: 0.01, def: 0 } },
  },
  measure_pnr: {
    label: "PNR 测量",
    kind: "single",
    measure: true,
    backends: ["fock"],
    tip: "光子数分辨测量：投影到光子数基，按序坍缩并移除被测模",
    params: { name: { string: true, def: "", optional: true } },
  },
  /* ── Bosonic-only (B6, mirrors ir.py BOSONIC_WHITELIST) ───── */
  interferometer: {
    label: "干涉仪",
    kind: "two",
    palette: false, // 矩阵参数 JSON-only（类比 Fock apply_unitary defer）
    backends: ["bosonic"],
    tip: "干涉仪：任意酉 U 矩阵（JSON-only，面板不编辑）",
    params: {},
  },
  gaussian_channel: {
    label: "高斯通道",
    kind: "single",
    channel: true,
    palette: false, // X/Y/d 矩阵参数 JSON-only
    backends: ["bosonic"],
    tip: "高斯通道：一般 (X,Y,d) CPTP 通道（JSON-only，面板不编辑）",
    params: {},
  },
  measure_threshold: {
    label: "阈值测量",
    kind: "single",
    measure: true,
    backends: ["bosonic"],
    tip: "阈值测量：单光子存在探测（on/off），返回 0/1，不删模",
    params: { name: { string: true, def: "", optional: true } },
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

/** Palette ops for one representation backend (F7). Ops whose `backends`
    list includes ``backend``; palette:false ops are still excluded by
    opGroup at render time. */
export function backendOps(backend) {
  return Object.keys(OPS).filter((op) => OPS[op].backends.includes(backend));
}

/** Default params object for an op (advanced params included, for JSON fidelity). */
export function paramsFromOp(op) {
  if (!Object.hasOwn(OPS, op)) throw new TypeError(`Unknown op: ${op}`); // OCR guard
  const out = {};
  for (const [k, d] of Object.entries(OPS[op].params)) out[k] = d.def;
  return out;
}

/** F7: per-backend palette table — OPS key lists (not the metadata map).
    Mirrors ir.py FOCK_WHITELIST (no interferometer/apply_unitary/apply_kraus). */
export const FOCK_PALETTE = Object.freeze(
  ["displace", "phase", "squeeze", "kerr", "beamsplitter",
   "two_mode_squeeze", "mach_zehnder", "cz", "cx",
   "loss", "amplifier", "phase_noise",
   "measure_pnr", "homodyne", "heterodyne"].sort()
);
export const GAUSSIAN_PALETTE = Object.freeze(
  ["vacuum", "tmsv", "coherent", "squeeze", "phase", "fourier",
   "displace", "loss", "amplifier", "beamsplitter", "mz",
   "two_mode_squeeze", "heterodyne", "homodyne"].sort()
);

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
  if (d?.string) return node; // F7: result names are id-managed, never slider-edited
  const v = Number(value);
  if (!d || !Number.isFinite(v)) return node; // OCR: unknown key / NaN rejected
  return { ...node, params: { ...node.params, [key]: Math.min(Math.max(v, d.min), d.max) } };
}

export function updateMode(node, mode) {
  const v = Number(mode);
  if (!Number.isInteger(v) || v < 0) return node;
  return { ...node, mode: v };
}

//: UI op names → circuit_v1 IR names (mirror of cvsim.lab.ir V0_TO_V1_OP).
const UI_TO_V1_OP = {
  homodyne: "measure_homodyne",
  heterodyne: "measure_heterodyne",
};
//: v1 IR param name for phase is ``theta`` (core builder 1:1, ADR-0003 #3).
const UI_TO_V1_PARAM = { phase: { phi: "theta" } };
//: Fock IR param mapping (fock core speaks eta for loss; squeeze has only r).
//  keyed by v1 op name; null value = param dropped on the fock path.
const FOCK_UI_TO_V1_PARAM = {
  loss: { T: "eta", nbar: null }, // fock loss is pure (no thermal nbar)
  squeeze: { phi: null },          // fock squeeze has only r
};

/** Build the circuit_v1 payload the backend consumes (schema from ADR-0003).
    Sources are expanded (vacuum counts nmode; tmsv → two_mode_squeeze;
    coherent → displace); array order = execution order; measured-mode
    removal semantics live on the backend. */
export function toV1Json(state) {
  const ops = [];
  const staff = {}; // UI extension: gate layout columns (core ignores ui)
  let nmode = 0;
  for (const n of state.nodes) {
    const meta = OPS[n.op];
    if (meta && meta.kind === "source") {
      if (n.op === "vacuum") {
        nmode += Math.max(1, Number(n.params.nmode) || 1);
      } else if (n.op === "tmsv") {
        ops.push({ id: n.id, op: "two_mode_squeeze",
                   modes: [nmode, nmode + 1], params: { r: Number(n.params.r) || 0 } });
        nmode += 2;
      } else { // coherent → displace (L5.5: source replaced by gate expression)
        const a = n.params.alpha;
        const alpha = Array.isArray(a) ? a.map(Number)
                                       : [Number(a) || 0, 0];
        ops.push({ id: n.id, op: "displace", modes: [nmode], params: { alpha } });
        nmode += 1;
      }
      continue;
    }
    const out = { id: n.id, op: UI_TO_V1_OP[n.op] || n.op, params: {} };
    const pnames = state.backend === "fock"
      ? { ...(UI_TO_V1_PARAM[out.op] || {}), ...(FOCK_UI_TO_V1_PARAM[out.op] || {}) }
      : (UI_TO_V1_PARAM[out.op] || {});
    for (const [k, v] of Object.entries(n.params)) {
      const pk = pnames[k];
      if (pk === null) continue; // fock: param absent from the fock IR (loss nbar / squeeze phi)
      out.params[pk !== undefined ? pk : k] = v;
    }
    // F7: v1 measure ops carry a result name (Fock IR requires it; Gaussian
    // accepts it). Keep an explicitly loaded name, else the node id.
    if (out.op.startsWith("measure_")) {
      const nm = n.params && typeof n.params.name === "string" && n.params.name.length
        ? n.params.name : n.id;
      out.params.name = nm;
    }
    out.modes = n.modes !== undefined ? n.modes : [n.mode];
    ops.push(out);
    if (n.ui && Number.isFinite(n.ui.x)) staff[out.id] = n.ui.x; // staff layout
  }
  const outDoc = {
    schema: "circuit_v1",
    nmode,
    seed: Number.isInteger(state.seed) ? state.seed : 0,
    ops,
    view: {},
    ui: Object.keys(staff).length ? { staff } : {},
  };
  // F7 extensions: backend 缺省 gaussian（不写 = 旧文件字节不变）；
  // initial 非全零才写；cutoff 非默认（全 10）才写，均匀写 int 否则 list。
  if (state.backend === "fock") outDoc.backend = "fock";
  if (state.backend === "bosonic") outDoc.backend = "bosonic";
  // B6: bosonic per-mode 态名（非全真空才写；缺省不写 = 真空）
  if (state.backend === "bosonic" && Array.isArray(state.initial)
      && state.initial.slice(0, nmode).some((v) => v !== null)) {
    outDoc.initial = state.initial.slice(0, nmode);
  }
  const v = state.view && typeof state.view === "object" ? state.view : {};
  outDoc.view = { wigner_mode: v.wigner_mode, lim: v.lim, n: v.n };
  if (Array.isArray(v.joint_modes) && v.joint_modes.length === 2) {
    outDoc.view.joint_modes = v.joint_modes;
  }
  if (state.backend === "fock" && Array.isArray(state.initial)
      && state.initial.some((n) => n !== 0)) {
    outDoc.initial = state.initial.slice(0, nmode);
  }
  if (state.backend === "fock" && Array.isArray(state.cutoffs)) {
    const cut = state.cutoffs.slice(0, nmode);
    if (cut.some((c) => c !== 10)) {
      outDoc.cutoff = cut.every((c) => c === cut[0]) ? cut[0] : cut;
    }
  }
  return outDoc;
}
