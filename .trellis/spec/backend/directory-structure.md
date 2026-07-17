# Directory Structure

> Backend layout for `cv-photonic-notes` (sim package + theory notes).

---

## Overview

- **Theory notes** live at repo root as pure-physics Markdown/HTML. No library/API bindings.
- **Simulator code** lives in package `cvsim/` (sibling to notes, not inside notes).
- **Tests** live in `tests/` at repo root.

---

## Directory Layout

```text
cv-photonic-notes/
├── *.md / *.html          # pure theory notes (no dq./API)
├── cvsim/                 # simulators
│   ├── conventions.py     # ħ, xxpp, Ω, vacuum
│   ├── gaussian/          # (V, r̄) + symplectic.py + gates
│   ├── fock/              # truncated amplitudes + single-mode gates
│   ├── bosonic/           # components + cat + component-wise gates
│   └── demos/             # milestone self-checks (python -m)
├── tests/                 # pytest (test_m* + test_b1_*)
└── .trellis/              # workflow / specs / tasks
```

---

## Module Organization

| Path | Owns |
|------|------|
| `cvsim/conventions.py` | Global physics constants and vacuum helpers |
| `cvsim/gaussian/symplectic.py` | Shared xxpp S/d generators (only place for BS/D/R/S formulas) |
| `cvsim/gaussian/` | GaussianState, apply_symplectic, D/R/S/BS, det/⟨n⟩, Homodyne mean/var |
| `cvsim/fock/` | FockState, ladder+expm D/R/S, norm/⟨n⟩ |
| `cvsim/bosonic/` | Components, cat, gates reuse `gaussian.symplectic` |
| `cvsim/demos/m*.py` | Runnable AC scripts for MVP milestones |
| `tests/test_m*.py` / `test_b1_*.py` / `test_b2_*.py` | MVP + B1 gates + B2 Homodyne |

Do **not** invent a Circuit DSL until multi-representation shared scheduling is required.  
New gate matrices go in `symplectic.py` first; backends only apply maps.

---

## Naming Conventions

- Package: `cvsim` (lowercase)
- Modules: snake_case (`mean_photon`, `det_cov`)
- State types: PascalCase (`GaussianState`, `FockState`, `BosonicState`)
- Demo modules: `m1_*`, `m2_*`, `m3_*` matching PRD milestones

---

## Examples

- M1: `cvsim/gaussian/` + `tests/test_m1_gaussian.py`
- M2: `cvsim/fock/` + `tests/test_m2_fock.py`
- M3: `cvsim/bosonic/` + `tests/test_m3_bosonic.py`
- B1: `gaussian/symplectic.py` + `tests/test_b1_*.py`
