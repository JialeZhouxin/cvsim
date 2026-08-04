# Directory Structure

> Layout for the Gaussian Lab frontend (`cvsim/lab/static/`).

---

## Overview

The lab is **framework-free vanilla JS**: no React/Vue, no bundler, no `node_modules`, no TypeScript. ES modules loaded directly by the browser. The backend is FastAPI in the same `cvsim/lab/` package.

---

## Directory Layout

```text
cvsim/lab/
├── ir.py            # circuit_v0 IR: schema validation (CircuitV0Error)
├── server.py        # FastAPI app: GET /health, POST /run (422 mapping)
├── __main__.py      # uvicorn entry point
└── static/          # all frontend assets, served as-is
    ├── index.html   # single page, loads app.js as <script type="module">
    ├── app.js       # application assembly + Wigner visualization
    ├── editor.js    # sequence editor: state + JSON sync + DOM wiring
    ├── ops.js       # op metadata (OPS whitelist) + pure graph helpers
    ├── style.css    # component styles
    └── tokens.css   # design tokens (colors, spacing, radii)
```

## Module Rules

| File | Owns | Never contains |
|------|------|----------------|
| `ops.js` | `OPS` metadata, `TAU`, pure node helpers (`addNode`, `removeNode`, `moveNode`, `updateParam`, `sourceModes`, `toCircuitJson`) | DOM access, `document.*` |
| `editor.js` | editor state, `stateFromJson`/`toCircuitJson` sync, `initEditor()` DOM wiring | circuit-execution logic |
| `app.js` | page assembly, run → visualization | op metadata definitions |
| `tokens.css` | design tokens (`:root` custom properties) | component-specific rules |
| `style.css` | component styles | raw color/spacing values (use tokens) |

References: `cvsim/lab/static/*.js`, `tests/editor.test.mjs` (node:test for the pure parts).

Rules:
- New frontend files go under `static/`; ES modules use explicit `.js` extensions in imports.
- New backend endpoints go in `server.py`; IR validation in `ir.py`.
- Tests for pure frontend logic live in `tests/editor.test.mjs` (repo-root `tests/`), not inside `static/`.

## Anti-Patterns

- Adding a bundler/transpiler "for later" — no build step exists; direct ES modules are the contract.
- New `.html` pages — the lab is a single page; extend `index.html`.
- Framework imports (React, Vue, etc.) — violates the no-dependency convention (`CODE_REVIEW_GUIDE.md` §1.2: no new dependencies without review).
