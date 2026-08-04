/* Gaussian Lab L2 — pure editor logic tests (node --test, zero deps). */
import test from "node:test";
import assert from "node:assert/strict";

import {
  OPS, OP_NAMES, TAU, paramsFromOp, sourceModes,
  addNode, removeNode, moveNode, updateParam, updateMode, toCircuitJson,
} from "../cvsim/lab/static/ops.js";
import { stateFromJson, loadJson } from "../cvsim/lab/static/editor.js";

const EXPECTED_OPS = ["tmsv", "coherent", "squeeze", "phase", "displace", "loss", "beamsplitter", "heterodyne", "homodyne"];

test("ops metadata: 9 whitelist-subset ops", () => {
  assert.deepEqual([...OP_NAMES].sort(), [...EXPECTED_OPS].sort());
});

test("ops metadata: param ranges sane", () => {
  assert.equal(OPS.loss.params.T.min, 0.01);
  assert.equal(OPS.loss.params.T.max, 1);
  assert.equal(OPS.beamsplitter.params.theta.max, TAU);
  assert.ok(OPS.tmsv.params.r.step <= 0.01);
});

test("addNode appends with defaults + mode", () => {
  let nodes = [];
  nodes = addNode(nodes, "tmsv");
  assert.equal(nodes.length, 1);
  assert.equal(nodes[0].op, "tmsv");
  assert.equal(nodes[0].params.r, 0.6);
  assert.equal(nodes[0].mode, undefined); // source: no mode field
  nodes = addNode(nodes, "loss");
  assert.equal(nodes[1].mode, 0);
  nodes = addNode(nodes, "beamsplitter");
  assert.deepEqual(nodes[2].modes, [0, 1]);
});

test("sourceModes: tmsv=2, coherent=1", () => {
  let nodes = [];
  nodes = addNode(nodes, "tmsv");
  nodes = addNode(nodes, "coherent");
  assert.equal(sourceModes(nodes), 3);
});

test("removeNode / moveNode incl. bounds", () => {
  let nodes = [];
  for (const op of ["tmsv", "loss", "loss"]) nodes = addNode(nodes, op);
  const [a, b, c] = nodes;
  assert.deepEqual(removeNode(nodes, b.id).map((n) => n.id), [a.id, c.id]);
  assert.deepEqual(moveNode(nodes, a.id, -1).map((n) => n.id), [a.id, b.id, c.id]); // no-op
  assert.deepEqual(moveNode(nodes, a.id, 1).map((n) => n.id), [b.id, a.id, c.id]);
  assert.deepEqual(moveNode(nodes, c.id, 1).map((n) => n.id), [a.id, b.id, c.id]); // no-op
});

test("updateParam / updateMode", () => {
  let nodes = addNode([], "loss");
  nodes = nodes.map((n) => updateParam(n, "T", 0.5));
  assert.equal(nodes[0].params.T, 0.5);
  nodes = nodes.map((n) => updateMode(n, 1));
  assert.equal(nodes[0].mode, 1);
  assert.equal(updateMode(nodes[0], -2).mode, 1); // invalid rejected
});

test("OCR guards: clamp, dir type, unknown keys", () => {
  let nodes = addNode([], "loss");
  // out-of-range clamped to metadata bounds
  assert.equal(updateParam(nodes[0], "T", 99).params.T, 1);
  assert.equal(updateParam(nodes[0], "T", -5).params.T, 0.01);
  // NaN / unknown key rejected (no change)
  assert.equal(updateParam(nodes[0], "T", NaN).params.T, 0.8);
  assert.equal(updateParam(nodes[0], "nope", 1).params.T, 0.8);
  // non-integer move step rejected
  nodes = [addNode([], "tmsv")[0], addNode([], "loss")[0]];
  assert.equal(moveNode(nodes, nodes[0].id, "1").length, 2);
  assert.deepEqual(moveNode(nodes, nodes[0].id, "1").map((n) => n.op), ["loss", "tmsv"]);
  assert.equal(moveNode(nodes, nodes[0].id, 0.5).length, 2);
  // unknown op rejected
  assert.throws(() => paramsFromOp("mach_zehnder"), TypeError);
});

test("OCR guards: id collision after import, proto keys, dup ids", () => {
  const payload = toCircuitJson({
    nodes: [{ id: "n0", op: "tmsv", params: { r: 0.6 } }],
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
    { id: "a", op: "tmsv", params: { r: 0.5 } },
    { id: "a", op: "loss", params: { T: 0.9 }, mode: 0 },
  ] };
  assert.ok(stateFromJson(dup).error);
  // malformed param freezes instead of silently defaulting
  const bad = { schema: "circuit_v0", nodes: [{ id: "a", op: "squeeze", params: { r: "x" } }] };
  assert.ok(stateFromJson(bad).error);
});

test("toCircuitJson: L0-compatible payload", () => {
  let nodes = [];
  nodes = addNode(nodes, "tmsv");
  nodes = addNode(nodes, "loss");
  nodes = nodes.map((n) => (n.id === nodes[1].id ? { ...n, mode: 1 } : n));
  const payload = toCircuitJson({ nodes, view: { wigner_mode: 0, lim: 5.0, n: 64 }, ui: {} });
  assert.equal(payload.schema, "circuit_v0");
  assert.deepEqual(payload.edges, []);
  assert.equal(payload.nodes[0].op, "tmsv");
  assert.equal(payload.nodes[1].mode, 1);
  assert.ok(!("mode" in payload.nodes[0])); // sources carry no mode
});

test("stateFromJson: valid payload round-trips", () => {
  const payload = toCircuitJson({
    nodes: addNode(addNode([], "tmsv"), "loss"),
    view: { wigner_mode: 0, lim: 5.0, n: 64 },
    ui: {},
  });
  const { state, error } = stateFromJson(payload);
  assert.equal(error, undefined);
  assert.equal(state.nodes.length, 2);
  assert.equal(state.nodes[1].op, "loss");
  assert.equal(state.nodes[0].params.r, 0.6);
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
    nodes: addNode([], "tmsv"),
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
      { id: "a", op: "tmsv", params: { r: 0.6 } },
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
  const base = { schema: "circuit_v0", seed: 0, nodes: [{ id: "a", op: "tmsv", params: { r: 0.5 } }], view: { wigner_mode: 0, lim: 5, n: 64 } };
  assert.equal(stateFromJson(base).error, undefined); // seed 0 is valid (positive baseline)
  assert.ok(stateFromJson({ ...base, seed: -1 }).error);
  assert.ok(stateFromJson({ ...base, seed: 1.5 }).error);
  assert.ok(stateFromJson({ ...base, seed: "x" }).error);
});

test("L3: loadJson validates without mutating old state", () => {
  const good = { schema: "circuit_v0", seed: 3, nodes: [{ id: "a", op: "tmsv", params: { r: 0.5 } }], view: { wigner_mode: 0, lim: 5, n: 64 } };
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

test("stateFromJson: missing params freeze (frozen-graph policy)", () => {
  const { error } = stateFromJson({ schema: "circuit_v0", nodes: [{ id: "x", op: "squeeze", params: {} }] });
  assert.ok(error);
  assert.ok(error.includes("r"));
});
