# Vision: Production CV Simulator (Gaussian-first)

> **Audience:** AI coding agents and human maintainers.  
> **Role:** Single source of truth for *what to build* and *what must not drift*.  
> **Not:** An implementation changelog. Current code may lag this doc; when they disagree, **this doc wins for greenfield work**, and tasks must either implement the spec or explicitly amend this doc first.

**Last updated:** 2026-07-28  
**Status:** Target architecture / phased product vision  
**Codebase today:** `cvsim` (numpy, Gauss + Fock + Bosonic teaching MVP)

---

## 1. Purpose & non-goals

### 1.1 Purpose

Build a **production-grade continuous-variable (CV) simulator**, Gaussian-first but **not Gaussian-only**, that can be advanced in phases:

| Phase anchor | Meaning | Typical exit |
|--------------|---------|--------------|
| **A. Research-citable** | Algorithms and conventions reproduce published / reference numbers | Golden tests vs analytic formulae and (where applicable) SF / The Walrus adapters |
| **B. Teaching-production** | Stable API, full docs, three representations coherent | Semester-ready tutorials; semantic versioning; no silent convention breaks |
| **C. Industrial pipeline** | Large mode counts, batch runs, compile, deployable library | $m \sim 10^2$ routine, $m \sim 10^3$ target; layer merge to single $S$; CI |
| **D. Differentiable designer** | Parameters in training loops | Optional JAX/Torch backend; same math as numpy path |

Primary near-term readers of implementations derived from this doc are **AI agents**. Every feature below is written to be implementable without guessing math or API shape.

### 1.2 Product stance

- **Gaussian is the fast path**, not the cage. Full product includes Fock, Bosonic (cat/GKP), and **bridges** between them.
- Prefer **thin adapters** to battle-tested libraries (e.g. The Walrus for Hafnian) over re-implementing heavy combinatorics—unless a phase explicitly owns a self-contained algorithm.
- Stay honest in docs: teaching cuts and production cuts are labeled; no fake completeness.

### 1.3 Non-goals (until a phase unlocks them)

| Item | Default | Unlock condition |
|------|---------|------------------|
| Hardware / cloud device backend | Out of scope | Explicit hardware phase |
| GUI circuit editor | Out of scope | Explicit UX phase |
| Replacing The Walrus as a Hafnian kernel | Avoid | Only if adapter insufficient and benchmarks demand |
| Breaking hard conventions (§2) for “compatibility” | Forbidden | Adapter layer only (§8) |

### 1.4 How agents must use this document

1. Implement features **only** as specified (math + invariants + tests).  
2. If the spec is ambiguous → **stop and amend this doc**, do not invent a third convention.  
3. Each PR/task maps to a **Feature ID** (`F-xxx`) below.  
4. Do not “simplify” displacement scaling, $\Omega$, or xxpp ordering.  
5. Cross-rep work must preserve §2 in Gaussian core; convert at boundaries.

---

## 2. Hard conventions (immutable)

These are **core immutable clauses**. Adapters may convert at the edge; core `cvsim` types always speak this dialect.

### 2.1 Units and vacuum

| Symbol | Value | Notes |
|--------|-------|-------|
| $\hbar$ | `1.0` | `cvsim.conventions.HBAR` |
| Vacuum covariance | $V_{\mathrm{vac}} = \frac{1}{2} I_{2m}$ | Not $I$, not $\hbar I/2$ with $\hbar\neq1$ |
| Vacuum mean | $\bar r = 0$ | |

**Purity of pure Gaussian states:** $\det V = (1/4)^m$.

### 2.2 Quadrature ordering (xxpp)

For $m$ modes, the real vector is:

$$
\bar r = (x_1,\ldots,x_m,p_1,\ldots,p_m)^\mathsf T \in \mathbb R^{2m}
$$

Covariance $V$ is $2m\times 2m$ real symmetric, same ordering.

Constant:

```text
QUAD_ORDER = "xxpp"
```

**Forbidden in core:** silent `xpxp` / `xpxp` packing. Conversions belong in `cvsim.interop.*`.

### 2.3 Symplectic form

$$
\Omega = \begin{pmatrix} 0 & I_m \\ -I_m & 0 \end{pmatrix}
\quad\text{(xxpp)}
$$

Implemented by `cvsim.conventions.omega(nmode)`.

A real matrix $S$ is **symplectic** iff

$$
S \Omega S^\mathsf T = \Omega
$$

(within numerical tolerance; see §7).

### 2.4 Displacement convention

Complex amplitude $\alpha$ maps to quadrature shift:

$$
d_x = \sqrt{2}\,\Re\alpha,\qquad d_p = \sqrt{2}\,\Im\alpha
$$

So vacuum → coherent: $\bar r = d$ on the target mode pair $(x_k,p_k)$.

This matches current `cvsim.symplectic.d_displace`. **Do not** switch to $d_x=\Re\alpha$ without a major version + this doc change.

### 2.5 Mode indexing

- Modes are integers `0 .. nmode-1`.  
- After measurement-removal, **circuit builders use original logical indices**; runtime maintains `logical → physical` maps (already in `GaussianCircuit`).  
- Partial trace / reduce APIs take logical mode indices on the state they accept.

### 2.6 Dtype and randomness

| Item | Rule |
|------|------|
| Default floating dtype | `float64` (`numpy` default float) |
| Complex gate params | Python `complex` / `np.complex128`; stored channels real in xxpp |
| RNG | `np.random.Generator`; no global `np.random.*` in library code |
| Reproducibility | All samplers accept `rng=`; tests use fixed seeds |

### 2.7 State identity (Gaussian)

A pure/mixed Gaussian state is exactly the pair $(V, \bar r)$ plus the conventions above. No hidden Fock cutoff inside `GaussianState`.

---

## 3. Architecture layers

```text
┌─────────────────────────────────────────────────────────────┐
│  Circuit DSL     parameters, measure, feedforward, compose   │  L4
├─────────────────────────────────────────────────────────────┤
│  Compile         merge Gaussian unitaries → single S, d      │  L5
├─────────────────────────────────────────────────────────────┤
│  Sample          Gaussian shots / GBS bridge / batch 10³     │  L6
├─────────────────────────────────────────────────────────────┤
│  Analyse         physicality, purity, eigs, entanglement…    │  L3b
├─────────────────────────────────────────────────────────────┤
│  Measure         Homodyne / Heterodyne / threshold / PNR     │  L3
├─────────────────────────────────────────────────────────────┤
│  Channel         general (X,Y) CPTP Gaussian + presets       │  L2
├─────────────────────────────────────────────────────────────┤
│  Gate / S        named gates + arbitrary symplectic          │  L1
├─────────────────────────────────────────────────────────────┤
│  State           factories + (V, r̄) container                │  L0
├─────────────────────────────────────────────────────────────┤
│  Conventions     ħ, xxpp, Ω, displace scaling                │  core
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    Gaussian core      Fock (cutoff)        Bosonic (cat/GKP)
         └────────────── bridges / interop ──────────┘
```

**Dependency rule for agents:** do not implement layer $k+1$ by forking a private copy of layer $k$ math. Call shared `conventions` / `symplectic` / analyse helpers.

**Package layout (target):**

```text
cvsim/
  conventions.py          # frozen
  symplectic.py           # S generators + validate
  gaussian/
    state.py              # GaussianState + factories
    gates.py              # apply named + apply_symplectic
    channels.py           # (X,Y) + presets
    observables.py        # moments, homodyne, …
    measure.py            # (optional split) sampling + condition
    analyse.py            # purity, eigs, log_neg, fidelity
    circuit.py            # DSL
    compile.py            # merge to S
  interop/
    ordering.py           # xxpp ↔ xpxp
    walrus.py             # optional extras
    strawberryfields.py   # optional
  fock/ … bosonic/ …      # peer representations
```

Names may vary slightly, but **Feature IDs and math must not**.

---

## 4. Functional specifications

Each feature has:

- **ID** — stable handle for tasks  
- **Math** — equations agents must implement  
- **API sketch** — shape of public surface (not bike-shedding names without reason)  
- **Invariants** — postconditions  
- **Tests** — minimum acceptance  
- **Depends** — prerequisite IDs  
- **Phase** — when it becomes mandatory  

---

### 4.1 P0 — Phase-1 detailed specs (implement next)

#### F-STATE-FACTORY — Standard Gaussian state factories

**Phase:** P0 / Phase 1  
**Depends:** conventions (§2)

**Math**

| Factory | $V$ | $\bar r$ |
|---------|-----|----------|
| `vacuum(m)` | $\frac12 I_{2m}$ | $0$ |
| `coherent(m, alpha, mode=0)` | vacuum $V$ | $d(\alpha)$ on `mode` |
| `thermal(m, nbar, mode=0)` | single-mode block $\frac{2nbar+1}{2}I_2$; others vac | $0$ |
| `squeezed(m, r, phi=0, mode=0)` | $S(r,\phi)\,V_{\mathrm{vac}}\,S^\mathsf T$ | $0$ |
| `displaced_squeezed(...)` | same $V$ as squeezed | $d(\alpha)$ |
| `tmsv(m, r, mode1, mode2)` | $S_2(r) V_{\mathrm{vac}} S_2^\mathsf T$ on pair | $0$ |
| `product(states)` | block-diag embed in xxpp (see below) | concat means |

**Squeezed with angle:** $S(r,\phi)=R(\phi)S(r)R(-\phi)$ using existing `S_phase`, `S_squeeze`.

**Thermal single-mode covariance (xxpp):**

$$
V_{\mathrm{th}}(\bar n)=\frac{2\bar n+1}{2}\begin{pmatrix}1&0\\0&1\end{pmatrix}
$$

**xxpp multi-mode embed rule:** when building product states, allocate full $(2M\times 2M)$ and place mode $k$'s $(x,p)$ at indices $(k,\,M+k)$.

**API sketch**

```python
class GaussianState:
    @classmethod
    def vacuum(cls, nmode: int = 1) -> GaussianState: ...
    @classmethod
    def coherent(cls, alpha: complex, *, nmode: int = 1, mode: int = 0) -> GaussianState: ...
    @classmethod
    def thermal(cls, nbar: float, *, nmode: int = 1, mode: int = 0) -> GaussianState: ...
    @classmethod
    def squeezed(cls, r: float, phi: float = 0.0, *, nmode: int = 1, mode: int = 0) -> GaussianState: ...
    @classmethod
    def displaced_squeezed(cls, alpha: complex, r: float, phi: float = 0.0, *, nmode: int = 1, mode: int = 0) -> GaussianState: ...
    @classmethod
    def tmsv(cls, r: float, *, nmode: int = 2, mode1: int = 0, mode2: int = 1) -> GaussianState: ...
    @classmethod
    def product(cls, *states: GaussianState) -> GaussianState: ...
```

**Invariants**

- All factories return `float64` arrays, shape `(2m,2m)` / `(2m,)`.  
- `thermal`: `nbar >= 0`; pure iff `nbar==0`.  
- `coherent` purity equals vacuum purity.  
- `tmsv`: reduced single-mode is thermal with $\bar n=\sinh^2 r$.

**Tests**

- Vacuum: `V == 0.5*I`, `rbar==0`.  
- Coherent: `homodyne_mean` matches $\sqrt{2}\Re/\Im$.  
- Squeezed `phi=0`: $\mathrm{Var}(x)=\frac12 e^{-2r}$, $\mathrm{Var}(p)=\frac12 e^{2r}$.  
- TMSV: $\mathrm{Var}(x_0-x_1)=e^{-2r}$ (with vacuum units as in existing tutorials).  
- Product of two vacua ≡ `vacuum(2)`.

---

#### F-SYMPLECTIC-CORE — Arbitrary symplectic apply + validation

**Phase:** P0 / Phase 1  
**Depends:** §2.3

**Math**

Unitary Gaussian evolution (no noise):

$$
\bar r \mapsto S\bar r + d,\qquad V \mapsto S V S^\mathsf T
$$

with $d\in\mathbb R^{2m}$ (often from displacements) and $S\Omega S^\mathsf T=\Omega$.

**API sketch**

```python
# cvsim/symplectic.py
def is_symplectic(S: np.ndarray, *, atol: float = 1e-8) -> bool: ...
def validate_symplectic(S: np.ndarray, *, atol: float = 1e-8) -> None:  # raises ValueError

# cvsim/gaussian/gates.py
def apply_symplectic(
    state: GaussianState,
    S: np.ndarray,
    d: np.ndarray | None = None,
    *,
    validate: bool = True,
) -> GaussianState: ...
```

**Invariants**

- `S.shape == (2m,2m)`, `d.shape == (2m,)` if given.  
- If `validate`, reject non-symplectic $S$.  
- Pure states remain pure under symplectic maps: $\det V$ unchanged (up to atol).  
- Named gates must be thin wrappers: build $S$ (and $d$) → `apply_symplectic`.

**Tests**

- Random Sp(2m) from composition of library gates → `is_symplectic` true.  
- `S = I`, `d = d_displace` ≡ `displace`.  
- Known squeeze matrix matches `S_squeeze`.  
- Ill-conditioned non-symplectic matrix raises when `validate=True`.

---

#### F-GATE-SET — Complete named Gaussian unitary set

**Phase:** P0 / Phase 1  
**Depends:** F-SYMPLECTIC-CORE

**Required named operations** (all return **new** state; functional style):

| Name | Parameters | Math / $S$ source |
|------|------------|-------------------|
| `squeeze` | `r`, `mode`, optional `phi` | $R(\phi)S(r)R(-\phi)$ |
| `displace` | `alpha`, `mode` | $V$ unchanged; $\bar r += d(\alpha)$ |
| `phase` | `theta`, `mode` | `S_phase` |
| `fourier` | `mode` | `phase(theta=π/2)` alias |
| `beamsplitter` | `m1,m2,theta,phi` | existing `S_beamsplitter` |
| `mach_zehnder` | `m1,m2, theta, phi` | standard MZ = phase·BS·phase·BS decomposition **documented in code** |
| `two_mode_squeeze` | `r, m1, m2` | `S_two_mode_squeeze` |
| `cz` | `weight, m1, m2` | `S_CZ` — $p_i \mathrel{+}= g x_j$, $p_j \mathrel{+}= g x_i$ |
| `cx` | `weight, m1, m2` | `S_CX` — $x_j \mathrel{+}= g x_i$, $p_i \mathrel{-}= g p_j$ |
| `interferometer` | unitary $U$ ($m\times m$ complex) | passive embed §F-INTERFEROMETER |

**CZ / CX (do not re-derive differently)**

- CZ: $U=\exp(i g \hat x_i \hat x_j)$ → in xxpp, $S[nmode+i,j]=g$, $S[nmode+j,i]=g$.  
- CX: $U=\exp(-i g \hat x_i \hat p_j)$ → $S[j,i]=g$, $S[nmode+i, nmode+j]=-g$.

**Invariants**

- Every named gate is symplectic (displacement is inhomogeneous affine).  
- `cz`/`cx` on vacuum produce $\langle n\rangle>0$ for $g\neq0$ while preserving purity.  
- Mode indices validated; clear `IndexError`.

**Tests**

- Existing suite remains green.  
- `fourier` four times = identity on $V,\bar r$.  
- MZ at known angles matches BS+phase composition.  
- Gate vs manual `apply_symplectic(S_*)` bitwise-close (`atol=1e-12`).

---

#### F-INTERFEROMETER — Passive linear optics from $U$ + mesh compile

**Phase:** P0 / Phase 1  
**Depends:** F-SYMPLECTIC-CORE, F-GATE-SET (BS, phase)

**Math — passive embed**

For unitary $U\in\mathrm U(m)$ acting on mode annihilators $\vec a \mapsto U\vec a$, the xxpp symplectic is:

$$
S_U = \begin{pmatrix} \Re U & -\Im U \\ \Im U & \Re U \end{pmatrix}
$$

**Sanity:** $U=I\Rightarrow S=I$; 50:50 BS matches library BS (up to documented phase convention).

**Mesh compilation (Clements preferred; Reck acceptable as alt)**

- **Input:** $U$ ($m\times m$ unitary).  
- **Output:** list of native ops `(phase, beamsplitter, …)` **or** direct $S_U$.  
- Phase-1 **minimum:** `S_from_unitary(U)` + `apply_interferometer(state, U)`.  
- Phase-1 **target:** `clements_decomposition(U) -> list[GateOp]` matching $U$ within atol.

**API sketch**

```python
def S_from_unitary(U: np.ndarray) -> np.ndarray: ...
def apply_interferometer(state: GaussianState, U: np.ndarray) -> GaussianState: ...

def clements_decomposition(U: np.ndarray) -> list[tuple]: ...
def apply_mesh(state: GaussianState, ops: list[tuple]) -> GaussianState: ...
```

**Invariants**

- `S_from_unitary` result is symplectic.  
- $U$ must be unitary: $U^\dagger U=I$ within atol (validate).  
- Decomposition recomposed equals $U$ (operator norm / Frobenius).

**Tests**

- Haar-random $U$ (via QR) for $m=2,4,8$.  
- TMSV + balanced BS → known EPR correlations.  
- Decomposition round-trip.

**Performance note:** applying $S_U$ as one matrix multiply is $O(m^3)$; preferred path under F-COMPILE when many passive layers exist.

---

#### F-CHANNEL-GENERAL — General Gaussian CPTP maps $(X,Y)$

**Phase:** P0 / Phase 1  
**Depends:** F-SYMPLECTIC-CORE (for pure unitary limits)

**Math**

A single-shot Gaussian channel:

$$
\bar r \mapsto X\bar r + d,\qquad V \mapsto X V X^\mathsf T + Y
$$

with $X,Y$ real $2m\times 2m$, $Y=Y^\mathsf T$, and **complete positivity / Gaussian physicality**:

$$
Y + i\Omega - i X\Omega X^\mathsf T \succeq 0
$$

(Hermitian PSD in the complex sense; implement via numerical check on the Hermitian matrix).

**Presets (must be special cases of $(X,Y)$)**

| Preset | $X$ | $Y$ | Notes |
|--------|-----|-----|-------|
| Identity | $I$ | $0$ | |
| Loss / attenuator transmittance $T\in[0,1]$, env $\bar n$ | $\sqrt{T}I$ (per mode block) | $(1-T)(2\bar n+1)\frac12 I$ on affected modes | Match current `loss` |
| Phase diffusion (approx Gaussian) | $R$ average or small-noise $X\approx I$, $Y$ phase-noise form | Document chosen model in code docstring | Phase-1: single agreed formula |
| Amplifier gain $G\ge1$, $\bar n_{\mathrm{amp}}$ | $\sqrt{G}I$ | $(G-1)(2\bar n_{\mathrm{amp}}+1)\frac12 I$ | Quantum-limited default $\bar n=0$ |

**Multi-mode loss:** default independent identical $T$ on listed modes; correlated loss is P1+ with explicit $X,Y$.

**API sketch**

```python
def apply_gaussian_channel(
    state: GaussianState,
    X: np.ndarray,
    Y: np.ndarray,
    d: np.ndarray | None = None,
    *,
    validate: bool = True,
) -> GaussianState: ...

def loss(state, T: float, nbar: float = 0.0, modes=None) -> GaussianState: ...
def amplifier(state, G: float, nbar: float = 0.0, modes=None) -> GaussianState: ...
def phase_noise(state, sigma: float, modes=None) -> GaussianState: ...  # document kernel
```

**Invariants**

- Unitary channel: $X=S$ symplectic, $Y=0$ ≡ `apply_symplectic`.  
- Loss $T=1$: identity; $T=0$, `nbar=0`: vacuum on those modes (mean shrinks).  
- `validate=True` rejects non-PSD CP condition (with clear error).  
- Existing tutorial numbers for pure loss still match.

**Tests**

- CP boundary: pure loss family passes validate.  
- Random invalid $Y$ fails validate.  
- Amplifier then attenuator photon-number trends.  
- Composition of channels: $X=X_2X_1$, $Y=X_2Y_1X_2^\mathsf T+Y_2$.

---

### 4.2 P1 — Specified enough to schedule (detail when entering phase)

#### F-ANALYSE — Physicality & information quantities

| Symbol | Definition (Gaussian, $\hbar=1$) |
|--------|----------------------------------|
| Physicality | $V=V^\mathsf T$ and $V + i\Omega/2 \succeq 0$ |
| Purity | $\mu = 1/(2^m \sqrt{\det V})$ |
| Symplectic eigenvalues | eigenvalues $\nu_j\ge1/2$ of spectrum from $\lvert i\Omega V\rvert$ standard algorithm |
| von Neumann entropy | $\sum g(\nu_j)$ with $g$ the bosonic thermal entropy function |
| Fidelity (two Gaussians) | Marian–Marian / Banchi–Braunstein–Pirandola formula (cite in code) |
| Log negativity | $\mathcal E_N=\max\{0,-\sum_j\log_2(2\tilde\nu_j)\}$ on partial transpose |
| Partial trace | drop modes from $V,\bar r$ **without** measurement collapse (≠ post-measure `remove_mode` only when no correlations conditioning) |

**API:** `is_physical`, `purity`, `symplectic_eigenvalues`, `entropy_vn`, `fidelity`, `log_negativity(state, modes_A)`, `partial_trace(state, keep)`.

**Tests:** vacuum purity 1; thermal purity $1/(2\bar n+1)$; TMSV log-neg matches analytic $-{\log_2}(e^{-2r}\cdot…)$ form used in literature (freeze formula in tests).

---

#### F-MEASURE-FULL — Measurement toolbox

| Measurement | Output | State update |
|-------------|--------|--------------|
| Homodyne $\phi$ | Gaussian scalar | conditional Gaussian (existing) |
| Heterodyne | complex $\beta$ / pair $(x,p)$ | Husimi, projection to coherent |
| Threshold (on/off) | $\{0,1\}$ | non-Gaussian → **flag**: exact update leaves Gaussian manifold; either reject, use Fock, or return outcome-only without state |
| PNR | photon counts | via Fock bridge or Walrus sample; Gaussian state update not generally Gaussian |

**Phase rule:** Homodyne+Heterodyne stay in Gaussian core; threshold/PNR sampling may live in `sample` + interop.

**Heterodyne math (document in code):** POVM $\lvert\beta\rangle\langle\beta\rvert/\pi$; for Gaussian, outcome covariance $V+I/2$, then condition.

---

#### F-CIRCUIT-PROD — Production circuit DSL

Extend current `GaussianCircuit`:

- Parameter placeholders (str) + `ParamRef` feedforward (exists).  
- `+` / `+=` compose (exists).  
- Measurement mode elimination + logical map (exists).  
- **Add:** `to_ops()`, serialization JSON, `bind(**params)` without run, validation of ParamRef sources.  
- **Add:** mid-circuit heterodyne; loss as circuit op (exists loss).  
- **Add:** compile hook `circuit.compile() -> CompiledGaussian` (F-COMPILE).

---

#### F-COMPILE — Merge Gaussian unitary layers to single $S$

**Math:** consecutive affine maps $(S_i,d_i)$ compose as

$$
S=S_n\cdots S_1,\qquad d = d_n + S_n d_{n-1} + \cdots + S_n\cdots S_2 d_1
$$

**Break merge at:** non-unitary channel, measurement, feedforward depending on RNG outcome.

**API:** `compile_unitary_prefix(ops) -> (S,d, rest_ops)`.

**Exit metric:** random depth-100 passive circuit on $m=32$ matches uncompiled state (`atol=1e-9`) and is faster in benchmark fixture.

---

#### F-SAMPLE — Batch sampling

- Homodyne / heterodyne / Gaussian quadrature batch: `size=10**3` default OK.  
- Vectorize where easy (`rng.normal(size=(shots, ...))`).  
- GBS: **adapter** `export_cov_for_walrus(state)` + docs; optional extra dependency.  
- Self-hosted Hafnian only if phase charter says so.

---

#### F-AD — Differentiable backend

- Math identical to numpy path.  
- Backend protocol: `Array` type alias; `symplectic` functions backend-agnostic.  
- JAX first candidate; Torch second.  
- No AD in core import path (optional package extra).

---

#### F-BRIDGE — Cross-representation

| Bridge | Rule |
|--------|------|
| Gauss → Fock | Given cutoff $N$, build density/vector from $V,\bar r$ (known formulae) for small $m$ |
| Fock → Gauss | Only if state is Gaussian within tol; else reject |
| Gauss → Bosonic | Single-component weight-1 embedding |
| Bosonic → moments | Existing weighted moments; match Gaussian when one component |

GKP **error correction demo** uses Gaussian Circuit CZ + Homodyne + displace feedforward; ideal GKP peaks live in Bosonic module.

---

#### F-PERF — Scale targets

| Target | Value |
|--------|-------|
| Routine $m$ | $100$ modes, compiled passive + local squeezers |
| Stretch $m$ | $1000$ modes for apply $S$ dense (memory $\sim (2m)^2$) |
| Shots | $10^3$ batch standard; $10^5$ stress optional |
| Dtype | float64 |
| Memory warning | document dense $O(m^2)$ storage; sparse/block future |

For $m\sim10^3$, prefer: store circuit + apply layerwise / compiled $S$ once; avoid many full copies.

---

### 4.3 P2 — Named only (expand before implementation)

- Circuit diagram export (matplotlib/text).  
- Correlated multi-mode loss baths.  
- TDM / time-domain multiplexed modes as first-class.  
- Approximate GBS samplers.  
- GPU batch beyond JAX defaults.  
- Full SF feature parity matrix automation.

---

## 5. Phased roadmap & exit criteria

Ordering principle: **S1 ∩ S2** — dependency order first, each phase ships a demo exit.

### Phase 0 — Baseline (done / freeze)

**Has:** `GaussianState`, named gates (incl. CZ/CX), loss, Homodyne condition, `GaussianCircuit` L2–L4, Wigner 1-mode, Fock/Bosonic siblings, tutorials.

**Exit:** Treat conventions §2 as frozen; any change is major version.

---

### Phase 1 — Gaussian core completeness (P0 features)

**Build:** F-STATE-FACTORY, F-SYMPLECTIC-CORE, F-GATE-SET, F-INTERFEROMETER, F-CHANNEL-GENERAL.

**Exit criteria**

1. All P0 APIs public in `cvsim.gaussian` / `cvsim.symplectic`.  
2. Tests: analytic cases + random symplectic composition.  
3. Tutorial or demo: “interferometer + loss channel + homodyne”.  
4. `pytest` green; no convention drift.  
5. Docstrings state math from this file.

**Demo exit:** $m=4$ TMSV-like sources → user $U$ → loss → homodyne means match hand calculation.

---

### Phase 2 — Analyse + measure + teach (A+B)

**Build:** F-ANALYSE, Heterodyne, partial_trace, purity/log_neg in TMSV tutorial, API stability policy.

**Exit criteria**

1. Research quantities match analytic TMSV / thermal.  
2. Teaching notebooks Run-All.  
3. Version policy: breaking convention requires vision doc amend + major bump.

---

### Phase 3 — Compile, scale, sample pipeline (C)

**Build:** F-COMPILE, F-SAMPLE batch, optional Walrus interop, $m=100$ benchmark job in CI (time-capped).

**Exit criteria**

1. Compiled vs naive identical on fixtures.  
2. $m=100$ compile+apply under agreed time budget (record in `benchmarks/`).  
3. $10^3$ homodyne shots API stable.  
4. GBS path documented (adapter or explicit skip).

---

### Phase 4 — Differentiable designer (D)

**Build:** F-AD extras, one optimization notebook (e.g. maximize log-neg under loss).

**Exit criteria**

1. Gradients agree with finite difference on squeeze/BS params.  
2. Numpy and JAX paths share tests via backend parametrization.

---

### Phase 5 — Bridges & CV error-correction story

**Build:** F-BRIDGE Gauss↔Fock small-$m$, GKP feedforward tutorial at production quality, Bosonic consistency tests.

**Exit criteria**

1. Documented GKP-style circuit using CZ+measure+ParamRef.  
2. Bridge tests for coherent/squeezed low cutoff.

---

## 6. Cross-representation strategy

```text
                 ┌──────── Gaussian (V, r̄) ────────┐
                 │  fast m→100–1000, channels, FF   │
                 └────────────┬─────────────────────┘
                              │ bridges
              ┌───────────────┼───────────────┐
              ▼                               ▼
     Fock (cutoff N)                   Bosonic (Σ weights × Gauss)
     PNR exact small m                 cat / GKP peaks
```

**Rules**

1. One physical experiment → one “source of truth” rep for evolution; convert for analysis.  
2. Never silently truncate Gaussians into Fock inside `gaussian.gates`.  
3. Shared `symplectic.py` + `conventions.py` across Gauss/Bosonic.  
4. Circuit DSL may later become rep-agnostic; Phase 1 keeps `GaussianCircuit`.

---

## 7. Performance & numerics budget

| Topic | Rule |
|-------|------|
| Dtype | float64 default |
| Symplecticity atol | default `1e-8` check; gates internal `1e-12` agreement |
| Physicality atol | eig ≥ `-1e-10` after symmetrizing $V\leftarrow\frac12(V+V^\mathsf T)$ |
| Det / purity | use `slogdet` for stability |
| Compile | merge unitaries; do not merge across noise/measure |
| Copies | functional API may copy; provide `out=` or in-place advanced API only later |
| Batch shots | $10^3$ normal; allocate once |
| $m=1000$ | single dense $S$ apply allowed; document ~32MB+ for $S$ alone |

**Numerical hygiene for agents**

- Symmetrize $V$ after every noisy update.  
- Optional `project_physical(V)` P2.  
- No `scipy` hard req unless already accepted; prefer numpy. (Project lock: numpy/scipy OK.)

---

## 8. Interop adapters

| External | Direction | Responsibility |
|----------|-----------|----------------|
| Ordering SF / xpxp | both | `interop.ordering.to_xpxp(V,rbar)` / `from_xpxp` |
| The Walrus | export cov + μ | metadata: $\hbar$, ordering annotation in docstring |
| Strawberry Fields | optional round-trip tests | not a runtime dependency |
| DeepQuantum | comparison suite only | no hard dep |

**Rule:** Core never switches to external ordering to “make tests easier.”

---

## 9. Testing doctrine (for agents)

Every `F-*` feature needs:

1. **Unit:** math identities.  
2. **Invariants:** purity/symplecticity/CP where applicable.  
3. **Golden:** fixed seed snapshots for samplers (statistical or exact).  
4. **Regression:** tutorials or demos import public API only.

Marker idea: `@pytest.mark.phase1` etc. for optional CI slicing.

---

## 10. Mapping: vision → current repo (gap snapshot)

| Feature | Now | Gap |
|---------|-----|-----|
| Conventions xxpp ħ=1 | Done | Freeze |
| vacuum factory | Done | Extend factories |
| Named gates + CZ/CX | Done | phi-squeeze, Fourier, MZ, interferometer |
| apply_symplectic | Partial | validate + d + public guarantee |
| loss | Done | General $(X,Y)$, amp, phase noise |
| Homodyne + FF circuit | Done | Heterodyne, serialize, compile |
| Analyse | det_cov, mean_photon | Full F-ANALYSE |
| Compile merge S | Missing | F-COMPILE |
| GBS | Out | Adapter phase 3 |
| AD | Out | Phase 4 |
| Fock/Bosonic | Teaching MVP | Bridges phase 5 |

---

## 11. Open questions (resolve by amending this doc)

1. Phase-noise Gaussian kernel: Ornstein–Uhlenbeck phase diffusion vs static random phase average—**pick one before F-CHANNEL-GENERAL preset**.  
2. Threshold measurement: outcomes-only vs forced Fock backend.  
3. Whether `GaussianCircuit` becomes generic `CVCircuit` in phase 5.  
4. Exact fidelity formula reference implementation (Banchi et al. vs other).  
5. CI wall-time budget for $m=100$ benchmark on available runners.

---

## 12. Agent checklist (copy into tasks)

```text
[ ] Feature ID listed in vision §4
[ ] Math matches vision (no alternate vacuum variance)
[ ] xxpp + displace √2 scaling
[ ] Invariants tested
[ ] Public exports updated
[ ] Tutorial/demo if Phase exit requires
[ ] If spec conflict: amend vision first in same PR
```

---

## 13. Document control

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-07-28 | Initial vision from stack survey + grill decisions |

**Amendments:** require human or explicit task approval; agents must not delete hard conventions (§2) without major-version note.
