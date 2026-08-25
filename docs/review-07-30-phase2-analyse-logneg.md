# Adversarial Review: F-ANALYSE-3 `log_negativity`

**审查范围**: 最近两次 git 提交  
**提交**: `d53af23` (feat) + `f7dfd7d` (chore)  
**日期**: 2026-07-30  
**审查人**: AI Researcher (独立验证)  
**方法**: 代码审查 + 45 项单元测试 + 7 组独立验证实验

---

## §1 提交概览

| 提交 | 类型 | 变更 | 文件数 |
|------|------|------|--------|
| `d53af23` | feat(gaussian) | F-ANALYSE-3 log_negativity + vision 0.1.3 | 8 (+204, -2) |
| `f7dfd7d` | chore(task) | archive 07-30-phase2-analyse-logneg | 4 (+2, -2) |

**核心变更**: `cvsim/gaussian/analyse.py` 新增 `log_negativity()` + 两个内部辅助函数。

---

## §2 数学正确性审查

### 2.1 Partial Transpose 实现

**代码**: `_partial_transpose_cov` 对 `modes_A` 中每个 mode 的 p-quadrature 翻号 (xxpp ordering: index `nmode + k`)。

**物理**: 在 xxpp 排序下，对 mode k 做部分转置 ⟺ 翻 p_k → -p_k，即 `V ↦ Λ V Λ`，`Λ = diag(1,...,1,-1,...,-1)`。

**判定**: **正确**。等价于 Simon (2000) / Vidal & Werner (2002) 的 PT 定义。

### 2.2 Raw Symplectic Eigenvalues

**代码**: `_symplectic_eigenvalues_raw` 使用 `eigvals(iΩV)` 直接求特征值，**不做 vacuum-floor clip**。

**关键点**: PT 后的 V' 通常非正定（有负辛本征值 < 1/2），Cholesky-Williamson 路径不适用。直接用 `|eig(iΩV')|` 是正确选择。

**判定**: **正确**。`[::2]` 取法与 `symplectic_eigenvalues` 一致（每 ±pair 取一个）。

### 2.3 Log-Negativity 公式

**实现**: `E_N = Σ_j max{0, -log₂(2ν̃_j)}`

**文献对照**:
- Vidal & Werner (2002): E_N = Σ max{0, -log₂(2ν̃_j)} ✓
- Weedbrook RMP §III.D: 一致 ✓
- Adesso et al.: 一致 ✓

**TMSV freeze**: E_N = -log₂(e^{-2r}) = 2r/ln(2)。代码 docstring 明确记录此公式。

**判定**: **正确**。

### 2.4 Vision 文档同步

Vision v0.1.3 已将公式从 `max{0, -Σ_j log₂(2ν̃_j)}` 修正为 `Σ_j max{0, -log₂(2ν̃_j)}`，并附 amendment 说明。

**判定**: **正确且一致**。

---

## §3 独立验证实验结果

### 3.1 测试环境

- Python 3.13.5, numpy + scipy
- `PYTHONPATH=.` 加载 cvsim
- 45 项项目单元测试 + 7 组独立验证

### 3.2 项目测试: **45/45 PASS**

```
tests/test_analyse.py — 45 passed in 0.46s
```

包含:
- 真空 / 热态 / TMSV / 混合态纯度与辛本征值
- R1-R3 review 修复回归测试
- F-ANALYSE-2 entropy_vn + partial_trace
- F-ANALYSE-3 log_negativity (9 项专属测试)

### 3.3 独立验证: **7/7 PASS**

| # | 实验 | 结果 |
|---|------|------|
| 1 | TMSV E_N vs 解析 E_N = 2r/ln(2)，r ∈ {0.3, 0.6, 1.0, 1.5} | max error = 3.2e-14 |
| 2 | 可分态 (热态积 + 真空) → E_N = 0 | exact 0.0 |
| 3 | 二分对称性 E_N(A\|B) = E_N(B\|A) | 精确相等 |
| 4 | 四模态 (一对TMSV + 两真空)，切割检测 | E_N(entangled)=1.731, E_N(vacuum)≈0 |
| 5 | 单调性: E_N 随 r 严格递增 | r: 0.2→1.0, E_N: 0.58→2.89 |
| 6 | 边界: 空集/全集 → E_N = 0 | exact 0.0 |
| 7 | 与 von Neumann 熵关系: S(A) = S(B) (纯态) | 精确相等; E_N > S(A) 符合 CV 物理 |

---

## §4 代码质量审查

### 4.1 输入验证

| 检查 | 实现 | 评价 |
|------|------|------|
| 类型检查 | `isinstance(state, GaussianState)` → TypeError | ✓ 正确 |
| 模式索引越界 | `0 <= k < m` → IndexError | ✓ 正确 |
| 空集/全集 | 短路返回 0.0 | ✓ 正确 |
| int/Iterable 统一 | `isinstance(modes_A, (int, np.integer))` | ✓ 正确 |
| 去重排序 | `sorted({int(k) for k in modes_A})` | ✓ 正确 |

### 4.2 数值安全

| 措施 | 实现 | 评价 |
|------|------|------|
| V 对称化 | `V = 0.5 * (V + V.T)` (两处) | ✓ |
| log2(0) 防护 | `np.maximum(2.0 * nu, 1e-300)` | ✓ (见 §5.2) |
| float64 精度 | 全程 float64 | ✓ |

### 4.3 API 一致性

- 与 `partial_trace` 模式: 相同 `modes_A` 参数模式 (int | Iterable[int])。✓
- 与 `entropy_vn`/`purity` 区别: `log_negativity` **仅接受** `GaussianState`（不接受裸 ndarray）。设计合理 — PT 需要知道 `nmode` 以定位 xxpp 索引。✓
- 导出: `__init__.py` 中 `__all__` 包含 `"log_negativity"`。✓

---

## §5 发现与建议

### 5.1 【低-信息】PT 辛本征值算法的数值精度上限未标注

**位置**: `_symplectic_eigenvalues_raw`

**观察**: 使用 `eigvals(1j * Ω @ V)` 直接求特征值。对于病态 PT V（极强纠缠 + 强损耗 → PT 接近半正定边界），`eigvals` 条件数可能较差。

**当前测试覆盖**: r ≤ 1.5, 无损耗。未测试极端条件。

**建议**: 补充一个 high-loss TMSV 回归测试 (如 η=0.01, r=2.0)，锁定当前数值结果作为 baseline。

**严重度**: 低。教学工具场景下不会遇到。

### 5.2 【低】`1e-300` guard 值文档缺失

**位置**: `log_negativity` L343

**观察**: `np.maximum(2.0 * nu, 1e-300)` 防止 `log2(0)`。若 ν̃ 理论为零，`log2(1e-300) ≈ -997`，但实际中 PT 的 ν̃ 不会精确为零。

**建议**: docstring 补充 "ν̃ = 0 未物理实现，guard 值仅防浮点异常"。

**严重度**: 低。非 bug。

### 5.3 【中】Docstring "Note" 段措辞可改进

**位置**: `log_negativity` docstring L316-320

**原文**:
> "vision §4.2 writes max{0, -Σ_j log₂(2ν̃_j)} over *all* j; that literal sum cancels on TMSV"

**问题**: 读者可能误读为 "vision 公式是错的"。实际上 vision v0.1.3 已修正公式。该 Note 应描述为 **历史修正**，而非 "两种等价写法"。

**建议修改为**:
> "Prior to vision v0.1.3, the formula was written as max{0, -Σ_j log₂(2ν̃_j)} (max over the full sum). That form cancels on TMSV and is incorrect for general multimode states. The implemented per-term form Σ_j max{0, -log₂(2ν̃_j)} is the standard PPT log-negativity (Weedbrook/Adesso/Vidal-Werner)."

**严重度**: 中。文档一致性，不影响数值正确性。Vision 已修正，仅 docstring 滞后。

### 5.4 【信息】`log_negativity` 不支持裸 ndarray

**观察**: 与 `purity`/`entropy_vn` 不同，`log_negativity` 要求 `GaussianState`（不接受裸 `V`）。

**原因**: PT 需要 `nmode` 以确定 xxpp 索引偏移。裸 ndarray 无法推断 nmode（`V.shape[0]//2` 可以，但 design choice 是要求显式 state）。

**判定**: 设计合理。无需修改。

---

## §6 总体评价

| 维度 | 评分 | 说明 |
|------|------|------|
| 数学正确性 | **A** | PT + raw symplectic eigs + PPT log-neg 公式均正确 |
| 代码质量 | **A** | 输入验证完备，数值安全措施到位，API 一致 |
| 测试覆盖 | **A** | 45 项单元 + 7 组独立验证，覆盖解析/边界/对称/单调 |
| 文档一致性 | **B+** | Vision 已同步; docstring Note 段措辞可改进 |
| 数值鲁棒性 | **A-** | 常规场景优秀; 极端条件未标注精度上限 |

**结论**: **通过审查**。`log_negativity` 实现正确、测试充分、API 设计一致。仅有 docstring Note 段措辞需要小幅改进（§5.3），无功能性 bug。

---

*审查日期: 2026-07-30*  
*验证脚本: `review_f_analyse_3_verify.py`*  
*测试套件: 45 passed (test_analyse.py) + 7/7 independent verification*
