"""Sparse photon-number amplitudes (F3 vision: photon-number-sparse states).

``FockSparse`` stores the amplitude tensor as a scipy.sparse COO array —
states with few populated Fock components (single photons, GKP-like combs,
sparse superpositions) keep memory/symplectic scaling flat in the *number of
occupied components*, not the dense Hilbert-space volume. Anchored at m≤10
(vision Q6: dense caps at m≤4, sparse extends to m≤10+).

Honest boundary: only *diagonal* gates (phase, kerr) and permutations stay
sparse. Any non-diagonal unitary (squeeze, displace, beamsplitter, ...)
generically fills the tensor — :meth:`to_dense` hands over to the dense
:class:`FockState` machinery (identical physics, vision L171).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import coo_array

from cvsim.fock.state import FockState

__all__ = ["FockSparse"]


@dataclass
class FockSparse:
    """Photon-number-sparse amplitude state (COO tensor, complex)."""

    data: coo_array
    cutoffs: tuple[int, ...]

    def __init__(self, data: coo_array, cutoffs: tuple[int, ...] | list[int]) -> None:
        if data.ndim != len(cutoffs):
            raise ValueError(
                f"data ndim {data.ndim} != len(cutoffs) {len(cutoffs)}"
            )
        for d, c in zip(data.shape, cutoffs, strict=False):
            if d != c:
                raise ValueError(f"shape {data.shape} != cutoffs {cutoffs}")
        norm = float(np.sum(np.abs(data.data) ** 2))
        if not np.isclose(norm, 1.0, atol=1e-10):
            raise ValueError(
                f"amplitude must be normalized (Σ|ψ|² = 1), got {norm}"
            )
        object.__setattr__(self, "data", data.tocoo())
        object.__setattr__(self, "cutoffs", tuple(cutoffs))

    @property
    def nmode(self) -> int:
        return len(self.cutoffs)

    @property
    def nnz(self) -> int:
        return self.data.nnz

    @property
    def amps(self) -> np.ndarray:
        """Dense amplitude tensor (materializes the full volume — use with care)."""
        return self.data.toarray()

    # -- factories -----------------------------------------------------------

    @classmethod
    def vacuum(cls, nmode: int, cutoffs: int | list[int] = 10) -> FockSparse:
        cutoffs = [cutoffs] * nmode if isinstance(cutoffs, int) else list(cutoffs)
        data = coo_array(
            (np.array([1.0 + 0j]), np.zeros((nmode, 1), dtype=int)),
            shape=tuple(cutoffs),
        )
        return cls(data, cutoffs)

    @classmethod
    def single_photon(cls, mode: int, nmode: int, cutoffs: int | list[int] = 10) -> FockSparse:
        """|1⟩ on `mode`, vacuum elsewhere."""
        cutoffs = [cutoffs] * nmode if isinstance(cutoffs, int) else list(cutoffs)
        idx = np.zeros((nmode, 1), dtype=int)
        idx[mode, 0] = 1
        data = coo_array((np.array([1.0 + 0j]), idx), shape=tuple(cutoffs))
        return cls(data, cutoffs)

    @classmethod
    def from_components(
        cls,
        components: dict[tuple[int, ...], complex],
        cutoffs: int | list[int],
    ) -> FockSparse:
        """``{fock_tuple: amplitude}`` — e.g. {(0, 3): 1/√2, (2, 1): 1j/√2}."""
        cutoffs = list(cutoffs)
        nmode = len(cutoffs)
        comps = tuple(components)
        coords = np.asarray(comps, dtype=int).T
        vals = np.asarray([components[c] for c in comps], dtype=complex)
        data = coo_array((vals, coords), shape=tuple(cutoffs))
        return cls(data, cutoffs)

    # -- sparse-preserving ops ------------------------------------------------

    def phase(self, mode: int, theta: float) -> FockSparse:
        """Diagonal e^{iθ a†a} — stays sparse (per-component phase)."""
        self._check_mode(mode)
        coo = self.data.tocoo()
        vals = coo.data * np.exp(1j * theta * coo.coords[mode])
        return FockSparse(coo_array((vals, coo.coords), shape=coo.shape), self.cutoffs)

    def kerr(self, mode: int, chi: float) -> FockSparse:
        """Diagonal e^{iχ n²} (aligned with ``gates.kerr``) — stays sparse."""
        self._check_mode(mode)
        coo = self.data.tocoo()
        n = coo.coords[mode]
        vals = coo.data * np.exp(1j * chi * n * n)
        return FockSparse(coo_array((vals, coo.coords), shape=coo.shape), self.cutoffs)

    def permute(self, perm: list[int]) -> FockSparse:
        """Reorder mode axes (e.g. swap [1, 0]) — stays sparse."""
        if sorted(perm) != list(range(self.nmode)):
            raise ValueError(f"perm {perm} must be a permutation of 0..{self.nmode - 1}")
        coo = self.data.tocoo()
        # coords: tuple of per-axis index arrays → reorder axes by `perm`
        coords = tuple(coo.coords[i] for i in perm)
        return FockSparse(
            coo_array((coo.data, coords), shape=coo.shape), self.cutoffs
        )

    # -- measurement ----------------------------------------------------------

    def pnrd_probs(self, mode: int = 0) -> np.ndarray:
        """Marginal P(n) on `mode` — diagonal access, no dense materialization."""
        self._check_mode(mode)
        coo = self.data.tocoo()
        n = coo.coords[mode]
        marginal = np.zeros(self.cutoffs[mode])
        np.add.at(marginal, n, np.abs(coo.data) ** 2)
        return marginal

    def norm(self) -> float:
        """Σ|ψ|² over occupied components (1.0 by construction)."""
        return float(np.sum(np.abs(self.data.data) ** 2))

    # -- dense handoff --------------------------------------------------------

    def to_dense(self) -> FockState:
        """Materialize as a dense :class:`FockState` (identical physics)."""
        return FockState(amps=self.data.toarray())

    # -- internals ------------------------------------------------------------

    def _check_mode(self, mode: int) -> None:
        if not 0 <= mode < self.nmode:
            raise IndexError(f"mode {mode} out of range for nmode={self.nmode}")
