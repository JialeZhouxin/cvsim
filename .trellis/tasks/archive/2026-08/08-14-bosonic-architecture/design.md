# Bosonic 生产级模拟器 — 架构设计（grill A1–A12 锁定，2026-08-14）

> 战略层已锁（vision-bosonic-simulator.md + ADR-0005，Q1–Q13）：本文件只锁**架构层**。
> 与 vision 冲突时：本文件是设计层细化；改物理语义必须先改 vision。

## 0. 决策总表

| # | 决策 | 锁定 |
|---|------|------|
| A1 | 组件数据结构 = dataclass 列表（现状即终态），不上张量引擎 | ✅ |
| A2 | 门执行 = 逐组件循环 + 函数式（返回新态），签名 1:1 对齐 Gaussian 命名集 | ✅ |
| A3 | 归一化 = Σ_k w_k = 1（复数求和，实 = 1）；`weight_sum(state)` 公共 API；`is_hermitian` 共轭对闭合校验 | ✅ |
| A4 | 测量全并入 `measure.py`（homodyne/heterodyne/threshold 同仓），`observables.py` 只留矩 → **amend vision §3 模块树** | ✅ |
| A5 | B3 精确采样 = **CDF 网格反演**（复权重混合无正概率权重，拒绝采样不可行） | ✅ |
| A6 | 组件工程 = `component_eng.py` 纯函数 + `LeakReport` 显式报告 + warn>1e-6 / fail>1e-3 | ✅ |
| A7 | analyse = 三闭式（purity / overlap / pure_fidelity）；entropy_vn 与混合-混合 fidelity 不进 B 范围（开放问题） | ✅ |
| A8 | IR `initial` = per-mode 工厂规格列表 `[{"kind","params"},...]`，缺省 vacuum；核心 validator 保持 opaque | ✅ |
| A9 | 分步执行 = Bosonic 编译子类专属 `run_steps()`，共享 `circuit_common` 零改动 | ✅ |
| A10 | 保真度 sweep = 后端 `fidelity_sweep` 一次成型，GUI 只画 | ✅ |
| A11 | `BOSONIC_PUBLIC` 冻结于 **B1 出口**；marker `phaseB1`–`phaseB7` | ✅ |
| A12 | gkp0/gkp1 = 初始态工厂（电路无 gkp 门）；`gkp_logical_overlap` 保留 + deprecated 标注，不进冻结核心面 | ✅ |

## 1. 模块架构（vision §3 树 amend 后）

```text
cvsim/
  conventions.py         # 共享（ħ=1, xxpp）— 已有
  symplectic.py          # 共享辛核心 — 已有
  circuit_common.py      # 共享 DSL 核（op 5-tuple, ParamRef, compile_segments, CompiledCircuit）— 已有
  bosonic/
    state.py             # BosonicState + Component (V, r̄ complex, w complex) + weight_sum() + vacuum/from_gaussian — 已有
    cat.py               # even_cat / odd_cat — 已有
    gkp.py               # gkp0 / gkp1（+ gkp_logical_overlap deprecated 标注）— 已有
    gates.py             # 门 11：displace/phase/squeeze/fourier/beamsplitter/mach_zehnder/
                         #   two_mode_squeeze/cz/cx/interferometer（B1 对齐 Gaussian 全集）— 部分已有
    channels.py          # loss（已有）/ amplifier / phase_noise（B1 对齐）— 部分已有
    observables.py       # 只留矩：mean_photon — 已有（homodyne 迁出）
    measure.py           # 全部测量：homodyne（教学→B3 精确）+ heterodyne/threshold（B1）— 新建
    component_eng.py     # B2: merge/truncate/underflow/normalize/leakage/is_hermitian + LeakReport — 新建
    analyse.py           # B2/B4: purity/overlap/pure_fidelity（闭式，高斯重叠核）— 新建
    circuit.py           # B5: BosonicCircuit（任意 m）+ BosonicCompiledCircuit（run_steps）— 新建
    ir.py                # B5: to_ir/from_ir（circuit_v1 roundtrip）— 新建
```

## 2. 数据模型（A1, A3）

### 2.1 Component（冻结，B0 已锁）

```python
@dataclass
class Component:
    V: np.ndarray      # 2m×2m float64，xxpp
    rbar: np.ndarray   # 2m complex128（虚部 = 干涉中心）
    w: complex         # 对角实正；交叉复（干涉）
```

### 2.2 归一化不变量（A3，新增锁定）

- `Tr ρ = Σ_k w_k`（每分量 trace-1）→ 归一化 = **Σ_k w_k = 1**（结果必须实 = 1）
- **`weight_sum(state) -> complex`**（state.py）：归一检查 `|sum−1| ≤ atol`；条件测量后重归一用它
- **`is_hermitian(state, atol) -> bool`**（component_eng.py）：对每个 `(V, r̄, w)` 分量必须存在共轭配对 `(V, r̄*, w*)`。工厂与条件化后必测；O(K²) 查对，K≤几百可忽略
- 对角 Re(w) ≥ 0（物理态）；Σ|w_k| ≠ 1 一般（交叉项抵消），**不得**当归一

## 3. 门/通道执行（A2）

- 函数式：每个门 = `for comp: V_k ↦ S V_k Sᵀ, r̄_k ↦ S r̄_k + d`，w 不动（高斯门不混分量）；返回新 state
- 签名 1:1 对齐 Gaussian：displace/phase/squeeze/fourier/beamsplitter/mach_zehnder/two_mode_squeeze/cz/cx/interferometer（B1 出口 = K=1 atol 对齐，测试可复用）
- 通道 per-component 仿射 + 权重规则：loss（已有）；amplifier/phase_noise（B1）
- **门/通道内部永不隐式 merge/truncate**（vision §5 铁律 3）

## 4. 测量（A4, A5）

### 4.1 模块归属（A4）

所有测量进 `measure.py`（与 Gaussian 对齐）；`observables.py` 只留矩。vision §3 树同步 amend。

### 4.2 homodyne（B3 精确化核心）

- **边缘分布**：`P(x) = Σ_k w_k p_k(x)`，`p_k` = 分量高斯边缘（实正），`w_k` 复
- **采样 = CDF 网格反演**（A5）：
  - 网格上算 `S(x) = Σ w_k p_k(x)`，取 Re（厄米闭合 → Im≈0，A3 兜底），`P = max(Re S, 0)`（负值 = 非物理，warn）
  - 网格自动定：`δx ≤ σ_min/5`（最窄对角分量），范围 = 实部质心 ± 数 σ；ε≥0.05 的 GKP → ~10⁴ 点
  - `rng.uniform` + `searchsorted` 反演：确定性、无拒绝循环、10³ shots 一次向量化
- **条件化**：后验 `ρ_post = Σ_k [w_k p_k(x)] ρ_k / P(x)`（同一核逐分量复标量重加权）→ 重归一（A3）
- **出口验证**：Fock 高 cutoff P(x) atol 交叉（B3 exit 1）；恒等式 `Σ p(o)·ρ_post(o) = ρ`（exit 2）；直方图 vs 精确密度 KS/分箱（exit 3）

### 4.3 heterodyne / threshold（B1）

- heterodyne：Gaussian 语义 —— 条件化 + 删除被测模（compile_segments remove_mode_ops 现成）
- threshold：outcome-only {0,1}，无态更新；`p_click = 1 − Σ_k w_k |⟨0|g_k⟩|²`（真空重叠闭式）

## 5. 组件工程（A6, B2）

`component_eng.py` 纯函数 + `LeakReport`：

```python
@dataclass
class LeakReport:
    n_before: int
    n_after: int
    discarded_weight: float   # Σ|w_k| 被丢弃分量（代理量，诚实标注）
    merge_distortion: float   # 合并畸变估计（重叠加权范数差）
    weight_drift: float       # normalize 前后 |Σw − 1|
    status: Literal["ok", "warn", "fail"]

def merge(state, *, rtol=1e-3, vtol=1e-3) -> tuple[BosonicState, LeakReport]   # 近峰合并，w_new = w_i + w_j
def truncate(state, *, amp_cutoff=..., wmin=...) -> tuple[BosonicState, LeakReport]
def underflow(state, *, wmin=1e-15) -> tuple[BosonicState, LeakReport]
def normalize(state) -> BosonicState                    # 按 trace 重归一，漂移记日志
def leakage(state) -> float                             # 快捷泄漏估计
def is_hermitian(state, atol=1e-10) -> bool             # A3
```

- warn > 1e-6（默认，RuntimeWarning）/ fail > 1e-3（严格，ValueError）—— 镜像 Fock §5
- 泄漏度量 = 丢弃 |w_k| 质量是**代理量**，真实代价 = 对可观测量的影响；文档写清
- 条件化内部自动重归一（B3 恒等式要求）；`normalize` 是用户显式管道 + merge 后的 API

## 6. analyse（A7, B2/B4）

`analyse.py` 三闭式（高斯重叠核，bosonic 私有，ADR-0001）：

- `purity(state)`：`Tr ρ² = Σ_kl w_k w_l* Tr(ρ_k ρ_l)`（高斯重叠闭式）
- `overlap(ρ, σ)`：`Σ_kl w_k v_l* Tr(ρ_k σ_l)`（闭式）
- `pure_fidelity(ρ, ψ)`：`Tr(ρ|ψ⟩⟨ψ|) = Σ_k w_k |⟨ψ|g_k⟩|²`（闭式；GKP 教学主用，B4 层 2 单调性测试）

**明确不进 B 范围**（开放问题，解锁条件 = 教程真需要，走 Fock 高 cutoff 数值路径）：
- `entropy_vn`（混合态无闭式）
- 混合-混合 `fidelity`（需 √ρσ√ρ 谱分解）

## 7. 电路与 IR（A8, A9, A10, B5/B6）

### 7.1 BosonicCircuit（B5）

- `BosonicCircuit(nmode, initial=[...])`：`initial` = per-mode 工厂规格列表，缺省 vacuum
- 工厂规格：`{"kind": "vacuum"|"coherent"|"even_cat"|"odd_cat"|"gkp0"|"gkp1", "params": {...}}`（cat: alpha; gkp: epsilon/grid_size/cross/lattice）
- op 注册表（B1 全集）：门 11 + 通道 3 + 测量 3；**无 Kerr / 无 gkp 门 / 无协议 op**（A12, P1）
- ParamRef feedforward 由 `partition` 现成支持（测量结果 → 后续门参数）

### 7.2 IR（A8）

```json
{"schema": "circuit_v1", "nmode": 1, "backend": "bosonic",
 "initial": [{"kind": "gkp0", "params": {"epsilon": 0.1, "grid_size": 3, "cross": "none", "lattice": "1d"}}],
 "ops": [...]}
```

- 工厂名 = 规范名 → roundtrip 天然无损；**不**序列化任意 BosonicState（不可逆）
- 核心 validator 视 `initial` opaque（EXTENSION_FIELDS 已有）；bosonic validator 校验 kind/params 白名单
- `backend: "bosonic"` 复用 F7 扩展字段，旧 JSON 零破坏

### 7.3 分步执行（A9, B6）

```python
class BosonicCompiledCircuit(CompiledCircuit):   # circuit.py，共享基类零改动
    def run_steps(self, *, rng=None, **values) -> list[StepSnapshot]
    # StepSnapshot = (op, state_after, results_so_far, outcome)
```

- 快照只在 break op 边界（= 测量数，不爆）；纯高斯段合并执行（compile_segments 现成）
- lab bosonic 路径：终态走 `run`，步骤视图走 `run_steps`（同一编译快照两条出口）
- Gaussian/Fock 回归面（758+ 测试）零波及

### 7.4 保真度 sweep（A10, B6）

- 后端：`fidelity_sweep(circuit, ideal_state, gamma_range, **params) -> (gammas, fidelities)`（内部每 γ 编译执行一次，seed 约定）
- 三处复用：GUI 面板 / 教程 notebook / pytest 回归；golden fixture 直接断言（B6 exit 2）
- `ideal_state` = gkp0/gkp1 工厂态（A7 pure_fidelity 闭式，无特征分解）

## 8. 工程纪律（A11）

- `BOSONIC_PUBLIC` 冻结于 **B1 出口**（核心面：BosonicState/Component + 工厂 + 门集 + 通道 + measure.py 三测量 + weight_sum/is_hermitian + mean_photon）；B2+ 新增走 `docs/api-stability.md` 增补流程
- `tests/test_public_api.py` 扩展 bosonic 段（现有文件加块）
- marker `@pytest.mark.phaseB1`–`phaseB7`，CI 可切片
- `gkp_logical_overlap`：保留 + docstring deprecated（指向 pure_fidelity）；不进冻结核心面；B4 层 2 用 pure_fidelity 锁真值

## 9. B 阶段映射

| 决策 | 落地切片 |
|------|---------|
| A2/A4/A12 | B1（门对齐、通道、measure.py、deprecated 标注） |
| A3/A6 | B2（weight_sum/is_hermitian/merge/truncate/underflow/leakage + BOSONIC_PUBLIC 冻结） |
| A5 | B3（精确边缘 + 条件化 + CDF 反演采样） |
| A7 | B2/B4（analyse 闭式 + 层 2 套件） |
| A8/A9 | B5（BosonicCircuit + IR + run_steps） |
| A9/A10 | B6（分步执行 + fidelity_sweep + GUI 三件套） |
| A1 | 贯穿（数据结构冻结，B2 基准再评估） |

## 10. 开放问题（继承 vision §10，无新增）

- 双模生产级（K² 爆炸）、组件式 PNR、AD、tensor networks
- entropy_vn / 混合-混合 fidelity（A7 defer，解锁 = 教程需要 + Fock 桥）

## 11. 文档控制

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.1.0 | 2026-08-14 | Grill A1–A12 锁定，架构设计定稿 |
