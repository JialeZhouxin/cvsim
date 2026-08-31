# ADR-0007: Bosonic 混合态 heterodyne 精确化 — 2D Q-surface + 顺序 CDF 反演

- 日期: 2026-09-03
- 状态: 已接受（grill Q1–Q7 锁定，2026-09-03 会话）
- 前置: ADR-0006（B3 homodyne CDF 反演策略；本 ADR 是其 2D 推广）

## 背景

B1 教学切：`measure.py::heterodyne_sample/condition/sample_and_condition`
只从**实对角分量池**（`_real_diag_pool`：实中心 + Re(w)>0）采样/条件化。
猫态交叉项（复中心 `(0, ±i√2α)`、复权重）出池 → Q 干涉条纹静默丢失，
混合态只有 K=1 精确。`p_click`/`sample_threshold` 已精确（复二次型全保留），
无需动。homodyne 精确版（`observables.py` CDF 网格反演）是 1D 姊妹，本 ADR
补 2D。

## 决策 — 2D Q-surface + 顺序 CDF 反演

Q(β) = Σ_k w_k Q_k(β) 在 (x, p) 网格上求和；Q_k 为复中心解析延拓的
复高斯，厄米共轭对闭合（`is_hermitian` 上游守卫）保证 Im Σ ≈ 0。

1. **网格**：照抄 homodyne 规则 —— δ ≤ σ_min/5（σ 取 Q-edge，即
   `V_k + I/2` 边缘的每方向标准差），范围 = 质心 ± 6σ_max，自动网格；
   x/p 可不等距（各方向独立 σ）。
2. **Q 面**：S(x,p) = Σ w_k Q_k(x,p)（complex dtype）；|Im| > 1e-8 raise；
   `Q = max(Re S, 0)`，负值 warn 泄漏质量。
3. **采样**：顺序反演 —— 先抽边缘 P(x)（x 轴求和），再抽条件 P(p|x)
   （该 x 列归一），uniform + searchsorted，10³ shots 向量化。
4. **条件化**：同一核，w_k ∝ w_k · Q_k(β)，复权重重加权 + Σw=1 归一，
   复中心公式与 Gaussian `heterodyne_condition` 同形（解析延拓），
   模删除/xxpp 重排骨架复用现实现。
5. **公开面**：新增 `heterodyne_pdf(state, mode, ...) -> (xs, ps, Q)`，
   镜像 `homodyne_pdf`；`BOSONIC_PUBLIC` 45→46；`imag_tol` 参数从三个
   heterodyne 入口移除（无外部调用者，rg 已核），Im 校验用模块级
   `_IM_TOL = 1e-8`。

### 否决项

- **拒绝采样**：GKP 梳峰间 Q→0，拒绝比爆炸（同 ADR-0006 否决）
- **逐分量抽签 + 复权重**：复 w_k 非概率，非法
- **保留 `_real_diag_pool` 作默认**：正是要替换的教学切；homodyne 精确化
  先例已删池换全分量
- **2D 自适应网格**：YAGNI，单模锚点下均匀网格够用（`ponytail:` 标注
  升级路径）

## 验收 oracle（R1 分层）

1. 偶/奇猫闭式 Q（交叉项 cos 条纹闭式）atol 1e-7；
2. ∫Q d²β = 1（网格积分，1e-9 容差）；
3. 一致性恒等式 Σ p(o)·ρ_post(o) = ρ（条件化对账）；
4. 采样直方图 vs Q 网格 bin-level 一致；
5. K=1 reconciliation 全绿（现有测试不动）。

## 后果

- 正面：heterodyne 与 homodyne 同为精确实现，`measure.py` 头部教学切
  声明可撤；B3 gap 表 Measures 行关闭；backlog #1 完成。
- 负面：2D 网格 O(N²)；小 ε GKP 网格成本上升（`ponytail:` 标注升级路径，
  未承诺）。
- 契约：改采样策略必须先改本 ADR + vision §2.3/§9；`BOSONIC_PUBLIC`
  增补走 api-stability.md 表。
