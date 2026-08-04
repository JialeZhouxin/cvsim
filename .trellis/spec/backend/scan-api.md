# `/scan` API Contract (F-LAB-SCAN)

> Cross-layer contract added in L4: single-parameter sweep → E_N curve.

## 1. Scope / Trigger

- Trigger: L4 added `POST /scan` (param sweep of one node's real-numeric param → `log_negativity` curve). Cross-layer request/response contract → code-spec depth mandatory.

## 2. Signatures

```python
# cvsim/lab/ir.py
def scan_circuit(circuit: CircuitV0, sweep: dict[str, Any]) -> dict[str, Any]

# cvsim/lab/server.py
@router.post("/scan")  # validate -> scan_circuit -> 422 on CircuitV0Error
```

## 3. Contracts

Request: `circuit_v0` payload **plus** a `sweep` object (never persisted back to schema):

```json
{"schema": "circuit_v0", "seed": 0, "nodes": [...], "edges": [], "view": {...}, "ui": {},
 "sweep": {"node_id": "s0", "param": "r", "min": 0.0, "max": 2.0, "n": 50, "modes_A": [0]}}
```

Response (pure function, no RNG, same request → same response):

```json
{"node_id": "s0", "param": "r", "min": 0.0, "max": 2.0, "n": 50,
 "modes_A": [0], "xs": [...], "ys": [...]}
```

- `xs = linspace(min, max, n)`; `ys[i]` = `log_negativity` at param value, **`null` when singular** (curve breakpoint, frontend skips).
- Sweepable params: **real-numeric only** (op's `SWEEPABLE_PARAMS` in ir.py mirrors ops.js `sweep` metadata). Complex params (e.g. coherent `alpha`) are never sweepable.

## 4. Validation & Error Matrix

| Condition | Error |
|-----------|-------|
| `node_id` unknown / op has no such param | 422 `{detail}` |
| `param` not real-numeric (e.g. `alpha`) | 422 |
| `min`/`max` not finite (`math.isfinite`) | 422 (NaN would leak into response) |
| `min >= max` | 422 |
| `n` not int in `[2, 200]` | 422 |
| `modes_A` not non-empty int list, out of range, or len ≥ nmode | 422 |
| circuit contains measurement nodes (homodyne/heterodyne) | 422 (E_N undefined on conditional states) |
| `min`/`max` invalid for op domain (e.g. `G < 1`) | 422 from underlying gate/channel ValueError |

## 5. Good / Base / Bad Cases

- **Good**: TMSV `r ∈ [0,2]` → ys ≈ `2r/ln2` (pure TMSV, atol 1e-6; probe measured maxErr 7e-15).
- **Base**: `G` sweep on amplifier with loss — curve bends down (physical mixing reduces entanglement).
- **Bad**: `min=-inf` → NaN midpoints → `JSON.parse` crash in frontend. Fixed by `math.isfinite` gate (P1 from check).

## 6. Tests Required

- `tests/test_lab_l4.py`:
  - analytic TMSV E_N = 2r/ln2 across n≥20 points (atol 1e-6)
  - 422 matrix: unknown node/param, non-finite range, min≥max, n out of bounds, bad modes_A, measurement node in circuit, G<1
  - 3-mode `modes_A` selection
  - sweep never writes back: circuit_v0 round-trip unchanged
- CDP probe `tests/lab_scan_probe.mjs`: panel renders, defaults (r: 0–2, n=50), modes_A default `[0]`, SVG polyline points, E_N vs analytic.

## 7. Wrong vs Correct

```python
# Wrong: only pmin < pmax
pmin = _num(sweep.get("min"), "sweep.min", "min")
pmax = _num(sweep.get("max"), "sweep.max", "max")
if not pmin < pmax: raise CircuitV0Error(...)   # -inf / inf / NaN slip through

# Correct: finite gate first
import math
if not (math.isfinite(pmin) and math.isfinite(pmax) and pmin < pmax):
    raise CircuitV0Error("sweep: need finite min < max")
```
