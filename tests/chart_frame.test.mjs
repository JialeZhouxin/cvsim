/* Gaussian Lab — chart_frame.js leaf tests (node --test, zero deps).
   Review §3.3 #4: grid geometry / theme lookup / axis label specs were rebuilt
   inline in drawFidSvg, drawScanCurve and drawBars — each untestable. */
import test from "node:test";
import assert from "node:assert/strict";

import {
  AXIS_THEME, FOCK_HEAT_THEME, FOCK_THEME, FRAME_THEME,
  axisLabelSpecs, gridLines, gridSegments, themeVars, yFractionScale,
} from "../cvsim/lab/static/chart_frame.js";

const PAD = { l: 34, r: 10, t: 10, b: 18 };

test("gridLines: n+1 lines spanning the padded plot area", () => {
  const { xs, ys } = gridLines(320, 150, PAD, 4);
  assert.equal(xs.length, 5);
  assert.equal(ys.length, 5);
  assert.equal(xs[0], PAD.l);
  assert.equal(xs[4], 320 - PAD.r);
  assert.equal(ys[0], PAD.t);
  assert.equal(ys[4], 150 - PAD.b);
  // evenly spaced
  const dx = xs[1] - xs[0];
  for (let i = 1; i < xs.length; i++) assert.ok(Math.abs((xs[i] - xs[i - 1]) - dx) < 1e-9);
});

test("gridLines: degenerate pad/n still yields finite coordinates", () => {
  const { xs } = gridLines(10, 10, { l: 0, r: 0, t: 0, b: 0 }, 1);
  assert.deepEqual(xs, [0, 10]);
});

test("yFractionScale: v/vmax over the padded span", () => {
  const h = yFractionScale(2, 150, 10, 18);
  assert.equal(h(2), 122);      // full vmax → whole span
  assert.equal(h(1), 61);
  assert.equal(h(0), 0);
});

test("yFractionScale: vmax=0 → all zero, never NaN/Infinity", () => {
  const h = yFractionScale(0, 150, 10, 18);
  for (const v of [0, 1, -1]) assert.equal(h(v), 0);
});

test("themeVars: reads CSS vars, falls back when empty", () => {
  const fakeStyle = {
    getPropertyValue: (k) => ({ "--color-rule": "  #abc  ", "--color-ink": "" }[k] ?? ""),
  };
  const v = themeVars(fakeStyle, FOCK_THEME);
  assert.equal(v.rule, "#abc", "value must be trimmed");
  assert.equal(v.ink, "#333", "empty → declared fallback, not ''");
  assert.equal(v.accent, "#2e63d1", "missing entirely → fallback");
  assert.equal(v.error, "#c33");
});

test("themeVars: FRAME_THEME has NO fallbacks — verbatim to the old scan code", () => {
  // The old drawScanCurve did `.trim()` with no `|| fallback`. Adding one would
  // be a silent behaviour change (a missing token would render a different
  // colour instead of an invalid one), so it must stay empty.
  const empty = { getPropertyValue: () => "" };
  assert.deepEqual(themeVars(empty, FRAME_THEME), { rule: "", ink: "", accent: "" });
  // AXIS_THEME: axis has a fallback, paper deliberately does not.
  assert.deepEqual(themeVars(empty, AXIS_THEME), { axis: "#7fe0ff", paper: "" });
});

test("themeVars: returned keys match the spec, no extras", () => {
  const fakeStyle = { getPropertyValue: () => "#000" };
  for (const spec of [FRAME_THEME, FOCK_THEME, FOCK_HEAT_THEME, AXIS_THEME]) {
    assert.deepEqual(Object.keys(themeVars(fakeStyle, spec)).sort(),
      Object.keys(spec).sort());
  }
});

test("theme specs: every entry is [cssVar, fallback] and cssVar is a --token", () => {
  for (const spec of [FRAME_THEME, FOCK_THEME, FOCK_HEAT_THEME, AXIS_THEME]) {
    for (const [key, pair] of Object.entries(spec)) {
      assert.ok(Array.isArray(pair) && pair.length === 2, `${key} not a pair`);
      assert.match(pair[0], /^--color-/, `${key} css var name`);
      assert.equal(typeof pair[1], "string", `${key} fallback is a string`);
    }
  }
});

test("theme specs: fock fallbacks preserved verbatim (no drift)", () => {
  assert.equal(FOCK_THEME.accent[1], "#2e63d1");
  assert.equal(FOCK_THEME.error[1], "#c33");
  assert.equal(FOCK_THEME.rule[1], "#ccc");
  assert.equal(FOCK_THEME.ink[1], "#333");
  assert.deepEqual(FOCK_HEAT_THEME, {
    accent: ["--color-accent", "#2e63d1"],
    error: ["--color-error", "#c33"],
  });
});

test("gridSegments: interleaved vertical/horizontal, original draw order", () => {
  const segs = gridSegments(320, 150, PAD, 4);
  assert.equal(segs.length, 10, "5 verticals + 5 horizontals");
  segs.forEach((s, i) => {
    if (i % 2 === 0) { // vertical
      assert.equal(s.x1, s.x2, `seg ${i} should be vertical`);
      assert.equal(s.y1, PAD.t);
      assert.equal(s.y2, 150 - PAD.b);
    } else { // horizontal
      assert.equal(s.y1, s.y2, `seg ${i} should be horizontal`);
      assert.equal(s.x1, PAD.l);
      assert.equal(s.x2, 320 - PAD.r);
    }
  });
  const { xs, ys } = gridLines(320, 150, PAD, 4);
  assert.deepEqual(segs.filter((_, i) => i % 2 === 0).map((s) => s.x1), xs);
  assert.deepEqual(segs.filter((_, i) => i % 2 === 1).map((s) => s.y1), ys);
});

test("axisLabelSpecs: four labels at the plot corners", () => {
  const fmt = (v) => String(v);
  const specs = axisLabelSpecs({ x0: 0, x1: 1, ylo: 0, yhi: 2, W: 320, H: 150, pad: PAD }, fmt);
  assert.equal(specs.length, 4);
  assert.deepEqual(specs.map((s) => s.text), ["0", "1", "2", "0"]);
  assert.equal(specs[0].anchor, "start");
  assert.equal(specs[1].anchor, "end");
  // both y labels sit left of the plot area, end-anchored
  assert.equal(specs[2].x, PAD.l - 6);
  assert.equal(specs[3].x, PAD.l - 6);
  assert.equal(specs[2].anchor, "end");
  assert.equal(specs[3].anchor, "end");
  // x labels sit at the bottom
  assert.equal(specs[0].y, 150 - 4);
  assert.equal(specs[1].y, 150 - 4);
});

test("axisLabelSpecs: fmt is injected (leaf stays import-free)", () => {
  const specs = axisLabelSpecs({ x0: 1, x1: 2, ylo: 3, yhi: 4, W: 100, H: 50, pad: PAD },
    (v) => `#${v}`);
  assert.deepEqual(specs.map((s) => s.text), ["#1", "#2", "#4", "#3"]);
});
