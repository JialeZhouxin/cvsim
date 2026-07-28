"""Parameterized GaussianCircuit acceptance tests."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import GaussianCircuit, det_cov, mean_photon


def test_basic_parameter_scan():
    """Same circuit, different parameters produce different results."""
    c = GaussianCircuit(2)
    c.squeeze(0, r='r1')
    c.cz(0, 1, weight='g')

    n0 = mean_photon(c.run(r1=0.5, g=0.0))
    n1 = mean_photon(c.run(r1=0.5, g=0.5))
    assert n1 > n0  # CZ adds photons


def test_fixed_vs_param():
    """Fixed parameters are baked in; symbolic are resolved at run."""
    c = GaussianCircuit(1)
    c.squeeze(0, r='r1')
    c.phase(0, theta=0.5)  # fixed
    st = c.run(r1=0.3)
    # After phase rotation, V should have off-diagonal x-p correlation
    assert abs(st.V[0, 1]) > 1e-6


def test_loss_channel():
    """Loss makes state mixed (det V > (1/4)^nmode)."""
    c = GaussianCircuit(1)
    c.squeeze(0, r=0.5)
    c.loss(0, T='trans')
    st = c.run(trans=0.8)
    assert det_cov(st) > 0.25  # mixed


def test_missing_param_raises():
    """Missing symbolic parameter raises ValueError with param name."""
    c = GaussianCircuit(2)
    c.squeeze(0, r='r1')
    with pytest.raises(ValueError, match="r1"):
        c.run()


def test_chain_builder():
    """Builder methods return self for chaining."""
    c = GaussianCircuit(3)
    result = (
        c.squeeze(0, r=0.5)
        .cz(0, 1, weight=0.3)
        .beamsplitter(1, 2, theta=np.pi / 4)
        .cx(0, 2, weight='g')
        .loss(0, T=0.9)
    )
    assert result is c
    assert len(c) == 5


def test_repr_shows_fixed_and_param():
    """repr distinguishes fixed values from symbolic params."""
    c = GaussianCircuit(1)
    c.squeeze(0, r='r1')
    c.phase(0, theta=0.5)
    s = repr(c)
    assert '${r1}' in s
    assert 'theta=0.5' in s


def test_invalid_nmode():
    with pytest.raises(ValueError):
        GaussianCircuit(0)


def test_three_mode_cz():
    """CZ on modes 0,2 leaves mode 1 untouched."""
    c = GaussianCircuit(3)
    c.cz(0, 2, weight=0.5)
    st = c.run()
    n0 = mean_photon(st, mode=0)
    n1 = mean_photon(st, mode=1)
    n2 = mean_photon(st, mode=2)
    assert n0 > 0 and n2 > 0
    assert n1 == 0.0
