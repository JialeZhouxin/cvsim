# Implement · G6

## Checklist

1. moments helpers + mean/var in `fock/observables.py`
2. sample via HO wavefunctions + grid
3. export `__init__`
4. tests
5. docs 未做/矩阵
6. pytest + UAT

## Validate

```bash
.venv\Scripts\python.exe -m pytest tests/test_fock_homodyne.py tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```
