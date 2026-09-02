"""B7 Wigner kernel 数值稳定性 — log 域合并(红/绿)。

背景:``_K_re`` 对远距复中心对(如 GKP grid_size≥3 full-cross 交叉分量)会在
M2 积分项上算 ``exp(+754)`` 溢出(inf/0 型 nan)。物理上这些项的贡献是有限
小量(逐项有界定理:同一对 (i,j) 里 w_c = c_i·c_j·S_ij 的指数压制与 M2 的
指数放大精确抵消),但浮点中 w 与 M 两端各自出界,``w_i·w_j·inf = nan``。

log 域合并:指数全程在 log 域做,``log_w_i + log_w_j + log|M_kernel|`` 先在
log 域合成(如 -818 + 754 = -64),只在结果不小于 LOG_CUTOFF(≈-745,subnormal
下限之下)时才回线性域。数学值与旧实现完全一致(共享核,B4/B6/B7),只是避开
中间出界。
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import BosonicCircuit, gkp0, gkp1, pure_fidelity, purity
from cvsim.bosonic.cat import even_cat, odd_cat

pytestmark = pytest.mark.phaseB6


class TestKernelLogDomain:
    def test_purity_grid3_full_finite(self):
        """默认 grid_size=3, cross=full 2d 纯态:purity 有限且为 1(修正 nan)。"""
        z0 = gkp0(0.1, grid_size=3, lattice="2d", cross="full")
        z1 = gkp1(0.1, grid_size=3, lattice="2d", cross="full")
        assert z0.n_components == 49
        assert z1.n_components == 49
        assert abs(purity(z0) - 1.0) < 1e-9
        assert abs(purity(z1) - 1.0) < 1e-9

    def test_fidelity_z_basis_default_params(self):
        """AC-3(gkp.py 层等价物):grid_size=3 full 2d 0/1 正交,fidelity 有限。"""
        z0 = gkp0(0.1, grid_size=3, lattice="2d", cross="full")
        z1 = gkp1(0.1, grid_size=3, lattice="2d", cross="full")
        f = pure_fidelity(z0, z1)
        assert np.isfinite(f)
        assert f < 0.1

    def test_frontend_initial_z_basis_orthogonal(self):
        """前端默认路径:circuit initial=['gkp0_2d'] vs ['gkp1_2d'],fidelity 有限<0.1。"""
        c0 = BosonicCircuit(1, initial=["gkp0_2d"])
        c1 = BosonicCircuit(1, initial=["gkp1_2d"])
        f = pure_fidelity(c0._initial, c1._initial)
        assert np.isfinite(f)
        assert f < 0.1

    def test_regression_grid1_eps015(self):
        """N=1,eps=0.15 回归锚多(旧实现逐位)."""
        z0 = gkp0(0.15, grid_size=1, lattice="2d", cross="full")
        z1 = gkp1(0.15, grid_size=1, lattice="2d", cross="full")
        assert purity(z0) == pytest.approx(0.9999999999999999, rel=1e-14)
        assert purity(z1) == pytest.approx(0.9999999999999992, rel=1e-14)
        assert pure_fidelity(z0, z1) == pytest.approx(0.01221048428995681, rel=1e-8)

    def test_regression_grid2_eps01(self):
        """N=2,eps=0.1 回归锚多(旧实现逐位)."""
        z0 = gkp0(0.1, grid_size=2, lattice="2d", cross="full")
        z1 = gkp1(0.1, grid_size=2, lattice="2d", cross="full")
        assert purity(z0) == pytest.approx(1.0000000000000016, rel=1e-14)
        assert purity(z1) == pytest.approx(1.0, rel=1e-14)
        assert pure_fidelity(z0, z1) == pytest.approx(0.001280194916685476, rel=1e-8)

    def test_regression_cat_purity(self):
        """cat 纯态 purity=1(复权重,cat 交叉分量)."""
        assert purity(even_cat(0.5)) == pytest.approx(1.0, rel=1e-12)
        assert purity(odd_cat(0.5)) == pytest.approx(1.0, rel=1e-12)

    def test_1d_cross_none_unchanged(self):
        """1d default cross=none = 对角混合态,purity 不变(非 1)."""
        assert purity(gkp0()) == pytest.approx(0.22558040617805283, rel=1e-12)

    def test_nan_pairs_are_zero_contribution(self):
        """直接暴露耦合:任意分量对的单项贡献必须有限(不产生 nan;grid_size=3)."""
        z0 = gkp0(0.1, grid_size=3, lattice="2d", cross="full")
        comps = z0.components
        acc = 0.0
        for ci in comps:
            for cj in comps:
                k = _K_pair(ci, cj)
                assert np.isfinite(k.real) and np.isfinite(k.imag), (ci.rbar, cj.rbar)
                acc += k.real
        assert np.isfinite(acc)


from cvsim.bosonic.analyse import _K_pair  # noqa: E402  (探针导入,仅供单项有限性检查)
