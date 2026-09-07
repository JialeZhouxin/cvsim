/* Gaussian Lab — scan 表单校验纯核 leaf（票B，ADR-0009 下半场）。
   doScan 的三段前置 if-return 收单点：参数存在性 → min/max → n。
   报错文案与现 app.js 行为逐字一致（lab_scan_probe 等待 status 文案，
   路径不变）。零 import、零 DOM：node --test 直测（tests/scan_form.test.mjs）。
   「有可扫参数」的取值（node && d && Array.isArray(d.sweep)）由调用方
   布尔化传入 hasSweepParam——leaf 不摸 OPS/editor/DOM。 */
"use strict";

/** @param {{hasSweepParam: boolean, min: number, max: number, n: number}} input
    @returns {string|null} 报错文案（setStatus(msg, false)）或 null（全过）。 */
export function validateScanForm(input) {
  if (!input.hasSweepParam) return "扫参：请先选择有可扫参数的节点";
  if (!Number.isFinite(input.min) || !Number.isFinite(input.max) || input.min >= input.max) {
    return "扫参：min 必须是有限数且 < max";
  }
  if (!Number.isInteger(input.n) || input.n < 2 || input.n > 200) {
    return "扫参：n 必须是 2–200 的整数";
  }
  return null;
}