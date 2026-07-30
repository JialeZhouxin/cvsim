# cvsim API stability policy

**Status:** Phase 2 exit item (vision §5 Phase 2 criterion 3)  
**Applies to:** public surface of `cvsim.gaussian`, `cvsim.symplectic`, `cvsim.conventions`  
**Date:** 2026-07-30

---

## 1. Hard conventions (never silent)

These are **frozen**. Changing any of them is a **major** version bump **and** requires amending `docs/vision-gaussian-simulator.md` §2 in the same change set.

| Item | Value |
|------|--------|
| $\hbar$ | `1` (`cvsim.conventions.HBAR`) |
| Quadrature order | **xxpp**: $(x_1,\ldots,x_m,p_1,\ldots,p_m)$ |
| Vacuum covariance | $V_{\mathrm{vac}} = I/2$ |
| Displacement | $d_x=\sqrt{2}\Re\alpha$, $d_p=\sqrt{2}\Im\alpha$ |
| Float dtype (core paths) | `float64` |
| Homodyne quadrature | $x_\phi = x\cos\phi + p\sin\phi$ |

Adapters for other lab conventions live only under future `cvsim.interop.*` (Phase 3+). Core must not switch ordering to match external libraries.

---

## 2. What is public

### 2.1 Guaranteed public (semver-covered)

Import from package roots, not private modules with leading underscore:

```python
from cvsim.gaussian import GaussianState, squeeze, loss, purity, log_negativity, ...
from cvsim.symplectic import omega  # if re-exported; else cvsim.conventions
from cvsim.conventions import HBAR, QUAD_ORDER, omega, vacuum_cov
```

**Canonical Gaussian export list:** `cvsim.gaussian.__all__`.

A regression test (`tests/test_public_api.py`) freezes that set. **Removing or renaming** an entry is a **major** bump. **Adding** an entry is a **minor** bump.

### 2.2 Public but “thin / may grow”

| Surface | Notes |
|---------|--------|
| `GaussianCircuit` / `ParamRef` | L2–L4 DSL; op names in the IR are semi-stable; new measure ops may appear |
| `cvsim.wigner` | Teaching grids; signature may gain kwargs |
| `cvsim.fock` / `cvsim.bosonic` | Sibling reps; not the Phase 2 freeze focus |
| Demo scripts under `cvsim.demos` / `examples/` | May move or rename without major bump |

### 2.3 Private (no stability promise)

- Any name starting with `_` (e.g. `_bosonic_g`, `_as_cov`, `_symplectic_eigenvalues_raw`)
- Modules not listed in a package `__all__`
- Files under `.trellis/`, `docs/review-*.md`, adversarial scratch scripts

---

## 3. Version policy (semver)

Until a tagged release exists, treat the repo `master` tip as **0.x** pre-release. When tagging:

| Bump | Trigger |
|------|---------|
| **MAJOR** | Break hard conventions (§1); remove/rename public export; change default physics of a public function (e.g. entropy nats→bits); change return type of a public API in a breaking way |
| **MINOR** | New public export; new optional kw-only arg with default preserving old behaviour; new tutorial |
| **PATCH** | Bugfix, docstring, tests, performance with identical numerics on freezes |

**Rules for agents**

1. If a task needs a convention change → **stop**, amend vision §2 + this file, mark major, get explicit approval.
2. Prefer **kw-only** optional args over positional signature churn.
3. Docstring math must match vision; if they disagree, **amend vision first** in the same PR (agent checklist §12).
4. Tutorials and `examples/` must import **public** API only (vision §9).

---

## 4. Phase 2 Gaussian public surface (freeze snapshot)

Frozen by `tests/test_public_api.py` at the Phase 2 API-stability commit. Categories:

| Category | Symbols |
|----------|---------|
| State | `GaussianState` |
| Gates | `apply_symplectic`, `squeeze`, `displace`, `phase`, `fourier`, `beamsplitter`, `mach_zehnder`, `two_mode_squeeze`, `cz`, `cx`, `interferometer`, `apply_interferometer`, `apply_mesh` |
| Channels | `loss`, `amplifier`, `phase_noise`, `apply_gaussian_channel`, `is_cp_channel`, `validate_channel` |
| Observables | `det_cov`, `mean_photon`, `homodyne_*`, `heterodyne_*` |
| Analyse | `is_physical`, `validate_state`, `symplectic_eigenvalues`, `purity`, `entropy_vn`, `partial_trace`, `log_negativity`, `fidelity` |
| Circuit | `GaussianCircuit`, `ParamRef` |

**Units (document in call sites, do not silently switch)**

| API | Unit / range |
|-----|----------------|
| `entropy_vn` | **nats** (ln) |
| `log_negativity` | **bits** (log₂) |
| `purity` | $\mu\in(0,1]$ physical |
| `fidelity` | $F\in[0,1]$ Uhlmann |
| Heterodyne outcome | complex $\beta$, $\beta=(x+ip)/\sqrt{2}$ |

---

## 5. Measurement semantics (do not conflate)

| API | Keeps measured mode? |
|-----|----------------------|
| `homodyne_condition` | **Yes** (singular $V$ along $u$); circuit then `remove_mode` |
| `heterodyne_condition` | **No** — mode removed inside the call |
| `partial_trace` | Drops modes **without** measurement conditioning |

---

## 6. Related docs

| Doc | Role |
|-----|------|
| `docs/vision-gaussian-simulator.md` | Source of truth for physics + roadmap |
| `cvsim/README.md` | Capability matrix (engineering) |
| `cvsim/USER_ACCEPTANCE.md` | User-facing acceptance scenarios |
| `docs/phase1-exit-demo.md` / `examples/phase1_exit_demo.py` | Phase 1 exit |
| This file | Semver + public surface policy |

---

## 7. Checklist for API-touching PRs

```text
[ ] Public symbol added → update cvsim.gaussian.__all__ + test_public_api
[ ] Public symbol removed/renamed → MAJOR + vision note
[ ] Convention touch → vision §2 amend + MAJOR
[ ] New physics default → docstring + tests freeze + minor/major as above
[ ] Demo/tutorial uses only public imports
```
