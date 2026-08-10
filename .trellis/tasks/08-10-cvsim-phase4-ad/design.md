# Design — Phase 4: Differentiable designer (F-AD) 技术设计

## 1. 架构与边界

```text
cvsim/
├── backend.py            # 新增：backend 分发核心（唯一 JAX 感知点）
├── symplectic.py         # 重写：19 函数加 backend= 参数（默认 numpy，行为不变）
├── gaussian/
│   ├── analyse.py        # 不动（numpy 目标函数源，公式参照）
│   └── ad.py             # 新增（child 6）：apply + 可微 log_neg + 优化目标
└── (其余 fock/bosonic/wigner)  # 零改动
```

**边界规则**：
- `cvsim/backend.py` 是**唯一** import jax 的文件；其余模块经 `_get_xp()` 间接取数组库。
- 核心 import 路径不碰 JAX（vision："No AD in core import path"）—— lazy import。
- 现有调用方零改动：所有新参数带默认值 `backend="numpy"`。
- JAX 路径用裸 jnp 数组（不强制走 `GaussianState` dataclass，那是 numpy 容器）。

## 2. Backend 协议（cvsim/backend.py）

```python
BACKENDS = ("numpy", "jax")
def _get_xp(backend: str) -> module:
    # "numpy" → np；"jax" → lazy import jax.numpy + 首次启用 x64
def require_jax() -> None:   # jax 未装时 raise ImportError（清晰报错 + pip install cvsim[jax]）
```

- **x64 强制**：jax backend 首次使用时 `jax.config.update("jax_enable_x64", True)`（F-PERF: dtype float64；cvsim 数值测试全为 float64 量级，float32 会破坏 atol）。
- **np/jnp 差异封装**（helper，避免 19 个函数各自处理）：
  - `_set(xp, arr, idx, val)` — np 用 `arr[idx] = val`（in-place），jnp 用 `arr.at[idx].set(val)`（不可变数组）。
  - `_block(xp, blocks)` — np 用 `np.block`，jnp 用嵌套 `jnp.concatenate`（jnp 无 block）。
  - `_allclose(xp, a, b, ...)` — np.allclose / jnp.allclose。
- **类型契约**：每个函数 docstring 注明输入可为 np.ndarray 或 jnp.ndarray（取决于 backend），返回同 backend 数组；`float`/`complex` 标量两后端通用。

## 3. symplectic.py 重写模式（16 函数双实现 + 3 函数仅 numpy）

统一模式（示例 `S_squeeze`）：

```python
def S_squeeze(nmode: int, r: float, mode: int = 0, *, backend: str = "numpy") -> Array:
    xp = _get_xp(backend)
    S = xp.eye(2 * nmode)
    S = _set(xp, S, (mode, mode), xp.exp(-r))
    S = _set(xp, S, (nmode + mode, nmode + mode), xp.exp(r))
    return S
```

**分组**：

| Child | 函数 | 备注 |
|-------|------|------|
| 2 gates-basic | `d_displace`, `S_squeeze`, `S_phase`, `S_beamsplitter`, `S_two_mode_squeeze` | `d_displace` 用 `xp.asarray` + `alpha.real/imag`；`S_beamsplitter` 用 `_block` |
| 3 gates-advanced | `S_CZ`, `S_CX`, `U_beamsplitter`, `embed_U_2mode`, `S_from_unitary`, `S_mach_zehnder` | `S_from_unitary` 用 `_block` |
| 4 validate | `is_symplectic`, `validate_symplectic`, `is_unitary`, `validate_unitary` | `_allclose` 封装 |
| 5 decompose | `reck_decomposition`, `clements_decomposition`, `compose_unitary_mesh` | **仅 numpy**：jax → `NotImplementedError`；docstring + ponytail 注释 |

**兼容性保险**：每个函数改动后立即跑现有 592 测试 —— numpy 默认路径必须逐值不变（`backend` 默认参数下代码路径等价或恒等）。

## 4. 可微目标链（child 6: cvsim/ad.py — 顶层模块）

**位置说明（ADR-0001）**：`cvsim.gaussian` 包只允许导入 conventions/symplectic，可微链需要 `cvsim.backend` → 放顶层 `cvsim/ad.py`（无隔离限制），`test_architecture.py` 全过。

```python
def apply_gaussian(backend, S, V) -> V'          # S V Sᵀ（jnp 直接 matmul，可微）
def log_neg_loss(backend, V, modes_A) -> E_N     # PT + 原始 symplectic 谱 + Σ max(0, -log2(2ν̃))
                                                 # 公式照抄 analyse.log_negativity（numpy 源），jnp 实现
```

- log_neg 公式源 = `cvsim/gaussian/analyse.py` L296（PT 翻 p、原始谱、逐项 max）—— ad.py 内 jnp 镜像，注释互链。
- `modes_A` 只支持 `int`（notebook 是 bipartition A=1 模 vs 其余），够用；多模 iterable 留 ponytail。
- 优化：`jax.grad` 求梯度 + 简单梯度上升（notebook 内实现，不进库）或 scipy 包装 grad；notebook 教学用梯度上升展示收敛轨迹。

## 5. 测试策略（测试先行，每 child red→green）

- **共享参数化**：`tests/conftest.py` 加 `backends` fixture：`pytest.param("jax", marks=pytest.mark.skipif(jax 未装))` + `"numpy"`；全部新测试 `@pytest.mark.parametrize("backend", backends)`（exit 2 主体）。
- **每 child 测试**：
  - gates-basic/advanced：np 路径与旧实现结果逐值一致（回归断言硬编码已知值）；jax 路径与 np 路径数值一致；**梯度 vs 有限差分**（central diff，squeeze r / BS θ，exit 1）。
  - validate：np/jax 对已知 symplectic/非 symplectic 矩阵判定一致。
  - decompose：numpy 回归（现有行为不变）+ jax → NotImplementedError。
  - objective：log_neg 梯度 vs FD（对 r）；优化收敛到**扫描最优** r*（物理修正：损耗下 E_N(r) 饱和无闭式最优，目标改用能量惩罚 E_N − λ·2sinh²r，参照=暴力扫描）。
- **JAX 未装时**：所有 jax 用例 skip（`importorskip`），numpy 用例照跑 —— CI 无 jax 依赖也能绿。

## 6. 兼容性与回滚

- 每 child 独立 commit，`backend=` 默认值保证中间状态可发布。
- 回滚点：任意 child 的 commit 可 revert，不影响其余。
- 破坏性变更：**无**（新增参数、默认 numpy、唯一新文件 backend.py/ad.py）。
- pyproject 变更（child 1 或 6）：新增 `[jax]` extra，**不**动现有依赖。

## 7. 权衡记录

| 决策 | 权衡 |
|------|------|
| 方案 B（全量 backend 化） | 工作量大 vs 接口彻底、vision 字面兑现；用 6 小步 + 默认参数化解风险 |
| decompose 仅 numpy | 接口不完整（显式 raise） vs 避免 jnp 控制流大坑；docstring 诚实标注 |
| backend.py 唯一 JAX 感知点 | 违反"无全局状态"直觉 vs 单一 import 点、lazy、测试友好 |
| 裸 jnp 数组（不走 GaussianState） | 教学示例需手写 apply vs 避免 dataclass 双后端化（那是另一个大坑） |
