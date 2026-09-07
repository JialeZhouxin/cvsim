/* 票B — scan_form leaf 契约测试 (node --test, zero deps, ADR-0009)。
   三分支报错文案逐字断言 + 边界（n=2/200 过、1/201 拒、min==max 拒）。
   文案回归红线：doScan 现文案迁移，probe（lab_scan_probe.mjs）依赖
   status 文案路径不变。 */
import test from "node:test";
import assert from "node:assert/strict";

import { validateScanForm } from "../cvsim/lab/static/scan_form.js";

const pass = { hasSweepParam: true, min: 0, max: 4, n: 50 };

/* ── 全通过 → null ───────────────────────────────────────── */

test("validateScanForm：全字段合法 → null（调用方继续组装 payload）", () => {
  assert.equal(validateScanForm(pass), null);
});

test("validateScanForm：n 边界 2 与 200 过（含端点）", () => {
  assert.equal(validateScanForm({ ...pass, n: 2 }), null);
  assert.equal(validateScanForm({ ...pass, n: 200 }), null);
});

/* ── 分支一：参数存在性 ─────────────────────────────────── */

test("validateScanForm：无可扫参数 → 文案逐字「扫参：请先选择有可扫参数的节点」", () => {
  assert.equal(
    validateScanForm({ ...pass, hasSweepParam: false }),
    "扫参：请先选择有可扫参数的节点",
  );
});

/* ── 分支二：min/max ────────────────────────────────────── */

test("validateScanForm：min 非有限 → 文案逐字「扫参：min 必须是有限数且 < max」", () => {
  assert.equal(
    validateScanForm({ ...pass, min: NaN }),
    "扫参：min 必须是有限数且 < max",
  );
});

test("validateScanForm：max 非有限 → 同文案（min/max 共用一段 if-return）", () => {
  assert.equal(
    validateScanForm({ ...pass, max: Infinity }),
    "扫参：min 必须是有限数且 < max",
  );
});

test("validateScanForm：min==max 拒（pmin >= pmax 边界）", () => {
  assert.equal(
    validateScanForm({ ...pass, min: 1, max: 1 }),
    "扫参：min 必须是有限数且 < max",
  );
});

test("validateScanForm：min>max 拒", () => {
  assert.equal(
    validateScanForm({ ...pass, min: 4, max: 0 }),
    "扫参：min 必须是有限数且 < max",
  );
});

/* ── 分支三：n ──────────────────────────────────────────── */

test("validateScanForm：n 非整数 → 文案逐字「扫参：n 必须是 2–200 的整数」", () => {
  assert.equal(
    validateScanForm({ ...pass, n: 2.5 }),
    "扫参：n 必须是 2–200 的整数",
  );
  assert.equal(
    validateScanForm({ ...pass, n: NaN }),
    "扫参：n 必须是 2–200 的整数",
  );
});

test("validateScanForm：n 越界 1 / 201 拒（端点外一格）", () => {
  assert.equal(
    validateScanForm({ ...pass, n: 1 }),
    "扫参：n 必须是 2–200 的整数",
  );
  assert.equal(
    validateScanForm({ ...pass, n: 201 }),
    "扫参：n 必须是 2–200 的整数",
  );
});

/* ── 校验顺序：存在性优先（先缺参再 min/max，与 doScan 现顺序一致） ── */

test("validateScanForm：顺序 — hasSweepParam=false 时 min/n 再烂也报第一分支", () => {
  assert.equal(
    validateScanForm({ hasSweepParam: false, min: NaN, max: NaN, n: 0 }),
    "扫参：请先选择有可扫参数的节点",
  );
});

test("validateScanForm：顺序 — min/max 先于 n（双非法时报 min 分支）", () => {
  assert.equal(
    validateScanForm({ hasSweepParam: true, min: NaN, max: 4, n: 2.5 }),
    "扫参：min 必须是有限数且 < max",
  );
});