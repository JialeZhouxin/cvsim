# Design · Wigner G+B

## 1. Formula (ħ=1, single mode, xxpp)

Let `r=(x,p)ᵀ`, `V` real SPD 2×2, `μ = Re(r̄)`, `s = Im(r̄)`.

**Real-mean Gaussian** (standard, vacuum check):

\[
W_0(\mathbf r)=\frac{1}{\pi\sqrt{\det(2V)}}\,
\exp\bigl(-\tfrac12(\mathbf r-\mu)^{\mathsf T}V^{-1}(\mathbf r-\mu)\bigr)
\quad?\quad
\]

Calibrate: `V=I/2` → want `W(0)=1/π`.  
`det(2V)=1` → prefactor `1/π` with `exp(-½ δᵀ (I/2)^{-1} δ)=exp(-δᵀδ)` →  
`W=1/π exp(-(x²+p²))` ✓ if prefactor `1/(π√det(2V))` and quadratic `-½ δᵀ V^{-1} δ`.

**Complex mean** (note 04):

\[
W = W_{\mathrm{env}}(\delta;V)\cdot \exp\bigl(i\,\delta^{\mathsf T} V^{-1} s\bigr)
\]

（若 cat 负区不够，试系数 2；以测为准。）

**Bosonic:**

\[
W=\sum_k w_k\, W_G(V_k,\bar r_k)
\]

Return `float(W.real)` on grid.

## 2. Files

```text
cvsim/wigner.py           # point + grid; G and B
cvsim/__init__ or demos   # optional export
tests/test_wigner.py
cvsim/README.md           # one section
quality-guidelines.md
```

## 3. API

```python
def wigner_point_gaussian(V, rbar, x, p) -> complex: ...
def wigner_gaussian(state: GaussianState, x, p) -> float: ...
def wigner_bosonic(state: BosonicState, x, p) -> float: ...
def wigner_grid(state, lim=5.0, n=81) -> tuple[np.ndarray, np.ndarray, np.ndarray]: ...
```

`wigner_grid`：`isinstance` G vs B.

## 4. Perf

`n=81` → 6.5k points × K；cat K=4 可接受。向量化可选（后做）。

## 5. Tests

prd AC-W*。
