# Fock 生产级架构设计（design.md）

> ADR 摘要：`docs/adr/0004-fock-circuit-common.md`（已接受）。本文为实现蓝图。

## 1. 总览

```
cvsim/
├── circuit_common.py     # 共享 DSL 核（D1/D2）：ParamRef + partition + compile_segments + CompiledCircuit
├── fock/                 # Fock 生产级（模块划分已认可）
│   ├── state.py          # FockState + 工厂 + leakage 三件套
│   ├── density.py        # FockDensity + thermal 工厂
│   ├── gates.py          # 命名门 + apply_unitary
│   ├── channels.py       # Kraus 通道
│   ├── observables.py    # 期望/测量
│   ├── analyse.py        # (F2 新建) 熵/纠缠/fidelity/partial_trace
│   ├── circuit.py        # (F3 新建) FockCircuit
│   ├── compile.py        # (F3 新建) Fock 编译
│   └── __init__.py       # 导出面（F2 冻结）
└── gaussian/             # 现状，迁移后 import circuit_common
```

依赖方向：`fock/* → circuit_common`（F3 起）；`gaussian/* → circuit_common`（迁移后）。
ADR-0001 allowlist：+ `cvsim.circuit_common`（`tests/test_architecture.py` 同步，F3 前置）。

## 2. circuit_common.py 规格（F1 前置迁移切片）

```
ParamRef(source: str, gain: float = 1.0)                      # 迁出 gaussian.circuit
partition(op_name, modes, *, _fixed_str_keys=frozenset(), **kwargs) -> 5 元组
compile_segments(ops, nmode, *, break_ops, remove_mode_ops)   # 泛化 _compile_segments
CompiledCircuit:  # 基类，物理经注册表注入
    __init__(nmode, segments, params)
    run(*, rng=None, **values) -> state | (state, results)
```

每表示注册表（frozen dict，放各自 compile/circuit 模块）：
- `FACTOR: dict[str, Callable]` — merged 段物理构造（高斯: (S,d)；Fock: (U,None) 或 F3 定）
- `DISPATCH: dict[str, Callable]` — break 段执行（通道/测量/ParamRef op）
- `BREAK_OPS: frozenset[str]` / `REMOVE_MODE_OPS: frozenset[str]`

迁移步骤（独立切片，766 测试兜底）：
1. 建 `cvsim/circuit_common.py`：搬 ParamRef + partition + compile_segments 骨架 + CompiledCircuit 骨架
2. `gaussian/circuit.py` / `compile.py` 改为 import 共享层，删本地副本（git mv 语义）
3. 全量 pytest 766 绿 + `tests/test_architecture.py` 确认（allowlist 暂不加，fock 未用）
4. commit + OCR

## 3. fock 包接口规格（A–H 已锁）

### 3.1 state.py

```python
@dataclass(frozen=True)
class FockState:
    amps: np.ndarray          # (N,) 或 (N, N) 截断系数；nmode = amps.ndim；cutoff = amps.shape[0]
    # 类方法工厂：
    vacuum(cutoff, nmode=1) / fock(n, cutoff) / fock2(n0, n1, cutoff)   # 现有
    coherent(cutoff, alpha)   # F1 新增
    squeezed(cutoff, r, phi=0.0)  # F1 新增
    cat(cutoff, alpha, even=True) # F1 新增；(|α⟩±|−α⟩)/√N，偶/奇约定与 bosonic cat 对齐
```

泄漏三件套（F1 新增，放 state.py 模块级函数）：

```python
truncation_leakage(state) -> float | None   # 工厂态精确（解析尾部）；非工厂态 None
check_leakage(state, *, validate=False,
              warn_threshold=1e-6, fail_threshold=1e-3) -> None
    # 已知泄漏 > warn → RuntimeWarning；> fail 或 validate=True → ValueError；None → 跳过
estimate_leakage(state, cutoff2) -> float   # 高 cutoff 对照工具（m≤2 可行），文档标注成本
```

### 3.2 density.py

```python
FockDensity:  # 现有（2 模）；通用 m F2
    thermal(cutoff, nbar)    # F1 新增类方法（对角密度阵 p_n = nbar^n/(nbar+1)^{n+1}）
```

### 3.3 gates.py（F1 新增）

```python
cz(state, weight, mode1, mode2)      # e^{i·weight·x̂⊗x̂} Fock 矩阵（与高斯同物理）
cx(state, weight, mode1, mode2)      # e^{i·weight·x̂⊗p̂}
mach_zehnder(state, theta, phi, mode1, mode2)
interferometer(state, U)             # U: m×m 酉，全模式张量积
apply_unitary(state, U, modes=None)  # Fock 独有通用入口（截断空间任意 U）
# backend= 参数 F4 加（ADR-0001 再评估）
```

### 3.4 channels.py（F1 新增）

```python
apply_kraus(state, kraus_ops: list[np.ndarray], mode)  # 通用 Kraus 应用
amplifier(state, G, nbar=0.0, mode=0)   # 相位不敏感放大（Kraus 构造 F1 prd 定）
phase_noise(state, sigma, mode=0)       # 去相（Kraus 构造 F1 prd 定）
```

### 3.5 observables.py（F2）

```python
pnr_sample(state, mode, rng=None) -> int
pnr_condition(state, mode, n) -> FockState        # 后验态
pnr_sample_and_condition(state, mode, rng=None) -> (int, FockState)
heterodyne_condition(state, mode, beta) -> FockState
heterodyne_sample_and_condition(state, mode, rng=None) -> (complex, FockState)
# 现有 homodyne 族不动；不做 heterodyne mean
```

### 3.6 analyse.py（F2，镜像 gaussian/analyse.py）

```python
entropy_vn(state) / log_negativity(state) / fidelity(a, b) / partial_trace(state, keep)
```

### 3.7 circuit.py + compile.py（F3，ADR-0004 §1）

FockCircuit builder：镜像高斯 + `measure_pnr(mode, name)`；
`compile()/run()/to_ir()/from_ir()` 同构；merged 合并策略（Kronecker 优化）F3 prd 定；
测量语义注册表回调（PNR 条件化 vs homodyne remove-mode）。

### 3.8 __init__.py + api-freeze

F1 期间导出面自由生长；**F2 出口冻结**（镜像 `tests/test_public_api.py` 的
GAUSSIAN_PUBLIC 模式 → FOCK_PUBLIC）。

## 4. 验证命令

```bash
.venv/Scripts/python.exe -m pytest tests -q          # 全量 766 绿（每次切片后）
.venv/Scripts/python.exe -m pytest tests/test_architecture.py -q  # allowlist
.venv/Scripts/python.exe -m pytest tests/test_fock_*.py -q        # Fock 侧
.venv/Scripts/python.exe -m ruff check cvsim/ tests/ --select I    # import 顺序
```

## 5. 风险表

| 风险 | 缓解 |
|------|------|
| circuit_common 迁移破坏高斯 | 独立切片 + 766 全量 + OCR 审查 |
| allowlist AST 扫描漏改 | test_architecture.py 显式加 circuit_common 用例 |
| 泄漏检查误报（非工厂态） | 三件套设计：None 跳过，绝不猜测 |
| Fock merged 合并性能（40⁴ 矩阵） | F3 定 Kronecker/逐 op 策略，架构留 segments 抽象 |

## 6. 开放项（F3+ 前置，不在本任务）

- Fock IR schema 演进（circuit_v1 是否复用）
- Fock 编译合并策略 + 性能预算
- 双后端 F4（ADR-0001 再评估）
- per-mode cutoffs（F2/F3）
