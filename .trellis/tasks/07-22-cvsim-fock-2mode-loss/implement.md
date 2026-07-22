# Implement · G5

1. 扩 `FockDensity` nmode 1|2 + from_pure 2 模  
2. `loss(..., mode=)` 2 模 Kronecker Kraus  
3. observables 2 模 dens  
4. tests + docs  
5. pytest + UAT  

## Validate

```bash
.venv\Scripts\python.exe -m pytest tests/test_fock_loss.py tests/test_fock_2mode_loss.py tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```
