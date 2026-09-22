/* Gaussian Lab — scan_panel.js leaf tests (node --test, zero deps).
   Review §3.3 #3: the scan query half (sweepability, dirty key, param keys,
   adaptive range) used to be reachable only by reading app.js source text.
   The §4.6 test that did exactly that is now a behaviour test below. */
import test from "node:test";
import assert from "node:assert/strict";

import {
  isSweepable, modesAOptions, scanEnabled, scanNodeListKey, sweepDefaults,
  sweepParamKeys, sweepableNodes,
} from "../cvsim/lab/static/scan_panel.js";

/** Minimal OPS table: squeeze has a sweepable `r`, phase has none. */
const OPS = {
  squeeze: { label: "压缩", params: { r: { sweep: [0, 2] }, phi: {} } },
  phase: { label: "相位", params: { theta: { sweep: [0, 6.28] } } },
  loss: { label: "损耗", params: { T: {} } },
};

const st = (nodes, nmode = 2) => ({ nmode, nodes });

test("isSweepable: only params carrying a sweep array qualify", () => {
  assert.equal(isSweepable({ id: 0, op: "squeeze" }, OPS), true);
  assert.equal(isSweepable({ id: 0, op: "loss" }, OPS), false);
  assert.equal(isSweepable({ id: 0, op: "unknown" }, OPS), false);
});

test("sweepableNodes: keeps order, drops non-sweepable", () => {
  const nodes = [
    { id: 0, op: "phase" },
    { id: 1, op: "loss" },
    { id: 2, op: "squeeze" },
  ];
  assert.deepEqual(sweepableNodes(st(nodes), OPS).map((n) => n.id), [0, 2]);
});

test("scanNodeListKey: node identity (id/op), NOT the nodes array reference", () => {
  const nodes = [{ id: 0, op: "squeeze" }];
  const a = scanNodeListKey(st(nodes), OPS);
  // Same logical nodes, brand-new array object (what onParam's map() produces).
  const b = scanNodeListKey(st(nodes.map((n) => ({ ...n }))), OPS);
  assert.equal(a, b, "a rebuilt array with identical nodes must hash the same " +
    "(otherwise the dirty key never hits — the bug this replaced)");
  assert.equal(a, "2|0:squeeze");
});

test("scanNodeListKey: param VALUE changes do not rebuild (only id/op/nmode do)", () => {
  const before = st([{ id: 0, op: "squeeze", params: { r: 0.5 } }]);
  const after = st([{ id: 0, op: "squeeze", params: { r: 1.9 } }]);
  assert.equal(scanNodeListKey(before, OPS), scanNodeListKey(after, OPS));
  // ...but op / id / nmode changes do.
  assert.notEqual(scanNodeListKey(before, OPS),
    scanNodeListKey(st([{ id: 0, op: "phase" }]), OPS));
  assert.notEqual(scanNodeListKey(before, OPS), scanNodeListKey(st([{ id: 0, op: "squeeze" }], 3), OPS));
});

test("scanNodeListKey: no sweepable nodes is still a stable key", () => {
  const k = scanNodeListKey(st([{ id: 0, op: "loss" }]), OPS);
  assert.equal(k, "2|");
});

test("sweepParamKeys: filters to sweepable params, empty for missing node", () => {
  assert.deepEqual(sweepParamKeys({ id: 0, op: "squeeze" }, OPS), ["r"]);
  assert.deepEqual(sweepParamKeys({ id: 0, op: "loss" }, OPS), []);
  assert.deepEqual(sweepParamKeys(undefined, OPS), []);
  assert.deepEqual(sweepParamKeys({ id: 0, op: "unknown" }, OPS), []);
});

test("sweepDefaults: adaptive range from metadata, null when not sweepable", () => {
  assert.deepEqual(sweepDefaults({ id: 0, op: "squeeze" }, "r", OPS),
    { min: 0, max: 2, n: 50 });
  assert.equal(sweepDefaults({ id: 0, op: "squeeze" }, "phi", OPS), null);
  assert.equal(sweepDefaults({ id: 0, op: "loss" }, "T", OPS), null);
  assert.equal(sweepDefaults(undefined, "r", OPS), null);
});

test("modesAOptions: 1..nmode-1 labels, empty below 2 modes", () => {
  assert.deepEqual(modesAOptions(3), [
    { value: "1", label: "[0..0]" },
    { value: "2", label: "[0..1]" },
  ]);
  assert.deepEqual(modesAOptions(2), [{ value: "1", label: "[0..0]" }]);
  assert.deepEqual(modesAOptions(1), []);
  assert.deepEqual(modesAOptions(0), []);
});

test("scanEnabled: needs nmode>=2 AND a non-empty node list", () => {
  assert.equal(scanEnabled(2, 1), true);
  assert.equal(scanEnabled(3, 5), true);
  assert.equal(scanEnabled(1, 5), false, "E_N needs >=2 modes");
  assert.equal(scanEnabled(2, 0), false, "nothing to sweep");
  assert.equal(scanEnabled(0, 0), false);
});
