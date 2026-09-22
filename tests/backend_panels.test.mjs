/* Gaussian Lab — backend_panels.js leaf tests (node --test, zero deps).
   Review §3.3 #1: per-backend 差异知识的表驱动部分收单点后，终于可直测
   （此前 4 张表埋在 app.js/editor.js 里，0 export → 结构上测不到）。 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  BACKEND_PANELS, INITIAL_INPUT_KIND, METER_ROWS, RUN_BODY_EXTENSIONS,
  initialInputKind, meterRowPlan, panelsFor, runBodyExtensions,
} from "../cvsim/lab/static/backend_panels.js";

test("panelsFor: three backends, unknown → undefined", () => {
  for (const b of ["gaussian", "fock", "bosonic"]) {
    assert.ok(panelsFor(b), `${b} missing`);
  }
  assert.equal(panelsFor("nope"), undefined);
  assert.equal(panelsFor(undefined), undefined);
});

test("panelsFor: every backend declares the same panel id set", () => {
  const ids = Object.keys(BACKEND_PANELS.gaussian).sort();
  for (const b of ["fock", "bosonic"]) {
    assert.deepEqual(Object.keys(BACKEND_PANELS[b]).sort(), ids,
      `${b} declares a different panel id set — a missing key silently keeps ` +
      `the previous backend's hidden state`);
  }
});

test("panelsFor: gaussian/fock/bosonic visibility is mutually exclusive where it should be", () => {
  const g = panelsFor("gaussian"), f = panelsFor("fock"), b = panelsFor("bosonic");
  // each backend's own panel is visible only for itself
  assert.equal(g["scan-panel"], true);
  assert.equal(f["scan-panel"], false);
  assert.equal(b["scan-panel"], false);
  assert.equal(f["fock-panel"], true);
  assert.equal(g["fock-panel"], false);
  assert.equal(b["bosonic-panel"], true);
  assert.equal(g["bosonic-panel"], false);
  // meters: gaussian + bosonic only; wigner side likewise
  assert.equal(g["meters-panel"], true);
  assert.equal(b["meters-panel"], true);
  assert.equal(f["meters-panel"], false);
  assert.equal(f["wigner-side"], false);
});

test("meterRowPlan: matrix keys decide visibility, plan keeps every declared row", () => {
  const plan = meterRowPlan(new Set(["purity", "mean_photon"]));
  assert.equal(plan.length, Object.keys(METER_ROWS).length);
  const byKey = Object.fromEntries(plan.map((r) => [r.key, r]));
  assert.equal(byKey.purity.visible, true);
  assert.equal(byKey.mean_photon.visible, true);
  assert.equal(byKey.log_negativity.visible, false);
  // gaussian-only key must stay hidden for a fock key set
  assert.equal(byKey.log_negativity.rowId, "m-row-log_negativity");
});

test("meterRowPlan: empty matrix hides every row (never leaves a stale visible row)", () => {
  const plan = meterRowPlan(new Set());
  assert.ok(plan.every((r) => !r.visible));
});

test("meterRowPlan: row ids and value ids match the HTML contract", () => {
  const plan = meterRowPlan(new Set());
  const byKey = Object.fromEntries(plan.map((r) => [r.key, r]));
  assert.equal(byKey.purity.valueId, "m-purity");
  assert.equal(byKey.mean_photon.valueId, "m-nbar");
  assert.equal(byKey.mean_photon_per_mode.valueId, "m-permode");
  assert.equal(byKey.log_negativity.valueId, "m-logneg");
  // every rowId is m-row-<key> — the consumer builds $(row.rowId) from it
  for (const r of plan) assert.equal(r.rowId, `m-row-${r.key}`);
});

test("runBodyExtensions: bosonic asks for steps, others add nothing", () => {
  assert.deepEqual(runBodyExtensions("bosonic"), { detail: "steps" });
  assert.deepEqual(runBodyExtensions("gaussian"), {});
  assert.deepEqual(runBodyExtensions("fock"), {});
  assert.deepEqual(runBodyExtensions("nope"), {});
  // spreadable without a guard at the call site
  assert.deepEqual({ ...{ backend: "fock" }, ...runBodyExtensions("fock") },
    { backend: "fock" });
});

test("initialInputKind: fock int / bosonic enum / gaussian undefined", () => {
  assert.equal(initialInputKind("fock"), "int");
  assert.equal(initialInputKind("bosonic"), "enum");
  assert.equal(initialInputKind("gaussian"), undefined);
  assert.equal(initialInputKind("nope"), undefined);
  assert.deepEqual(Object.keys(INITIAL_INPUT_KIND).sort(), ["bosonic", "fock"]);
});

test("RUN_BODY_EXTENSIONS is the single declaration (no second table drifted in)", () => {
  assert.deepEqual(Object.keys(RUN_BODY_EXTENSIONS), ["bosonic"]);
});
