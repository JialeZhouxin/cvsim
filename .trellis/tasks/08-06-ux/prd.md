# PRD: UX 差距优化 —— 托盘分组 / 删除命中区 / 双模放置引导

## 背景

`docs/lab-drag-ux.md`（Laws of UX 锚定的体验设计）§7 差距对照表列出当前实现与理想设计的差距。本任务落地其中 **3 项可执行差距**：

| # | 法则 | 差距 | 建议 |
|---|------|------|------|
| 1 | Fitts's Law | 删除按钮 × 命中区偏小（~16px） | 命中区 ≥ 24px |
| 2 | Hick's Law / Choice Overload | 托盘无分组 | 按 源/门/通道/测量 分组加分隔线 |
| 3 | Goal-Gradient Effect | 双模放置第二步无引导 | 目标轨道加"→ 点击"微文案 |

其余差距项（§7 中已 ✓）不动；本任务**纯前端视觉/交互**，不涉及后端 IR 与物理。

## 验收标准

1. **删除按钮**：命中区 ≥ 24×24px（含 padding/伪元素扩展），悬停门才出现的行为不变，点击行为不变；probe 删除用例仍过。
2. **托盘分组**：`OPS` 按 `kind`（source/single/two + channel 标记）分组，组间有分隔线 + 组标题（源 / 门 / 通道），白名单顺序不变；`palette: false` 的 op 仍不出现。
3. **双模引导**：placing 状态（第一步后）目标轨道（非 modeA 的轨道）显示微文案"→ 点击"或等效提示，放置完成/取消后消失；状态栏提示保留。
4. 回归：`node --test tests/editor.test.mjs`、`node tests/lab_staff_probe.mjs`、`node tests/lab_scan_probe.mjs`、pytest 相关套件全绿。

## 不做（非目标）

- 不改物理/API（circuit_v0 不变）
- 不新增托盘操作种类
- 不做整体重设计
