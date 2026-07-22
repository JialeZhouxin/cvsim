# Implement · δ1 full-pair

1. `CrossMode` + full 分支 in `gkp.py`  
2. tests  
3. docs  
4. pytest + UAT  

## Validate

```bash
.venv\Scripts\python.exe -m pytest tests/test_bosonic_gkp.py tests/test_bosonic_gkp_cross.py tests/test_bosonic_gkp1.py tests/test_bosonic_gkp_full.py tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```
