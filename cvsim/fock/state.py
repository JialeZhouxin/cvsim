"""Fock state: truncated amplitudes, 1-mode (N,) or 2-mode (N,N)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class FockState:
    """Pure Fock state in truncated basis.

    amps.ndim == 1: single mode, shape (cutoff,)
    amps.ndim == 2: two mode, shape (cutoff, cutoff), c[n0, n1]
    """

    amps: np.ndarray

    def __post_init__(self) -> None:
        self.amps = np.asarray(self.amps, dtype=complex)
        if self.amps.ndim == 1:
            pass
        elif self.amps.ndim == 2:
            if self.amps.shape[0] != self.amps.shape[1]:
                raise ValueError("two-mode amps must be square (N,N)")
        else:
            raise ValueError("amps must be 1-D or 2-D")

    @property
    def cutoff(self) -> int:
        return int(self.amps.shape[0])

    @property
    def nmode(self) -> int:
        return 1 if self.amps.ndim == 1 else 2

    @classmethod
    def vacuum(cls, cutoff: int, nmode: int = 1) -> FockState:
        if cutoff < 1:
            raise ValueError("cutoff must be >= 1")
        if nmode == 1:
            amps = np.zeros(cutoff, dtype=complex)
            amps[0] = 1.0
            return cls(amps=amps)
        if nmode == 2:
            amps = np.zeros((cutoff, cutoff), dtype=complex)
            amps[0, 0] = 1.0
            return cls(amps=amps)
        raise ValueError("nmode must be 1 or 2")

    @classmethod
    def fock(cls, n: int, cutoff: int) -> FockState:
        if not 0 <= n < cutoff:
            raise ValueError(f"n={n} out of range for cutoff={cutoff}")
        amps = np.zeros(cutoff, dtype=complex)
        amps[n] = 1.0
        return cls(amps=amps)

    @classmethod
    def fock2(cls, n0: int, n1: int, cutoff: int) -> FockState:
        if not (0 <= n0 < cutoff and 0 <= n1 < cutoff):
            raise ValueError("occupation out of cutoff")
        amps = np.zeros((cutoff, cutoff), dtype=complex)
        amps[n0, n1] = 1.0
        return cls(amps=amps)

    def copy(self) -> FockState:
        return FockState(amps=self.amps.copy())
