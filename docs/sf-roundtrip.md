# Strawberry Fields round-trip 对照脚本（vision §8）

本仓库核心约定：**ħ=1、xxpp 序**（`cvsim/conventions.py` `QUAD_ORDER="xxpp"`）。
Strawberry Fields 默认 **ħ=2、xpxp 序**。互通两处差异：

| 差异 | 仓库 (cvsim) | Strawberry Fields |
|------|--------------|-------------------|
| ordering | xxpp：`(x_1..x_m, p_1..p_m)` | xpxp：`(x_1,p_1,...,x_m,p_m)` |
| ħ | 1（真空 V=½I） | 2（真空 V=I） |

`cvsim.interop.to_xpxp/from_xpxp` 只做**排列**，不做 ħ 缩放（纯函数，调用方责任）。

## 转换链（cvsim → SF）

```python
V_xpxp, rbar_xpxp = to_xpxp(state.V, state.rbar)
V_sf = 2.0 * V_xpxp          # ħ=1 → ħ=2
rbar_sf = np.sqrt(2.0) * rbar_xpxp   # displacement 约定差异（SF 用无量纲 α 基）
```

rbar 缩放：SF 的位移向量在 ħ=2 下为 `(√2 Re α, √2 Im α)`；cvsim ħ=1 下
`(x, p) = (√2 Re α, √2 Im α)` 数值相同 → 传递时需确认 SF 期望的基（上述
√2 因子仅当 SF 侧用 α 而非 x,p 时）。

## 反向（SF → cvsim）

```python
V_xxpp, rbar_xxpp = from_xpxp(V_sf / 2.0, rbar_sf / np.sqrt(2.0))
```

## 完整对照（装 SF 后运行）

```bash
uv pip install strawberryfields  # optional; 本仓库无 SF 依赖
```

```python
import numpy as np
import strawberryfields as sf
from strawberryfields.ops import Sgate
import cvsim
from cvsim.interop import to_xpxp

# cvsim 侧：r=0.7 双模挤压真空（xxpp, ħ=1）
from cvsim.gaussian import GaussianState, two_mode_squeeze
g = two_mode_squeeze(GaussianState.vacuum(2), 0.7, 0, 1)

# SF 侧：同一物理态
prog = sf.Program(2)
with prog.context as q:
    Sgate(0.7) | q[0]
    Sgate(0.7) | q[1]
eng = sf.Engine("fock", backend_options={"cutoff_dim": 20})
state = eng.run(prog).state
V_sf = state.cov()          # ħ=2, xpxp
mu_sf = state.means()

# 对照（需缩放一致）
V_cv_xpxp, r_cv_xpxp = to_xpxp(g.V, g.rbar)
np.testing.assert_allclose(V_sf, 2.0 * V_cv_xpxp, atol=1e-6)
np.testing.assert_allclose(mu_sf, np.sqrt(2.0) * r_cv_xpxp, atol=1e-6)
```

## 已知坑

- SF 的 `Sgate(r)` 与 cvsim `squeeze(r)` 同一符号约定（x 挤压），但 SF
  `Sgate(r, phi=0)` 挤压的是 p 正交 —— 对照时核对方向，必要时用
  `Sgate(r, phi=np.pi)` 对齐。
- SF `state.cov()` 在 ħ=2 下真空为 I；无位移时 `means()` 全零。
- thewalrus ≥ 0.22 已是 xxpp（见 `docs/gbs-walrus.md`）—— 无需排列。
