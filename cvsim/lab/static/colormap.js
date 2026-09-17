/* 票1 — Wigner 配色 leaf（零 import、零 DOM，node --test 直测；ADR-0009）。
   三块纯核：diverging LUT 构建 / Wigner 网格校验 / 对称归一化 + t 映射。
   app.js drawHeatmap 消费本模块，自身只留 canvas/离屏/colorbar 落笔。 */
"use strict";

/* Diverging Wigner LUT: negative interference = blue/purple, W=0 = black,
   positive peaks = orange/yellow/white. Interpolated to 256 in JS. */
const LUT_ANCHORS = [
  [15, 20, 75], [29, 25, 105], [48, 22, 125], [78, 25, 135],
  [111, 29, 125], [111, 35, 100], [75, 24, 65], [24, 8, 28],
  [0, 0, 0], [24, 7, 2], [70, 17, 3], [125, 31, 2],
  [180, 60, 7], [224, 111, 22], [247, 177, 54], [255, 223, 105],
  [255, 250, 210],
];

/** 17 锚均匀插值出 256 级 RGB 查找表（Uint8Array 768，索引 i*3+c）。 */
export function buildLut() {
  const lut = new Uint8Array(256 * 3);
  const last = LUT_ANCHORS.length - 2;
  for (let i = 0; i < 256; i++) {
    // scale over len-1 so the final sample reaches the last anchor (f = 1)
    const t = (i / 255) * (LUT_ANCHORS.length - 1);
    const k = Math.min(Math.floor(t), last);
    const f = t - k;
    for (let c = 0; c < 3; c++) {
      lut[i * 3 + c] = Math.round(LUT_ANCHORS[k][c] + f * (LUT_ANCHORS[k + 1][c] - LUT_ANCHORS[k][c]));
    }
  }
  return lut;
}

/** Wigner 网格防御校验（原 drawHeatmap 内联防御块）：合法网格静默通过，
    非法（非数组 / 尺寸不在 2..512 / 行不等长 / 值非有限数）抛 Error。 */
export function validateWignerGrid(W) {
  if (!Array.isArray(W) || W.length < 2 || W.length > 512 ||
      W.some((row) => !Array.isArray(row) || row.length !== W.length ||
        row.some((v) => !Number.isFinite(v)))) {
    throw new Error("Invalid Wigner grid");
  }
}

/** 对称归一化尺度（原 drawHeatmap 内联）：物理零点锚在 LUT 中点（黑），
    全零网格兜底 scale=1（避免除零，诚实退化非 fabricated）。 */
export function wignerScale(W) {
  let wmin = Infinity, wmax = -Infinity;
  for (const row of W) for (const v of row) { if (v < wmin) wmin = v; if (v > wmax) wmax = v; }
  return Math.max(Math.abs(wmin), Math.abs(wmax)) || 1;
}

/** 一次遍历完成「校验 + 求尺度」（C2 R2）：原 drawHeatmap 先 validateWignerGrid(W)
    再 wignerScale(W)，两次 n² 扫描。语义与逐条调用等价——非法网格同样抛
    Error("Invalid Wigner grid")（含同样的判定顺序与维度范围），合法网格返回同一
    scale（含全零网格兜底 1）。
    app.js 消费 { scale }；保留 validateWignerGrid / wignerScale 导出不动
    （既有测试与其它消费者不受影响）。 */
export function inspectWignerGrid(W) {
  if (!Array.isArray(W) || W.length < 2 || W.length > 512) {
    throw new Error("Invalid Wigner grid");
  }
  let wmin = Infinity, wmax = -Infinity;
  const n = W.length;
  for (const row of W) {
    if (!Array.isArray(row) || row.length !== n) throw new Error("Invalid Wigner grid");
    for (const v of row) {
      if (!Number.isFinite(v)) throw new Error("Invalid Wigner grid");
      if (v < wmin) wmin = v;
      if (v > wmax) wmax = v;
    }
  }
  return { scale: Math.max(Math.abs(wmin), Math.abs(wmax)) || 1 };
}

/** W 值 → 0..255 的 LUT 索引（原 drawHeatmap 内联映射）：v=+scale→255、
    −scale→0、0→中点；越界裁剪。 */
export function wignerT(v, scale) {
  return Math.min(255, Math.max(0, Math.round(((v + scale) / (2 * scale)) * 255)));
}