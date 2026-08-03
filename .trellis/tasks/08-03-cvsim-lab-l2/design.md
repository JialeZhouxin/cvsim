# Design — Gaussian Lab L2: 序列流水线编辑器

> 上游: `prd.md`（D1–D8 已锁）；视觉延续 L1 Hallmark（Workbench · Cobalt）

## 1. 文件结构

```
cvsim/lab/static/
  index.html        # 三区布局: 托盘 | 序列 | 结果（结果区复用 L1）
  tokens.css        # 不变
  style.css         # + 托盘/序列/参数面板/滑块样式
  ops.js            # op 元数据 schema（8 op: 名称/标签/参数定义/mode 类别）
  editor.js         # 编辑器状态机: 托盘→序列, 排序, 参数, JSON 双向同步, 防抖
  app.js            # 改造: 由 editor.js 驱动; 保留 L1 渲染管线(热图/meters/矩阵)
  main.js           # 装配 + 启动（或并入 editor.js——最小化文件数）
```

**决策**: 不拆 main.js，装配放 editor.js 尾部；op 元数据独立 ops.js 供编辑器 + 单测共享。

## 2. Op 元数据（ops.js，对齐 ir.py 白名单子集）

| op | 类别 | params | 滑块范围/步长 |
|----|------|--------|----------------|
| tmsv | source | r | [-3, 3] / 0.01 |
| coherent | source | alpha | [-5, 5] / 0.05（实数；数字框可输复数文本 `[re,im]`） |
| squeeze | single | r, phi | r: [-3,3]; phi: [0, 2π] / 0.01 |
| phase | single | phi | [0, 2π] / 0.01 |
| displace | single | alpha | 同 coherent |
| loss | single | T | (0, 1] / 0.01（nbar 默认 0，数字框可选填） |
| beamsplitter | two | theta, phi | [0, 2π] / 0.01 |
| heterodyne | single | （无参数） | — |

**mode 分配**: 添加节点时默认 mode = 首个源之后的最小未用模式号（源: 0 起）; 参数面板数字框可改（越界由后端 422 兜底 + UI 即时提示）。

## 3. 编辑器状态机（editor.js）

```
state = { nodes: [{id, op, params, mode|modes}], view, ui }
```

- **托盘 → 序列**: HTML5 DnD（draggable 卡片 → drop 到列表尾部追加）+ 兜底点击"+"按钮（Edge DnD 失效路径）
- **序列行**: 序号 · op 中文标签 · 参数摘要 chip · mode 徽标 · ↑/↓/🗑（文本按钮，无 emoji）
- **参数面板**: 点行展开（行内滑杆 + 数字框双态）；拖动 input[type=range] → 120ms 防抖 → 自动 run + 请求序号守卫（丢弃过期响应）
- **JSON 双向同步**:
  - 图形 → JSON: 每次 state 变更 `JSON.stringify(state, null, 2)` 写 textarea
  - JSON → 图形: textarea input 事件防抖 400ms → `parse` 成功 = 重建图形（校验：必须合法 circuit 结构）; 失败 = 红条提示 + 图形冻结在最近合法态（不闪回、不清空）
  - 避免循环: 图形→JSON 写 textarea 时挂 `suppress` 标志
- **热图模式选择**: view.wigner_mode 由"结果区" mode 下拉更新（wigner_mode 下拉 = 0..nmode-1）
- **重置示例**: 恢复 L1 DEFAULT_JSON → 图形 + JSON 同步重建

## 4. 布局（Workbench 三区）

```
header.lite（不变，badge 加 "editor"）
main.workbench
  左 托盘 panel（8 op 卡片，draggable）      ← 320px 内
  中 序列 panel（节点行列表 + 参数面板内嵌）
  右 结果 panel（L1 原样: 热图/meters/矩阵 + wigner_mode 下拉）
footer.statusbar（不变）
```
≥1100px 三列; 768–1100 托盘上浮为横向滚动条; <768 堆叠（托盘折叠为水平条）。

## 5. 防抖与竞态（关键）

- 滑块拖动: 120ms debounce；每次请求带递增 seq；响应回来 seq !== 最新 → 丢弃（不渲染不写状态）
- 手动 Run 按钮保留（编辑器模式 JSON 面板共享）
- Latency >500ms 显示"运行中…"（vision 4.6）—— 64 网格本地 <50ms，防御性兜底

## 6. 测试

- `tests/test_lab_editor.py`（或 node 侧）:
  - ops.js: 8 op 元数据完整性（params 定义 vs ir.py 白名单子集一致）—— 静态断言
  - editor state→JSON 纯函数: 构造主剧本电路 → JSON 结构与 /run 兼容（POST 200）
  - 防抖: 单测 debounce 函数（fake timers 不需要 —— 断言 seq 守卫函数行为）
- node 单测脚本: `tests/editor.test.mjs`（node --test，无框架），验证 editor.js 可剥离的纯函数（addNode/removeNode/moveNode/toCircuitJson）
- 主剧本 1–6: 手工验收（用户）
- 全套 pytest + ruff + 离线守卫回归

## 7. 不做

- 画布/连线/拖拽排序（D1/D9）; modes_A 选择器（D5）; undo（P1）; Save/Load/Measure（L3）
- 白名单其余 4 op（vacuum/fourier/two_mode_squeeze/homodyne）defer
