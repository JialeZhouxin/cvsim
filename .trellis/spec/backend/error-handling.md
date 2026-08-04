# Error Handling

> How `cvsim` validates inputs and surfaces errors.

---

## Overview

Two layers, two styles:

- **Library layer** (`cvsim/gaussian`, `cvsim/fock`, `cvsim/bosonic`): plain `ValueError` at entry points, fail-fast. No custom exception hierarchy.
- **Lab layer** (`cvsim/lab`): one custom subclass `CircuitV0Error(ValueError)` for IR validation; FastAPI maps it to HTTP 422 at the boundary.

---

## Library Layer: `raise ValueError` at Entry

Validate arguments/constructor inputs immediately; every message is an f-string carrying the offending value.

```python
raise ValueError(f"T must be in [0,1], got {T}")
```

Reference files (repeated pattern, dozens of call sites):
- `cvsim/bosonic/channels.py:39` — range check with value
- `cvsim/bosonic/gkp.py:127` — enum-style check (`cross` must be `'none'|'nn'|'full'`)
- `cvsim/gaussian/state.py` — constructor validates `V`/`rbar` shapes, `nmode >= 1`

Rules:
- Check at function/constructor entry, before any computation.
- Message = constraint + `got {value}` (or `{value!r}` for strings).
- No custom exception classes in library code — one class for everything is the pattern.

## Validation Is Explicit, Not Implied

`GaussianState.__post_init__` validates *shape* only; physicality (`V + iΩ/2 ≽ 0`) is **not** enforced at construction (comment in `cvsim/gaussian/state.py`). Callers opt in:

```python
state.is_physical(atol=1e-10)      # or cvsim.gaussian.analyse.is_physical
validate_state(...)                # heavier, explicit call
```

Don't silently clamp or normalize bad input to make it pass — raise instead.

## Lab Layer: IR Errors and the 422 Boundary

`cvsim/lab/ir.py` defines `CircuitV0Error(ValueError)`; `load_circuit` raises it with `where:`-prefixed messages (`ir.py:83-137`, helpers `_require`, `_as_complex`, `_as_pos_int`).

`cvsim/lab/server.py:56` catches it at the API boundary:

```python
except CircuitV0Error as e:
    raise HTTPException(status_code=422, detail=str(e)) from e
```

Rules:
- IR validation lives in `ir.py`, not in `server.py` handlers.
- API boundary converts domain errors to HTTP status; never leak tracebacks.
- 422 for client-payload problems (the UI shows `detail` to the user).

---

## Anti-Patterns

| Pattern | Why it fails here |
|---------|-------------------|
| Custom exception per module | Library uses plain `ValueError` everywhere; hierarchy adds nothing |
| Silently clamping params (e.g. `min(max(x, 0), 1)`) | Hides bad input; physics results become wrong without a trace |
| `assert` for user-input validation | Stripped under `python -O`; use `raise ValueError` |
| Catching broad `Exception` in library code | No recovery happens inside the lib; let callers handle |
| `print()` inside library modules | Debug residue; demos print, library code never does |

## Verification

```bash
ruff check cvsim/
python -m pytest tests/ -q
```
