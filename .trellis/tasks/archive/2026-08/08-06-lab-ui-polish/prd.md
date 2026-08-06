# PRD: Lab UI 14 项优化（识图结果落地）

**Task**: `.trellis/tasks/08-06-lab-ui-polish`
**范围**: `cvsim/lab/static/`（index.html / style.css / tokens.css / app.js / editor.js / staff.js / ops.js）
**约束**: 不新增依赖；纯前端；不触碰 `cvsim/` 库代码与后端 API；维持 zero-scroll 工作台决策（80rem 断点、默认无滚动条、details 折叠）。

---

## 背景

用户对 Gaussian Lab 截图做了 14 条识图结果。逐条核对源码后，11 条落地、1 条改方案、1 条保守化、1 条不适用（系统级）。

## 需求决策表

| # | 识图结果 | 结论 | 方案 |
|---|---------|------|------|
| 1 | 版本号位置偏远 | ✅ 做 | `#version-tag` 从 header 右缘移入 `.lite__brand`（标题右侧） |
| 2 | 托盘分类标签过浅 | ✅ 做 | `.palette__group-title` 对比度 `color-mix(ink 55%)` → `75%` |
| 3 | 托盘术语缺提示 | ✅ 做 | palette item 加 `title` 属性（中文物理含义一句话）；不做图标 |
| 4 | 轨道行高过大 | ✅ 做 | `staff.js` `ROW_H` 56 → 44px，`.staff__row` 相关值（lane wire top 等）同步 |
| 5 | 状态栏 "ok" 模糊 | ✅ 做 | `data-state="ok"` 时 CSS `::before` 绿色 ✓；保持 error 态红底 |
| 6 | colorbar 缺刻度 | ✅ 做 | colorbar 下标注 `min / max` 数值（来自 wmin/wmax），"max" 截断修复 |
| 7 | PURITY 全大写 | ✅ 做 | 中文主标签（纯度/平均光子数/对数负度）+ 去 `text-transform: uppercase` |
| 8 | 折叠后仅剩标题 | 🔄 改方案 | **不做预览图**（违背 zero-scroll）；summary 加一行结果摘要（如 `E_N 最大 0.42 @ α=0.8`） |
| 9 | 按钮无反馈 | ✅ 做 | hover/active 增强（亮度/位移更明显） |
| 10 | 拖拽说明被忽略 | ✅ 做 | hint 移出 staff 下方，置于 `panel__head` 下（轨道区上方） |
| 11 | "激活Windows"水印 | ❌ 不做 | 系统级水印，非应用元素 |
| 12 | Wigner 占屏过大 | ⚠️ 保守做 | grid 右列 `1.2fr → 1.1fr`；若 probe scrollbar 失败则回退 1.2fr。**不做**可拖拽分隔条 |
| 13 | 806ms 响应慢 | ✅ 做 | 拖拽期间（dragstart→dragend）抑制 emit，drop 后单次运行；保留 debounce 120ms；不动 `view.n` |
| 14 | 托盘未分组折叠 | ✅ 做 | 每组用 `<details>` 折叠（默认展开），省窄列高度 |

## 验收标准

1. `node --test tests/editor.test.mjs` 通过
2. `tests/lab_scan_probe.mjs`、`tests/lab_staff_probe.mjs`、`tests/lab_undo_probe.mjs` 全过（hit-test / wheel / 默认无滚动条守卫）
3. `pytest tests/test_lab_*.py tests/test_lab_api.py` 通过（后端未动，回归保险）
4. 无新依赖；style.css 无 raw 颜色/间距字面量（tokens only，design-system 规则 1）
5. 手动目检：起 server，确认 11 项视觉/交互改动生效、折叠默认态无滚动条、拖拽后结果正常更新
6. OCR review 无 blocker 级发现

## 明确不做

- 托盘图标（窄列放图标挤中文标签，无现成图标体系）
- 可拖拽分隔条（投入/收益比低）
- 扫描折叠预览图（违背 zero-scroll）
- `view.n` 降采样（改变保存 JSON 的显示语义）
- 后端任何改动

## 风险

- #12 列宽变窄 → probe scrollbar 检查可能失败 → 回退 1.2fr（已列为标准）
- #4 行高变化 → staff probe 拖拽坐标可能偏移 → 以 probe 结果为准微调
- #13 拖拽抑制 → 需保证 drop/取消拖拽后一定有 emit（无状态丢失）
- #8 summary 需在每次 run/scan 后更新（`render()` 与 `drawScanCurve` 挂点）
