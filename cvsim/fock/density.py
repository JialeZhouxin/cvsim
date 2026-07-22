"""Fock density matrix (truncated): 1-mode or 2-mode flattened."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvsim.fock.state import FockState


@dataclass
class FockDensity:
    """Density operator ρ, shape (d, d) with d = cutoff**nmode.

    nmode=1: d=N. nmode=2: d=N², basis |n0 n1⟩ row-major (n0 slow or
    kron order matching amps.reshape(N,N) ravel C-order).
    """

    rho: np.ndarray
    nmode: int = 1

    def __post_init__(self) -> None:
        self.rho = np.asarray(self.rho, dtype=complex)
        if self.rho.ndim != 2 or self.rho.shape[0] != self.rho.shape[1]:
            raise ValueError("rho must be square 2-D")
        if self.nmode not in (1, 2):
            raise ValueError("nmode must be 1 or 2")
        d = self.rho.shape[0]
        if self.nmode == 1:
            return
        # nmode=2: d must be perfect square
        n = int(round(d**0.5))
        if n * n != d:
            raise ValueError(f"2-mode rho dim {d} is not a perfect square")

    @property
    def cutoff(self) -> int:
        d = int(self.rho.shape[0])
        if self.nmode == 1:
            return d
        n = int(round(d**0.5))
        return n

    @classmethod
    def from_pure(cls, state: FockState) -> FockDensity:
        if state.nmode == 1:
            a = state.amps
            return cls(rho=np.outer(a, a.conj()), nmode=1)
        if state.nmode == 2:
            a = state.amps.ravel()
            return cls(rho=np.outer(a, a.conj()), nmode=2)
        raise ValueError("FockDensity.from_pure supports nmode 1 or 2 only")

    def copy(self) -> FockDensity:
        return FockDensity(rho=self.rho.copy(), nmode=self.nmode)
