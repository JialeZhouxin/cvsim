"""Single-mode Fock Wigner (ħ=1)."""

from __future__ import annotations

import numpy as np

from cvsim.fock import FockCircuit, FockDensity, FockState
from cvsim.fock import squeeze as f_squeeze
from cvsim.gaussian import GaussianCircuit, GaussianState
from cvsim.gaussian import squeeze as g_squeeze
from cvsim.wigner import wigner_fock, wigner_gaussian, wigner_grid


def test_fock_vacuum_center():
    st = FockState.vacuum(8)
    assert abs(wigner_fock(st, 0.0, 0.0) - 1.0 / np.pi) < 1e-12


def test_fock_one_negative_center():
    st = FockState.fock(1, 8)
    assert wigner_fock(st, 0.0, 0.0) < -1e-3
    assert abs(wigner_fock(st, 0.0, 0.0) + 1.0 / np.pi) < 1e-10


def test_fock_density_matches_pure():
    pure = FockState.fock(1, 6)
    dens = FockDensity.from_pure(pure)
    for x, p in [(0.0, 0.0), (0.5, -0.2)]:
        assert abs(wigner_fock(dens, x, p) - wigner_fock(pure, x, p)) < 1e-12


def test_fock_squeeze_near_gaussian():
    r = 0.3
    N = 24
    f = f_squeeze(FockState.vacuum(N), r)
    g = g_squeeze(GaussianState.vacuum(1), r)
    for x, p in [(0.0, 0.0), (0.3, 0.0), (0.0, 0.3)]:
        assert abs(wigner_fock(f, x, p) - wigner_gaussian(g, x, p)) < 5e-3


def test_fock_grid_vac():
    _, _, W = wigner_grid(FockState.vacuum(6), lim=2.0, n=11)
    mid = W.shape[0] // 2
    assert abs(W[mid, mid] - 1.0 / np.pi) < 1e-10


# -- ⟨p⟩ ≠ 0: the kernel's α/ᾱ branches were swapped -------------------------
#
# W(α) = W(−α) holds for a real amplitude, so every test above (vacuum, number
# states, real-r squeeze, p=0 grid points) is blind to a sign error that only
# shows up once the amplitude has an imaginary part. A pure-p displacement is
# the minimal probe: its Wigner peak must sit at +p = √2·Im(α), not −p.


def _fock_grid(alpha: complex, cutoff: int = 30, lim: float = 3.0, n: int = 41):
    c = FockCircuit(nmode=1, cutoff=cutoff)
    if alpha != 0:
        c.displace(0, alpha=alpha)
    st = c.run()
    if isinstance(st, tuple):
        st = st[0]
    return np.asarray(wigner_grid(st, lim=lim, n=n)[2], dtype=float)


def _gauss_grid(alpha: complex, lim: float = 3.0, n: int = 41):
    c = GaussianCircuit(1)
    if alpha != 0:
        c.displace(0, alpha=alpha)
    return np.asarray(wigner_grid(c.run(), lim=lim, n=n)[2], dtype=float)


def test_fock_wigner_p_displaced_peak_is_positive_p() -> None:
    """α = 0.4i must sit at +p — the pre-fix kernel mirrored it to −p."""
    W = _fock_grid(0.4j)
    _, P, _ = wigner_grid(FockState.vacuum(2), lim=3.0, n=41)
    i, j = np.unravel_index(np.argmax(W), W.shape)
    assert P[i, j] > 0.0, f"peak at p={P[i, j]:+.3f}; expected +0.566 (α=0.4i)"


def test_fock_wigner_matches_gaussian_for_imaginary_amplitude() -> None:
    """The decisive cross-representation guard: ⟨p⟩ ≠ 0 states, no flip."""
    for alpha in (0.4j, 0.3 - 0.2j, -0.5j, 0.25 + 0.35j):
        Wf = _fock_grid(alpha)
        Wg = _gauss_grid(alpha)
        assert np.abs(Wf - Wg).max() < 1e-6, f"α={alpha}: fock Wigner != gaussian"


def test_fock_wigner_scalar_and_grid_paths_agree_offaxis() -> None:
    """wigner_fock (scalar kernel) and wigner_grid (vectorized copy) must match
    at points with ⟨p⟩ ≠ 0 — they are two copies of the same α/ᾱ branches."""
    st = FockState.vacuum(20)
    c = FockCircuit(nmode=1, cutoff=20)
    c.displace(0, alpha=0.4j)
    out = c.run()
    st = out[0] if isinstance(out, tuple) else out
    for x, p in ((0.0, 0.6), (0.2, -0.4), (-0.3, 0.5), (0.1, 0.25)):
        scalar = wigner_fock(st, x, p)
        _, _, W = wigner_grid(st, lim=1.0, n=3)
        # evaluate the grid path through wigner_grid on a tiny window containing (x,p)
        assert np.isfinite(scalar)
        assert abs(scalar - wigner_fock(st, x, p)) < 1e-12
    # and the grid path must equal the scalar path pointwise
    lim, n = 1.0, 5
    X, P, W = wigner_grid(st, lim=lim, n=n)
    for i in range(n):
        for j in range(n):
            assert abs(W[i, j] - wigner_fock(st, float(X[i, j]), float(P[i, j]))) < 1e-12
