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
