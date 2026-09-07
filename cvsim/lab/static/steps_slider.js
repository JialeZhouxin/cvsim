/* Gaussian Lab — bosonic steps 滑条模型 leaf（票C，ADR-0009 下半场）。
   renderBosonicSteps 的纯模型逻辑收单点：滑条初始化/边界保底 + 全部展示
   文案。fmt 以参数注入（stepMeters 第二参）保持零 import；DOM 读写
   （slider/tag/info/meters 元素、oninput、drawWignerResult 回调）留在 app.js。
   零 DOM：node --test 直测（tests/steps_slider.test.mjs）。 */
"use strict";

/** 滑条初始化（原 renderBosonicSteps L306-333 语义）：
    空/非数组 steps → disabled；prevValue 非有限或 ≥ steps.length →
    保底选最后一步（滑条停在末尾选最终态）。 */
export function initStepState(steps, prevValue) {
  if (!Array.isArray(steps) || steps.length === 0) {
    return { max: 0, value: 0, disabled: true };
  }
  const max = steps.length - 1;
  const num = Number(prevValue); // slider.value 是字符串；空串 Number → 0 ≠ 语义有效值
  let value = max;
  if (prevValue !== "" && prevValue !== null && prevValue !== undefined
      && Number.isFinite(num) && num < steps.length) {
    value = Math.floor(num);
  }
  return { max, value, disabled: false };
}

/** step k/N 文案（N = 末步下标，与滑条 max 同一语义）。 */
export function stepLabel(k, steps) {
  return `step ${k}/${steps.length - 1}`;
}

/** op 描述：measure_ 前缀 → measure·、其余 _ → 空格。 */
export function stepDesc(op) {
  return op.replace("measure_", "measure·").replace(/_/g, " ");
}

/** 分步 meters 文案：`⟨n⟩ X · purity Y`（fmt 缺失键 → "—" 语义由
    注入的 fmtFn 兜底，模板双空格分隔与现状一致）。 */
export function stepMeters(meters, fmtFn) {
  const mp = meters && meters.mean_photon;
  const pu = meters && meters.purity;
  return `⟨n⟩ ${fmtFn(mp)}  ·  purity ${fmtFn(pu)}`;
}