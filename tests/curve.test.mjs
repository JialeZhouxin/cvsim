/* 票2 — curve leaf 契约测试 (node --test, zero deps, ADR-0009)。
   锁两曲线（/scan 折线 + /fidelity path）的纯几何：有限值折叠、断轴/基线
   域计算、坐标映射、polyline 断段与 path 拼接。期望值全部手推独立事实源
   （固定映射 X(x)=10+40x, Y(y)=90−40y 的工作例），不回抄实现。 */
import test from "node:test";
import assert from "node:assert/strict";

import { finitePoints, plotDomain, makeScale, polylineSegments, svgPath } from "../cvsim/lab/static/curve.js";

/* ── finitePoints ─────────────────────────────────────────── */

test("finitePoints：scan 模式（无钳制）— 丢弃 null/NaN/Infinity/非数值，保留有限值原样", () => {
  const pts = finitePoints([0, 1, 2, 3, 4], [1, null, NaN, 2, Infinity]);
  assert.deepEqual(pts, [{ x: 0, y: 1 }, { x: 3, y: 2 }]);
});

test("finitePoints：非数值 y 丢弃（Number.isFinite 语义涵盖 typeof number）", () => {
  assert.deepEqual(finitePoints([0, 1, 2], [0.5, "x", 1.5]), [{ x: 0, y: 0.5 }, { x: 2, y: 1.5 }]);
});

test("finitePoints：fid 模式 yClamp [0,1] — 截断 GKP 数值过冲（display only）", () => {
  const pts = finitePoints([0, 1, 2, 3], [1.2, -0.3, 0.5, 1], { yClamp: [0, 1] });
  assert.deepEqual(pts, [{ x: 0, y: 1 }, { x: 1, y: 0 }, { x: 2, y: 0.5 }, { x: 3, y: 1 }]);
});

test("finitePoints：x 经 Number 归一（JSON 数字恒等，字符串坐标不再渗入映射）", () => {
  const pts = finitePoints(["3", 2], [1, 1]);
  assert.deepEqual(pts, [{ x: 3, y: 1 }, { x: 2, y: 1 }]);
  assert.ok(pts.every((p) => typeof p.x === "number"));
});
/* ── plotDomain ─────────────────────────────────────────── */

test("plotDomain：scan 模式 — x 取 xs 首末，y 数据域 ±10% 展宽", () => {
  // xmin=0, xmax=4, ymin=1, ymax=2 → 展宽 0.1 → ylo=0.9, yhi=2.1
  const d = plotDomain({ xs: [0, 1, 2, 4], ys: [2, 1, 1.5, 2], yPad: 0.1 });
  assert.deepEqual(d, { x0: 0, x1: 4, ylo: 0.9, yhi: 2.1 });
});

test("plotDomain：单点/平线断轴补齐 — ylo/yhi = ymin∓0.5（不除零、不零高图）", () => {
  const d = plotDomain({ xs: [1, 2], ys: [3, 3], yPad: 0.1 });
  assert.deepEqual(d, { x0: 1, x1: 2, ylo: 2.5, yhi: 3.5 });
});

test("plotDomain：fid 模式 — 基线 0 并入 y 域（y0=min(0,数据)，y1≥y0+1e-9）", () => {
  const d = plotDomain({ xs: [0.5, 1], ys: [0.9, 0.2], baseline: 0 });
  assert.deepEqual(d, { x0: 0.5, x1: 1, ylo: 0, yhi: 0.9 });
  // 全零数据：y0=y1=0 → 防护抬到 1e-9
  const z = plotDomain({ xs: [0.5, 1], ys: [0, 0], baseline: 0 });
  assert.equal(z.yhi, 1e-9);
});

/* ── makeScale（共享映射工厂，工作例手推） ───────────────── */

test("makeScale：线性映射端点 — X(x0)=padL、X(x1)=W−padR、Y(yhi)=padT、Y(ylo)=H−padB", () => {
  // W=100,H=100,pad 全 10：X(x)=10+80x̂, Y(y)=90−80ŷ
  const { X, Y } = makeScale({ x0: 0, x1: 1, ylo: 0, yhi: 1, W: 100, H: 100, pad: { l: 10, r: 10, t: 10, b: 10 } });
  assert.equal(X(0), 10);
  assert.equal(X(1), 90);
  assert.equal(Y(1), 10);   // yhi → padT
  assert.equal(Y(0), 90);   // ylo → H−padB
  assert.equal(X(0.5), 50); // 中点
});

test("makeScale：x1===x0 除零防护 — 分母置 1，不产生 NaN", () => {
  const { X } = makeScale({ x0: 5, x1: 5, ylo: 0, yhi: 1, W: 100, H: 100, pad: { l: 10, r: 10, t: 10, b: 10 } });
  assert.equal(X(5), 10);   // (5-5)/1 = 0 → padL
  assert.ok(Number.isFinite(X(5)));
});

/* ── polylineSegments（scan 折线断段） ───────────────────── */

test("polylineSegments：连续有限段 → 单段 polyline（保留 xs/ys 原序）", () => {
  // X/Y 映射沿用工作例：X(x)=10+40x, Y(y)=90−40y → (0,1)→"10,50" (1,2)→"50,10"
  const segs = polylineSegments(
    [[0, 1], [1, 2]],
    (x) => 10 + 40 * x,
    (y) => 90 - 40 * y,
    2,
  );
  assert.deepEqual(segs, ["10.00,50.00 50.00,10.00"]);
});

test("polylineSegments：中间空洞（null/非有限）→ 两段 polyline（curve gap）", () => {
  const segs = polylineSegments(
    [[0, 1], null, [2, 3]],
    (x) => 10 + 40 * x,
    (y) => 90 - 40 * y,
    4,
  );
  assert.deepEqual(segs, ["10.00,50.00", "90.00,-30.00"]);
});

test("polylineSegments：全空洞 → 空数组（不产出空 polyline 元素）", () => {
  const segs = polylineSegments([null, null], (x) => x, (y) => y, 2);
  assert.deepEqual(segs, []);
});

/* ── svgPath（fid 的 M/L path） ──────────────────────────── */

test("svgPath：首点 M 后续 L，toFixed(1)", () => {
  const d = svgPath(
    [{ x: 0, y: 1 }, { x: 1, y: 2 }],
    (x) => 10 + 40 * x,
    (y) => 90 - 40 * y,
  );
  assert.equal(d, "M10.0 50.0 L50.0 10.0");
});

test("svgPath：空点集 → 空串", () => {
  assert.equal(svgPath([], (x) => x, (y) => y), "");
});
