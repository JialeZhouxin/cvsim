/* Gaussian Lab — svg micro-kit leaf（票A，ADR-0009 下半场）。
   SVG 命名空间 + 元素工厂 + 数字→展示字符串 词表（fmt/axisVal/outcomeText），
   app.js 与 fock.js 的重复实现收单点。el 用 document.createElementNS 是
   leaf 纪律中唯一允许的 DOM 边界（不单测，靠消费方 probe/人工）；其余
   纯函数零 import、零 DOM，node --test 直测（tests/svg_kit.test.mjs）。 */
"use strict";

export const SVG_NS = "http://www.w3.org/2000/svg";

/** DOM 边界函数：仅 document.createElementNS 一个调用点。 */
export function el(tag, attrs) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

/** 数字 → 展示字符串：非有限数诚实 "—"（fmt 缺失键 → "—" 语义）。 */
export function fmt(x, digits = 5) {
  if (typeof x !== "number" || !Number.isFinite(x)) return "—";
  return x.toPrecision(digits);
}

/** 数字 → 轴刻度字符串：toPrecision(3) + 尾零裁剪（5→"5"、4.5→"4.5"）。 */
export function axisVal(v) {
  if (!Number.isFinite(v)) return "—";
  let s = v.toPrecision(3);
  if (s.includes(".")) s = s.replace(/\.?0+$/, "");
  return s;
}

/** measurement 节点 → 完整 outcome 文案行（原 app.js showMeasurement
    内联三态格式化 + φ/name 拼接，语义原样迁移）：
    数组 → `(a, b)`；整数 → String；浮点 → toFixed(4)。 */
export function outcomeText(m) {
  const out = Array.isArray(m.outcome)
    ? `(${m.outcome.map((v) => Number(v).toFixed(4)).join(", ")})`
    : (Number.isInteger(m.outcome) ? String(m.outcome) : Number(m.outcome).toFixed(4));
  const phi = m.phi !== undefined ? ` φ=${Number(m.phi).toFixed(3)}` : "";
  const nm = m.name !== undefined ? ` ${m.name}` : "";
  return `${m.op}${nm} · mode ${m.mode}${phi} → ${out}`;
}