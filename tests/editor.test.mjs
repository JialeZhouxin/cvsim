/* Gaussian Lab L2 — pure editor logic tests (node --test, zero deps). */
import test from "node:test";
import assert from "node:assert/strict";

import {
  OPS, OP_NAMES, TAU, paramsFromOp, sourceModes,
  addNode, removeNode, moveNode, updateParam, updateMode, toCircuitJson,
} from "../cvsim/lab/static/ops.js";
import { stateFromJson } from "../cvsim/lab/static/editor.js";

const EXPECTED_OPS = ["tmsv", "coherent", "squeeze", "phase", "displace", "loss", "beamsplitter", "heterodyne"];

test("ops metadata: 8 whitelist-subset ops", () => {
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

test("stateFromJson: missing params filled with defaults", () => {
  const { state } = stateFromJson({ schema: "circuit_v0", nodes: [{ id: "x", op: "squeeze", params: {} }] });
  assert.equal(state.nodes[0].params.r, 0.4);
  assert.equal(state.nodes[0].params.phi, 0);
});
