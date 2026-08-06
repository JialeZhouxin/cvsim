# PRD: Lab undo/redo 撤销栈 + fourier 托盘缺口 + 主剧本复验

## 背景

Lab UI（vision 0.1.6 解锁，L0–L5.5 已落地）存在三处收尾工作：

1. **undo/redo 撤销栈**（主任务）：vision §4.5 P1 点名 "撤销栈"，L4 归档注释 "undo 独立任务"，代码中 0 实现。五线谱编辑器操作密集（拖放、双模两步选择、删除、参数修改），误操作无路可退。
2. **fourier 托盘缺口**（小修复）：白名单 §4.2 ✅ 列有 `fourier`，后端 `cvsim/lab/ir.py` 支持（L20/42/248），但前端 `ops.js` 无定义 → 拖不出来，仅旧 JSON 可载入。
3. **主剧本复验**：L5.5 大改（格子化 snap、托盘分组、删除命中区）后，vision §5 接受度剧本 1–6+8 无复验记录，需确认无回退。

## 验收标准

1. **undo/redo**：
   - 五线谱编辑器所有可变操作（拖放添加、删除、参数修改、双模放置）均进入撤销栈；`Ctrl+Z` / `Ctrl+Y` 或 UI 按钮可回退/重做
   - 撤销后电路拓扑与参数完全恢复，后端结果（Wigner/meters/scan）随电路变化刷新
   - 撤销到空栈边界无崩溃；保存/载入 JSON 后历史栈重置
   - probe 回归：`node --test tests/editor.test.mjs`、`node tests/lab_staff_probe.mjs`、`node tests/lab_scan_probe.mjs` 全绿
2. **fourier**：托盘出现 fourier 门，可拖放、可运行，与后端 `ir.py` 语义一致（相位空间旋转 90°）
3. **主剧本复验**：vision §5 剧本 1–6+8 手工过一遍，结果记录到任务 research/ 或笔记，有回退则修复

## 不做（非目标）

- 不改物理/API（circuit_v0 不变、后端 IR 不新增 op）
- 不做多文档 tabs（vision P1 另一项，本次不做）
- 不加 thermal 源节点（vision §4.1 defer，需先 amend 文档）
- 不做整体重设计
