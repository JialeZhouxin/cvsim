/* 票A — svg_kit leaf 契约测试 (node --test, zero deps, ADR-0009)。
   只测纯函数 fmt/axisVal/outcomeText；el 用 document.createElementNS
   （浏览器 API），不单测，靠消费方 probe/人工走查。期望值手推独立事实源，
   文案逐字断言（outcomeText 行模板与 scan 校验文案同属回归红线）。 */
import test from "node:test";
import assert from "node:assert/strict";

import { fmt, axisVal, outcomeText, SVG_NS } from "../cvsim/lab/static/svg_kit.js";

/* ── fmt ─────────────────────────────────────────────────── */

test("fmt：有限数默认 5 位有效数字", () => {
  assert.equal(fmt(0.123456789), "0.12346"); // toPrecision(5)
  assert.equal(fmt(3.14159), "3.1416");
  assert.equal(fmt(42), "42.000");
  assert.equal(fmt(0), "0.0000");
});

test("fmt：显式 digits 参数生效", () => {
  assert.equal(fmt(1 / 3, 3), "0.333");
  assert.equal(fmt(1 / 3, 8), "0.33333333");
});

test("fmt：非有限数 → 诚实 —（NaN / ±Infinity）", () => {
  assert.equal(fmt(NaN), "—");
  assert.equal(fmt(Infinity), "—");
  assert.equal(fmt(-Infinity), "—");
});

test("fmt：非 number 类型 → —（undefined 键 / null / 字符串，fmt 缺失键语义）", () => {
  assert.equal(fmt(undefined), "—");
  assert.equal(fmt(null), "—");
  assert.equal(fmt("x"), "—");
});

/* ── axisVal ─────────────────────────────────────────────── */

test("axisVal：整数与尾零裁剪 — 5→5、4.50→4.5、-2.00→-2", () => {
  assert.equal(axisVal(5), "5");
  assert.equal(axisVal(4.5), "4.5");
  assert.equal(axisVal(0.5), "0.5");
  assert.equal(axisVal(-2.5), "-2.5");
});

test("axisVal：toPrecision(3) 舍入 + 裁剪 — 2.501→2.5、1.234→1.23、-0.501→-0.501", () => {
  assert.equal(axisVal(2.501), "2.5"); // "2.50" → 裁掉尾零
  assert.equal(axisVal(1.234), "1.23");
  assert.equal(axisVal(-0.501), "-0.501"); // 3 位有效全保留
  assert.equal(axisVal(0.1234), "0.123"); // "0.123" 无尾零可裁
});

test('axisVal：0 → 裁剪后保 "0"（点号需尾随数字，正则不整段吃）', () => {
  assert.equal(axisVal(0), "0");
});

test("axisVal：非有限数 → —", () => {
  assert.equal(axisVal(NaN), "—");
  assert.equal(axisVal(Infinity), "—");
});

/* ── outcomeText ─────────────────────────────────────────── */

test("outcomeText：数组 outcome → (a, b) 四位小数 + φ/name 后缀", () => {
  const line = outcomeText({
    op: "homodyne", outcome: [1.23456, -2.5], mode: 0, phi: 1.23456, name: "q",
  });
  assert.equal(line, "homodyne q · mode 0 φ=1.235 → (1.2346, -2.5000)");
});

test("outcomeText：整数 outcome → String 原样（PNR 计数不加小数）", () => {
  const line = outcomeText({ op: "pnr", outcome: 3, mode: 1 });
  assert.equal(line, "pnr · mode 1 → 3");
});

test("outcomeText：浮点 outcome → toFixed(4)", () => {
  const line = outcomeText({ op: "measure_x", outcome: 0.12345678, mode: 2 });
  assert.equal(line, "measure_x · mode 2 → 0.1235");
});

test("outcomeText：无 φ/name 字段 → 不拼接后缀（undefined 检查）", () => {
  const line = outcomeText({ op: "pnr", outcome: 0, mode: 0 });
  assert.equal(line, "pnr · mode 0 → 0");
  assert.ok(!line.includes("φ"));
});

test("outcomeText：op/行模板逐字 — `op name · mode i[ φ=x] → (out)`", () => {
  const line = outcomeText({ op: "homodyne", outcome: [0], mode: 3, phi: 0, name: "p" });
  assert.equal(line, "homodyne p · mode 3 φ=0.000 → (0.0000)");
});

/* ── SVG_NS（el 的边界依赖，值锁死） ─────────────────────── */

test("SVG_NS：W3C 命名空间常量原样", () => {
  assert.equal(SVG_NS, "http://www.w3.org/2000/svg");
});