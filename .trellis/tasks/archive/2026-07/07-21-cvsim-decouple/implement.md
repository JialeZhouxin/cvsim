# Implement · 拆耦合

## Steps

1. `cvsim/symplectic.py` 从 gaussian 抽出
2. gaussian shim re-export
3. gates import 改共享
4. `from_gaussian` duck
5. 轻测 + README
6. pytest + UAT + `rg` 验 B 无 `cvsim.gaussian`

## Validate

```bash
rg "from cvsim\.gaussian|import cvsim\.gaussian" cvsim/bosonic
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```
