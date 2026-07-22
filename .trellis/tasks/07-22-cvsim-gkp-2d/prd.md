# δ2 · GKP 2D lattice

## Goal

教学 **2D 相空间格点** GKP 峰：`gkp0`/`gkp1` 在 \((x,p)\) 平面上截断格子。  
**诚实：对角峰为主；非 Gram 正交；非逻辑 Clifford。**

## Background

- 现：仅 **1D x 梳**；`cross=none|nn|full`；\(V=\frac12\mathrm{diag}(ε,1/ε)\)
- 用户锁 full GKP 子包 **δ2 = 2D 格**
- 未做仍：Gram（δ3）/ 逻辑门

## Physics card

ħ=1，与现 1D 同 Δ：

```text
Δ = √(2π)
|0⟩_2d: peaks at (k Δ, l Δ),  k,l ∈ {-N…N}
|1⟩_2d: peaks at ((k+½)Δ, l Δ)   # half-shift in x only
```

2D 峰局域（双轴挤）：

```text
V = (ε/2) I_2     # isotropic; ε small → sharp peaks
envelope a_{k,l} ∝ exp(−π ε (k²+l²)/2)
diag weight ∝ a²
```

与 1D 异：1D 用各向异性 \(V=\frac12\mathrm{diag}(ε,1/ε)\)（x 尖、p 宽）；2D 用各向同性小方差。

## Decisions

| # | 选择 |
|---|------|
| D0 | 新参 **`lattice: Literal["1d","2d"] = "1d"`**（默认不破旧 API） |
| D1 | `lattice="2d"`：对角格点 K=(2N+1)² |
| D2 | 2D 本切片 **`cross` 仅 `"none"`**；`nn`/`full` → raise（组合爆炸；δ2 聚焦格点） |
| D3 | `gkp0`/`gkp1` 同参；gkp1 仅 x 半格偏移 |
| D4 | 1d 路径零行为变（含 full） |
| D5 | 无 Gram / 无 Clifford / 无 3D |
| D6 | 工程 docs 必改；理论 MD 可选 03 一句 |

## Requirements

### R1 API

```python
gkp0(epsilon=0.1, grid_size=2, *, cross="none", lattice="1d")
gkp0(..., lattice="2d")           # K=(2N+1)², cross must be none
gkp1(..., lattice="2d")
```

### R2 tests

- 2d N=1：K=9，∑w=1  
- 峰在整数格（gkp0）/ 半格 x（gkp1）  
- V 对角 ≈ ε/2  
- 1d 旧测全绿  
- 2d + cross=nn raise  

### R3 docs

- USER_ACCEPTANCE：2D 对角格落地；未做改 Gram/Clifford  
- README 一行  

## Acceptance Criteria

- [x] **AC1** lattice=2d 可构造，∑w=1，K=(2N+1)²  
- [x] **AC2** gkp0/gkp1 2d；1d 回归绿  
- [x] **AC3** pytest **133**；UAT 8/8  
- [x] **AC4** 文档诚实：2d 仅对角；无 Gram  

## Out of Scope

- 2D 上 nn/full 交叉  
- δ3 Gram  
- 逻辑 Clifford  
- 六角格 / 非方格  

## Notes

- N≥3 → K≥49 组件；测 N≤2  
- Wigner 自动可用（既有 B 路径）
