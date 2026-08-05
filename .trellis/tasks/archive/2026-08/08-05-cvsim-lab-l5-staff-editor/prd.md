# Gaussian Lab L5 — 五线谱式电路编辑器（staff editor）

## Goal

Lab L5 / P1（vision-gaussian-lab-ui.md）：将前端**列表式**电路编辑（palette 拖入 `#node-list` + mode 参数面板 + ↑↓ 排序）**替换**为**量子线路式五线谱编辑**——每个模一条横向轨道，操作拖到轨道 = 作用于该模，水平位置 = 时序。`circuit_v0` JSON IR + 后端**零接触**。

## Background

- 现状：`editor.js` 列表式（palette DnD/click → node-list 尾部；mode 靠参数面板；↑↓ 移动；JSON 双向同步 frozen-graph）
- 后端 `_check_mode` 对越界 mode 抛 `CircuitV0Error`（ir.py L211）→ 删源必须连带删门
- 后端源支持：`vacuum`（nmode≥1）、`coherent`、`tmsv`（ir.py `_source`）；前端 palette 现仅 tmsv/coherent
- `two_mode_squeeze` 门（kind: two）已存在 = TMSV 操作的通用形式（`exp(r(a†b†−ab))` 作用于任意两模）

## Requirements

### R1 — 五线谱画布（替换 node-list）
- 每模一条横向轨道，行序 = mode 升序；门 = 轨道上的方块；水平 x = 时序
- 电路面板内**双向滚动**容器（不动 3 列一屏骨架）；托盘图标化让宽
- JSON textarea 收为电路面板内折叠区（默认折叠；双向同步 + frozen-graph 策略保留）

### R2 — 排序契约
- 执行序 = nodes 数组序 = 按 **(x, 模序号)** 稳定排序；同 x 模小在前；双模门取 `modes[0]`
- 移动门改 x → 实时重排数组 → JSON 同步新顺序
- 无并行列概念（IR 线性顺序；CV 操作顺序敏感）

### R3 — 放置交互
- 单模门：拖到轨道 → 落定 `mode`（=`拖到的轨道`）
- 双模门（beamsplitter/mz/two_mode_squeeze）：拖到轨道 A → 半透明预览 + `modes[0]=A` + 轨道 A 高亮 + 状态条提示"选择第二个模式" → **点击**另一轨道 B → 落定 `modes[1]=B`
- 取消：Esc / 点空白 → 丢弃回正常态；点击同模 A → 拒绝 + 提示"双模操作需要两个不同模式"，保持待选态
- 双模门需 ≥2 个源模（沿用现有 sourceModes 守卫）

### R4 — 源重构
- palette 源 = **`真空模`（+1 模，无参数）** + `coherent`（1 模，α）
- **`tmsv` 源从 palette 移除**（后端 + JSON IR 保留兼容，旧文件可载入）；构建纠缠 = 真空模 + `two_mode_squeeze` 门
- 源渲染：轨道左端标记（coherent 单行圆点；真空模纯标签）；源不参与水平排序（数组最前）
- 删源 = 删除其贡献行 + **连带删除**作用在这些模上的所有门（先确认弹窗），否则后端越界报错

### R5 — 参数编辑
- 点击门块 → 浮层参数卡片（复用滑块+数字输入）；点空白/Esc 关闭；实时更新 + 就地重跑
- 源标记点击 → 同款浮层（coherent α）
- 浮层内显示 mode/modes（只读）

### R6 — 移动/删除
- 拖动已放门块 → 改 x 重排；拖到无模区 → 弹回原位
- 悬停门块 → 右上角 `×` 删除（无连带）
- 双模门移动只改 x（modes 不变）；改 mode = 删+重放

### R7 — 扫描联动
- scan 面板保留下拉兜底；点击门块参数浮层时，若该门有可扫参数（`sweep`）→ 自动同步 scan 面板节点下拉

### R8 — 旧 JSON 兼容
- 载入无 `ui.x` 的 JSON → 按数组序排格子，不报错
- x 坐标持久化：node 级 `ui` 字段（`ui: {x, t?}`）；IR 核心 schema 不变（`ui` 本就是自由对象）
- 手写 JSON 不写 x 合法

## Acceptance Criteria

- [ ] **A1 放置单模**：拖 `phase` 到轨道 1 → 节点 mode=1，位置 = drop 处 x
- [ ] **A2 放置双模**：拖 `beamsplitter` 到轨道 0 → 预览 + 高亮 + 提示 → 点轨道 2 → modes=[0,2]；Esc/空白取消无残留；点同模拒绝且保持待选态
- [ ] **A3 排序**：同 x 多门按模序渲染 + 数组序正确；JSON 输出顺序与 (x, mode) 一致
- [ ] **A4 源**：真空模 +1 模；coherent +1 模；palette 无 tmsv；删 TMSV 源（旧 JSON 载入）连带删其门并确认
- [ ] **A5 参数浮层**：点门弹浮层、滑块调参即时生效；Esc/空白关闭
- [ ] **A6 移动/删除**：拖门改 x 重排；悬停 × 删除；拖空白弹回
- [ ] **A7 扫描联动**：点可扫门 → scan 面板目标自动同步
- [ ] **A8 兼容**：无 ui.x JSON 载入按数组序排格子不报错；旧 circuit_v0 文件全量载入可运行
- [ ] **A9 回归**：pytest 全绿、node --test 全绿（纯函数迁移）、ruff lab 干净、vision-gaussian-lab-ui.md amend + changelog
- [ ] **A10 headless**：CDP 验证五线谱渲染、双模两步放置流程、折叠 JSON 区

## Out of Scope

- 后端/IR/schema 任何改动（含新增源、排序字段）
- undo（独立任务）
- 双模门拖放直接改 modes（移动只改 x）
- 并行列/并行执行
- 模拟器 Phase 3

## Technical Notes

- 排序键实现：`ui.x`（float）+ 模序号（single: mode；two: modes[0]）；稳定排序重排 nodes
- 拖放用 HTML5 DnD（现有 palette 机制扩展）；"待选第二模"状态存 editor state
- 双模门预览 = 半透明方块；高亮 = 轨道 CSS class
- 源轨道行数 = `sourceModes()`；行序按 mode 升序（空洞编号允许，后端只看 mode < nmode）
- editor.js 纯函数（排序/放置状态机/JSON 构建）ESM 导出供 node --test；DOM 在 initEditor
