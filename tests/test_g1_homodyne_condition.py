"""G1 conditional Homodyne."""

from __future__ import annotations

from cvsim.gaussian import (
    GaussianState,
    displace,
    homodyne_condition,
    homodyne_mean,
    homodyne_var,
    two_mode_squeeze,
)


def test_vac_condition_phi0():
    st = GaussianState.vacuum(1)
    out = 0.3
    st2 = homodyne_condition(st, 0, 0.0, out)
    assert abs(st2.V[0, 0]) < 1e-12
    assert abs(st2.V[1, 1] - 0.5) < 1e-12
    assert abs(st2.rbar[0] - out) < 1e-12


def test_displace_pins_mean():
    alpha = 0.6 + 0.1j
    st = displace(GaussianState.vacuum(1), alpha)
    phi = 0.4
    outcome = 1.2
    st2 = homodyne_condition(st, 0, phi, outcome)
    assert abs(homodyne_mean(st2, 0, phi) - outcome) < 1e-10
    assert abs(homodyne_var(st2, 0, phi)) < 1e-10


def test_tms_steering():
    r = 0.7
    st = two_mode_squeeze(GaussianState.vacuum(2), r, 0, 1)
    var1_before = homodyne_var(st, 1, 0.0)
    st2 = homodyne_condition(st, 0, 0.0, 0.0)
    var1_after = homodyne_var(st2, 1, 0.0)
    # EPR: measuring x0 shrinks x1 variance
    assert var1_after < var1_before - 1e-6


def test_var_matches_edge_api():
    st = displace(GaussianState.vacuum(1), 0.2)
    assert abs(homodyne_var(st, 0, 0.3) - (0.5)) < 1e-12
