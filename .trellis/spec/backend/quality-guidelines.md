# Quality Guidelines

> Standards for `cvsim` and related backend code.

---

## Overview

MVP stack: **Python + uv + numpy + scipy**. No quantum libraries (DeepQuantum, Strawberry Fields, etc.) as implementation deps.

Acceptance is numeric: analytic identities and cross-representation trends, not “imports without error”.

---

## Forbidden Patterns

| Pattern | Why |
|---------|-----|
| Bind DeepQuantum/API into theory `*.md` | Notes are pure physics |
| Homodyne/PNRD/Hafnian in MVP without new PRD | Out of scope for three-simulators MVP |
| Early Circuit / backend abstraction with one use | YAGNI; three reps may share later |
| Treat Fock truncated-unitary `norm==1` as “no truncation error” | Truncated U is still unitary on ℂ^N; true deficit needs high-N evolve then project |

---

## Required Patterns

### Physics contracts (`cvsim`)

| Item | Value |
|------|--------|
| ħ | `1` |
| Quad order | `xxpp`: `(x_1..x_m, p_1..p_m)` |
| Vacuum | `V = I/2`, `r̄ = 0` |
| Pure single-mode Gaussian | `det V = 1/4` |
| Vacuum squeeze mean photon | `⟨n⟩ = sinh² r` |

### Fock truncation checks

1. Scan cutoff: `⟨n⟩(N)` approaches `sinh² r`.
2. For **norm deficit**: evolve at high cutoff, **project** amplitudes to low `N`, then `1 - ∑|c|² > 0`.

### Bosonic cat weights

Even/odd cat uses **4 components** (2 diagonal + 2 cross). Cross weights include overlap  
`ov = exp(-2α²)` (real α). After normalize: `∑ w_k = 1`.  
Wrong: set cross weight equal to diagonal without `ov`.

### Bosonic moment loop (full A)

| Item | Contract |
|------|----------|
| vacuum | single component `V=I/2`, `r̄=0`, `w=1` |
| weighted moments | `⟨O⟩=∑ w_k ⟨O⟩_k`; Homodyne `Var=⟨x²⟩−μ²` with `⟨x²⟩=∑w(var+μ²)` |
| return type | `float` real part; physical Im≈0 |
| single component | match Gaussian same gate/observable |
| gates | `w` unchanged |

Bosonic `loss(T)`: per-component same X,Y as Gaussian; **w unchanged**.

### Bosonic GKP `|0⟩` (diagonal tooth comb)

| Item | Contract |
|------|----------|
| API | `gkp0(epsilon, grid_size=N)` → `K=2N+1` components |
| spacing | `x_k = k √(2π)` |
| tooth | `V=½ diag(ε,1/ε)`, det=1/4 |
| weights | `w∝exp(−π ε k²)`, real, `∑w=1` |
| honesty | **no** p-teeth / cross → diagonal approx, not full pure GKP |

Out: `|1⟩_GKP`, 2D lattice, conditional Homodyne.

### Wigner grid (single-mode, ħ=1)

| Item | Contract |
|------|----------|
| API | `cvsim/wigner.py`: `wigner_gaussian` / `wigner_bosonic` / `wigner_grid` |
| vacuum | `V=I/2` → `W(0,0)=1/π` |
| pref | `1/(π √det(2V))`, quadratic `−½ δᵀV⁻¹δ` |
| complex mean | `exp(+½ sᵀV⁻¹s) exp(i δᵀV⁻¹s)`, `s=Im r̄` |
| Bosonic | `∑ w_k W_G`; return real part |
| cat check | odd cat: `W(0,0)<0` |

Out: Fock Wigner, multimode, GUI.

### Gaussian squeeze (xxpp, mode `i`)

- `x_i → e^{-r} x_i`, `p_i → e^{r} p_i`
- Vacuum single-mode: `V = ½ diag(e^{-2r}, e^{2r})`

### B1 gate contracts (ħ=1, xxpp)

| Gate | Contract |
|------|----------|
| `D(α)` | `d_x=√2 Re α`, `d_p=√2 Im α`; vac ⟨n⟩ = |α|² |
| `R(θ)` | (x,p) rotation; `S Ω Sᵀ = Ω` |
| `S(r)` | as above |
| `BS(θ,φ)` | unitary U embed `S=[[ReU,-ImU],[ImU,ReU]]`; only in `symplectic.py` |
| Bosonic gates | same S,d per component; **w unchanged** under unitary Gaussian |
| Fock B1 | single-mode D/R/S (MVP) |
| Fock full (1–2 mode) | `amps` ndim 1\|2; `kerr`; 2-mode `beamsplitter` via expm; `pnrd_probs`; no loss/Homodyne in this slice |

Hard AC patterns: `S→BS(π/4)` total ⟨n⟩ = sinh² r; pure 2-mode det V ≈ (1/4)²; Fock vs Gaussian ⟨n⟩ closes with cutoff.

Do **not** duplicate BS/phase matrices in bosonic — import `cvsim.gaussian.symplectic`.

### B2 Homodyne (Gaussian edge moments only)

| Item | Contract |
|------|----------|
| API | `homodyne_mean` / `homodyne_var` in `gaussian/observables.py` |
| Quad | `x_φ = x cosφ + p sinφ` |
| Mean | `⟨x_φ⟩ = cosφ r̄_x + sinφ r̄_p` |
| Var | `uᵀ V u` **central** (no r̄²) |
| Vacuum | any φ: mean=0, var=1/2 |
| After S(r) | var(0)=½e^{-2r}, var(π/2)=½e^{2r} |
| After D(α) | mean = √2 (Reα cosφ + Imα sinφ); var still 1/2 |

Out of B2: conditional update, sampling, Bosonic/Fock Homodyne.

### B3 two-mode squeeze S₂ (real r)

| Item | Contract |
|------|----------|
| Formula | only in `symplectic.S_two_mode_squeeze` |
| xxpp EPR block | `(x_i,x_j,p_i,p_j)`: x-mix `[[ch,sh],[sh,ch]]`, p-mix `[[ch,-sh],[-sh,ch]]` |
| Vacuum TMS | total `⟨n⟩=2 sinh² r`, each mode `sinh² r` |
| Pure 2-mode | `det V ≈ (1/4)²` |
| Bosonic | same S per component; `w` unchanged |

Out of B3: S₂ phase φ, Fock TMS.

### G-full Gaussian loop (condition + loss)

| Item | Contract |
|------|----------|
| `homodyne_condition` | ideal; no mode delete; `V'=V−vvᵀ/σ`, `r̄'=r̄+v(outcome−μ)/σ`; same `u` as edge API |
| singular V | measured direction var → 0; OK |
| `loss(T)` | `channels.py`; `0≤T≤1`; `X=√T`, `Y=(1−T)I/2` on acted quads (align `V_vac=I/2`) |
| `T=1` / `T=0` | identity / vacuum on acted modes |
| coherent + loss | `⟨n⟩ ≈ T\|α\|²` |

Out of G-full core: sampling, PNRD/Hafnian, Fock/Bosonic condition/loss.

---

## Testing Requirements

- Each milestone: pytest under `tests/` **and** `python -m cvsim.demos.m*_...` green.
- New observable/gate: at least one analytic or cross-backend assert.
- B1: `tests/test_b1_*.py` + symplectic `S Ω Sᵀ=Ω`.
- B2: `tests/test_b2_homodyne.py`.
- Final user acceptance: `cvsim/USER_ACCEPTANCE.md` + `python -m cvsim.demos.user_acceptance` (U1–U5; run-all then exit).
- Commands:

```bash
uv pip install numpy scipy pytest
python -m pytest tests -q
python -m cvsim.demos.user_acceptance
python -m cvsim.demos.m1_gaussian_squeeze
python -m cvsim.demos.m2_fock_cutoff_scan
python -m cvsim.demos.m3_cat_weights
```

---

## Code Review Checklist

- [ ] Conventions match `conventions.py` (no silent ħ/order mix)
- [ ] No quantum-lib dependency added without PRD change
- [ ] Theory MD unchanged re: API bindings
- [ ] Fock error claims use projection or ⟨n⟩ trend, not only `norm(Uψ)`
- [ ] Cat `∑w` and cross/diag structure covered by test
- [ ] New S matrices live in `symplectic.py` and pass Ω identity
- [ ] Bosonic reuses shared S/d (no second BS formula)
