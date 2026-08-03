# Implement — Gaussian Lab L1

> 上游: `design.md`。每步验证后进下一步。

## 步骤

### S1: 后端挂载 + 启动入口
- `server.py`: `StaticFiles` mount（API 路由之后）
- `__main__.py`: uvicorn 入口
- `tests/test_lab_ui.py`: GET / 200 + 关键元素 + 离线守卫
- verify: `uv run pytest tests/test_lab_ui.py -q` 绿 + 全套不回归

### S2: 静态页（功能先，视觉后）
- `static/index.html` + `app.js`（JSON 编辑 → /run → canvas 热图 + meters + rbar/V）
- 浏览器手工验证: 默认示例可见热图；改 r 0.6→2.0 热图变胖；非法 T → 错误条
- verify: 手工主剧本无 BS 版

### S3: Hallmark 视觉 pass
- `tokens.css`（Cobalt 令牌）→ `style.css`（token-only 引用）
- 8-state（按钮/textarea）、focus ring、tabular-nums、响应式 320/375/414/768
- slop test 58 门自查 → preview block 更新 → `.hallmark/log.json` 记录
- verify: 浏览器四宽度无横滚无折行

### S4: 收尾
- `uv run pytest -q` 全套 + `uv run ruff check cvsim/lab tests/`
- vision changelog 0.3.0 条目
- commit + task archive

## 不做清单

- ❌ 拖拽编辑器（L2）、Save/Load、Measure once（L3）
- ❌ npm/构建链/外部字体 CDN
- ❌ 扫参、undo、非白名单 op、热图插值平滑（像素即物理）
