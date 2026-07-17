"""Fock state: truncated single-mode amplitudes (MVP)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class FockState:
    """Single-mode pure state in truncated Fock basis.

    Attributes:
        amps: complex amplitudes c_0 ... c_{N-1}, shape (cutoff,)
    """

    amps: np.ndarray

    def __post_init__(self) -> None:
        self.amps = np.asarray(self.amps, dtype=complex).reshape(-1)

    @property
    def cutoff(self) -> int:
        return self.amps.shape[0]

    @classmethod
    def vacuum(cls, cutoff: int) -> FockState:
        if cutoff < 1:
            raise ValueError("cutoff must be >= 1")
        amps = np.zeros(cutoff, dtype=complex)
        amps[0] = 1.0
        return cls(amps=amps)

    def copy(self) -> FockState:
        return FockState(amps=self.amps.copy())
