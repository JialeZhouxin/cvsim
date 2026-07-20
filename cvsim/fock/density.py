"""Single-mode Fock density matrix (truncated)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvsim.fock.state import FockState


@dataclass
class FockDensity:
    """1-mode density operator ρ, shape (cutoff, cutoff)."""

    rho: np.ndarray

    def __post_init__(self) -> None:
        self.rho = np.asarray(self.rho, dtype=complex)
        if self.rho.ndim != 2 or self.rho.shape[0] != self.rho.shape[1]:
            raise ValueError("rho must be square 2-D")

    @property
    def cutoff(self) -> int:
        return int(self.rho.shape[0])

    @property
    def nmode(self) -> int:
        return 1

    @classmethod
    def from_pure(cls, state: FockState) -> FockDensity:
        if state.nmode != 1:
            raise ValueError("FockDensity.from_pure requires single-mode state")
        a = state.amps
        return cls(rho=np.outer(a, a.conj()))

    def copy(self) -> FockDensity:
        return FockDensity(rho=self.rho.copy())
