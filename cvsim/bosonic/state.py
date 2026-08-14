"""Bosonic state: list of Gaussian components (V, r̄, w)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvsim.conventions import vacuum_cov, vacuum_mean


def weight_sum(state: BosonicState) -> complex:
    """∑ w_k — should be 1 for a normalized density-operator decomposition."""
    return sum(c.w for c in state.components)


@dataclass
class Component:
    """One Gaussian peak: covariance, (possibly complex) mean, complex weight."""

    V: np.ndarray
    rbar: np.ndarray
    w: complex

    def __post_init__(self) -> None:
        self.V = np.asarray(self.V, dtype=float)
        self.rbar = np.asarray(self.rbar, dtype=complex)
        self.w = complex(self.w)


@dataclass
class BosonicState:
    components: list[Component]

    @property
    def n_components(self) -> int:
        return len(self.components)

    @property
    def nmode(self) -> int:
        # 0-mode state = empty component list (heterodyne K=1 condition tail);
        # gates still refuse empty states via gates._nmode.
        if not self.components:
            return 0
        return self.components[0].V.shape[0] // 2

    @classmethod
    def vacuum(cls, nmode: int = 1) -> BosonicState:
        """Single vacuum component: V=I/2, r̄=0, w=1."""
        if nmode < 1:
            raise ValueError("nmode must be >= 1")
        return cls(
            components=[
                Component(
                    V=vacuum_cov(nmode),
                    rbar=vacuum_mean(nmode).astype(complex),
                    w=1.0 + 0.0j,
                )
            ]
        )

    @classmethod
    def from_gaussian(cls, state) -> BosonicState:
        """Wrap object with .V and .rbar as one component w=1 (duck type)."""
        return cls(
            components=[
                Component(
                    V=np.asarray(state.V, dtype=float).copy(),
                    rbar=np.asarray(state.rbar, dtype=complex).copy(),
                    w=1.0 + 0.0j,
                )
            ]
        )


def coherent(alpha: complex, nmode: int = 1, mode: int = 0) -> BosonicState:
    """Coherent state |α⟩: single vacuum component displaced to r̄=√2(Re α, Im α).

    Direct construction (no gate overhead) — equivalent to
    ``displace(BosonicState.vacuum(nmode), alpha, mode)``.
    """
    if nmode < 1:
        raise ValueError("nmode must be >= 1")
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    rbar = np.zeros(2 * nmode, dtype=complex)
    a = complex(alpha)
    rbar[mode] = np.sqrt(2.0) * a.real
    rbar[nmode + mode] = np.sqrt(2.0) * a.imag
    return BosonicState(
        components=[Component(V=vacuum_cov(nmode), rbar=rbar, w=1.0 + 0.0j)]
    )
