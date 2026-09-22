"""Planar Wigner kernel tests (09-22-lab-wigner-plane S1).

AC1/AC2 anchors: the general ``wigner_plane(V, r̄, A)`` must reproduce the
legacy single-mode path bitwise when ``A`` picks one mode's ``(x, p)``, and the
complex-centre envelope must match ``wigner_point_gaussian`` point-for-point.

The bitexact assertion is deliberately ``array_equal`` (not ``allclose``): the
Lab golden responses are value-locked, so a 1e-15 drift in the quadratic form's
association order is a real regression, not tolerance noise.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import GaussianCircuit, GaussianState, partial_trace
from cvsim.wigner import wigner_gaussian, wigner_grid, wigner_plane, wigner_point_gaussian


def _run(circuit: GaussianCircuit) -> GaussianState:
    out = circuit.compile().run()
    return out[0] if isinstance(out, tuple) else out


def _legacy_scalar_grid(V: np.ndarray, rbar: np.ndarray, lim: float, n: int):
    """The removed Python double loop, kept here as the independent oracle."""
    xs = np.linspace(-lim, lim, n)
    ps = np.linspace(-lim, lim, n)
    X, P = np.meshgrid(xs, ps, indexing="xy")
    W = np.empty_like(X, dtype=float)
    state = GaussianState(V=V, rbar=rbar)
    for i in range(n):
        for j in range(n):
            W[i, j] = wigner_gaussian(state, float(X[i, j]), float(P[i, j]))
    return X, P, W


def _unit_basis_row(m: int, k: int, quad: str) -> np.ndarray:
    row = np.zeros(2 * m)
    row[k if quad == "x" else m + k] = 1.0
    return row


# --- AC1: A = [e_k, e_{m+k}] reproduces partial_trace + wigner_grid ---------


@pytest.mark.parametrize("m", [1, 2, 3])
def test_plane_unit_rows_match_partial_trace_grid(m: int) -> None:
    circuit = GaussianCircuit(m)
    for k in range(m):
        circuit.squeeze(k, r=m * 0.1 + 0.3 * k)
    for k in range(m):
        circuit.displace(k, alpha=0.2 * (k + 1) - 0.1j * k)
    state = _run(circuit)

    for k in range(m):
        reduced = partial_trace(state, keep=[k])
        Xg, Pg, Wg = wigner_grid(reduced, lim=5.0, n=16)
        A = np.stack([_unit_basis_row(m, k, "x"), _unit_basis_row(m, k, "p")])
        Xp, Yp, Wp = wigner_plane(state.V, state.rbar, A, lim=5.0, n=16)
        assert np.array_equal(Wp, Wg), f"m={m} k={k}: plane != partial_trace grid"
        assert np.array_equal(Xp, Xg)
        assert np.array_equal(Yp, Pg)


def test_plane_matches_legacy_scalar_loop_bitwise() -> None:
    """Vectorization must not move a single bit (golden lock depends on it)."""
    for circuit in (
        GaussianCircuit(1).squeeze(0, r=0.6),
        GaussianCircuit(1).displace(0, alpha=0.3j),
    ):
        state = _run(circuit)
        for n in (9, 32, 64):
            _, _, Wvec = wigner_grid(state, lim=5.0, n=n)
            _, _, Wleg = _legacy_scalar_grid(state.V, state.rbar, 5.0, n)
            assert np.array_equal(Wvec, Wleg), f"n={n}: vectorized grid drifted"


def test_grid_orientation_first_row_and_column() -> None:
    """X varies along axis 1, P along axis 0 (wigner_grid's documented order)."""
    state = GaussianState.vacuum(1)
    n, lim = 9, 4.0
    X, P, W = wigner_grid(state, lim=lim, n=n)
    xs = np.linspace(-lim, lim, n)
    assert np.array_equal(X[0], xs)
    assert np.array_equal(P[:, 0], xs)
    assert W.shape == (n, n)
    Xp, Yp, Wp = wigner_plane(state.V, state.rbar, np.eye(2), lim=lim, n=n)
    assert np.array_equal(Xp, X) and np.array_equal(Yp, P) and np.array_equal(Wp, W)


# --- AC2: complex centre matches the scalar kernel --------------------------


def test_plane_complex_centre_matches_point_kernel() -> None:
    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(20):
        B = rng.normal(size=(2, 2))
        V = B.T @ B + 0.3 * np.eye(2)
        rbar = rng.normal(size=2) + 1j * rng.normal(size=2)
        X, Y, W = wigner_plane(V, rbar, np.eye(2), lim=2.0, n=7)
        for i in range(7):
            for j in range(7):
                ref = wigner_point_gaussian(V, rbar, float(X[i, j]), float(Y[i, j])).real
                worst = max(worst, abs(W[i, j] - ref))
    assert worst < 1e-12, f"complex-centre envelope drifted: worst={worst:.3e}"


# --- presets: the A rows the Lab will actually build ------------------------


def test_xx_pp_epr_presets_match_hand_computed_covariance() -> None:
    """Each preset's C = A V Aᵀ must equal the hand-built sub-covariance."""
    state = _run(GaussianCircuit(2).two_mode_squeeze(0, 1, r=0.8))
    V, m = state.V, 2
    k, j = 0, 1

    xx = np.zeros((2, 2 * m))
    xx[0, k], xx[1, j] = 1.0, 1.0
    pp = np.zeros((2, 2 * m))
    pp[0, m + k], pp[1, m + j] = 1.0, 1.0
    epr = np.zeros((2, 2 * m))
    epr[0, k], epr[0, j] = 1 / np.sqrt(2), -1 / np.sqrt(2)
    epr[1, m + k], epr[1, m + j] = 1 / np.sqrt(2), 1 / np.sqrt(2)

    for name, A in (("xx", xx), ("pp", pp), ("epr", epr)):
        C = A @ V @ A.T
        assert np.allclose(C, C.T), f"{name}: C not symmetric"
        # odd n puts a grid point exactly on the mean → peak = prefactor.
        # (even n never samples the centre; do not assert the prefactor there.)
        X, Y, W = wigner_plane(V, state.rbar, A, lim=5.0, n=9)
        peak = W.max()
        assert peak == pytest.approx(1.0 / (np.pi * np.sqrt(np.linalg.det(2 * C))), rel=1e-12)

    # TMSV r=0.8 EPR plane: each axis is (x0−x1)/√2 etc, so vacuum-normalized
    # variance is e^{-2r}/2 — not e^{-2r} (that is the *unnormalized* axis).
    C_epr = epr @ V @ epr.T
    assert C_epr[0, 0] == pytest.approx(np.exp(-0.8 * 2) / 2, rel=1e-12)
    assert C_epr[1, 1] == pytest.approx(np.exp(-0.8 * 2) / 2, rel=1e-12)
    assert np.linalg.det(C_epr) == pytest.approx(0.010190550994591532, rel=1e-12)
    # axis std 0.3177 vs the vacuum reference 0.7071 (= 1/√2 per axis)
    assert np.sqrt(C_epr[0, 0]) == pytest.approx(0.31772356, rel=1e-6)
    assert 1 / np.sqrt(2) == pytest.approx(0.7071067811865476, rel=1e-15)
    # xx/pp planes keep the single-mode marginal variances on the diagonal
    C_xx = xx @ V @ xx.T
    assert C_xx[0, 0] == pytest.approx(1.28873224, rel=1e-6)
    assert C_xx[1, 1] == pytest.approx(1.28873224, rel=1e-6)
    # the xx plane is the correlated one: positive off-diagonal, and its
    # 45°-rotated eigen-basis variance is e^{-2r}/2 (that is why EPR works)
    assert C_xx[0, 1] == pytest.approx(1.18778398, rel=1e-6)
    lam = np.linalg.eigvalsh(C_xx)
    assert lam[0] == pytest.approx(np.exp(-1.6) / 2, rel=1e-9)
    C_pp = pp @ V @ pp.T
    assert C_pp[0, 1] == pytest.approx(-1.18778398, rel=1e-6)


# --- guards -----------------------------------------------------------------


def test_plane_guards() -> None:
    V = np.eye(2) / 2
    rbar = np.zeros(2)
    A = np.eye(2)
    with pytest.raises(ValueError, match="n must be >= 2"):
        wigner_plane(V, rbar, A, n=1)
    with pytest.raises(ValueError, match="lim must be a positive number"):
        wigner_plane(V, rbar, A, lim=0.0)
    with pytest.raises(ValueError, match=r"A must be \(2, 2\)"):
        wigner_plane(V, rbar, np.eye(3))
    with pytest.raises(ValueError, match=r"rbar must be \(2,\)"):
        wigner_plane(V, rbar=np.zeros(3), A=A, lim=1.0)
    with pytest.raises(ValueError, match=r"V must be \(2m,2m\)"):
        wigner_plane(np.eye(3), np.zeros(3), A)


def test_plane_singular_subcovariance_raises() -> None:
    """det(2C) <= 0 → ValueError (callers turn this into an honest null)."""
    V_singular = np.array([[0.5, 0.0], [0.0, 0.0]])
    with pytest.raises(ValueError, match=r"det\(2C\) must be > 0"):
        wigner_plane(V_singular, np.zeros(2), np.eye(2))


def test_plane_zero_norm_row_raises() -> None:
    """A row of zeros gives a singular C — same honest refusal, not a crash."""
    A = np.array([[1.0, 0.0], [0.0, 0.0]])
    with pytest.raises(ValueError, match=r"det\(2C\) must be > 0"):
        wigner_plane(np.eye(2) / 2, np.zeros(2), A)


def test_wigner_grid_still_rejects_multimode_gaussian() -> None:
    with pytest.raises(ValueError, match="single-mode only"):
        wigner_grid(GaussianState.vacuum(2))
