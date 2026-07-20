"""Bosonic state: list of Gaussian components (V, r̄, w)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from cvsim.conventions import vacuum_cov, vacuum_mean

if TYPE_CHECKING:
    from cvsim.gaussian.state import GaussianState


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
        if not self.components:
            raise ValueError("empty BosonicState")
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
    def from_gaussian(cls, state: GaussianState) -> BosonicState:
        """Wrap a GaussianState as one component with weight 1."""
        return cls(
            components=[
                Component(
                    V=np.asarray(state.V, dtype=float).copy(),
                    rbar=np.asarray(state.rbar, dtype=complex).copy(),
                    w=1.0 + 0.0j,
                )
            ]
        )
