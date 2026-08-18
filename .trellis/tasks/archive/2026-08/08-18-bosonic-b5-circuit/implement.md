# B5 — BosonicCircuit 电路 DSL Implement Plan

## 8 步执行

### Step 1: `BosonicState.remove_mode(mode)` — state.py

新增 `remove_mode(mode)` 方法：逐分量 partial trace（V_k 删 2 行 2 列 + xxpp 重排，r̄_k 删 2 元素，w 不变）。提取 `heterodyne_condition` 的删模逻辑（idx_A/idx_B/pack/perm）为通用。

验证：`python -c "from cvsim.bosonic import BosonicState; s=BosonicState.vacuum(2); s2=s.remove_mode(0); print(s2.nmode, len(s2.components[0].V))"` → 1, 2。

### Step 2: `cvsim/bosonic/circuit.py` — BosonicCircuit builder

镜像 `GaussianCircuit`：
- `__init__`/`_ops`/`_partition`（复用 circuit_common.partition）
- 11 gate builder（squeeze/displace/phase/fourier/beamsplitter/mach_zehnder/two_mode_squeeze/cz/cx/interferometer）
- 3 channel builder（loss/amplifier/phase_noise/gaussian_channel）
- 3 measure builder（measure_homodyne/measure_heterodyne/measure_threshold）
- `__iadd__`/`__add__`/`__repr__`/`__len__`
- `compile()`/`run()`（委托 CompiledBosonic）
- `to_ir()`/`from_ir()`

验证：`python -c "from cvsim.bosonic import BosonicCircuit; c=BosonicCircuit(2); c.squeeze(0,0.5); c.beamsplitter(0,1,0.3); print(len(c))"` → 2。

### Step 3: `cvsim/bosonic/compile.py` — CompiledBosonic + _instantiate + _factor + _run_op

复刻 Gaussian compile.py：
- `_BREAK_OPS` / `_REMOVE_MODE_OPS` / `_MERGEABLE_OPS`（同集合）
- `_factor(op, nmode) -> (S, d)`：复用 `cvsim.symplectic.S_*` + `d_displace`（与 Gaussian _factor 相同逻辑，直接复刻）
- `_instantiate(ops, nmode, values) -> (S, d)`：合并 merged ops（同 Gaussian）
- `_run_op(op, st, results, values, *, rng)`：channels + measures + ParamRef
  - measure_homodyne: `outcomes, post = homodyne_sample_and_condition(st, mode, phi, rng=rng, shots=1)`; `results[name] = float(outcomes[0])`; `st = post.remove_mode(mode)`
  - measure_heterodyne: `beta, post = heterodyne_sample_and_condition(st, mode, rng=rng)`; `results[name] = complex(beta)`; `st = post`（已删模）
  - measure_threshold: `results[name] = int(sample_threshold(st, mode, rng=rng))`
  - channels: 调用 `bosonic.channels.loss/amplifier/phase_noise`
  - gaussian_channel: 调用 `bosonic._apply_affine`
- `CompiledBosonic(CompiledCircuit)`：`_init_state`/`_apply_merged`/`_run_op`

验证：`python -c "from cvsim.bosonic import BosonicCircuit; c=BosonicCircuit(1); c.squeeze(0,0.5); c.displace(0,0.5); st=c.run(); print(type(st), st.nmode)"`。

### Step 4: `cvsim/bosonic/ir.py` — circuit_v1 to_ir/from_ir

镜像 Gaussian ir.py，无扩展字段：
- `SCHEMA = "circuit_v1"`
- `OpMeta` dataclass（同 Gaussian 的 arity/kind/defaults）
- `to_ir(circuit) -> dict`：op 列表编码
- `from_ir(data) -> BosonicCircuit`：解码 + 重建
- `_encode`/`_decode`/`_check_value`（值编码与表示无关，复刻或共享）

验证：`python -c "from cvsim.bosonic import BosonicCircuit; c=BosonicCircuit(1); c.squeeze(0,0.5); d=c.to_ir(); c2=BosonicCircuit.from_ir(d); print(c2.to_ir()==d)"`。

### Step 5: 公共面

- `cvsim/bosonic/__init__.py`：import + `__all__` +`BosonicCircuit` +`ParamRef` +`to_ir` +`from_ir`
- `pyproject.toml`：`markers` +`phaseB5: Bosonic B5 circuit DSL tests`
- `tests/test_public_api.py`：BOSONIC_PUBLIC +`BosonicCircuit` +`ParamRef` +`to_ir` +`from_ir`

验证：`python -c "import cvsim.bosonic as b; print(b.BosonicCircuit, b.ParamRef, b.to_ir, b.from_ir)"`；`pytest tests/test_public_api.py -q`。

### Step 6: `tests/test_b5_bosonic_circuit.py` — 全 @phaseB5

- 出口 1 compiled vs naive：gate 序列 (squeeze/displace/bs/cz/...) 直接调 gates 函数 vs circuit.run()，态 atol 1e-12
- 出口 2 IR roundtrip：to_ir → from_ir → run，态 atol 1e-12 + golden fixture
- 出口 3 Lab backend="bosonic"：circuit JSON → lab 加载 → run
- 测量+feedforward：homodyne 测 + ParamRef 反馈 + 删模，results dict 正确，后续 gate 模映射正确
- 通道：loss/amplifier 逐分量 apply

验证：`pytest tests/test_b5_bosonic_circuit.py -m phaseB5 -q`。

### Step 7: Lab backend 路由 + spec

- `cvsim/lab/ir.py`：`backend in ("gaussian","fock","bosonic")` + `_load_bosonic`
- `.trellis/spec/cvsim/bosonic.md`：§6.3 B5 契约

### Step 8: 全套回归 + commit + 归档

`pytest -q` → 1105 + B5 新增 passed。commit `feat(bosonic): B5 BosonicCircuit 电路 DSL`。

## 风险/回退点

- `remove_mode` partial trace 逻辑：复用 `heterodyne_condition` 删模片段，需确认 xxpp 重排一致
- `_factor` 复刻：symplectic 函数与 Gaussian 同源，零差异风险
- Lab backend：新增 `_load_bosonic` 不改 gaussian/fock 路径
- IR 复刻：Bosonic 无 cutoff 扩展，比 Fock IR 更简

## 验证命令

```powershell
.venv\Scripts\python.exe -m pytest tests/test_b5_bosonic_circuit.py -m phaseB5 -q
.venv\Scripts\python.exe -m pytest -m phaseB5 -q
.venv\Scripts\python.exe -m pytest -q
```
