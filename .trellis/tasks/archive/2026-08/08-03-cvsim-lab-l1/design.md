# Design — Gaussian Lab L1: workbench result page

> 上游: `prd.md`；UI 规范: Hallmark（genre=modern-minimal · theme=Cobalt · macrostructure=05-Workbench）

## 1. 文件结构

```
cvsim/lab/
  static/
    index.html      # 页面结构（语义标签、零外部资源）
    tokens.css      # Hallmark 令牌（颜色/字体/间距/动效）；页面引用
    style.css       # 页面样式（只引用 token 变量，禁内联色值）
    app.js          # 状态流：JSON 编辑 → POST /run → 热图/meters/矩阵
  server.py         # + StaticFiles 挂载（"/" → static）
  __main__.py       # python -m cvsim.lab → uvicorn
tests/
  test_lab_ui.py    # GET / 200 + 关键元素 + 离线守卫（无外部 URL）
```

## 2. Hallmark 选型记录（stamp）

```
/* Hallmark · genre: modern-minimal · macrostructure: Workbench · theme: Cobalt
 * enrichment: none · nav: N1a minimal · footer: Ft2 inline
 * offline-substitution: Space Grotesk → Bahnschrift; JetBrains Mono → Cascadia Code
 * (CDN unavailable — local workbench; system font stacks only) */
```

- **Palette**（Cobalt cool-white，全 OKLCH，冷调中性 tint 250°）:
  - `--color-paper: oklch(98% 0.004 250)` · `--color-paper-2: oklch(95.5% 0.006 250)` · `--color-rule: oklch(88% 0.01 250)`
  - `--color-neutral: oklch(55% 0.01 250)` · `--color-muted: oklch(42% 0.012 250)` · `--color-ink: oklch(20% 0.015 255)`
  - `--color-accent: oklch(55% 0.19 260)`（electric cobalt，用量 ≤3%）· `--color-focus: oklch(55% 0.19 260)`
  - `--color-error: oklch(55% 0.2 25)` · `--color-success: oklch(58% 0.15 155)`
- **Fonts**（2+1 规则）: `--font-display: "Bahnschrift", "Segoe UI Variable Display", system-ui` · `--font-body: "Segoe UI Variable", "Segoe UI", system-ui` · `--font-mono: "Cascadia Code", "Consolas", monospace`
- **Scale**: 1.25 major third（--text-xs 0.64rem → --text-lg 1.5625rem，页面 ≤5 档）· tabular-nums 用于 meters/矩阵
- **Spacing**: 4pt 语义刻度 --space-xs/sm/md/lg/xl/2xl/3xl
- **Motion**: --ease-out/in/in-out + --dur- 短时；只动 transform/opacity；reduced-motion 折叠；focus ring 即时

## 3. 页面布局（Workbench 骨架）

```
header.lite ── wordmark "Gaussian Lab" · badge circuit_v0 · cvsim 版本（mono）
main.workbench（grid: 左 1fr · 右 1.2fr，≥960px 两栏；<960px 堆叠）
  section.editor
    textarea#json-input（mono，默认示例 JSON：TMSV r=0.6 + 双 loss T=0.8）
    .editor__actions ── button#run-btn（Run）· button#reset-btn（Reset sample）
    .editor__hint（view 字段说明：wigner_mode/lim/n 随 JSON 提交）
  section.result
    .wigner ── canvas#wigner-canvas + 轴标签（x/p）+ 色阶条（inferno LUT）
    .meters ── purity · mean_photon · log_negativity（tabular-nums）
    .state-summary ── nmode + rbar 表（mono grid）
    .covariance ── V 矩阵表（mono grid，xxpp 标注）
footer.statusbar ── 错误（--color-error）或 "ok · <ms>" · 右侧 Ft2 行
```

## 4. 前端状态流（app.js，零依赖 vanilla）

- `run()`: JSON.parse（语法错 → 就地错误条，不请求）→ `POST /run` → 成功：canvas 重绘 + meters/矩阵更新；422/网络错 → statusbar 显示 detail
- Canvas 热图: 逐格 `fillRect`（n×n，默认 64² = 4096 格）；inferno 风格 LUT 内嵌 32 色数组（数据可视化，独立于主题色，属物理约定非装饰）；`image-rendering: pixelated` 观感；坐标轴边缘标注 ±lim
- meters/矩阵: 纯文本渲染（`textContent`，无 XSS 面）；V 显示 xxpp 分区提示
- 运行中状态: button disabled + `aria-busy`；不显示闪 spinner（本地 <200ms）
- 防抖: L1 手动按钮，不做拖拽防抖（L2 需求）
- 移动端: <960px 堆叠单列；320/375/414/768 无横滚（html/body `overflow-x: clip`）；按钮 nowrap

## 5. 后端增量

- `server.py`: `app.mount("/", StaticFiles(directory=..., html=True), name="static")` —— 注意挂载顺序：API 路由先声明，mount 在最后
- `__main__.py`: `uvicorn.run("cvsim.lab.server:app", host="127.0.0.1", port=8000)` + `python -m cvsim.lab` 启动
- API 不变（L0 的 /run /health 原样）

## 6. 测试（test_lab_ui.py）

- `GET /` → 200 + `text/html`
- 页面含关键元素 id: `json-input` / `run-btn` / `wigner-canvas` / `meters-panel`
- **离线守卫**: index.html/tokens.css/style.css/app.js 不含 `http://` / `https://` 外部引用（本地工作台硬约束）
- 默认 JSON 可运行: 页面内嵌示例 → `POST /run` 200（复用 L0 断言）
- 全套 pytest + ruff 绿

## 7. 关键决策

| # | 决策 | 理由 |
|---|------|------|
| D1 | 零 npm/零 CDN，单页三文件 | 本地离线工作台；vision §6.1 允许极简自研 |
| D2 | inferno LUT 独立于主题 | Wigner 是物理数据约定，非装饰；主题色管 UI chrome |
| D3 | 手动 Run（无防抖） | L1 编辑粒度粗；防抖是 L2 拖拽要求 |
| D4 | Bahnschrift/Cascadia Code 替代 Cobalt 字体 | CDN 不可用；系统栈保证离线可渲染，stamp 记录 |
| D5 | API 路由先于 mount | FastAPI mount 会吞前缀路由；顺序敏感 |
