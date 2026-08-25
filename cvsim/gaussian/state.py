"""Gaussian state: (V, r̄) in xxpp, ħ=1, V_vac = I/2."""

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
        # Note: constructor does *not* enforce physicality (V + iΩ/2 ≽ 0).
        # Use cvsim.gaussian.analyse.is_physical / validate_state when needed.

    @property
    def nmode(self) -> int:
        return self.V.shape[0] // 2

    def is_physical(self, *, atol: float = 1e-10) -> bool:
        """Uncertainty relation V + iΩ/2 ≽ 0 (ħ=1, xxpp)."""
        from cvsim.gaussian.analyse import is_physical

        return is_physical(self, atol=atol)

    # --- factories (F-STATE-FACTORY) ---

    @classmethod
    def vacuum(cls, nmode: int = 1) -> GaussianState:
        """m-mode vacuum: V = I/2, r̄ = 0."""
        if nmode < 1:
            raise ValueError("nmode must be >= 1")
        return cls(V=vacuum_cov(nmode), rbar=vacuum_mean(nmode))

    @classmethod
    def coherent(
        cls,
        alpha: complex,
        *,
        nmode: int = 1,
        mode: int = 0,
    ) -> GaussianState:
        """Coherent state: vacuum covariance, mean d(α) on `mode`."""
        from cvsim.symplectic import d_displace

        st = cls.vacuum(nmode)
        d = d_displace(nmode, alpha, mode)
        return cls(V=st.V, rbar=st.rbar + d)

    @classmethod
    def thermal(
        cls,
        nbar: float,
        *,
        nmode: int = 1,
        mode: int = 0,
    ) -> GaussianState:
        """Thermal state on `mode`, vacuum elsewhere.

        Single-mode block: V = ((2 n̄ + 1)/2) I₂.
        """
        if nbar < 0:
            raise ValueError("nbar must be >= 0")
        if not 0 <= mode < nmode:
            raise IndexError(f"mode {mode} out of range for nmode={nmode}")
        V = vacuum_cov(nmode)
        scale = 0.5 * (2.0 * nbar + 1.0)
        V = V.copy()
        V[mode, mode] = scale
        V[nmode + mode, nmode + mode] = scale
        return cls(V=V, rbar=vacuum_mean(nmode))

    @classmethod
    def squeezed(
        cls,
        r: float,
        phi: float = 0.0,
        *,
        nmode: int = 1,
        mode: int = 0,
    ) -> GaussianState:
        """Single-mode squeezed vacuum: S(r,φ)=R(φ)S(r)R(-φ) on vacuum."""
        from cvsim.gaussian.gates import apply_symplectic
        from cvsim.symplectic import S_phase, S_squeeze

        st = cls.vacuum(nmode)
        S_r = S_squeeze(nmode, r, mode)
        # S(r,φ) = R(φ) S(r) R(-φ); φ=0 degenerates to bare squeeze
        S = (
            S_r
            if phi == 0.0
            else S_phase(nmode, phi, mode) @ S_r @ S_phase(nmode, -phi, mode)
        )
        return apply_symplectic(st, S, validate=False)

    @classmethod
    def displaced_squeezed(
        cls,
        alpha: complex,
        r: float,
        phi: float = 0.0,
        *,
        nmode: int = 1,
        mode: int = 0,
    ) -> GaussianState:
        """Squeezed vacuum then displaced by α on `mode`."""
        from cvsim.symplectic import d_displace

        st = cls.squeezed(r, phi, nmode=nmode, mode=mode)
        return cls(V=st.V, rbar=st.rbar + d_displace(nmode, alpha, mode))

    @classmethod
    def tmsv(
        cls,
        r: float,
        *,
        nmode: int = 2,
        mode1: int = 0,
        mode2: int = 1,
    ) -> GaussianState:
        """Two-mode squeezed vacuum on (mode1, mode2)."""
        from cvsim.gaussian.gates import apply_symplectic
        from cvsim.symplectic import S_two_mode_squeeze

        if nmode < 2:
            raise ValueError("tmsv requires nmode >= 2")
        st = cls.vacuum(nmode)
        S = S_two_mode_squeeze(nmode, r, mode1, mode2)
        return apply_symplectic(st, S, validate=False)

    @classmethod
    def product(cls, *states: GaussianState) -> GaussianState:
        """Tensor product in xxpp ordering (always builds a new embed).

        Local mode k of a factor with m modes maps to a global slot;
        x-block then p-block layout is preserved globally. A single
        argument still goes through the embed path (deep copy of arrays).
        """
        if not states:
            raise ValueError("product() requires at least one state")

        ms = [s.nmode for s in states]
        M = sum(ms)
        V = np.zeros((2 * M, 2 * M), dtype=float)
        rbar = np.zeros(2 * M, dtype=float)

        offset = 0
        for st, m in zip(states, ms, strict=False):
            # local (x0..xm-1, p0..pm-1) → global (x_{off..}, p_{off..})
            local_to_global = list(range(offset, offset + m)) + list(
                range(M + offset, M + offset + m)
            )
            idx = np.asarray(local_to_global, dtype=int)
            rbar[idx] = st.rbar
            V[np.ix_(idx, idx)] = st.V
            offset += m

        return cls(V=V, rbar=rbar)

    def copy(self) -> GaussianState:
        return GaussianState(V=self.V.copy(), rbar=self.rbar.copy())

    def remove_mode(self, mode: int) -> GaussianState:
        """Return new state with specified physical mode removed.

        In xxpp, drops row/col *mode* and *nmode+mode* from V,
        and the same entries from rbar.
        """
        m = self.nmode
        if not 0 <= mode < m:
            raise IndexError(f"mode {mode} out of range for nmode={m}")
        keep = [i for i in range(2 * m) if i != mode and i != m + mode]
        return GaussianState(
            V=self.V[np.ix_(keep, keep)],
            rbar=self.rbar[keep],
        )

    def sample_quadratures(
        self, size: int = 1000, *, rng: np.random.Generator | None = None
    ) -> np.ndarray:
        """Batch (size, 2m) samples of the xxpp quadrature vector.

        iid draws from N(r̄, V) — the raw Gaussian shots of the whole
        state (vision §4.2 F-SAMPLE). One RNG call.
        """
        if rng is None:
            rng = np.random.default_rng()
        if not isinstance(size, (int, np.integer)) or isinstance(size, bool) or size < 1:
            raise ValueError(f"size must be a positive int, got {size!r}")
        return rng.multivariate_normal(self.rbar, self.V, size=size)
