# 主剧本复验记录（vision-gaussian-lab-ui §5）

日期：2026-08-06 · 方法：`uv run python -m cvsim.lab` 起服务 + API 级脚本 + CDP headless probe

## 结果

| 剧本 | 内容 | 结果 |
|------|------|------|
| 1–2 | 纠缠源（TMSV 语义 = vacuum×2 + two_mode_squeeze(r=0.6)）+ 两臂 loss(T=1) | E_N = 1.7312 = freeze -log₂(e^{-2·0.6}) ✓ |
| 3 | r 增大 0.6→1.2 | E_N = 3.4625 = -log₂(e^{-2·1.2}) ✓（Wigner 变胖由后端 W 网格间接验证） |
| 4 | 两模间 BS | θ=π/4 时 E_N=0 —— **正确物理**（TMSV 的 EPR 压缩被 50:50 BS 对角化为两个独立单模压缩真空，独立计算验证 purity=1 且 θ=0.2/0.9 保留纠缠 E_N=1.6336/0.4856）；θ=0.2 时 E_N=1.6336 与独立计算一致 ✓ |
| 5 | loss T=0.5 | E_N = 0.8874 < 1.6336 ✓（混态纠缠下降） |
| 6 | heterodyne on mode 0 | nmode 2→1 删模 ✓ |
| 7 | Measure once | seed 7 返回，heterodyne outcome 合理 ✓ |
| 8 | Save/Load | stateFromJson/loadJson round-trip 测试覆盖（含 fourier 新用例）✓ |

## 附带发现（本次任务修复）

- **fourier 门缺口**：前端 `ops.js` 无 fourier 定义（白名单 ✅ 列与后端 ir.py 早已支持）→ 补回托盘，旧 JSON 也可载入
- **BS(π/4) 消纠缠**：非 bug，物理正确；复验预期据此修正

## 回归

- `node --test tests/editor.test.mjs` 34/34
- `node tests/lab_staff_probe.mjs` 25/25（fourier 补入后断言更新 11→12 items）
- `node tests/lab_scan_probe.mjs` 全 PASS
- `node tests/lab_undo_probe.mjs` 11/11（新增）
- pytest 472 passed
