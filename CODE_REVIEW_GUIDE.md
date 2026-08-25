# CV Photonic Notes — Code Review Guide

> 面向团队内部代码审查的标准与最佳实践。本指南假设审查者已理解 CV 量子光学基础，侧重工程实践和物理正确性。

---

## 1. 审查流程

### 1.1 审查阈值

| 变更规模 | 审查要求 |
|----------|----------|
| 文档/注释修正 | 自查后可合并 |
| < 50 行逻辑变更 | 至少 1 人审查 |
| 50–200 行逻辑变更 | 至少 1 人审查 + 物理正确性检查 |
| > 200 行/新增子模块 | 至少 2 人审查 + 跨表示一致性测试 |

### 1.2 提交前自查清单

在请求审查之前，确认以下项：

```
[ ] 所有测试通过：python -m pytest tests/ -q
[ ] Ruff 无告警：ruff check cvsim/
[ ] 没有 print() 调试残余
[ ] 新增公共 API 有完整 docstring（含参数、返回、异常）
[ ] 物理公式在 docstring 中标注（LaTeX/Unicode）
[ ] 如果改了公共 API，更新了相应的 __init__.py 导出
[ ] 没有引入依赖（除非 RFC 批准）
```

---

## 2. 物理正确性审查标准

这比风格检查更重要——一个计算错误的模拟器比没有模拟器更危险。

### 2.1 必备验证

每个涉及数值计算的 PR 必须证明：

1. **真空回归**：所有门/通道作用于真空后，纯态的 `det(V) = (1/4)^m`  
   ```python
   from cvsim.gaussian import GaussianState, det_cov
   st = some_gate(GaussianState.vacuum(1))
   np.testing.assert_allclose(det_cov(st), 0.25, atol=1e-12)
   ```

2. **辛性保持**（Gaussian 门）：  
   ```python
   from cvsim.symplectic import is_symplectic
   assert is_symplectic(some_symplectic_matrix)
   ```

3. **CPTP 保持**（Gaussian 通道）：  
   ```python
   from cvsim.gaussian.channels import is_cp_channel
   assert is_cp_channel(X, Y)
   ```

### 2.2 已知解析公式对照

审查时必须要求作者提供至少一个解析对照：

| 物理量 | 解析公式 | 测试断言 |
|--------|----------|----------|
| 压缩真空 ⟨n⟩ | sinh² r | `assert_allclose(mean_photon(st), sinh(r)**2)` |
| TMSV 纠缠熵 | cosh²r log₂(cosh²r) − sinh²r log₂(sinh²r) | 与 entropy_vn 对比 |
| 相干态 ⟨n⟩ | \|α\|² | `assert_allclose(mean_photon(st), abs(alpha)**2)` |
| 热态 V | (2n̄+1)I/2 | `assert_allclose(st.V, 0.5*(2*nbar+1)*eye(2))` |
| BS 变换 | 辛嵌入 S = [[Re U, -Im U], [Im U, Re U]] | 与 S_from_unitary 一致 |
| homodyne var (真空) | 0.5（任意角度） | `assert_allclose(homodyne_var(vac, 0, theta), 0.5)` |

### 2.3 跨表示一致性

Fock/Gaussian/Bosonic 三种表示必须对同一物理场景给出一致结果。例如：

```python
# Gaussian 和 Bosonic 的 Wigner 函数在单分量时必须一致
g = squeeze(GaussianState.vacuum(1), 0.5)
b = BosonicState.from_gaussian(g)
for x, p in [(0,0), (1.0, 0.5), (-0.5, 1.0)]:
    assert abs(wigner_bosonic(b, x, p) - wigner_gaussian(g, x, p)) < 1e-12
```

### 2.4 数值稳定性红牌

以下情况直接打回：

- **不做对称化**：`V = 0.5 * (V + V.T)` 必须在非精确运算后调用
- **浮点等值比较**：不使用 `atol` 的 `np.testing.assert_*`
- **行列式为零的矩阵求逆**：未检查 `det > 0`
- **mode 参数越界**：未做 `0 <= mode < nmode` 检查
- **复数 mean 处理**：rbar 可能是复数（Wigner 函数中），不能假设 `rbar = rbar.real` 除非显式需要

---

## 3. 代码风格规范

### 3.1 数值约定（不可变）

- **ħ = 1**（全局约定）
- **Quadrature order**: xxpp，即 `r = (x₁, ..., x_m, p₁, ..., p_m)^T`
- **辛形式**: Ω = `[[0, I], [-I, 0]]`  
- **真空协方差**: V = I/2（不是 I，不是 ħI/2）

这些约定通过 `cvsim.conventions` 统一管理。**禁止在模块内硬编码**这些值。

### 3.2 命名约定

```python
# 状态变量
st: GaussianState   # 高斯态
fst: FockState       # Fock 纯态
rho: FockDensity     # Fock 密度矩阵
bst: BosonicState    # 玻色态（分量叠加）

# 物理量
V: np.ndarray        # 协方差矩阵 (2m, 2m)
rbar: np.ndarray     # 位移矢量 (2m,)
S: np.ndarray        # 辛矩阵 (2m, 2m)
d: np.ndarray        # 位移矢量 (2m,)

# 参数
r: float             # 压缩参数
nbar: float          # 平均光子数
alpha: complex       # 相干振幅
theta, phi: float    # 角度参数
T: float             # 透射率 (0 ≤ T ≤ 1)
m: int               # 模数
nmode: int           # 模数（与 m 等价，优先使用）
```

### 3.3 导入顺序

```python
# 1. 标准库
from __future__ import annotations

# 2. 第三方
import numpy as np
from scipy.special import ...

# 3. cvsim 内部 — 始终用完整路径
from cvsim.conventions import omega
from cvsim.gaussian.state import GaussianState
```

禁止使用相对导入（`from .state import ...`）。

### 3.4 类型提示

- **公共函数必须有返回类型注解**（当前已 100% 覆盖）
- 可选参数使用 `*` 分隔：`def f(state, *, atol: float = 1e-8)`
- 复杂类型用 `from __future__ import annotations` + PEP 604 联合：`FockState | FockDensity`

---

## 4. 测试标准

### 4.1 测试结构

```python
"""模块简称: 简短描述。"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.xxx import ...

# ---------------------------------------------------------------------------
# 1. Smoke tests — 基本功能不崩溃
# ---------------------------------------------------------------------------

def test_vacuum_creation():
    ...

# ---------------------------------------------------------------------------
# 2. Physics correctness — 与解析公式对照
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("r", [0.1, 0.3, 0.6, 1.0])
def test_squeezing_nbar_vs_analytic(r):
    ...

# ---------------------------------------------------------------------------
# 3. Error paths — 无效输入正确处理
# ---------------------------------------------------------------------------

def test_invalid_mode_raises():
    with pytest.raises(IndexError):
        ...

# ---------------------------------------------------------------------------
# 4. Edge cases — 极端/退化参数
# ---------------------------------------------------------------------------

def test_zero_squeezing_identity():
    ...
```

### 4.2 测试命名

```
test_<what>_<condition>
```

正确：`test_vacuum_factory()`, `test_squeeze_purity_r0()`, `test_loss_channel_cptp()`
错误：`test1()`, `check()`, `verify_something()`

### 4.3 容差选择

```python
atol=1e-12   # 解析公式对照——严格
atol=1e-10   # 经过几次矩阵运算后——适中
atol=1e-8    # 随机生成/数值分解——宽松
```

不要在测试中混用容差。如果某个测试需要宽松容差，在注释中说明原因。

---

## 5. 反模式与常见错误

### 5.1 ❌ 硬编码物理常数

```python
# 错误
V = np.eye(2) / 2  # 隐含 ħ=1

# 正确
from cvsim.conventions import vacuum_cov
V = vacuum_cov(1)
```

### 5.2 ❌ 忽略对称化

```python
# 错误
V_new = S @ V @ S.T  # 浮点误差可能破坏对称性

# 正确
V_new = 0.5 * (S @ V @ S.T + (S @ V @ S.T).T)
```

### 5.3 ❌ 循环依赖

```python
# 错误：在 GaussianState 中直接 import cvsim.gaussian.analyse
# 正确：延迟导入
def is_physical(self):
    from cvsim.gaussian.analyse import is_physical as _ip
    return _ip(self)
```

### 5.4 ❌ 静默类型转换

```python
# 错误：可能引入浮点误差的方向性偏差
V = np.array(user_input)  # dtype 可能是 float32

# 正确
V = np.asarray(user_input, dtype=float)  # 确保 float64
```

### 5.5 ❌ 魔法数字

```python
# 错误
if det < 1e-15:  # 这个阈值是哪来的？

# 正确
if det <= 0:     # 行列式必须严格正数
    raise ValueError(f"det(2V) must be > 0, got {det2v}")
```

### 5.6 ❌ 缺少 mode 边界检查

```python
# 错误
def squeeze(m, r, mode):
    S = np.eye(2*m)
    S[mode, mode] = np.exp(-r)  # mode >= m 时静默越界

# 正确
def squeeze(m, r, mode):
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range")
    ...
```

---

## 6. 架构决策记录

### 6.1 为什么三个表示不合并？

- **Gaussian**: 精确、快速、有限门集（仅高斯门）
- **Fock**: 通用门集、但截断近似、指数复杂度
- **Bosonic**: 高斯分量的线性组合，处理猫态/GKP 等非高斯态

三者在物理上是同一希尔伯特空间的不同基/截断。保持独立实现可防止一种表示的 bug 污染另一种。

### 6.2 为什么 `cvsim.symplectic` 是共享层？

Gaussian 和 Bosonic 都依赖辛矩阵运算。提取到 `cvsim.symplectic` 避免了两份实现分歧的风险。

```python
# 始终从顶层导入辛矩阵
from cvsim.symplectic import S_squeeze  # ✅ 推荐

# 不要从兼容 shim 导入（可能在未来版本移除）
from cvsim.gaussian.symplectic import S_squeeze  # ❌ 不推荐
```

### 6.3 依赖最小化原则

cvsim 的依赖锁定为 `numpy` + `scipy`。**任何新依赖都需要 RFC 批准**，审查时需考虑：

- 是否真的必要？（能否用 numpy/scipy 实现？）
- 维护负担 vs 功能收益
- 是否会影响安装便利性（pip install 一键安装是目标）

---

## 7. PR 描述模板

```markdown
## Summary
<!-- 一句话描述做了什么 -->

## Physics validation
- [ ] 真空回归测试通过
- [ ] 辛性/CPTP 保持（如适用）
- [ ] 已有解析公式对照通过
- [ ] 跨表示一致性通过（如适用）

## Test coverage
- [ ] 新增测试覆盖 happy path + error path + edge cases
- [ ] `pytest tests/ -q` 全部通过
- [ ] 无 docstring 警告

## Breaking changes
<!-- 如果改变公共 API，在此说明迁移路径 -->
```

---

## 8. 工具链速查

```bash
# 运行所有测试
python -m pytest tests/ -q

# 运行特定测试文件 + 详细输出
python -m pytest tests/test_gaussian_circuit.py -v

# 只运行标记为 "slow" 的测试
python -m pytest tests/ -m slow

# 代码风格检查
ruff check cvsim/

# 自动修复
ruff check --fix cvsim/

# 类型检查
mypy cvsim/

# 覆盖率报���
python -m pytest tests/ --cov=cvsim --cov-report=term-missing
```

---

> **审核哲学**: "如果一段代码需要审查者用纸笔推导才能确认正确性，那它应该附带推导过程。"  
> — 在 docstring 或 PR 评论中写出关键推导步骤，不要假设审查者能心算。

*最后更新: 2026-07-30*
