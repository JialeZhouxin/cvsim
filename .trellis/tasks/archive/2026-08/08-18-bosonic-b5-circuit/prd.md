# B5 — BosonicCircuit 电路 DSL PRD

## Goal

B5 = BosonicCircuit 电路 DSL 三件套（builder + compile + IR）+ Lab `backend="bosonic"` 路由。复用 `circuit_common.py`（ADR-0004），镜像 Gaussian 结构，逐分量执行。circuit 从 vacuum 起，K=1 恒定（gate 不增分量）。

## Background

- B0-B4 done（vision v0.5.0）。BOSONIC_PUBLIC 41 名。
- `circuit_common.py`（ADR-0004）已提供 `ParamRef`/`partition`/`compile_segments`/`CompiledCircuit` 基类——复用零修改。
- Gaussian 三件套（`GaussianCircuit` + `compile.py` + `ir.py`）+ Fock 同构——Bosonic 镜像此结构。
- Bosonic gates/channels/measures 全套已存在（B1-B3）：11 门 + 3 通道 + 3 测量，可直接被 circuit builder 调用。
- Lab `ir.py` `backend` 路由目前只支持 gaussian/fock——B5 加 bosonic。

## Requirements

### R1 — BosonicCircuit builder（`cvsim/bosonic/circuit.py`，新文件）

- **R1.1** 镜像 GaussianCircuit builder：`__init__(nmode)` + 11 gate builder（squeeze/displace/phase/fourier/beamsplitter/mach_zehnder/two_mode_squeeze/cz/cx/interferometer）+ 4 channel builder（loss/amplifier/phase_noise/gaussian_channel）+ 3 measure builder（measure_homodyne/measure_heterodyne/measure_threshold）。签名 1:1 复制 GaussianCircuit。
- **R1.2** composition：`__iadd__`/`__add__`/`__repr__`/`__len__`（nmode 匹配校验）。
- **R1.3** 执行：`compile() -> CompiledBosonic` + `run(*, rng=None, **params) -> BosonicState | tuple[BosonicState, dict]`（委托 CompiledBosonic，单执行路径 ADR-0002）。
- **R1.4** `_partition` 复用 `circuit_common.partition`。

### R2 — compile（`cvsim/bosonic/compile.py`，新文件）

- **R2.1** `_factor(op, nmode) -> (S, d)`：复用 `cvsim.symplectic.S_*` + `d_displace`（与 Gaussian `_factor` 同源逻辑，复刻保持隔离）。
- **R2.2** `_instantiate(ops, nmode, values) -> (S, d)`：合并 merged gate ops 成单个 symplectic。
- **R2.3** `CompiledBosonic(CompiledCircuit)`：`_init_state` = `BosonicState.vacuum(nmode)`；`_apply_merged` = `apply_symplectic(st, S, d, validate=False)`（逐分量）；`_run_op` = channels + measures + ParamRef。
- **R2.4** `_BREAK_OPS` = channels + measurements；`_REMOVE_MODE_OPS` = {measure_homodyne, measure_heterodyne}。
- **R2.5** measure 语义：
  - homodyne: `homodyne_sample_and_condition(shots=1)` → `results[name]=float(outcomes[0])` → `post.remove_mode(mode)`（手动删模，B3 homodyne_condition 不删模）
  - heterodyne: `heterodyne_sample_and_condition` → `results[name]=complex(beta)` → post（已删模，不再删）
  - threshold: `sample_threshold` → `results[name]=int(outcome)`，无删模

### R3 — IR（`cvsim/bosonic/ir.py`，新文件）

- **R3.1** `to_ir(circuit) -> dict` / `from_ir(data) -> BosonicCircuit`，circuit_v1 schema，**无扩展字段**（初态 vacuum，K=1 恒定）。
- **R3.2** `_encode`/`_decode`/`_check_value` 值编码与表示无关，复刻 Gaussian ir.py。

### R4 — BosonicState.remove_mode（`cvsim/bosonic/state.py`，改）

- **R4.1** `remove_mode(mode) -> BosonicState`：逐分量 partial trace（V_k 删 2 行 2 列 + xxpp 重排，r̄_k 删 2 元素，w 不变）。提取 `heterodyne_condition` 的删模逻辑（idx_A/idx_B/pack/perm）。

### R5 — 公共面 + Lab 路由

- **R5.1** `cvsim/bosonic/__init__.py`：`__all__` +`BosonicCircuit` +`ParamRef`(re-export) +`to_ir` +`from_ir`；BOSONIC_PUBLIC 41→45。
- **R5.2** `pyproject.toml`：+`phaseB5` marker。
- **R5.3** `tests/test_public_api.py`：BOSONIC_PUBLIC +4 名。
- **R5.4** `cvsim/lab/ir.py`：`backend in ("gaussian","fock","bosonic")` + `_load_bosonic` 路由（验证 IR + 返回 circuit）。

## Acceptance criteria

1. **AC1（R1-R2 compiled vs naive）**：gate 序列直接调 gates 函数 vs `circuit.run()`，态 atol 1e-12（K=1, m=1 fixture）。
2. **AC2（R3 IR roundtrip）**：`to_ir → from_ir → run`，态 atol 1e-12（golden fixture，lossless）。
3. **AC3（R5.4 Lab backend）**：Bosonic JSON → Lab 加载 → run，态匹配脚本（atol）。
4. **AC4（测量+feedforward）**：homodyne 测 + ParamRef 反馈 + 删模，results dict 正确，模映射 shift 正确。
5. **AC5**：全套回归绿（1105 + B5 新增 passed），`error:cvsim.*` filterwarnings 不破。

## Out of scope

- Bosonic IR 扩展字段（initial 注入、K_max 截断）——初态 vacuum，K=1 恒定
- GKP 初态注入——B6/B7 教程场景
- GUI 三件套（Wigner view / fidelity sweep / step execution）——B6
- circuit_common 改动——复用零修改

## Technical notes

- `homodyne_condition`（B3）不删模 → circuit `measure_homodyne` 手动 `remove_mode`；`heterodyne_condition` 已删模 → circuit `measure_heterodyne` 直接用 post（双重删模会错）。
- `homodyne_sample_and_condition`（B3）返回 `(outcomes_array, post)`，circuit 取 `outcomes[0]`。
- `_factor` 复用 `cvsim.symplectic`（symplectic 矩阵与表示无关）。
- K=1 恒定：gate 不增分量，O(1) per merged segment。
