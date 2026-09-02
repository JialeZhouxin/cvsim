"""B8 Bosonic non-Gaussian kerr gate (component expansion).

Kerr: |n⟩ → e^{iχ n²} |n⟩. In the component (Wigner) representation a single
Gaussian component is NOT closed under Kerr (it is non-Gaussian), so kerr
expands each input Gaussian component into complex Gaussian components
(diagonal real-centre + cross complex-centre, Gram-normalised).

Truth anchors used here (no cross-rep bridge — ADR-0001):
  - Kerr is photon-number diagonal → ⟨n⟩ preserved (= |α|² for coherent).
    Verified against Fock kerr as the authoritative reference.
  - kerr(χ=π) = parity split: decomposes coherent into even/odd cats, so
    pure_fidelity(kerr(π)|α⟩, even_cat) + (·, odd_cat) = 1 exactly.
  - Vacuum invariant (e^{iχ·0}=1); kerr output must be Hermitian-closed.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import (
    coherent,
    even_cat,
    is_hermitian,
    kerr,
    mean_photon,
    odd_cat,
    weight_sum,
)
from cvsim.bosonic.analyse import pure_fidelity, purity
from cvsim.bosonic.state import BosonicState
from cvsim.conventions import vacuum_cov


@pytest.mark.phaseB8
def test_kerr_vacuum_unchanged():
    """kerr on vacuum: phase e^{iχ·0}=1 → vacuum stays single component."""
    vac = BosonicState.vacuum(1)
    out = kerr(vac, 1.7)
    assert out.n_components == 1
    assert abs(weight_sum(out) - 1.0) < 1e-12
    np.testing.assert_allclose(out.components[0].V, vacuum_cov(1), atol=1e-12)
    np.testing.assert_allclose(out.components[0].rbar, 0.0, atol=1e-12)


@pytest.mark.phaseB8
def test_kerr_coherent_is_nongaussian_and_normalized():
    """kerr on coherent increases components but keeps weight_sum ~ 1."""
    st = coherent(1.5)
    out = kerr(st, 1.0)
    assert out.n_components > 1
    assert abs(weight_sum(out) - 1.0) < 1e-10
    assert is_hermitian(out)  # closure under conjugation


@pytest.mark.phaseB8
def test_kerr_preserves_mean_photon_exact_chi():
    """Kerr is photon-number diagonal → ⟨n⟩ = |α|² preserved exactly.

    For closed-loop χ (2π/χ integer → auto-q matches the phase grid) the
    component expansion reproduces the invariant to tight tolerance.
    """
    alpha = 1.5
    for chi in (np.pi, np.pi / 2, 2 * np.pi / 3):
        out = kerr(coherent(alpha), chi)
        assert abs(mean_photon(out) - abs(alpha) ** 2) < 1e-6, f"chi={chi}"


@pytest.mark.phaseB8
def test_kerr_pi_decomposes_into_even_odd_cats():
    """kerr(χ=π) = parity split: even_cat + odd_cat decomposition sums to 1.

    e^{iπn²}=(-1)^n projects coherent onto even/odd parity. The kerr output
    must therefore have overlap 1 with the even/odd cat pair (each < 1), and
    ≈0 with the original coherent state. This is a strong bosonic-native
    validation via pure_fidelity (no cross-rep bridge needed).
    """
    alpha = 1.5
    kpi = kerr(coherent(alpha), np.pi)
    f_even = pure_fidelity(kpi, even_cat(alpha))
    f_odd = pure_fidelity(kpi, odd_cat(alpha))
    # Parity decomposition: total overlap with the cat pair = 1 exactly.
    assert abs(f_even + f_odd - 1.0) < 1e-9
    # Both branches present (α=1.5 gives near-balanced split).
    assert 0.4 < f_even < 0.6
    assert 0.4 < f_odd < 0.6
    # Kerr changed the state: overlap with the original coherent ≈ 0.
    f_coh = pure_fidelity(kpi, coherent(alpha))
    assert f_coh < 1e-3


@pytest.mark.phaseB8
def test_kerr_pi_is_pure_state():
    """kerr(χ=π) on coherent is a pure state (unitary on a pure state)."""
    out = kerr(coherent(1.5), np.pi)
    assert abs(purity(out, validate=False) - 1.0) < 1e-6


@pytest.mark.phaseB8
def test_kerr_matches_fock_mean_photon():
    """Cross-representation scalar: ⟨n⟩ of kerr(χ)(|α⟩) agrees with Fock kerr.

    Fock is the authoritative reference (no ADR-bridge, scalar observable
    only). Closed-loop χ → tight 1e-6; non-closed χ (χ=1.0) → the component
    expansion has a known ~1% floor, so a looser bound is asserted honestly.
    """
    from cvsim.fock import FockState
    from cvsim.fock.gates import kerr as fock_kerr
    from cvsim.fock.observables import mean_photon as fock_mean

    cutoff = 40
    alpha = 1.5
    for chi, tol in ((np.pi, 1e-6), (np.pi / 2, 1e-6), (2 * np.pi / 3, 1e-6), (1.0, 0.03)):
        gold_n = fock_mean(fock_kerr(FockState.coherent(cutoff, complex(alpha)), chi))
        bos_n = mean_photon(kerr(coherent(alpha), chi))
        assert abs(bos_n - gold_n) / max(1.0, abs(gold_n)) < tol, f"chi={chi}"
