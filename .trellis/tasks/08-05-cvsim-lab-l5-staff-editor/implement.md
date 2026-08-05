# Gaussian Lab L5 — Implement 步骤

## 阶段 1：纯函数核心（ops.js，node --test 先行）

- [x] 1.1 `vacuum` 入 OPS（label "真空模"，kind source，modes 1，params {}）；`tmsv` 移出 OPS（保留后端）
- [x] 1.2 `sortNodes(nodes)`：按 (x, modeKey) 稳定排序，source 恒前（x=-∞）
- [x] 1.3 `placeNode(nodes, op, modeOrModes, x)` / `startPlacing(op, modeA)` / `finishPlacing(nodes, modeB)` / `cancelPlacing()`：放置状态机纯函数
- [x] 1.4 `moveNodeX(nodes, id, x)`：改 ui.x + sortNodes 重排
- [x] 1.5 `sourceRows(nodes)`：源 → 行映射（coherent/vacuum→1 行、tmsv→2 行、vacuum nmode>1→n 行），每行带源 id
- [x] 1.6 `removeSource(nodes, id)`：连带删除该源行上所有门，返回 (newNodes, removedIds)
- [x] 1.7 `toCircuitJson` 输出带 `ui: {x}`；`stateFromJson` 无 ui.x → 按索引赋 x
- 验证：node --test 全绿（新增 staff 测试文件）

## 阶段 2：DOM 渲染（staff.js 新文件）

- [x] 2.1 五线谱网格渲染：`sourceRows` → 行 + 源标记 + 门块绝对定位
- [x] 2.2 双模门跨行渲染（竖直块）
- [x] 2.3 palette 拖放：dragover 轨道判定 mode；单模落定 / 双模进入 placing
- [x] 2.4 placing 视觉：预览门 + 轨道 .arm 高亮 + 状态条提示；点击轨道 B 落定 / Esc / 空白取消 / 同模拒绝
- [x] 2.5 已有门拖动改 x（重排）+ 悬停 × 删除 + 拖空白弹回
- [x] 2.6 源标记渲染 + 删源确认 + 连带删除
- 验证：浏览器手测 + headless CDP 截图

## 阶段 3：浮层 + 集成

- [x] 3.1 门块点击 → 参数浮层（滑块+数字复用）；Esc/外点关闭；实时 emit
- [x] 3.2 源标记点击 → 浮层（coherent α / tmsv r）
- [x] 3.3 scan 联动：浮层打开 → onPickSweep → app.js 同步下拉
- [x] 3.4 JSON textarea 收折叠区（editor.js 布局 + style.css）
- [x] 3.5 托盘图标化（style.css + index.html label 简化）
- [x] 3.6 editor.js 旧测试迁移（renderRows 移除 → staff 渲染）；frozen-graph 策略验证（JSON 编辑→五线谱同步）

## 阶段 4：验证 + 文档

- [x] 4.1 pytest 全绿（后端未动，回归确认）
- [x] 4.2 node --test 全绿；ruff lab 干净
- [x] 4.3 headless CDP：五线谱渲染、双模两步放置、扫参联动、JSON 折叠、旧 JSON 载入
- [x] 4.4 vision-gaussian-lab-ui.md amend（五线谱交互 + 托盘变更）+ changelog
- [x] 4.5 OCR review（lab 前端改动）— 25m18s 完成，5 findings（2 medium+2 low 已修 a92a088，1 浮点 x 为设计决策忽略）
