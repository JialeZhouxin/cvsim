/* 票1 — colormap leaf 契约测试 (node --test, zero deps, ADR-0009)。
   锁三块纯核：LUT 插值构建、Wigner 网格校验（防御语义）、对称归一化 +
   t 映射。配色知识（改色轴）与热图数值纪律（截断泄漏级诚实）首次可直测。 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  buildLut,
  inspectWignerGrid,
  validateWignerGrid,
  wignerScale,
  wignerT,
} from "../cvsim/lab/static/colormap.js";

/* ── buildLut ─────────────────────────────────────────────── */

test("buildLut：端点锚定 — i=0 落首锚、i=255 落末锚（scale over len-1 语义）", () => {
  const lut = buildLut();
  assert.ok(lut instanceof Uint8Array);
  assert.equal(lut.length, 256 * 3);
  // 首锚 [15,20,75]
  assert.equal(lut[0], 15);
  assert.equal(lut[1], 20);
  assert.equal(lut[2], 75);
  // 末锚 [255,250,210]
  assert.equal(lut[255 * 3], 255);
  assert.equal(lut[255 * 3 + 1], 250);
  assert.equal(lut[255 * 3 + 2], 210);
});

test("buildLut：i=127/128 跨黑色锚点（锚 8 [0,0,0]）— 两侧插值对称趋零", () => {
  // 17 锚 16 段：t = i/255*16；i=127 → 段 7（[24,8,28]→[0,0,0]）f=0.9686 → round(24·0.0314)=1, round(28·0.0314)=1
  const lut = buildLut();
  assert.equal(lut[127 * 3], 1);
  assert.equal(lut[127 * 3 + 1], 0);
  assert.equal(lut[127 * 3 + 2], 1);
  // i=128 → 段 8（[0,0,0]→[24,7,2]）f=0.0314 → [1,0,0]
  assert.equal(lut[128 * 3], 1);
  assert.equal(lut[128 * 3 + 1], 0);
  assert.equal(lut[128 * 3 + 2], 0);
});

/* ── validateWignerGrid ─────────────────────────────────── */

const okGrid = [[0.5, -1.25], [2, 0]];

test("validateWignerGrid：合法 2×2 网格静默通过", () => {
  assert.doesNotThrow(() => validateWignerGrid(okGrid));
});

test("validateWignerGrid：非法形状逐一抛 Invalid Wigner grid", () => {
  for (const bad of [
    null,                                        // 非数组
    [[0, 0]],                                    // 尺寸 1 < 2
    Array.from({ length: 513 }, () => [0, 0]),   // 尺寸 513 > 512
    [[0, 0], [0]],                               // 行不等长
    [[0, 0], [0, NaN]],                          // NaN
    [[0, 0], [0, Infinity]],                     // Infinity
    [[0, 0], [0, "x"]],                          // 非数值
  ]) {
    assert.throws(() => validateWignerGrid(bad), /Invalid Wigner grid/, JSON.stringify(bad)?.slice(0, 40));
  }
});

/* ── wignerScale ─────────────────────────────────────── */

test("wignerScale：对称尺度 = max(|wmin|,|wmax|) — 正主导/负主导/对称三例", () => {
  assert.equal(wignerScale([[1, -3], [2, 0.5]]), 3);   // 负主导
  assert.equal(wignerScale([[-1, 0.25], [4, 0.5]]), 4); // 正主导
  assert.equal(wignerScale([[-2, 2], [2, -2]]), 2);     // 对称
});

test("wignerScale：全零网格兜底 1（|| 1 防除零，诚实退化）", () => {
  assert.equal(wignerScale([[0, 0], [0, 0]]), 1);
});

/* ── wignerT ─────────────────────────────────────────── */

test("wignerT：端点锚定 — +scale→255、−scale→0、0→中点 128", () => {
  const s = 5;
  assert.equal(wignerT(s, s), 255);
  assert.equal(wignerT(-s, s), 0);
  assert.equal(wignerT(0, s), 128); // round(0.5*255) = round(127.5) = 128
});

test("wignerT：越界双向裁剪", () => {
  const s = 5;
  assert.equal(wignerT(10, s), 255);  // 1.5×scale
  assert.equal(wignerT(-10, s), 0);   // −1.5×scale
});

/* ── inspectWignerGrid（C2 R2：校验+求尺度合一）───────────── */

test("inspectWignerGrid：合法网格返回与 wignerScale 相同的 scale", () => {
  for (const g of [okGrid, [[1, -3], [2, 0.5]], [[-1, 0.25], [4, 0.5]], [[-2, 2], [2, -2]]]) {
    assert.equal(inspectWignerGrid(g).scale, wignerScale(g), JSON.stringify(g));
  }
});

test("inspectWignerGrid：全零网格兜底 scale=1（与 wignerScale 一致）", () => {
  assert.equal(inspectWignerGrid([[0, 0], [0, 0]]).scale, 1);
});

test("inspectWignerGrid：非法网格逐条抛 Invalid Wigner grid（与 validateWignerGrid 用例对齐）", () => {
  for (const bad of [
    null,                                        // 非数组
    [[0, 0]],                                    // 尺寸 1 < 2
    Array.from({ length: 513 }, () => [0, 0]),   // 尺寸 513 > 512
    [[0, 0], [0]],                               // 行不等长
    [[0, 0], [0, NaN]],                          // NaN
    [[0, 0], [0, Infinity]],                     // Infinity
    [[0, 0], [0, "x"]],                          // 非数值
  ]) {
    assert.throws(() => inspectWignerGrid(bad), /Invalid Wigner grid/, JSON.stringify(bad)?.slice(0, 40));
    // 与既有校验器判定必须完全一致（合一不得放宽或收紧）
    let a = null, b = null;
    try { validateWignerGrid(bad); } catch (e) { a = e.message; }
    try { inspectWignerGrid(bad); } catch (e) { b = e.message; }
    assert.equal(b, a, "合一后的抛错语义须与 validateWignerGrid 逐字一致");
  }
});

test("inspectWignerGrid：合法网格不得抛错（与 validateWignerGrid 一致）", () => {
  assert.doesNotThrow(() => inspectWignerGrid(okGrid));
  let vThrew = false, iThrew = false;
  try { validateWignerGrid(okGrid); } catch { vThrew = true; }
  try { inspectWignerGrid(okGrid); } catch { iThrew = true; }
  assert.equal(iThrew, vThrew);
});