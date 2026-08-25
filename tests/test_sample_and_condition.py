"""homodyne_sample_and_condition thin wrapper."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import BosonicState
from cvsim.bosonic import homodyne_sample_and_condition as b_sc
from cvsim.gaussian import GaussianState, homodyne_var, squeeze
from cvsim.gaussian import homodyne_sample_and_condition as g_sc


def test_g_vac_sample_condition():
    o, st = g_sc(GaussianState.vacuum(1), rng=np.random.default_rng(0))
    assert abs(st.V[0, 0]) < 1e-12
    assert abs(st.rbar[0] - o) < 1e-12
    assert abs(homodyne_var(st, 0, 0.0)) < 1e-12


def test_b_matches_g_seed():
    """B3: bosonic sample+condition uses CDF inversion (not the Gaussian's direct
    normal), so same-seed value equality no longer holds. Verify instead that
    the posterior after conditioning on a sample is self-consistent: the
    posterior mean tracks the outcome, and K=1 reduces to the Gaussian
    condition formula."""
    g0 = squeeze(GaussianState.vacuum(1), 0.3)
    o_g, st_g = g_sc(g0, rng=np.random.default_rng(3))
    o_b_arr, st_b = b_sc(BosonicState.from_gaussian(g0), rng=np.random.default_rng(3), shots=1)
    o_b = float(o_b_arr[0])
    # posterior r̄[0] ≈ outcome (homodyne pins x at the measured value)
    assert abs(st_b.components[0].rbar[0].real - o_b) < 1e-9
    # K=1 Gaussian condition formula matches for the same outcome
    from cvsim.gaussian.observables import homodyne_condition as g_cond

    st_g_same = g_cond(g0, 0, 0.0, o_b)
    assert abs(st_b.components[0].rbar[0].real - st_g_same.rbar[0]) < 1e-10
