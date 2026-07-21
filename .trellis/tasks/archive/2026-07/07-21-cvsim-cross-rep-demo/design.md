# Design · m4 cross-rep

## File

`cvsim/demos/m4_cross_rep.py`

## Logic

```python
def t4_squeeze_n(r=0.5, fock_cutoff=24):
    n_ex = sinh(r)**2
    n_g = mean_photon(g_squeeze(vac, r))
    n_f = mean_photon(f_squeeze(FockState.vacuum(fock_cutoff), r))
    print columns; assert |n_g-n_ex|<1e-12; assert |n_f-n_ex|<1e-3

def t1_coherent_loss(alpha=0.7, T=0.4, fock_cutoff=24):
    n_ex = T * abs(alpha)**2
    n_g = mean_photon(g_loss(g_displace(vac, alpha), T))
    n_f = mean_photon(f_loss(f_displace(FockState.vacuum(N), alpha), T))
    n_b = mean_photon(b_loss(BosonicState.from_gaussian(g_displace(...)), T))
    # or from_gaussian after displace on G then wrap
    assert |n_g-n_ex|<1e-12; |n_b-n_g|<1e-12; |n_f-n_ex|<0.05
```

## Params

| 题 | 参数 |
|----|------|
| T4 | `r=0.5`, F cutoff 24 |
| T1 | `α=0.7` real, `T=0.4`, F cutoff 24 |

## Docs

- `cvsim/README.md`：demos 列表 + 一行 m4
- 根理论 README：**不**加 API（可选工程段已有 cvsim 链则不动理论闭环）

## No

- pytest 新文件（demo assert 够）
- UAT 注册
