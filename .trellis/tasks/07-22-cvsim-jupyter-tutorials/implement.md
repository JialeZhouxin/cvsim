# Implement · tutorials

1. `tutorials/README.md`  
2. `01_gaussian_beginner.ipynb`  
3. `02_fock_beginner.ipynb`  
4. `03_bosonic_beginner.ipynb`  
5. 链到根 / cvsim README  
6. 可选：用 `nbconvert --execute` 或手跑关键 assert（有 jupyter 则 execute）  
7. pytest 回归确认不破  

## Validate

```bash
.venv\Scripts\python.exe -m pytest tests -q
# 若已装 jupyter:
# .venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute tutorials/01_*.ipynb --stdout >nul
```
