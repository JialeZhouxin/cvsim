# Design System (Frontend)

> Visual design conventions for the Gaussian Lab frontend (`cvsim/lab/static/`): theme, tokens, and the rules for extending them.

---

## Overview

The lab uses **Hallmark Cobalt** (genre `modern-minimal` · macrostructure `Workbench` · theme `Cobalt` · nav `N1a minimal` · footer `Ft2 inline`). The theme is **offline-substituted**: zero CDN, system font stacks only (Space Grotesk → Bahnschrift, JetBrains Mono → Cascadia Code). All design values live as `:root` custom properties in `tokens.css`; `style.css` only references them.

---

## Design Decisions (locked)

| Decision | Value | Reason |
|----------|-------|--------|
| Color space | OKLCH everywhere | Perceptual uniformity; tune neutrals via one hue (250°) |
| Neutrals | Cool, tinted 250° (paper → ink, L→D) | Cool-white paper suits data/dark-heatmap work |
| Accent | Electric cobalt `oklch(55% 0.19 260)` | Theme identity; focus reuses accent |
| Axis overlay | Ice-cyan `oklch(85% 0.09 210)` | Complementary to the inferno LUT — inferno has no cyan, so the axis never fights the heatmap |
| Type system | 2+1: display / body / mono | Body = Segoe UI stack; mono only for JSON, tables, meters (tabular-nums) |
| Scale | Major third 1.25, max 5 sizes (`--text-xs`…`--text-lg`) | No 6th size; if a component "needs" one, the layout is wrong |
| Spacing | 4pt scale (`--space-xs`…`--space-3xl`) | `--space-md` (0.75rem) is the default gap |
| Motion | Durations `instant/micro/short/med` (0/90/150/240ms) + 3 eases | Default: `--dur-micro` + `--ease-out` |
| Elevation | Single `--shadow-1` | One level is enough for a workbench surface |

## Token Semantics (`tokens.css`)

| Token group | Members | Contract |
|-------------|---------|----------|
| Colors | `--color-paper[-2|-3]`, `--color-rule`, `--color-neutral`, `--color-muted`, `--color-ink`, `--color-accent[-soft]`, `--color-focus`, `--color-error[-soft]`, `--color-success`, `--color-axis` | paper-2/paper-3 = inset surfaces (frames, meters); rule = borders; ink = text; accent-soft/error-soft = tinted fills; axis = canvas overlay only |
| Type | `--font-display`, `--font-body`, `--font-mono` | Display for headings/wordmark only; body everywhere else |
| Type scale | `--text-xs`…`--text-lg` | Base `1rem`; labels/notes `--text-sm` or `--text-xs` |
| Spacing | `--space-xs`…`--space-3xl` | No raw `px`/`rem` spacing values in `style.css` |
| Radii | `--radius-sm` (4px), `--radius-md` (6px) | md = cards/frames/inputs; sm = pills/tags |
| Motion | `--dur-*`, `--ease-*` | Transitions only; hover states use `--dur-micro` |
| Elevation | `--shadow-1` | Cards/frames that need separation |

## Layout (breakpoints & columns)

| Width | Layout | Columns |
|-------|--------|---------|
| `< 80rem` (1280px) | Single column, `max-width: 90rem` centered, normal page scroll | 1fr |
| `≥ 80rem` | 3-column workbench, **full width (no max-width cap)** | `13rem minmax(0, 1fr) minmax(0, 1.2fr)` |

- **Column semantics**: palette `13rem` (fixed) · circuit editor `1fr` · results/Wigner `1.2fr` (heatmap benefits from extra width).
- **`80rem` is the only layout breakpoint.** Below it the 3 columns are too narrow to be usable (the seq toolbar and node rows wrap, overflowing the column).
- The 3-column grid itself bounds line length — no `max-width` cap there; a centered gutter on ultrawide screens is wasted workspace.
- **Above-the-fold workbench**: at `≥ 80rem`, `html, body` are locked to `100dvh` with `overflow: hidden` — the page never scrolls (a real wheel does nothing). Content is compressed so the **default view has no scrollbars at all**: scan panel + state tables are `<details>` folds (start collapsed), the Wigner canvas is capped at `min(column width, calc(100dvh - 31rem))`, node rows and the JSON textarea are compacted. Expanding a fold may exceed the column — that column then scrolls (`:has(.fold[open])` → `overflow-y: auto`) so expanded content stays reachable.
- **`<details>` gotcha**: author `display` rules (e.g. `.scan__controls { display: flex }`) override the UA's collapse `display:none` — `.fold:not([open]) > *:not(summary) { display: none }` must stay in `style.css`.
- **Toolbar overflow rule**: any `.panel__actions` must wrap (`flex-wrap: wrap`) — a non-wrapping toolbar spills into the results column, where the Wigner canvas covers the buttons. Guarded by the probe hit-test check.

---

## Rules

1. **Tokens only, no raw values.** Component styles in `style.css` reference `var(--…)`; inline hex/px/rem colors and spacing are forbidden. Violations fail review.
2. **New tokens need a reason.** Adding a token changes every surface using it — the cost of a global edit. Prefer composing existing tokens (e.g. `color-mix`) over a new one.
3. **Don't introduce new font families.** The system-font stack is an offline constraint; a new family means a new substitution mapping.
4. **SVG overlays are JS-drawn, CSS-styled.** Axis/ticks (Wigner overlay, `app.js`) get styling via classes/attributes, never inline style attributes — `--color-axis` exists for exactly this.
5. **Semantic naming, not visual naming.** Token names describe role (`--color-muted`, not `--color-gray-2`) so theme swaps don't rename tokens.
6. **The `--color-axis` token is reserved** for canvas-overlay drawing; it is not a general UI accent.

## Probe Guardrails

In `tests/lab_scan_probe.mjs` (headless Edge CDP, zero-dep):

- hit-test at 1920/1280/640 — no interactive control may be covered by another element
- wheel-event check at ≥1280 — a real wheel must not move the page (`scrollTo` is a wrong proxy: it can programmatically scroll `overflow: hidden` containers)
- scrollbar check at ≥1280 — in the folded default view, no panel may exceed its column (`scrollHeight > clientHeight`)
- reset column scroll between widths: panel `scrollTop` survives width switches and skews hit-test coordinates

---

## Anti-Patterns

- Inline `#hex` or `oklch(...)` literals in `style.css` or JS string templates
- New token per component ("one-off" tokens) — reuse the scale instead
- A 6th type size or 5pt spacing step "just for this component"
- Referencing `tokens.css` values in JS instead of reading `getComputedStyle` (see `app.js` axis/rule color reads)
- Copying Hallmark token values into another theme without re-auditing the axis/LUT pairing (heatmap colors are physics-adjacent, not decorative)

---

## Adding a Token (path)

1. Add the `--…` property to `:root` in `tokens.css` with a semantic name + comment
2. Update this file's Token Semantics table
3. Use it via `var(--…)` in `style.css` — never inline the literal
4. Check the offline guard: no CDN/web-font fallbacks introduced
