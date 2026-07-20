# Bosonic 条件 Homodyne · 全复似然

## Goal

升级 `bosonic.homodyne_condition`：对 **所有** 组件（含复 `r̄`）做同一仿射条件更新 + 复高斯边缘似然乘权，再 `∑w→1`。替换教学 A「丢交叉」。

## Background

- 现 A：实峰 G 更新 + 实高斯似然；`Im r̄≠0` 丢弃
- 队列 ①→②采样→③Fock loss→④U8；**本任务仅 ①**
- 用户选 **A：复仿射 + 复高斯边缘**

## Decisions

| # | 选择 |
|---|------|
| D1 | **A：全组件复仿射**；`μ=u·r̄` 可复；`σ=uᵀVu` 实 |
| D2 | `L∝σ^{-1/2} exp(−(o−μ)²/(2σ))`（`o` 实，`μ` 可复 → `L` 可复） |
| D3 | **去掉** `imag_tol` 丢弃逻辑（或保留参数但默认不用丢弃） |
| D4 | 实单组件仍 ≡ G；不删模 |
| D5 | 旧测 `test_all_complex_raises` / cat「无复组件」**改写** |

## Requirements

### R1 更新（每组件 k）

```text
u real, V real SPD
v = V u
σ = uᵀ V u > ε
μ = u · r̄_k          # complex OK
V' = V − vvᵀ/σ
r̄' = r̄_k + v (o − μ)/σ   # complex OK
L_k = (2πσ)^{-1/2} exp( −(o−μ)² / (2σ) )
w_k⁰ = w_k · L_k
```

最后 `w ← w⁰ / Σ w⁰`（Σ 可复；物理 `∑w≈1`）。

### R2 API

```python
def homodyne_condition(state, mode, phi, outcome) -> BosonicState
```

- 不再因全复而 raise「no real-mean」
- σ 过小仍 ValueError（同 G）
- docstring 诚实：复似然为教学闭式推广，非完整 Generaldyne POVM 文献全式

### R3 文件

- 改 `cvsim/bosonic/observables.py`
- 改 `tests/test_bosonic_condition.py`（+ 可选 `test_bosonic_cond_complex.py`）
- quality / README 一行；UAT 不破

## Acceptance Criteria

- [x] **AC-1** 单组件实 ≡ G
- [x] **AC-2** even cat：K=4 + 复中心残量
- [x] **AC-3** `∑w≈1`；+diag `|w|` > −diag
- [x] **AC-4** 纯交叉不 raise
- [x] **AC-5** pytest + UAT

## Out of Scope

- ② 采样 · ③ Fock loss · ④ U8
- 删模 · Generaldyne 有限噪声 · 完整 char-func POVM

## Notes

- 复 `exp(−(o−μ)²/(2σ))` 用 `cmath`/`np.exp` 复数即可
- 归一用 `s=sum(raw_w)`；`|s|~0` → ValueError
