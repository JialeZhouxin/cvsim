# Gaussian Lab L4 — Implement

## 顺序（每步验证）

### 1. Amend vision §4 白名单 + changelog（前置规则 §13.2）
- [ ] `docs/vision-gaussian-lab-ui.md` §4 白名单表加 `amplifier`（G 主参、nbar advanced）、`mz`（theta/phi）
- [ ] §10 L4 行更新为"E_N(r) 扫参 + amp/MZ（undo 独立）"；§12 F-LAB-SCAN 标注 landed
- [ ] changelog 草案（0.6.0，commit 时定稿）
- 验证：grep §4 表含新 op

### 2. 后端：ir.py amp/mz + scan_circuit + server.py /scan
- [ ] `SINGLE_MODE_OPS` 加 `"amplifier"`；`_apply` 分支（调 `cvsim.gaussian.channels.amplifier`；G<1/nbar<0 → CircuitV0Error）
- [ ] `TWO_MODE_OPS` 加 `"mz"`；`_apply` 分支（BS→phase→BS 组合，theta/phi 校验）
- [ ] `scan_circuit(circuit, sweep)`：校验（node/param/range/n/modes_A/测量节点拒绝）→ linspace → 逐点 run → ys（singular → null）
- [ ] `server.py` `POST /scan`：validate → `scan_circuit` → 响应；异常 → 422 `{detail}`
- 验证：`uv run pytest tests/test_lab_l4.py`（先写测试：mz≡bs+phase+bs、amp 单点对照、scan 解析 TMSV E_N=2r/ln2、422 矩阵）

### 3. 前端：ops.js 元数据 + 扫参面板 + SVG 曲线
- [ ] ops.js：`amplifier`/`mz` 卡片 + 现有 op 补 `sweep` 元数据（tmsv.r、squeeze.r、loss.T、bs.theta、phase.phi、two_mode_squeeze.r…）；alpha 无 sweep
- [ ] index.html：扫参面板骨架（select×2 + min/max/n + modes_A + Scan + svg 容器）
- [ ] app.js：`doScan`（fetch /scan → 渲染曲线）；node/param 级联选择；modes_A 选项随 nmode；busy/status 处理
- [ ] style.css：面板 + 曲线 token 配色（沿用现有设计）
- 验证：`node --check` 三个 js；`node --test tests/editor.test.mjs`；`uv run pytest tests/test_lab_ui.py`（如加 sentinel）

### 4. 测试补全 + 全量回归
- [ ] `tests/test_lab_l4.py`（scan 端点 TestClient + ir 层单测 + mz/amp 等值）
- [ ] `uv run pytest`（430+ 全绿）；`node --test`；ruff lab 干净
- 验证：suite 计数记录

### 5. headless CDP 验收
- [ ] 探针：TMSV 电路 → 扫参面板选 r → Scan → 曲线点与解析 2r/ln2 对照（读 svg 数据/请求响应）
- [ ] 探针：amp/MZ 拖拽 → /run ok → meters 合理（amp G=1 不变量：E_N 不变）
- 验证：探针输出 PASS 记录

### 6. trellis-check + OCR + commit
- [ ] `trellis-check` 子代理验证（spec 合规 + 全量回归）
- [ ] OCR review 每 commit（mandatory, Phase 3.4）→ 修 high/medium
- [ ] 归档 `08-04-cvsim-lab-l4`

## 风险点 / 回滚

- MZ 组合顺序（BS→phase(m0)→BS）— 等值测试兜底
- ops.js sweep 元数据遗漏现有 op — 前端参数 select 空 → 面板提示"无可扫参数"
- 测量节点在扫描电路 → 422 拒绝（诚实，不伪造 E_N）
- 回滚：commit 可 revert；vision amend 同 commit

## 验收映射

| AC | 验证 |
|----|------|
| A7 | pytest /scan 解析对照 + CDP 曲线 |
| A8 | pytest amp 单点 + CDP 拖拽 |
| A9 | pytest mz 等值 + CDP 拖拽 |
| A10 | CDP 面板渲染 + modes_A |
| A11 | 全量回归 + vision amend |
