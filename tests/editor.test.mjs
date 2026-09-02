/* Gaussian Lab L2–L5 — pure editor logic tests (node --test, zero deps). */
import test from "node:test";
import assert from "node:assert/strict";

import {
  OPS, OP_NAMES, TAU, paramsFromOp, sourceModes, opGroup, backendOps,
  FOCK_PALETTE, GAUSSIAN_PALETTE,
  addNode, removeNode, placeSingle, completePlacing, moveNodeX,
  sortNodes, sourceRows, removeSource, updateParam, updateMode, toV1Json,
  cellOccupied,
} from "../cvsim/lab/static/ops.js";
import { stateFromJson, loadJson, createHistory } from "../cvsim/lab/static/editor.js";

const EXPECTED_OPS = ["vacuum", "tmsv", "coherent", "squeeze", "phase", "fourier", "displace", "loss", "beamsplitter", "heterodyne", "homodyne", "amplifier", "mz", "two_mode_squeeze", "kerr", "cz", "cx", "mach_zehnder", "phase_noise", "measure_pnr", "interferometer", "gaussian_channel", "measure_threshold"];

test("ops metadata: 23 ops (B6 +3 bosonic JSON-only / threshold) (tmsv/coherent kept for JSON compat, palette:false)", () => {
  assert.deepEqual([...OP_NAMES].sort(), [...EXPECTED_OPS].sort());
  assert.equal(OPS.tmsv.palette, false); // legacy source: loadable, not in palette
  assert.equal(OPS.coherent.palette, false); // L5.5: unified into vacuum + displace gate
});

test("UX: opGroup — source/gate/channel/measure, palette:false → null", () => {
  assert.equal(opGroup("vacuum"), "source");
  assert.equal(opGroup("tmsv"), null); // palette:false
  assert.equal(opGroup("coherent"), null); // palette:false
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

test("F7/B6: backends metadata — per-backend palette tables", () => {
  // gaussian-only
  assert.deepEqual(OPS.vacuum.backends, ["gaussian"]);
  assert.deepEqual(OPS.mz.backends, ["gaussian"]);
  // fock-only
  assert.deepEqual(OPS.kerr.backends, ["fock"]);
  assert.deepEqual(OPS.measure_pnr.backends, ["fock"]);
  // bosonic-only
  assert.deepEqual(OPS.interferometer.backends, ["bosonic"]);
  assert.deepEqual(OPS.gaussian_channel.backends, ["bosonic"]);
  assert.deepEqual(OPS.measure_threshold.backends, ["bosonic"]);
  // gaussian + bosonic
  assert.deepEqual(OPS.fourier.backends, ["gaussian", "bosonic"]);
  // fock + bosonic（cz/cx/phase_noise/mach_zehnder 亦 bosonic）
  assert.deepEqual(OPS.cz.backends, ["fock", "bosonic"]);
  assert.deepEqual(OPS.cx.backends, ["fock", "bosonic"]);
  assert.deepEqual(OPS.phase_noise.backends, ["fock", "bosonic"]);
  assert.deepEqual(OPS.mach_zehnder.backends, ["fock", "bosonic"]);
  // shared three-backend
  assert.deepEqual(OPS.displace.backends, ["gaussian", "fock", "bosonic"]);
  assert.deepEqual(OPS.beamsplitter.backends, ["gaussian", "fock", "bosonic"]);
  assert.deepEqual(OPS.homodyne.backends, ["gaussian", "fock", "bosonic"]);
  // every op declares its backend table
  for (const op of OP_NAMES) {
    assert.ok(Array.isArray(OPS[op].backends) && OPS[op].backends.length > 0, `${op} 缺 backends`);
  }
});

test("F7: backendOps — Fock 托盘集正确（含 kerr/cz/cx/measure_pnr，无 interferometer/apply_unitary/fourier）", () => {
  assert.deepEqual(backendOps("fock").sort(), [...FOCK_PALETTE]);
  assert.ok(backendOps("fock").includes("kerr"));
  assert.ok(backendOps("fock").includes("cz"));
  assert.ok(backendOps("fock").includes("cx"));
  assert.ok(backendOps("fock").includes("measure_pnr"));
  assert.ok(backendOps("fock").includes("homodyne"));
  assert.ok(backendOps("fock").includes("heterodyne"));
  assert.ok(backendOps("fock").includes("phase_noise"));
  assert.ok(backendOps("fock").includes("mach_zehnder"));
  // 反白名单教义：矩阵编辑器 defer
  assert.ok(!backendOps("fock").includes("interferometer"));
  assert.ok(!backendOps("fock").includes("apply_unitary"));
  assert.ok(!backendOps("fock").includes("fourier"));
  assert.ok(!backendOps("fock").includes("mz"));
  // Fock 无源节点托盘
  assert.ok(!backendOps("fock").includes("vacuum"));
  assert.ok(!backendOps("fock").includes("coherent"));
  assert.ok(!backendOps("fock").includes("tmsv"));
  // gaussian 托盘
  assert.deepEqual(backendOps("gaussian").sort(), [...GAUSSIAN_PALETTE]);
  assert.ok(backendOps("gaussian").includes("fourier"));
  assert.ok(!backendOps("gaussian").includes("kerr"));
  assert.ok(!backendOps("gaussian").includes("measure_pnr"));
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
  assert.equal(OPS.tmsv.params.r.step <= 0.01, true);
  assert.equal(OPS.vacuum.kind, "source");
  assert.equal(OPS.vacuum.modes, 1);
  assert.equal(OPS.vacuum.params.nmode.def, 1);
  assert.ok(OPS.vacuum.params.nmode.advanced);
});

test("addNode appends with defaults + mode + x", () => {
  let nodes = [];
  nodes = addNode(nodes, "vacuum");
  assert.equal(nodes.length, 1);
  assert.equal(nodes[0].op, "vacuum");
  assert.equal(nodes[0].params.nmode, 1);
  assert.equal(nodes[0].mode, undefined); // source: no mode field
  nodes = addNode(nodes, "loss");
  assert.equal(nodes[1].mode, 0);
  assert.equal(nodes[1].ui.x, 0); // first gate x=0
  assert.ok(!("ui" in nodes[0])); // source carries no layout
  nodes = addNode(nodes, "beamsplitter");
  assert.deepEqual(nodes[2].modes, [0, 1]);
  assert.equal(nodes[2].ui.x, 1); // appended after loss
  assert.deepEqual(nodes.map((n) => n.op), ["vacuum", "loss", "beamsplitter"]); // source first
});

test("sourceModes: vacuum=1, coherent=1 (tmsv legacy=2)", () => {
  let nodes = [];
  nodes = addNode(nodes, "vacuum");
  nodes = addNode(nodes, "coherent");
  assert.equal(sourceModes(nodes), 2);
  // legacy JSON vacuum with nmode>1
  nodes = [{ id: "v", op: "vacuum", params: { nmode: 4 } }];
  assert.equal(sourceModes(nodes), 4);
});

test("removeNode incl. bounds", () => {
  let nodes = [];
  for (const op of ["vacuum", "loss", "loss"]) nodes = addNode(nodes, op);
  const [a, b, c] = nodes;
  assert.deepEqual(removeNode(nodes, b.id).map((n) => n.id), [a.id, c.id]);
});

test("L5: sortNodes — (x, mode) order, sources first", () => {
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
  // sources always leftmost, stable among themselves
  const vac = { id: "v0", op: "vacuum", params: { nmode: 1 } };
  const coh = { id: "c0", op: "coherent", params: { alpha: 1 } };
  assert.deepEqual(sortNodes([s0, vac, coh]).map((n) => n.id), [vac.id, coh.id, s0.id]);
});

test("L5.5: placeSingle — snaps x to nearest integer column (round)", () => {
  let nodes = addNode([], "vacuum");
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
    { id: "v0", op: "vacuum", params: {} },
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
  let nodes = addNode([], "vacuum");
  nodes = addNode(nodes, "vacuum"); // 2 modes
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
  let nodes = addNode([], "vacuum");
  nodes = placeSingle(nodes, "phase", 0, 1);
  nodes = placeSingle(nodes, "squeeze", 0, 2);
  const [ph, sq] = nodes.slice(1);
  const moved = moveNodeX(nodes, sq.id, 0.4); // squeeze snaps to 0, now before phase
  assert.deepEqual(moved.slice(1).map((n) => n.op), ["squeeze", "phase"]);
  assert.equal(moved[1].ui.x, 0); // round(0.4)
  assert.equal(moveNodeX(nodes, sq.id, "x").length, nodes.length); // NaN rejected
  // same-column move keeps order
  const sameCol = moveNodeX(nodes, ph.id, 1.4);
  assert.equal(sameCol[1].ui.x, 1);
});

test("L5: sourceRows — vacuum nmode lanes, coherent/tmsv legacy", () => {
  const nodes = [
    { id: "v1", op: "vacuum", params: { nmode: 2 } },
    { id: "c", op: "coherent", params: { alpha: 1 } },
    { id: "t", op: "tmsv", params: { r: 0.5 } }, // legacy JSON only
  ];
  const rows = sourceRows(nodes);
  assert.deepEqual(rows.map((r) => [r.srcId, r.modeStart, r.modeEnd]), [
    ["v1", 0, 2], ["c", 2, 3], ["t", 3, 5],
  ]);
  assert.equal(sourceModes(nodes), 5);
});

test("L5: staffLayout — reversed two-mode (modeB<modeA) spans correctly", async () => {
  const { staffLayout } = await import("../cvsim/lab/static/staff.js");
  const state = {
    nodes: [
      { id: "v0", op: "vacuum", params: {} },
      { id: "v1", op: "vacuum", params: {} },
      { id: "v2", op: "vacuum", params: {} },
      { id: "bs", op: "beamsplitter", params: { theta: 0.5 }, modes: [2, 0], ui: { x: 1 } },
    ],
    view: {}, ui: {},
  };
  const { rows, gates } = staffLayout(state);
  assert.equal(rows.length, 3);
  assert.equal(gates.length, 1);
  assert.equal(gates[0].span, 3); // |2-0|+1
  assert.equal(gates[0].top, 0);
  assert.equal(gates[0].modeA, 2); // JSON order preserved
  assert.equal(gates[0].modeB, 0);
});

test("L5: removeSource — cascades gates on its lanes only", () => {
  const nodes = [
    { id: "v0", op: "vacuum", params: {} },                    // lane 0
    { id: "v1", op: "vacuum", params: {} },                    // lane 1
    { id: "p0", op: "phase", params: { phi: 1 }, mode: 0, ui: { x: 1 } },
    { id: "p1", op: "squeeze", params: { r: 0.4 }, mode: 1, ui: { x: 1 } },
    { id: "bs", op: "beamsplitter", params: { theta: 0.5 }, modes: [0, 1], ui: { x: 2 } },
    { id: "coh", op: "coherent", params: { alpha: 1 } },
    { id: "d", op: "displace", params: { alpha: 1 }, mode: 2, ui: { x: 3 } },
  ];
  const { nodes: kept, removed } = removeSource(nodes, "v0");
  assert.deepEqual(removed, ["v0", "p0", "bs"]); // gate on lane 0 + cross-lane two-mode
  assert.deepEqual(kept.map((n) => n.id), ["v1", "p1", "coh", "d"]);
  // unknown source: no-op
  assert.equal(removeSource(nodes, "nope").nodes.length, nodes.length);
});

test("L5: removeSource — remaps surviving gates below the deleted row", () => {
  // lanes: va=0, vb=1（删）, vc=2, vd(tmsv)=3..4；删后 vd 提供 2..3，下方门全部 -1
  const nodes = [
    { id: "va", op: "vacuum", params: {} },
    { id: "vb", op: "vacuum", params: {} },
    { id: "vc", op: "vacuum", params: {} },
    { id: "vd", op: "tmsv", params: { r: 0.6 } },
    { id: "pa", op: "phase", params: { phi: 1 }, mode: 0, ui: { x: 1 } },
    { id: "pb", op: "squeeze", params: { r: 0.4 }, mode: 1, ui: { x: 1 } },
    { id: "pc", op: "phase", params: { phi: 2 }, mode: 2, ui: { x: 2 } },
    { id: "bs", op: "beamsplitter", params: { theta: 0.5 }, modes: [2, 3], ui: { x: 3 } },
    { id: "czg", op: "cz", params: {}, modes: [3, 4], ui: { x: 4 } },
  ];
  const { nodes: kept, removed } = removeSource(nodes, "vb");
  assert.deepEqual(removed, ["vb", "pb"]); // lane 1 上的门级联删除
  const byId = Object.fromEntries(kept.map((n) => [n.id, n]));
  assert.deepEqual(kept.map((n) => n.id), ["va", "vc", "vd", "pa", "pc", "bs", "czg"]);
  assert.equal(byId.pa.mode, 0);           // 删除行上方不动
  assert.equal(byId.pc.mode, 1);           // 下方单模门 -1
  assert.deepEqual(byId.bs.modes, [1, 2]); // 下方双模门整体 -1
  assert.deepEqual(byId.czg.modes, [2, 3]);
  assert.equal(sourceModes(kept), 4);      // nmode 5 → 4
});

test("L5: toV1Json — v1 payload, sources expanded, no ui.x on ops", () => {
  let nodes = addNode([], "vacuum");
  nodes = placeSingle(nodes, "phase", 0, 3.5);
  nodes = addNode(nodes, "loss");
  nodes = nodes.map((n) => (n.op === "loss" ? { ...n, mode: 1 } : n));
  const payload = toV1Json({ nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.schema, "circuit_v1");
  assert.equal(payload.nmode, 1); // vacuum(1) counts nmode
  assert.deepEqual(payload.ops.map((o) => o.op), ["phase", "loss"]);
  assert.deepEqual(payload.ops[0].params, { theta: Math.PI / 2 }); // phase phi → theta (placeSingle uses default param)
  assert.deepEqual(payload.ops[1].modes, [1]); // mode → modes
  assert.ok(!("ui" in payload.ops[0]) && !("edges" in payload));
  assert.deepEqual(payload.ui, { staff: { n1: 4, n2: 5 } }); // staff layout in ui extension
  const st = stateFromJson(payload);
  assert.deepEqual(st.state.nodes.filter((n) => n.op !== "vacuum").map((n) => n.ui.x), [4, 5]);
});

test("L5: stateFromJson — missing ui.x falls back to array index", () => {
  const legacy = {
    schema: "circuit_v0",
    nodes: [
      { id: "s", op: "vacuum", params: {} },
      { id: "a", op: "phase", params: { phi: 1 }, mode: 0 },
      { id: "b", op: "squeeze", params: { r: 0.4, phi: 0 }, mode: 1 },
    ],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const { state, error } = stateFromJson(legacy);
  assert.equal(error, undefined);
  assert.deepEqual(state.nodes.map((n) => n.ui?.x), [undefined, 0, 1]); // source layout-free
  // explicit ui.x honored (snapped to integer column)
  const withX = { ...legacy, nodes: [{ ...legacy.nodes[1], ui: { x: 7.5 } }] };
  const { state: sx } = stateFromJson(withX);
  assert.equal(sx.nodes[0].ui.x, 8); // round(7.5)
  // round-trip: ui.x survives
  const rt = stateFromJson(toV1Json(state));
  assert.deepEqual(rt.state.nodes.map((n) => n.ui?.x), [undefined, 0, 1]);
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
    nodes: [{ id: "n0", op: "vacuum", params: {} }],
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  const { state } = stateFromJson(payload);
  const grown = addNode(state.nodes, "loss");
  assert.equal(grown[1].id, "n0"); // vac0 does not occupy the n-prefix
  // __proto__ / constructor must not pass the whitelist
  assert.ok(stateFromJson({ schema: "circuit_v0", nodes: [{ id: "x", op: "__proto__", params: {} }] }).error);
  assert.ok(stateFromJson({ schema: "circuit_v0", nodes: [{ id: "x", op: "constructor", params: {} }] }).error);
  // duplicate ids rejected
  const dup = { schema: "circuit_v0", nodes: [
    { id: "a", op: "vacuum", params: {} },
    { id: "a", op: "loss", params: { T: 0.9 }, mode: 0 },
  ] };
  assert.ok(stateFromJson(dup).error);
  // malformed param freezes instead of silently defaulting
  const bad = { schema: "circuit_v0", nodes: [{ id: "a", op: "squeeze", params: { r: "x" } }] };
  assert.ok(stateFromJson(bad).error);
});

test("toV1Json: circuit_v1 payload (ADR-0003)", () => {
  let nodes = [];
  nodes = addNode(nodes, "vacuum");
  nodes = addNode(nodes, "loss");
  nodes = nodes.map((n) => (n.id === nodes[1].id ? { ...n, mode: 1 } : n));
  const payload = toV1Json({ nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.schema, "circuit_v1");
  assert.equal(payload.nmode, 1);
  assert.ok(!("edges" in payload));
  assert.deepEqual(payload.ops[0].op, "loss");
  assert.deepEqual(payload.ops[0].modes, [1]);
  assert.equal(payload.ops.length, 1); // vacuum folded into nmode
});

test("stateFromJson: valid payload round-trips", () => {
  const payload = toV1Json({
    nodes: addNode(addNode([], "vacuum"), "loss"),
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes.length, 2);
  assert.equal(state.nodes[1].op, "loss");
  assert.equal(state.nodes[0].params.nmode, 1); // v1 nmode → implicit vacuum source
});

test("stateFromJson: rejects unknown op / wrong schema", () => {
  assert.ok(stateFromJson({ schema: "nope", nodes: [] }).error);
  assert.ok(stateFromJson({ schema: "circuit_v0", nodes: [{ id: "x", op: "mach_zehnder", params: {} }] }).error);
  assert.ok(stateFromJson(null).error);
  assert.ok(stateFromJson({ schema: "circuit_v0", nodes: "nope" }).error);
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
    nodes: addNode([], "vacuum"),
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  assert.equal(payload.seed, 42);
});

test("L3: stateFromJson accepts seed + homodyne optional phi", () => {
  const payload = {
    schema: "circuit_v0",
    seed: 7,
    nodes: [
      { id: "a", op: "vacuum", params: {} },
      { id: "b", op: "homodyne", params: { phi: 1.5 }, mode: 0 },
      { id: "c", op: "homodyne", params: {}, mode: 1 },
    ],
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.seed, 7);
  assert.equal(state.nodes[1].params.phi, 1.5);
  assert.equal(state.nodes[2].params.phi, 0); // missing phi → default 0
  // round-trip
  const rt = stateFromJson(toV1Json(state));
  assert.equal(rt.error, undefined);
  assert.equal(rt.state.seed, 7);
  assert.equal(rt.state.nodes[1].params.phi, 1.5);
});

test("L3: stateFromJson rejects invalid seed", () => {
  const base = { schema: "circuit_v0", seed: 0, nodes: [{ id: "a", op: "vacuum", params: {} }], view: { wigner_mode: 0, lim: 5, n: 64 } };
  assert.equal(stateFromJson(base).error, undefined); // seed 0 is valid (positive baseline)
  assert.ok(stateFromJson({ ...base, seed: -1 }).error);
  assert.ok(stateFromJson({ ...base, seed: 1.5 }).error);
  assert.ok(stateFromJson({ ...base, seed: "x" }).error);
});

test("L3: loadJson validates without mutating old state", () => {
  const good = { schema: "circuit_v0", seed: 3, nodes: [{ id: "a", op: "vacuum", params: {} }], view: { wigner_mode: 0, lim: 5, n: 64 } };
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
  assert.equal(OPS.coherent.params.alpha.sweep, undefined);
  assert.equal(OPS.displace.params.alpha.sweep, undefined);
  assert.equal(OPS.vacuum.params.nmode.sweep, undefined); // structural, not sweepable
  assert.deepEqual(OPS.squeeze.params.r.sweep, [0, 2]);
  assert.deepEqual(OPS.loss.params.T.sweep, [0, 1]);
  assert.deepEqual(OPS.beamsplitter.params.theta.sweep, [0, Math.PI]);
  assert.deepEqual(OPS.phase.params.phi.sweep, [0, Math.PI]);
  assert.deepEqual(OPS.two_mode_squeeze.params.r.sweep, [0, 2]);
});

test("L4: stateFromJson accepts amplifier/mz", () => {
  const payload = {
    schema: "circuit_v0",
    seed: 0,
    nodes: [
      { id: "s", op: "vacuum", params: {} },
      { id: "a", op: "amplifier", params: { G: 2 }, mode: 0 },
      { id: "m", op: "mz", params: { theta: 0.5, phi: 0.3 }, modes: [0, 1] },
    ],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes[1].params.nbar, 0); // advanced default filled
  assert.equal(state.nodes[2].params.theta, 0.5);
  const rt = stateFromJson(toV1Json(state));
  assert.equal(rt.error, undefined);
  // missing required G freezes
  const noG = { ...payload, nodes: [{ id: "a", op: "amplifier", params: {}, mode: 0 }] };
  assert.ok(stateFromJson(noG).error);
});

test("stateFromJson: missing params freeze (frozen-graph policy)", () => {
  const { error } = stateFromJson({ schema: "circuit_v0", nodes: [{ id: "x", op: "squeeze", params: {} }] });
  assert.ok(error);
  assert.ok(error.includes("r"));
});

test("fourier gate: palette-visible gate, JSON round-trip loadable", () => {
  assert.equal(opGroup("fourier"), "gate");
  assert.deepEqual(Object.keys(OPS.fourier.params), []); // no knobs
  const payload = {
    schema: "circuit_v0", seed: 0,
    nodes: [
      { id: "s", op: "vacuum", params: { nmode: 1 } },
      { id: "f", op: "fourier", params: {}, mode: 0, ui: { x: 0 } },
    ],
    view: { wigner_mode: 0, lim: 5, n: 64 },
  };
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes[1].op, "fourier");
  assert.equal(state.nodes[1].ui.x, 0);
  const rt = stateFromJson(toV1Json(state)); // save → load round-trip
  assert.equal(rt.error, undefined);
  assert.equal(rt.state.nodes[1].op, "fourier");
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

test("v1: toV1Json expands tmsv/coherent sources", () => {
  let nodes = addNode([], "tmsv");
  nodes = addNode(nodes, "coherent");
  const payload = toV1Json({ nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.nmode, 3); // tmsv 2 + coherent 1
  assert.deepEqual(payload.ops.map((o) => o.op), ["two_mode_squeeze", "displace"]);
  assert.deepEqual(payload.ops[0].modes, [0, 1]);
  assert.deepEqual(payload.ops[1].modes, [2]);
  assert.equal(payload.ops[0].params.r, 0.6);
});

test("v1: toV1Json maps measure ops + keeps measurement order", () => {
  const nodes = [
    addNode([], "vacuum")[0],
    { id: "n1", op: "homodyne", params: { phi: 1.2 }, mode: 0 },
    { id: "n2", op: "heterodyne", params: {}, mode: 1 },
  ];
  const payload = toV1Json({ nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.deepEqual(payload.ops.map((o) => o.op), ["measure_homodyne", "measure_heterodyne"]);
  assert.equal(payload.ops[0].params.phi, 1.2);
});

test("v1: stateFromJson inverts native v1 doc (implicit vacuum, op remap)", () => {
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
  assert.equal(state.nodes.length, 4); // vacuum source + 3 ops
  assert.equal(state.nodes[0].op, "vacuum");
  assert.equal(state.nodes[0].params.nmode, 3);
  assert.equal(state.nodes[0].ui, undefined); // source layout-free
  assert.deepEqual(state.nodes.map((n) => n.op), ["vacuum", "two_mode_squeeze", "heterodyne", "phase"]);
  assert.deepEqual(state.nodes[3].params, { phi: 0.7 }); // theta → phi
  assert.equal(state.nodes[2].mode, 1);
  // round-trip back to v1 is stable
  const again = toV1Json(state);
  assert.equal(again.nmode, 3);
  assert.deepEqual(again.ops.map((o) => o.op), ["two_mode_squeeze", "measure_heterodyne", "phase"]);
});

test("v1: stateFromJson rejects core-only ops (Lab whitelist)", () => {
  const payload = {
    schema: "circuit_v1", nmode: 2,
    ops: [{ op: "interferometer", modes: [0, 1], params: { U: [[1, 0], [0, 1]] } }],
  };
  assert.ok(stateFromJson(payload).error);
  const au = {
    schema: "circuit_v1", nmode: 1,
    ops: [{ op: "apply_unitary", modes: [0], params: { U: [[1, 0], [0, 1]] } }],
  };
  assert.ok(stateFromJson(au).error); // 矩阵编辑器 defer（反白名单教义）
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
  const st = { seed: 0, nodes: addNode([], "vacuum"), view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, backend: "gaussian", initial: null, cutoffs: [10] };
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
    nodes: addNode(addNode([], "vacuum"), "vacuum"),
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
    addNode([], "vacuum")[0],
    { id: "n1", op: "homodyne", params: { phi: 1.2 }, mode: 0 },
    { id: "n2", op: "heterodyne", params: {}, mode: 1 },
    { id: "n3", op: "measure_pnr", params: { name: "" }, mode: 2 },
  ];
  const payload = toV1Json({ nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, backend: "fock" });
  assert.equal(payload.ops[0].params.name, "n1"); // 未命名 → 节点 id
  assert.equal(payload.ops[1].params.name, "n2");
  assert.equal(payload.ops[2].params.name, "n3");
  // 显式载入的 name 保留
  const named = toV1Json({
    nodes: [{ id: "n9", op: "measure_pnr", params: { name: "m_n" }, mode: 0 }],
    view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, backend: "fock",
  });
  assert.equal(named.ops[0].params.name, "m_n");
});

test("F7: stateFromJson — backend/initial/cutoff 解析 + 校验", () => {
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

test("F7: v0 路径同样解析 backend/initial（无 backend 字段 → gaussian）", () => {
  const v0 = {
    schema: "circuit_v0",
    nodes: [
      { id: "s", op: "vacuum", params: { nmode: 2 } },
      { id: "k", op: "kerr", params: { chi: 1.5 }, mode: 0 },
    ],
    view: { wigner_mode: 0, lim: 5, n: 64 },
    backend: "fock",
    initial: [0, 1],
  };
  const { state, error } = stateFromJson(v0);
  assert.equal(error, undefined);
  assert.equal(state.backend, "fock");
  assert.deepEqual(state.initial, [0, 1]);
  assert.equal(state.nodes[1].params.chi, 1.5);
  assert.equal(state.nodes[1].params.name, undefined); // kerr has no name param
  // initial 长度 vs v0 源计模
  const bad = stateFromJson({ ...v0, initial: [1] });
  assert.ok(bad.error);
});

test("F7: toV1Json — fock param mapping (loss T→eta 掉 nbar, squeeze 掉 phi)", () => {
  const base = { view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {}, seed: 0 };
  const nodes = [
    { id: "n1", op: "loss", params: { T: 0.8, nbar: 0.1 }, mode: 0 },
    { id: "n2", op: "squeeze", params: { r: 0.4, phi: 1.2 }, mode: 1 },
    { id: "n3", op: "phase", params: { phi: 0.7 }, mode: 0 },
  ];
  const f = toV1Json({ ...base, backend: "fock", nodes, initial: null, cutoffs: [] });
  assert.deepEqual(f.ops[0].params, { eta: 0.8 }); // nbar dropped (fock loss is pure)
  assert.deepEqual(f.ops[1].params, { r: 0.4 });   // phi dropped (fock squeeze has only r)
  assert.deepEqual(f.ops[2].params, { theta: 0.7 }); // phase theta shared
  // gaussian 路径字节不变
  const g = toV1Json({ ...base, backend: "gaussian", nodes, initial: null, cutoffs: [] });
  assert.deepEqual(g.ops[0].params, { T: 0.8, nbar: 0.1 });
  assert.deepEqual(g.ops[1].params, { r: 0.4, phi: 1.2 });
});

test("F7: stateFromV1 — fock 载入（loss eta→T、squeeze 无 phi、name 保留）+ round-trip", () => {
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
  assert.equal(sq.params.phi, 0); // fock 路径 phi optional → default
  const pnr = state.nodes.find((n) => n.op === "measure_pnr");
  assert.equal(pnr.params.name, "m_n"); // 显式 name 保留
  // round-trip: save → load 一致（eta 往返）
  const rt = stateFromJson(toV1Json(state));
  assert.equal(rt.error, undefined);
  const rtLoss = rt.state.nodes.find((n) => n.op === "loss");
  assert.equal(rtLoss.params.T, 0.8);
  assert.deepEqual(toV1Json(rt.state).ops.find((o) => o.op === "loss").params, { eta: 0.8 });
});
