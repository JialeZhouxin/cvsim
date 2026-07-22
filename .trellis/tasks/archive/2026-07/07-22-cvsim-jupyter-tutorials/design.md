# Design · Jupyter 三教程

## Layout

```text
tutorials/
  README.md
  01_gaussian_beginner.ipynb
  02_fock_beginner.ipynb
  03_bosonic_beginner.ipynb
```

## Kernel / import

First code cell of each notebook:

```python
# 从仓库根启动 Jupyter；或本 cell 兜底
import sys
from pathlib import Path
ROOT = Path.cwd()
if not (ROOT / "cvsim").is_dir():
    ROOT = Path.cwd().parent  # notebooks sometimes open inside tutorials/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

## Notebook construction

Prefer **nbformat** write via short Python script, or hand-write JSON.  
Keep cells: markdown / code alternate. No widgets.

## Plot policy

```python
try:
    import matplotlib.pyplot as plt
    HAS_PLT = True
except ImportError:
    HAS_PLT = False
```

Wigner / var plots only if `HAS_PLT`.

## Content sources (reuse numbers)

| Tutorial | Mirror demos / tests |
|----------|----------------------|
| T1 | `m1_gaussian_squeeze`, U2/U3 |
| T2 | `m2_fock_cutoff_scan`, fock wigner tests |
| T3 | `m3_cat_weights`, gkp tests |

## Docs touch

- `tutorials/README.md` new  
- `cvsim/README.md` + root `README.md`：一行「新手教程」链接  

## Risk

| 风险 | 缓解 |
|------|------|
| 路径错 | 双路径 ROOT 探测 |
| 过长 | 每本 ≤ ~15–20 cells |
| 过 API | 只讲当篇用到的 import |
