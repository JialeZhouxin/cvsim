# Implement · γ gkp1

1. refactor/share comb in `gkp.py` + `gkp1`
2. export
3. tests
4. docs
5. pytest + UAT

## Validate

```bash
.venv\Scripts\python.exe -m pytest tests/test_bosonic_gkp.py tests/test_bosonic_gkp_cross.py tests/test_bosonic_gkp1.py tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```
