"""GKP |0⟩ nearest-neighbour cross construction."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import gkp0, phase, squeeze, weight_sum
from cvsim.wigner import wigner_grid


def test_nn_count_and_weight_sum():
    st = gkp0(0.2, grid_size=2, cross="nn")
    # K = 6N+1 = 13
    assert st.n_components == 13
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_nn_cross_centres():
    eps, N = 0.2, 2
    st = gkp0(eps, grid_size=N, cross="nn")
    delta = np.sqrt(2.0 * np.pi)
    # cross components: Im p ≠ 0
    cross = [c for c in st.components if abs(c.rbar[1].imag) > 1e-14]
    assert len(cross) == 2 * (2 * N)  # 8
    midpoints = {0.5 * (k + k + 1) * delta for k in range(-N, N)}
    for c in cross:
        assert abs(c.rbar[0].real) in midpoints or any(
            abs(c.rbar[0].real - m) < 1e-12 for m in midpoints
        )
        assert abs(c.rbar[1].imag) > 1e-12


def test_nn_wigner_differs_from_none():
    eps, N = 0.35, 2
    none = gkp0(eps, grid_size=N, cross="none")
    nn = gkp0(eps, grid_size=N, cross="nn")
    _, _, W0 = wigner_grid(none, lim=6.0, n=31)
    _, _, W1 = wigner_grid(nn, lim=6.0, n=31)
    assert float(np.max(np.abs(W1 - W0))) > 1e-4


def test_nn_gates_keep_weights():
    st = gkp0(0.25, grid_size=1, cross="nn")
    w0 = [c.w for c in st.components]
    st2 = squeeze(phase(st, 0.2), 0.15)
    assert all(abs(a - b) < 1e-15 for a, b in zip(w0, [c.w for c in st2.components], strict=False))


def test_cross_bad_arg():
    with pytest.raises(ValueError):
        gkp0(cross="pair")  # type: ignore[arg-type]
