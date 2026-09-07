/* 票2 — 曲线几何 leaf（零 import、零 DOM，node --test 直测；ADR-0009）。
   /scan 折线与 /fidelity path 两段绘制的纯核：有限值折叠、绘图域计算、
   坐标映射、折线断段 / path 拼接。app.js 消费本模块，自身只留 DOM 汇点
   与文案。 */
"use strict";

/** xs/ys 平行数组 → 有限值点对。默认丢弃 y 非 finite（null/NaN/Infinity/
    非数值）；opts.yClamp=[lo,hi] 时 y 先钳制（fidelity 截断 GKP 数值过冲，
    display only）——钳制在过滤后施加，被钳到边界的点仍保留。x 经 Number
    归一。 */
export function finitePoints(xs, ys, opts = {}) {
  const [lo, hi] = opts.yClamp || [null, null];
  const pts = [];
  for (let i = 0; i < ys.length; i++) {
    const y = ys[i];
    if (typeof y !== "number" || !Number.isFinite(y)) continue;
    const cy = opts.yClamp ? Math.min(hi, Math.max(lo, y)) : y;
    pts.push({ x: Number(xs[i]), y: cy });
  }
  return pts;
}

/** 绘图域计算。scan 模式（opts.yPad=0.1）：x 取 xs 首末，y 数据域上下各
    展宽 yPad 比例；数据平线（ymin===ymax）断轴补齐 ∓0.5 绝对量（不零高
    图、不除零）。fid 模式（opts.baseline）：基线 0 并入 y 域，yhi 至少
    ylo+1e-9 防全零退化。返回 {x0,x1,ylo,yhi}。 */
export function plotDomain({ xs, ys, yPad, baseline }) {
  const finiteYs = ys.filter((y) => typeof y === "number" && Number.isFinite(y));
  const x0 = xs[0];
  const x1 = xs[xs.length - 1];
  const ymin = Math.min(...finiteYs);
  const ymax = Math.max(...finiteYs);
  let ylo, yhi;
  if (yPad !== undefined) {
    ylo = ymin === ymax ? ymin - 0.5 : ymin - (ymax - ymin) * yPad;
    yhi = ymin === ymax ? ymin + 0.5 : ymax + (ymax - ymin) * yPad;
  } else {
    ylo = Math.min(baseline, ymin);
    yhi = Math.max(baseline, ymax, ylo + 1e-9);
  }
  return { x0, x1, ylo, yhi };
}

/** 数据域 → 像素线性映射工厂。X: x0→pad.l, x1→W−pad.r；Y: yhi→pad.t,
    ylo→H−pad.b（y 向上翻转）。x1===x0 时分母置 1（除零防护）；
    yhi===ylo 由 plotDomain 保证不出现，不再重复防护。 */
export function makeScale({ x0, x1, ylo, yhi, W, H, pad }) {
  const X = (x) => pad.l + ((x - x0) / (x1 - x0 || 1)) * (W - pad.l - pad.r);
  const Y = (y) => pad.t + (1 - (y - ylo) / (yhi - ylo)) * (H - pad.t - pad.b);
  return { X, Y };
}

/** scan 折线断段：points 是长度 n 的槽位数组（有限对或 null），经 X/Y 映射
    拼成 "x.xx,y.yy x.xx,y.yy" 段（toFixed(2)，同原实现），非有限槽断开。
    返回段字符串数组（消费方逐段建 polyline 元素）；无内容段不产出。 */
export function polylineSegments(points, X, Y, n) {
  const segs = [];
  let seg = "";
  for (let i = 0; i < n; i++) {
    const p = points[i];
    if (!p) {
      if (seg) { segs.push(seg); seg = ""; }
      continue;
    }
    seg += (seg ? " " : "") + X(p[0]).toFixed(2) + "," + Y(p[1]).toFixed(2);
  }
  if (seg) segs.push(seg);
  return segs;
}

/** fid path：首点 M 后续 L，toFixed(1)（同原实现）；空点集 → 空串。 */
export function svgPath(pts, X, Y) {
  return pts.map((p, i) => `${i ? "L" : "M"}${X(p.x).toFixed(1)} ${Y(p.y).toFixed(1)}`).join(" ");
}