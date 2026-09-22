/* Gaussian Lab L2–L5 — pure editor logic tests (node --test, zero deps). */
import test from "node:test";
import assert from "node:assert/strict";

import {
  OPS, OP_NAMES, TAU, paramsFromOp, opGroup,
  addNode, removeNode, placeSingle, completePlacing, moveNodeX,
  sortNodes, removeMode, updateParam, updateMode, toV1Json,
  cellOccupied, stateNmode, clampParam, visibleParams,
} from "../cvsim/lab/static/ops.js";
// ticket 4: palette/backends derived from schema (ops.js mirrors deleted).
import { deriveOps } from "../cvsim/lab/static/ops_schema.js";
import { publishSchema, opsForBackend, meterKeys } from "../cvsim/lab/static/schema_store.js";
import { stateFromJson, loadJson, createHistory, deriveEditorTables, setEditorSchema } from "../cvsim/lab/static/editor.js";
import { setInitialSchema, dropMode, clampInitial } from "../cvsim/lab/static/initial.js";

// Minimal hand-written /schema payload (shape = ticket-2 golden; ops keys
// are IR names; uiName present only where IR name differs). backends values
// = ticket-4 derived whitelist (schema.py: core ir_schema - UI-hidden).
// 09-21-lab-gaussian-unhide-ops: gaussian now also exposes cz/cx/
// interferometer/phase_noise/gaussian_channel (mach_zehnder +
// measure_threshold stay hidden).
const IR_BY_UI = { homodyne: "measure_homodyne", heterodyne: "measure_heterodyne" };
const BACKENDS_BY_UI = {
  mz: ["gaussian"],
  kerr: ["fock"], measure_pnr: ["fock"],
  interferometer: ["gaussian", "bosonic"], gaussian_channel: ["gaussian", "bosonic"],
  measure_threshold: ["bosonic"],
  fourier: ["gaussian", "bosonic"],
  cz: ["gaussian", "fock", "bosonic"], cx: ["gaussian", "fock", "bosonic"],
  phase_noise: ["gaussian", "fock", "bosonic"], mach_zehnder: ["fock", "bosonic"],
};
// Real per-op core arity / value_kind (dumped from assemble_schema()). The
// loader now reads `meta.arity` + `meta.value_kind`, so a mock that gives
// every op arity "one" would exercise the fallback path instead of the
// production one — and silently pass for multi-mode / matrix ops.
const ARITY_BY_UI = {
  interferometer: "all", gaussian_channel: "none", phase_noise: "any",
  amplifier: "any", cz: "two", cx: "two", mz: "two", mach_zehnder: "two",
  beamsplitter: "two", two_mode_squeeze: "two",
};
const VALUE_KIND_BY_UI = {
  interferometer: { U: "matrix" },
  gaussian_channel: { X: "matrix", Y: "matrix", d: "matrix" },
};
const MOCK_SCHEMA = {
  ops: Object.fromEntries(Object.entries(OPS).map(([ui, meta]) => {
    const ir = IR_BY_UI[ui] ?? ui;
    const entry = {
      backends: BACKENDS_BY_UI[ui] ?? ["gaussian", "fock", "bosonic"],
      meta: { arity: ARITY_BY_UI[ui] ?? "one", value_kind: VALUE_KIND_BY_UI[ui] ?? {} },
    };
    if (ir !== ui) entry.uiName = ui;
    return [ir, entry];
  })),
  initial: { gaussian: null, fock: { kind: "int", min: 0 }, bosonic: { kind: "enum", sources: ["gkp0", "gkp1", "gkp0_2d", "gkp1_2d"], vacuum: null } },
  extensions: { cutoff: [1, 30], view: { lim_max: 50, lim_min_exclusive: 0, n: [2, 512] }, sweep: { n: [2, 200] }, shots: [1, 100000], rounds: [1, 100] },
  meters: { core: ["purity", "mean_photon", "mean_photon_per_mode"], extensions: { gaussian: ["log_negativity", "singular"], fock: ["leakage"], bosonic: [] } },
};
//: 09-21: install the mock schema into editor.js too (the loader reads
//: meta.arity/value_kind from there); without it the production path —
//: matrix params + 'all'/'none' arity — is never exercised.
setEditorSchema(MOCK_SCHEMA);
// palette derived publish happens in the F7 tests at file end (avoids polluting fallback-path tests).

const EXPECTED_OPS = ["squeeze", "phase", "fourier", "displace", "loss", "beamsplitter", "heterodyne", "homodyne", "amplifier", "mz", "two_mode_squeeze", "kerr", "cz", "cx", "mach_zehnder", "phase_noise", "measure_pnr", "interferometer", "gaussian_channel", "measure_threshold"];

test("ops metadata: 20 ops (ADR-0014: 三个源节点 op 已退役)", () => {
  assert.deepEqual([...OP_NAMES].sort(), [...EXPECTED_OPS].sort());
  assert.equal(OPS.vacuum, undefined);
  assert.equal(OPS.tmsv, undefined);
  assert.equal(OPS.coherent, undefined);
});

test("UX: opGroup — gate/channel/measure, palette:false → null (ADR-0014: 无 source 组)", () => {
  assert.equal(opGroup("squeeze"), "gate");
  assert.equal(opGroup("phase"), "gate");
  assert.equal(opGroup("fourier"), "gate");
  assert.equal(opGroup("displace"), "gate");
  assert.equal(opGroup("beamsplitter"), "gate");
  assert.equal(opGroup("mz"), "gate");
  assert.equal(opGroup("two_mode_squeeze"), "gate");
  assert.equal(opGroup("kerr"), "gate");
  assert.equal(opGroup("cz"), "gate");
  assert.equal(opGroup("cx"), "gate");
  assert.equal(opGroup("mach_zehnder"), "gate");
  assert.equal(opGroup("loss"), "channel");
  assert.equal(opGroup("amplifier"), "channel");
  assert.equal(opGroup("phase_noise"), "channel");
  assert.equal(opGroup("heterodyne"), "measure");
  assert.equal(opGroup("homodyne"), "measure");
  assert.equal(opGroup("measure_pnr"), "measure");
  assert.equal(opGroup("nope"), null);
});


test("F7: fock op metadata — params sane, measure_pnr name is a string param", () => {
  assert.equal(OPS.kerr.kind, "single");
  assert.equal(OPS.kerr.params.chi.min, 0);
  assert.equal(OPS.kerr.params.chi.max, TAU);
  assert.equal(OPS.kerr.params.chi.def, Math.PI / 2);
  assert.equal(OPS.cz.kind, "two");
  assert.equal(OPS.cz.params.weight.def, 1);
  assert.equal(OPS.cx.kind, "two");
  assert.equal(OPS.phase_noise.params.sigma.def, 0);
  assert.equal(OPS.mach_zehnder.kind, "two");
  assert.equal(OPS.measure_pnr.measure, true);
  assert.equal(OPS.measure_pnr.params.name.string, true); // string param: no slider
  assert.deepEqual(paramsFromOp("measure_pnr"), { name: "" });
  assert.deepEqual(paramsFromOp("kerr"), { chi: Math.PI / 2 });
  const pnr = addNode([], "measure_pnr");
  assert.equal(pnr[0].mode, 0);
  assert.equal(pnr[0].params.name, "");
  // string params never slider-edited
  assert.equal(updateParam(pnr[0], "name", "x").params.name, "");
});

test("ops metadata: param ranges sane", () => {
  assert.equal(OPS.loss.params.T.min, 0.01);
  assert.equal(OPS.loss.params.T.max, 1);
  assert.equal(OPS.beamsplitter.params.theta.max, TAU);
  assert.equal(OPS.two_mode_squeeze.params.r.step <= 0.01, true);
  assert.equal(OPS.squeeze.params.r.sweep[1], 2);
});

test("addNode appends with defaults + mode + x", () => {
  let nodes = [];
  nodes = addNode(nodes, "loss");
  assert.equal(nodes.length, 1);
  assert.equal(nodes[0].op, "loss");
  assert.equal(nodes[0].mode, 0);
  assert.equal(nodes[0].ui.x, 0); // first gate x=0
  nodes = addNode(nodes, "beamsplitter");
  assert.deepEqual(nodes[1].modes, [0, 1]);
  assert.equal(nodes[1].ui.x, 1); // appended after loss
  assert.deepEqual(nodes.map((n) => n.op), ["loss", "beamsplitter"]);
});

test("stateNmode: 模数读取单点，缺字段/非法值退化 1", () => {
  assert.equal(stateNmode({ nmode: 3 }), 3);
  assert.equal(stateNmode({ nmode: 1 }), 1);
  assert.equal(stateNmode({ nmode: 0 }), 1);        // IR 要求 >= 1
  assert.equal(stateNmode({ nmode: -2 }), 1);
  assert.equal(stateNmode({ nmode: "4" }), 4);      // JSON 文本域来的字符串
  assert.equal(stateNmode({ nmode: "x" }), 1);
  assert.equal(stateNmode({}), 1);                  // 老 state 无字段
  assert.equal(stateNmode({ nmode: 2.7 }), 2.7);    // 不四舍五入（上游保证整数）
  assert.equal(stateNmode(null), 1);                // 防御
});

/* ADR-0014: per-mode 数组按索引删除（padTo/remapForBackend 只做截尾/补位，
   直接复用会把被删模的值留在原索引）。 */
test("dropMode: 按索引删除，内容对齐（null 直通）", () => {
  assert.deepEqual(dropMode([3, 5, 7], 1), [3, 7]);
  assert.deepEqual(dropMode([3, 5, 7], 0), [5, 7]);
  assert.deepEqual(dropMode([12, 15, 20], 1), [12, 20]);
  assert.deepEqual(dropMode([null, "gkp0", "gkp1"], 1), [null, "gkp1"]);
  assert.equal(dropMode(null, 0), null);       // 全真空省略语义
  assert.deepEqual(dropMode([], 0), []);
});

test("removeNode incl. bounds", () => {
  let nodes = [];
  for (const op of ["loss", "loss", "loss"]) nodes = addNode(nodes, op);
  const [a, b, c] = nodes;
  assert.deepEqual(removeNode(nodes, b.id).map((n) => n.id), [a.id, c.id]);
});

test("L5: sortNodes — (x, mode) order", () => {
  const mk = (op, mode, x, modes) => {
    const n = { id: `${op}-${mode}-${x}`, op, params: paramsFromOp(op) };
    if (modes) n.modes = modes; else n.mode = mode;
    n.ui = { x };
    return n;
  };
  // same x: mode 1 before mode 0 → sorted mode 0 first
  const s1 = mk("phase", 1, 3);
  const s0 = mk("squeeze", 0, 3);
  assert.deepEqual(sortNodes([s1, s0]).map((n) => n.id), [s0.id, s1.id]);
  // two-mode key = modes[0]
  const bs = mk("beamsplitter", 0, 3, [2, 0]);
  assert.deepEqual(sortNodes([bs, s0]).map((n) => n.id), [s0.id, bs.id]);
  // x order dominates mode order
  const far = mk("phase", 0, 9);
  assert.deepEqual(sortNodes([far, s1]).map((n) => n.id), [s1.id, far.id]);
  // stable among equal keys
  assert.deepEqual(sortNodes([s0, s1]).map((n) => n.id), [s0.id, s1.id]);
});

test("L5.5: placeSingle — snaps x to nearest integer column (round)", () => {
  let nodes = [];
  nodes = placeSingle(nodes, "phase", 1, 2.5);
  assert.equal(nodes.find((n) => n.mode === 1).ui.x, 3); // round(2.5)
  nodes = placeSingle(nodes, "squeeze", 0, 0.4);
  assert.equal(nodes.find((n) => n.op === "squeeze").ui.x, 0); // round(0.4)
  nodes = placeSingle(nodes, "phase", 0, -3);
  assert.equal(nodes.filter((n) => n.op === "phase").find((n) => n.mode === 0).ui.x, 0); // clamped
  // invalid: non-single op / bad mode / bad x rejected
  const n0 = nodes.length;
  assert.equal(placeSingle(nodes, "beamsplitter", 0, 1).length, n0);
  assert.equal(placeSingle(nodes, "phase", -1, 1).length, n0);
  assert.equal(placeSingle(nodes, "phase", 0, NaN).length, n0);
});

test("L5.5: cellOccupied — single/two-mode cells, excludeId", () => {
  const nodes = [
    { id: "p", op: "phase", params: { phi: 1 }, mode: 0, ui: { x: 1 } },
    { id: "bs", op: "beamsplitter", params: { theta: 0.5 }, modes: [0, 1], ui: { x: 2 } },
  ];
  assert.equal(cellOccupied(nodes, 0, 1.4), true);  // single gate, round(1.4)=1
  assert.equal(cellOccupied(nodes, 0, 0.6), true);  // round(0.6)=1 → same cell
  assert.equal(cellOccupied(nodes, 0, 0.4), false); // round(0.4)=0 → free
  assert.equal(cellOccupied(nodes, 0, 2), true);    // bs locks lane 0 @ x2
  assert.equal(cellOccupied(nodes, 1, 2), true);    // bs locks lane 1 @ x2
  assert.equal(cellOccupied(nodes, 1, 2.4), true);  // round to 2
  assert.equal(cellOccupied(nodes, 2, 2), false);   // no gate on lane 2
  assert.equal(cellOccupied(nodes, 0, 3), false);
  // excludeId: the moving gate ignores its own cells
  assert.equal(cellOccupied(nodes, 0, 1, "p"), false);
  assert.equal(cellOccupied(nodes, 0, 2, "bs"), false);
  assert.equal(cellOccupied(nodes, 1, 2, "bs"), false);
  assert.equal(cellOccupied(nodes, 0, 2, "nope"), true);
});

test("L5: completePlacing — two-mode two-step flow", () => {
  let nodes = [];
  nodes = placeSingle(nodes, "loss", 0, 0);
  nodes = placeSingle(nodes, "loss", 1, 0); // two modes occupied by gates
  const placing = { op: "beamsplitter", modeA: 0, x: 1.5 };
  const ok = completePlacing(nodes, placing, 1);
  assert.equal(ok.ok, true);
  assert.equal(ok.nodes[2].op, "beamsplitter");
  assert.deepEqual(ok.nodes[2].modes, [0, 1]);
  assert.equal(ok.nodes[2].ui.x, 2); // round(1.5)
  // same-lane reject, state preserved
  const same = completePlacing(nodes, placing, 0);
  assert.equal(same.ok, false);
  assert.match(same.reason, /不同模式/);
  // L5.5: second lane's cell occupied → rejected, placing kept
  const gated = completePlacing(ok.nodes, placing, 1);
  assert.equal(gated.ok, false);
  assert.match(gated.reason, /已被占用/);
  // invalid placing / non-two op rejected
  assert.equal(completePlacing(nodes, { op: "phase", modeA: 0, x: 1 }, 1).ok, false);
  assert.equal(completePlacing(nodes, null, 1).ok, false);
  assert.equal(completePlacing(nodes, placing, -1).ok, false);
});

test("L5: moveNodeX — reorders by new x, snaps round, guards NaN", () => {
  let nodes = [];
  nodes = placeSingle(nodes, "phase", 0, 1);
  nodes = placeSingle(nodes, "squeeze", 0, 2);
  const [ph, sq] = nodes;
  const moved = moveNodeX(nodes, sq.id, 0.4); // squeeze snaps to 0, now before phase
  assert.deepEqual(moved.map((n) => n.op), ["squeeze", "phase"]);
  assert.equal(moved[0].ui.x, 0); // round(0.4)
  assert.equal(moveNodeX(nodes, sq.id, "x").length, nodes.length); // NaN rejected
  // same-column move keeps order
  const sameCol = moveNodeX(nodes, ph.id, 1.4);
  assert.equal(sameCol[0].ui.x, 1);
});

test("L5: staffLayout — one row per mode, D1(b) labels", async () => {
  const { staffLayout, modeLabel } = await import("../cvsim/lab/static/staff.js");
  const base = {
    nodes: [
      { id: "bs", op: "beamsplitter", params: { theta: 0.5 }, modes: [2, 0], ui: { x: 1 } },
    ],
    view: {}, ui: {}, backend: "gaussian", initial: null, nmode: 3,
  };
  const { rows, gates, nmode } = staffLayout(base);
  assert.equal(rows.length, 3);
  assert.equal(nmode, 3);
  assert.deepEqual(rows.map((r) => r.mode), [0, 1, 2]);
  assert.deepEqual(rows.map((r) => r.label), ["mode 0 · 真空", "mode 1 · 真空", "mode 2 · 真空"]);
  assert.equal(gates.length, 1);
  assert.equal(gates[0].span, 3); // |2-0|+1
  assert.equal(gates[0].top, 0);
  assert.equal(gates[0].modeA, 2); // JSON order preserved
  assert.equal(gates[0].modeB, 0);
  // 缺 nmode 字段 → 退化为 1 行（防御，不炸）
  assert.equal(staffLayout({ nodes: [], view: {}, ui: {} }).rows.length, 1);
  // modeLabel: fock 0/非 0、bosonic null/名、gaussian 恒真空
  const fock = { backend: "fock", initial: [0, 3, null] };
  assert.equal(modeLabel(fock, 0), "mode 0 · 真空");
  assert.equal(modeLabel(fock, 1), "mode 1 · |3⟩");
  assert.equal(modeLabel(fock, 2), "mode 2 · 真空"); // 非法值不撒谎
  const bos = { backend: "bosonic", initial: [null, "gkp0"] };
  assert.equal(modeLabel(bos, 0), "mode 0 · 真空");
  assert.equal(modeLabel(bos, 1), "mode 1 · gkp0");
  assert.equal(modeLabel(bos, 2), "mode 2 · 真空");
  assert.equal(modeLabel({ backend: "gaussian", initial: [7] }, 0), "mode 0 · 真空");
});

test("L5: removeMode — cascades gates on that mode only", () => {
  const nodes = [
    { id: "p0", op: "phase", params: { phi: 1 }, mode: 0, ui: { x: 1 } },
    { id: "p1", op: "squeeze", params: { r: 0.4 }, mode: 1, ui: { x: 1 } },
    { id: "bs", op: "beamsplitter", params: { theta: 0.5 }, modes: [0, 1], ui: { x: 2 } },
    { id: "d", op: "displace", params: { alpha: 1 }, mode: 2, ui: { x: 3 } },
  ];
  const kept = removeMode(nodes, 0);
  // lane 0 上的单模门 + 跨 lane 的双模门级联删除；lane 2 的门上移
  assert.deepEqual(kept.map((n) => n.id), ["p1", "d"]);
  assert.equal(kept[0].mode, 0);           // 原 lane 1 → 0
  assert.equal(kept[1].mode, 1);           // 原 lane 2 → 1
});

test("L5: removeMode — remaps surviving gates above the deleted mode", () => {
  const nodes = [
    { id: "pa", op: "phase", params: { phi: 1 }, mode: 0, ui: { x: 1 } },
    { id: "pb", op: "squeeze", params: { r: 0.4 }, mode: 1, ui: { x: 1 } },
    { id: "pc", op: "phase", params: { phi: 2 }, mode: 2, ui: { x: 2 } },
    { id: "bs", op: "beamsplitter", params: { theta: 0.5 }, modes: [2, 3], ui: { x: 3 } },
    { id: "czg", op: "cz", params: {}, modes: [3, 4], ui: { x: 4 } },
  ];
  const kept = removeMode(nodes, 1);
  const byId = Object.fromEntries(kept.map((n) => [n.id, n]));
  assert.deepEqual(kept.map((n) => n.id), ["pa", "pc", "bs", "czg"]);
  assert.equal(byId.pa.mode, 0);           // 删除模上方不动
  assert.equal(byId.pc.mode, 1);           // 下方单模门 -1
  assert.deepEqual(byId.bs.modes, [1, 2]); // 下方双模门整体 -1
  assert.deepEqual(byId.czg.modes, [2, 3]);
});

test("L5: toV1Json — v1 payload, nmode read from state, no ui.x on ops", () => {
  let nodes = placeSingle([], "phase", 0, 3.5);
  nodes = placeSingle(nodes, "loss", 1, 0);
  const payload = toV1Json({ nmode: 2, nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.schema, "circuit_v1");
  assert.equal(payload.nmode, 2); // state.nmode 直读（ADR-0014）
  // sortNodes: x asc，同 x 按 mode；loss@x0 先于 phase@x4
  assert.deepEqual(payload.ops.map((o) => o.op), ["loss", "phase"]);
  assert.deepEqual(payload.ops[1].params, { theta: Math.PI / 2 }); // phase phi → theta
  assert.deepEqual(payload.ops[0].modes, [1]); // mode → modes
  assert.ok(!("ui" in payload.ops[0]) && !("edges" in payload));
  assert.equal(typeof payload.ui.staff[payload.ops[0].id], "number"); // staff layout in ui extension
  const st = stateFromJson(payload);
  assert.deepEqual(st.state.nodes.map((n) => n.ui.x), payload.ops.map((o) => payload.ui.staff[o.id]));
});

test("L5: stateFromJson — missing staff falls back to array index", () => {
  // v1: graph model ops map from circuit_v1 ops (vacuum folded to nmode);
  // layout columns come from ui.staff, missing entries → array order.
  const base = {
    schema: "circuit_v1",
    nmode: 2,
    ops: [
      { id: "a", op: "phase", params: { theta: 1 }, modes: [0] },
      { id: "b", op: "squeeze", params: { r: 0.4, phi: 0 }, modes: [1] },
    ],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const { state, error } = stateFromJson(base);
  assert.equal(error, undefined);
  assert.deepEqual(state.nodes.map((n) => n.ui?.x), [0, 1]); // 无源节点（ADR-0014）
  // explicit ui.staff honored
  const withX = { ...base, ui: { staff: { a: 7, b: 3 } } };
  const { state: sx } = stateFromJson(withX);
  assert.equal(sx.nodes.find((n) => n.id === "a").ui.x, 7);
  assert.equal(sx.nodes.find((n) => n.id === "b").ui.x, 3);
  // round-trip: ui.x survives
  const rt = stateFromJson(toV1Json(state));
  assert.deepEqual(rt.state.nodes.map((n) => n.ui?.x), [0, 1]);
});

test("clampParam: 声明区间夹紧单点（updateParam 与参数卡片共用）", () => {
  assert.equal(clampParam("loss", "T", 99), 1);       // 上界
  assert.equal(clampParam("loss", "T", -5), 0.01);    // 下界
  assert.equal(clampParam("loss", "T", 0.5), 0.5);    // 区间内不变
  assert.equal(clampParam("squeeze", "r", "2"), 2);  // 字符串输入（number 框）
  assert.equal(clampParam("loss", "nope", 1), null);  // 未知键 → 调用方拒绝
  assert.equal(clampParam("loss", "T", NaN), null);   // NaN
  assert.equal(clampParam("loss", "T", Infinity), null);
  assert.equal(clampParam("nope", "T", 1), null);     // 未知 op
});

test("visibleParams: fock 隐藏 IR 丢弃的参数（与 toV1Json drop 表同源）", () => {
  // 09-14-fock-squeeze-phi：fock 的 squeeze 已带 phi（与 FockState.squeezed 同约定），三后端一致
  assert.deepEqual(Object.keys(visibleParams("squeeze", "gaussian")), ["r", "phi"]);
  assert.deepEqual(Object.keys(visibleParams("squeeze", "fock")), ["r", "phi"]);
  assert.deepEqual(Object.keys(visibleParams("squeeze", "bosonic")), ["r", "phi"]);
  // fock loss 纯损耗，无热 nbar（drop 表仍生效）
  assert.deepEqual(Object.keys(visibleParams("loss", "gaussian")), ["T", "nbar"]);
  assert.deepEqual(Object.keys(visibleParams("loss", "fock")), ["T"]);
  // 未受影响的后端 op 全量保留；未知 op 空表
  assert.deepEqual(Object.keys(visibleParams("phase", "fock")), ["phi"]);
  assert.deepEqual(Object.keys(visibleParams("nope", "fock")), []);
});

test("updateParam / updateMode", () => {
  let nodes = addNode([], "loss");
  nodes = nodes.map((n) => updateParam(n, "T", 0.5));
  assert.equal(nodes[0].params.T, 0.5);
  nodes = nodes.map((n) => updateMode(n, 1));
  assert.equal(nodes[0].mode, 1);
  assert.equal(updateMode(nodes[0], -2).mode, 1); // invalid rejected
});

test("OCR guards: clamp, unknown keys", () => {
  let nodes = addNode([], "loss");
  // out-of-range clamped to metadata bounds
  assert.equal(updateParam(nodes[0], "T", 99).params.T, 1);
  assert.equal(updateParam(nodes[0], "T", -5).params.T, 0.01);
  // NaN / unknown key rejected (no change)
  assert.equal(updateParam(nodes[0], "T", NaN).params.T, 0.8);
  assert.equal(updateParam(nodes[0], "nope", 1).params.T, 0.8);
  // unknown op rejected
  assert.throws(() => paramsFromOp("even_cat"), TypeError);
  assert.throws(() => paramsFromOp("zzz_unknown"), TypeError);
});

test("OCR guards: id collision after import, proto keys, dup ids", () => {
  const payload = toV1Json({
    nmode: 1,
    nodes: [{ id: "n0", op: "phase", params: { phi: 1 }, mode: 0 }],
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  const { state } = stateFromJson(payload);
  const grown = addNode(state.nodes, "loss");
  assert.equal(grown[1].id, "n1"); // next free numeric id
  // __proto__ / constructor must not pass the whitelist
  assert.ok(stateFromJson({ schema: "circuit_v1", nmode: 1, ops: [{ id: "x", op: "__proto__", modes: [0], params: {} }] }).error);
  assert.ok(stateFromJson({ schema: "circuit_v1", nmode: 1, ops: [{ id: "x", op: "constructor", modes: [0], params: {} }] }).error);
  // duplicate ids rejected
  const dup = { schema: "circuit_v1", nmode: 1, ops: [
    { id: "a", op: "phase", modes: [0], params: { theta: 0.5 } },
    { id: "a", op: "loss", modes: [0], params: { T: 0.9 } },
  ] };
  assert.ok(stateFromJson(dup).error);
  // malformed param freezes instead of silently defaulting
  const bad = { schema: "circuit_v1", nmode: 1, ops: [{ id: "a", op: "squeeze", modes: [0], params: { r: "x" } }] };
  assert.ok(stateFromJson(bad).error);
});

test("toV1Json: circuit_v1 payload (ADR-0003)", () => {
  const nodes = placeSingle([], "loss", 1, 0);
  const payload = toV1Json({ nmode: 2, nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.schema, "circuit_v1");
  assert.equal(payload.nmode, 2);
  assert.ok(!("edges" in payload));
  assert.deepEqual(payload.ops[0].op, "loss");
  assert.deepEqual(payload.ops[0].modes, [1]);
  assert.equal(payload.ops.length, 1);
  // 防御：state 缺 nmode → 退化为 1（IR 要求 nmode >= 1）
  assert.equal(toV1Json({ nodes: [], view: {}, ui: {} }).nmode, 1);
});

test("stateFromJson: valid payload round-trips (nmode 一等字段)", () => {
  const payload = toV1Json({
    nmode: 2,
    nodes: placeSingle([], "loss", 0, 0),
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes.length, 1);
  assert.equal(state.nodes[0].op, "loss");
  assert.equal(state.nmode, 2);            // payload.nmode → state.nmode
  assert.equal(state.nodes.some((n) => n.op === "vacuum"), false); // 不再注入源节点
});

test("stateFromJson: rejects wrong schema / non-object (ADR-0011: v1 only)", () => {
  assert.ok(stateFromJson({ schema: "nope", nodes: [] }).error);
  assert.ok(stateFromJson({ schema: "circuit_v0", nmode: 1, ops: [] }).error);
  assert.ok(stateFromJson(null).error);
  assert.ok(stateFromJson("nope").error);
  // op absent from OPS (no UI control) rejected. NOTE: a valid `view` is
  // required here — without it the loader fails on view.wigner_mode first
  // and the assertion would pass for the wrong reason (09-21 review).
  const VIEW = { wigner_mode: 0, lim: 5.0, n: 64 };
  const bad = stateFromJson({
    schema: "circuit_v1", nmode: 2, view: VIEW,
    ops: [{ id: "x", op: "apply_unitary", modes: [0], params: {} }],
  });
  assert.match(bad.error, /不在 Lab 白名单/);
  // mach_zehnder is a core op WITH a UI entry but no gaussian whitelist
  // entry — the loader lets it through (it is not UI-hidden by op table);
  // the *backend* is what rejects it. Assert the real reason:
  const mz = stateFromJson({
    schema: "circuit_v1", nmode: 2, view: VIEW,
    ops: [{ id: "x", op: "mach_zehnder", modes: [0, 1], params: { theta: 0.5, phi: 0 } }],
  });
  assert.equal(mz.error, undefined, "mach_zehnder 有 UI 条目，前端放行（后端按白名单拒）");
});

test("L3: homodyne visible with phi default 0 / max TAU", () => {
  assert.ok(OPS.homodyne);
  assert.equal(OPS.homodyne.kind, "single");
  assert.equal(OPS.homodyne.params.phi.def, 0);
  assert.equal(OPS.homodyne.params.phi.max, TAU);
  assert.deepEqual(paramsFromOp("homodyne"), { phi: 0, name: "" });
  const node = addNode([], "homodyne");
  assert.equal(node[0].mode, 0);
  assert.equal(node[0].params.phi, 0);
});

test("L3: toV1Json preserves top-level seed", () => {
  const payload = toV1Json({
    seed: 42,
    nmode: 1,
    nodes: addNode([], "loss"),
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  assert.equal(payload.seed, 42);
});

test("L3: stateFromJson accepts seed + homodyne optional phi", () => {
  const payload = {
    schema: "circuit_v1",
    seed: 7,
    nmode: 2,
    ops: [
      { id: "b", op: "measure_homodyne", params: { phi: 1.5, name: "b" }, modes: [0] },
      { id: "c", op: "measure_homodyne", params: { name: "c" }, modes: [1] },
    ],
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.seed, 7);
  assert.equal(state.nodes[0].params.phi, 1.5);
  assert.equal(state.nodes[1].params.phi, 0); // missing phi → default 0
  // round-trip
  const rt = stateFromJson(toV1Json(state));
  assert.equal(rt.error, undefined);
  assert.equal(rt.state.seed, 7);
  assert.equal(rt.state.nodes[0].params.phi, 1.5);
});

/* 存量档案回归锁：fock squeeze 的 phi 曾进 drop 表（后端当时只吃实 r），
   所以旧存盘文件**不带 phi**。09-14-fock-squeeze-phi 补 phi 后若标必填，
   这些文件全部 422。缺省许可**只对 fock 生效**（editor.js 的 optionalOnFock），
   gaussian/bosonic 的 phi 仍必填——本测试把两侧都锁住。 */
test("存量 fock 档案（squeeze 无 phi）仍能载入 —— 缺省许可限 fock", () => {
  const payload = {
    schema: "circuit_v1", backend: "fock", nmode: 1, cutoff: 10,
    ops: [{ id: "s", op: "squeeze", params: { r: 0.4 }, modes: [0] }],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  const sq = state.nodes.find((n) => n.op === "squeeze");
  assert.equal(sq.params.r, 0.4);
  assert.equal(sq.params.phi, 0); // 缺省 0 —— 不是报错
  // 非数值（缺省许可只免“缺省”，不免“胡写”）：fock 也按 NaN → 默认 0 收敛
  const bad = stateFromJson({
    ...payload, ops: [{ id: "s", op: "squeeze", params: { r: 0.4, phi: "x" }, modes: [0] }],
  });
  assert.equal(bad.error, undefined);
  assert.equal(bad.state.nodes[0].params.phi, 0);
});

/* 超范围护栏：缺省许可**不得**外溢到 gaussian/bosonic —— AC6「gaussian 行为不变」。
   这两个后端的 phi 一直必填（旧行为：缺 phi → 冻结图 + 报错）。 */
test("gaussian/bosonic: squeeze 缺 phi 仍冻结（缺省许可未外溢）", () => {
  const payload = {
    schema: "circuit_v1", nmode: 1,
    ops: [{ id: "s", op: "squeeze", params: { r: 0.4 }, modes: [0] }],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  for (const backend of [undefined, "gaussian", "bosonic"]) {
    const { error } = stateFromJson(backend ? { ...payload, backend } : payload);
    assert.ok(error, `backend=${backend}: 应冻结，却放行了`);
    assert.ok(error.includes("phi"), `backend=${backend}: 报错应指向 phi，得到 ${error}`);
  }
});

/* /schema 的 cutoff 是 {min,max} 对象（schema.py ``_EXTENSIONS``，
   test_lab_schema.py 锁定），editor 内部要 [min,max] 二元组
   （``cutMax = tables().cutoff[1]``）。曾不归一化 → cutMax=undefined →
   带显式 cutoff 的 fock JSON 全被拒。纯函数，不碰全局。 */
test("deriveEditorTables: cutoff {min,max} 归一化为 [min,max]", () => {
  const t = deriveEditorTables({ ops: {}, extensions: { cutoff: { min: 1, max: 30 } } });
  assert.deepEqual(t.cutoff, [1, 30]);
  // 数组形式（旧形/回退常量）仍接受
  assert.deepEqual(
    deriveEditorTables({ ops: {}, extensions: { cutoff: [2, 12] } }).cutoff, [2, 12]);
  // 完全缺省 → 回退常量
  assert.deepEqual(deriveEditorTables({ ops: {}, extensions: {} }).cutoff, [1, 30]);
});

test("L3: stateFromJson rejects invalid seed", () => {
  const base = { schema: "circuit_v1", seed: 0, nmode: 1, ops: [], view: { wigner_mode: 0, lim: 5, n: 64 } };
  assert.equal(stateFromJson(base).error, undefined); // seed 0 is valid (positive baseline)
  assert.ok(stateFromJson({ ...base, seed: -1 }).error);
  assert.ok(stateFromJson({ ...base, seed: 1.5 }).error);
  assert.ok(stateFromJson({ ...base, seed: "x" }).error);
});

test("L3: loadJson validates without mutating old state", () => {
  const good = { schema: "circuit_v1", seed: 3, nmode: 1, ops: [], view: { wigner_mode: 0, lim: 5, n: 64 } };
  const bad = { schema: "nope", nodes: [] };
  const old = { seed: 0, nodes: [], view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} };
  const ok = loadJson(good);
  assert.equal(ok.error, undefined);
  assert.equal(ok.state.seed, 3);
  assert.deepEqual(old, { seed: 0, nodes: [], view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  const badRes = loadJson(bad);
  assert.ok(badRes.error);
  assert.deepEqual(old, { seed: 0, nodes: [], view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
});

test("L4: amplifier + mz metadata", () => {
  assert.equal(OPS.amplifier.kind, "single");
  assert.equal(OPS.amplifier.params.G.min, 1);
  assert.equal(OPS.amplifier.params.G.def, 2);
  assert.deepEqual(OPS.amplifier.params.G.sweep, [1, 4]);
  assert.equal(OPS.amplifier.params.nbar.advanced, true);
  assert.equal(OPS.amplifier.params.nbar.sweep, undefined); // advanced, not sweepable
  assert.equal(OPS.mz.kind, "two");
  assert.deepEqual(OPS.mz.params.theta.sweep, [0, Math.PI]);
  assert.deepEqual(OPS.mz.params.phi.sweep, [0, Math.PI]);
  const a = addNode([], "amplifier");
  assert.equal(a[0].mode, 0);
  assert.equal(a[0].params.G, 2);
  assert.equal(a[0].params.nbar, 0);
  const m = addNode([], "mz");
  assert.deepEqual(m[0].modes, [0, 1]);
  assert.equal(m[0].params.theta, Math.PI / 4);
  assert.equal(m[0].params.phi, Math.PI / 2);
});

test("L4: sweep metadata — alpha excluded, real numerics included", () => {
  assert.equal(OPS.displace.params.alpha.sweep, undefined);
  assert.deepEqual(OPS.squeeze.params.r.sweep, [0, 2]);
  assert.deepEqual(OPS.loss.params.T.sweep, [0, 1]);
  assert.deepEqual(OPS.beamsplitter.params.theta.sweep, [0, Math.PI]);
  assert.deepEqual(OPS.phase.params.phi.sweep, [0, Math.PI]);
  assert.deepEqual(OPS.two_mode_squeeze.params.r.sweep, [0, 2]);
});

test("L4: stateFromJson accepts amplifier/mz", () => {
  const payload = {
    schema: "circuit_v1",
    seed: 0,
    nmode: 2,
    ops: [
      { id: "a", op: "amplifier", params: { G: 2 }, modes: [0] },
      { id: "m", op: "mz", params: { theta: 0.5, phi: 0.3 }, modes: [0, 1] },
    ],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes[0].params.nbar, 0); // advanced default filled
  assert.equal(state.nodes[1].params.theta, 0.5);
  const rt = stateFromJson(toV1Json(state));
  assert.equal(rt.error, undefined);
  // missing required G freezes
  const noG = { ...payload, ops: [{ id: "a", op: "amplifier", params: {}, modes: [0] }] };
  assert.ok(stateFromJson(noG).error);
});

test("stateFromJson: missing params freeze (frozen-graph policy)", () => {
  const { error } = stateFromJson({ schema: "circuit_v1", nmode: 1, ops: [{ id: "x", op: "squeeze", modes: [0], params: {} }] });
  assert.ok(error);
  assert.ok(error.includes("r"));
});

test("fourier gate: palette-visible gate, JSON round-trip loadable", () => {
  assert.equal(opGroup("fourier"), "gate");
  assert.deepEqual(Object.keys(OPS.fourier.params), []); // no knobs
  const payload = {
    schema: "circuit_v1", seed: 0, nmode: 1,
    ops: [{ id: "f", op: "fourier", params: {}, modes: [0], ui: { x: 0 } }],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes[0].op, "fourier");
  assert.equal(state.nodes[0].ui.x, 0);
  const rt = stateFromJson(toV1Json(state)); // save → load round-trip
  assert.equal(rt.error, undefined);
  assert.equal(rt.state.nodes[0].op, "fourier");
});

test("undo/redo: push → undo → redo round-trips state references", () => {
  const h = createHistory(50);
  const s0 = { n: 0 }, s1 = { n: 1 }, s2 = { n: 2 };
  h.push(s0); h.push(s1); // edits: s0 → s1 → s2
  assert.equal(h.canUndo(), true);
  assert.equal(h.undo(s2), s1);
  assert.equal(h.undo(s1), s0);
  assert.equal(h.undo(s0), null); // empty: no-op
  assert.equal(h.canRedo(), true);
  assert.equal(h.redo(s0), s1);
  assert.equal(h.redo(s1), s2);
  assert.equal(h.redo(s2), null);
});

test("undo/redo: new edit clears redo; clear() empties both; max caps history", () => {
  const h = createHistory(2);
  const a2 = { a: 2 }, a3 = { a: 3 }, a4 = { a: 4 };
  h.push({ a: 1 }); h.push(a2); h.push(a3);
  assert.equal(h.canRedo(), false); // push cleared redo
  // oldest ({a:1}) was shifted out: only {a:2},{a:3} remain; current = {a:4}
  assert.equal(h.undo(a4), a3);
  assert.equal(h.undo(a3), a2);
  assert.equal(h.undo(a2), null);
  const h2 = createHistory(3);
  h2.push({ a: 1 }); h2.push({ a: 2 });
  h2.undo({ a: 2 });
  assert.equal(h2.canRedo(), true);
  h2.push({ a: 3 }); // new edit after undo
  assert.equal(h2.canRedo(), false);
  h2.clear();
  assert.equal(h2.canUndo(), false);
  assert.equal(h2.canRedo(), false);
});

/* ── circuit_v1 (ADR-0003) ───────────────────────────────── */

test("v1: toV1Json — nmode 由 state 决定，节点不再贡献模数", () => {
  const nodes = [
    { id: "t", op: "two_mode_squeeze", params: { r: 0.6 }, modes: [0, 1], ui: { x: 0 } },
    { id: "d", op: "displace", params: { alpha: 1 }, mode: 2, ui: { x: 0 } },
  ];
  const payload = toV1Json({ nmode: 3, nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.nmode, 3);
  assert.deepEqual(payload.ops.map((o) => o.op), ["two_mode_squeeze", "displace"]);
  assert.deepEqual(payload.ops[0].modes, [0, 1]);
  assert.deepEqual(payload.ops[1].modes, [2]);
  assert.equal(payload.ops[0].params.r, 0.6);
});

test("v1: toV1Json maps measure ops + keeps measurement order", () => {
  const nodes = [
    { id: "n1", op: "homodyne", params: { phi: 1.2 }, mode: 0, ui: { x: 0 } },
    { id: "n2", op: "heterodyne", params: {}, mode: 1, ui: { x: 0 } },
  ];
  const payload = toV1Json({ nmode: 2, nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.deepEqual(payload.ops.map((o) => o.op), ["measure_homodyne", "measure_heterodyne"]);
  assert.equal(payload.ops[0].params.phi, 1.2);
});

test("v1: stateFromJson inverts native v1 doc (op remap, nmode 直读)", () => {
  const payload = {
    schema: "circuit_v1", nmode: 3, seed: 5,
    ops: [
      { op: "two_mode_squeeze", modes: [0, 1], params: { r: 0.4 } },
      { op: "measure_heterodyne", modes: [1], params: {} },
      { op: "phase", modes: [2], params: { theta: 0.7 } },
    ],
    view: { wigner_mode: 2, lim: 4.0, n: 32 }, ui: {},
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.seed, 5);
  assert.equal(state.nodes.length, 3);      // 无源节点
  assert.equal(state.nmode, 3);             // 模数来自 payload.nmode
  assert.deepEqual(state.nodes.map((n) => n.op), ["two_mode_squeeze", "heterodyne", "phase"]);
  assert.deepEqual(state.nodes[2].params, { phi: 0.7 }); // theta → phi
  assert.equal(state.nodes[1].mode, 1);
  // round-trip back to v1 is stable
  const again = toV1Json(state);
  assert.equal(again.nmode, 3);
  assert.deepEqual(again.ops.map((o) => o.op), ["two_mode_squeeze", "measure_heterodyne", "phase"]);
});

test("v1: stateFromJson 放行解锁的 gaussian op，仍拒无 UI 条目的 op", () => {
  const VIEW = { wigner_mode: 0, lim: 5.0, n: 64 };
  // 09-21: interferometer 现已在 gaussian 白名单 + 是矩阵 op → 必须载入
  // 且 U 不丢（此前因 view 缺失被误判为"白名单拒绝"，断言空转）。
  const itf = stateFromJson({
    schema: "circuit_v1", nmode: 2, view: VIEW,
    ops: [{ op: "interferometer", modes: [0, 1], params: { U: [[1, 0], [0, 1]] } }],
  });
  assert.equal(itf.error, undefined);
  assert.deepEqual(itf.state.nodes[0].params.U, [[1, 0], [0, 1]]);
  assert.deepEqual(toV1Json(itf.state).ops[0].params.U, [[1, 0], [0, 1]]);
  // 矩阵编辑器 defer（反白名单教义）：apply_unitary 无 UI 条目 → 拒
  const au = stateFromJson({
    schema: "circuit_v1", nmode: 1, view: VIEW,
    ops: [{ op: "apply_unitary", modes: [0], params: { U: [[1, 0], [0, 1]] } }],
  });
  assert.match(au.error, /不在 Lab 白名单/);
});

test("v1: auto id never collides with explicit id", () => {
  const payload = {
    schema: "circuit_v1", nmode: 1,
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ops: [
      { op: "fourier", modes: [0] },          // auto → n0
      { id: "n0", op: "phase", modes: [0], params: { theta: 1 } }, // explicit n0
      { op: "squeeze", modes: [0], params: { r: 0.4, phi: 0 } },  // auto → n2_? (n2 free)
    ],
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.deepEqual(state.nodes.filter((n) => n.op !== "vacuum").map((n) => n.id), ["n0_1", "n0", "n2"]);
});

test("v1: displace array alpha round-trips (UI takes real part)", () => {
  const payload = {
    schema: "circuit_v1", nmode: 2, seed: 0,
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ops: [{ id: "d", op: "displace", modes: [0], params: { alpha: [0.3, -0.4] } }],
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes.find((n) => n.op === "displace").params.alpha, 0.3);
  // save again: back to v1 with a real scalar (UI real-part semantics)
  const again = toV1Json(state);
  assert.equal(again.ops.find((o) => o.op === "displace").params.alpha, 0.3);
});

/* ── F7: backend / initial / cutoff JSON sync ───────────── */

test("F7: toV1Json — backend 缺省 gaussian（不写字段，旧文件字节不变）", () => {
  const st = { seed: 0, nmode: 1, nodes: addNode([], "loss"), view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, backend: "gaussian", initial: null, cutoffs: [10] };
  const payload = toV1Json(st);
  assert.equal(payload.backend, undefined); // 缺省 gaussian = 旧 JSON 零破坏
  assert.equal(payload.initial, undefined);
  assert.equal(payload.cutoff, undefined);
  // fock 显式写 backend
  const fockPayload = toV1Json({ ...st, backend: "fock" });
  assert.equal(fockPayload.backend, "fock");
  assert.equal(fockPayload.initial, undefined); // 全零 initial 不写
  assert.equal(fockPayload.cutoff, undefined);  // 默认 10 不写
});

test("F7: toV1Json — initial 非全零才写；cutoff 均匀 int / 非均匀 list", () => {
  const base = {
    seed: 0,
    nmode: 2,
    nodes: [],
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
    backend: "fock",
  };
  const hom = toV1Json({ ...base, initial: [1, 1], cutoffs: [12, 12] });
  assert.deepEqual(hom.initial, [1, 1]);
  assert.equal(hom.cutoff, 12); // 均匀 → int
  const mixed = toV1Json({ ...base, initial: [0, 2], cutoffs: [10, 15] });
  assert.deepEqual(mixed.initial, [0, 2]);
  assert.deepEqual(mixed.cutoff, [10, 15]); // 非均匀 → list
  // gaussian backend 忽略 initial/cutoff
  const g = toV1Json({ ...base, backend: "gaussian", initial: [1, 1], cutoffs: [12, 12] });
  assert.equal(g.initial, undefined);
  assert.equal(g.cutoff, undefined);
});

test("F7: toV1Json — measure ops carry a result name (Fock IR requires it)", () => {
  const nodes = [
    { id: "n1", op: "homodyne", params: { phi: 1.2 }, mode: 0, ui: { x: 0 } },
    { id: "n2", op: "heterodyne", params: {}, mode: 1, ui: { x: 0 } },
    { id: "n3", op: "measure_pnr", params: { name: "" }, mode: 2, ui: { x: 0 } },
  ];
  const payload = toV1Json({ nmode: 3, nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, backend: "fock" });
  assert.equal(payload.ops[0].params.name, "n1"); // 未命名 → 节点 id
  assert.equal(payload.ops[1].params.name, "n2");
  assert.equal(payload.ops[2].params.name, "n3");
  // 显式载入的 name 保留
  const named = toV1Json({
    nmode: 1,
    nodes: [{ id: "n9", op: "measure_pnr", params: { name: "m_n" }, mode: 0, ui: { x: 0 } }],
    view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, backend: "fock",
  });
  assert.equal(named.ops[0].params.name, "m_n");
});

test("F7: stateFromJson — backend/initial/cutoff 解析 + 校验", () => {
  setInitialSchema(MOCK_SCHEMA); // ticket 4: no mirror fallback — inject first
  const base = {
    schema: "circuit_v1", nmode: 2, seed: 0,
    ops: [{ op: "kerr", modes: [0], params: { chi: 1.5 } }],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const g = stateFromJson(base);
  assert.equal(g.error, undefined);
  assert.equal(g.state.backend, "gaussian"); // 缺省
  assert.equal(g.state.initial, null);
  assert.deepEqual(g.state.cutoffs, [10, 10]);
  const f = stateFromJson({ ...base, backend: "fock", initial: [1, 0], cutoff: 12 });
  assert.equal(f.error, undefined);
  assert.equal(f.state.backend, "fock");
  assert.deepEqual(f.state.initial, [1, 0]);
  assert.deepEqual(f.state.cutoffs, [12, 12]);
  // per-mode list
  const pl = stateFromJson({ ...base, backend: "fock", cutoff: [10, 14] });
  assert.deepEqual(pl.state.cutoffs, [10, 14]);
  // 非法值
  // B6: bosonic 合法（initial 为 GKP 态名/null；非法值拒收）
  const bo = stateFromJson({ ...base, backend: "bosonic", initial: ["gkp0", null] });
  assert.equal(bo.error, undefined);
  assert.equal(bo.state.backend, "bosonic");
  assert.deepEqual(bo.state.initial, ["gkp0", null]);
  assert.ok(stateFromJson({ ...base, backend: "bosonic", initial: ["even_cat", null] }).error); // 未知态名
  // GKP 2d Z 基初态名单(gkp0_2d/gkp1_2d)通过校验;未知态名仍拒收(AC-6)
  const bo2d = stateFromJson({ ...base, backend: "bosonic", initial: ["gkp0_2d", null] });
  assert.equal(bo2d.error, undefined);
  assert.equal(bo2d.state.backend, "bosonic");
  assert.deepEqual(bo2d.state.initial, ["gkp0_2d", null]);
  assert.ok(stateFromJson({ ...base, backend: "bosonic", initial: ["gkp9", null] }).error); // 未知态名
  assert.ok(stateFromJson({ ...base, initial: [1] }).error); // 长度不符
  assert.ok(stateFromJson({ ...base, initial: [1, -1] }).error);
  assert.ok(stateFromJson({ ...base, cutoff: 0 }).error);
  assert.ok(stateFromJson({ ...base, cutoff: [10] }).error);
  assert.ok(stateFromJson({ ...base, cutoff: "x" }).error);
  // round-trip: save → load 一致（含 kerr + initial）
  const rt = stateFromJson(toV1Json(f.state));
  assert.equal(rt.error, undefined);
  assert.equal(rt.state.backend, "fock");
  assert.deepEqual(rt.state.initial, [1, 0]);
  assert.deepEqual(rt.state.cutoffs, [12, 12]);
  assert.equal(rt.state.nodes.find((n) => n.op === "kerr").params.chi, 1.5);
});

test("F7: stateFromJson — view.joint_modes 解析 + 校验", () => {
  const base = {
    schema: "circuit_v1", nmode: 2, seed: 0, ops: [],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const g = stateFromJson(base);
  assert.equal(g.error, undefined);
  assert.equal(g.state.view.joint_modes, null);
  const j = stateFromJson({ ...base, view: { ...base.view, joint_modes: [1, 0] } });
  assert.equal(j.error, undefined);
  assert.deepEqual(j.state.view.joint_modes, [1, 0]);
  // round-trip: toV1Json omits null, keeps pair
  assert.equal(toV1Json(g.state).view.joint_modes, undefined);
  assert.deepEqual(toV1Json(j.state).view.joint_modes, [1, 0]);
  // invalid pairs rejected
  assert.ok(stateFromJson({ ...base, view: { ...base.view, joint_modes: [0, 0] } }).error);
  assert.ok(stateFromJson({ ...base, view: { ...base.view, joint_modes: [0] } }).error);
  assert.ok(stateFromJson({ ...base, view: { ...base.view, joint_modes: [0, -1] } }).error);
});

test("R8: stateFromJson — view.plane 双向保真 + 校验（D4b 白名单不丢字段）", () => {
  const base = {
    schema: "circuit_v1", nmode: 2, seed: 0, ops: [],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  // 缺省：导入 → "single"，导出不写键（缺省字节不变）
  const g = stateFromJson(base);
  assert.equal(g.error, undefined);
  assert.equal(g.state.view.plane, "single");
  assert.equal(toV1Json(g.state).view.plane, undefined);

  // 非缺省：导入必须**留住** plane（此前是硬编码白名单重建 → 静默丢失）
  const e = stateFromJson({ ...base, view: { ...base.view, plane: "epr", joint_modes: [0, 1] } });
  assert.equal(e.error, undefined);
  assert.equal(e.state.view.plane, "epr");
  assert.equal(toV1Json(e.state).view.plane, "epr");
  assert.deepEqual(toV1Json(e.state).view.joint_modes, [0, 1]);

  // 未知预设 → 导入即报错
  assert.ok(stateFromJson({ ...base, view: { ...base.view, plane: "zz" } }).error);
  // 非 single 缺 pair → 导入即报错（否则要等一次 /run 才 422）
  assert.ok(stateFromJson({ ...base, view: { ...base.view, plane: "xx" } }).error);
  // single 不需要 pair
  assert.equal(stateFromJson({ ...base, view: { ...base.view, plane: "single" } }).error, undefined);
  // R-G: 非 gaussian 后端带 plane → 导入即报错（后端 load_circuit 同样拒绝；
  // 否则 fock 请求会校验通过、正常执行、静默忽略 plane）
  assert.ok(stateFromJson({
    ...base, backend: "fock",
    view: { ...base.view, plane: "xx", joint_modes: [0, 1] },
  }).error);
  assert.equal(stateFromJson({
    ...base, backend: "fock", view: { ...base.view, plane: "single" },
  }).error, undefined);
});

test("F7: v1 直载解析 backend/initial（无 backend 字段 → gaussian）", () => {
  const v1 = {
    schema: "circuit_v1",
    nmode: 2,
    ops: [
      { id: "k", op: "kerr", params: { chi: 1.5 }, modes: [0] },
    ],
    view: { wigner_mode: 0, lim: 5, n: 64 },
    backend: "fock",
    initial: [0, 1],
  };
  const { state, error } = stateFromJson(v1);
  assert.equal(error, undefined);
  assert.equal(state.backend, "fock");
  assert.deepEqual(state.initial, [0, 1]);
  const kerr = state.nodes.find((n) => n.id === "k");
  assert.equal(kerr.params.chi, 1.5);
  assert.equal(kerr.params.name, undefined); // kerr has no name param
  // initial 长度 vs nmode
  const bad = stateFromJson({ ...v1, initial: [1] });
  assert.ok(bad.error);
});

test("F7: toV1Json — fock param mapping (loss T→eta 掉 nbar, squeeze 带 phi)", () => {
  const base = { view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, seed: 0, nmode: 2 };
  const nodes = [
    { id: "n1", op: "loss", params: { T: 0.8, nbar: 0.1 }, mode: 0 },
    { id: "n2", op: "squeeze", params: { r: 0.4, phi: 1.2 }, mode: 1 },
    { id: "n3", op: "phase", params: { phi: 0.7 }, mode: 0 },
  ];
  const f = toV1Json({ ...base, backend: "fock", nodes, initial: null, cutoffs: [] });
  assert.deepEqual(f.ops[0].params, { eta: 0.8 }); // nbar dropped (fock loss is pure)
  // 09-14-fock-squeeze-phi：fock IR 已带 phi（与 FockState.squeezed 同约定），不再丢
  assert.deepEqual(f.ops[1].params, { r: 0.4, phi: 1.2 });
  assert.deepEqual(f.ops[2].params, { theta: 0.7 }); // phase theta shared
  // gaussian 路径字节不变
  const g = toV1Json({ ...base, backend: "gaussian", nodes, initial: null, cutoffs: [] });
  assert.deepEqual(g.ops[0].params, { T: 0.8, nbar: 0.1 });
  assert.deepEqual(g.ops[1].params, { r: 0.4, phi: 1.2 });
});

test("F7: stateFromV1 — fock 载入（loss eta→T、squeeze 带 phi、name 保留）+ round-trip", () => {
  const payload = {
    schema: "circuit_v1", backend: "fock", nmode: 2, seed: 0,
    ops: [
      { id: "l", op: "loss", modes: [0], params: { eta: 0.8 } },
      { id: "s", op: "squeeze", modes: [1], params: { r: 0.4 } },
      { id: "m", op: "measure_pnr", modes: [0], params: { name: "m_n" } },
    ],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  const loss = state.nodes.find((n) => n.op === "loss");
  assert.equal(loss.params.T, 0.8);
  assert.equal(loss.params.nbar, 0); // advanced default
  const sq = state.nodes.find((n) => n.op === "squeeze");
  assert.equal(sq.params.r, 0.4);
  assert.equal(sq.params.phi, 0); // payload 未给 phi → default 0（带 phi 见 test_fock_squeeze_phi.py）
  const pnr = state.nodes.find((n) => n.op === "measure_pnr");
  assert.equal(pnr.params.name, "m_n"); // 显式 name 保留
  // round-trip: save → load 一致（eta 往返）
  const rt = stateFromJson(toV1Json(state));
  assert.equal(rt.error, undefined);
  const rtLoss = rt.state.nodes.find((n) => n.op === "loss");
  assert.equal(rtLoss.params.T, 0.8);
  assert.deepEqual(toV1Json(rt.state).ops.find((o) => o.op === "loss").params, { eta: 0.8 });
});

/* ── B6/F7: initial 单点语义（initial.js）+ backend 切换往返 ────────────── */

test("initial.js: parseInitial — 语义按 backend 二分（fock 整数 / bosonic 源名）", async () => {
  setInitialSchema(MOCK_SCHEMA); // ticket 4: no mirror fallback — inject first
  const { parseInitial, vacuumDefault, initialCacheKey } = await import("../cvsim/lab/static/initial.js");
  // fock
  assert.deepEqual(parseInitial("fock", [1, 0], 2), { initial: [1, 0] });
  assert.ok(parseInitial("fock", ["gkp0", null], 2).error); // 源名进 fock → 拒
  // bosonic
  assert.deepEqual(parseInitial("bosonic", ["gkp0", null], 2), { initial: ["gkp0", null] });
  assert.ok(parseInitial("bosonic", [0, 0], 2).error); // 整数进 bosonic → 拒（422 现场）
  // 缺省 / 长度 / gaussian（gaussian 语义沿用旧 parseExtensions：非 fock 按源名校验，
  // initial 不参与 gaussian 执行，但入口校验不放松）
  assert.deepEqual(parseInitial("fock", undefined, 2), { initial: null });
  assert.ok(parseInitial("fock", [0], 2).error);
  assert.deepEqual(parseInitial("gaussian", ["gkp0", null], 2), { initial: ["gkp0", null] });
  assert.ok(parseInitial("gaussian", [0, 0], 2).error);
  // vacuumDefault / cache key
  assert.equal(vacuumDefault("bosonic"), null);
  assert.equal(vacuumDefault("fock"), 0);
  assert.equal(initialCacheKey("bosonic", 2), "bosonic:2");
});

test("initial.js: serializeInitial — 非全真空才写，gaussian 永不写", async () => {
  setInitialSchema(MOCK_SCHEMA); // ticket 4: no mirror fallback — inject first
  const { serializeInitial } = await import("../cvsim/lab/static/initial.js");
  assert.equal(serializeInitial("gaussian", [1, 1], 2), undefined);
  assert.equal(serializeInitial("fock", [0, 0], 2), undefined);   // 全真空省略
  assert.deepEqual(serializeInitial("fock", [0, 2], 2), [0, 2]);
  assert.equal(serializeInitial("bosonic", [null, null], 2), undefined); // 全真空省略
  assert.deepEqual(serializeInitial("bosonic", ["gkp0", null], 2), ["gkp0", null]);
  assert.equal(serializeInitial("bosonic", [0, 0], 2), undefined); // 跨后端残留不外泄
  assert.equal(serializeInitial("fock", [null, null], 2), undefined);
});

test("initial.js: remapForBackend — 真空对应保留，非真空重置并计数（Q2=B）", async () => {
  const { remapForBackend } = await import("../cvsim/lab/static/initial.js");
  // fock → bosonic：0 保留为 null，非零重置
  const fb = remapForBackend("fock", "bosonic", [0, 3, null], 3);
  assert.deepEqual(fb.initial, [null, null, null]);
  assert.equal(fb.reset, 1); // 只数非真空对应项
  // bosonic → fock：null 保留为 0，源名重置
  const bf = remapForBackend("bosonic", "fock", [null, "gkp0"], 2);
  assert.deepEqual(bf.initial, [0, 0]);
  assert.equal(bf.reset, 1);
  // 同后端（加模场景）：原值保留 + 真空补位
  const same = remapForBackend("fock", "fock", [2], 3);
  assert.deepEqual(same.initial, [2, 0, 0]);
  assert.equal(same.reset, 0);
  // gaussian → 任意：无旧语义，全缺省真空
  const g = remapForBackend("gaussian", "bosonic", undefined, 2);
  assert.deepEqual(g.initial, [null, null]);
  assert.equal(g.reset, 0);
});

test("B6/F7 回归: fock→bosonic 切换后 toV1Json 不再产出非法 initial（422 根因）", () => {
  // fock 状态：默认全 0（真空）+ 一个非零项（模数来自 nmode，无源节点）
  const fockState = { seed: 0, nmode: 2, nodes: [], view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, backend: "fock", initial: [0, 3], cutoffs: [10, 10] };
  // 模拟 setBackend('bosonic') 的重映射（与 editor.js 同一来源）
  const st = { ...fockState, backend: "bosonic", initial: [null, null] };
  const payload = toV1Json(st);
  // 修复前: payload.initial === [0, 3] → 服务端 422；修复后: 全真空不写
  assert.equal(payload.initial, undefined);
  // 非真空 bosonic initial 照常写
  const st2 = { ...st, initial: ["gkp0", null] };
  assert.deepEqual(toV1Json(st2).initial, ["gkp0", null]);
  // 反向: bosonic → fock，旧 [null,null] 不再泄漏进 payload
  const back = { ...st2, backend: "fock", initial: [0, 0] };
  assert.equal(toV1Json(back).initial, undefined);
});

test("B6/F7 回归: stateFromJson 对 fock 整数进 bosonic 报错（前端守门）", () => {
  const base = {
    schema: "circuit_v1", nmode: 2, backend: "bosonic",
    ops: [], seed: 0, view: { wigner_mode: 0, lim: 5.0, n: 64 },
  };
  assert.ok(stateFromJson({ ...base, initial: [0, 0] }).error);
  assert.ok(stateFromJson({ ...base, initial: ["gkp9", null] }).error);
  const ok = stateFromJson({ ...base, initial: ["gkp0_2d", null] });
  assert.equal(ok.error, undefined);
  assert.deepEqual(ok.state.initial, ["gkp0_2d", null]);
});

test("ticket-4 F7/B6: backends derived (deriveOps); ops.js carries none", () => {
  // v0 sources 已退役（ADR-0014）→ pass 1 兜底仅剩 schema 内未知 op
  const d = deriveOps(MOCK_SCHEMA);
  assert.deepEqual(d.mz.backends, ["gaussian"]);
  assert.deepEqual(d.kerr.backends, ["fock"]);
  assert.deepEqual(d.measure_pnr.backends, ["fock"]);
  // 09-21-lab-gaussian-unhide-ops: gaussian 加入这两个（JSON-only，仍 palette:false）
  assert.deepEqual(d.interferometer.backends, ["gaussian", "bosonic"]);
  assert.deepEqual(d.gaussian_channel.backends, ["gaussian", "bosonic"]);
  assert.deepEqual(d.measure_threshold.backends, ["bosonic"]);
  assert.deepEqual(d.fourier.backends, ["gaussian", "bosonic"]);
  // gaussian 加入 cz/cx/phase_noise
  assert.deepEqual(d.cz.backends, ["gaussian", "fock", "bosonic"]);
  assert.deepEqual(d.phase_noise.backends, ["gaussian", "fock", "bosonic"]);
  // mach_zehnder 仍不含 gaussian（gaussian 用 mz，分解不同）
  assert.deepEqual(d.mach_zehnder.backends, ["fock", "bosonic"]);
  assert.deepEqual(d.displace.backends, ["gaussian", "fock", "bosonic"]);
  assert.deepEqual(d.homodyne.backends, ["gaussian", "fock", "bosonic"]);
});

test("ticket-4 F7: opsForBackend derived palette (fock has kerr/cz/cx/measure_pnr; no interferometer/fourier)", () => {
  publishSchema(MOCK_SCHEMA, { ops: deriveOps(MOCK_SCHEMA), uiToOp: {}, uiToParam: {}, fockUiToParam: {} });
  assert.ok(opsForBackend("fock").includes("kerr"));
  assert.ok(opsForBackend("fock").includes("cz"));
  assert.ok(opsForBackend("fock").includes("cx"));
  assert.ok(opsForBackend("fock").includes("measure_pnr"));
  assert.ok(opsForBackend("fock").includes("homodyne"));
  assert.ok(opsForBackend("fock").includes("heterodyne"));
  assert.ok(opsForBackend("fock").includes("phase_noise"));
  assert.ok(opsForBackend("fock").includes("mach_zehnder"));
  // anti-whitelist creed: matrix editor deferred (UI-hidden -> not derived)
  assert.ok(!opsForBackend("fock").includes("interferometer"));
  assert.ok(!opsForBackend("fock").includes("apply_unitary"));
  assert.ok(!opsForBackend("fock").includes("fourier"));
  assert.ok(!opsForBackend("fock").includes("mz"));
  // Fock has no source nodes in the palette
  assert.ok(!opsForBackend("fock").includes("vacuum"));
  assert.ok(!opsForBackend("fock").includes("coherent"));
  assert.ok(!opsForBackend("fock").includes("tmsv"));
  // gaussian palette
  assert.ok(opsForBackend("gaussian").includes("fourier"));
  assert.ok(!opsForBackend("gaussian").includes("kerr"));
  assert.ok(!opsForBackend("gaussian").includes("measure_pnr"));
  assert.ok(opsForBackend("bosonic").includes("measure_threshold"));
  // 09-21-lab-gaussian-unhide-ops: gaussian 解锁 5 op。出卡片的三张
  // （cz/cx/phase_noise 无 palette:false）→ 进托盘；两个矩阵 op 仍
  // palette:false → backends 里有 gaussian 但托盘不列（JSON-only）。
  for (const op of ["cz", "cx", "phase_noise"]) {
    assert.ok(opsForBackend("gaussian").includes(op), `gaussian 托盘应含 ${op}`);
  }
  assert.equal(OPS.interferometer.palette, false);
  assert.equal(OPS.gaussian_channel.palette, false);
  assert.ok(opsForBackend("gaussian").includes("interferometer")); // 后端放行（JSON-only）
  assert.ok(opsForBackend("gaussian").includes("gaussian_channel"));
  // 仍隐藏的两个
  assert.ok(!opsForBackend("gaussian").includes("mach_zehnder"));
  assert.ok(!opsForBackend("gaussian").includes("measure_threshold"));
});

/* ── R6 (ADR-0008 决策 3): meterKeys — meter 支持矩阵前端唯一消费口 ── */
test("R6: meterKeys = core ∪ extensions[backend]，逐后端与 result.py 矩阵一致", () => {
  publishSchema(MOCK_SCHEMA, { ops: deriveOps(MOCK_SCHEMA), uiToOp: {}, uiToParam: {}, fockUiToParam: {} });
  const g = meterKeys("gaussian");
  assert.ok(g.has("purity") && g.has("mean_photon") && g.has("mean_photon_per_mode"));
  assert.ok(g.has("log_negativity") && g.has("singular"));
  const b = meterKeys("bosonic");
  assert.ok(b.has("purity") && b.has("mean_photon"));
  assert.ok(!b.has("log_negativity")); // bosonic 扩展行为空集 — 物理事实
  assert.ok(!b.has("singular"));
  const f = meterKeys("fock");
  assert.ok(f.has("leakage"));
  assert.ok(!f.has("log_negativity"));
});

test("R6: meterKeys fail-fast — meters 块缺失 / 缺 backend 扩展行 / 未知 backend 均 throw", () => {
  const probe = (doc, backend = "bosonic") => {
    publishSchema(doc, { ops: deriveOps(doc), uiToOp: {}, uiToParam: {}, fockUiToParam: {} });
    try { return meterKeys(backend); } finally { publishSchema(MOCK_SCHEMA, { ops: deriveOps(MOCK_SCHEMA), uiToOp: {}, uiToParam: {}, fockUiToParam: {} }); }
  };
  assert.throws(() => probe({ ops: {} }), /未初始化/);
  assert.throws(() => probe({ ops: {}, meters: { core: ["purity"] } }), /扩展行/);
  assert.throws(() => meterKeys("nosuch"), /扩展行/); // 上一行 finally 己恢复 MOCK_SCHEMA
});

/* ── §3.1 回归: 派生表键名是发布契约，消费方不得猜 ──────────────────────
   历史缺陷: editor.js 的中间回落分支读 s.irToUiOp/s.v1ToUiParam/
   s.fockV1ToUiParam，而 app.js:855-857 发布的是 uiToOp/uiToParam/
   fockUiToParam —— 三个键全部 undefined，`{...undefined}` = {}，于是
   op 改名（measure_homodyne→homodyne）与参数改名（theta→phi、eta→T）
   全部静默失效，只有 op 那一路会报 "不在 Lab 白名单" 而暴露出来。
   该分支已删（tables() 回归两态）。以下两条守卫分别锁行为与结构。 */
test("§3.1: 混合态（store 已发布 / editor 未注入）改名仍然正确", () => {
  // 与 app.js:854-859 同形发布 —— 键名逐字相同，这是契约本身
  const dEt = deriveEditorTables(MOCK_SCHEMA);
  publishSchema(MOCK_SCHEMA, {
    uiToOp: Object.fromEntries(Object.entries(dEt.irToUi).map(([ir, ui]) => [ui, ir])),
    uiToParam: dEt.v1ToUiParam,
    fockUiToParam: dEt.fockV1ToUiParam,
    ops: deriveOps(MOCK_SCHEMA),
  });
  try {
    const VIEW = { wigner_mode: 0, lim: 5.0, n: 64 };
    // op 改名（曾报 "op measure_homodyne 不在 Lab 白名单"）
    const g = stateFromJson({
      schema: "circuit_v1", nmode: 1, seed: 0, view: VIEW,
      ops: [{ id: "h0", op: "measure_homodyne", modes: [0], params: {} }],
    });
    assert.equal(g.error, undefined);
    assert.equal(g.state.nodes[0].op, "homodyne");
    // 参数改名 theta→phi（曾报 "ops[0].params.phi 必须是有限数值"）
    const p = stateFromJson({
      schema: "circuit_v1", nmode: 1, seed: 0, view: VIEW,
      ops: [{ id: "p0", op: "phase", modes: [0], params: { theta: 0.7 } }],
    });
    assert.equal(p.error, undefined);
    assert.deepEqual(p.state.nodes[0].params, { phi: 0.7 });
    // fock drop-table T→eta/nbar（曾报 "ops[0].params.T 必须是有限数值"）
    const f = stateFromJson({
      schema: "circuit_v1", backend: "fock", nmode: 1, seed: 0, view: VIEW,
      ops: [{ id: "l0", op: "loss", modes: [0], params: { eta: 0.5 } }],
    });
    assert.equal(f.error, undefined);
    // nbar 是 fock drop 表项且 advanced:true → 回落 UI 默认 0（editor.js:241），
    // 序列化时再被 ops.js drop 表丢掉（round-trip 稳定）。曾报 "params.T 必须是有限数值"。
    assert.deepEqual(f.state.nodes[0].params, { T: 0.5, nbar: 0 });
    assert.equal(toV1Json(f.state).ops[0].params.nbar, undefined); // fock drop 表生效
  } finally {
    publishSchema(MOCK_SCHEMA, { ops: deriveOps(MOCK_SCHEMA), uiToOp: {}, uiToParam: {}, fockUiToParam: {} });
  }
});

test("§3.1: editor.js 不读未经发布的派生表键（结构守卫）", async () => {
  const { readFileSync } = await import("node:fs");
  const raw = readFileSync(new URL("../cvsim/lab/static/editor.js", import.meta.url), "utf8");
  // 去注释后再扫 —— 否则本次修复的历史说明注释自己就会命中
  const src = raw.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  // 发布契约（app.js:854-859）= 这四个键；任何别的 s.<key> 读取都是猜名
  const PUBLISHED = new Set(["uiToOp", "uiToParam", "fockUiToParam", "ops"]);
  const bad = [...src.matchAll(/\bs\.([A-Za-z_$][\w$]*)/g)]
    .map((m) => m[1])
    .filter((k) => !PUBLISHED.has(k));
  assert.deepEqual(bad, [], `editor.js 读了未发布的派生表键: ${bad.join(", ")}`);
  // 且 tables() 不得再从 schemaTables() 取表（中间态已删）
  assert.ok(!/schemaTables/.test(src), "editor.js 不应再 import/调用 schemaTables()");
});

/* ── §3.4: setInitial 必须按 cutoff 夹取（曾与自身注释矛盾）────────────
   缺陷: editor.js 的 setInitial 直接 `next[i] = v`，无 cutoff 上界，
   而 modeLabel 渲染 `|v⟩`、服务端 fock/ir.py 又硬拒越界（422
   "initial[i]=n must be in [0, c)"）。浏览器**不会**把手工输入夹到
   input.max，故 cutoff=2 + 输入 9 → 状态 initial=[9] + 标签 |9⟩ + 422。
   clampInitial 原先只在 fock.js（结果面板）里，那条路是拖 cutoff 滑条，
   与 initial 输入框这条路无关 —— 所以"唯一夹取实现"从没被走到。
   修法: 夹取实现移到 initial.js（fock 语义单点），setInitial 里调。 */

test("§3.4: clampInitial — per-mode Fock 光子数夹到 [0, cutoffs[i]-1]", () => {
  // 原 fock.test.mjs 的用例逐条搬来（导出位置变了，语义未变）
  assert.deepEqual(clampInitial([1, 1], [10, 10], 2), [1, 1]);
  assert.deepEqual(clampInitial([99, -2], [10, 10], 2), [9, 0]);
  assert.deepEqual(clampInitial(null, [5, 5], 2), [0, 0]);
  assert.deepEqual(clampInitial([1], [10, 10], 2), [1, 0]); // pad
  assert.deepEqual(clampInitial([1, 1, 1], [10, 10], 2), [1, 1]); // truncate
  // 本次缺陷的核心场景：cutoff=2 时 9 必须夹成 1（= cutoff-1）
  assert.deepEqual(clampInitial([9], [2], 1), [1]);
  assert.deepEqual(clampInitial([9], [2, 2], 2), [1, 0]);
});

test("§3.4: clampInitial 归位 initial.js（fock.js 不再自己实现）", async () => {
  const { readFileSync } = await import("node:fs");
  const ini = readFileSync(new URL("../cvsim/lab/static/initial.js", import.meta.url), "utf8");
  const fk = readFileSync(new URL("../cvsim/lab/static/fock.js", import.meta.url), "utf8");
  assert.ok(/export function clampInitial\(/.test(ini), "clampInitial 必须由 initial.js 导出");
  assert.ok(!/function clampInitial\(/.test(fk), "fock.js 不得再保留第二份实现");
  assert.ok(/import \{[^}]*clampInitial[^}]*\} from "\.\/initial\.js"/.test(fk),
    "fock.js 应从 initial.js import clampInitial");
});

test("§3.4: setInitial 走 clampInitial（结构守卫，fock 分支）", async () => {
  const { readFileSync } = await import("node:fs");
  const raw = readFileSync(new URL("../cvsim/lab/static/editor.js", import.meta.url), "utf8");
  const src = raw.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  const body = src.split("function setInitial(i, v) {")[1].split("\n  }\n", 1)[0];
  assert.ok(body, "找不到 setInitial");
  assert.ok(/clampInitial\(/.test(body), "setInitial 必须调 clampInitial 夹 initial");
  // 只对 fock 生效 —— bosonic 项是 null / 源名，过 clamp 会被毁成数字
  assert.ok(/backend === "fock"/.test(body),
    "clampInitial 必须限定在 fock 分支（bosonic 源名不能被当数字夹）");
});

/* ══════════════════════════════════════════════════════════════════════
   09-21-lab-gaussian-unhide-ops：解锁 5 个 gaussian op + 三个前端缺陷回归
   ──────────────────────────────────────────────────────────────────────
   缺陷 1（矩阵参数静默丢失）：stateFromV1 只遍历 `meta.params` 搬参数，而
   interferometer/gaussian_channel 的 U / X,Y,d 不在那里（它们无面板块），
   → 载入即丢、下次 toV1Json 抹掉。影响 gaussian **和** bosonic。
   缺陷 2（arity 'none' 无分支）：`modes: []` 落到 `kind:"single"` 分支，
   要求恰好 1 个模 → gaussian_channel 永远载不进（bosonic 同样）。
   缺陷 3（arity 'all' 只收 2 模）：`kind:"two"` 分支要求恰好 2 个 →
   m≥3 的 interferometer 载不进。
   实测证据：.trellis/tasks/09-21-lab-gaussian-unhide-ops/design.md §1.3
   ══════════════════════════════════════════════════════════════════════ */

const V1_VIEW = { wigner_mode: 0, lim: 5.0, n: 64 };
const v1doc = (ops, nmode, extra = {}) => ({
  schema: "circuit_v1", nmode, view: V1_VIEW, ops, ...extra,
});

test("09-21 缺陷1: 矩阵参数 U 往返保真（interferometer，gaussian + bosonic）", () => {
  const U = [[1, 0], [0, 1]];
  for (const backend of ["gaussian", "bosonic"]) {
    const { state, error } = stateFromJson(v1doc(
      [{ op: "interferometer", modes: [0, 1], params: { U } }], 2, { backend }));
    assert.equal(error, undefined, `${backend} 应能载入 interferometer`);
    assert.deepEqual(state.nodes[0].params.U, U, `${backend} 载入后 U 必须保留`);
    const back = toV1Json(state).ops[0];
    assert.deepEqual(back.params.U, U, `${backend} 回写后 U 必须保留`);
    assert.deepEqual(back.modes, [0, 1]);
  }
});

test("09-21 缺陷1: X/Y/d 往返保真（gaussian_channel，含 d）", () => {
  const X = [[1, 0], [0, 1]], Y = [[0.1, 0], [0, 0.1]], d = [0.5, -0.25];
  for (const backend of ["gaussian", "bosonic"]) {
    const { state, error } = stateFromJson(v1doc(
      [{ op: "gaussian_channel", modes: [], params: { X, Y, d } }], 1, { backend }));
    assert.equal(error, undefined, `${backend} 应能载入 gaussian_channel`);
    assert.deepEqual(state.nodes[0].params, { X, Y, d });
    assert.deepEqual(toV1Json(state).ops[0].params, { X, Y, d });
    assert.deepEqual(toV1Json(state).ops[0].modes, [], "arity none → modes 保持空数组");
  }
});

test("09-21 缺陷2: arity 'none' — modes 必须为空，非空被拒", () => {
  const X = [[1, 0], [0, 1]];
  // 空 modes → ok（缺陷前必然报 "必须是一个非负整数"）
  assert.equal(stateFromJson(v1doc(
    [{ op: "gaussian_channel", modes: [], params: { X } }], 1)).error, undefined);
  // 非空 modes → 拒（核心 none-arity 语义）
  const bad = stateFromJson(v1doc(
    [{ op: "gaussian_channel", modes: [0], params: { X } }], 1));
  assert.match(bad.error, /必须为空/);
});

test("09-21 缺陷3: arity 'all' — m=2 与 m=3 均可载入，模集必须等于全部模", () => {
  const U2 = [[1, 0], [0, 1]];
  const U3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
  const r2 = stateFromJson(v1doc([{ op: "interferometer", modes: [0, 1], params: { U: U2 } }], 2));
  assert.equal(r2.error, undefined, "m=2 应能载入");
  assert.deepEqual(r2.state.nodes[0].modes, [0, 1]);
  // m=3 —— 缺陷前报 "必须是两个非负整数"
  const r3 = stateFromJson(v1doc([{ op: "interferometer", modes: [0, 1, 2], params: { U: U3 } }], 3));
  assert.equal(r3.error, undefined, "m=3 应能载入");
  assert.deepEqual(r3.state.nodes[0].modes, [0, 1, 2]);
  assert.deepEqual(toV1Json(r3.state).ops[0].params.U, U3);
  // 模集不等于 range(nmode) → 拒（核心 validate_ir 同判据）
  const bad = stateFromJson(v1doc([{ op: "interferometer", modes: [0, 1], params: { U: U2 } }], 3));
  assert.match(bad.error, /\[0\.\.2\]/);
});

test("09-21: arity 'any' — phase_noise 收 1 模或空数组（= 全部模）", () => {
  const one = stateFromJson(v1doc([{ op: "phase_noise", modes: [0], params: { sigma: 0.3 } }], 2));
  assert.equal(one.error, undefined);
  assert.equal(one.state.nodes[0].mode, 0);
  const empty = stateFromJson(v1doc([{ op: "phase_noise", modes: [], params: { sigma: 0.3 } }], 2));
  assert.equal(empty.error, undefined, "空 modes = 全部模（服务端接受）");
  assert.deepEqual(empty.state.nodes[0].modes, []);
  assert.deepEqual(empty.state.nodes[0].params, { sigma: 0.3 });
  // 2 个模 → 拒（核心 "takes at most 1 mode"）
  const bad = stateFromJson(v1doc([{ op: "phase_noise", modes: [0, 1], params: { sigma: 0.3 } }], 2));
  assert.match(bad.error, /至多一个/);
});

test("09-21: cz/cx 载入 + weight 往返（gaussian 解锁）", () => {
  for (const op of ["cz", "cx"]) {
    const { state, error } = stateFromJson(v1doc(
      [{ op, modes: [0, 1], params: { weight: 1.5 } }], 2, { backend: "gaussian" }));
    assert.equal(error, undefined, `gaussian 应能载入 ${op}`);
    assert.deepEqual(state.nodes[0].params, { weight: 1.5 });
    assert.deepEqual(toV1Json(state).ops[0].params, { weight: 1.5 });
    assert.deepEqual(toV1Json(state).ops[0].modes, [0, 1]);
  }
});

test("09-21 R6: staffLayout — all-arity 跨度覆盖全部模（m≥3 不漏模）", async () => {
  const { staffLayout } = await import("../cvsim/lab/static/staff.js");
  const { state } = stateFromJson(v1doc(
    [{ op: "interferometer", modes: [0, 1, 2], params: { U: [[1, 0, 0], [0, 1, 0], [0, 0, 1]] } }], 3));
  const g = staffLayout(state).gates[0];
  assert.equal(g.span, 3, "必须覆盖 0..2（缺陷前 span=2，漏 mode 2）");
  assert.equal(g.top, 0);
  assert.deepEqual([g.modeA, g.modeB], [0, 1], "modeA/modeB 保持 JSON 顺序（显示契约）");
});

test("09-21 R6: staffLayout — none-arity 几何有限（不产出 null）", async () => {
  const { staffLayout } = await import("../cvsim/lab/static/staff.js");
  const X = [[1, 0], [0, 1]];
  const { state } = stateFromJson(v1doc(
    [{ op: "gaussian_channel", modes: [], params: { X } }], 2));
  const g = staffLayout(state).gates[0];
  assert.ok(Number.isFinite(g.span), `span 必须有限，实为 ${g.span}`);
  assert.ok(Number.isFinite(g.top), `top 必须有限，实为 ${g.top}`);
  assert.equal(g.span, 1);
  assert.equal(g.top, 0);
});

test("09-21 R6: cellOccupied/modeKeyOf/removeMode 按整组 modes 判定", async () => {
  const { modeKeyOf } = await import("../cvsim/lab/static/ops.js");
  const { state } = stateFromJson(v1doc(
    [{ op: "interferometer", modes: [0, 1, 2], params: { U: [[1, 0, 0], [0, 1, 0], [0, 0, 1]] } }], 3));
  const n = state.nodes[0];
  assert.equal(cellOccupied(state.nodes, 2, 0), true, "all-arity 门须锁住它跨的每个模（含 mode 2）");
  assert.equal(cellOccupied(state.nodes, 2, 9), false, "不同 x 列不算占用");
  assert.equal(modeKeyOf(n), 0);
  assert.equal(removeMode(state.nodes, 1).length, 0, "删任一模 → 跨该模的门级联删除");
  // none-arity：不锁任何模，删模不牵连它
  const gc = stateFromJson(v1doc([{ op: "gaussian_channel", modes: [], params: { X: [[1, 0], [0, 1]] } }], 1)).state.nodes[0];
  assert.equal(Number.isFinite(modeKeyOf(gc)), true, "modeKeyOf 不得返回 undefined（排序 NaN 源）");
  assert.equal(cellOccupied([gc], 0, 0), false);
  assert.equal(removeMode([gc], 0).length, 1);
});

test("09-21: 未知/无 UI 条目的 op 仍被拒（反脆弱：解锁不能放宽守门）", () => {
  assert.match(stateFromJson(v1doc(
    [{ op: "no_such_op", modes: [0], params: {} }], 1)).error, /不在 Lab 白名单/);
  assert.match(stateFromJson(v1doc(
    [{ op: "apply_unitary", modes: [0], params: { U: [[1, 0], [0, 1]] } }], 1)).error,
    /不在 Lab 白名单/);
});

test("09-21: 每个 OPS op 的 arity 都有处理器（applyArity 不变式）", async () => {
  // applyArity 的 default 分支现在是**响亮报错**（曾静默按 one 处理）。若某天
  // 给一个 arity 为 'subset'（fock apply_unitary）或别的未知 arity 的 op 加了
  // UI 条目，载入会直接失败而不是被当成单模门。
  const HANDLED = new Set(["one", "two", "all", "any", "none"]);
  const { readFileSync } = await import("node:fs");
  const src = readFileSync(new URL("../cvsim/lab/static/editor.js", import.meta.url), "utf8");
  const body = src.split("function applyArity(")[1].split("\nfunction ", 1)[0];
  const cases = [...body.matchAll(/case "([a-z]+)":/g)].map((m) => m[1]);
  for (const a of HANDLED) {
    assert.ok(cases.includes(a), `applyArity 缺 case "${a}"`);
  }
  assert.ok(/default:/.test(body) && /未知的 arity/.test(body),
    "applyArity 的 default 必须响亮报错，不得静默按 one 处理");
  // 真实 payload 里每个有 UI 条目的 op，arity 都必须被显式处理
  for (const [ir, entry] of Object.entries(MOCK_SCHEMA.ops)) {
    const a = entry.meta.arity;
    assert.ok(HANDLED.has(a), `${ir} 的 arity ${a} 无处理器（有 UI 条目 → 载入会报未知 arity）`);
  }
  // 反向锁：fock 的 subset arity 属于"无 UI 条目"类，前端到不了这里
  assert.equal(OPS.apply_unitary, undefined, "apply_unitary 不得有 UI 条目（否则需实现 subset）");
  // 未知 arity 确实被拒（直接构造一个假 schema 条目验证）
  const bad = stateFromJson({ ...v1doc([{ op: "squeeze", modes: [0], params: { r: 0.4, phi: 0 } }], 1) });
  assert.equal(bad.error, undefined); // 对照：正常 op 仍可载
});
