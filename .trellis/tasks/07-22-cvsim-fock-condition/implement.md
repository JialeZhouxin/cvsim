# Implement · Fock condition

1. `fock/observables.py` condition + sample_and_condition  
2. export `__init__.py`  
3. `tests/test_fock_condition.py`  
4. docs  
5. pytest + UAT  

## Validate

```bash
.venv\Scripts\python.exe -m pytest tests/test_fock_condition.py tests/test_fock_homodyne.py tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```
