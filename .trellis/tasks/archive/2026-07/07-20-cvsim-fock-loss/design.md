# Design · Fock loss A1

## Types

```python
# cvsim/fock/density.py (or state.py)
@dataclass
class FockDensity:
    rho: np.ndarray  # (N,N)

    @property
    def cutoff(self) -> int: ...
    @classmethod
    def from_pure(cls, state: FockState) -> FockDensity:
        if state.nmode != 1: raise
        a = state.amps
        return cls(rho=np.outer(a, a.conj()))
```

## loss

```python
def loss(state: FockState | FockDensity, T: float) -> FockDensity:
    if not 0<=T<=1: raise
    if isinstance FockState and nmode!=1: raise
    ρ = from_pure or state.rho
    # Kraus operators E_k, k=0..N-1
    # E_k[m,n] = δ_{m, n-k} * sqrt(C(n,k)) * T**((n-k)/2) * (1-T)**(k/2)
    ρ' = sum_k E_k @ ρ @ E_k.conj().T
    hermitize
```

Build E_k as N×N sparse-ish dense once per call.

## Observables (minimal)

```python
def trace(rho_state) -> float: Tr ρ
def mean_photon(rho_state) -> float: sum n ρ_nn
def pnrd_probs(rho_state) -> array: diag real
```

Either overload in `observables.py` via isinstance, or `density_observables` — prefer **same names + isinstance** in `observables.py` to keep import surface small.

## Files

| File | Change |
|------|--------|
| `cvsim/fock/density.py` | NEW `FockDensity` |
| `cvsim/fock/channels.py` | NEW `loss` |
| `cvsim/fock/observables.py` | ρ support |
| `cvsim/fock/__init__.py` | export |
| `tests/test_fock_loss.py` | AC-F* |

## Tests

- T=1 pure identity
- T=0 vacuum
- |1⟩ diagonal formula
- coherent ⟨n⟩
