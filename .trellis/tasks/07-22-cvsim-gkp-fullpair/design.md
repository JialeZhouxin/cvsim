# Design · full-pair

## Code path

`_gkp_x_comb`:

```python
if cross == "nn" and N >= 1:
    # existing neighbour loop
elif cross == "full" and N >= 0:
    for i_idx, ki in enumerate(ks):
        for kj in ks[i_idx+1:]:
            # n = |ki-kj| in index units for gkp0;
            # for gkp1 same: spacing multiples of Δ via xs
            dx = xs[ki] - xs[kj]
            ov = exp(-dx**2 / (4*epsilon))
            m = 0.5*(xs[ki]+xs[kj])
            d = 0.5*(xs[ki]-xs[kj])
            w_c = a[ki]*a[kj]*ov
            ± complex peaks
```

Use `xs` so gkp0/gkp1 both correct.

## K formula

| cross | K |
|-------|---|
| none | 2N+1 |
| nn | 6N+1 (N≥1) |
| full | (2N+1)² |

## Files

- `cvsim/bosonic/gkp.py`
- `tests/test_bosonic_gkp_full.py` (new)
- maybe extend bad_arg tests
- USER_ACCEPTANCE / README

## Risk

| 风险 | 缓解 |
|------|------|
| 破 nn 测 | 保留 nn 分支不动 |
| 权重非正 | 同 renorm |
| N 太大 | 测 N≤2–3 |
