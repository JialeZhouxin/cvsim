# Design · G5 Fock 2-mode loss

## FockDensity

```python
@dataclass
class FockDensity:
    rho: np.ndarray          # (d, d), d = N**nmode
    nmode: int = 1

    @property
    def cutoff(self) -> int: ...

    @classmethod
    def from_pure(cls, state: FockState) -> FockDensity:
        # nmode 1 or 2
```

旧构造 `FockDensity(rho=...)` → nmode=1。

## loss

```text
_kraus_ops(N, T)  # 已有 1 模 E_k

# mode 0: Ek_full = kron(Ek, I)
# mode 1: Ek_full = kron(I, Ek)
rho2 = sum_k Ek_full @ rho @ Ek_full.conj().T
```

两侧 `mode=None` 且 nmode=2：

```python
return loss(loss(state, T, mode=0), T, mode=1)
```

## observables

- `mean_photon` dens 2 模：diag → p(n0,n1) shape (N,N)  
- `pnrd_probs(..., mode=None)` → (N,N)；`mode=0|1` 边际  

## gates

2 模 dens：现有 1 模门路径继续 `mode must be 0` / nmode check → **raise 明确**「2-mode density gates out of scope」。

## Files

- `cvsim/fock/density.py`
- `cvsim/fock/channels.py`
- `cvsim/fock/observables.py`（mean/pnrd/trace）
- `cvsim/fock/gates.py`（可选：dens nmode!=1 raise 更清晰）
- `tests/test_fock_2mode_loss.py`
- README / USER_ACCEPTANCE

## Risk

| 风险 | 缓解 |
|------|------|
| 破 1 模 dens | 默认 nmode=1 + 旧测 |
| N 太大慢 | 测 N≤8–12 |
| from_pure 调用点 | 只扩 2 模；1 模路径不变 |
