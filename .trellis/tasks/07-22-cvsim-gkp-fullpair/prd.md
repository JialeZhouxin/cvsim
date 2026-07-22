# δ1 · GKP full-pair x-comb

## Goal

在现有 1D x 齿梳上，为 `gkp0`/`gkp1` 增加 **`cross="full"`**：所有齿对 \(k≠k'\) 的交叉项（扩 nn）。  
**诚实：仍非 2D 格、非 Gram 正交化。**

## Background

- 现：`cross="none"|"nn"`；nn 只邻齿  
- 用户锁 full GKP 子包 **δ1 = full-pair**  
- 未做仍：2D lattice / full Gram / 逻辑 Clifford

## Physics

两实峰（同 V，均值差 \(\Delta r=(δx,0)\)）高斯重叠：

\[
\mathrm{ov}=\exp\!\Bigl(-\frac{δx^2}{4ε}\Bigr)
=\exp\!\Bigl(-\frac{n^2\pi}{2ε}\Bigr),\quad δx=nΔ,\ Δ=\sqrt{2π}.
\]

\(n=1\) 时 \(\mathrm{ov}=e^{-π/(2ε)}\) ≡ 现 nn。

交叉表示（与 nn 同模板）：对每对 \((i,j), i<j\)：

```text
m = (x_i+x_j)/2
d = (x_i-x_j)/2
w = a_i a_j ov(|i-j|)
r̄± = (m, ±i d)
```

权重归一 \(\sum w=1\)（含对角 \(a_k^2\)）。

## Decisions

| # | 选择 |
|---|------|
| D0 | `CrossMode = "none"|"nn"|"full"` |
| D1 | full：所有 \(i<j\) 对，每对 2 复均值组件 |
| D2 | **K_full = (2N+1)²**（对角 2N+1 + 2·C(2N+1,2)） |
| D3 | `gkp0`/`gkp1` 同逻辑；只改 `_gkp_x_comb` |
| D4 | 默认仍 `cross="none"`（UAT/旧测不破） |
| D5 | 无 2D / 无 Gram / 无逻辑门 |
| D6 | 工程 docs 必改；理论 MD 可选 |

## Requirements

### R1 API

```python
gkp0(..., cross="full")
gkp1(..., cross="full")
```

### R2 tests

- N=2 full：`K=25`，∑w=1  
- full ⊃ nn 的邻对中心（集合包含）  
- Wigner(full) ≠ Wigner(none)  
- bad cross still raise  
- gkp1 full 半格偏移仍成立  

### R3 docs

- USER_ACCEPTANCE：full-pair 落地；未做改 2D/Gram  
- README 一行  

## Acceptance Criteria

- [x] **AC1** full 可构造，∑w=1，K=(2N+1)²  
- [x] **AC2** gkp0/gkp1 均支持；旧 none/nn 测绿  
- [x] **AC3** pytest **127**；UAT 8/8  
- [x] **AC4** 文档诚实：非 2D / 非 Gram  

## Out of Scope

- δ2 2D 格  
- δ3 Gram 正交  
- 逻辑 Clifford  
- P2  

## Notes

- N 大时 K~4N²，教学 N≤3–4  
- nn 路径可保留或走 full 过滤 |i-j|=1；保持现 nn 循环避免改测
