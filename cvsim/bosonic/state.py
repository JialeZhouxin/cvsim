"""Bosonic state: list of Gaussian components (V, r̄, w)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvsim.conventions import vacuum_cov, vacuum_mean


def weight_sum(state: BosonicState) -> complex:
    """∑ w_k — should be 1 for a normalized density-operator decomposition."""
    return sum(c.w for c in state.components)


def tensor_product(states: list[BosonicState]) -> BosonicState:
    """Tensor product of 1-mode Bosonic states → multi-mode state (B6).

    Component-wise Cartesian product: ``K = Π K_k``, ``V = blockdiag``,
    ``r̄ = concat``, ``w = Π w_k``. Used by ``BosonicCircuit(initial=...)``
    to assemble per-mode state sources (gkp0 ⊗ gkp1, …).
    """
    states = [s for s in states if s is not None]
    if not states:
        raise ValueError("tensor_product: need at least one state")
    from itertools import product

    mode_counts = [s.nmode for s in states]
    total_modes = sum(mode_counts)
    out: list[Component] = []
    for combo in product(*(s.components for s in states)):
        V = np.zeros((2 * total_modes, 2 * total_modes), dtype=float)
        rbar = np.zeros(2 * total_modes, dtype=complex)
        mode_offset = 0
        for c, nmode in zip(combo, mode_counts, strict=True):
            # Each input component is xxpp locally; place its x block and p
            # block at global xxpp indices instead of concatenating x,p pairs.
            idx = list(range(mode_offset, mode_offset + nmode))
            idx += list(range(total_modes + mode_offset, total_modes + mode_offset + nmode))
            V[np.ix_(idx, idx)] = c.V
            rbar[idx] = c.rbar
            mode_offset += nmode
        w = 1.0 + 0.0j
        for c in combo:
            w = w * c.w
        out.append(Component(V=V, rbar=rbar, w=w))
    return BosonicState(components=out)


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
        # 0-mode state = empty component list (heterodyne K=1 condition tail);
        # gates still refuse empty states via gates._nmode.
        if not self.components:
            return 0
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
    def from_gaussian(cls, state) -> BosonicState:
        """Wrap object with .V and .rbar as one component w=1 (duck type)."""
        return cls(
            components=[
                Component(
                    V=np.asarray(state.V, dtype=float).copy(),
                    rbar=np.asarray(state.rbar, dtype=complex).copy(),
                    w=1.0 + 0.0j,
                )
            ]
        )

    def remove_mode(self, mode: int) -> BosonicState:
        """Remove a mode from every component (partial trace, weights unchanged).

        Per component: delete the x and p rows/cols for *mode*, then repack
        the remaining (x_0..x_{m-1}, p_0..p_{m-1}) into xxpp order. Used by
        circuit ``measure_homodyne`` (B3 ``homodyne_condition`` does not drop
        the mode). A 0-mode state (all modes measured) is returned as an empty
        component list.
        """
        if not self.components:
            return BosonicState(components=[])
        m = self.nmode
        if not 0 <= mode < m:
            raise IndexError(f"mode {mode} out of range for nmode={m}")
        idx_A = [mode, m + mode]
        idx_B = [i for i in range(2 * m) if i not in idx_A]
        keep = sorted(i for i in range(m) if i != mode)
        pack = list(keep) + [m + k for k in keep]
        pos = {ax: j for j, ax in enumerate(idx_B)}
        perm = [pos[ax] for ax in pack]
        out: list[Component] = []
        for c in self.components:
            if not idx_B:
                continue
            Vn = c.V[np.ix_(idx_B, idx_B)][np.ix_(perm, perm)]
            rn = c.rbar[idx_B][perm]
            out.append(Component(V=Vn, rbar=rn, w=c.w))
        return BosonicState(components=out)


def coherent(alpha: complex, nmode: int = 1, mode: int = 0) -> BosonicState:
    """Coherent state |α⟩: single vacuum component displaced to r̄=√2(Re α, Im α).

    Direct construction (no gate overhead) — equivalent to
    ``displace(BosonicState.vacuum(nmode), alpha, mode)``.
    """
    if nmode < 1:
        raise ValueError("nmode must be >= 1")
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    rbar = np.zeros(2 * nmode, dtype=complex)
    a = complex(alpha)
    rbar[mode] = np.sqrt(2.0) * a.real
    rbar[nmode + mode] = np.sqrt(2.0) * a.imag
    return BosonicState(
        components=[Component(V=vacuum_cov(nmode), rbar=rbar, w=1.0 + 0.0j)]
    )
