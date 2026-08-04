# State Management

> The lab's actual state pattern: module-level singleton + factory + pure transitions. No framework, no store library.

---

## Overview

Editor state is a module-level object created by a `defaultState()` factory, mutated only through exported pure functions, and synced with the backend via a JSON contract (`circuit_v0`). Pattern source: `cvsim/lab/static/editor.js`.

---

## The Pattern

### 1. State shape via factory

```js
const defaultState = () => ({
  nodes: [],
  view: { wigner_mode: 0, lim: 5.0, n: 64 },
  ui: {},
});
```

- `nodes`: circuit graph (op nodes + params).
- `view`: visualization settings (Wigner mode, axis limits, grid size).
- `ui`: transient UI state.
- Factory (not a literal) so every reset gets a fresh object — `initEditor()` calls `state = defaultState()`.

### 2. Single mutable reference

`let state` at module scope (`editor.js`). `app.js` and DOM handlers read it via the module's exported accessor path; there is exactly one copy of the circuit state.

### 3. Transitions are pure functions

All mutations go through exported helpers in `ops.js` / `editor.js`:

- `addNode(op, params)`, `removeNode(id)`, `moveNode(id, dy)`, `updateParam(id, key, value)`, `updateMode(view, …)`
- `stateFromJson(payload)` / `toCircuitJson(state)` — two-way JSON sync (see below)

Handlers never mutate `state.nodes` directly from event listeners; they call these functions.

### 4. JSON is the interchange contract

`stateFromJson` validates a `circuit_v0` payload (`schema: "circuit_v0"` checked first) and builds state; `toCircuitJson` serializes back. This is the **same contract `cvsim/lab/ir.py` validates server-side** — frontend and backend are two validators of one schema. Unknown ops / malformed shapes are errors (the frozen-graph policy keeps UI consistent).

---

## Rules

- State changes only through exported pure functions — keeps node:test possible and diffable.
- Circuit state (`nodes`) stays separate from view state (`view`/`ui`); JSON sync covers `nodes` only.
- Reset by reassigning from the factory, never by clearing fields in place.

## Anti-Patterns

| Pattern | Why it fails here |
|---------|-------------------|
| `window.myState = …` globals | Two copies of state drift; module singleton is the convention |
| Mutating `state.nodes` in event listeners | Untestable, no validation; use `addNode`/`removeNode`/… |
| Multiple sources of truth (DOM + JS copies) | JSON sync + single `state` object is the contract |
| Creating state with a literal at module top | Same object reused across resets; use the factory |
| Schema check after partial parsing | `schema !== "circuit_v0"` is checked first (`stateFromJson`) |

## Verification

```bash
node --test tests/editor.test.mjs
```
