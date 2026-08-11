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
    _nbar: float | None = None  # thermal factory parameter (analytic tail)

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

    @classmethod
    def thermal(cls, cutoff: int, nbar: float) -> FockDensity:
        """Thermal state with mean photon number nbar (diagonal).

        p_n = nbar^n / (nbar+1)^{n+1}; exact analytic tail
        (nbar/(nbar+1))^cutoff.
        """
        if cutoff < 1:
            raise ValueError("cutoff must be >= 1")
        if nbar < 0:
            raise ValueError("nbar must be >= 0")
        n = np.arange(cutoff)
        # p_n = (nbar/(nbar+1))^n / (nbar+1) — base < 1, no overflow for large nbar
        p = (nbar / (nbar + 1.0)) ** n / (nbar + 1.0)
        rho = np.diag(p).astype(complex)
        return cls(rho=rho, nmode=1, _nbar=nbar)

    @property
    def tail(self) -> float | None:
        """Analytic truncation tail: thermal states exact, else ``None``.

        Thermal tail = (nbar/(nbar+1))^cutoff (closed form). General density
        matrices: unknown — never guessed (vision §5).
        """
        if self._nbar is not None:
            return float((self._nbar / (self._nbar + 1.0)) ** self.cutoff)
        return None

    def copy(self) -> FockDensity:
        return FockDensity(rho=self.rho.copy(), nmode=self.nmode, _nbar=self._nbar)
