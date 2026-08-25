# 对抗式审查与测试报告：`07-29-phase1-interferometer-gates`

| 字段 | 内容 |
|------|------|
| 任务 ID | `phase1-interferometer-gates` |
| 标题 | Phase1: F-INTERFEROMETER + fourier/MZ gate set |
| 状态 | completed（2026-07-29） |
| 审查角色 | 研究员 / 对抗式审查 |
| 审查日期 | 2026-07-29 |
| 代码基线 | `cvsim/symplectic.py`, `cvsim/gaussian/gates.py`, `tests/test_interferometer.py` |

---

## 1. 任务完成了什么

本任务实现 vision 文档中的 **F-INTERFEROMETER** 与 **F-GATE-SET** 收尾能力：把被动线性光学幺正矩阵 \(U\in\mathrm{U}(m)\) 嵌入 xxpp 辛群，并补齐薄门别名与 mesh 分解/回放路径。

### 1.1 交付物清单

| 能力 | API | 位置 |
|------|-----|------|
| 幺正 → 辛嵌入 | `S_from_unitary(U)` | `cvsim/symplectic.py` |
| 幺正性检查 | `is_unitary` / `validate_unitary` | 同上 |
| 状态上施加干涉仪 | `interferometer` / `apply_interferometer` | `cvsim/gaussian/gates.py` |
| Fourier 门 | `fourier(state, mode)` ≡ `phase(π/2)` | 同上 |
| Mach–Zehnder | `mach_zehnder` + `S_mach_zehnder` | gates + symplectic |
| 2×2 BS 幺正 | `U_beamsplitter`, `embed_U_2mode` | symplectic |
| Mesh 分解 | `reck_decomposition`；`clements_decomposition` 为文档化别名 | symplectic |
| Mesh 合成 / 回放 | `compose_unitary_mesh`, `apply_mesh` | symplectic / gates |
| 导出 | `cvsim.gaussian` 与 `cvsim.symplectic`（含 `gaussian.symplectic` shim） | `__init__.py` 等 |
| 测试 | `tests/test_interferometer.py`（11 项） | tests |

### 1.2 数学模型（已实现）

被动变换 \(\vec a \mapsto U\vec a\) 的 xxpp 辛矩阵：

\[
S_U=\begin{pmatrix}\Re U&-\Im U\\\Im U&\Re U\end{pmatrix}
\]

与既有 `S_beamsplitter` 两模块布局一致。Gaussian 更新沿用：

\[
V\leftarrow S V S^\top,\quad \bar r\leftarrow S\bar r
\]

（被动情形位移 \(d=0\)）。

### 1.3 Mach–Zehnder 固定分解（代码为准）

```text
S = S_BS(π/4, 0) @ S_phase(φ, mode1) @ S_BS(θ, 0)
```

即状态顺序：**BS(θ) → phase(φ on mode1) → BS(π/4)**。

### 1.4 明确不在本任务范围（PRD Out）

- 一般 Gaussian CPTP \((X,Y)\) 通道（后续 F-CHANNEL-GENERAL）
- Circuit DSL 挂载（可选 follow-up）
- Compile 层合并多个 \(S\)（F-COMPILE）

### 1.5 对 PRD Acceptance 的对照

| # | 验收项 | 结果 |
|---|--------|------|
| 1 | `S_from_unitary(I)=I`；\(U\) 幺正时 \(S\) 辛 | **通过** |
| 2 | 非幺正 \(U\) 抛错 | **通过** |
| 3 | 库 BS 与其 2×2 \(U\) 嵌入一致 | **通过** |
| 4 | Haar \(U\)，\(m\in\{2,4,8\}\)：辛 + 真空纯度不变 | **通过** |
| 5 | 分解再合成回到 \(U\)（Frobenius） | **通过**（Reck；Clements 名为别名） |
| 6 | 相关 pytest 全绿 | **通过**（见 §3） |

**结论（完成度）：** Phase-1 *minimum*（`S_from_unitary` + `apply_interferometer`）与 *target*（分解 round-trip，Reck 作为 vision 允许的 alt）均已落地；`fourier` / `mach_zehnder` 已实现并导出。

---

## 2. 对抗式审查

审查策略：不默认信任已有单测，从**群同态 / 物理不变量 / 命名诚实性 / API 逃逸舱 / 数值极限 / 规格漂移**六个方向施压。

### 2.1 数学正确性（高置信）

| 检查 | 方法 | 结果 |
|------|------|------|
| 嵌入公式 | 与 \(\begin{psmallmatrix}\Re U&-\Im U\\\Im U&\Re U\end{psmallmatrix}\) 逐元对比 | 精确一致 |
| 辛条件 | \(S\Omega S^\top=\Omega\)，Haar \(m\le16\) | 通过（atol～1e-7～1e-8） |
| \(\det S=+1\) | 含 \(\det U=-1\) 的实对角幺正 | 恒为 +1 |
| 同态 | \(S(U_2U_1)=S(U_2)S(U_1)\) | max err \(\sim10^{-16}\) |
| 逆 | \(S(U^\dagger)=S(U)^{-1}\)；被动 \(S^\top S=I\) | max err \(\sim10^{-15}\) |
| 与 `S_phase` 符号 | \(U=(e^{i\theta})\) vs `S_phase` | 全角度一致 |
| 与 `S_beamsplitter` | 同一 \((\theta,\phi)\) 的 \(U\) 嵌入 | 一致 |
| 真空不动点 | 任意被动 \(U\)：\(V=\frac12 I,\bar r=0\) | 通过 |
| 总光子数 | \(\sum_i\langle n_i\rangle\) 在干涉仪下守恒 | \(\|\Delta n\|\sim10^{-15}\) |
| 纯度 / \(\det V\) | 多次随机 \(U\) 复合 | 保持 |
| Fourier | \((x,p)\mapsto(-p,x)\)；\(F^2\) 中心反演；\(F^4=\mathrm{id}\) | 通过 |
| 模式定域 | `fourier` 只作用目标模 | 通过 |
| Mesh 等价 | `apply_mesh(decomp(U))` ≡ `interferometer(U)` | \(m\le8\)，20×Haar 通过 |

**判定：** 核心嵌入与门语义在 xxpp、\(\hbar=1\) 约定下正确，未发现会破坏 Gaussian 物理性的实现级 bug。

### 2.2 分解算法审查

**实现：** 左乘剥离的 **Reck 三角分解**（`u2` 两模幺正 + 对角 `phase`），状态施加顺序为「先对角相位，再逆序两模门」，与 `compose_unitary_mesh`（\(U=\mathrm{Op}_n\cdots\mathrm{Op}_1\)）一致。

| 检查 | 结果 |
|------|------|
| Round-trip \(\|U_{\mathrm{rec}}-U\|_F\) | \(m\le12\) 典型 \(10^{-15}\) |
| \(m=1\) 纯相位 | 正确 |
| 对角相位幺正 | 正确 |
| 极端 BS \(\theta=\pi/2\) | 正确 |
| 非幺正输入 | `ValueError` |
| `u2` 计数 | \(m(m-1)/2\)，符合 Reck |
| `clements_decomposition is reck` | 行为完全相同；docstring **明确写明** Phase-1 用 Reck 别名 |

**对抗观点：**

1. **命名债务（中）：** 公共名 `clements_decomposition` 会让调用方以为得到矩形 Clements 网格（固定光学深度、近邻 BS 布局）。实际是 Reck 三角网。文档诚实，但 **API 名偏乐观**，后续若有人按 Clements 硬件布局编译会静默做错架构假设。
2. **原生门粒度（低）：** 分解输出大量 `("u2", i, j, U2)`，不是 `(bs, phase)` 原子序列。`apply_mesh` 对 `u2` 走 `S_from_unitary`；对 `bs`/`phase` 另有路径。功能正确，但离“编译到库内命名门”仍差一步。
3. **数值路径（低）：** 剥离用列归一化构造 \(T\)，未看到显式 pivot 失败；在 Haar / 近对角 / \(m=12\) 下残差仍机精级。尚未用病理条件数矩阵做正式稳定性证明（工程上可接受）。

### 2.3 规格 / 文档漂移

| 来源 | 表述 | 实现 | 严重度 |
|------|------|------|--------|
| vision F-GATE-SET | MZ = `phase·BS·phase·BS` | `BS(θ)·R(φ)·BS(π/4)`（单内相位，末级固定 50:50） | **中（文档）** |
| PRD / 代码 docstring | “documented BS+phase composition” | 与代码一致，单测按代码分解断言 | 可接受 |
| vision F-INTERFEROMETER | Clements preferred；Reck acceptable | Reck + 别名 | **低–中**（合规但名实不完全一致） |
| PRD Out | Circuit DSL optional | `GaussianCircuit` **无** interferometer/fourier/MZ | 符合 Out，但是产品缺口 |
| vision Phase1 exit | tutorial “interferometer + loss + homodyne” | 本任务未交付教程 | **范围外 / 跟踪项** |

**MZ 对抗说明：**  
实现与 *自身文档字符串及单测* 自洽，也与“可调第一 BS + 内臂相位 + 50:50 合束”的常见 MZ 变体一致；但 **不等于** vision 表中的双 phase 四因子模板，也不等于双 50:50 + 单相位的教科书特例（对抗测 D1：`match_textbook_50_50=False`）。  
对研究者：调用前必须读 `S_mach_zehnder` 文档，不能凭名字假设。

### 2.4 API 与鲁棒性

| 点 | 行为 | 评价 |
|----|------|------|
| 默认校验幺正 | 非幺正 / 非方阵 → `ValueError` | 好 |
| `validate_u=False` | 允许非辛嵌入；真空 `det V` 仍可能“看起来正常” | 逃逸舱必要，但 **静默物理破坏风险**；应仅限内部信任路径 |
| 近幺正噪声 \(10^{-12}\) | 接受 | 合理 |
| 偏差 \(10^{-4}\) | 拒绝 | 合理 |
| 模式越界 / MZ 同模 | 抛错 | 好 |
| 实正交 \(U\)（float） | 接受且辛 | 好 |
| `apply_interferometer is interferometer` | 是 | API 清晰 |
| 顶层 `cvsim.gaussian` 是否导出 `S_from_unitary` | **否**（在 `cvsim.symplectic`） | 与 vision “gaussian / symplectic 公开”字面略窄，但可发现 |

### 2.5 设计优点

1. **约定不漂移：** \(S_U\) 与历史 `S_beamsplitter` 共用同一嵌入，避免“库 BS vs 干涉仪”双栈。
2. **信任边界清楚：** 命名门 `validate=False`；用户 `U` 默认严格校验。
3. **分解与施加顺序写进 docstring**，并有 `compose_unitary_mesh` 可独立验证——可测试性好。
4. **被动层可 O(m³) 一次乘**，符合 vision performance note；mesh 路径为可编译性预留。
5. **shim** `cvsim.gaussian.symplectic` 全量再导出，降低迁移成本。

### 2.6 缺陷与风险登记

| ID | 级别 | 描述 | 建议 |
|----|------|------|------|
| R1 | 中 | `clements_decomposition` 名实为 Reck | 保留别名同时导出 `reck_decomposition`（已有）；或改名/警告；真正 Clements 单独立项 |
| R2 | 中 | vision MZ 文案与实现分解不一致 | 回写 vision 为代码分解，或改实现并对齐单测 |
| R3 | 低 | Circuit DSL 未挂载 interferometer/fourier/MZ | 可选 follow-up：`GaussianCircuit.interferometer(U)` 等 |
| R4 | 低 | `u2` 未进一步拆成 BS+phase | 若要对片上相移器+BS 网表，需要第二级参数化 |
| R5 | 低 | `validate_u=False` 可产生非辛 \(S\) | 文档标明 danger；或 debug 模式 warn |
| R6 | 信息 | 全局相位 \(e^{i\phi}U\) 在 CV 模图景下 **不是** no-op（集体相位） | 文档一句即可，避免量子信息直觉误用 |
| R7 | 信息 | 本任务无新教程/demo | 纳入 Phase1 exit 总验收时补 |

**未发现：** 辛破坏性静默错误、光子数漏计、分解顺序反号、Fourier 符号与 `S_phase` 冲突等 *blocking* 缺陷。

### 2.7 对抗式结论

| 维度 | 评分（1–5） | 说明 |
|------|-------------|------|
| 数学正确性 | 5 | 同态、辛、不变量全面成立 |
| 与 PRD 符合度 | 4.5 | 验收项全过；Clements 为合法 alt |
| 与 vision 符合度 | 4 | 功能齐；MZ 文案与 Clements 命名有漂移 |
| API 完成度 | 4 | 核心+导出齐；DSL/教程未做（部分 Out） |
| 测试充分度（原库） | 4 | 主路径覆盖好；缺大 \(m\)、同态、光子守恒等 |
| 可维护性 | 4.5 | 文档串与分解顺序清楚 |
| **总评** | **通过（有文档/命名债）** | 可合并使用；建议清 R1/R2 |

---

## 3. 测试报告

### 3.1 原有回归

```text
pytest tests/test_interferometer.py -v
11 passed
```

| 用例 | 意图 | 结果 |
|------|------|------|
| `test_S_from_unitary_identity` | \(S(I)=I\) 且辛 | PASS |
| `test_S_from_unitary_rejects_non_unitary` | 非幺正拒绝 | PASS |
| `test_S_from_unitary_matches_beamsplitter` | BS 约定对齐 | PASS |
| `test_S_from_unitary_matches_S_phase_sign` | 相位符号 | PASS |
| `test_haar_unitary_symplectic_and_purity` | Haar m=2,4,8 + 真空 | PASS |
| `test_reck_roundtrip` | Reck/Clements 别名 round-trip | PASS |
| `test_apply_mesh_matches_interferometer` | mesh≡整模 \(S_U\) | PASS |
| `test_tmsv_plus_balanced_bs` | TMSV+50:50 | PASS |
| `test_fourier_four_times_identity` | \(F^4=\mathrm{id}\) | PASS |
| `test_mach_zehnder_matches_manual` | MZ vs 手工门序列 | PASS |
| `test_interferometer_shape_mismatch` | 形状错误 | PASS |

扩展回归（相邻模块，防回归）：

```text
pytest tests/test_interferometer.py \
       tests/test_symplectic_core.py \
       tests/test_b1_gaussian_gates.py \
       tests/test_gaussian_circuit.py -q
51 passed
```

### 3.2 对抗 / 研究员测试

脚本：`tests/_adversarial_interferometer_review.py`  
运行：`PYTHONPATH=. py -3 tests/_adversarial_interferometer_review.py`

```text
TOTAL: 39 PASS, 0 FAIL / 39
```

#### 分组摘要

**A. 数学与约定（7）** — 全过  
`det S=1`、同态、逆与正交、真空不动点、总光子守恒、Fourier 象限映射、\(F^2\)。

**B. 分解（6）** — 全过  
对角/极端 BS/多 Haar+mesh、`clements` 别名文档、非幺正拒绝、\(m=1\)。  
量化：`m∈{3,4,6,8}`×20 Haar，max Frobenius err \(\approx1.8\times10^{-15}\)。

**C. API 鲁棒性（8）** — 全过  
近幺正、明显非幺正、`validate_u=False` 逃逸、矩形、模式错误、实 \(U\)、未知 mesh op、别名身份。

**D. 门语义（4）** — 全过  
MZ 与代码文档分解一致；确认 **不等于** 双 50:50 教科书默认；Fourier 定域；矩阵乘顺序 `S3@S2@S1`。

**E. 物理压力（4）** — 全过  
\(m=16\) Haar 保物理与 \(\det V\)；20 次随机 \(U\) 保纯度；TMSV+BS50 两模 \(\langle n\rangle\) 平衡；block 公式。

**F. 导出（2）** — 全过  
`cvsim.symplectic` / `cvsim.gaussian` 必需符号齐全；`S_from_unitary` 仅在 symplectic 侧（记录为观察项）。

**G. Bug hunt（8）** — 全过  
Reck 残差、相位全范围、第三模隔离、`bs/phase` mesh 路径、全局相位观察、dtype、\(\det U=-1\)、compose/apply 顺序。

#### 额外手测快照

| 项 | 结果 |
|----|------|
| Reck `u2` 计数 | \(m=2..8\) 均为 \(m(m-1)/2\) |
| \(m=12\) 分解+合成 | err \(\sim1.8\times10^{-15}\)，耗时 \(\sim3\,\mathrm{ms}\)（本机） |
| `GaussianCircuit` 含 interferometer/fourier/MZ | **False**（预期 Out） |
| 近对角微扰幺正 round-trip | 机精级 |

### 3.3 原测试缺口（审查后仍建议补的单测）

原 `test_interferometer.py` 质量良好，但作为长期回归建议补充：

1. **同态** `S(U2@U1)==S(U2)@S(U1)`  
2. **总光子数守恒**（非真空）  
3. **`S(U).T @ S(U) == I`**（被动正交）  
4. **`det S == 1`**  
5. **Fourier 象限映射**（比只测 \(F^4\) 更强）  
6. **大 m（如 16）烟雾** + 分解残差阈值  
7. **显式断言** `clements_decomposition` docstring/别名行为（防未来误改成真·假 Clements 却无测）

---

## 4. 总体结论

### 4.1 一句话

**`07-29-phase1-interferometer-gates` 正确实现了被动干涉仪的辛嵌入、状态施加、Fourier/MZ 薄门，以及可 round-trip 的 Reck mesh（以 `clements_decomposition` 为文档化别名）；数学与物理不变量在对抗测试下稳定，PRD 验收项全部满足。主要剩余问题是命名/vision 文档漂移与 DSL/教程未接线，不是正确性 blocker。**

### 4.2 建议行动项

| 优先级 | 行动 |
|--------|------|
| P1 | 修订 `docs/vision-gaussian-simulator.md` 中 MZ 分解与 Clements/Reck 现状，消除与代码冲突 |
| P2 | 真·Clements 矩形分解单独立项时，**不要**静默替换当前别名语义，或保留 `reck_decomposition` 并版本化 |
| P2 | Circuit DSL：`interferometer` / `fourier` / `mach_zehnder` |
| P3 | 将 §3.3 对抗用例精简并入 `tests/test_interferometer.py` |
| P3 | Phase1 总出口：补 “interferometer + loss + homodyne” 教程 |

### 4.3 审查签字意见

- **功能合并 / 使用：** 批准  
- **视为“真 Clements 硬件编译已就绪”：** 不批准（仅 Reck 别名）  
- **视为“vision 文档已与代码零漂移”：** 不批准（MZ 文案）  

---

## 附录 A — 关键代码锚点

```text
cvsim/symplectic.py
  is_unitary, validate_unitary
  S_from_unitary
  U_beamsplitter, embed_U_2mode
  reck_decomposition, clements_decomposition, compose_unitary_mesh
  S_mach_zehnder

cvsim/gaussian/gates.py
  fourier, mach_zehnder, interferometer, apply_interferometer, apply_mesh

cvsim/gaussian/__init__.py          # 门导出
cvsim/gaussian/symplectic.py        # shim
tests/test_interferometer.py
tests/_adversarial_interferometer_review.py
.trellis/tasks/archive/2026-07/07-29-phase1-interferometer-gates/prd.md
docs/vision-gaussian-simulator.md   # F-GATE-SET / F-INTERFEROMETER
```

## 附录 B — 最小复现

```bash
# 单元测试
PYTHONPATH=. py -3 -m pytest tests/test_interferometer.py -v

# 对抗套件
PYTHONPATH=. py -3 tests/_adversarial_interferometer_review.py

# 研究员快速检查
PYTHONPATH=. py -3 - <<'PY'
import numpy as np
from cvsim.symplectic import S_from_unitary, is_symplectic, reck_decomposition, compose_unitary_mesh
from cvsim.gaussian import GaussianState, interferometer, fourier, det_cov

U = np.eye(2, dtype=complex)
assert np.allclose(S_from_unitary(U), np.eye(4))
rng = np.random.default_rng(0)
z = rng.normal(size=(4,4)) + 1j*rng.normal(size=(4,4))
q, r = np.linalg.qr(z)
U = q * (np.diag(r)/np.abs(np.diag(r)))
assert is_symplectic(S_from_unitary(U))
assert np.linalg.norm(compose_unitary_mesh(4, reck_decomposition(U)) - U) < 1e-10
st = interferometer(GaussianState.vacuum(4), U)
assert abs(det_cov(st) - (0.25)**4) < 1e-12
st2 = fourier(GaussianState.displaced_squeezed(0.3+0.1j, 0.2), 0)
print("ok", st2.nmode)
PY
```
