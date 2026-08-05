# Frontend Development Guidelines

> Coding standards for the Gaussian Lab frontend (`cvsim/lab/static/`).

---

## Overview

The lab frontend is framework-free vanilla JS (ES modules, no build step) backed by the FastAPI lab server. Guidelines document the real module split, state pattern, and contract sync with the backend IR.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | `cvsim/lab/` layout, module rules, single page | Filled |
| [Design System](./design-system.md) | Hallmark Cobalt theme, token semantics, styling rules | Filled |
| [Component & Module Patterns](./component-guidelines.md) | Pure logic vs DOM wiring, op metadata contract, validation | Filled |
| [State Management](./state-management.md) | Module singleton + factory + pure transitions + JSON sync | Filled |
| [Quality Guidelines](./quality-guidelines.md) | No-framework constraints, node:test, ops.js ↔ ir.py sync | Filled |

---

## Pre-Development Checklist

- [ ] Read [directory-structure.md](./directory-structure.md) before adding files to `cvsim/lab/`
- [ ] Read [design-system.md](./design-system.md) before touching `tokens.css` / `style.css` (or adding any visual element)
- [ ] Read [component-guidelines.md](./component-guidelines.md) — where pure logic vs DOM wiring goes
- [ ] If touching ops: check `cvsim/lab/ir.py` needs the matching change (contract sync)
- [ ] Read [quality-guidelines.md](./quality-guidelines.md) for test + pre-commit requirements

## Quality Check

- [ ] `node --test tests/editor.test.mjs` passes
- [ ] No new dependencies / framework imports
- [ ] `ops.js` ↔ `ir.py` contract in sync
- [ ] No `console.log` / debugger residue
