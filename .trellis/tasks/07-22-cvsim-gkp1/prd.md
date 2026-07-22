# γ · GKP |1⟩ 教学态

## Goal

教学用 **|1⟩_GKP** 多组件 `BosonicState`，API 对齐 `gkp0`（`epsilon`, `grid_size`, `cross`）。  
**诚实：非完整 Gram / 非二维格点纯 GKP。**

## Background

- 用户锁深化包 **γ**
- 现有 `gkp0`：x 齿 kΔ，Δ=√(2π)；`cross="none"|"nn"`
- 未做表仍写：完整纯态 GKP / `|1⟩`

## Decisions

| # | 选择 |
|---|------|
| D0 | 新 API **`gkp1(...)`**，签名同 `gkp0` |
| D1 | 物理：同一 ε、V；齿心 **x=(k+½)Δ**，k∈{-N,…,N-1} 或等价 2N 个半格点（与 |0⟩ 的 2N+1 对齐策略见 design） |
| D2 | `cross` 同语义：none 对角；nn 近邻交叉 |
| D3 | 只 1 模 x 梳；**无** 二维格点、**无** full-pair Gram |
| D4 | 门/矩/Wigner 复用既有 B 路径（自动） |
| D5 | 理论 MD 可选轻补 03 一句；工程 docs 必改 |
| D6 | 无新量子库 |

## Physics card

ħ=1 教学约定（与现 `gkp0` 一致）：

```text
Δ = √(2π)
|0⟩: peaks x = k Δ,     k = -N … N
|1⟩: peaks x = (k+½) Δ, k = -N … N-1   # half-period shift
V = ½ diag(ε, 1/ε)
envelope a_k ∝ exp(−π ε ξ_k² / 2)  with ξ scaled tooth index
```

检查点：

- ∑w≈1；K 计数与 none/nn 公式文档化  
- 相邻齿距 = Δ  
- `gkp1` 相对 `gkp0` 中心齿偏移 Δ/2  
- 可选：`phase(π)` 不把 |0⟩ 变成 |1⟩（诚实：对角混合非逻辑 Clifford 教学）

## Requirements

### R1 API

```python
gkp1(epsilon=0.1, grid_size=3, *, cross="none") -> BosonicState
```

export `bosonic.__init__`

### R2 tests

- weight_sum≈1  
- spacing Δ  
- shift vs gkp0  
- nn K=… 与 none 对比  
- 门 keep weights（同 gkp0 风格）

### R3 docs

- USER_ACCEPTANCE：|1⟩ 落地；未做改为 full Gram / 2D  
- README 矩阵一行  

## Acceptance Criteria

- [x] **AC1** `gkp1` none/nn 可构造，∑w=1  
- [x] **AC2** 齿距 Δ；相对 gkp0 半格偏移  
- [x] **AC3** pytest **117**；UAT 8/8  
- [x] **AC4** 文档更新；诚实边界保留  

## Out of Scope

- full-pair / 2D lattice pure GKP  
- 逻辑门完备（H, CNOT on GKP）  
- Fock 展开 GKP  
- P2  

## Notes

- 实现：复制 `gkp0` 齿循环，改 `k*delta → (k+0.5)*delta` 与 k 范围  
- nn 的 ov 公式同 gkp0（邻齿间距仍 Δ）
