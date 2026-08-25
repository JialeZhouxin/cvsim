"""F3 sparse: FockSparse — photon-number-sparse amplitudes (m≤10 anchor)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import coo_array

from cvsim.fock import FockState
from cvsim.fock.sparse import FockSparse


def test_factories_and_nnz() -> None:
    v = FockSparse.vacuum(10, cutoffs=2)
    assert v.nmode == 10 and v.nnz == 1
    sp = FockSparse.single_photon(3, 4, cutoffs=[5, 6, 7, 8])
    assert sp.nnz == 1
    assert sp.cutoffs == (5, 6, 7, 8)
    c = FockSparse.from_components(
        {(0, 3): 1 / np.sqrt(2), (2, 1): 1j / np.sqrt(2)}, cutoffs=[4, 5]
    )
    assert c.nnz == 2
    assert abs(c.norm() - 1.0) < 1e-12


def test_diagonal_gates_stay_sparse() -> None:
    s = FockSparse.single_photon(1, 2, cutoffs=[4, 5])
    s2 = s.phase(1, 0.7).kerr(0, 0.3)
    assert s2.nnz == 1  # never densified
    np.testing.assert_allclose(s2.norm(), 1.0, atol=1e-12)
    # phase by n·θ: single photon n=1 → e^{iθ}
    np.testing.assert_allclose(s2.data.data, np.exp(1j * 0.7), atol=1e-12)


def test_permute_reorders_modes() -> None:
    s = FockSparse.single_photon(1, 2, cutoffs=[4, 5]).phase(1, 0.9)
    p = s.permute([1, 0])
    coords = p.data.coords
    assert coords[0][0] == 1 and coords[1][0] == 0  # photon moved to mode 0
    np.testing.assert_allclose(p.data.data, np.exp(1j * 0.9), atol=1e-12)


def test_identical_physics_vs_dense() -> None:
    """Sparse chain == dense chain on the shared (diagonal + permute) ops."""
    s = (
        FockSparse.from_components({(0, 0): 0.6, (1, 0): 0.8}, cutoffs=[3, 3])
        .phase(0, 0.4)
        .kerr(1, 0.2)
        .permute([1, 0])
    )
    d = s.to_dense()
    assert isinstance(d, FockState)
    # dense reference: same ops on the dense tensor (free-function gates)
    from cvsim.fock.gates import kerr, phase

    ref = np.zeros((3, 3), dtype=complex)
    ref[0, 0], ref[1, 0] = 0.6, 0.8
    ref = phase(FockState(amps=ref), 0.4)
    ref = kerr(ref, 0.2, mode=1)
    ref = FockState(amps=np.transpose(ref.amps, (1, 0)))
    np.testing.assert_allclose(d.amps, ref.amps, atol=1e-12)


def test_pnrd_probs_no_dense_materialization() -> None:
    c = FockSparse.from_components({(0, 0): 1 / np.sqrt(2), (2, 1): 1 / np.sqrt(2)}, cutoffs=[4, 3])
    p0 = c.pnrd_probs(0)
    assert p0.shape == (4,)
    np.testing.assert_allclose(p0, [0.5, 0.0, 0.5, 0.0], atol=1e-12)
    assert abs(p0.sum() - 1.0) < 1e-12


def test_m10_anchor() -> None:
    """m=10 sparse state (dense volume 2^10=1024, 3^10≈59k) stays tiny."""
    v = FockSparse.vacuum(10, cutoffs=3)
    s = FockSparse.single_photon(9, 10, cutoffs=3)
    both = FockSparse.from_components(
        {(0,) * 10: 1 / np.sqrt(2), (1,) + (0,) * 9: 1 / np.sqrt(2)},
        cutoffs=[3] * 10,
    )
    assert v.nnz == 1 and s.nnz == 1 and both.nnz == 2
    out = both.phase(9, 0.5).kerr(0, 0.1)
    assert out.nnz == 2
    # sparse access only — dense m>4 handoff is honestly capped (vision Q6)
    np.testing.assert_allclose(out.pnrd_probs(0), [0.5, 0.5, 0.0], atol=1e-12)


def test_validation_rejects_bad_states() -> None:
    with pytest.raises(ValueError):
        FockSparse.from_components({(0, 0): 0.5}, cutoffs=[2, 2])  # unnormalized
    with pytest.raises(ValueError):
        FockSparse(coo_array(([1.0], ([0], [0])), shape=(2, 2)), [2])  # ndim mismatch
    with pytest.raises(ValueError):
        FockSparse.single_photon(1, 2, cutoffs=[4, 5]).permute([0, 0])
    with pytest.raises(IndexError):
        FockSparse.single_photon(0, 2, cutoffs=[4, 5]).phase(2, 0.3)
