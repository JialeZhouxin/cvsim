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
│   ├── gaussian/          # (V, r̄)
│   ├── fock/              # truncated amplitudes
│   ├── bosonic/           # Gaussian mixture components
│   └── demos/             # milestone self-checks (python -m)
├── tests/                 # pytest
└── .trellis/              # workflow / specs / tasks
```

---

## Module Organization

| Path | Owns |
|------|------|
| `cvsim/conventions.py` | Global physics constants and vacuum helpers |
| `cvsim/gaussian/` | GaussianState, symplectic gates, det/⟨n⟩ |
| `cvsim/fock/` | FockState, ladder+expm gates, norm/⟨n⟩ |
| `cvsim/bosonic/` | Component list, cat constructors, weight_sum |
| `cvsim/demos/m*.py` | Runnable AC scripts for each milestone |
| `tests/test_m*.py` | Regression tests mirroring demos |

Do **not** invent a Circuit DSL until multi-representation shared scheduling is required.

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
