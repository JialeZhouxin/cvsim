"""Bosonic state: list of Gaussian components (V, r̄, w)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


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
