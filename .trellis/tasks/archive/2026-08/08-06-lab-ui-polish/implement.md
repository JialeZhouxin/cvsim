# Implement: Lab UI 14 项优化

**顺序**: 基线 → HTML → CSS → JS → 验证 → 目检。每步验证点明确。

## 0. 基线（改前先跑）

```
node --test tests/editor.test.mjs
node tests/lab_scan_probe.mjs && node tests/lab_staff_probe.mjs && node tests/lab_undo_probe.mjs
pytest tests/test_lab_ui.py -q
```
全部通过才动代码。记录基线结果。

## 1. HTML（index.html）

- **#1**: `#version-tag` 移到 `.lite__brand` 内（wordmark 右侧），badge 保留
- **#7**: meters 标签改中文：`纯度` / `平均光子数` / `对数负度`（label 语义不变）
- **#10**: 拖拽 hint `<p>` 移到 `panel__head` 之后、`#staff` 之前（轨道区上方）
- **#6**: colorbar 结构：`<span id="colorbar-min">` / canvas / `<span id="colorbar-max">`（替代孤立 "max"）
- **#8**: scan summary 加 `<span id="scan-summary">`（空时隐藏）；state-grid summary 同理（V 摘要可留空）

验证：HTML 结构无语法错（`details`/`span` 闭合）。

## 2. CSS（style.css / tokens.css）

- **#2**: `.palette__group-title` `color-mix(ink 55%)` → `75%`
- **#4**: `.staff__row` 高 56→44 相关值同步：`height: 44px`、lane wire `top: 27px` → `top: 21.5px`（行居中）、`.staff__grid` 背景偏移与 ROW_H 联动处核对（JS 用 ROW_H 常量，CSS 手写值需一致）
- **#5**: `.statusbar__msg[data-state="ok"]::before { content: "✓"; color: var(--color-success); }` + 间距
- **#6**: colorbar min/max 数值样式（`--text-xs`、`--color-muted`）
- **#7**: `.meter__label` 去掉 `text-transform: uppercase`，letter-spacing 保留或减
- **#9**: `.btn--primary:hover` 加亮（`color-mix(ink, accent)` 或 box-shadow），`:active` 位移保留并增强
- **#10**: hint 移后调整 margin（`.seq .hint` 顶部间距）
- **#12**: `@media (min-width: 80rem)` grid `13rem minmax(0,1fr) minmax(0,1.1fr)` —— probe 失败即回退
- **#14**: `.palette__group` 用 details 语义：`summary` 复用 `.palette__group-title` 样式 + 折叠箭头（复用 `.fold summary` 模式）；`summary::marker` 隐藏

验证：`node tests/lab_scan_probe.mjs`（scrollbar 守卫最敏感）。

## 3. JS（editor.js / app.js / ops.js）

- **#3**: palette card 加 `title`（editor.js palette 渲染处，来源 `OPS[op]` 加 `tip` 字段或映射表；中文一句话物理含义）
- **#4**: `staff.js` `ROW_H = 56` → `44`（唯一常量，双模门 span 自动适配）
- **#6**: `drawHeatmap` 把 `wmin/wmax` 写入 `#colorbar-min/max` 文本（`axisVal` 格式）；singular 分支清空
- **#8**: scan 完成后 summary 文本 = `E_N 最大 {ymax} @ {对应 x}`（`drawScanCurve` 挂点）；run/scan 前置为空
- **#13**: 拖拽期间抑制 emit：editor.js 加 `suppressEmit` 标志，dragstart 置 true / dragend（含取消）置 false 并 emit 一次；`onMove`/`onPlace` 走 `render()` 但 emit 被抑制。**注意**：undo/redo、JSON 编辑、按钮操作的 emit 不受影响
- **#13b**: `render()` 里 `emit` 前检查标志（不要动 hooks 签名）

验证：`node --test tests/editor.test.mjs` + `node tests/lab_staff_probe.mjs`（拖拽路径回归）。

## 4. 验证（对照 PRD 验收标准）

```
node --test tests/editor.test.mjs
node tests/lab_scan_probe.mjs && node tests/lab_staff_probe.mjs && node tests/lab_undo_probe.mjs
pytest tests/test_lab_ui.py tests/test_lab_api.py -q
grep -nE "#[0-9a-fA-F]{3,6}|oklch\(|rgb\(" style.css   # 应只命中 tokens.css 引用外的合法残留
```

## 5. 手动目检

起 server（`python -m cvsim.lab` 或等价命令），确认：
- 版本号在标题旁；托盘分类可读；palette 项 hover 有 title
- 轨道行高明显变紧凑；拖拽放置后结果刷新一次而非连续多次
- 状态栏 ✓ 图标；colorbar 有 min/max 数值
- meters 中文标签；scan summary 显示结果
- 默认折叠态三列均无滚动条；拖拽 hint 在轨道上方
- 按钮 hover 反馈明显

## 6. 收尾

- 跑 `tests/test_lab_ui.py` 全绿后提交
- 若 #12 或 #4 触发 probe 失败且无法微调 → 按 PRD 回退方案执行并记录
