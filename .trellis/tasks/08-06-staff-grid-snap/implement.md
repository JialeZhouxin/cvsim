# implement.md — L5.5 staff 格子化与默认场景重构

## 实施清单

1. **ops.js — 纯函数改造**
   - `coherent` 加 `palette: false`（保留定义，旧 JSON 兼容；删 `sourceModes` 里无影响——coherent 仍算 1 模源）
   - 新增纯函数 `cellOccupied(nodes, mode, x) -> bool`：单模门占 (mode, round(x))；双模门占 (modes[0], round(x)) 与 (modes[1], round(x))；源不占格
   - `placeSingle`：x 改 `Math.round`；目标格被占 → 返回原 nodes（或结果对象），由 editor 层报错
   - `completePlacing`：x round；第二步 (modeB, x) 格被占 → `{ok:false, reason}`
   - `moveNodeX`：x round；目标格被占（且目标格非该门自身当前两格）→ 拒绝返回原 nodes
   - 执行顺序仍按 sortNodes（(x, mode)），不变
2. **staff.js — 交互**
   - dragover：实时计算 round 列 + 悬停轨道 → 目标格高亮（`--hover`）；冲突 → `--conflict` 红显
   - drop：沿用 ops 拒绝结果，失败走 onStatus
   - 幽灵预览块对齐整数列（已是）
   - 双模第二步：点击 B 轨道时若 (modeB, x) 被占 → onStatus 提示，保持 placing 状态
3. **app.js — DEFAULT_JSON**
   - 替换为：`vacuum`×2（s0/s1, nmode 1）+ `displace`×2（d0/d1, mode 0/1, ui.x=0, alpha=1.0）
4. **style.css**
   - `.staff__grid` 加垂直虚线分列（repeating-linear-gradient，每 GATE_W 一条）
   - `.staff__lane--hover`（悬停高亮）、`.staff__lane--conflict`（红显）样式；gate--preview 冲突态红边框
5. **测试**
   - `tests/editor.test.mjs`：新增 round snap、冲突拒绝、双模占两格、moveNodeX 拒绝用例；更新受影响断言
   - `tests/lab_staff_probe.mjs`：默认场景断言改 vacuum×2 + displace×2；加格子高亮/冲突红显断言
   - 运行 `node --test tests/editor.test.mjs`、`node tests/lab_staff_probe.mjs`
6. **回归**
   - `uv run pytest tests/test_lab_*.py -q`（后端不动，确认无回归）
   - headless CDP probe（若脚本可用）验证浏览器端

## 验证命令

```bash
node --test tests/editor.test.mjs
node tests/lab_staff_probe.mjs
uv run pytest tests/test_lab_ir.py tests/test_lab_api.py tests/test_lab_ui.py -q
```

## 评审关口

- 提交前自审：占格语义一致性（单模/双模/移动自身格豁免）、旧 JSON 兼容、错误提示可读
- OCR review（项目惯例：每任务必做）
