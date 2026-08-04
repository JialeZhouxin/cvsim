# Component & Module Patterns

> Vanilla-JS module conventions for the lab frontend. ("Components" here = ES modules + DOM-wiring init functions, not framework components.)

---

## Overview

The lab splits into three JS modules with a strict separation: **pure logic vs DOM wiring**. Pure functions are `export`ed and unit-tested with node:test; DOM work lives only inside `init*` functions. See the header comment in `cvsim/lab/static/editor.js` (L0/L2): "Pure helpers are ESM-exported for node --test; DOM work lives only inside initEditor."

---

## Module Structure (the local pattern)

1. **File header comment**: level (e.g. `Gaussian Lab L2 —`) + one-line responsibility.
2. **`"use strict";`** at the top of every module.
3. **Metadata as data, not code**: op definitions are plain objects in `OPS` (`ops.js`) — `{label, kind, modes, params: {min, max, step, def}}`. Slider ranges, defaults, and labels all derive from this table; UI never hardcodes per-op logic.
4. **Pure helpers first, DOM wiring last**: `editor.js` exports `stateFromJson` / `toCircuitJson` / `addNode` etc., then `initEditor()` at the bottom attaches event listeners.

## Op Metadata Contract (`ops.js`)

`OPS` is the single source of truth for the palette, sliders, and JSON validation. It **mirrors `cvsim/lab/ir.py`** (comment: "whitelist subset, mirrors ir.py"):

- `kind`: `source | single | two` (drives palette sections and source-mode counting via `sourceModes()`).
- `params.<k>`: `{min, max, step, def}`; `advanced: true` marks optional params (e.g. loss `nbar`) that default when absent in JSON. `optional: true` is the same contract (homodyne `phi`, L3); treat them identically in `stateFromJson`.
- `sweep: [min, max]` marks a **real-numeric sweepable** param + adaptive default range for the scan panel (L4). Params without it (e.g. complex `alpha`) are never sweepable. Mirrors `SWEEPABLE_PARAMS` in ir.py.
- Changing an op means updating **all three**: `ops.js`, `ir.py`, and vision §4 whitelist (`docs/vision-gaussian-lab-ui.md`) — three views of one contract.

## Validation & Security Patterns

- `stateFromJson` validates every field, returning `{error}` objects with **Chinese messages** (`editor.js`) — the UI shows them verbatim.
- `Object.hasOwn(OPS, n.op)` instead of `n.op in OPS` — `__proto__`/`constructor` are inherited keys on `OPS` (OCR finding, fixed in `8172398`).
- Node ids must be non-empty unique strings (`seenIds` set).

## Styling

- Design tokens (colors, spacing, radii) live in `tokens.css` as `:root` custom properties.
- Component styles in `style.css` reference tokens; never inline raw hex values.
- SVG overlays (axes, ticks) are drawn from JS but styled via CSS classes/attributes (see `cvsim/lab/static/app.js` Wigner overlay work).

---

## Anti-Patterns

| Pattern | Why it fails here |
|---------|-------------------|
| DOM calls inside pure/exported functions | Breaks node --test (no DOM in node) |
| Per-op `if (op === 'squeeze') …` chains in UI code | Op table exists precisely to avoid this; extend `OPS` |
| Magic numbers for angles in JS | `TAU = 2 * Math.PI` is exported from `ops.js`; use it |
| English-only UI strings | All user-facing messages are Chinese in this lab |
| Circular imports between app/editor/ops | `ops.js` imports nothing; keep the dependency direction one-way |

## Verification

```bash
node --test tests/editor.test.mjs
```
