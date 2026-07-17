# Design · B3 S₂

## 1. Scope

| 内 | 外 |
|----|----|
| `S_two_mode_squeeze` | φ、Fock |
| G + B `two_mode_squeeze` | 条件测量、通道 |
| pytest | 强制 UAT U7 |

## 2. Architecture

```text
cvsim/gaussian/symplectic.py  # + S_two_mode_squeeze
cvsim/gaussian/gates.py       # + two_mode_squeeze
cvsim/bosonic/gates.py        # + two_mode_squeeze
__init__.py exports
tests/test_b3_s2.py
```

## 3. Physics（ħ=1, xxpp, 实 r）

两模子空间 `(i,j)`，块序 `(x_i,x_j,p_i,p_j)` 对应全局下标  
`[i, j, m+i, m+j]`。

令 `ch=cosh r`，`sh=sinh r`。**EPR 型**（模间耦合；笔记 04 的 `[[ch I, sh Z],[…]]` 在 xxpp 下会退成无跨模关联，实现不用那块字面嵌入）：

\[
S_{4\times4}
=
\begin{pmatrix}
\mathrm{ch}&\mathrm{sh}&0&0\\
\mathrm{sh}&\mathrm{ch}&0&0\\
0&0&\mathrm{ch}&-\mathrm{sh}\\
0&0&-\mathrm{sh}&\mathrm{ch}
\end{pmatrix}
\quad\text{on }(x_i,x_j,p_i,p_j).
\]

嵌入 `2m×2m` 单位阵对应行列。

验证：`S Ω Sᵀ = Ω`。

真空 → S₂：

- 总光子 `⟨n₀⟩+⟨n₁⟩ = 2\sinh^2 r`
- 对称 `⟨n₀⟩=⟨n₁⟩=\sinh^2 r`
- 模间相关：`V[i,j]` 或 `V[i,m+j]` 等非零

## 4. API

```python
def two_mode_squeeze(state, r: float, mode1: int, mode2: int) -> State: ...
```

`mode1 != mode2`；越界 `IndexError`。

## 5. Trade-offs

| 选择 | 原因 |
|------|------|
| 无 φ | B3 瘦；可后加 |
| 无 UAT 强制 | 用户选 A；文档可后续补 U7 |
| 笔记 04 块形式 | 与 Ω 测互证 |

## 6. Tests

- symplectic identity
- ⟨n⟩ analytic
- correlation + det
- bosonic weight / V match
