# δ3 · GKP Gram 权重正规化

## Goal

把 GKP 多组件权重 **显式建成 Gram 纯态形式** \(Z=c^\dagger S c\)，与 cat 同构；  
可选 **2d + full 交叉**（小 N）。  
**诚实：非逻辑 Clifford；非完整 dual 基；非生产级 stabilizer 解码。**

## Background

- δ1：1d `cross=full`，`w ∝ a_i a_j ov`，再 \(\sum w=1\)  
- δ2：2d 仅对角，`cross` 禁 nn/full  
- cat：\(N=2(1\pm\mathrm{ov})\)，diag \(1/N\)，cross \(\pm\mathrm{ov}/N\) ≡ 二元 Gram  

**关键观察：** 1d full 的 \(\sum_{\mathrm{raw}} = a^\dagger S a\)（每对 2 个组件各 \(a_i a_j S_{ij}\)）**已是** Gram 归一。  
δ3 不是重做 δ1，而是：

1. **显式化** Gram（可测、可文档）  
2. **补 2d 交叉**（δ2 缺口）用 2d 重叠 \(S\)  
3. **逻辑正交检查**（教学）：小 ε 时 gkp0/gkp1 重叠应小  

## Physics

同 V 两归一高斯峰：

\[
S_{ij}=\langle g_i|g_j\rangle
=\exp\Bigl(-\tfrac18\Delta r^\top V^{-1}\Delta r\Bigr)
\quad(\hbar=1\text{ 教学公式；与现 1d ov 对齐验证}).
\]

1d 现码：\(V=\frac12\mathrm{diag}(ε,1/ε)\)，\(\Delta r=(δx,0)\) → \(S=\exp(-δx^2/(4ε))\)（保持）。  
2d：\(V=(ε/2)I\)，\(\Delta r=(δx,δp)\) → \(S=\exp(-(δx^2+δp^2)/(4ε))\)。

纯态 \(|ψ\rangle=\sum_k c_k|g_k\rangle/\sqrt{Z}\)，\(c_k>0\) 包络：

\[
Z=c^\dagger S c,\quad
w_{ii}=c_i^2/Z,\quad
w_{ij}^{\pm}=c_i c_j S_{ij}/Z
\quad(i<j\text{ 各一复均值组件}).
\]

## Decisions

| # | 选择 |
|---|------|
| D0 | 抽 `_gram_weights` / `_overlap(V, r_i, r_j)`；1d full **数值对齐旧路径** |
| D1 | 2d 允许 **`cross="full"`**（仅 full；仍无 nn 以减 API） |
| D2 | 2d full：N≤1 默认测（K_peaks=9 → 组件 81）；N=2 可选 skip 或慢测 |
| D3 | 新教学 API **`gkp_gram_overlap(st0, st1)`** 或模块内 `_logical_overlap`：两 pure 形 GKP 的 \(c^\dagger T d/\sqrt{Z0 Z1}\) 用峰集合（对角峰 + 同 V）近似；**仅对角峰 c** 教学版 |
| D4 | 默认 API 不变：`lattice/cross` 默认值不动 |
| D5 | **不做** Clifford、stabilizer、S^{-1} dual 重展 |
| D6 | 工程 docs 必改；理论 MD 可选 |

## Requirements

### R1

- 1d full：行为与 δ1 一致（权重/K/∑w）  
- 2d full：可构造，∑w=1，K = M + 2·C(M,2) = M²，M=(2N+1)²  
- overlap 教学函数：gkp0 vs gkp1 在 ε 小、N 适中时 |ov| 明显小于 1  

### R2 tests

- 1d full regression（K、∑w、与 none Wigner 差）  
- 2d full N=1：K=81，∑w=1  
- 2d full + nn 仍 raise（若只开 full）  
- gram_overlap(gkp0,gkp0)≈1；gkp0 vs gkp1 |ov| < 0.5（教学阈值）  

### R3 docs

- USER_ACCEPTANCE：Gram 显式 + 2d full；未做 Clifford  
- README 一行  

## Acceptance Criteria

- [x] **AC1** 1d full 回归绿  
- [x] **AC2** 2d cross=full 可跑  
- [x] **AC3** Gram/overlap 检查点过  
- [x] **AC4** pytest **139**；UAT 8/8  
- [x] **AC5** 文档诚实边界  

## Out of Scope

- 逻辑门 H/CNOT on GKP  
- 2d nn only  
- 完整 Fock 截断 GKP  
- P2  

## Open 默认

| 项 | 默认 |
|----|------|
| 2d 是否开 nn | **否**，只 full |
| overlap API 公开 | 是，`bosonic.gkp_logical_overlap` 短名 |
| 1d 是否重写循环 | 可 refactor 到 Gram 路径，数值不变 |
