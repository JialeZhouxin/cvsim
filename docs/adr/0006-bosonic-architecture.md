# ADR-0006: Bosonic 架构决策 — CDF 采样 + IR initial 工厂规格

- 日期: 2026-08-14
- 状态: 已接受（grill A1–A12 锁定，任务 08-14-bosonic-architecture）
- 前置: ADR-0005（Bosonic 生产级愿景）

## 背景

愿景锁了 B0–B7 路线（ADR-0005），但架构层留白：B3 精确采样的数学策略、
B5 电路 IR 的 `initial` 形状。两处都是"硬反转 + 无上下文会困惑 + 有真实替代方案"，
单独记 ADR。

## 决策 1 — B3 homodyne 精确采样 = CDF 网格反演（A5）

精确边缘分布 `P(x) = Σ_k w_k p_k(x)`：`p_k` 是实高斯密度但 `w_k` 是**复数**
（干涉交叉项），混合无正概率权重 → 标准高斯混合采样不可用。

- 网格上算 `S(x) = Σ w_k p_k(x)`，取 Re（厄米共轭对闭合保证 Im≈0，`is_hermitian`
  兜底），`P = max(Re S, 0)`（负值 = 非物理，warn）
- 网格自动定：`δx ≤ σ_min/5`（最窄对角分量），范围 = 实部质心 ± 数 σ
  （ε≥0.05 的 GKP → ~10⁴ 点，快）
- `rng.uniform` + `searchsorted` CDF 反演：确定性、无拒绝循环、10³ shots 一次向量化
- 条件化免费：`ρ_post = Σ_k [w_k p_k(x)] ρ_k / P(x)` 同一核逐分量复标量重加权
- 近似仅来自 CDF 插值（网格截断），B3 出口 1（Fock 高 cutoff atol）锁死

### 否决项

- **拒绝采样**（包络 Σ|w_k|p_k）：奇猫/GKP 梳峰间 P→0，拒绝比爆炸，不可行
- **解析反演**：混合高斯 CDF 无闭式
- **对角峰池**：教学切，正是 B3 要替换的近似（`gkp_logical_overlap` 同源）
- **重要性修正**（先对角池再修正）：复杂度高且仍是近似

## 决策 2 — IR `initial` = per-mode 工厂规格列表（A8）

`circuit_v1` 的 `initial` 扩展字段：Fock 是 `list[int]`（per-mode 数态）。
Bosonic 初始态全是工厂（vacuum/coherent/cat/gkp0/gkp1），无"裸态"概念：

```json
"initial": [{"kind": "gkp0", "params": {"epsilon": 0.1, "grid_size": 3,
            "cross": "none", "lattice": "1d"}}]
```

- 形状对齐 Fock 语义（per-mode 列表），元素从 int 升级为工厂规格对象
- 工厂名 = 规范名 → to_ir/from_ir **roundtrip 天然无损**
- 核心 validator 视 `initial` opaque（EXTENSION_FIELDS 已有），bosonic validator
  校验 kind/params 白名单；`backend: "bosonic"` 复用 F7 扩展字段，旧 JSON 零破坏

### 否决项

- **头部 prepare ops**：滥用 op 语义，roundtrip 丢失工厂身份
- **序列化任意 BosonicState**：组件列表 → 规范名不可逆，破坏无损承诺
- **单对象 `{"kind": ...}`**：m>1 无法表达 per-mode 初始态

## 权衡

- CDF 反演是确定性采样，代价是网格插值近似（可测可锁）；拒绝采样无插值但 GKP 场景不可行
- 工厂规格进 IR 意味着新增工厂类型 = IR 白名单变更（向后兼容的增补，非破坏）

## 后果

- 正面：B3 有可执行数学 + 可测误差；B5 IR roundtrip 无损有保障
- 负面：CDF 网格精度依赖 σ_min/5 经验规则，B3 需实测校准；IR 白名单需与 BOSONIC_PUBLIC
  冻结同步维护
- 契约：改采样策略必须先改本 ADR + vision §2.3；改 initial 形状必须先改本 ADR + ADR-0003
  兼容评估
