# Lab Gaussian 执行路径统一——删 _apply 13 分支 dispatch

## Goal

消除 `cvsim/lab/ir.py` 中 Gaussian 路径与 `GaussianCircuit` 的重复 op dispatch。Lab 的 `_apply()` 手搓 13 个非测量 op 的 `if op==` 分支，把 `gaussian/circuit.py` + `compile.py` 已有的派发在 Lab 里重写一遍。Fock/Bosonic 路径已走 `XxxCircuit.from_ir().run()`，Gaussian 是异类。

统一后 Lab 只调度：非测量 op 交 `GaussianCircuit.from_ir().compile()` 的合并段，测量 op 走 Lab 自家 mean/sample path（保留 entry 元信息）。

## Background

架构评审（2026-08-25）候选①+③合并。Grilling 六问全锁定：
- Q1=A 保留 Lab mean path（`/run` 确定性期望），非测量 op 交编译合并段
- Q2=A 测量 op（homodyne/heterodyne）留 Lab 自家路径 + entry 元信息
- Q3=A1 Lab 遍历 `compiled._segments`，merged 调 `_apply_merged`，测量走自家（接受访问 `_segments`）
- Q4=A scan 路径也统一 `GaussianCircuit`，用 symbolic param `$param`，删 `_state_after`
- Q5=A `_meters`/`_build_result` 留 Lab，不动结果组装胶水
- Q6=C Gaussian Lab 不支持 threshold，保持现状报错

## Requirements

### R1 删除 Lab `_apply` 的非测量 op dispatch
- 删 `_apply()` 中 11 个非测量分支：squeeze/displace/phase/fourier/bs/tms/cz/cx/mz/interferometer/loss/amp/phase_noise/gaussian_channel
- 保留 homodyne/heterodyne 2 个测量分支（mean path + entry 生成）
- 新增 threshold 拒绝分支（保持 Q6=C 现状不支持）

### R2 `_execute` 改用 `GaussianCircuit.from_ir().compile()`
- Lab `_execute` 遍历 `compiled._segments`：merged 段调 `compiled._apply_merged(ops, nmode, values, st)`；断点 op 段（测量）走 Lab 自家测量路径
- 删 `_logical_phys`、`_remove_phys`（重排已由 `compile_segments` 完成；Lab 仅从 IR node 读逻辑模号填 entry）
- mean path（`/run`）：测量用 `homodyne_mean` + `homodyne_condition`（确定性，不抽 RNG）
- sample path（`/sample`）：测量用 `homodyne_sample_and_condition(rng=rng)`

### R3 `scan_circuit` 统一到 symbolic param
- 删 `_state_after`（被 `compiled.run(**{param: x})` 替代）
- sweep param 用 `GaussianCircuit` 的 symbolic param 机制：被 sweep 的 node param 改成 `$param`，`from_ir` + `compile` 一次，每 sweep 点 `run(**{param: x})`
- 保持 `/scan` 契约不变（scan-api.md）：纯函数、无 RNG、同请求同响应、ys null when singular

### R4 不动范围
- `_meters` / `_build_result` / `translate_v0` / schema / `View` / `LabCircuit` 不动
- Fock 路径（`run_fock_circuit` + `_fock_*` helpers）不动
- Bosonic 路径（`run_bosonic_circuit` + `_bosonic_*` helpers）不动
- `circuit_common.py` / `gaussian/compile.py` / `gaussian/circuit.py` 不动
- `measured` entry 结构不变（op/mode/phi/outcome），前端 + 测试契约保

## Acceptance Criteria

- [ ] 全量 pytest 绿（基线 1147 passed / 4 skipped / 6 warnings）
- [ ] `tests/test_lab_ir.py` 测量 entry 结构断言不破（op/mode/phi/outcome 字段）
- [ ] `tests/test_lab_l3.py` 测量断言不破（measured[0].op/mode/phi/outcome 类型）
- [ ] `/run` mean path 仍确定性（同电路同结果）
- [ ] `/sample` 仍抽样（rng 驱动）
- [ ] `scan_circuit` sweep 输出数值不变（symbolic param 绑定值 = 原替换值）
- [ ] `tests/test_ir_translate.py` 不破
- [ ] `lab/ir.py` 体积下降（删 ~80 行 13 分支 + 3 个 helper）

## Constraints

- ADR-0001 导入边界：lab 可 import `cvsim.gaussian`（lab 是顶层，非 rep 包）
- ADR-0003 circuit_v1 IR：schema 不动
- `/scan` API 契约（scan-api.md）：请求/响应格式不变
- `measured` entry 是 Lab 公开契约（前端 app.js L463-470 + 6 测试断言），字段不动
- Lab 访问 `CompiledGaussian._segments`（私有属性）—— Q3=A1 已确认接受

## Notes

- Lab mean path 是教学需求（展示期望值），不被采样覆盖（Q1=A）
- threshold 在 Gaussian Lab 无场景，Bosonic（GKP QEC）才需要（Q6=C）
- scan 用 symbolic param 后每点不重编译，性能更好（ADR-0002 结构编译一次、值绑定多次）
