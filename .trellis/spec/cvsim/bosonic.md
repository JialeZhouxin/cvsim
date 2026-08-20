# Bosonic 表示 — 可执行契约（B1 落地固化）

> 物理/架构决策事实源：`docs/vision-bosonic-simulator.md` + `docs/adr/0005` + `docs/adr/0006` + 任务 `08-14-bosonic-architecture/design.md`。本文件只记 agent 实施时必须遵守的边界与坑。

## 1. 模块边界与导入

- `cvsim/bosonic/*` 只 import `cvsim.conventions` / `cvsim.symplectic`（+ 包内模块）。**禁 import `cvsim.bridge`**（ADR-0001 ALLOWED_ROOT_IMPORTS 不含它，`test_architecture.py` 会红）。
- 测量在 `cvsim/bosonic/measure.py`（A4）；`observables.py` 只留矩 + `_as_real` 等私有 helper。
- B3 前 homodyne 实现单一来源 = `observables.py`，`measure.py` re-export；外部路径 `cvsim.bosonic.homodyne_*` 冻结不变（BOSONIC_PUBLIC 33 名，`test_public_api.py`）。

## 2. 空态语义

- `BosonicState.nmode`：空 components 返回 `0`（不抛错）—— heterodyne 删模尾部（单模 K=1 条件化后）。
- heterodyne 条件化后的单模多分量态 = **0-dim-V components**（V shape (0,0)，权重保留归一化 Σw=1）；不是空列表。
- `gates._nmode` 对空态**保持抛错**（对空态应用门 = 用户错误）。

## 3. 真空重叠 — bridge 浮点化陷阱（Gotcha）

> **Warning**: `cvsim.bridge.vacuum_probability` 内部 `rbar = np.asarray(rbar, dtype=float)` —— **静默丢弃复位移虚部**（干涉中心）。交叉分量的真空重叠会错。

- Bosonic 阈值测量用私有 `_vacuum_probability_complex`（measure.py）：同一二次型 `e^{−½r̄ᵀ(V+½I)⁻¹r̄}/√det(V+½I)`，复 r̄ 能力；实 r̄ 时与 bridge 数值一致（K=1 测试证明）。
- 复值结果取实部必须过虚部容差检查（`_as_real`，|imag| > 1e-8 抛错）—— 永不许静默丢干涉。

## 4. 教学切边界（B1 → B3）

- heterodyne（B1）= **教学切**：sample/condition 只用实对角分量池（`imag_tol=1e-12` 过滤），K=1 与 Gaussian 严格对齐；混合态精确化（CDF 反演）属 B3，同 homodyne。
- homodyne（B1）= 教学切（`homodyne_sample` 实峰池）→ B3 换 CDF 网格反演（ADR-0006）。
- **B3 已落地（2026-08-18）**：`homodyne_sample` 已不是教学切，改为 CDF 网格反演精确采样（`observables.py`）；新增 `homodyne_pdf` 公共 API（BOSONIC_PUBLIC +1 名）。返回类型 `float` → `np.ndarray (shots,)`——**破坏性变更**，调用方需取 `[0]` 或 `outcomes[i]`。`homodyne_condition` 未动（已是精确 Born-rule 闭式）。
- 仅 `heterodyne` 仍是教学切（实对角分量池，spec §4 原条目）。
- 教学切 API 的 docstring 必须显式标注"teaching cut, not production"——防被当生产用。

## 5. deprecation 纪律

- pyproject `filterwarnings = ["error:cvsim.*"]`：cvsim 模块发 `DeprecationWarning` → pytest error。**deprecation 只能写 docstring**（`.. deprecated::` 块），零运行时 warning。
- 先例：`gkp_logical_overlap`（B1，指向 B2/B4 `pure_fidelity`）。

> **Warning**: `filterwarnings = ["error:cvsim.*"]` 的 `cvsim.*` 匹配的是 warning **消息文本**（regex），不是模块名。`warnings.warn("homodyne_pdf: ...")` 消息以 `homodyne_pdf:` 开头，不匹配 `cvsim.*` → **不**被转 error，可安全运行时 warn（B3 负 Re(S) clip 即用此）。若要让 warning 变 error，消息须以 `cvsim.` 开头。

## 6. B2 组件工程

- `cvsim.bosonic.component_eng` 提供纯函数 `merge`、`truncate`、`normalize`、`is_hermitian` 与 frozen `LeakReport`。
- `merge` 默认 `atol=1e-10`、`rtol=1e-8`，按输入顺序稳定贪心分组；代表保留组内第一组件，权重求和，畸变写入报告。
- `truncate` 默认只删除 `abs(w) < 1e-6` 的组件；丢弃质量 `sum(abs(w))`，超过 `1e-6` 警告、超过 `1e-3` 失败，`validate=True` 时超过警告阈值即失败。
- 组件工程不自动归一化、不修改输入；推荐显式先 `merge` 后 `truncate`，分别保存报告。
- B2 不改变 B1 门、通道、测量的隐式行为；精确测量仍属 B3。

## 6.1 B3 测量精度（homodyne CDF 网格反演）

- `homodyne_pdf(state, mode=0, phi=0.0, *, n_grid=None, lim=None) -> (xs, P)`：精确边分布 `P(x_φ) = Σ_k w_k p_k(x)`，复权重/复 r̄ 全保留（干涉项）；`P = max(Re S, 0)`，负值 clip + warn；`is_hermitian` 兑底 Im≈0。
- `homodyne_sample(state, mode=0, phi=0.0, *, rng=None, n_grid=None, lim=None, shots=1000) -> np.ndarray (shots,)`：CDF cumsum + `searchsorted(rng.uniform)` 反演，向量化。
- 网格自动规则：`δx = σ_min/5`（最窄峰），范围 = 质心 ± 6σ_max（最宽峰），`n_grid = ceil(60·σ_max/σ_min)+1`。override `n_grid`+`lim` 同设则 `linspace(-lim, lim, n_grid)`。
- **Born 一致性局限**（vision §4 B3 判据 2）：`homodyne_condition` 的高斯近似 `V'` 与 outcome 无关（`V' = V − vvᵀ/σ`），积分 `∫P·ρ_post·do` **不**恢复原 V——这是高斯流形近似本质，非 Born 违反。判据 2 只验：① 后验 `weight_sum==1`（每点）、② `∫P·mean_post·do == 原 mean`、③ `∫Σ_k w_k L_k·do == Σ_k w_k == 1`。完整 V 调和属 B4 R1 layer 2。

## 6.2 B4 调和对账（analyse 闭式 + R1 分层套件）

- `cvsim.bosonic.analyse`（新文件）：`purity` + `pure_fidelity`。
- `purity(state, *, validate=False) -> float`：`μ = Σ_k |w_k|² / (2^m·√det V_k)`——**teaching 对角近似**（非严格 `Tr(ρ²)`，忽略非对角项 `Tr(ρ_i ρ_j)`）。GKP/cat 分量空间分离时误差极小；强重叠态偏差大。`validate=True` 走 `is_hermitian`；`det V_k≤0` 抛 ValueError。严格混合态纯度需 `overlap`（未实现）。
- `pure_fidelity(state_a, state_b) -> float`：`|⟨ψ|φ⟩|²`，**等 V 限制**（两态所有分量 V 必须相同，否则 ValueError）。Gram `T[i,j]=_gauss_overlap(V, r_i^a, r_j^b)`（复用 gkp.py），`⟨ψ|φ⟩=c_aᴴ·T·c_b`（c=√w，复平方根保相位）。通用双 V 公式留 B7。
- `gkp_logical_overlap`（deprecated）由 `pure_fidelity` 替代；等 V 同 grid 退化对齐（L2c）。
- **R1 分层对账**（`tests/test_b4_bosonic_reconciliation.py`，全 `@phaseB4`）：
  - layer 1（L1a-L1e）：退化情形 atol（K=1 squeezed/coherent vs Gaussian、K=2 混合 purity 自洽、cat 4 分量 mean_photon、cat vs Fock cutoff=30 homodyne_pdf）。
  - layer 2（L2a-L2e）：GKP 内部恒等式（self-fidelity≈1、vs deprecated logical_overlap 对账、post-condition 自洽、loss 后 purity<1）。
  - **GKP 无解析基准**（已锁）：layer 2 是内部互验，tolerance 放宽（self-fidelity atol 1e-5，GKP Gram 归一化数值精度限）。
- Born 一致性局限（B3）：`homodyne_condition` 的 `V'` 与 outcome 无关，`∫P·ρ_post·do` 不恢复原 V——高斯近似本质，非 Born 违反。判据 2 只验权重归一+质心重构+似然归一。完整 V 调和需 `overlap`（未实现）。

## 6.3 B5 BosonicCircuit 电路 DSL（circuit_v1 第三消费者）

- `cvsim.bosonic.circuit.BosonicCircuit`：镜像 GaussianCircuit builder（11 门 + 3 通道 + 3 测量）+ composition + `compile()`/`run()` + `to_ir()`/`from_ir()`。复用 `circuit_common`（ParamRef/partition/compile_segments/CompiledCircuit，ADR-0004）零修改。
- `cvsim.bosonic.compile.CompiledBosonic`：`_init_state`=vacuum，`_apply_merged`=`apply_symplectic(st, S, d)`（逐分量，复刻 Gaussian `_instantiate`+`_factor`，复用 `cvsim.symplectic`）。K=1 恒定（gate 不增分量）。
- `cvsim.bosonic.ir`：circuit_v1 to_ir/from_ir + validate_ir，**无扩展字段**（初态 vacuum，K=1 恒定）。复刻 Gaussian ir 的 OP_META/encode/decode（去 mz）。
- `BosonicState.remove_mode(mode)`（state.py）：逐分量 partial trace（V_k 删 2 行 2 列 + xxpp 重排，w 不变）。homodyne 手动删模（B3 homodyne_condition 不删）；heterodyne 已内置删模。
- 测量语义：homodyne `homodyne_sample_and_condition(shots=1)` → `results[name]=float(outcomes[0])` → `post.remove_mode`；heterodyne `heterodyne_sample_and_condition` → `results[name]=complex(beta)` → post（已删模）；threshold outcome-only 无删模。
- **Lab 接入延后 B6（已解锁 2026-08-19）**：vision §6.2 硬边界类比 Fock F7 解锁；B5 先落 IR 库（circuit_v1 schema 兼容），B6 补 Lab `backend="bosonic"` 路由（`BOSONIC_WHITELIST` + `_load_bosonic` + `run_bosonic_circuit`）+ Wigner view + fidelity sweep + 分步执行。
- phaseB5 marker；BOSONIC_PUBLIC 41→45（+BosonicCircuit +ParamRef re-export +to_ir +from_ir）。

## 6.4 B6 GUI 三件套（同壳第三后端）

- **initial 扩展字段（R1）**：IR `initial` 字段 = per-mode 态名列表（`null`/`"gkp0"`/`"gkp1"`，仅无参态；缺省=真空）；`BosonicCircuit(initial=...)` 接受 `BosonicState` 或列表；`tensor_product(states)`（state.py）逐分量直积：K 乘、V 块对角、r̄ 拼接、w 乘；to_ir/from_ir 序列化 initial（对含非真空才写）。
- **双 V overlap（R3）**：`_gauss_overlap_two_V(Va,Vb,r_i,r_j)`（gkp.py）`2ᴹ(detVa·detVb)^{¼}/√det(Va+Vb)·exp(−¼Δrᵀ(Va+Vb)⁻¹Δr)`；`pure_fidelity` 逐分量 V（破 B4 等 V 锁）。等 V=V₀ 精确退化 `exp(−⅛ΔrᵀV₀⁻¹Δr)` ≡ B4 内核（layer2 测试不破）。
- **GKP 位移纠错主剧本（R2）**：`initial:[gkp0,gkp1] + cz(0,1,1) + loss(0,T) + measure_homodyne(1,φ) + displace(0,α=$ref)`。**正确 quadrature = φ=π/2（测 ancilla p，CZ 耦合读法）**，gain=1。T=1 时可达保真度≈1（数值截断容差 1e-3）；outcome 落 teeth 决定纠错质量（GKP 本性，rounds 平均教学呈现）。fidelity>1 是截断态已知现象（B4 caveat），GUI 展示 clamp。
- **Lab 三后端**：`BOSONIC_WHITELIST`（11 门+3 通道+3 测量，含 cz/cx/interferometer/gaussian_channel/measure_threshold）；`fidelity_sweep`（stochastic，每 γ 点固定 seed，`rounds` 平均，target `{state, mode}`）；`detail="steps"` 一次返断点快照（op/nmode/meters/wigner）；`/fidelity` 端点 bosonic-only（否则 422）。`/scan` 对 bosonic → 422（sweep 带 RNG 走 /fidelity）。
- **前端**：`ops.js` 18 个 bosonic op（含 3 个 JSON-only：interferometer/gaussian_channel/measure_threshold 进 palette 定义但矩阵参数面板不编辑）；初始卡 per-mode GKP 源；结果面板 = Wigner（复用）+ fidelity 曲线 + 分步滑条；bosonic 时藏 scan/state-grid（无单一 V）。
- phaseB6 marker；`test_a8_no_private_or_other_rep_imports` 随 vision §6.2 更新（bosonic public 解锁，`bosonic._` 仍禁）；`test_b6_bosonic_gui.py` 21 项（IR initial / 双 V / QEC / Lab golden / steps / fidelity / 旧 JSON 不变）。
- **测向锁定**：GUI 默认剧本 φ=π/2 测 p（Q2 原拍 x 为引导误判，数值证 p 才对）；fidelity 曲线不锁单调性（GKP 阈值 + outcome 依赖是教学点，非 bug）。

## 7. 门/通道对齐模式

- 门 = 薄封装 `apply_symplectic(state, S_*(...))`，签名 1:1 复制 `cvsim/gaussian/gates.py`（含 `interferometer(..., *, validate_u=True)`）。
- 通道 = 逐分量 `V_k ← X V_k Xᵀ + Y`，权重不动，V 对称化；X/Y 数学复制 Gaussian channels.py（amplifier `X=√G·I, Y=(G−1)(nbar+½)·I`；phase_noise `X=e^{−σ²/2}·I, Y=(1−e^{−σ²})·½·I`）。
- 任何 K=1 对齐改动必须有 `BosonicState.from_gaussian` 包装态 vs `cvsim.gaussian` 的 atol 测试。

## 8. 验证命令

```powershell
.venv\Scripts\python.exe -m pytest -q                                   # 全套（1124+）
.venv\Scripts\python.exe -m pytest -m phaseB1 -q                        # B1 切片
.venv\Scripts\python.exe -m pytest -m phaseB2 -q                        # B2 切片
.venv\Scripts\python.exe -m pytest -m phaseB3 -q                        # B3 切片
.venv\Scripts\python.exe -m pytest -m phaseB4 -q                        # B4 切片
.venv\Scripts\python.exe -m pytest -m phaseB5 -q                        # B5 切片
.venv\Scripts\python.exe -m pytest -m phaseB6 -q                        # B6 切片
node --test tests/editor.test.mjs tests/fock.test.mjs                 # 前端纯逻辑（node）
```
