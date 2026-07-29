# PRD: Phase1 F-SYMPLECTIC-CORE + F-STATE-FACTORY

## Goal

Implement vision P0 foundation features so all Gaussian unitary evolution goes through a validated symplectic apply path, and users/agents stop hand-rolling `(V, rbar)`.

**Spec anchor:** `docs/vision-gaussian-simulator.md` §4.1  
- `F-SYMPLECTIC-CORE`  
- `F-STATE-FACTORY`

## Scope

### In

1. `is_symplectic` / `validate_symplectic` in `cvsim/symplectic.py`
2. `apply_symplectic(state, S, d=None, *, validate=True)` — public, validated
3. Named gates remain thin wrappers (already are); ensure exports include `apply_symplectic`
4. `GaussianState` factories: vacuum (exists), coherent, thermal, squeezed, displaced_squeezed, tmsv, product
5. Tests for conventions, purity, TMSV, bad-S rejection, product embed

### Out

- Interferometer / Clements
- General `(X,Y)` channels
- Analyse API (purity helper optional only if needed by tests via det)
- Circuit changes
- AD / GBS

## Hard conventions (do not drift)

- ħ=1, xxpp, V_vac=I/2
- displace: d_x=√2 Re α, d_p=√2 Im α
- float64
- S Ω S^T = Ω with Ω = block [[0,I],[-I,0]]

## Acceptance

1. `is_symplectic` true on library gate products; false on broken S
2. `validate_symplectic` raises `ValueError` on bad S
3. `apply_symplectic(..., validate=True)` rejects bad S; `validate=False` still applies (escape hatch)
4. Factories match vision math (coherent means, squeezed vars, TMSV nbar=sinh²r, product of vacua = vacuum(2))
5. Existing suite still green; new tests added
6. Public exports updated (`apply_symplectic`, factories via `GaussianState.*`)

## Exit demo (manual)

```python
st = GaussianState.tmsv(0.5)
st2 = apply_symplectic(st, S_phase(2, 0.1, 0), validate=True)
```
