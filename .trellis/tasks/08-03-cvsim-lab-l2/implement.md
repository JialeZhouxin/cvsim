# Implement — Gaussian Lab L2

> 上游: `design.md`。每步验证后进下一步。

## 步骤

### S1: 纯逻辑层（可测）
- `ops.js`: 8 op 元数据（params 定义、滑块范围、mode 类别）
- `editor.js` 剥离纯函数: `addNode` / `removeNode` / `moveNode` / `paramsFromOp` / `toCircuitJson`（state → circuit_v0 payload）
- `tests/editor.test.mjs`（node --test，零依赖）
- verify: `node --test tests/editor.test.mjs` 绿

### S2: UI 装配
- `index.html` 三区布局 + `style.css` 扩展
- `editor.js` DOM 层: 托盘 DnD + 点击兜底; 序列行; 参数面板（滑块+数字）; 上移/下移/删除
- JSON 双向同步（suppress 标志 + 合法态缓存 + 400ms 重建防抖）
- `app.js` 改造: run 流程接 editor state; seq 守卫; wigner_mode 下拉
- verify: headless Edge dump-dom（无 console error; 默认场景渲染; 改 r → /run 触发）

### S3: 视觉 pass
- 延续 Hallmark: 托盘卡片 hover/focus; 节点行 8-state; 滑杆样式（accent 色）
- 响应式 320/375/414/768; 离线守卫测试维持
- verify: headless 截图四宽度无横滚; slop 自查

### S4: 收尾
- A3 验证: T=1 r=0.6 → log_neg ≈ -log2(e^-1.2) = 1.731（测试 + 前端显示）
- 全套 pytest + ruff + node --test; vision changelog 0.4.0
- commit + 用户主剧本 1–6 手工验收 → archive

## 不做清单

- ❌ 画布/连线/拖拽排序/undo/modes_A 选择器/Save/Load/Measure once
- ❌ 白名单其余 op（vacuum/fourier/two_mode_squeeze/homodyne）
- ❌ 非白名单 op（MZ/CZ/interferometer/amp/phase_noise）
