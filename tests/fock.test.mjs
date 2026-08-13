/* Gaussian Lab F7 — fock.js pure logic tests (node --test, zero deps).
   histBars / overlayHeat / leakInfo / clampInitial / batchMeasRows /
   marginalOf / sampleSeries — no DOM. */
import test from "node:test";
import assert from "node:assert/strict";

import {
  histBars, reshapeCounts, overlayHeat, leakInfo, slowCutoff,
  clampInitial, batchMeasRows, sampleSeries, marginalOf,
} from "../cvsim/lab/static/fock.js";

test("histBars: theory-only view (counts=null → sample 0)", () => {
  const bars = histBars([0.5, 0, 0.5], null, 0);
  assert.equal(bars.length, 3);
  assert.deepEqual(bars, [
    { n: 0, theory: 0.5, sample: 0 },
    { n: 1, theory: 0, sample: 0 },
    { n: 2, theory: 0.5, sample: 0 },
  ]);
});

test("histBars: sample overlay — counts/shots, pad missing, cap 30", () => {
  const bars = histBars([0.25, 0.5, 0.25], [500, 0, 500], 1000);
  assert.equal(bars[0].sample, 0.5);
  assert.equal(bars[1].sample, 0);
  assert.equal(bars[2].sample, 0.5);
  // counts longer than probs → padded theory 0, sample aligned
  const long = histBars([1.0], [400, 600], 1000);
  assert.deepEqual(long, [
    { n: 0, theory: 1, sample: 0.4 },
    { n: 1, theory: 0, sample: 0.6 },
  ]);
  // cap at 30
  const big = histBars(Array(50).fill(0), Array(50).fill(10), 1000);
  assert.equal(big.length, 30);
});

test("reshapeCounts: row-major 2D, mismatch → null", () => {
  assert.deepEqual(reshapeCounts([1, 2, 3, 4, 5, 6], [2, 3]), [[1, 2, 3], [4, 5, 6]]);
  assert.equal(reshapeCounts([1, 2, 3], [2, 3]), null);
  assert.equal(reshapeCounts(null, [2, 2]), null);
  assert.equal(reshapeCounts([1, 2, 3, 4], [2]), null);
});

test("marginalOf: row/column sums of flat joint counts", () => {
  // grid [[1,2],[3,4]] row-major
  assert.deepEqual(marginalOf([1, 2, 3, 4], [2, 2], true), [3, 7]);
  assert.deepEqual(marginalOf([1, 2, 3, 4], [2, 2], false), [4, 6]);
  assert.equal(marginalOf([1, 2], [2, 2], true), null);
});

test("overlayHeat: theory + sample cells", () => {
  const grid = [[0.5, 0], [0, 0.5]];
  const cells = overlayHeat(grid, [500, 0, 0, 500], 1000);
  assert.equal(cells.rows, 2);
  assert.equal(cells.cols, 2);
  assert.deepEqual(cells.cells, [
    { i: 0, j: 0, theory: 0.5, sample: 0.5 },
    { i: 0, j: 1, theory: 0, sample: 0 },
    { i: 1, j: 0, theory: 0, sample: 0 },
    { i: 1, j: 1, theory: 0.5, sample: 0.5 },
  ]);
  // no batch counts → sample 0
  const noBatch = overlayHeat(grid, [], 0);
  assert.deepEqual(noBatch.cells.map((c) => c.sample), [0, 0, 0, 0]);
  assert.equal(overlayHeat([], [1], 10), null);
});

test("leakInfo: null honest —, 1% gate → warn", () => {
  assert.deepEqual(leakInfo(null), { pct: null, warn: false });
  assert.deepEqual(leakInfo("x"), { pct: null, warn: false });
  const ok = leakInfo(0.005);
  assert.equal(ok.warn, false);
  assert.ok(Math.abs(ok.pct - 0.5) < 1e-12);
  const warn = leakInfo(0.02);
  assert.equal(warn.warn, true);
  assert.ok(Math.abs(warn.pct - 2) < 1e-12);
  assert.equal(leakInfo(0.01).warn, false); // 恰好 1% 不黄（>1% 才黄）
});

test("slowCutoff: cutoff>20 → Wigner 慢速提示", () => {
  assert.equal(slowCutoff([10, 25]), true);
  assert.equal(slowCutoff([10, 10]), false);
  assert.equal(slowCutoff([20]), false);
  assert.equal(slowCutoff([]), false);
  assert.equal(slowCutoff(null), false);
});

test("clampInitial: per-mode Fock number into [0, cutoffs[i]-1]", () => {
  assert.deepEqual(clampInitial([1, 1], [10, 10], 2), [1, 1]);
  assert.deepEqual(clampInitial([99, -2], [10, 10], 2), [9, 0]);
  assert.deepEqual(clampInitial(null, [5, 5], 2), [0, 0]);
  assert.deepEqual(clampInitial([1], [10, 10], 2), [1, 0]); // pad
  assert.deepEqual(clampInitial([1, 1, 1], [10, 10], 2), [1, 1]); // truncate
});

test("batchMeasRows: measured histogram sorted desc", () => {
  assert.deepEqual(batchMeasRows({ "(1, 0)": 600, "(0, 1)": 400 }), [
    { key: "(1, 0)", count: 600 },
    { key: "(0, 1)", count: 400 },
  ]);
  assert.deepEqual(batchMeasRows({}), []);
  assert.deepEqual(batchMeasRows(null), []);
});

test("sampleSeries: 1D / 2D-joint marginal → dist overlay series", () => {
  const distMode = 1;
  // 1D batch on this mode
  assert.deepEqual(sampleSeries(1, { counts: [400, 600], shape: [2], modes: [1], shots: 1000 }),
    { counts: [400, 600], shots: 1000 });
  // 1D batch on another mode → null
  assert.equal(sampleSeries(1, { counts: [400, 600], shape: [2], modes: [0], shots: 1000 }), null);
  // 2D joint incl. this mode as col (modes [0,1], distMode 1 → col sums)
  const b2 = { counts: [1, 2, 3, 4], shape: [2, 2], modes: [0, 1], shots: 10 };
  assert.deepEqual(sampleSeries(1, b2), { counts: [4, 6], shots: 10 });
  // distMode = modes[0] → row sums
  assert.deepEqual(sampleSeries(0, b2), { counts: [3, 7], shots: 10 });
  // measured batch → no overlay
  assert.equal(sampleSeries(0, { measured_names: ["a"], counts: { "(0)": 5 }, shots: 10 }), null);
  assert.equal(sampleSeries(0, null), null);
});
