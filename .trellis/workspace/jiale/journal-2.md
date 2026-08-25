# Journal - jiale (Part 2)

> Continuation from `journal-1.md` (archived at ~2000 lines)
> Started: 2026-08-18

---



## Session 57: Bosonic B3 测量精度——homodyne CDF 网格反演精确采样

**Date**: 2026-08-18
**Task**: Bosonic B3 测量精度——homodyne CDF 网格反演精确采样
**Branch**: `master`

### Summary

B3 完成：homodyne_sample 换 CDF 网格反演（删旧实峰池，复权重混合含干涉，返回 ndarray）；新增 homodyne_pdf 公共 API；condition 未动。15 项 B3 测试（cat vs Fock cutoff=30 atol=1e-7、Born 一致性解析核验、直方图、K=1 atol=1e-12）；1094 passed。trellis-check 审查全绿（warnings/filterwarnings 安全、导入边界、complex dtype、searchsorted clamp）；spec 更新（§4 教学切边界 + §6.1 B3 契约 + filterwarnings gotcha）。OCR 超时未跑成，记为残留。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `fb3cea7` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 58: Bosonic B4 调和对账——purity/pure_fidelity 闭式 + R1 分层套件

**Date**: 2026-08-18
**Task**: Bosonic B4 调和对账——purity/pure_fidelity 闭式 + R1 分层套件
**Branch**: `master`

### Summary

B4 完成：新增 cvsim/bosonic/analyse.py（purity 对角近似 + pure_fidelity 等 V 限制 Gram 矩阵）；公共面 39→41（+purity +pure_fidelity），phaseB4 marker。10 项 B4 测试（layer 1 退化 L1a-L1e atol 1e-7+ + layer 2 GKP 恒等式 L2a-L2e，GKP 无解析基准内部互验）。L2d/L2e 因等 V 限制改用 self-fidelity/purity。替代 deprecated gkp_logical_overlap。全套 1105 passed。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `d96fa3a` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 59: Bosonic B5 BosonicCircuit 电路 DSL——circuit_v1 第三消费者

**Date**: 2026-08-19
**Task**: Bosonic B5 BosonicCircuit 电路 DSL——circuit_v1 第三消费者
**Branch**: `master`

### Summary

B5 完成：BosonicCircuit 三件套（builder + compile + ir）镜像 Gaussian，复用 circuit_common 零修改。新增 BosonicState.remove_mode（partial trace，homodyne 手动删模）。公共面 41→45。16 项 B5 测试（compiled vs naive atol 1e-12、IR roundtrip lossless、测量+feedforward+删模、通道）。Lab 接入延后 B6（vision §6.2 硬边界：lab import bosonic 类比 Fock F7 解锁）。全套 1124 passed。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `125aae4` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 60: Bosonic B6 GUI 任务清账 + 基线复验 1147 绿

**Date**: 2026-08-24
**Task**: Bosonic B6 GUI 任务清账 + 基线复验 1147 绿
**Branch**: `master`

### Summary

全套 pytest 1147 passed/4 skipped/6 warnings (249.65s)。B6 任务收尾：task.json 补 commit=f3f2848 + completedAt；start→finish→archive；auto-commit 17d9073。active tasks=0。B0-B6 done，B7 bridges+tutorials 为下一开放项。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `17d9073` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 61: Lab Gaussian 执行路径统一——删 _apply 13 分支 dispatch

**Date**: 2026-08-24
**Task**: Lab Gaussian 执行路径统一——删 _apply 13 分支 dispatch
**Branch**: `master`

### Summary

Session summary was not supplied.

### Main Changes

## 改动
`cvsim/lab/ir.py`（+154/-143，1 文件）——删 `_apply` 13 分支非测量 dispatch + `_logical_phys`/`_remove_phys`/`_state_after`，统一执行路径到 `GaussianCircuit.from_ir().compile()` 的 `_segments` 遍历。

## 决策（grilling Q1-Q6 全 A）
- Q1=A Lab 保留 mean path（`/run` 确定性），非测量 op 交编译合并段
- Q2=A 测量 op（homodyne/heterodyne）留 Lab 自家路径 + entry 元信息
- Q3=A1 Lab 遍历 `compiled._segments`，merged 调 `_apply_merged`，测量走自家（接受访问私有 `_segments`）
- Q4=A scan 路径统一 `GaussianCircuit`，用 symbolic param `$param`，删 `_state_after`
- Q5=A `_meters`/`_build_result` 留 Lab，不动结果组装胶水
- Q6=C Gaussian Lab 不支持 threshold，保持报错

## 语义保真
- homodyne 删模、heterodyne 不删模（镜像 `gaussian/compile.py:_run_op`）
- `measured` entry 结构不变（op/mode/phi/outcome，前端 app.js + 6 测试断言）
- scan 纯函数无 RNG，symbolic param 绑定 = 原替换值，输出数值不变
- Lab 特有校验保留：amplifier modes=[] 拒绝、通道 op 必填参数（`_LAB_REQUIRED_PARAMS`，不允许 core defaults）

## 验证
- 全量 pytest：**1147 passed / 4 skipped / 3 warnings**（171.66s，零回归）
- ruff：clean
- mypy：lab/ir.py 9 错（旧版 16，减少；无新类别，全是既有 `core: CircuitV1|None` union-attr / `safe` untyped / fock generic 技术债）

## 架构收益
Gaussian Lab 不再重复 `gaussian/circuit.py` 的 op dispatch；新后端加法从"抄一份 dispatch + 胶水"降为"写结果组装"。`circuit_common` 已是真深度（三表示继承 `CompiledCircuit`），Lab 现也坐上这趟车。

## 残留
- bafc534 archive auto-commit 把 lab/ir.py 代码与任务归档混在一起（commit message `chore(task): archive` 含 feat 代码），未拆分。


### Git Commits

| Hash | Message |
|------|---------|
| `bafc534` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 62: Lab 后端拆分——Fock/Bosonic 抽到独立模块（候选②）

**Date**: 2026-08-24
**Task**: Lab 后端拆分——Fock/Bosonic 抽到独立模块（候选②）
**Branch**: `master`

### Summary

Session summary was not supplied.

### Main Changes

## 改动
候选②：lab/ir.py 能力分层——Fock/Bosonic 后端执行拆到独立模块。

### 新文件
- `cvsim/lab/fock_backend.py`（280 行）：`run_fock_circuit` + `batch_fock_circuit` + 8 个 `_fock_*` helpers（mode_probs/mean_photon/purity/leakage/wigner/joint/measured）+ `_LEAKAGE_DIM_CAP`
- `cvsim/lab/bosonic_backend.py`（259 行）：`run_bosonic_circuit` + `fidelity_sweep` + 7 个 `_bosonic_*` helpers + `_fidelity_target`；复用 `fock_backend._fock_measured`（measured entry 格式共享）

### ir.py 变化
1216→759 行（-446），回 ADR-0001 §5 安全区（<800 行触发器）。保留 Gaussian 执行 + schema + translate_v0 + load_circuit。末尾 backward-compat re-export shim（外部 `from cvsim.lab.ir import run_fock_circuit` 不破）。

## 设计
- 三后端无相互依赖；共享类型（CircuitV0Error/View/LabCircuit/SCHEMA + _require/_num）经 `from cvsim.lab.ir import` 获取，ir.py 不 import 子模块 → 无循环
- bosonic_backend 复用 fock_backend 的 `_fock_measured`（measured entry 格式两后端相同，避免重复）
- 用 AST 精确定位函数边界抽取（非按行号估算），避免残块

## 验证
- 全量 pytest：**1147 passed / 4 skipped / 3 warnings**（223.75s，零回归）
- ruff：clean（22 错全 --fix，import 排序 + unused 删除）
- mypy：lab/ir.py 0 错；fock_backend/bosonic_backend 仅 4 错（全是既有类别：SCHEMA attr-defined + list/dict generic，从 ir.py 转移的技术债）

## 架构收益
ir.py 回到单一职责（Gaussian 执行 + schema）；Fock/Bosonic 各自独立文件，导航改善；加新后端 = 新文件，不动 ir.py 核心。

## 残留
- mypy 272 错总数含 cvsim 全包既有技术债（非本次引入）；fock/bosonic_backend 仅 4 错。


### Git Commits

| Hash | Message |
|------|---------|
| `6657c92` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 63: Lab 后端拆分——Fock/Bosonic 抽到独立模块（候选②）

**Date**: 2026-08-25
**Task**: Lab 后端拆分——Fock/Bosonic 抽到独立模块（候选②）
**Branch**: `master`

### Summary

Session summary was not supplied.

### Main Changes

## 改动
候选②：lab/ir.py 能力分层——Fock/Bosonic 后端执行拆到独立模块。

### 新文件
- `cvsim/lab/fock_backend.py`（280 行）：`run_fock_circuit` + `batch_fock_circuit` + 8 个 `_fock_*` helpers（mode_probs/mean_photon/purity/leakage/wigner/joint/measured）+ `_LEAKAGE_DIM_CAP`
- `cvsim/lab/bosonic_backend.py`（259 行）：`run_bosonic_circuit` + `fidelity_sweep` + 7 个 `_bosonic_*` helpers + `_fidelity_target`；复用 `fock_backend._fock_measured`（measured entry 格式共享）

### ir.py 变化
1216→759 行（-446），回 ADR-0001 §5 安全区（<800 行触发器）。保留 Gaussian 执行 + schema + translate_v0 + load_circuit。末尾 backward-compat re-export shim（外部 `from cvsim.lab.ir import run_fock_circuit` 不破）。

## 设计
- 三后端无相互依赖；共享类型（CircuitV0Error/View/LabCircuit/SCHEMA + _require/_num）经 `from cvsim.lab.ir import` 获取，ir.py 不 import 子模块 → 无循环
- bosonic_backend 复用 fock_backend 的 `_fock_measured`（measured entry 格式两后端相同，避免重复）
- 用 AST 精确定位函数边界抽取（非按行号估算），避免残块

## 验证
- 全量 pytest：**1147 passed / 4 skipped / 3 warnings**（223.75s，零回归）
- ruff：clean（22 错全 --fix，import 排序 + unused 删除）
- mypy：lab/ir.py 0 错；fock_backend/bosonic_backend 仅 4 错（全是既有类别：SCHEMA attr-defined + list/dict generic，从 ir.py 转移的技术债）

## 架构收益
ir.py 回到单一职责（Gaussian 执行 + schema）；Fock/Bosonic 各自独立文件，导航改善；加新后端 = 新文件，不动 ir.py 核心。

## 残留
- mypy 272 错总数含 cvsim 全包既有技术债（非本次引入）；fock/bosonic_backend 仅 4 错。


### Git Commits

| Hash | Message |
|------|---------|
| `9fa6480` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete
