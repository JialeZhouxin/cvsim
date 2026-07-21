# Design · G6 Fock Homodyne

## API

`cvsim/fock/observables.py`（export `__init__`）:

```python
homodyne_mean(state: FockState|FockDensity, mode=0, phi=0.0) -> float
homodyne_var(state, mode=0, phi=0.0) -> float
homodyne_sample(state, mode=0, phi=0.0, *, rng=None) -> float
```

1 模 only；`mode!=0` raise。

## Moments (ħ=1)

```text
a  = annihilation(N) truncated
⟨a⟩ = ψ† a ψ  or  Tr(ρ a)
⟨x⟩ = √2 Re⟨a⟩
⟨p⟩ = √2 Im⟨a⟩
⟨x_φ⟩ = ⟨x⟩cosφ + ⟨p⟩sinφ

⟨a†a⟩, ⟨a²⟩, ⟨a†²⟩ from state
⟨x²⟩ = ⟨a†a⟩ + 1/2 + Re⟨a²⟩   # standard ħ=1
⟨p²⟩ = ⟨a†a⟩ + 1/2 - Re⟨a²⟩
⟨{x,p}/2⟩ = Im⟨a²⟩
Var(x_φ) = c²⟨x²⟩ + s²⟨p²⟩ + 2sc⟨xp⟩_sym - μ²
```

Verify vac: ⟨x²⟩=⟨p²⟩=1/2。

## Sample

1. Build quadrature grid `q ∈ [-L,L]`  
2. Rotate state by `R(-φ)` then use **x** marginal (or apply phase in a-space)  
3. Pure: ψ(x) from Fock basis harmonic oscillator wavefunctions (scipy `eval_hermite` + gauss weight)  
4. Density: ρ_xx' on grid expensive → **teaching**: diagonalize ρ in Fock, mixture of pure |ψ_k⟩² weighted by eigenvalues ≥0  
5. Discrete normalize → `rng.choice`

Constants: `L=8`, `nq=513` odd center 0.

## Tests

`tests/test_fock_homodyne.py`

- vac mean/var  
- coherent vs G  
- squeeze var vs analytic (atol 1e-2)  
- sample vac stats N=3000 seed  

## Docs

USER_ACCEPTANCE 未做；README 能力矩阵一行。
