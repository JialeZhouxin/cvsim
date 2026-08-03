# PRD — Gaussian Lab L1: read-only result page + param editing

> 来源: [`docs/vision-gaussian-lab-ui.md`](../../docs/vision-gaussian-lab-ui.md) §5/§6/§7/§8/§11/§12
> 状态: **planning**（2026-08-03）
> 上游: L0 已落地（`cvsim.lab` IR + `/run`，commit `e96be7f` + OCR fix `aef9ab7`）
> UI 视觉规范: **Hallmark skill**（用户指定）—— 实现阶段遵循其 Design flow

## 1. 背景

L0 交付了 `circuit_v0` IR + `POST /run`。L1 是 Lab 第一个前端切片：**结果只读页 + 参数 JSON 编辑**，无拖拽（L2 才有）。退出标准：主剧本无 BS 版可看热图（vision §11）。

## 2. 目标

| Feature ID | Deliverable | Exit |
|-----------|-------------|------|
| **F-LAB-UI** | 单页结果页：JSON 编辑 → 运行 → Wigner 热图 + meters + **rbar/V 矩阵** | 主剧本无 BS 版可看热图：改 `r` 热图变胖、meters 刷新（vision §5 step 3 雏形） |
| **F-LAB-STATIC** | FastAPI 挂载静态页 + 启动入口 | 浏览器冷启动 < 30s 到可编辑页（A1 雏形） |

## 3. 范围

**做**:
- 单个静态页（`cvsim/lab/static/index.html` + 内嵌 CSS/JS，或分文件），FastAPI `StaticFiles` 挂载
- 默认加载示例电路 JSON（主剧本无 BS 版：TMSV r=0.6 + 双 loss T=0.8）
- 左侧 JSON 编辑（textarea）→ 运行按钮 → `POST /run` → 右侧 canvas Wigner 热图 + meters（purity / mean_photon / log_negativity）+ **rbar 均值与 V 协方差矩阵**（用户 use case 明确要求：调参时看态摘要）+ nmode 显示
- 422 错误展示（detail 文本，UI 友好）
- `view` 参数编辑（wigner_mode / lim / n）随 JSON 提交
- 启动入口：`python -m cvsim.lab` 或 uvicorn 命令文档化
- 测试：静态页可达（GET / → 200 + 含关键元素）、/run 端到端已有

**不做**（L2/L3）:
- 拖拽编辑器、节点图（L2）
- Save/Load、Measure once、seed 抽样（L3）
- 扫参、undo、非白名单 op
- 构建工具链、npm 依赖、框架（hallmark 允许"极简自研"）
- 外部字体 CDN（本地离线工作台，用系统字体栈）

## 4. 技术方案（骨架，UI 视觉归 Hallmark）

```
cvsim/lab/
  static/
    index.html     # 页面结构（左右分栏：JSON 编辑 | Wigner + meters）
    app.js         # 内嵌或独立 JS：编辑→防抖/按钮→POST /run→canvas 热图
    style.css      # Hallmark tokens.css 引用 + 页面样式
  server.py        # + StaticFiles 挂载（L0 已有 app 上追加）
  __main__.py      # python -m cvsim.lab 启动入口（uvicorn）
```

- 热图：canvas 2D，逐格 fillRect（n×n，默认 64×64 = 4096 格，无压力）；colormap 内嵌 LUT（inferno/viridis 风格 32 色）；axis 刻度简绘
- 状态流：JSON 校验前端只做语法检查（JSON.parse），物理校验交给后端 422
- 防抖：L1 手动按钮触发即可（vision debounce 100-150ms 是 L2 拖拽要求）
- 响应式：桌面宽度优先（vision 明确无手机布局需求），但 hallmark 要求 320-768px 不破版 → 保留基本折叠

## 5. Hallmark 流程约定（本任务 UI 部分）

- **Pre-flight 已完成**: 无 design.md / 无 tokens.css / 无 package.json / 无前端代码（纯 vanilla 项目）；无 `.hallmark/log.json`（本项目首个 Hallmark run）
- **设计约束**（技能硬规则，实现时逐条执行）:
  - **Design-context gate 已答（2026-08-03）**: Audience=作者本人（研究/调参）· Use case=改参数→Wigner 热图响应 + rbar/V 矩阵 + meters · Tone=**technical（技术仪器感）**
  - 从 21 个 macrostructure 选一（工作台类优先，如 05-workbench）+ 声明
  - Genre 判定（默认 editorial）；theme 从 catalog 选（20 个命名主题）或 custom
  - 所有颜色/字体走 tokens（`tokens.css` 输出到项目根或 lab/static/），禁内联值
  - 58 项 slop test 全过；preview block 输出；macrostructure stamp；`.hallmark/log.json` 记录
  - 8-state 交互（按钮/输入框全状态）
  - 排版禁斜体标题、禁 AI 味要素（fake chrome、编号 eyebrow 等）
- **离线约束**（本项目特殊）: 无 Google Fonts CDN → 字体用系统栈或随仓库携带的本地字体；catalog 主题的免费字体若无本地可用，需在实现时替换为等效系统栈并在 stamp 中注明

## 6. 验收（L1 Done 判定）

1. **主剧本无 BS 版**: 浏览器打开页 → 默认 TMSV+loss 电路 → 看到 Wigner 热图 + meters；改 JSON 中 `r: 0.6 → 2.0` → 运行 → 热图变胖（数值与 `/run` 直调一致）
2. **A1 雏形**: 冷启动（uvicorn 起）→ 浏览器可编辑 < 30s
3. 422 错误（如非法 T）在页面显示后端 detail，不白屏
4. 测试: `GET /` 返回 200 + 页面含关键元素 id（`json-input` / `run-btn` / `wigner-canvas` / `meters-panel`）；现有 404 测试全绿
5. Hallmark: preview block 已出、slop test 58/58、tokens.css 已产出、log.json 已记录

## 7. 依赖

无新增 Python 依赖（StaticFiles 是 fastapi 自带）。前端零 npm 依赖。

## 8. 里程碑

1. F-LAB-STATIC: server.py 挂载 + `__main__.py` + 页面可达测试 → verify: pytest 绿
2. F-LAB-UI: index.html + app.js + canvas 热图 + meters 接线（先裸功能后 hallmark 视觉）→ verify: 浏览器手工主剧本
3. Hallmark 视觉 pass: 三问 → genre/macrostructure/theme → tokens.css → slop test → verify: preview block + 58/58
4. 收尾: vision changelog 更新、任务 archive
