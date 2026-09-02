"""GKP 2D logical Z basis (Q5b): alternating phase (−1)^k.

Per docs/gkp-2d-square-lattice.md §2/§3: single-mode square-lattice GKP has two
complementary logical bases. lattice="2d" is the Z basis: |1⟩ = Σ (−1)^k c_k |kΔ⟩
(peaks same as |0⟩, alternating phase). Orthogonality of |0⟩_Z and |1⟩_Z follows
from the alternating cross-component sign — it only appears with cross="full"
(the coherent Gram state); cross="none" is the diagonal-only mixt state where
gkp0/gkp1 peaks coincide.

Logic-fidelity entry point is pure_fidelity (B7 complex-centre kernel); the
deprecated gkp_logical_overlap uses diagonal √w and drops the sign, so it cannot
distinguish the Z basis.
"""

from __future__ import annotations

import pytest

from cvsim.bosonic import gkp0, gkp1, pure_fidelity, weight_sum


def test_2d_logical_z_self_and_orthogonal_full():
    eps, N = 0.15, 1
    z0 = gkp0(eps, grid_size=N, lattice="2d", cross="full")
    z1 = gkp1(eps, grid_size=N, lattice="2d", cross="full")
    assert abs(weight_sum(z0) - 1.0) < 1e-12
    assert abs(weight_sum(z1) - 1.0) < 1e-12
    assert abs(pure_fidelity(z0, z0) - 1.0) < 1e-5  # pure (self)
    assert abs(pure_fidelity(z1, z1) - 1.0) < 1e-5  # pure (self)
    assert abs(pure_fidelity(z0, z1)) < 0.1         # Z-basis orthogonal (finite ε)

def test_2d_full_count_is_single_mode_square():
    eps, N = 0.15, 1
    M = 2 * N + 1
    z0 = gkp0(eps, grid_size=N, lattice="2d", cross="full")
    # M diagonal + 2·C(M,2) = M(M−1) cross components (2 per pair) = M²
    assert z0.n_components == M * M
    assert abs(weight_sum(z0) - 1.0) < 1e-12

def test_gkp1_2d_alternating_cross_sign_direct():
    """Direct pin of the (−1)^k coefficient (AC-3, not inferred via fidelity).

    With cross="full" the alternating phase lives ONLY in the cross-component
    sign: gkp1's cross weights are the exact negation of gkp0's at identical
    centres (diagonal weights agree; Z-normalization rounding differs slightly).
    """
    eps, N = 0.15, 1
    z0 = gkp0(eps, grid_size=N, lattice="2d", cross="full")
    z1 = gkp1(eps, grid_size=N, lattice="2d", cross="full")

    def cross_key(c):
        return (round(float(c.rbar[0].real), 8), round(float(c.rbar[1].imag), 8))

    m0 = {cross_key(c): c for c in z0.components if abs(c.rbar[1].imag) > 1e-14}
    m1 = {cross_key(c): c for c in z1.components if abs(c.rbar[1].imag) > 1e-14}
    assert set(m0) == set(m1)  # same cross centres; sign lives in w, not position
    flipped = 0
    for key, c0 in m0.items():
        c1 = m1[key]
        if abs(c0.w) < 1e-12:  # far pair (k=-1, k=+1): S underflows in both
            assert abs(c1.w) < 1e-12
            continue
        flipped += 1
        assert c1.w == pytest.approx(-c0.w, rel=1e-3)  # (−1)^k flip
    assert flipped >= 4  # every non-vanishing pair flipped
