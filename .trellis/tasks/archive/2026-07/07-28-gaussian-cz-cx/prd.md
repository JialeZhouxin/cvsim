# PRD: Gaussian CZ/CX 门

## 背景

我们高斯模拟器缺少两个关键的两模高斯门：CZ（Controlled-Z）和 CX（Controlled-X/SUM），DeepQuantum 的 `gate.py` 中有这两个。它们是 GKP 纠错和 cluster state 教学的基础。

## 需求

### R1: 底层 symplectic 矩阵

在 `cvsim/symplectic.py` 中新增两个函数，与现有 `S_squeeze`/`S_beamsplitter` 风格一致：

- `S_CZ(nmode, weight, mode1, mode2)` — CZ = exp(i·weight·x̂₁·x̂₂)
  - 作用：p₁ → p₁ + weight·x₂，p₂ → p₂ + weight·x₁
  - xxpp 顺序，返回 (2·nmode, 2·nmode) 矩阵

- `S_CX(nmode, weight, mode1, mode2)` — CX = exp(-i·weight·x̂₁·p̂₂)
  - 作用：p₁ → p₁ - weight·p₂，x₂ → x₂ + weight·x₁
  - xxpp 顺序，返回 (2·nmode, 2·nmode) 矩阵

### R2: 门函数封装

在 `cvsim/gaussian/gates.py` 中新增两个薄封装函数（调用 `apply_symplectic`）：

- `cz(state, weight, mode1, mode2)` → `GaussianState`
- `cx(state, weight, mode1, mode2)` → `GaussianState`

不修改传入的 state，返回新 GaussianState。

### R3: 导出

在 `cvsim/gaussian/__init__.py` 的 `__all__` 中加入 `cz` 和 `cx`。

### R4: 测试

至少覆盖：
- CZ/CX 作用于两模真空：验证 det V 和光子数（预期真空 → 非真空）
- CX 作用于压缩态 + 真空：验证控制行为正确
- 参数校验：mode1 == mode2 抛 ValueError

## 非需求（不做）

- 不暴露底层 `S_CZ`/`S_CX` 在 `__all__` 中（跟 `S_squeeze` 等一样，内部分布即可）
- 不做非幺正通道版
- 不做复 weight

## 验收标准

1. `pytest cvsim/ -x -q` 全绿，新增测试通过
2. 可从 `cvsim.gaussian` 直接 import `cz` 和 `cx`
3. 两模真空 + CZ(weight=0.5)：`<n>` > 0（光子数 > 0），`det V = (1/4)^2`（幺正保纯）
4. 两模真空 + CX(weight=0.3) + CX(weight=-0.3)：回到真空（逆操作验证）
5. `mode1 == mode2` 抛 `ValueError`
