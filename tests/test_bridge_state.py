"""State bridge bosonic -> fock (ADR-0012): acceptance criteria AC-1..AC-8.

Gold sources (two independent paths per criterion where possible):
- analytic closed forms: ``bridge.coherent_element`` / ``squeezed_element`` /
  ``thermal_diag``;
- bosonic-side photon statistics: ``cvsim.bosonic.measure.pnr_probs``;
- fock-side gate chains (loose, expm cutoff artifacts) and the exact TMSV
  heralding structure (TMSV = sum_t t_t |t,t>, per-element exact).

Tolerance policy (probe-pinned): TOL = 1e-9 vs analytic / exact-structure
golds; LOOSE = 3e-2 vs fock gate chains (their own expm truncation artifacts
at small cutoff dominate). No renormalization in the kernel: elements are the
exact truncated operators; trace = 1 - tail (tail never guessed, vision §5).
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic.cat import even_cat
from cvsim.bosonic.gates import displace as bosonic_displace
from cvsim.bosonic.gates import squeeze as bosonic_squeeze
from cvsim.bosonic.gates import two_mode_squeeze
from cvsim.bosonic.measure import pnr_probs
from cvsim.bosonic.state import BosonicState, Component
from cvsim.bridge import (
    bosonic_to_fock,
    coherent_element,
    pnr_condition_bosonic,
    pnr_sample_and_condition_bosonic,
    squeezed_element,
    thermal_diag,
)
from cvsim.fock.density import FockDensity
from cvsim.fock.gates import displace as fock_displace
from cvsim.fock.gates import squeeze as fock_squeeze
from cvsim.gaussian.state import GaussianState

TOL = 1e-9
LOOSE = 3e-2

SQRT2 = np.sqrt(2.0)


def _tmsv(r: float) -> BosonicState:
    return two_mode_squeeze(BosonicState.vacuum(2), r, 0, 1)


# -- AC-1: coherent gold (analytic outer product) -----------------------------

def test_ac1_coherent_gold() -> None:
    alpha = 0.9 + 0.4j
    st = BosonicState.from_gaussian(GaussianState.coherent(alpha))
    rho = bosonic_to_fock(st, cutoff=10)
    amps = np.array([coherent_element(n, alpha) for n in range(10)])
    gold = np.outer(amps, amps.conj())
    assert rho.nmode == 1
    assert float(np.max(np.abs(rho.rho - gold))) <= TOL
    # exact-truncation convention: trace carries the analytic-window tail too
    assert abs(float(np.trace(rho.rho).real) - float(np.trace(gold).real)) <= TOL
    assert float(np.max(np.abs(rho.rho - rho.rho.conj().T))) <= TOL


def test_ac1_coherent_2mode_product() -> None:
    """Two coherent modes: kernel result vs analytic product state."""
    a0, a1 = 0.7 + 0.2j, -0.4 + 0.3j
    st = BosonicState.from_gaussian(GaussianState.coherent(a0, nmode=2, mode=0))
    st = bosonic_displace(st, a1, 1)
    N = 8
    rho = bosonic_to_fock(st, cutoff=N)
    amps0 = np.array([coherent_element(n, a0) for n in range(N)])
    amps1 = np.array([coherent_element(n, a1) for n in range(N)])
    vec = np.kron(amps0, amps1)
    gold = np.outer(vec, vec.conj())
    assert float(np.max(np.abs(rho.rho - gold))) <= 1e-6
    # joint diagonal exact vs analytic product distribution
    diag = np.real(np.diag(rho.rho)).reshape(N, N)
    assert float(np.max(np.abs(diag - np.outer(np.abs(amps0) ** 2, np.abs(amps1) ** 2)))) <= TOL


# -- AC-2: thermal gold (mixed component, spectral route) ----------------------

def test_ac2_thermal_diagonal() -> None:
    nbar = 0.7
    st = BosonicState.from_gaussian(GaussianState.thermal(nbar))
    N = 15
    rho = bosonic_to_fock(st, cutoff=N)
    p = np.array([thermal_diag(n, nbar) for n in range(N)])
    assert float(np.max(np.abs(np.real(np.diag(rho.rho)) - p))) <= TOL
    off = rho.rho - np.diag(np.diag(rho.rho))
    assert float(np.max(np.abs(off))) <= 1e-12
    # exact-truncation convention: trace = 1 - tail (never renormalized)
    tail = (nbar / (nbar + 1.0)) ** N
    assert abs(float(np.trace(rho.rho).real) - (1.0 - tail)) <= 1e-6
    # bridged density carries no factory tail: unknown, never guessed (vision §5)
    assert rho.tail is None


# -- AC-3: vacuum + squeezed analytic gold --------------------------------------

def test_ac3_vacuum() -> None:
    rho = bosonic_to_fock(BosonicState.vacuum(1), cutoff=6)
    expect = np.zeros((6, 6), dtype=complex)
    expect[0, 0] = 1.0
    assert float(np.max(np.abs(rho.rho - expect))) <= TOL


def test_ac3_squeezed_gold() -> None:
    """Squeezed vacuum via bosonic gate chain vs analytic squeezed_element."""
    r = 0.8
    st = bosonic_squeeze(BosonicState.vacuum(1), r)
    N = 12
    rho = bosonic_to_fock(st, cutoff=N)
    amps = np.array([squeezed_element(n, r) for n in range(N)])
    amps /= np.linalg.norm(amps)  # window-normalized gold (truncated basis)
    gold = np.outer(amps, amps.conj())
    # N=12 window leaves ~1.5e-3 mass at n>=12 (squeezed tail): kernel keeps
    # exact truncation, gold is renormalized -> compare window-normalized
    rho_n = rho.rho / float(np.trace(rho.rho).real)
    assert float(np.max(np.abs(rho_n - gold))) <= 1e-6


# -- AC-4: cat interference (complex rbar cross operands survive) ---------------

def test_ac4_even_cat_interference() -> None:
    alpha = 0.8
    st = even_cat(alpha)
    N = 12
    rho = bosonic_to_fock(st, cutoff=N)
    comps = st.components
    # gold: Schrodinger-split window-normalized |+alpha>, |-alpha> amplitudes
    p = np.array([coherent_element(n, alpha) for n in range(N)])
    m = np.array([coherent_element(n, -alpha) for n in range(N)])
    p /= np.linalg.norm(p)
    m /= np.linalg.norm(m)
    tr_pm = complex(np.vdot(p, m))
    gp = np.outer(p, p.conj())
    gm = np.outer(m, m.conj())
    gmp = np.outer(p, m.conj()) / np.conj(tr_pm)  # |p><m| / window overlap
    gpm = np.outer(m, p.conj()) / tr_pm  # |m><p| / window overlap
    gold = comps[0].w * gp + comps[1].w * gm + comps[2].w * gpm + comps[3].w * gmp
    assert float(np.max(np.abs(rho.rho - gold))) <= TOL
    # interference structure survives: |0><2| coherence nonzero and hermitian
    assert abs(rho.rho[0, 2]) > 1e-3
    assert abs(rho.rho[0, 2] - rho.rho[2, 0].conj()) <= TOL


# -- AC-5: TMSV joint diagonal vs bosonic pnr_probs (two independent paths) -----

def test_ac5_tmsv_joint_diag_vs_pnr_probs() -> None:
    r = 0.7
    st = _tmsv(r)
    N = 14
    rho = bosonic_to_fock(st, cutoff=N)
    joint = pnr_probs(st, modes=None, cutoff=N).reshape(-1)
    diag = np.real(np.diag(rho.rho))
    # per-element agreement (no renormalization on either side)
    assert float(np.max(np.abs(joint - diag))) <= 1e-7


# -- AC-6: heralding — TMSV conditioned on mode-0 outcome k -> |k,k> structure --

def test_ac6_tmsv_heralding() -> None:
    """TMSV = sum_t t_t|t,t>: projecting mode 0 on |k> leaves pure |k,k>."""
    st = _tmsv(0.7)
    N = 12
    for k in (0, 2):
        post = pnr_condition_bosonic(st, mode=0, n=k, cutoff=N)
        expect = np.zeros((N * N, N * N), dtype=complex)
        expect[k * N + k, k * N + k] = 1.0
        assert float(np.max(np.abs(post.rho - expect))) <= 1e-7
        # reduced state of the remaining mode is |k><k|
        diag = np.real(np.diag(post.rho)).reshape(N, N)
        expect_diag = np.zeros((N, N))
        expect_diag[k, k] = 1.0
        assert float(np.max(np.abs(diag - expect_diag))) <= 1e-7


# -- AC-7: probability conservation (trace posterior = pnr_probs marginal) ------

def test_ac7_probability_conservation() -> None:
    """trace(posterior_n) = pnr_probs marginal; posterior itself normalized."""
    st = _tmsv(0.7)
    N = 12
    marginal = pnr_probs(st, cutoff=N)
    # posterior traces are 1 by fock normalization — TRUE conservation lives in
    # the pre-projection joint diagonal: row sums of the bridged rho diag must
    # reproduce the pnr_probs marginal per-element (two independent paths).
    rho = bosonic_to_fock(st, cutoff=N)
    diag = np.real(np.diag(rho.rho)).reshape(N, N)
    rows = diag.sum(axis=1)
    assert float(np.max(np.abs(rows - marginal))) <= 1e-7
    # each posterior is a proper normalized density
    for n in (0, 1, 2):
        post = pnr_condition_bosonic(st, mode=0, n=n, cutoff=N)
        assert abs(float(np.trace(post.rho).real) - 1.0) <= 1e-9


# -- AC-8: honest errors ----------------------------------------------------------

def test_ac8_zero_probability_outcome_raises() -> None:
    # vacuum has exactly zero support at n=1 (elementwise zero -> p <= _EPS)
    with pytest.raises(ValueError, match="zero probability"):
        pnr_condition_bosonic(BosonicState.vacuum(1), mode=0, n=1, cutoff=6)


def test_ac8_three_modes_raises() -> None:
    with pytest.raises(ValueError, match="1..2 modes"):
        bosonic_to_fock(BosonicState.vacuum(3), cutoff=6)


def test_ac8_2mode_mixed_raises() -> None:
    """2-mode mixed component (product thermal) -> honest ValueError."""
    v = np.eye(4) * 1.2  # det(2V) > 1, 2V not symplectic -> mixed
    st = BosonicState(components=[Component(V=v, rbar=np.zeros(4), w=1.0)])
    with pytest.raises(ValueError, match="2-mode mixed"):
        bosonic_to_fock(st, cutoff=6)


def test_ac8_complex_rbar_mixed_raises() -> None:
    v = (2 * 0.5 + 1) * 0.5 * np.eye(2)
    st = BosonicState(
        components=[Component(V=v, rbar=np.array([0.3, 1.2j]), w=1.0)]
    )
    with pytest.raises(ValueError, match="complex"):
        bosonic_to_fock(st, cutoff=8)


def test_ac8_empty_state_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        bosonic_to_fock(BosonicState(components=[]), cutoff=6)


def test_ac8_below_vacuum_raises() -> None:
    v = 0.3 * np.eye(2)  # det(2V) = 0.36 < 1
    st = BosonicState(components=[Component(V=v, rbar=np.zeros(2), w=1.0)])
    with pytest.raises(ValueError, match="below vacuum"):
        bosonic_to_fock(st, cutoff=6)


# -- sample-and-condition + mixed-kernel extras -----------------------------------

def test_pnr_sample_and_condition_smoke() -> None:
    rng = np.random.default_rng(42)
    st = BosonicState.from_gaussian(GaussianState.coherent(0.5))
    outcomes = set()
    for _ in range(40):
        n, post = pnr_sample_and_condition_bosonic(st, 0, cutoff=10, rng=rng)
        assert isinstance(n, int)
        assert abs(float(np.trace(post.rho).real) - 1.0) <= 1e-9
        outcomes.add(n)
    assert outcomes and outcomes <= set(range(6))


def test_displaced_thermalized_squeeze_vs_fock_chain() -> None:
    """Mixed displaced squeezed thermal: kernel vs fock chain gold (LOOSE).

    Bosonic state: V = (2 nbar+1) S V_vac S^T, mean = displacement alpha;
    Fock gold: D(alpha) S(r) rho_th(nbar) S(r)^dag D(alpha)^dag.
    """
    r_s, nbar, alpha = 0.5, 0.8, 0.6 + 0.3j
    v1 = np.diag([np.exp(-2 * r_s), np.exp(2 * r_s)]) * 0.5
    v = (2 * nbar + 1) * v1
    st = BosonicState(
        components=[
            Component(V=v, rbar=np.array([SQRT2 * 0.6, SQRT2 * 0.3]), w=1.0)
        ]
    )
    N = 12
    rho = bosonic_to_fock(st, cutoff=N)
    gold = fock_displace(fock_squeeze(FockDensity.thermal(N, nbar), r_s), alpha)
    assert float(np.max(np.abs(rho.rho - gold.rho))) <= LOOSE
    # kernel exact-truncation loses squeeze-window mass (~1.3e-2 at N=12);
    # gold chain keeps only thermal-tail loss -> compare against gold trace
    tr_k = float(np.trace(rho.rho).real)
    tr_g = float(np.trace(gold.rho).real)
    assert abs(tr_k - tr_g) <= 3 * LOOSE


def test_purity_thermalized_squeeze() -> None:
    """Thermalized squeezed vacuum: kernel Tr(rho^2) = bosonic purity = 1/(2n+1)."""
    from cvsim.bosonic.analyse import purity as bosonic_purity

    r_s, nbar = 0.5, 0.8
    v1 = np.diag([np.exp(-2 * r_s), np.exp(2 * r_s)]) * 0.5
    v = (2 * nbar + 1) * v1
    st = BosonicState(components=[Component(V=v, rbar=np.zeros(2), w=1.0)])
    rho = bosonic_to_fock(st, cutoff=40)
    tr2 = float(np.real(np.trace(rho.rho @ rho.rho)))
    assert abs(tr2 - 1.0 / (2 * nbar + 1)) <= 1e-6
    assert abs(float(bosonic_purity(st)) - 1.0 / (2 * nbar + 1)) <= 1e-12


def test_cutoff_validation() -> None:
    with pytest.raises(ValueError, match="cutoff"):
        bosonic_to_fock(BosonicState.vacuum(1), cutoff=0)
