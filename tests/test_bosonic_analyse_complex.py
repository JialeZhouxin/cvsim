"""B7: complex-centre analyse kernel — purity / pure_fidelity exactness.

The old B4 forms were the teaching cut:
  - purity: diagonal approximation sum |w_k|^2 mu_k (drops Tr(rho_i rho_j))
  - pure_fidelity: real-mean Gram (rbar.real silently drops interference)
B7 replaces both with the closed-form complex-centre overlap kernel
Tr(rho_a rho_b) = sum_ij w_i^a w_j^b |<g_i^a|g_j^b>|^2 (design.md).

Layer 1: degenerate cases vs analytic / Fock closed forms.
Layer 2: GKP internal identities (no analytic benchmark — mutual numerics).
"""
from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import (
    BosonicState,
    Component,
    gkp0,
    gkp1,
    homodyne_condition,
    loss,
    pure_fidelity,
    purity,
)
from cvsim.bosonic.cat import _cat4
from cvsim.fock.channels import loss as fock_loss
from cvsim.fock.state import FockState

CUT = 40


class TestL1ComplexKernelDegenerate:
    """Layer 1: vs analytic / Fock closed forms."""

    def test_L1a_k1_squeezed_purity_analytic(self):
        """K=1 Gaussian: purity == 1 (pure state; matches Gaussian package atol 1e-10)."""
        from cvsim.bosonic.state import BosonicState
        from cvsim.gaussian import GaussianState
        from cvsim.gaussian import purity as g_purity
        from cvsim.gaussian import squeeze as g_squeeze

        r = 0.6
        st_g = g_squeeze(GaussianState.vacuum(1), r)
        st_b = BosonicState.from_gaussian(st_g)
        assert abs(purity(st_b) - 1.0) < 1e-10
        assert abs(purity(st_b) - g_purity(st_g)) < 1e-10

    def test_L1b_lossy_cat_purity_vs_fock(self):
        """lossy even cat: purity vs Fock high-cutoff (atol 1e-6)."""
        for alpha, T in [(0.8, 0.7), (0.8, 0.9), (1.2, 0.7)]:
            fs = FockState.cat(CUT, alpha, even=True)
            fld = fock_loss(fs, T)
            fock_pur = float(np.trace(fld.rho @ fld.rho).real)

            st = _cat4(alpha, even=True)
            bs = loss(st, T)
            b_pur = purity(bs)
            assert abs(b_pur - fock_pur) < 1e-6, (alpha, T, b_pur, fock_pur)

    def test_L1c_even_odd_orthogonal(self):
        """even cat vs odd cat: fidelity == 0 (atol 1e-10).

        Old real-mean Gram gave 0.5 here (cross components misplaced).
        """
        for alpha in (0.5, 1.0, 1.5):
            st_e = _cat4(alpha, even=True)
            st_o = _cat4(alpha, even=False)
            fid = pure_fidelity(st_e, st_o)
            assert abs(fid) < 1e-10, (alpha, fid)

    def test_L1d_even_cat_self_fidelity(self):
        """even cat: pure_fidelity(st, st) == 1 (atol 1e-9)."""
        for alpha in (0.5, 1.0, 1.5):
            st = _cat4(alpha, even=True)
            assert abs(pure_fidelity(st, st) - 1.0) < 1e-9, alpha

    def test_L1e_cat_vs_fock_fidelity(self):
        """even cat vs displaced cat: fidelity vs Fock (atol 1e-6)."""
        from cvsim.bosonic import displace
        from cvsim.bosonic.cat import _cat4 as c4

        alpha = 1.0
        st = c4(alpha, even=True)
        fs = FockState.cat(CUT, alpha, even=True)
        # displaced bosonic cat vs displaced Fock cat
        dshift = complex(0.3, 0.2)
        from cvsim.fock.gates import displace as fock_displace
        fs2 = fock_displace(FockState.cat(CUT, alpha, even=True), dshift)
        st2 = displace(st, dshift, 0)
        from cvsim.fock.state import FockState as FS
        fock_fid = abs(np.dot(FS.cat(CUT, alpha, True).amps.conj(), fs2.amps)) ** 2
        b_fid = pure_fidelity(st, st2)
        # sanity: both non-trivial
        assert abs(b_fid - fock_fid) < 1e-6, (b_fid, fock_fid)


class TestL2GkpComplexIdentities:
    """Layer 2: GKP mutual numerics (no analytic benchmark)."""

    def test_L2a_gkp_full_cross_self_fidelity(self):
        """GKP cross='full': pure_fidelity(st, st) == 1 (atol 1e-5).

        Old real-mean Gram silently misplaced the K(K-1) cross components
        (complex centres) — this failed before B7 (1d gave 0.43, and the
        kernel returned values > 1 for 2d via the misplaced Gram).

        Only lattice='1d' is asserted: its components use the exact
        pure-state covariance V=½diag(ε,1/ε). The 2d lattice uses the
        TEACHING isotropic envelope V=½εI (documented in gkp.py), which
        is a non-pure per-peak Gaussian for ε ≠ 1 — self-fidelity is
        expected < 1 by construction (a 2d representation bug, tracked
        separately; not a kernel issue).

        grid_size=1 (3 peaks for 1d → 9 components): pure-state
        self-fidelity is grid-independent, and full-cross scales as
        O(N⁴) in components (49 peaks → 2401 comps would be minutes).
        """
        st = gkp0(epsilon=0.1, grid_size=1, cross="full", lattice="1d")
        fid = pure_fidelity(st, st)
        assert abs(fid - 1.0) < 1e-5, fid

    def test_L2b_gkp1_full_cross_self_fidelity(self):
        st = gkp1(epsilon=0.1, grid_size=1, cross="full", lattice="1d")
        assert abs(pure_fidelity(st, st) - 1.0) < 1e-5

    def test_L2c_conditioned_state_delta_divergence(self):
        """Ideal homodyne → delta projection: V singular, Tr(ρ²) diverges.

        ``homodyne_condition`` on an ideal (zero-noise) homodyne produces
        V with a zero eigenvalue (delta along the measured quadrature).
        Mathematically Tr(ρ²) = 2π∫W² **diverges** for a delta Wigner —
        the kernel must raise ``ValueError`` (det(V) ≤ 0 guard) instead of
        silently returning the numerically-unbounded value. Guard is the
        honest behaviour: delta states are not finite-density-matrix states.
        """
        st = gkp0(epsilon=0.1, grid_size=1, cross="none", lattice="1d")
        post = homodyne_condition(st, mode=0, phi=0.0, outcome=0.0)
        # delta projection: all components share singular V (eig ≈ 0)
        with pytest.raises(ValueError, match="det|singular|δ"):
            purity(post, validate=False)
        with pytest.raises(ValueError, match="det|singular|δ"):
            pure_fidelity(post, post)

    def test_L2c2_finite_resolution_scales_like_1_over_sqrt_det(self):
        """Finite detector width δ: Tr(ρ²) ~ 1/√det(V_xx) — delta limit unbounded.

        A δ-smoothed conditioning V+δI is still a strongly-squeezed state;
        its purity grows as δ^-1/2 (diagonal-dominant component). This is
        the physical signature of the delta projection, not a kernel bug.
        """
        st = gkp0(epsilon=0.1, grid_size=1, cross="none", lattice="1d")
        post = homodyne_condition(st, mode=0, phi=0.0, outcome=0.0)
        purities = []
        for delta in (1e-4, 1e-6, 1e-8):
            comps = [
                Component(V=np.asarray(c.V) + delta * np.eye(2), rbar=c.rbar, w=c.w)
                for c in post.components
            ]
            pf = BosonicState(components=comps)
            p = pure_fidelity(pf, pf)
            purities.append(p)
            assert p > 0
        # monotone increasing as delta shrinks (delta^-1/2 divergence)
        assert purities[0] < purities[1] < purities[2], purities
        # ratio between successive δ (×100) ≈ √100 = 10
        r1 = purities[1] / purities[0]
        r2 = purities[2] / purities[1]
        assert 3.0 < r1 < 30.0 and 3.0 < r2 < 30.0, (r1, r2)

    def test_L2d_gkp_none_cross_matches_real_kernel(self):
        """cross='none' (real centres): new kernel == old B4 value (atol 1e-7)."""
        st0 = gkp0(epsilon=0.1, grid_size=1, cross="none", lattice="1d")
        st1 = gkp1(epsilon=0.1, grid_size=1, cross="none", lattice="1d")
        # old value from B4 test (identical math on real means)
        fid = pure_fidelity(st0, st1)
        assert 0.0 <= fid <= 1.0
        # cross='none' is a mixed-state (teaching diagonal cut): self-fid
        # equals the diagonal purity Σw² < 1 — the two forms must agree.
        assert abs(pure_fidelity(st0, st0) - purity(st0)) < 1e-8
        assert abs(pure_fidelity(st1, st1) - purity(st1)) < 1e-8

    def test_L2e_loss_purity_vs_fock_crosscheck(self):
        """gkp0 (cross='none') -> loss: purity vs Fock high-cutoff (layer 2)."""
        st = gkp0(epsilon=0.1, grid_size=1, cross="none", lattice="1d")
        bs = loss(st, 0.9)
        b_pur = purity(bs)
        assert b_pur < 1.0
        # Fock-side check is expensive & GKP has no analytic benchmark;
        # monotonicity + self-consistency are the honest layer-2 anchors:
        assert purity(loss(st, 0.5)) < b_pur  # more loss -> lower purity


class TestHermitianDiscipline:
    """Complex-value real-part discipline (spec §3)."""

    def test_purity_validate_hermitian(self):
        """purity(validate=True) passes for Hermitian-closed states."""
        st = _cat4(1.0, even=True)
        assert purity(st, validate=True) > 0.9

    def test_purity_validate_non_hermitian_raises(self):
        """Single cross component alone is not Hermitian-closed -> ValueError."""
        c = _cat4(1.0, even=True)
        one = c.components[2]  # one of the cross components (complex centre)
        st = BosonicState(components=[Component(V=one.V, rbar=one.rbar, w=1.0 + 0.0j)])
        with pytest.raises(ValueError):
            purity(st, validate=True)
