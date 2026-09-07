# 票1：colormap.js — LUT 纯核 + Wigner 网格校验 + 对称归一化

## 概述

从 app.js 提取 Wigner 配色的纯核到 `cvsim/lab/static/colormap.js`（零 import、零 DOM，leaf 纪律见 CONTEXT.md「leaf 模块」、ADR-0009）。配色知识与热图数值纪律首次可直测。[spec](./spec.md) 票 1/4。

## 变更

1. 新建 `colormap.js`，迁移三块纯逻辑：
   - `LUT_ANCHORS` + `buildLut()`（app.js:24-41）→ 导出 `buildLut`（或预构建常量 `LUT`），插值逻辑原样；
   - **Wigner 网格校验**：`drawHeatmap` 开头的防御块（app.js:134-137，`Invalid Wigner grid` 抛错：Array/尺寸 2..512/行等长/值有限）→ 导出纯函数 `validateWignerGrid(W)`；
   - **对称归一化**：wmin/wmax 扫描 + `scale = max(|wmin|,|wmax|) || 1` + t 值裁剪映射 `((W[j][i]+scale)/(2*scale))*255`（app.js:143-149、164-167）→ 导出纯函数 `wignerScale(W)` 与 `wignerT(v, scale)`（或合并单函数，实现时按接口最小化定）。
2. app.js `drawHeatmap` 改为消费上述导出：校验、scale、t→LUT 索引全部经 colormap.js，自身只留 canvas/离屏/colorbar 落笔。
3. 新建 `tests/colormap.test.mjs`（leaf 直测）：
   - buildLut：端点锚定（i=0 → 首锚、i=255 → 末锚，f=1 注释语义）、中间插值抽查、输出 Uint8Array(768)；
   - validateWignerGrid：合法网格通过；非数组/尺寸越界（1 与 513）/行不等长/NaN·Infinity·非数值 各自抛 `Invalid Wigner grid`；
   - wignerScale：全零网格（`|| 1` 兜底）、正主导、负主导、对称；wignerT：v=+scale→255、v=−scale→0、v=0→127.5 取整、越界裁剪。

## 验收

- [ ] `node --test tests/colormap.test.mjs`（并入 AGENTS.md/CONTEXT.md 的显式列文件清单）全绿
- [ ] pytest 全绿（drawHeatmap 行为无回归，三后端渲染不变）
- [ ] app.js 中不再有 LUT_ANCHORS 字面量与网格校验/归一化内联数学
- [ ] colormap.js 零 import、零 `document` 引用（grep 验证）

**Blocks**: 无