"""B1 Bosonic component-wise gates."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import displace, even_cat, phase, weight_sum
from cvsim.bosonic.state import BosonicState, Component
from cvsim.conventions import vacuum_cov


def test_cat_phase_keeps_weight_sum_and_rotates():
    st = even_cat(0.8)
    theta = 0.5
    st2 = phase(st, theta)
    assert abs(weight_sum(st2) - 1.0) < 1e-12
    # diagonal peaks (±rx, 0) rotate in (x,p)
    r0 = st.components[0].rbar
    r0p = st2.components[0].rbar
    c, s = np.cos(theta), np.sin(theta)
    expect = np.array([c * r0[0] - s * r0[1], s * r0[0] + c * r0[1]])
    assert np.allclose(r0p, expect, atol=1e-12)


def test_displace_single_component_weights():
    vac = BosonicState(
        components=[Component(V=vacuum_cov(1), rbar=np.zeros(2, dtype=complex), w=1.0)]
    )
    st = displace(vac, 0.3 + 0.2j)
    assert abs(weight_sum(st) - 1.0) < 1e-12
    rx = np.sqrt(2) * 0.3
    rp = np.sqrt(2) * 0.2
    assert abs(st.components[0].rbar[0] - rx) < 1e-12
    assert abs(st.components[0].rbar[1] - rp) < 1e-12
