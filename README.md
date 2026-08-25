# cvsim · 连续变量光量子模拟器

> Gaussian / Fock / Bosonic 三表示最小模拟器，理论先行，仅依赖 `numpy` + `scipy`。
> 约定：`\hbar = 1`，正交序 **xxpp**，真空 `V = I/2`。

三表示同物理、异结构、异代价——同一套电路可跨表示对账验证：

| 表示 | 存什么 | 何时用 | 代价 |
|------|--------|--------|------|
| **Gaussian** | 协方差 `V` + 位移 `r̄` | 大规模高斯演化、GBS | `O(m²)` |
| **Fock** | 截断光子数振幅 / 密度 | 小系统、非高斯门、精确 Fock 概率 | `N^m` |
| **Bosonic** | `{(V_k, r̄_k, w_k)}` | Cat / GKP、高斯叠加非高斯态 | `O(K·m²)` |

## 安装

```bash
uv venv && .venv\Scripts\activate   # Windows；Linux/macOS 用 source .venv/bin/activate
uv pip install -e ".[dev]"
```

或纯依赖：

```bash
uv pip install numpy scipy
```

## 快速开始

```python
import cvsim
from cvsim.gaussian import GaussianCircuit, GaussianState, purity

cir = GaussianCircuit(nmode=2)
cir.squeeze(mode=0, r=0.5)
cir.beamsplitter(0, 1, theta=0.4)
state = cir.run()

print(purity(state))   # pure TMSV-like → 1.0
```

Fock：

```python
from cvsim.fock import FockCircuit

fc = FockCircuit(nmode=2, cutoff=8)   # default initial = vacuum
fc.squeeze(mode=0, r=0.5)
state = fc.run()
```

## 能力矩阵

| 表示 | 初态 | 门 | 通道 | 测量 / 分析 |
|------|------|----|------|-------------|
| **Gaussian** | vacuum / coherent / thermal / squeezed / displaced_squeezed / tmsv / product | D/R/S/BS/S₂/Fourier/MZ/CZ/CX/interferometer | loss / amplifier / phase_noise / general `(X,Y)` | Homodyne + Heterodyne；purity / ν / entropy_vn / ptrace / log_neg / fidelity |
| **Fock** | `fock`/`fock2`/`FockDensity`/`FockSparse` | D/R/S/Kerr/BS/S₂/CZ/CX/MZ/interferometer + `FockCircuit` | loss / amplifier / phase_noise / apply_kraus | norm / ⟨n⟩ / `pnrd_probs` / PNR·Homodyne·Heterodyne / Wigner / IR roundtrip |
| **Bosonic** | 真空 / cat / `gkp0`/`gkp1` | D/R/S/BS/S₂ | loss `(T, nbar=0)` | ∑w / 加权 ⟨n⟩ / Homodyne / sample / condition |

辛矩阵只在 `cvsim/symplectic.py`（G/B 共享地基）。Gaussian 有 `GaussianCircuit`（含 feedforward）。Bosonic 不 import Gaussian 包——三表示边界由 `tests/test_ast_boundaries.py` + ADR 守护。

## 本地图形化实验室（Lab UI）

```bash
python -m cvsim.lab   # 启动 http://127.0.0.1:8000
```

浏览器内可视化光路编辑、Wigner 函数、扫描、Fock/Bosonic 双后端。愿景见 [`docs/vision-gaussian-lab-ui.md`](./docs/vision-gaussian-lab-ui.md)。

## 教程

三表示各一本新手 Jupyter：[`tutorials/README.md`](./tutorials/README.md)

## 项目结构

```
cvsim/
├── cvsim/
│   ├── gaussian/        # Gaussian：V/r̄，m→100，GBS adapter
│   ├── fock/           # Fock：截断光子数；state/density/sparse/circuit/ir
│   ├── bosonic/        # Bosonic：{(V_k, r̄_k, w_k)}；cat/GKP
│   ├── interop/        # 跨表示桥（xxpp↔xpxp 等）
│   ├── lab/            # 本地图形化实验室 UI（前端 + server）
│   ├── symplectic.py   # 辛矩阵地基（G/B 共享）
│   ├── wigner.py       # Wigner 函数
│   ├── backend.py      # 统一后端接口
│   ├── bridge.py       # 表示间观测桥
│   └── ...
├── tests/              # pytest 套件（1000+ 测试）
├── benchmarks/         # m=100 基准
├── tutorials/          # 新手 Jupyter
├── docs/               # vision / API 稳定性 / ADR
└── pyproject.toml
```

## 开发

```bash
python -m pytest tests/ -q          # 全量测试
ruff check cvsim/                    # 代码风格
mypy cvsim/                          # 类型检查
```

- **API 稳定性政策**：[`docs/api-stability.md`](./docs/api-stability.md)——公开面以 `__all__` 为准，由 `tests/test_public_api.py` 冻结
- **架构决策记录**：[`docs/adr/`](./docs/adr/)——模块边界、Bosonic 架构、IR schema 等
- **代码审查标准**：[`CODE_REVIEW_GUIDE.md`](./CODE_REVIEW_GUIDE.md)

## 许可证

MIT
