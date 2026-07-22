"""Fock 1-mode projective Homodyne condition (truncated X eigenstate)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import (
    FockDensity,
    FockState,
    displace,
    homodyne_condition,
    homodyne_mean,
    homodyne_sample_and_condition,
)
from cvsim.fock.observables import _x_phi_matrix


def _matrix_x_mean_var(amps: np.ndarray, phi: float) -> tuple[float, float]:
    N = len(amps)
    Xh = 0.5 * (_x_phi_matrix(N, phi) + _x_phi_matrix(N, phi).conj().T)
    mu = float((amps.conj() @ Xh @ amps).real)
    x2 = float((amps.conj() @ (Xh @ Xh) @ amps).real)
    return mu, x2 - mu * mu


def test_condition_mean_near_outcome():
    N = 32
    m = 0.55
    post = homodyne_condition(FockState.vacuum(N), outcome=m)
    mu = homodyne_mean(post)
    # nearest truncated eigenvalue of x; spacing ~ O(1/√N)
    assert abs(mu - m) < 0.2
    mx, vx = _matrix_x_mean_var(post.amps, 0.0)
    assert abs(mx - mu) < 1e-12
    assert vx < 1e-12  # exact eigen of truncated X


def test_phi_and_prior_independence():
    N = 32
    m, phi = 0.4, 0.7
    p0 = homodyne_condition(FockState.vacuum(N), phi=phi, outcome=m)
    p1 = homodyne_condition(displace(FockState.vacuum(N), 0.6), phi=phi, outcome=m)
    assert abs(homodyne_mean(p0, phi=phi) - m) < 0.2
    assert abs(homodyne_mean(p1, phi=phi) - m) < 0.2
    assert abs(abs(np.vdot(p0.amps, p1.amps)) - 1.0) < 1e-12
    _, vx = _matrix_x_mean_var(p0.amps, phi)
    assert vx < 1e-12


def test_density_input_returns_pure():
    dens = FockDensity.from_pure(FockState.vacuum(24))
    post = homodyne_condition(dens, outcome=0.2)
    assert isinstance(post, FockState)
    assert abs(homodyne_mean(post) - 0.2) < 0.25
    _, vx = _matrix_x_mean_var(post.amps, 0.0)
    assert vx < 1e-12


def test_sample_and_condition():
    rng = np.random.default_rng(1)
    st = FockState.vacuum(24)
    o, post = homodyne_sample_and_condition(st, rng=rng)
    mu = homodyne_mean(post)
    # post snaps to nearest X eig of o; allow grid vs spectrum mismatch
    assert abs(mu - o) < 0.35
    _, vx = _matrix_x_mean_var(post.amps, 0.0)
    assert vx < 1e-12


def test_two_mode_raises():
    st = FockState.vacuum(4, nmode=2)
    with pytest.raises(ValueError):
        homodyne_condition(st, outcome=0.0)
