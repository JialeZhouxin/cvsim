# Implement — Fock Lab GUI（同壳双后端）

> 执行清单。每步含验证命令。教义：先改 vision 文档，再改代码（Lab vision §13 agent rules）。

## 步骤

### S0 文档先行（vision 同步）

- [ ] `docs/vision-fock-simulator.md`：§10 Q9 状态更新（已评估 → GUI 解锁）；roadmap 加 **F7 — GUI**；FOCK_PUBLIC 冻结表 + `FockCircuit.initial` + IR `initial` 字段；document control + 0.6.0 条目
- [ ] `docs/vision-gaussian-lab-ui.md`：§2.2 砍项表「Fock/Bosonic UI」条款 amend（Fock 解锁、Bosonic 仍砍）；新增 Fock 白名单表（§4.x，R2 清单 + defer 矩阵编辑器）；changelog 条目
- 验证：`git diff docs/` 人工复核

### S1 FockCircuit 初始态 API（cvsim/fock/）

- [ ] `cvsim/fock/circuit.py`：`__init__(nmode, cutoff=10, initial=None)` + 校验（len=nmode、`0<=n_i<cutoffs[i]`）；`CompiledFock` 带 `initial`；`_init_state` 改 Kronecker 积
- [ ] `cvsim/fock/ir.py`：`validate_ir` 接受 `"initial"`；`EXTENSION_FIELDS = {"view","seed","ui","backend"}`（修 view/seed/ui 被拒 bug）；`to_ir`/`from_ir` 读写 initial
- 验证：`py -3 -m pytest tests -x -q`（全量回归，重点 fock）；新增测试见 S2

### S2 测试：初始态 + IR

- [ ] `tests/test_fock_initial.py`：initial=[1,1] 运行态 ≡ `FockState` fock2 直构（atol 1e-12）；真空缺省等价；per-mode cutoff 下校验（n≥cutoff → ValueError）；to_ir/from_ir roundtrip 含 initial；旧 IR 无 initial 字段 → 真空
- 验证：`py -3 -m pytest tests/test_fock_initial.py -q`

### S3 lab 后端拆层（cvsim/lab/）

- [ ] `cvsim/lab/ir.py`：`FOCK_WHITELIST`；`EXTENSION_FIELDS` + `backend`/`initial`；`load_circuit` 按 `backend` 分流（fock 走 `cvsim.fock.ir.validate_ir` + 白名单）；fock `run`/`sample` 路径（`FockCircuit.from_ir` → run）；payload 构造（dist/joint/wigner/meters/outcomes，见 design §2.3）
- [ ] `cvsim/lab/server.py`：`/run` `/sample` 路由 backend；`POST /batch`（shots 校验 1..100000；`pnr_sample_batch` / condition 链 batch）；`/scan`+fock → 422
- 验证：`py -3 -m pytest tests -q`

### S4 测试：lab Fock 后端

- [ ] `tests/test_lab_fock.py`：
  - golden fixture：HOM JSON（nmode=2, initial=[1,1], BS θ=π/4）→ `/run` joint grid P(1,1)≈0、单模边缘 P(1)=0，与等价脚本 `FockCircuit` 一致（atol 1e-12）
  - `/sample` seed 复现（同 seed 同 outcomes）
  - `/batch` 1000 shots counts 与 `pnrd_probs` 统计一致（tol 5σ 或宽松相对误差）
  - backend 缺省 gaussian：旧 JSON 回归不变
  - 422 路径：坏 initial、超白名单 op、坏 cutoff
  - 泄漏仪表：纯态 truncation_leakage 正确；密度态诚实 null
- 验证：`py -3 -m pytest tests/test_lab_fock.py -q`

### S5 前端

- [ ] `ops.js`：OPS 每项 `backends` 元数据 + Fock-only 项（kerr/cz/cx/measure_pnr）+ 参数浮层元数据分表；托盘按 backend 过滤
- [ ] `editor.js`：state.backend/initial/cutoffs + JSON 双向同步；backend 切换器 UI；加模按钮（Fock 无源托盘）
- [ ] `static/fock.js`（新）：分布柱状图卡 + joint 2D heatmap + 采样对照（Measure once/Batch 双色叠画）+ 截断护栏卡（滑块/per-mode/泄漏仪表/慢速提示）+ outcomes 卡
- [ ] `app.js`：Fock 面板装配 + payload 消费分支；`index.html`/`style.css`/`tokens.css`：面板骨架 + 样式（只加必要）
- 验证：`node --test tests/` 全绿；手工浏览器冒烟

### S6 前端测试

- [ ] `tests/editor.test.mjs` 扩展：OPS per-backend 过滤、toCircuitJson/stateFromJson 含 backend/initial/cutoffs、Fock 托盘集正确（无 interferometer/apply_unitary）
- [ ] 纯逻辑单测：直方图/heatmap 网格构建、双色叠画数据
- 验证：`node --test tests/editor.test.mjs`

### S7 验收 + 收口

- [ ] 主剧本 A1 + 次剧本 A2 + 测量剧本 A3 手工/headless 全过
- [ ] 全量：`py -3 -m pytest tests -q` + `node --test tests/` 全绿
- [ ] trellis-check（子代理）→ 修 findings
- [ ] OCR review 任务内全部 commit → 修 high/medium
- [ ] Phase 3.4 batched commit → `/trellis:finish-work`

## 回滚点

| 步骤 | 回滚 |
|------|------|
| S3 后 | git revert 后端 commit，前端未动 |
| S5 后 | 前端 revert；后端 API 独立可用 |
| 任何步测试红 | 该步内修；修不动 → 回上一步 |
