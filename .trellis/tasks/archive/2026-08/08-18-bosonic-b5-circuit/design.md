# B5 — BosonicCircuit 电路 DSL Design

## 1. 范围

B5 = BosonicCircuit 三件套（builder + compile + IR）+ Lab backend="bosonic" 路由。
复用 `circuit_common.py`（ADR-0004），镜像 Gaussian 结构，逐分量执行。
- 新增公共 API：`BosonicCircuit` + `ParamRef`(re-export) + `to_ir`/`from_ir`（+4 名，41→45）
- IR 无新扩展字段，初态 vacuum，K=1 恒定（circuit 内不增分量）

## 2. 架构

```
cvsim/bosonic/
├── circuit.py      # 新：BosonicCircuit builder（镜像 Gaussian 11门+3通道+3测量）
├── compile.py      # 新：CompiledBosonic + _instantiate + _factor + _DISPATCH + _run_op
├── ir.py           # 新：circuit_v1 to_ir/from_ir（无扩展字段）
├── state.py        # 改：+remove_mode(mode) 方法
└── __init__.py     # 改：+BosonicCircuit +ParamRef +to_ir +from_ir
cvsim/lab/ir.py     # 改：backend 路由 +bosonic
```

## 3. 数学/物理

### 3.1 merged segment（gate 合并）

复用 Gaussian `_instantiate` 逻辑：merged gate ops 合成单个 (S, d)：
- `S = S_n @ ... @ S_1`，`d = S_n @ ... @ S_1 d_1 + ... + d_n`
- `_factor` 用 `cvsim.symplectic` 的 `S_*`（与表示无关）+ `d_displace`
- Bosonic `_apply_merged`：逐分量 `V_k ← S V_k Sᵀ, r̄_k ← S r̄_k + d, w_k 不变`（复用 `bosonic.apply_symplectic`）

### 3.2 break ops

- channels（loss/amplifier/phase_noise/gaussian_channel）：break，逐分量 apply（非 symplectic）
- measurements（homodyne/heterodyne/threshold）：break
- ParamRef op（feedforward gate）：break

### 3.3 measurements

| op | 采样 | condition | 删模 | 结果存储 |
|----|------|-----------|------|----------|
| measure_homodyne | `homodyne_sample`（CDF） | `homodyne_condition` | **手动 `remove_mode`** | `results[name] = float(outcomes[0])` |
| measure_heterodyne | `heterodyne_sample` | `heterodyne_condition`（已内置删模） | 内置 | `results[name] = complex(beta)` |
| measure_threshold | `sample_threshold` | 无 | 无删模 | `results[name] = int(outcome)` |

### 3.4 remove_mode（partial trace，逐分量）

`BosonicState.remove_mode(mode)`：
- per component: `V_k` 删第 mode 行/列 + 第 m+mode 行/列（xxpp 重排），`r̄_k` 删第 mode + m+mode 元素，`w_k` 不变
- 复用 `heterodyne_condition` 的删模逻辑（idx_A/idx_B/pack/perm）提取为通用 `remove_mode` 函数

## 4. API

### 4.1 BosonicCircuit（builder，镜像 GaussianCircuit）

```python
class BosonicCircuit:
    def __init__(self, nmode: int) -> None
    # builder 方法（镜像 Gaussian，1:1 签名）：
    squeeze/displace/phase/fourier/beamsplitter/mach_zehnder/two_mode_squeeze/cz/cx/interferometer
    loss/amplifier/phase_noise/gaussian_channel
    measure_homodyne/measure_heterodyne/measure_threshold
    # composition
    __iadd__/__add__/__repr__/__len__
    # 执行
    compile() -> CompiledBosonic
    run(*, rng=None, **params) -> BosonicState | tuple[BosonicState, dict]
    # IR
    to_ir() -> dict / from_ir(cls, data) -> BosonicCircuit
    # 内部
    _partition(op_name, modes, *, _fixed_str_keys=frozenset(), **kwargs) -> tuple
```

### 4.2 compile.py

```python
class CompiledBosonic(CompiledCircuit):
    _init_state: return BosonicState.vacuum(self.nmode)
    _apply_merged: S,d = _instantiate(...); return apply_symplectic(st, S, d, validate=False)
    _run_op: _run_op(op, st, results, values, rng=rng)  # channels + measures + ParamRef
```

### 4.3 ir.py

`to_ir(circuit) -> dict` / `from_ir(data) -> BosonicCircuit`：circuit_v1 schema，无扩展字段。
复用 Gaussian ir.py 的 `_encode`/`_decode`/`_check_value` 逻辑（值编码与表示无关）。

### 4.4 Lab backend

`cvsim/lab/ir.py`：`backend in ("gaussian", "fock", "bosonic")`；`_load_bosonic` 路由（验证 IR + 返回 circuit）。

## 5. 坑

1. **homodyne 不删模**：B3 `homodyne_condition` 保留模，circuit 需手动 `remove_mode`——与 Gaussian 不同（Gaussian homodyne_condition 内置删模）。
2. **heterodyne 已删模**：B3 `heterodyne_condition` 内置删模——circuit 直接用 post 态，**不再** remove_mode（双重删模错误）。
3. **homodyne_sample 返回 ndarray**：B3 改了返回类型 `(shots,)`，circuit `measure_homodyne` 取 `outcomes[0]`。
4. **K=1 恒定**：circuit 从 vacuum 起，gate 不增分量。但 `measure_homodyne` 的 condition 仍 K=1（homodyne_condition 不改 K）。displace 不增 K（单高斯位移）。
5. **symplectic 复用**：`_factor` 直接 import `cvsim.symplectic.S_*`（与 Gaussian 同），零新矩阵逻辑。
6. **circuit_common 不改**：Bosonic 复用 `ParamRef`/`partition`/`compile_segments`/`CompiledCircuit`，零修改。
7. **Lab backend whitelist**：Bosonic 需定义 op whitelist（镜像 Gaussian LAB_WHITELIST），Lab 验证用。
8. **filterwarnings**：measurements 采样可能触发 homodyne_pdf 的负 Re(S) warn（消息不以 cvsim. 开头，安全）。

## 6. 测试设计

`tests/test_b5_bosonic_circuit.py`，全 `@pytest.mark.phaseB5`：
- 出口 1：compiled vs naive（K=1 fixture，m=1，gate 序列同态 atol 1e-12）
- 出口 2：IR roundtrip lossless（to_ir → from_ir → 重跑 atol 1e-12，golden fixture）
- 出口 3：Lab backend="bosonic" 消费 circuit_v1（JSON → run → 态）
- 测量+feedforward：homodyne 测+反馈+删模，结果 dict 正确
- 通道：loss/amplifier 逐分量
