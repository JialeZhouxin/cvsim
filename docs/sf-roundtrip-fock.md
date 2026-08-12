# Strawberry Fields Fock round-trip 对照（vision §4 F6）

Fock 基互操作：cvsim `cvsim.fock` ↔ Strawberry Fields **fock backend**。
与 Gaussian 互操作（`docs/sf-roundtrip.md`，需 ħ=2/ħ=1 的 2.0/√2 缩放链）不同：
**Fock 基幺正与 ħ 无关** — D/S/BS/S₂/R/K 矩阵元只含 α/ζ/θ/κ，无 ħ → 只需复数逐位比对，无任何缩放因子。

## 门与态约定对照

| 门/态 | SF（fock backend） | cvsim fock | 对应关系 |
|--------|--------------------|------------|----------|
| 位移 | `Dgate(r, phi)` = D(r e^{iφ}) | `displace(state, alpha)` | alpha = r e^{iφ} |
| 挤压 | `Sgate(r, phi)` = S(r e^{iφ}) | `squeeze(state, r)`（实 r） | SF phi=0 |
| 分束器 | `BSgate(θ, φ)` | `beamsplitter(state, θ, φ)` | **cvsim(θ,φ) = SF(−θ,−φ)** |
| 双模挤压 | `S2gate(r, phi)` | `two_mode_squeeze(state, r)`（实 r） | SF phi=0 |
| 相位 | `Rgate(φ)` = exp(iφa†a) | `phase(state, θ)` | θ=φ |
| Kerr | `Kgate(κ)` = exp(iκa†²a²) | `kerr(state, χ)` | χ=κ |
| 真空 | 默认初始态 | `FockState.vacuum(N, m)` | — |
| Fock | `Fock(n)` | `FockState.fock(n, N)` / `fock2` | — |
| 相干 | `Dgate`/`Coherent(alpha)` | `FockState.coherent(N, alpha)` | — |
| 热态 | `Thermal(nbar)` | `FockDensity.thermal(N, nbar)` | — |

**BS 映射（实证）**：cvsim `beamsplitter(θ,φ)` ≡ SF `BSgate(−θ,−φ)` — SF 0.23 fock
backend 实际符号约定与文档公式相反，全张量逐位实证 max|Δ|=1.1e-16（+θ,+φ 则差 1.39）。
对照时 cvsim 侧参数**取负**。

## 密度矩阵导出格式（F6 退出判据 3）

`FockDensity.rho` = (N^m, N^m) complex128，多模 **C-order**（`amps.reshape(N,N).ravel()`
序，|n0 n1…⟩ 的 n0 为慢指标）。SF 多模 `state.dm()` 返回 2m-D 张量、轴序
(n0, n0', n1, n1', …) → 转置展平后与 `FockDensity.rho` **逐位一致**（无排列、无缩放）：

```python
rho_sf = np.asarray(state.dm())                     # 2 模时 shape (N, N, N, N)
rho_sf = rho_sf.transpose(0, 2, 1, 3).reshape(N * N, N * N)   # == FockDensity.rho
```

```python
# cvsim → 外部（导出）
rho = FockDensity.from_pure(state).rho     # (N^m, N^m)
np.savez("rho.npz", rho=rho)

# SF 侧读取
import numpy as np
rho_sf = np.load("rho.npz")["rho"]          # 同一 (N^m, N^m) C-order 基
```

## 双向 copy-paste

### cvsim → SF（以 cvsim 结果为基准，SF 侧复现同一物理实验）

```python
import numpy as np
import strawberryfields as sf
from strawberryfields.ops import Sgate, Dgate, Kgate, BSgate

prog = sf.Program(2)
with prog.context as q:
    Sgate(0.4) | q[0]                        # cvsim squeeze(st, 0.4, mode=0)
    Dgate(0.3, 0.2) | q[0]                   # cvsim displace(st, 0.3*exp(1j*0.2), mode=0)
    Dgate(0.2, 0.5) | q[1]                   # cvsim displace(st, 0.2*exp(1j*0.5), mode=1)
    BSgate(0.8, 0.4) | (q[0], q[1])          # cvsim beamsplitter(st, -0.8, -0.4) ← 取负
    Kgate(0.1) | q[1]                        # cvsim kerr(st, 0.1, mode=1)
eng = sf.Engine("fock", backend_options={"cutoff_dim": 45})   # 每个 prog 新建 Engine！
rho_sf = np.asarray(eng.run(prog).state.dm())
```

### SF → cvsim（SF 为基准，cvsim 对照；golden 路线）

SF 无「加载任意 ket」API → 反向互操作以 SF 为基准一次性生成 golden
（`tools/gen_sf_golden.py` → `tests/_golden/sf_fock_golden.npz`），cvsim 侧对照：

```python
# SF 侧：S(0.5)|0> @ cutoff 50
prog = sf.Program(1)
with prog.context as q:
    Sgate(0.5) | q[0]
eng = sf.Engine("fock", backend_options={"cutoff_dim": 50})
rho_sf = np.asarray(eng.run(prog).state.dm())

# cvsim 侧：同一物理态
from cvsim.fock.state import FockState
from cvsim.fock.density import FockDensity
rho_cv = FockDensity.from_pure(FockState.squeezed(50, 0.5)).rho

np.testing.assert_allclose(rho_cv, rho_sf, atol=1e-9)   # 复数逐位（相对相位保留）
```

## 已知坑

- **Engine 复用残留**（实证）：同一 `sf.Engine("fock")` 实例连续跑多个 prog，后一个
  结果被前一个污染 → 每个 prog 必须新建 Engine。
- **Fock(n) 预备态 `ket()` 为 None**（SF 0.23 实证）：`pure=False` → 对照一律用
  `state.dm()`（dm 保相对相位，顺带覆盖密度导出格式）。
- **cutoff 分层**（泄漏扫描实证）：S(0.5)@50 残留 6e-10、D(0.4)@12 7.6e-11、
  S2(0.5)@30 3.6e-11、chain@45 1.7e-11、R/K/BS/thermal@10 ~0 → 对照 atol=1e-9。
- **scipy simps shim**：scipy>=1.15 把 `simps` 改名 `simpson`；SF 0.23 import 时直接
  `from scipy.integrate import simps` → 生成脚本先 `si.simps = si.simpson` 再 import SF。
- **setuptools<81**：`strawberryfields.apps` 用 pkg_resources（弃用告警，未来移除）→ pin `<81`。
- **np.math 移除**：numpy>=2 无 `np.math`（SF 老路径）；numpy 2.5.2 实证可用。
- **版本锁**：golden npz metadata 内嵌 SF/thewalrus/scipy/numpy 版本 + 生成日期；测试只读
  npz、不 import SF，SF 漂移不影响套件。
- **BS 符号**：见上表 — cvsim 侧参数取负（含 chain 中 BS(0.8,0.4) → `beamsplitter(-0.8,-0.4)`）。

## 重新生成 golden

```bash
uv venv /tmp/sfenv
uv pip install --python /tmp/sfenv "strawberryfields" "setuptools<81"
/tmp/sfenv/Scripts/python.exe tools/gen_sf_golden.py   # ~30s（含自检，逐项打印 max|d|）
py -3 -m pytest tests/test_sf_golden_f6.py -q          # 对照套件（无 SF import）
```

（Linux 路径为 `/tmp/sfenv/bin/python`。）
