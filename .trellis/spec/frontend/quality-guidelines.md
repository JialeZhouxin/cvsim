# Quality Guidelines (Frontend)

> Standards for the lab frontend: no frameworks, pure-logic testing, contract sync.

---

## Overview

The lab frontend is intentionally minimal: vanilla ES modules, zero dependencies, zero build step. Quality means: pure functions are testable under node:test, frontend/backend stay contract-synced, and no debug residue lands in commits.

---

## Hard Constraints

| Constraint | Evidence / reason |
|------------|-------------------|
| No frameworks (React/Vue/Svelte) | None in `cvsim/lab/static/`; adds a build step to a no-build project |
| No new dependencies without review | `CODE_REVIEW_GUIDE.md` §1.2 self-check |
| ES modules with explicit `.js` import extensions | Browser loads `static/` directly |
| Single page | `index.html` only; no new pages |
| Chinese UI strings | `stateFromJson` errors etc. are Chinese |

## Testing

- Pure logic lives in ESM-exported functions → unit-testable: `node --test tests/editor.test.mjs`.
- Tests cover JSON round-trip (`stateFromJson` → `toCircuitJson`), validation errors, and graph transitions (`addNode`/`removeNode`/`moveNode`).
- No DOM in tests: pure functions must not touch `document` (see `component-guidelines.md`).

## Contract Sync (the important one)

`ops.js` `OPS` and `ir.py` describe the **same** `circuit_v0` contract (ops, params, schema). When changing ops:

1. Update `ops.js` metadata (label/params/defaults) **and** `ir.py` validation together.
2. Dual-backend (F7+): each op carries `backends: ["gaussian"|"fock"]`; per-backend param-name translation lives in explicit tables (`FOCK_UI_TO_V1_PARAM` / `FOCK_V1_TO_UI_PARAM` in ops.js/editor.js) — never inline ad-hoc renames. UI param names stay gaussian-flavored (`T`, `phi`); Fock IR keeps `eta`, `r`-only.
2. Keep `stateFromJson` (frontend) and `load_circuit` (backend) aligned on required vs optional fields (`advanced: true` params may be absent).
3. Add/adjust `tests/editor.test.mjs` for new ops.

## Design Tokens

- Colors/spacing/radii in `tokens.css` `:root` variables only; `style.css` consumes them.
- No raw hex/rgb values in `style.css` or inline styles.

---

## Pre-Commit Checklist

```
[ ] node --test tests/editor.test.mjs passes
[ ] No console.log / debugger residue
[ ] ops.js ↔ ir.py contract in sync (both changed if ops changed)
[ ] New pure functions exported and covered by editor.test.mjs
[ ] No new dependencies, no framework imports
[ ] Chinese UI strings, English code identifiers
```

## Anti-Patterns

- Debug `console.log` left in — same rule as backend `print()` residue.
- Fixing a frontend bug by hardcoding op-specific logic in `app.js` instead of the op table / IR.
- Frontend-only contract changes without touching `ir.py` (or vice versa) — the two drift silently.
- Inline styles duplicating token values.
