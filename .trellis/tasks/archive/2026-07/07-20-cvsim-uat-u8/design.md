# Design · UAT U8

## `_u8` shape

```python
def _u8():
    # B condition
    st = even_cat(0.8)
    st2 = b_cond(st, 0, 0.0, sqrt(2)*0.8)
    b_ok = st2.n_components==4 and abs(weight_sum-1)<1e-10 and abs(w0)>abs(w1)

    # G sample stats
    xs = [g_sample(vac, rng=default_rng(0)) for _ in range(2000)]
    g_ok = abs(mean)<0.08 and abs(var-0.5)<0.08

    # B sample ≡ G single-comp
    o_g = g_sample(sq, rng=default_rng(7))
    o_b = b_sample(from_gaussian(sq), rng=default_rng(7))
    gb_ok = abs(o_g-o_b)<1e-12

    # F loss |1>
    rho = f_loss(fock(1,8), 0.3)
    f_ok = abs(rho[0,0]-(1-T))<1e-12 and abs(rho[1,1]-T)<1e-12

    return all, detail_str
```

## Docs

- USER_ACCEPTANCE: U8 table; remove from 未做: B cond / sample / Fock loss
- banner: U1–U5 + U7 + U8
- pytest count → 80

## Files

| File | Change |
|------|--------|
| `cvsim/demos/user_acceptance.py` | +U8 |
| `cvsim/USER_ACCEPTANCE.md` | +U8, 未做, 计数 |
| `cvsim/README.md` | 若提 6/6 → 7/7 |
