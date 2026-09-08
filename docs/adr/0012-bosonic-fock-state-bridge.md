# ADR-0012: bosonic→fock 状态桥与 PNR 条件化

- 日期: 2026-09-08
- 状态: 已接受
- 前置: ADR-0001（模块边界）、ADR-0005 决策 8（B7 桥）、spec `cvsim/bosonic.md` §7.1/§7.2（"pnr_condition 须先锁定返回表示与 ADR"）
- 任务: `.trellis/tasks/09-08-pnr-condition-state-bridge/`（probe 先行，PIN RESULT: OK）

## 背景

PNR 条件化后验一般是数态投影后的非高斯态，无法用有限高斯分量精确表示——
这是 B9/B10 一直推迟 `pnr_condition` 的原因（vision §1.3 非目标行、spec
§7.1/§7.2"明确非目标"）。B10 联合多模 PNR 概率面已交付（生成函数 +
branch anchoring），链路唯一缺口是"测量之后的态"：门控、掺 Er 纠错、HOM
层析都要后验，不只是概率。

PRD 初版的 Bargmann 表示 + Cauchy-FFT 核路线被 Phase-0 probe 否决（复权重
干涉下算符构造不收敛）；probe 转向 Bloch–Messiah-lite 矩阵原子路线，11 项
数值测试全绿（coherent/squeezed/rotated/TMSV/heralding/复 r̄ 猫态装配/
混合谱路线），随后按 probe 逐行移植生产代码。

## 决策

1. **PNR 后验 = Fock 表示**。后验本就是截断数态空间中的对象，fock 是其
   原生家。桥是**单向整态切换** bosonic→fock，不做 fock→bosonic（高斯分量
   分解无无损逆）。
2. **API 三件，落根 `cvsim/bridge.py`**（ADR-0001 允许跨包 import 的唯一层；
   bosonic 包禁 import bridge 的边界不变，架构测试锚定）：
   - `bosonic_to_fock(state, *, cutoff) -> FockDensity`
   - `pnr_condition_bosonic(state, mode=0, n=0, *, cutoff=30) -> FockDensity`
     （两步桥：整态桥 → fock `pnr_condition`）
   - `pnr_sample_and_condition_bosonic(state, mode=0, *, cutoff=30, rng=None)
     -> tuple[int, FockDensity]`
3. **分量核 = Bloch–Messiah-lite**（`tools/probe_bridge_kernel.py` 钉死）：
   - 纯分量：`C = sqrtm(2V)`、eigh 取 m 个最小本征值为压缩方向（fock
     `S(+r)` x-压缩约定），配对搜索 x←q、p←−Ωq 复原 `2V = O₁R₂O₁ᵀ`；
     `U_O = X − iY`（uo_sign=−1 由金标钉死）；|ψ⟩ = D 链 · U_passive ·
     ∏S_k(r_k)|0⟩ 在 `(N+24)^m` 梯空间构造后截断。
   - 复 r̄ 分量（干涉项）：B7 左右劈裂 `r_L − r_R = −ΩV⁻¹s`，算符
     `w·|ψ_L⟩⟨ψ_R|/⟨ψ_R|ψ_L⟩`；分母用截断数值重叠（窗口精确比值），
     绝不用解析 S_ij（下溢区 `w_c/S` 比值先约分，float64 安全）。
   - 单模混合分量：谱路线 `ν = √det 2V ≥ 1`，`U' = 2V/ν` 须辛（热对称
     族），`p_n = 2/(ν+1)·qⁿ`，`q = (ν−1)/(ν+1)`。
   - **无任何 renormalization**：逐元素精确截断算符，`trace = 1 − tail`
     （对齐 fock 工厂 / `pnr_probs` 约定；tail 永不猜测，vision §5）。
4. **诚实边界（全部 ValueError）**：m≥3 整态；2 模混合分量（积热核 kron
   支持考虑过、defer）；复 r̄ × 混合分量；below-vacuum `det(2V)<1`；零概率
   outcome 沿用 fock 侧报错。
5. **fock 端 `pnr_condition` 推广 nmode≤4**（同任务 AC-9）：纯态 `np.take`
   删模（k 模 → k−1 模），密度态投影掩膜冻模（k 模保持 k 模）；
   `pnrd_probs` 边际同步推广；2 模行为逐位回归锁定。
6. **Bargmann/Cauchy-FFT 路线废弃记录**：复权重混合下 Cauchy 提取的 branch
   翻转在算符构造中不可控（B10 概率提取已解决的是标量分支，算符版不可
   迁移）。全程 probe 先行（B10 纪律），probe 文件保留在 `tools/`。

## 影响

- 正面：ADR-0005 B7 的态桥半边落地；PNR 后验链路（门控/纠错/层析）可用；
  fock 端多模测量顺带补齐（k≤4）；cat 干涉（复 r̄ 交叉分量）在桥中存活
  （AC-4 金标 1e-9）。
- 负面/边界：桥代价 O(K·(N+pad)^{3m})（分量数 × 梯空间 expm），N、K 大时
  昂贵；整态上限 m≤2；m≥3 与 2 模混合是本 ADR 明示的 future work。
- 契约：vision §1.3 非目标行改判、§2.3 增桥语义、gap inventory §6 Top-1
  更新，与本 ADR 同一变更集生效。