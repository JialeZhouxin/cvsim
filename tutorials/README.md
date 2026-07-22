# cvsim 新手 Jupyter 教程

三本笔记本，对应三个表示。**目标：会跑、懂数字、知道何时换表示。**

## 阅读顺序

| 顺序 | 文件 | 学什么 |
|------|------|--------|
| 1 | [01_gaussian_beginner.ipynb](./01_gaussian_beginner.ipynb) | 真空·挤·位移·BS·loss·Homodyne |
| 2 | [02_fock_beginner.ipynb](./02_fock_beginner.ipynb) | 截断·PNRD·loss→ρ·Wigner |
| 3 | [03_bosonic_beginner.ipynb](./03_bosonic_beginner.ipynb) | cat·GKP·权重·Gram |

理论笔记仍建议：术语表 → 00 → **02 Gaussian** → 01 Fock → 03 Bosonic。

## 环境

在**仓库根** `cv-photonic-notes/`：

```bash
uv venv
.venv\Scripts\activate          # Windows
uv pip install numpy scipy
# 可选：笔记本 UI + 图
uv pip install jupyter matplotlib
```

启动（推荐在仓库根）：

```bash
jupyter notebook tutorials/
# 或
jupyter lab tutorials/
```

每本第一格会尝试把 `cvsim` 加进 `sys.path`（从根或 `tutorials/` 打开都能用）。

## 每本结构

1. 这是啥 / 为啥用  
2. 约定（ħ=1，xxpp，`V=I/2`）  
3. 最小可跑闭环  
4. 数字检查  
5. 再进一步  
6. 诚实边界 + 何时换表示  
7. **自检 assert**（全绿再往下）

## 无 Jupyter 时

同样物理可用命令行 demo：

```bash
python -m cvsim.demos.m1_gaussian_squeeze
python -m cvsim.demos.m2_fock_cutoff_scan
python -m cvsim.demos.m3_cat_weights
python -m cvsim.demos.m4_cross_rep      # 跨表示同一套数
```

## 维护

notebook 由 `_build_notebooks.py` 生成。改内容时优先改该脚本再 `python tutorials/_build_notebooks.py`，避免手改 JSON 漂移。
