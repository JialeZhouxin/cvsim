/* Gaussian Lab L2–L5 — pure editor logic tests (node --test, zero deps). */
import test from "node:test";
import assert from "node:assert/strict";

import {
  OPS, OP_NAMES, TAU, paramsFromOp, sourceModes,
  addNode, removeNode, placeSingle, completePlacing, moveNodeX,
  sortNodes, sourceRows, removeSource, updateParam, updateMode, toCircuitJson,
} from "../cvsim/lab/static/ops.js";
import { stateFromJson, loadJson } from "../cvsim/lab/static/editor.js";

const EXPECTED_OPS = ["vacuum", "tmsv", "coherent", "squeeze", "phase", "displace", "loss", "beamsplitter", "heterodyne", "homodyne", "amplifier", "mz", "two_mode_squeeze"];

test("ops metadata: 13 ops (tmsv kept for JSON compat, palette:false)", () => {
  assert.deepEqual([...OP_NAMES].sort(), [...EXPECTED_OPS].sort());
  assert.equal(OPS.tmsv.palette, false); // legacy source: loadable, not in palette
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

test("L5: placeSingle — lane + x locked, sorted", () => {
  let nodes = addNode([], "vacuum");
  nodes = placeSingle(nodes, "phase", 1, 2.5);
  assert.equal(nodes[1].op, "phase");
  assert.equal(nodes[1].mode, 1);
  assert.equal(nodes[1].ui.x, 2.5);
  // invalid: non-single op / bad mode / bad x rejected
  assert.equal(placeSingle(nodes, "beamsplitter", 0, 1).length, 2);
  assert.equal(placeSingle(nodes, "phase", -1, 1).length, 2);
  assert.equal(placeSingle(nodes, "phase", 0, NaN).length, 2);
});

test("L5: completePlacing — two-mode two-step flow", () => {
  let nodes = addNode([], "vacuum");
  nodes = addNode(nodes, "vacuum"); // 2 modes
  const placing = { op: "beamsplitter", modeA: 0, x: 1.5 };
  const ok = completePlacing(nodes, placing, 1);
  assert.equal(ok.ok, true);
  assert.equal(ok.nodes[2].op, "beamsplitter");
  assert.deepEqual(ok.nodes[2].modes, [0, 1]);
  assert.equal(ok.nodes[2].ui.x, 1.5);
  // same-lane reject, state preserved
  const same = completePlacing(nodes, placing, 0);
  assert.equal(same.ok, false);
  assert.match(same.reason, /不同模式/);
  // invalid placing / non-two op rejected
  assert.equal(completePlacing(nodes, { op: "phase", modeA: 0, x: 1 }, 1).ok, false);
  assert.equal(completePlacing(nodes, null, 1).ok, false);
  assert.equal(completePlacing(nodes, placing, -1).ok, false);
});

test("L5: moveNodeX — reorders by new x, guards NaN", () => {
  let nodes = addNode([], "vacuum");
  nodes = placeSingle(nodes, "phase", 0, 1);
  nodes = placeSingle(nodes, "squeeze", 0, 2);
  const [ph, sq] = nodes.slice(1);
  const moved = moveNodeX(nodes, sq.id, 0.5); // squeeze now before phase
  assert.deepEqual(moved.slice(1).map((n) => n.op), ["squeeze", "phase"]);
  assert.equal(moved[1].ui.x, 0.5);
  assert.equal(moveNodeX(nodes, sq.id, "x").length, nodes.length); // NaN rejected
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

test("L5: toCircuitJson carries ui.x; legacy node without ui stays clean", () => {
  let nodes = addNode([], "vacuum");
  nodes = placeSingle(nodes, "phase", 0, 3.5);
  const payload = toCircuitJson({ nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.nodes[1].ui.x, 3.5);
  assert.ok(!("ui" in payload.nodes[0])); // source: no ui.x → no ui emitted
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
  // explicit ui.x honored
  const withX = { ...legacy, nodes: [{ ...legacy.nodes[1], ui: { x: 7.5 } }] };
  const { state: sx } = stateFromJson(withX);
  assert.equal(sx.nodes[0].ui.x, 7.5);
  // round-trip: ui.x survives
  const rt = stateFromJson(toCircuitJson(state));
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
  assert.throws(() => paramsFromOp("mach_zehnder"), TypeError);
});

test("OCR guards: id collision after import, proto keys, dup ids", () => {
  const payload = toCircuitJson({
    nodes: [{ id: "n0", op: "vacuum", params: {} }],
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  const { state } = stateFromJson(payload);
  const grown = addNode(state.nodes, "loss");
  assert.equal(grown[1].id, "n1"); // no duplicate n0
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

test("toCircuitJson: L0-compatible payload", () => {
  let nodes = [];
  nodes = addNode(nodes, "vacuum");
  nodes = addNode(nodes, "loss");
  nodes = nodes.map((n) => (n.id === nodes[1].id ? { ...n, mode: 1 } : n));
  const payload = toCircuitJson({ nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.schema, "circuit_v0");
  assert.deepEqual(payload.edges, []);
  assert.equal(payload.nodes[0].op, "vacuum");
  assert.equal(payload.nodes[1].mode, 1);
  assert.ok(!("mode" in payload.nodes[0])); // sources carry no mode
});

test("stateFromJson: valid payload round-trips", () => {
  const payload = toCircuitJson({
    nodes: addNode(addNode([], "vacuum"), "loss"),
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes.length, 2);
  assert.equal(state.nodes[1].op, "loss");
  assert.equal(state.nodes[0].params.nmode, 1);
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
  assert.deepEqual(paramsFromOp("homodyne"), { phi: 0 });
  const node = addNode([], "homodyne");
  assert.equal(node[0].mode, 0);
  assert.equal(node[0].params.phi, 0);
});

test("L3: toCircuitJson preserves top-level seed", () => {
  const payload = toCircuitJson({
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
  const rt = stateFromJson(toCircuitJson(state));
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
  const rt = stateFromJson(toCircuitJson(state));
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
