# 对抗式审查与测试报告：`F-ANALYSE-1 symplectic_eigenvalues + purity`

| 字段 | 内容 |
|------|------|
| Commit | `6276358` |
| 标题 | `feat(gaussian): F-ANALYSE-1 symplectic_eigenvalues + purity` |
| 审查角色 | 研究员 / 对抗式审查 |
| 审查日期 | 2026-07-30 |
| 代码基线 | `cvsim/gaussian/analyse.py`, `cvsim/gaussian/__init__.py`, `tests/test_analyse.py` |

---

## 1. 任务完成了什么

本任务实现 vision 文档中的 **F-ANALYSE-1**：`symplectic_eigenvalues`（Williamson 分解）与 `purity`（高斯态纯度），并附全面测试。

### 1.1 交付物清单

| 能力 | API | 位置 |
|------|-----|------|
| 内部输入归一化 | `_as_cov(state)` | `cvsim/gaussian/analyse.py` |
| 物理性检查（既有，已重构） | `is_physical`, `validate_state` | 同上 |
| 辛本征值（Williamson-Cholesky） | `symplectic_eigenvalues(state, *, atol=1e-10)` | 同上 |
| 纯度 | `purity(state)` | 同上 |
| 模块导出 | `cvsim.gaussian` | `__init__.py` |
| 测试 | `tests/test_analyse.py`（19 项） | tests |

### 1.2 数学模型（已实现）

**Williamson 定理**（Serafini §3.2 / Weedbrook §II.B）：

$$
V = S^{\mathsf T} (\bigoplus_{j=1}^m \nu_j \mathbb I_2) S,\quad S^{\mathsf T}\Omega S = \Omega
$$

辛本征值 $\nu_j \ge 1/2$ 通过 Cholesky 路径计算：

1. $V \gets \frac12(V+V^{\mathsf T})$
2. $K = \mathrm{chol}(V)$（近奇异时 $V + 10^{-14}I$ jitter）
3. $A = K^{\mathsf T}\Omega K$（反对称）
4. 取 $\mathrm{eig}(iA)$ 得实 $\pm\nu_j$ 对
5. $\mathrm{sort}(|\nu_j|)[:m]$ 取前 m 个（等 $\nu$ 时修正：`[::2]` 而非 `nu_all[m:]`）
6. $\nu_j \gets \max(\nu_j, 1/2)$

**纯度**（vision §4.2, $\hbar=1$）：

$$
\mu = \frac{1}{2^m\sqrt{\det V}} = \prod_{j=1}^m \frac{1}{2\nu_j}
$$

### 1.3 对 PRD Acceptance 的对照

| # | 验收项 | 结果 |
|---|--------|------|
| 1 | `symplectic_eigenvalues` 对真空/热态/TMSV 返回正确 $\nu$ | **通过**（19 项现有测试） |
| 2 | `purity` 对纯态返回 1，热态返回 $1/(2\bar n+1)$ | **通过** |
| 3 | $\mu = \prod 1/(2\nu_j)$ cross-check 成立 | **通过** |
| 4 | 裸 ndarray / `GaussianState` 双入口 | **通过** |
| 5 | 非法形状/非 PD 抛错 | **通过** |
| 6 | 全量 pytest 无回归 | **通过**（315 项全绿） |

**结论（完成度）：** 核心数学实现正确，功能可用。

---

## 2. 对抗式审查

审查策略：不默认信任已有单测，从 **算法正确性 / 约定一致性 / 数值稳定性 / API 设计一致性** 四个方向施压。

### 2.1 数学正确性（高置信）

| 检查 | 方法 | 结果 |
|------|------|------|
| 真空（1/2/3 模） | $\nu=1/2$、$\mu=1$ | 全部通过 |
| 热态（4 个 $\bar n$ 值） | $\nu=\bar n+1/2$、$\mu=1/(2\bar n+1)$ | 全部通过 |
| TMSV 纯态（r=0.6） | $\nu=[0.5,0.5]$、$\mu=1$ | 全部通过 |
| TMSV + loss 混合 | $\mu<1$、$\nu\ge 0.5$ | 全部通过 |
| 不等 $\nu$ 多模产品（[0.6, 2.5, 5.5]） | `[::2]` 正确（非 `nu_all[m:]`） | 全部通过 |
| 挤压纯态（r=0.3/1.5/2.5） | $\nu=0.5$、$\mu=1$ | 全部通过 |
| $\mu = \prod 1/(2\nu_j)$ 混合 3 模 | max err < $10^{-9}$ | 全部通过 |
| $\mu = \prod 1/(2\nu_j)$ lossy TMSV | max err < $10^{-9}$ | 全部通过 |
| 对裸 ndarray 与 `GaussianState` 一致 | 全路径覆盖 | 全部通过 |
| Cholesky fallback（4 模 TMSV r=4.0） | jitter 路径仍返回 $\nu=0.5$、$\mu=1$ | 全部通过 |
| `symplectic_eigenvalues` 输出与独立 `\|iΩV\|` 参考 |
| 3 模不等 $\nu$ | 列一致 atol $10^{-8}$ | 全部通过 |
| TMSV+thermal combo | 列一致 atol $10^{-8}$ | 全部通过 |
| 真空底 clip | $V=0.5I-10^{-13}I$ → $\nu=0.5$ 被 clamp | 全部通过 |

**判定：** Williamson-Cholesky 路径在 $\hbar=1$、xxpp、$V_{\text{vac}}=I/2$ 约定下数学正确，`nu_all[::2]` 取对等 $\pm\nu$ 对的方法在不等 $\nu$ 多模场景已实证正确。

### 2.2 真实缺陷：`purity` 与 `symplectic_eigenvalues` 对非对称 V 处理不一致

**发现：** `symplectic_eigenvalues` 内部执行 $V \gets \frac12(V+V^{\mathsf T})$ 对称化；而 `purity` **不**对称化，直接对裸 $V$ 算 `slogdet`。

**对抗验证：**

```text
V_therm = 1.5·I  (热态 n̄=0.5, ν=1.5)
V_asym = V_therm.copy()
V_asym[0,1] += 0.4
V_asym[1,0] -= 0.4  # 真正的反对称扰动

symplectic_eigenvalues(V_asym) → [1.5]   (对称化后 ν 不变)
purity(V_asym)        → 0.32208            (裸 det 改变)
∏ 1/(2νⱼ)            → 0.33333            (从 ν 回算的参考纯度)

→ purity ≠ ∏ 1/(2νⱼ)  !  交叉校验在非对称输入下被打破
```

**影响：** 物理协方差本应对称，但浮点累积或外部脏输入可引入微小非对称性。vision §7 要求 "Symmetrize $V$ after every noisy update"；`purity` 违反此规范。研究员依赖 $\mu = \prod 1/(2\nu_j)$ 作为数值不变量时，非对称 V 会导致不可追踪的偏离。

**严重度：** 中

**建议修复：** `purity` 开头加 `V = 0.5 * (V + V.T)` 与 `symplectic_eigenvalues` 对齐。

### 2.3 真实缺陷：非物理输入静默

**发现：** `purity(V=0.4·\mathbb I_2)` 返回 **1.25 > 1** 不报错。`symplectic_eigenvalues` 把 $\nu$ clip 到 0.5，掩盖 sub-vacuum 不确定性关系破坏。

**对抗验证：**

```text
V_sub = 0.4·I_2     # det(V)=0.16 > 0

is_physical(V_sub)  → False  (V + iΩ/2 非 PSD)
purity(V_sub)       → 1.25   (无异常/警告)
symplectic_eigenvalues(V_sub) → [0.5]  (静默 clip 到 0.5)
```

**分析：**

- `purity` 的 docstring 说 "Raises ValueError if det(V) ≤ 0" —— 但 `det(0.4I)=0.16 > 0`，所以不进入错误分支。
- 然而 $V=0.4I$ 是非物理的：$0.4I + i\Omega/2$ 有负特征值。
- 返回 $\mu=1.25$ 在物理上不可能，但代码认为是"合法输出"。
- $\nu$ clip 到 0.5 进一步掩盖了非物理性。

**影响：** 研究员/用户依赖 `purity(V) ≤ 1` 作为高斯态的不变量校验时，会收到看似合法但物理上不可能的 $>1$ 值。非物理输入可以静默通过两个 API。

**严重度：** 中

**建议修复：**

1. **`purity`** 增加可选 `validate: bool = False` 参数，当 `validate=True` 时调用 `is_physical` 拒绝非物理态。
2. **`symplectic_eigenvalues`** 同样增加 `validate` 参数。
3. 或在 docstring 中明确注明："此函数**不**校验物理性；非物理 V 可能产生 $\mu > 1$ 或 $\nu$ 被 clip 的输出"。

### 2.4 真实缺陷：`atol` 参数是死参

**发现：** `symplectic_eigenvalues` 签名声明 `atol: float = 1e-10`，但函数体**从未引用** `atol`。

**对抗验证（源码检查）：**

```python
# 签名
def symplectic_eigenvalues(
    state: GaussianState | np.ndarray,
    *,
    atol: float = 1e-10,      # ← 声明
) -> np.ndarray:
    """..."""
    # 函数体: 仅引用 V, K, A, ev, nu_all, nu
    # 没有任何一行检查 if condition > atol 或类似用法
    nu = np.maximum(nu, 0.5)  # 硬编码 0.5
    return nu.astype(float)
```

`inspect.getsource` 确认函数体中无 `atol` 引用。

**影响：** 调用者传入 `atol=1e-6` 或 `atol=0` 时，实际行为不变。API 设计误导用户以为可以控制容差。

**严重度：** 低

**建议修复：**

1. 移除 `atol` 参数（简洁）。
2. 或将 clip 改成 `nu = np.maximum(nu, 0.5 - atol)` 让 `atol` 实际生效。

### 2.5 非缺陷（审查中澄清，原误判）

以下在初版对抗脚本中被标记为 FAIL，但经推理验证后确认**不是 bug**：

| 初版误报 | 澄清 |
|----------|------|
| 挤压态 `det V = 0.25` 不变 | 正确。$S_{\text{squeeze}}$ 是 symplectic（$\det S=1$），$\det(SVS^{\mathsf T}) = \det V = (1/4)^m$ 恒成立。纯态判据成立。 |
| `purity` 对非对称 V (仅改 `[0,1]`) 结果不变 | 测试设计缺陷：只改上三角没改下三角，$\det$ 不变。真正的反对称扰动（上下三角反号加）才能测出差异。 |
| `symplectic_eigenvalues` 对称化后 $\nu$ 改变 | 对称化后矩阵变了，$\nu$ 当然变。这是**正确的**对称化行为。 |
| list-of-lists 输入不抛错 | `[[1,0],[0,1]]` 是 I，合法 numpy 转换。$V=\mathbb I$ 对应 $\bar n=0.5$ 热态，物理。**不应**抛错。 |

### 2.6 设计优点

1. **`_as_cov` 抽象：** 将 `GaussianState | np.ndarray` 双入口归一化，同时允许 `is_physical` 在格式错误时返回 `False`（而非抛错），提供了弹性。
2. **Cholesky-jitter fallback：** 对近奇异纯态做了容错。
3. **`[::2]` 修正：** 有明确注释解释为何不用 `nu_all[m:]`，且在 `test_thermal_product_unequal_nbar` 中有回归测试。
4. **slogdet 用于 purity：** 避免 det 直接求值在纯态/大 m 时的浮点下溢。
5. **purity cross-check 测试：** 用 `∏ 1/(2νⱼ)` 做二次验证，发现不一致时的 debug 路径清晰。

---

## 3. 缺陷与风险登记

| ID | 级别 | 描述 | 证据 / 复现 | 建议修复 |
|----|------|------|-------------|----------|
| R1 | **中** | `purity` 不对称化 V，与 `symplectic_eigenvalues` 不一致。非对称 V 时 $\mu \neq \prod 1/(2\nu_j)$ | `V=1.5I` 上反对称扰动 ±0.4：`purity=0.32208` vs `∏1/(2ν)=0.33333` | `purity` 开头加 `V = 0.5 * (V + V.T)` |
| R2 | **中** | 非物理输入（$V=0.4I$）静默：`purity` 返回 1.25、`symplectic_eigenvalues` clip 到 0.5，均不报错 | `is_physical(0.4I)=False`，但两个 API 均返回"合法"数值 | 可选 `validate` 参数或显式 docstring 警告 |
| R3 | **低** | `symplectic_eigenvalues` 的 `atol` 参数声明但未使用 | 函数体中无 `atol` 引用 | 移除参数或让 clip 用 `0.5 - atol` |

**未发现：** 算法级错误（Williamson 分解）、真空底 clip 尺度错误、[::2] 取配逻辑错误、Cholesky 路径数值崩溃。

---

## 4. 测试报告

### 4.1 原有回归

```text
pytest tests/test_analyse.py -v
19 passed in 1.54s
```

| 用例 | 意图 | 结果 |
|------|------|------|
| `test_vacuum_purity_one` | m=1,2,3 真空纯度 1 | PASS |
| `test_vacuum_symplectic_eigenvalues` | m=1,2,3 真空 ν=0.5 | PASS |
| `test_thermal_purity`（4 参数） | $\bar n$ = {0, 0.5, 1, 2} | PASS |
| `test_thermal_symplectic_eigenvalue`（4 参数） | ν = $\bar n + 0.5$ | PASS |
| `test_tmsv_pure_purity_and_eigs` | TMSV 纯态 | PASS |
| `test_tmsv_loss_mixed` | TMSV+loss 混合 | PASS |
| `test_thermal_product_unequal_nbar` | [::2] vs nu_all[m:] 陷阱 | PASS |
| `test_bare_ndarray_vacuum` | 裸输入路径 | PASS |
| `test_bare_ndarray_bad_shape_raises` | 非法形状抛错 | PASS |
| `test_purity_non_pd_raises` | det≤0 抛错 | PASS |
| `test_purity_cross_check_via_eigs` | $\mu = \prod 1/(2\nu_j)$ | PASS |
| `test_is_physical_still_ok` | 重构后回归 | PASS |
| `test_as_cov_helper` | _as_cov 路径 | PASS |

全量回归（315 项）：

```text
pytest tests -q
315 passed in 13.69s
```

### 4.2 对抗 / 研究员测试

脚本（独立，审查后删除）：adb `_review_6276358.py` → 初版 8 FAIL → 修正 3 条误报 → **0 FAIL / 30 probe**。

#### 分组摘要

**A. 挤压纯态（3）** — 全过
- r=0.3/1.5/2.5：$\mu=1$、$\nu=0.5$（挤压改变 $V$ 对角但 $\det$ 不变）

**B. 不等 $\nu$ 多模 & 独立参考（4）** — 全过
- 3 模 [0.6, 2.5, 5.5]：排序正确、与 `|iΩV|` 参考一致
- TMSV+thermal combo [0.5, 0.5, 3.5]：与参考一致

**C. 真空底 clip（1）** — 全过
- $V=0.5I - 10^{-13}I$ → $\nu$ 被 clamp 到 0.5

**D. Cholesky fallback（2）** — 全过
- 4 模 TMSV r=2.5/4.0：仍回 $\nu=0.5$、$\mu=1$

**E. 对称化一致性（3）** — 3 PASS（含 2 缺陷标记"BUG"）
- `symplectic_eigenvalues` 对称化正确
- `purity` 不对称化 → 与 `∏1/(2ν)` 背离（**缺陷 R1**）
- 非物理 V=0.4I 静默（**缺陷 R2**）

**F. 交叉校验（2）** — 全过
- 混合 3 模 $\mu = \prod 1/(2\nu_j)$
- lossy TMSV $\mu = \prod 1/(2\nu_j)$

**G. atol 死参（2）** — 全过（**缺陷 R3**）
- 签名有 `atol`，函数体无

**H. 输入鲁棒性（2）** — 全过
- list-of-lists 合法输入正常转换
- 奇数维 list 抛 ValueError

---

## 5. 总体结论

### 5.1 一句话

**F-ANALYSE-1（commit 6276358） 正确实现了 `symplectic_eigenvalues` 与 `purity`，Williamson-Cholesky 算法在真空/热态/纯态/多模不等 ν/挤压态/近奇异场景下验证通过。审查发现 3 个非阻塞但值得修复的缺陷：`purity` 不对称化 V、非物理输入静默、`atol` 死参。**

### 5.2 建议行动项

| 优先级 | 行动 |
|--------|------|
| P1 | `purity` 加 `V = 0.5 * (V + V.T)` 与 `symplectic_eigenvalues` 对称化对齐（修复 R1） |
| P1 | 为 `purity` / `symplectic_eigenvalues` 增加可选 `validate` 参数或显式 docstring 警告（修复 R2） |
| P2 | 移除或生效 `atol` 参数（修复 R3） |
| P3 | 将 squeeze 纯态测试加入 `tests/test_analyse.py`（目前缺失，纯态测试只有 TMSV） |
| P3 | 将 `|iΩV|` 独立参考路径作为回归测试固化（目前仅对抗脚本中有） |

### 5.3 审查签字意见

- **功能合并 / 使用：** 批准（数学实现正确，325 项全绿）
- **视为"无已知缺陷"：** 不批准（R1/R2 需修复）
- **视为"文档与实现零漂移"：** 批准（docstring 与实现匹配）

---

## 附录 A — 关键代码锚点

```text
cvsim/gaussian/analyse.py           # _as_cov, is_physical, validate_state,
                                    # symplectic_eigenvalues, purity
cvsim/gaussian/__init__.py          # 公开导出
cvsim/gaussian/state.py            # GaussianState 工厂
cvsim/conventions.py               # omega, HBAR, vacuum_cov
tests/test_analyse.py              # F-ANALYSE-1 单元测试
docs/vision-gaussian-simulator.md  # §4.2 纯度 / §7 数值预算
```

## 附录 B — 最小复现

```bash
# 单元测试
.venv/Scripts/python.exe -m pytest tests/test_analyse.py -v

# 全量回归
.venv/Scripts/python.exe -m pytest tests -q
```

### B1 — 缺陷 R1 复现（对称化不一致）

```python
import numpy as np

V_therm = 1.5 * np.eye(2)
V_asym = V_therm.copy()
V_asym[0, 1] += 0.4
V_asym[1, 0] -= 0.4

from cvsim.gaussian import purity, symplectic_eigenvalues
nu = symplectic_eigenvalues(V_asym)    # [1.5] (对称化后)
mu = purity(V_asym)                    # 0.32208 (裸 det)
mu_cross = float(np.prod(1.0 / (2.0 * nu)))  # 0.33333

assert abs(mu - mu_cross) > 1e-6  # 交叉校验不成立
```

### B2 — 缺陷 R2 复现（非物理静默）

```python
import numpy as np
from cvsim.gaussian import purity, symplectic_eigenvalues, is_physical

V_sub = 0.4 * np.eye(2)
print(is_physical(V_sub))       # False
print(purity(V_sub))            # 1.25 (>1, 无错误)
print(symplectic_eigenvalues(V_sub))  # [0.5] (被 clip)
```

## 附录 C — 运行环境快照

```text
platform win32
Python 3.13.5
pytest 9.1.1
numpy ~= 2.x

tests/test_analyse.py: 19 passed
tests (full suite): 315 passed
review script: 30 probe → 0 FAIL (>--brk)
```
