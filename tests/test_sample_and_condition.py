"""homodyne_sample_and_condition thin wrapper."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import BosonicState
from cvsim.bosonic import homodyne_sample_and_condition as b_sc
from cvsim.gaussian import GaussianState
from cvsim.gaussian import homodyne_sample_and_condition as g_sc
from cvsim.gaussian import homodyne_var, squeeze


def test_g_vac_sample_condition():
    o, st = g_sc(GaussianState.vacuum(1), rng=np.random.default_rng(0))
    assert abs(st.V[0, 0]) < 1e-12
    assert abs(st.rbar[0] - o) < 1e-12
    assert abs(homodyne_var(st, 0, 0.0)) < 1e-12


def test_b_matches_g_seed():
    g0 = squeeze(GaussianState.vacuum(1), 0.3)
    o_g, st_g = g_sc(g0, rng=np.random.default_rng(3))
    o_b, st_b = b_sc(BosonicState.from_gaussian(g0), rng=np.random.default_rng(3))
    assert abs(o_g - o_b) < 1e-12
    assert abs(st_b.components[0].rbar[0].real - st_g.rbar[0]) < 1e-10
