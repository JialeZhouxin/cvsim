"""M3: even/odd cat 4 components + ∑w = 1."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import even_cat, odd_cat, weight_sum


def _check_structure(st, even: bool):
    assert st.n_components == 4
    c0, c1, c2, c3 = st.components
    assert abs(c0.rbar[0] + c1.rbar[0]) < 1e-12
    assert abs(c0.rbar[1]) < 1e-12 and abs(c1.rbar[1]) < 1e-12
    assert abs(c2.rbar[0]) < 1e-12 and abs(c2.rbar[1].imag) > 0
    assert abs(c3.rbar[0]) < 1e-12 and abs(c3.rbar[1].imag) > 0
    assert c0.w.real > 0 and abs(c0.w.imag) < 1e-12
    assert abs(c0.w - c1.w) < 1e-12
    if even:
        assert c2.w.real > 0
    else:
        assert c2.w.real < 0
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_even_cat_weights():
    _check_structure(even_cat(0.8), even=True)


def test_odd_cat_weights():
    _check_structure(odd_cat(0.8), even=False)


def test_cross_weight_has_overlap_factor():
    alpha = 0.8
    ov = np.exp(-2 * alpha**2)
    st = even_cat(alpha)
    w_diag = st.components[0].w.real
    w_cross = st.components[2].w.real
    assert abs(w_cross / w_diag - ov) < 1e-12
