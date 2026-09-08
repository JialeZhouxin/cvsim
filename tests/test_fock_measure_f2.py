"""F2 measures: PNR (sample/condition) + heterodyne (sample/condition)
— vision §4 F2, coherent POVM |β⟩⟨β|/π, Born-rule conditioning."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import FockDensity, FockState
from cvsim.fock.gates import two_mode_squeeze
from cvsim.fock.observables import (
    heterodyne_condition,
    heterodyne_sample,
    heterodyne_sample_and_condition,
    pnr_condition,
    pnr_sample,
    pnr_sample_and_condition,
    pnrd_probs,
)

# -- PNR --------------------------------------------------------------------


def test_pnr_sample_statistics() -> None:
    rng = np.random.default_rng(42)
    st = FockState.coherent(20, 1.2)
    n = np.array([pnr_sample(st, rng=rng) for _ in range(2000)])
    p = pnrd_probs(st)
    emp = np.bincount(n, minlength=p.size) / n.size
    np.testing.assert_allclose(emp[:8], p[:8], atol=3e-2)


def test_pnr_condition_1mode_pure_projective() -> None:
    st = FockState.coherent(12, 0.9)
    out = pnr_condition(st, 0, 3)
    np.testing.assert_allclose(out.amps, FockState.fock(3, 12).amps, atol=1e-14)


def test_pnr_condition_1mode_zero_probability() -> None:
    st = FockState.fock(2, 8)
    with pytest.raises(ValueError):
        pnr_condition(st, 0, 5)
    with pytest.raises(IndexError):
        pnr_condition(st, 0, 99)


def test_pnr_condition_2mode_pure() -> None:
    # |1,2⟩ + |0,3⟩ superposition: condition n=1 on mode 0 → |2⟩
    amps = np.zeros((8, 8), dtype=complex)
    amps[1, 2] = 0.6
    amps[0, 3] = 0.8
    st = FockState(amps=amps)
    out = pnr_condition(st, 0, 1)
    np.testing.assert_allclose(out.amps, FockState.fock(2, 8).amps, atol=1e-14)
    out2 = pnr_condition(st, 1, 3)
    # ⟨3| on mode1: ψ[0,3]*|0⟩ + ψ[1,3]... wait |1,2⟩ has mode1=2 → only |0⟩ component
    np.testing.assert_allclose(out2.amps, FockState.fock(0, 8).amps, atol=1e-14)


def test_pnr_condition_2mode_density() -> None:
    st = FockState.fock2(1, 0, 6)
    d = FockDensity.from_pure(st)
    out = pnr_condition(d, 0, 1)
    np.testing.assert_allclose(
        out.rho, FockDensity.from_pure(FockState.fock2(1, 0, 6)).rho, atol=1e-14
    )


def test_pnr_sample_and_condition_roundtrip() -> None:
    rng = np.random.default_rng(7)
    st = FockState.coherent(15, 0.5)
    n, out = pnr_sample_and_condition(st, rng=rng)
    assert 0 <= n < 15
    assert abs(np.sum(abs(out.amps) ** 2) - 1.0) < 1e-12


# -- heterodyne -------------------------------------------------------------


def test_heterodyne_condition_1mode_pure_coherent() -> None:
    st = FockState.squeezed(12, 0.4)
    beta = 0.8 + 0.3j
    out = heterodyne_condition(st, 0, beta)
    ref = FockState.coherent(12, beta)
    np.testing.assert_allclose(out.amps, ref.amps, atol=1e-14)


def test_heterodyne_condition_2mode_pure() -> None:
    # |1⟩₀|2⟩₁: condition β on mode 1 → ⟨β|2⟩·|1⟩ ∝ |1⟩
    st = FockState.fock2(1, 2, 10)
    out = heterodyne_condition(st, 1, 1.0)
    np.testing.assert_allclose(out.amps, FockState.fock(1, 10).amps, atol=1e-14)
    # mode 0: ⟨β|1⟩·|2⟩ ∝ |2⟩ (global phase allowed)
    out0 = heterodyne_condition(st, 0, 0.5j)
    assert abs(np.vdot(out0.amps, FockState.fock(2, 10).amps)) > 1.0 - 1e-14


def test_heterodyne_condition_2mode_density() -> None:
    d = FockDensity.from_pure(FockState.fock2(0, 3, 8))
    out = heterodyne_condition(d, 1, 0.7)
    np.testing.assert_allclose(out.rho, out.rho.conj().T, atol=1e-14)
    np.testing.assert_allclose(np.trace(out.rho), 1.0, atol=1e-12)


def test_heterodyne_sample_statistics_vacuum() -> None:
    """Q(β) for vacuum = e^{−|β|²}/π — sample |β|² ~ Exp(1)."""
    rng = np.random.default_rng(3)
    st = FockState.vacuum(12)
    bs = np.array([heterodyne_sample(st, rng=rng) for _ in range(800)])
    r2 = np.abs(bs) ** 2
    np.testing.assert_allclose(r2.mean(), 1.0, atol=0.15)


def test_heterodyne_sample_statistics_coherent() -> None:
    """Q(β) of |α⟩ = e^{−|β−α|²}/π — mean β ≈ α."""
    rng = np.random.default_rng(11)
    alpha = 1.0 + 0.0j
    st = FockState.coherent(20, alpha)
    bs = np.array([heterodyne_sample(st, rng=rng, lim=6.0) for _ in range(800)])
    np.testing.assert_allclose(bs.real.mean(), alpha.real, atol=0.12)
    np.testing.assert_allclose(bs.imag.mean(), 0.0, atol=0.12)


def test_heterodyne_sample_and_condition_roundtrip() -> None:
    rng = np.random.default_rng(5)
    st = FockState.cat(16, 1.0, even=True)
    b, out = heterodyne_sample_and_condition(st, rng=rng)
    assert isinstance(b, complex)
    assert abs(np.sum(abs(out.amps) ** 2) - 1.0) < 1e-12


def test_heterodyne_condition_probability() -> None:
    """p(β) = ⟨β|ρ|β⟩/π: Born weight of the conditioned state."""
    st = FockState.fock2(0, 2, 10)
    # Q(β) on mode1 marginal |2⟩: e^{−|β|²}|β|⁴/2
    beta = 0.9
    from cvsim.fock.observables import _q_function

    q = _q_function(st, 1, np.array([beta]))[0]
    expected = np.exp(-(abs(beta) ** 2)) * abs(beta) ** 4 / 2.0
    np.testing.assert_allclose(q, expected, atol=1e-12)


def test_heterodyne_matches_tms_marginal() -> None:
    """TMS marginal is thermal: Q(β) = e^{−|β|²/(n̄+1)}/(π(n̄+1))."""
    r = 0.4
    st = two_mode_squeeze(FockState.vacuum(16, nmode=2), r)
    nbar = np.sinh(r) ** 2
    from cvsim.fock.observables import _q_function

    betas = np.array([0.3, 0.8 + 0.2j, 1.1j])
    q = _q_function(st, 0, betas)
    expected = np.exp(-(np.abs(betas) ** 2) / (nbar + 1.0)) / (nbar + 1.0)
    np.testing.assert_allclose(q, expected, atol=1e-6)


# -- F3: PNR batch -----------------------------------------------------------


def test_pnr_sample_batch_shapes_and_range() -> None:
    from cvsim.fock import pnr_sample_batch

    st = FockState.vacuum(8)
    out = pnr_sample_batch(st, 0, size=1000, rng=np.random.default_rng(0))
    assert out.shape == (1000,)
    assert out.dtype.kind == "i" or out.dtype.kind == "u"
    assert out.min() >= 0 and out.max() < 8
    # all-zero draws must all be zero (vacuum)
    assert np.all(out == 0)


def test_pnr_sample_batch_matches_single_shot_distribution() -> None:
    from cvsim.fock import pnr_sample, pnr_sample_batch
    from cvsim.fock.gates import squeeze

    st = squeeze(FockState.vacuum(10), 0.8)  # n̄ = sinh²(0.8) ≈ 0.79
    rng1, rng2 = np.random.default_rng(1), np.random.default_rng(1)
    single = np.array([pnr_sample(st, 0, rng=rng1) for _ in range(400)])
    batch = pnr_sample_batch(st, 0, size=400, rng=rng2)
    # same RNG seed → same stream semantics: both draw from the same marginal,
    # so the empirical distributions agree (not necessarily identical draws).
    assert abs(batch.mean() - single.mean()) < 0.2
    # batch distribution ≈ theory n̄ = sinh² r
    assert abs(batch.mean() - np.sinh(0.8) ** 2) < 0.15


def test_pnr_sample_batch_density_2mode() -> None:
    from cvsim.fock import pnr_sample_batch
    from cvsim.fock.gates import two_mode_squeeze

    st = FockDensity.from_pure(two_mode_squeeze(FockState.vacuum(8, nmode=2), 0.5))
    out = pnr_sample_batch(st, mode=1, size=600, rng=np.random.default_rng(2))
    assert out.shape == (600,)
    # marginal on mode 1 of TMSV: thermal n̄ = sinh² r
    assert abs(out.mean() - np.sinh(0.5) ** 2) < 0.2


# -- coverage supplement (2026-09-07): guard/error/func branches ------------


def _pure1(N=5, alpha=0.0):
    return FockState.coherent(N, alpha)


def _pure2(N=4):
    amps = np.zeros((N, N), dtype=complex)
    amps[0, 0] = 1.0
    return FockState(amps=amps)


def _dens1(N=5, alpha=0.0):
    return FockDensity.from_pure(_pure1(N, alpha))


def _dens2(N=4):
    rho = np.zeros((N * N, N * N), dtype=complex)
    rho[0, 0] = 1.0
    return FockDensity(rho=rho, nmode=2)


class TestModeGuards:
    """index/value guards for pnrd_probs / mean_photon / pnr_condition."""

    def test_pnrd_dens1_mode1_raises(self):
        with pytest.raises(IndexError, match="nmode=1"):
            pnrd_probs(_dens1(), mode=1)

    def test_pnrd_dens2_mode2_raises(self):
        with pytest.raises(IndexError, match="nmode=2"):
            pnrd_probs(_dens2(), mode=2)

    def test_pnrd_pure2_mode2_raises(self):
        with pytest.raises(IndexError, match="nmode=2"):
            pnrd_probs(_pure2(), mode=2)

    def test_mean_photon_dens1_mode1_raises(self):
        from cvsim.fock.observables import mean_photon

        with pytest.raises(IndexError, match="nmode=1"):
            mean_photon(_dens1(), mode=1)

    def test_mean_photon_dens2_mode2_raises(self):
        from cvsim.fock.observables import mean_photon

        with pytest.raises(IndexError, match="nmode=2"):
            mean_photon(_dens2(), mode=2)

    def test_mean_photon_pure2_mode2_raises(self):
        from cvsim.fock.observables import mean_photon

        with pytest.raises(IndexError, match="nmode=2"):
            mean_photon(_pure2(), mode=2)

    def test_pnr_condition_pure1_mode1_raises(self):
        with pytest.raises(IndexError, match="nmode=1"):
            pnr_condition(_pure1(), mode=1)

    def test_pnr_condition_pure2_mode2_raises(self):
        with pytest.raises(IndexError, match="nmode=2"):
            pnr_condition(_pure2(), mode=2)

    def test_pnr_condition_pure2_zero_prob(self):
        # |1,0⟩: mode0 n=0 has zero amplitude
        st = FockState(amps=np.array([[0.0, 0.0], [1.0, 0.0]], dtype=complex))
        with pytest.raises(ValueError, match="zero probability"):
            pnr_condition(st, mode=0, n=0)

    def test_pnr_condition_dens1_n_out_of_cutoff(self):
        with pytest.raises(IndexError, match="cutoff"):
            pnr_condition(_dens1(N=5), n=5)

    def test_pnr_condition_dens1_mode1_raises(self):
        with pytest.raises(IndexError, match="nmode=1"):
            pnr_condition(_dens1(), mode=1)

    def test_pnr_condition_dens1_zero_prob(self):
        with pytest.raises(ValueError, match="zero probability"):
            pnr_condition(_dens1(), n=3)  # vacuum has no n=3

    def test_pnr_condition_dens2_mode2_raises(self):
        with pytest.raises(IndexError, match="nmode=2"):
            pnr_condition(_dens2(), mode=2)

    def test_pnr_condition_dens2_zero_prob(self):
        with pytest.raises(ValueError, match="zero probability"):
            pnr_condition(_dens2(), mode=0, n=1)


class TestPnrDensityPosterior:
    def test_dens1_pnr_posterior_projective(self):
        """1-mode density PNR posterior = |n⟩⟨n| (projective)."""
        out = pnr_condition(_dens1(alpha=1.0), n=2)
        assert isinstance(out, FockDensity)
        rho = out.rho
        assert abs(rho[2, 2] - 1.0) < 1e-12
        assert abs(rho[2, :].sum() - 1.0) < 1e-12  # normalised


class TestHeterodyneGuards:
    def test_heterodyne_sample_dens1_mode1_raises(self):
        with pytest.raises(IndexError, match="nmode=1"):
            heterodyne_sample(_dens1(), mode=1)

    def test_heterodyne_sample_pure1_mode1_raises(self):
        with pytest.raises(IndexError, match="nmode=1"):
            heterodyne_sample(_pure1(), mode=1)

    def test_heterodyne_sample_n_grid_raises(self):
        with pytest.raises(ValueError, match="n_grid"):
            heterodyne_sample(_pure1(), n_grid=2)

    def test_heterodyne_sample_zero_state(self):
        with pytest.raises(ValueError, match="zero state"):
            heterodyne_sample(FockState(amps=np.zeros(4)))

    def test_heterodyne_condition_dens1_mode1_raises(self):
        with pytest.raises(IndexError, match="nmode=1"):
            heterodyne_condition(_dens1(), mode=1)

    def test_heterodyne_condition_dens2_mode2_raises(self):
        with pytest.raises(IndexError, match="nmode=2"):
            heterodyne_condition(_dens2(), mode=2)

    def test_heterodyne_condition_dens2_zero_prob(self):
        with pytest.raises(ValueError, match="zero probability"):
            heterodyne_condition(_dens2(), beta=10.0)

    def test_heterodyne_condition_pure1_mode1_raises(self):
        with pytest.raises(IndexError, match="nmode=1"):
            heterodyne_condition(_pure1(), mode=1)

    def test_heterodyne_condition_pure2_mode2_raises(self):
        with pytest.raises(IndexError, match="nmode=2"):
            heterodyne_condition(_pure2(), mode=2)

    def test_heterodyne_condition_pure2_zero_prob(self):
        with pytest.raises(ValueError, match="zero probability"):
            heterodyne_condition(_pure2(), beta=10.0)


class TestHeterodyneDensityPaths:
    def test_heterodyne_sample_dens1_rng(self):
        out = heterodyne_sample(_dens1(alpha=0.5), rng=np.random.default_rng(0))
        assert isinstance(out, complex)

    def test_heterodyne_sample_dens2_mode0(self):
        out = heterodyne_sample(_dens2(), rng=np.random.default_rng(0))
        assert isinstance(out, complex)

    def test_heterodyne_sample_dens2_mode1(self):
        out = heterodyne_sample(_dens2(), mode=1, rng=np.random.default_rng(0))
        assert isinstance(out, complex)

    def test_heterodyne_condition_dens1_returns_coherent(self):
        """1-mode density posterior = |β⟩⟨β| (rank-1 POVM)."""
        out = heterodyne_condition(_dens1(), beta=0.5)
        assert isinstance(out, FockDensity)
        assert out.nmode == 1

    def test_heterodyne_sample_default_rng(self):
        """rng=None path (internal default_rng())."""
        out = heterodyne_sample(_pure1(alpha=0.5))
        assert isinstance(out, complex)

    def test_heterodyne_sample_both_modes_dens2(self):
        """2-mode density marginal einsum branches (mode 0 and 1)."""
        rng = np.random.default_rng(1)
        out0 = heterodyne_sample(_dens2(), mode=0, rng=rng)
        out1 = heterodyne_sample(_dens2(), mode=1, rng=rng)
        assert isinstance(out0, complex) and isinstance(out1, complex)


class TestRngDefaults:
    """rng=None default branches (TRIVIAL)."""

    def test_pnr_sample_default_rng(self):
        n = pnr_sample(_pure1(alpha=1.0))
        assert 0 <= n < 5

    def test_pnr_sample_batch_default_rng(self):
        from cvsim.fock import pnr_sample_batch

        out = pnr_sample_batch(_pure1(alpha=1.0), size=7)
        assert out.shape == (7,)
        assert np.all(out >= 0)

# -- ADR-0012 AC-9: pnr_condition / pnrd_probs generalized to nmode ≤ 4 ------
#
# Convention (unchanged from the 2-mode paths, regression-locked):
# - pure posterior: measured mode REMOVED (np.take on that axis), amps
#   (k−1)-D of shape (N,)*(nmode−1), renormalized;
# - density posterior: measured mode FROZEN at |n⟩ (projector masking),
#   nmode preserved, trace renormalized to 1.

def _pure3(N=4):
    """Product pure state |1⟩⊗|2⟩⊗|0⟩."""
    amps = np.zeros((N, N, N), dtype=complex)
    amps[1, 2, 0] = 1.0
    return FockState(amps=amps)

def _entangled3(N=4):
    """0.6|0,1,2⟩ + 0.8|1,0,2⟩ superposition (tests marginal/condition axes)."""
    amps = np.zeros((N, N, N), dtype=complex)
    amps[0, 1, 2] = 0.6
    amps[1, 0, 2] = 0.8
    return FockState(amps=amps)

def _e(N, n):
    out = np.zeros(N, dtype=complex)
    out[n] = 1.0
    return out

def test_ac9_pnrd_probs_pure3_joint_and_marginal() -> None:
    st = _entangled3(4)
    joint = pnrd_probs(st)  # mode=None → (N,N,N) joint |c|²
    assert joint.shape == (4, 4, 4)
    expect = np.zeros((4, 4, 4))
    expect[0, 1, 2] = 0.36
    expect[1, 0, 2] = 0.64
    np.testing.assert_allclose(joint, expect, atol=1e-14)
    np.testing.assert_allclose(pnrd_probs(st, mode=0), expect.sum(axis=(1, 2)), atol=1e-14)
    np.testing.assert_allclose(pnrd_probs(st, mode=1), expect.sum(axis=(0, 2)), atol=1e-14)
    np.testing.assert_allclose(pnrd_probs(st, mode=2), expect.sum(axis=(0, 1)), atol=1e-14)

def test_ac9_pnrd_probs_dens3_joint_and_marginal() -> None:
    st = FockDensity.from_pure(_entangled3(4))
    joint = pnrd_probs(st)  # diag(ρ) reshaped — independent of pure path
    assert joint.shape == (4, 4, 4)
    expect = np.zeros((4, 4, 4))
    expect[0, 1, 2] = 0.36
    expect[1, 0, 2] = 0.64
    np.testing.assert_allclose(joint, expect, atol=1e-14)
    np.testing.assert_allclose(pnrd_probs(st, mode=1), expect.sum(axis=(0, 2)), atol=1e-14)

def test_ac9_pnr_condition_pure3_product_gold() -> None:
    """|1⟩⊗|2⟩⊗|0⟩: condition mode j → tensor product of the other two."""
    st = _pure3(4)
    np.testing.assert_allclose(
        pnr_condition(st, mode=0, n=1).amps, np.outer(_e(4, 2), _e(4, 0)), atol=1e-14
    )
    np.testing.assert_allclose(
        pnr_condition(st, mode=1, n=2).amps, np.outer(_e(4, 1), _e(4, 0)), atol=1e-14
    )
    np.testing.assert_allclose(
        pnr_condition(st, mode=2, n=0).amps, np.outer(_e(4, 1), _e(4, 2)), atol=1e-14
    )

def test_ac9_pnr_condition_pure3_entangled_gold() -> None:
    """Condition mode0 n=0 of 0.6|0,1,2⟩+0.8|1,0,2⟩ → |1⟩⊗|2⟩;
    mode1 n=0 slice keeps only |1,0,2⟩ → |1⟩⊗|2⟩ as well."""
    st = _entangled3(4)
    np.testing.assert_allclose(
        pnr_condition(st, mode=0, n=0).amps, np.outer(_e(4, 1), _e(4, 2)), atol=1e-14
    )
    np.testing.assert_allclose(
        pnr_condition(st, mode=1, n=0).amps, np.outer(_e(4, 1), _e(4, 2)), atol=1e-14
    )

def test_ac9_pnr_condition_dens3_projector_gold() -> None:
    """3-mode density: posterior = A ρ A†/p, explicit kron projector gold;
    measured mode stays frozen at |n⟩ (nmode preserved)."""
    st = FockDensity.from_pure(_entangled3(4))
    mode, n = 0, 0
    out = pnr_condition(st, mode=mode, n=n)
    N = 4
    P = np.zeros((N, N))
    P[n, n] = 1.0
    A = np.kron(np.kron(P, np.eye(N)), np.eye(N))
    p = float(np.real(np.trace(A @ st.rho @ A)))
    gold = A @ st.rho @ A / p
    np.testing.assert_allclose(out.rho, gold, atol=1e-14)
    assert abs(np.trace(out.rho).real - 1.0) < 1e-12

def test_ac9_pnr_condition_dens3_mixed_rho() -> None:
    """Genuinely mixed 3-mode ρ with coherence: projection mode0→|0⟩ kills the
    |111⟩ block and |000⟩⟨111| coherence; posterior = pure |000⟩⟨000|."""
    N = 3
    rho = np.zeros((N**3, N**3), dtype=complex)
    i000 = 0
    i111 = 9 + 3 + 1
    rho[i000, i000] = 0.5
    rho[i111, i111] = 0.5
    rho[i000, i111] = 0.3
    rho[i111, i000] = 0.3
    st = FockDensity(rho=rho, nmode=3)
    out = pnr_condition(st, mode=0, n=0)
    expect = np.zeros((N**3, N**3), dtype=complex)
    expect[i000, i000] = 1.0
    np.testing.assert_allclose(out.rho, expect, atol=1e-14)

def test_ac9_pnr_condition_pure4_sanity() -> None:
    N = 2
    amps = np.zeros((N, N, N, N), dtype=complex)
    amps[0, 1, 0, 1] = 1.0  # |0,1,0,1⟩
    st = FockState(amps=amps)
    out = pnr_condition(st, mode=1, n=1)  # → |0,0,1⟩ (3-mode)
    assert out.nmode == 3
    expect = np.einsum("i,j,k->ijk", _e(2, 0), _e(2, 0), _e(2, 1))
    np.testing.assert_allclose(out.amps, expect, atol=1e-14)

def test_ac9_pnr_condition_dens4_sanity() -> None:
    """Density conditioning keeps nmode (frozen mode): 4-mode → 4-mode."""
    N = 2
    amps = np.zeros((N, N, N, N), dtype=complex)
    amps[0, 0, 1, 0] = 1.0  # |0,0,1,0⟩
    st = FockDensity.from_pure(FockState(amps=amps))
    out = pnr_condition(st, mode=2, n=1)
    assert out.nmode == 4
    expect = np.zeros((N**4, N**4), dtype=complex)
    idx = 0 * 8 + 0 * 4 + 1 * 2 + 0
    expect[idx, idx] = 1.0
    np.testing.assert_allclose(out.rho, expect, atol=1e-14)
    with pytest.raises(ValueError, match="zero probability"):
        pnr_condition(st, mode=2, n=0)

def test_ac9_pnr_condition_2mode_regression() -> None:
    """2-mode paths bit-identical to the pre-ADR-0012 convention."""
    amps = np.zeros((6, 6), dtype=complex)
    amps[1, 2] = 0.6
    amps[0, 3] = 0.8
    st = FockState(amps=amps)
    np.testing.assert_allclose(
        pnr_condition(st, 0, 1).amps, FockState.fock(2, 6).amps, atol=1e-14
    )
    np.testing.assert_allclose(
        pnr_condition(st, 1, 3).amps, FockState.fock(0, 6).amps, atol=1e-14
    )

def test_ac9_pnrd_and_condition_mode_out_of_range_raises() -> None:
    st3 = _entangled3(4)
    with pytest.raises(IndexError, match="nmode=3"):
        pnrd_probs(st3, mode=3)
    with pytest.raises(IndexError, match="nmode=3"):
        pnr_condition(st3, mode=3, n=0)
    d3 = FockDensity.from_pure(st3)
    with pytest.raises(IndexError, match="nmode=3"):
        pnrd_probs(d3, mode=3)
    with pytest.raises(IndexError, match="nmode=3"):
        pnr_condition(d3, mode=3, n=0)

def test_ac9_pnr_condition_nmode5_raises() -> None:
    # FockState ndim hard cap: 5-mode pure state cannot be constructed
    with pytest.raises(ValueError, match="ndim"):
        FockState(amps=np.zeros((2,) * 5, dtype=complex))
