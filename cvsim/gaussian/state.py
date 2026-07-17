"""Gaussian state: (V, r̄)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvsim.conventions import vacuum_cov, vacuum_mean


@dataclass
class GaussianState:
    """Gaussian state in xxpp order.

    Attributes:
        V: covariance (2m, 2m)
        rbar: displacement (2m,)
    """

    V: np.ndarray
    rbar: np.ndarray

    def __post_init__(self) -> None:
        self.V = np.asarray(self.V, dtype=float)
        self.rbar = np.asarray(self.rbar, dtype=float)
        d = self.V.shape[0]
        if self.V.shape != (d, d) or self.rbar.shape != (d,):
            raise ValueError("V must be (2m,2m) and rbar (2m,)")
        if d % 2 != 0:
            raise ValueError("dimension must be even (2m)")

    @property
    def nmode(self) -> int:
        return self.V.shape[0] // 2

    @classmethod
    def vacuum(cls, nmode: int = 1) -> GaussianState:
        return cls(V=vacuum_cov(nmode), rbar=vacuum_mean(nmode))

    def copy(self) -> GaussianState:
        return GaussianState(V=self.V.copy(), rbar=self.rbar.copy())
