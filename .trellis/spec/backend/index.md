# Backend Development Guidelines

> Coding standards for `cvsim` and backend work in this repo.

---

## Overview

Simulator package `cvsim/` implements three CV representations from pure theory notes at repo root. Notes stay physics-only; code lives beside them.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | `cvsim/` layout, notes isolation | Filled |
| [Backend Interface](./backend-interface.md) | Dual-backend protocol (numpy/jax, Phase 4 F-AD) | Filled |
| [Quality Guidelines](./quality-guidelines.md) | Physics contracts, tests, forbidden patterns | Filled |
| [Error Handling](./error-handling.md) | ValueError fail-fast + CircuitV0Error → 422 | Filled |
| [Scan API](./scan-api.md) | `POST /scan` sweep contract (L4) | Filled |
| [Output & Debugging](./logging-guidelines.md) | Library zero-output; demos print; server framework defaults | Filled |

---

## Pre-Development Checklist

- [ ] Read [directory-structure.md](./directory-structure.md) if adding modules under `cvsim/`
- [ ] Read [quality-guidelines.md](./quality-guidelines.md) for ħ/xxpp/vacuum and test gates
- [ ] Confirm work does not inject library/API into theory `*.md`

---

## Quality Check

- [ ] `pytest tests` and milestone demos pass
- [ ] No new quantum-lib dependency
- [ ] Fock truncation and cat weight gotchas respected
