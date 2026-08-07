# Implement — circuit_v1 核心 IR 收编

依赖序：核心 → lab 后端 → 前端 → 文档。每步独立提交 + OCR review（Phase 3.4 mandatory）。

## 1. 核心 `cvsim/gaussian/ir.py` + `circuit.py` → commit 1

- [ ] `cvsim/gaussian/ir.py` 新建：SCHEMA、OP_META（arity/defaults/value_kind/string_params）、IRNode/CircuitV1、`validate_ir`（结构 only）、`to_ir/from_ir`、值编解码（complex→[re,im]、array→nested list、$param/$ref、裸 str=fixed name）。
- [ ] `circuit.py`：`squeeze` 补 `phi=0.0`；`to_ir()` / `from_ir()`；mz → 三步展开（from_ir 侧）。
- [ ] `tests/test_ir.py`：14 op 往返 V,rbar atol=1e-12（含符号参数、ParamRef、复数 alpha、矩阵 U/X/Y/d）；校验拒绝矩阵；扩展字段忽略；mz 展开语义等价。
- verify: `pytest tests/test_ir.py tests/test_gaussian_circuit.py tests/test_compile.py`
- [ ] OCR review → 修 high/medium → commit `feat(ir): circuit_v1 核心 IR + to_ir/from_ir`

## 2. Lab 后端 `cvsim/lab/ir.py` + `server.py` → commit 2

- [ ] `translate_v0(data) -> dict`（源→块局部门 + nmode 求和；mode→modes；view/seed/ui 提取；edges 丢弃）。
- [ ] `load_circuit` 按 schema 分派（v0 翻译 / v1 直读）→ `LabCircuit(core, seed, view, ui)`。
- [ ] 引擎改遍历 `CircuitV1.ops`：逻辑→物理静态映射（仿 compile.py）；homodyne mean 路径改**删模**；测后引用已删模 → CircuitV0Error。
- [ ] `LAB_WHITELIST`（11 op）在 lab load 层追加拒绝；`SWEEPABLE_PARAMS` 保留。
- [ ] `server.py` 适配 LabCircuit（预期零/微改）。
- [ ] `tests/test_ir_translate.py` 新：v0 主剧本/多源/coherent/homodyne-末尾 golden（log_neg=2r/ln2 等）；语义统一用例（heterodyne 后高模、homodyne 删模）。
- [ ] 存量 lab 测试机械更新接口形状（Node→CircuitV1），语义用例保持绿。
- verify: `pytest tests` 全绿
- [ ] OCR review → 修 → commit `refactor(lab): v1 引擎 + v0 翻译层`

## 3. 前端 emit v1 → commit 3

- [ ] `ops.js`：`toV1(nodes, view, seed)`（源→门镜像翻译）；所有 POST body 走 toV1。
- [ ] `app.js`：Save 文件名 `circuit_v1.json`；`schema` 常量更新；Load 兼容 v0/v1。
- [ ] node 测试更新：toV1 结构、save 文件名、旧 v0 文件 load 路径。
- verify: `pytest tests` + node 测试全绿；`py -3 -m cvsim.lab` 冒烟（旧 v0 文件 load → run）
- [ ] OCR review → 修 → commit `feat(lab-ui): 电路文件迁 circuit_v1 (save/load/run)`

## 4. 文档 → commit 4

- [ ] `docs/api-stability.md`：`to_ir/from_ir` + `circuit_v1` 入稳定 API 表。
- [ ] 如实现暴露 PRD/design 未覆盖缺口 → 先 amend design/vision 再继续。

## 5. 收口

- [ ] trellis-check 子代理质量检查；全量 pytest + node 全绿。
- [ ] 每 commit OCR high/medium 清零（含 lab 前端文件）。
- [ ] `task.py archive` + 会话记录。
