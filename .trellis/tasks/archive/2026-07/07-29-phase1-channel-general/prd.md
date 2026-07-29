# PRD — Phase1: F-CHANNEL-GENERAL

**Vision ref:** `docs/vision-gaussian-simulator.md` §4.1 F-CHANNEL-GENERAL  
**Task:** `.trellis/tasks/07-29-phase1-channel-general`  
**Status:** planning

---

## Goal

Implement the general Gaussian CPTP channel `(X, Y, d)` and the named
presets that special-case it, closing the last P0 block of Phase 1.

A single-shot Gaussian channel acts on `(V, r̄)` (xxpp, ħ=1) as:

$$
\bar r \mapsto X\bar r + d,\qquad V \mapsto X V X^{\mathsf T} + Y
$$

with the **complete-positivity (CP) condition**

$$
Y + i\Omega - i\,X\Omega X^{\mathsf T} \succeq 0
$$

(Hermitian PSD in the complex sense).

---

## Scope (in)

1. `apply_gaussian_channel(state, X, Y, d=None, *, validate=True)` — core.
2. Presets as special cases of `(X, Y)`:
   - `loss(state, T, mode=None, nbar=0.0)` — **refactor existing** to route
     through `apply_gaussian_channel` (numbers must not change).
   - `amplifier(state, G, mode=None, nbar=0.0)` — quantum-limited default
     `nbar=0`.
   - `phase_noise(state, sigma, mode=None)` — **one** agreed kernel (see Open Q).
3. CP validation helper `is_cp_channel(X, Y, *, atol)` / `validate_channel`.
4. Exports in `cvsim.gaussian` + `cvsim.gaussian.channels`.
5. Tests: CP boundary, loss regression, amplifier photon trend, composition.

## Scope (out)

- Correlated multi-mode loss (P1+; explicit `(X,Y)` only).
- Non-Gaussian noise / threshold detection.
- Circuit DSL wiring (`GaussianCircuit.loss` already exists; `amplifier` /
  `phase_noise` DSL hooks are a separate follow-up, not this task).
- F-ANALYSE quantities (entropy, fidelity, log-neg) — separate task.

---

## Hard conventions (immutable)

- ħ=1, xxpp order, `V_vac = I/2`, float64.
- `Ω = [[0, I], [-I, 0]]` from `cvsim.conventions.omega`.
- Functional style: every channel returns a **new** `GaussianState`.
- `V ← 0.5 (V + Vᵀ)` symmetrization after the update (matches existing `loss`).

---

## Preset math (locked)

| Preset | X (per acted mode block) | Y (per acted mode block) | Constraint |
|--------|--------------------------|--------------------------|------------|
| Loss T∈[0,1], env n̄ | `√T · I₂` | `(1−T)(n̄+½) · I₂` | `0≤T≤1`, `n̄≥0` |
| Amplifier G≥1, n̄_amp | `√G · I₂` | `(G−1)(n̄_amp+½) · I₂` | `G≥1`, `n̄≥0` |
| Phase noise σ | `I₂` (no damping) | `σ² · diag(1,1)` on acted quads? | **see Open Q** |

Loss `nbar=0` ⇒ pure loss into vacuum (legacy behavior preserved).

---

## Open question (needs user decision before implementation)

### Phase-noise kernel

Vision §11 left the phase-noise model open. Three candidate kernels, all
Gaussian-CPTP, differing in physics:

| Option | Model | X | Y (acted mode) | Physics |
|--------|-------|---|-----------------|---------|
| **A** | Phase diffusion (small-angle Gaussian) | `I₂` | `σ² · (½)·[[1,0],[0,1]]`? | Isotropic added noise; simplest, **not** the standard phase-diffusion result |
| **B** | Random rotation average `R(φ)` with `φ∼N(0,σ²)` | `e^{−σ²/2}·I₂` (radial damping) | `(1−e^{−σ²})·½·I₂` | Averaged-over-rotations; damps off-diagonal V entries. Standard "phase diffusion" in many texts |
| **C** | Explicit `Y` only, `X=I`, anisotropic | `I₂` | `σ²·diag(0,1)` (p-noise only) | Adds noise to p only; **breaks rotation symmetry**, may violate CP unless scaled |

**Recommendation: B** (rotation-average). Reasons:
- It is the textbook "phase diffusion" channel (random phase rotation averaged).
- `X = e^{−σ²/2} I` is a contraction ⇒ CP-satisfying by construction.
- Reduces to identity at `σ=0`; damps coherences (off-diagonal V) as expected.
- Matches the form used in SF / MrMustard `phase_noise` (loss-like with `T=e^{−σ²}`).

Option A is isotropic thermal-like noise (not really "phase" noise).  
Option C is anisotropic and needs careful CP scaling; defer.

**Default if no answer: B.**

---

## Acceptance criteria

1. `apply_gaussian_channel` with `X=S` symplectic, `Y=0`, `d=0` reproduces
   `apply_symplectic(state, S)` bitwise (atol 1e-12).
2. `loss(T=1)` ≡ identity; `loss(T=0, nbar=0)` ⇒ vacuum on acted modes
   (mean → 0, V → I/2 on those quads).
3. **Regression:** existing `loss` tutorial/test numbers unchanged
   (run full pytest; `test_b1_gaussian_gates.py` + `test_gaussian_circuit.py`
   loss cases still pass).
4. CP boundary: pure-loss family `(√T, (1−T)/2)` passes `validate_channel`
   for all `T∈[0,1]`; a deliberately invalid `Y` (e.g. negative) fails.
5. Amplifier: `amplifier(G>1)` on coherent `|α⟩` ⇒
   `⟨n⟩ → G|α|²` (trend, atol 1e-9); `amplifier(G=1)` ≡ identity.
6. Phase noise (option B): `σ=0` ≡ identity; `σ>0` damps off-diagonal V
   of a squeezed state toward vacuum; CP passes.
7. Composition: `apply_gaussian_channel` twice with `(X1,Y1)` then `(X2,Y2)`
   equals one shot with `X=X2 X1`, `Y = X2 Y1 X2ᵀ + Y2` (atol 1e-10).
8. `validate=True` rejects non-PSD CP with a clear `ValueError`;
   `validate=False` skips (trusted escape hatch, documented).
9. Full `pytest tests` green; new tests in `tests/test_gaussian_channels.py`.

---

## Out-of-scope follow-ups (tracked, not done here)

- `GaussianCircuit.amplifier` / `.phase_noise` DSL methods.
- Correlated multi-mode loss.
- True Clements rectangular decomposition (separate API).
- Phase1 exit tutorial `interferometer + loss + homodyne`.
