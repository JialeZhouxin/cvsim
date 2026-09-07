# 票2：curve.js — 扫描曲线与保真度曲线的几何纯核

## 概述

从 app.js 提取两条曲线绘制（`drawScanCurve`、`drawFidSvg`）的几何/字符串纯核到 `cvsim/lab/static/curve.js`（零 import、零 DOM，leaf 纪律）。这是前端最复杂的两段未测数学：有限值折叠、断轴补齐、坐标映射、polyline/path 拼接。[spec](./spec.md) 票 2/4。

## 变更

1. 新建 `curve.js`，迁移纯逻辑：
   - **有限值折叠**：`finitePoints(xs, ys)` — `drawScanCurve` 的过滤（typeof number + isFinite → `[x,y]` 对，app.js:609-615）与 `drawFidSvg` 的过滤+钳制（null 丢弃 + `y=clamp(0,1)` 截断 GKP 数值过冲，app.js:382-386）统一为一个纯函数（钳制开关参数化，两处共用一个折叠知识）；
   - **坐标映射**：`makeScale({x0,x1,y0,y1,W,H,pad})` → `{X(x), Y(y)}`——`drawScanCurve` 的 X/Y（padL/padR/padT/padB，含 `ymin===ymax` 断轴补齐 ±0.5，app.js:625-629）与 `drawFidSvg` 的 X/Y（pad 对象 + `x1-x0 || 1` 除零防护 + `y1 ≥ y0+1e-9`，app.js:394-399）统一为一个带选项的映射工厂；
   - **折线拼接**：`polylinePath(points)` — scan 的 null 断段 polyline 字符串（app.js:644-651）与 fid 的 `M/L` path 字符串（app.js:400-401）各导出一个纯字符串函数。
   - 实现时若两曲线某子逻辑无法共用，允许各自独立导出——不为统一而统一，接口最小优先。
2. app.js `drawScanCurve` / `drawFidSvg` 改为消费导出：保留 DOM 汇点（scanSvg/scanNote/`$("scan-summary")`/innerHTML 落笔）与文案生成，数学全走 curve.js。
3. 新建 `tests/curve.test.mjs`（leaf 直测）：
   - finitePoints：null/NaN/Infinity 丢弃；fid 模式钳制 [0,1]；scan 模式保留有限值不钳制；
   - makeScale：线性映射端点（x0→padL、x1→W−padR、ylo→H−padB、yhi→padT）；`ymin===ymax` 断轴补齐；`x1===x0` 除零防护不产生 NaN；
   - polylinePath：连续有限段拼 polyline；中间 null 断段（两段 polyline）；全 null → 空串。

## 验收

- [ ] `node --test tests/curve.test.mjs`（并入显式列文件清单）全绿
- [ ] pytest 全绿；手工验证 /scan 曲线与 /fidelity 曲线渲染与改造前逐像素意图一致（同输入同输出）
- [ ] app.js 两函数中不再有内联坐标映射/折叠/字符串几何数学
- [ ] curve.js 零 import、零 `document` 引用（grep 验证）

**Blocks**: 无