# Design · notes align A

## Patch map

| File | Where | Add |
|------|-------|-----|
| `02-Gaussian表示原理.md` | §4.1 扩；§3 或新小节 loss | 边缘/条件/采样/loss |
| `01-Fock表示原理.md` | §4 后或 §3.x | Kraus loss |
| `03-Bosonic表示原理.md` | §5 | B cond/sample + Wigner 钉死 |
| `术语表.md` | §6 测量 + 通道 | 词条 |
| `README.md` | 最小闭环 | 第 5 概念步 |
| `04-...md` | G/B 测量节末 | 指针 1 行 |

## Formula cards（正文可原样/略改）

### G Homodyne condition

```text
u = (… cosφ on x_i, sinφ on p_i …)   # xxpp
v = V u,  σ = uᵀ V u,  μ = u · r̄
V' = V − v vᵀ / σ
r̄' = r̄ + v (o − μ) / σ
# ideal: no mode delete; measured direction var → 0
```

### G sample

```text
o ~ N(μ, σ)   # independent of whether one later conditions
```

### G/B loss (Gaussian channel)

```text
X = √T on acted quads,  Y = (1−T)(I/2) on those diagonals
V ← X V Xᵀ + Y,  r̄ ← X r̄
```

### F Kraus

```text
E_k |n⟩ = √C(n,k) (√T)^{n−k} (√(1−T))^k |n−k⟩
ρ' = Σ_k E_k ρ E_k†
|1⟩: ρ00=1−T, ρ11=T
```

### B condition (teaching)

```text
same V',r' per component; μ may be complex; L may be complex
w ← w L; renorm Σw
```

### B sample (teaching)

```text
pool real-mean peaks; mixture then Gaussian
cross (complex centres) out of pool
```

### Wigner (ħ=1 single-mode Gaussian)

```text
W ∝ 1/(π √det(2V)) exp(−½ δᵀ V⁻¹ δ)   # real mean
vacuum: W(0,0)=1/π
complex mean: extra phase / growth factors as teaching note
Bosonic: Σ w_k W_k
```

## Ban list in theory MD

`cvsim`, `dq.`, `deepquantum`, `GaussianState`, `FockState`, `BosonicState`,
`homodyne_condition`, `homodyne_sample`, `FockDensity`, `USER_ACCEPTANCE`,
`pytest`, path `cvsim/`

Exception: root README **工程段**已有 cvsim 链接可保留；新增理论句仍不绑 API。

## Style

- Match existing terse Chinese + LaTeX
- No new top-level file
- Surgical: touch only needed sections
