# Design · B1 门集

## 1. Scope

| 内 | 外 |
|----|----|
| Gaussian 多模 D/R/S/BS | S₂、通道、测量 |
| Fock 单模 D/R/S | Fock BS、Kerr |
| Bosonic 逐组件套 S,d | GKP、Wigner |
| 函数式 API | Circuit DSL |

## 2. Architecture（增量）

```text
cvsim/
  conventions.py          # 不变；可加 alpha→(dx,dp) helper
  gaussian/
    gates.py              # +displace, phase, beamsplitter；复用 apply_symplectic
    ...
  fock/
    gates.py              # +displace, phase
  bosonic/
    gates.py              # NEW: apply_symplectic_components + thin wrappers
  demos/                  # 可选 b1_*.py；pytest 为主
tests/
  test_b1_gaussian_gates.py
  test_b1_fock_gates.py
  test_b1_bosonic_gates.py
```

不建统一 Circuit。Bosonic 门内部调用与 Gaussian 相同的 `S` 构造逻辑——**共享构造函数**，避免两套 BS 矩阵：

- 推荐：`cvsim/gaussian/symplectic.py` 或 `gates.py` 内导出 `S_phase` / `S_squeeze` / `S_bs` / `d_displace`  
- Bosonic / 测试只 import 这些矩阵生成器 + `apply_symplectic` 风格更新

**最小重复原则：** 矩阵公式只写一处。

## 3. Physical contracts（xxpp, ħ=1）

### 3.1 Displacement

\[
d_x = \sqrt{2}\,\mathrm{Re}\,\alpha,\quad
d_p = \sqrt{2}\,\mathrm{Im}\,\alpha
\]

`S=I`，只加 `d` 到对应 mode 槽位。

### 3.2 Phase rotation

单模块：

\[
R(\theta)=\begin{pmatrix}\cos\theta&-\sin\theta\\\sin\theta&\cos\theta\end{pmatrix}
\]

嵌入 mode `i` 的 `(x_i,p_i)` 子空间（xxpp 下 index `i` 与 `m+i`）。

### 3.3 Squeeze

已有：`x→e^{-r}x`，`p→e^{r}p`。

### 3.4 Beam splitter

50:50 与一般 θ。推荐实现（实 BS，`φ=0` 优先验证）：

对 modes `i,j`，在 x 子空间与 p 子空间做同一 2×2 旋转：

\[
\begin{pmatrix}x_i'\\x_j'\end{pmatrix}
=
\begin{pmatrix}\cos\theta&\sin\theta\\-\sin\theta&\cos\theta\end{pmatrix}
\begin{pmatrix}x_i\\x_j\end{pmatrix}
\]

（符号约定：与笔记 Weedbrook 常见形式对齐；**实现后用 `S Ω Sᵀ = Ω` 单测锁死**。）

`φ≠0`：在 BS 前/后加相对相位，或用复 U 嵌入  
`S = [[Re U, -Im U],[Im U, Re U]]`（笔记 04 表）。B1 实现完整 `theta, phi`，测试至少覆盖 `phi=0` 与一个非零 `phi`。

### 3.5 Fock

- Phase: `c_n → e^{i n θ} c_n`
- Displace: `expm(α a† − α* a)`
- Squeeze: 已有

### 3.6 Bosonic

每组件：`V←S V Sᵀ`，`r̄←S r̄+d`（`r̄` 可复），`w` 不变。

## 4. Data flow（验收电路）

```text
AC-G1: vac --D(α)--> ⟨n⟩ ≈ |α|²
AC-G2: vac --S(r,0)--> --BS(π/4;0,1)--> ⟨n⟩_tot = sinh²r
AC-F*: 同 D 或 S，扫 cutoff
AC-B*: cat --R(θ)--> ∑w=1, peaks rotate
```

## 5. Trade-offs

| 选择 | 原因 | 代价 |
|------|------|------|
| 无 S₂ | B1 瘦 | EPR 源稍后 |
| 共享 S 生成 | 防 xxpp 两套公式 | bosonic 依赖 gaussian 矩阵 helper（可接受） |
| Fock 无 BS | 多模贵 | 跨后端 BS 对照只能 Gaussian |

## 6. Test strategy

- `S Ω Sᵀ ≈ Ω` 对 phase/squeeze/BS
- Analytic ⟨n⟩；G–F 对照
- 回归：全量 `pytest tests`
