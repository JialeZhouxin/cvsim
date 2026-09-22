"""F1 gates: cz/cx/mach_zehnder/interferometer/apply_unitary (continuous-
variable physics, matches Gaussian conventions — vision-fock-simulator §4 F1)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import FockDensity, FockState
from cvsim.fock.gates import (
    annihilation,
    apply_unitary,
    beamsplitter,
    cx,
    cz,
    displace,
    interferometer,
    mach_zehnder,
    squeeze,
)

# -- helpers ---------------------------------------------------------------


def _is_unitary(U: np.ndarray, atol: float = 1e-10) -> bool:
    return bool(np.allclose(U @ U.conj().T, np.eye(U.shape[0]), atol=atol))


def _fock_quadrature_moments(state: FockState, cutoff: int) -> tuple[np.ndarray, np.ndarray]:
    """(central V, r̄) in xxpp order [x₁, x₂, p₁, p₂] from a 2-mode pure Fock ket.

    Central (not raw) second moments — otherwise a displaced input inflates
    ⟨x̂²⟩ by ⟨x̂⟩² and the comparison against the Gaussian V is meaningless.
    """
    a = annihilation(cutoff)
    ad = a.conj().T
    eye = np.eye(cutoff)
    two = [
        np.kron((a + ad) / np.sqrt(2.0), eye),
        np.kron(eye, (a + ad) / np.sqrt(2.0)),
        np.kron((a - ad) / (1j * np.sqrt(2.0)), eye),
        np.kron(eye, (a - ad) / (1j * np.sqrt(2.0))),
    ]
    psi = np.asarray(state.amps).reshape(-1)
    mu = np.array([(psi.conj() @ (op @ psi)).real for op in two])
    V = np.array(
        [
            [(psi.conj() @ (two[i] @ two[j]) @ psi).real - mu[i] * mu[j] for j in range(4)]
            for i in range(4)
        ]
    )
    return V, mu


def _gauss_quadrature_moments(gst: object) -> tuple[np.ndarray, np.ndarray]:
    """(V, r̄) straight off a GaussianState (already xxpp, ħ=1)."""
    return np.asarray(gst.V, float), np.asarray(gst.rbar, float)  # type: ignore[attr-defined]


# -- cz --------------------------------------------------------------------


def test_cz_zero_weight_identity() -> None:
    st0 = FockState.fock2(1, 1, 12)
    np.testing.assert_allclose(cz(st0, 0.0).amps, st0.amps, atol=1e-14)


def test_cz_unitary() -> None:
    for st0 in (FockState.fock2(2, 0, 10), FockState.fock2(1, 1, 10)):
        out = cz(st0, 0.7)
        np.testing.assert_allclose(
            np.sum(abs(out.amps) ** 2), np.sum(abs(st0.amps) ** 2), atol=1e-12
        )


def test_cz_requires_two_modes() -> None:
    with pytest.raises(ValueError):
        cz(FockState.vacuum(8), 0.5)


def test_cz_against_gaussian() -> None:
    """CZ on squeezed×vacuum matches Gaussian cz (same physics, xxpp ħ=1).

    Compares the full central covariance, not just ⟨n⟩: ⟨n⟩ is even in the CZ/CX
    sign, so a mean-photon-only check cannot see a sign error.
    """
    from cvsim.gaussian import GaussianState
    from cvsim.gaussian import cz as g_cz

    r, g = 0.6, 0.5
    N = 24
    fst = squeeze(FockState.vacuum(N, nmode=2), r, 0)
    fst = cz(fst, g, 0, 1)
    gst = g_cz(GaussianState.squeezed(r, nmode=2, mode=0), g, 0, 1)
    V_f, mu_f = _fock_quadrature_moments(fst, N)
    V_g, mu_g = _gauss_quadrature_moments(gst)
    np.testing.assert_allclose(mu_f, mu_g, atol=2e-3)
    np.testing.assert_allclose(V_f, V_g, atol=1e-4)


# -- cx --------------------------------------------------------------------


def test_cx_zero_weight_identity() -> None:
    st0 = FockState.fock2(1, 2, 10)
    np.testing.assert_allclose(cx(st0, 0.0).amps, st0.amps, atol=1e-14)


def test_cx_unitary() -> None:
    st = FockState.fock2(0, 1, 10)
    out = cx(st, 0.8)
    np.testing.assert_allclose(np.sum(abs(out.amps) ** 2), 1.0, atol=1e-12)


def test_cx_against_gaussian() -> None:
    """CX on displaced×vacuum matches Gaussian cx (same physics, xxpp ħ=1).

    Sign-sensitive by construction: with a displaced input the CZ/CX sign moves
    ⟨x̂₂⟩ and the x₁x₂ / p₁p₂ covariance entries, so comparing ⟨n⟩ alone (which is
    even in the sign) would pass even with the opposite-sign gate.
    """
    from cvsim.gaussian import GaussianCircuit

    alpha, g = 0.45, 0.8
    N = 26
    fst = cx(displace(FockState.vacuum(N, nmode=2), alpha, 0), g, 0, 1)
    V_f, mu_f = _fock_quadrature_moments(fst, N)

    gc = GaussianCircuit(2)
    gc.displace(0, alpha=alpha)
    gc.cx(0, 1, weight=g)
    gst = gc.run()
    V_g, mu_g = _gauss_quadrature_moments(gst)

    np.testing.assert_allclose(mu_f, mu_g, atol=2e-3)
    np.testing.assert_allclose(V_f, V_g, atol=1e-4)


def test_cx_sign_follows_weight() -> None:
    """cx(w)† = cx(−w): negating the weight must undo the gate exactly."""
    N = 18
    st = cx(displace(FockState.vacuum(N, nmode=2), 0.45, 0), 0.8, 0, 1)
    back = cx(st, -0.8, 0, 1)
    ref = displace(FockState.vacuum(N, nmode=2), 0.45, 0)
    np.testing.assert_allclose(back.amps, ref.amps, atol=1e-10)


def test_cz_cx_default_weight_is_identity() -> None:
    """Omitted ``weight`` must be the identity, in all three representations.

    Every other gate in every package defaults to identity (squeeze r=0, phase
    θ=0, displace α=0, kerr χ=0, two_mode_squeeze r=0). fock's cz/cx alone
    defaulted to 1.0 — i.e. building a circuit while omitting the weight gave a
    full entangling gate on fock but nothing on gaussian/bosonic, so the same
    partial circuit meant different physics per backend.
    """
    from cvsim.bosonic.circuit import BosonicCircuit
    from cvsim.bosonic.ir import OP_META as B_META
    from cvsim.fock.circuit import FockCircuit
    from cvsim.fock.ir import OP_META as F_META
    from cvsim.gaussian.circuit import GaussianCircuit
    from cvsim.gaussian.ir import OP_META as G_META

    assert G_META["cz"].defaults == {"weight": 0.0}
    assert F_META["cz"].defaults == {"weight": 0.0}, F_META["cz"].defaults
    assert F_META["cx"].defaults == {"weight": 0.0}, F_META["cx"].defaults
    assert B_META["cz"].defaults == G_META["cz"].defaults == F_META["cz"].defaults
    assert B_META["cx"].defaults == G_META["cx"].defaults == F_META["cx"].defaults

    # circuit level: an omitted weight records 0.0, not the old fock 1.0
    for cls in (FockCircuit, GaussianCircuit, BosonicCircuit):
        c = cls(2)
        c.cz(0, 1)
        c.cx(0, 1)
        name_cz, _modes, kwargs_cz = c._ops[-2][0], c._ops[-2][1], c._ops[-2][2]
        name_cx, _m2, kwargs_cx = c._ops[-1][0], c._ops[-1][1], c._ops[-1][2]
        assert name_cz == "cz" and kwargs_cz["weight"] == 0.0, (cls, c._ops[-2])
        assert name_cx == "cx" and kwargs_cx["weight"] == 0.0, (cls, c._ops[-1])


def test_cx_mode_order_matches_gaussian() -> None:
    """CX is NOT symmetric under mode swap: mode1/mode2 are physical.

    Pre-fix the fock gate ignored both args, so (1,0) silently returned the
    (0,1) result while gaussian distinguishes them.
    """
    from cvsim.gaussian import GaussianCircuit

    alpha, g, N = 0.45, 0.8, 26
    seen = []
    for m1, m2 in ((0, 1), (1, 0)):
        for w in (g, -g):
            fst = cx(displace(FockState.vacuum(N, nmode=2), alpha, 0), w, m1, m2)
            V_f, mu_f = _fock_quadrature_moments(fst, N)

            gc = GaussianCircuit(2)
            gc.displace(0, alpha=alpha)
            gc.cx(m1, m2, weight=w)
            V_g, mu_g = _gauss_quadrature_moments(gc.run())

            np.testing.assert_allclose(mu_f, mu_g, atol=2e-3, err_msg=f"cx modes ({m1},{m2}) w={w}")
            np.testing.assert_allclose(V_f, V_g, atol=1e-4, err_msg=f"cx modes ({m1},{m2}) w={w}")
            seen.append((m1, m2, w, mu_f))

    order01 = next(s for s in seen if s[:3] == (0, 1, g))[3]
    order10 = next(s for s in seen if s[:3] == (1, 0, g))[3]
    assert not np.allclose(order01, order10, atol=1e-6), "cx ignores mode order"


# -- beamsplitter -----------------------------------------------------------


def _bs_against_gaussian(theta: float, phi: float, m1: int, m2: int, N: int = 22):
    from cvsim.gaussian import GaussianCircuit

    alpha = 0.4
    fst = beamsplitter(displace(FockState.vacuum(N, nmode=2), alpha, 0), theta, phi, m1, m2)
    V_f, mu_f = _fock_quadrature_moments(fst, N)

    gc = GaussianCircuit(2)
    gc.displace(0, alpha=alpha)
    gc.beamsplitter(m1, m2, theta=theta, phi=phi)
    V_g, mu_g = _gauss_quadrature_moments(gc.run())
    return (V_f, mu_f), (V_g, mu_g)


def test_beamsplitter_mode_order_matches_gaussian() -> None:
    """BS is not mode-symmetric either (θ,φ order matters); modes are physical."""
    for theta, phi in ((0.7, 0.0), (0.7, 0.3), (np.pi / 4, 0.2), (0.5, -0.9)):
        mus = {}
        for m1, m2 in ((0, 1), (1, 0)):
            (V_f, mu_f), (V_g, mu_g) = _bs_against_gaussian(theta, phi, m1, m2)
            np.testing.assert_allclose(
                mu_f, mu_g, atol=2e-3, err_msg=f"bs θ={theta} φ={phi} modes ({m1},{m2})"
            )
            np.testing.assert_allclose(
                V_f, V_g, atol=1e-4, err_msg=f"bs θ={theta} φ={phi} modes ({m1},{m2})"
            )
            mus[(m1, m2)] = mu_f
        assert not np.allclose(mus[(0, 1)], mus[(1, 0)], atol=1e-6), (
            f"bs θ={theta} φ={phi}: mode order has no effect"
        )


def test_beamsplitter_positional_call_unchanged() -> None:
    """Backward compatibility: the old 3-arg positional form is bit-identical.

    ``beamsplitter(state, theta, phi)`` must keep defaulting to modes (0,1).
    """
    N = 14
    st = displace(FockState.vacuum(N, nmode=2), 0.4, 0)
    legacy = beamsplitter(st, 0.7, 0.3)
    explicit = beamsplitter(st, 0.7, 0.3, 0, 1)
    defaulted = beamsplitter(st, 0.7, 0.3, mode1=0, mode2=1)
    np.testing.assert_allclose(legacy.amps, explicit.amps, atol=0.0)
    np.testing.assert_allclose(legacy.amps, defaulted.amps, atol=0.0)
    # keyword-only form of the mode args must also work
    swapped = beamsplitter(st, 0.7, 0.3, mode1=1, mode2=0)
    assert not np.allclose(legacy.amps, swapped.amps, atol=1e-8)


# -- mach_zehnder -----------------------------------------------------------


def test_mz_matches_gaussian() -> None:
    """MZ on displaced×vacuum matches Gaussian S_mach_zehnder (xxpp ħ=1).

    Sign/phase-sensitive by construction: the internal phase φ acts on mode1, so
    with a displaced input it moves ⟨x̂₂⟩ and the x₁x₂ / p₁p₂ covariance entries.
    Comparing ⟨n⟩ or V alone would not see it.
    """
    from cvsim.gaussian import GaussianCircuit

    alpha = 0.4
    N = 22
    for theta, phi in ((0.6, 0.7), (0.0, 0.7), (np.pi / 4, 0.7), (1.1, 1.9)):
        fst = mach_zehnder(displace(FockState.vacuum(N, nmode=2), alpha, 0), 0, 1, theta, phi)
        V_f, mu_f = _fock_quadrature_moments(fst, N)

        gc = GaussianCircuit(2)
        gc.displace(0, alpha=alpha)
        gc.mach_zehnder(0, 1, theta=theta, phi=phi)
        V_g, mu_g = _gauss_quadrature_moments(gc.run())

        np.testing.assert_allclose(mu_f, mu_g, atol=2e-3, err_msg=f"rbar θ={theta} φ={phi}")
        np.testing.assert_allclose(V_f, V_g, atol=1e-3, err_msg=f"V θ={theta} φ={phi}")


def test_mz_phi_matters() -> None:
    """φ must actually change the state — the pre-fix fock MZ ignored it entirely."""
    N = 16
    st = displace(FockState.vacuum(N, nmode=2), 0.4, 0)
    mu0 = _fock_quadrature_moments(mach_zehnder(st, 0, 1, 0.6, 0.0), N)[1]
    mu7 = _fock_quadrature_moments(mach_zehnder(st, 0, 1, 0.6, 0.7), N)[1]
    assert not np.allclose(mu0, mu7, atol=1e-6), "mach_zehnder: φ has no effect"


def test_mz_mode_order() -> None:
    """MZ is not symmetric under mode swap: (mode1, mode2) is physical."""
    from cvsim.gaussian import GaussianCircuit

    alpha, theta, phi = 0.4, 0.6, 0.7
    N = 22
    seen = []
    for m1, m2 in ((0, 1), (1, 0)):
        fst = mach_zehnder(displace(FockState.vacuum(N, nmode=2), alpha, 0), m1, m2, theta, phi)
        V_f, mu_f = _fock_quadrature_moments(fst, N)

        gc = GaussianCircuit(2)
        gc.displace(0, alpha=alpha)
        gc.mach_zehnder(m1, m2, theta=theta, phi=phi)
        V_g, mu_g = _gauss_quadrature_moments(gc.run())

        np.testing.assert_allclose(mu_f, mu_g, atol=2e-3, err_msg=f"modes ({m1},{m2})")
        np.testing.assert_allclose(V_f, V_g, atol=1e-3, err_msg=f"modes ({m1},{m2})")
        seen.append(mu_f)

    assert not np.allclose(seen[0], seen[1], atol=1e-6), "mach_zehnder ignores mode order"


def test_mz_rejects_equal_modes() -> None:
    with pytest.raises(ValueError):
        mach_zehnder(FockState.vacuum(8, nmode=2), 1, 1, 0.6, 0.3)


def test_mz_analytic_anchor() -> None:
    # |1,0⟩ → BS(θ,0) → P(φ) on mode1 → BS(π/4,0).
    # BS(θ,0): |1,0⟩ → cosθ|1,0⟩ − sinθ|0,1⟩, then the mode-1 phase multiplies the
    # |1,0⟩ branch by e^{iφ}, then 50:50 BS maps |1,0⟩→(|1,0⟩−|0,1⟩)/√2 and
    # |0,1⟩→(|1,0⟩+|0,1⟩)/√2:
    #   amps[1,0] = (cosθ·e^{iφ} − sinθ)/√2
    #   amps[0,1] = −(cosθ·e^{iφ} + sinθ)/√2
    theta, phi = 0.6, 0.3
    out = mach_zehnder(FockState.fock2(1, 0, 10), 0, 1, theta, phi)
    e = np.exp(1j * phi)
    np.testing.assert_allclose(
        out.amps[1, 0], (np.cos(theta) * e - np.sin(theta)) / np.sqrt(2.0), atol=1e-12
    )
    np.testing.assert_allclose(
        out.amps[0, 1], -(np.cos(theta) * e + np.sin(theta)) / np.sqrt(2.0), atol=1e-12
    )


def test_mz_phi_zero_analytic_anchor() -> None:
    """φ=0 reduces to the real textbook form on |1,0⟩."""
    theta = 0.6
    out = mach_zehnder(FockState.fock2(1, 0, 10), 0, 1, theta, 0.0)
    np.testing.assert_allclose(
        out.amps[1, 0], (np.cos(theta) - np.sin(theta)) / np.sqrt(2.0), atol=1e-12
    )
    np.testing.assert_allclose(
        out.amps[0, 1], -(np.cos(theta) + np.sin(theta)) / np.sqrt(2.0), atol=1e-12
    )


def test_mz_requires_two_modes() -> None:
    with pytest.raises(ValueError):
        mach_zehnder(FockState.vacuum(8), 0, 1, 0.5)


def test_mz_arg_order_matches_gaussian_bosonic() -> None:
    """Signature lock: (state, mode1, mode2, theta, phi) across all three reps.

    fock's ``gates.mach_zehnder`` alone used to be ``(state, theta, phi, mode1,
    mode2)`` — same five names, different meaning for the middle three, so a
    positional cross-representation call silently transposed modes and angles
    (no exception, just a different gate). The vision table freezes
    ``m1, m2, theta, phi`` (docs/vision-gaussian-simulator.md:333).
    """
    import inspect

    from cvsim.bosonic.gates import mach_zehnder as b_mz
    from cvsim.gaussian.gates import mach_zehnder as g_mz

    fock_params = list(inspect.signature(mach_zehnder).parameters)
    assert fock_params == ["state", "mode1", "mode2", "theta", "phi"], fock_params
    for other in (g_mz, b_mz):
        assert list(inspect.signature(other).parameters) == fock_params, (
            f"{other.__module__} disagrees with fock on mach_zehnder argument order"
        )


# -- interferometer ---------------------------------------------------------


def test_interferometer_identity() -> None:
    st = FockState.fock2(2, 1, 8)
    np.testing.assert_allclose(interferometer(st, np.eye(2)).amps, st.amps, atol=1e-12)


def test_interferometer_matches_beamsplitter() -> None:
    theta, phi = 0.5, 0.2
    # expm(θ(e^{iφ}a0†a1 − e^{−iφ}a1†a0)) — beamsplitter convention
    U = np.array(
        [
            [np.cos(theta), np.exp(1j * phi) * np.sin(theta)],
            [-np.exp(-1j * phi) * np.sin(theta), np.cos(theta)],
        ]
    )
    st = FockState.fock2(1, 1, 10)
    np.testing.assert_allclose(
        interferometer(st, U).amps, beamsplitter(st, theta, phi).amps, atol=1e-9
    )


def test_interferometer_unitary_validation() -> None:
    st = FockState.vacuum(6, nmode=2)
    with pytest.raises(ValueError):
        interferometer(st, np.array([[1.0, 0.5], [0.0, 1.0]]))


# -- apply_unitary ----------------------------------------------------------


def test_apply_unitary_single_mode_matches_squeeze() -> None:
    from cvsim.fock.gates import _squeeze_U

    r = 0.5
    st = FockState.vacuum(10)
    out = apply_unitary(st, _squeeze_U(10, r))
    np.testing.assert_allclose(out.amps, squeeze(st, r).amps, atol=1e-12)


def test_apply_unitary_mode_selection() -> None:
    U = np.diag(np.exp(1j * np.arange(8)))  # phase gate matrix
    st = FockState.fock2(2, 3, 8)
    out1 = apply_unitary(st, U, modes=[1])
    expected = FockState.fock2(2, 3, 8)
    expected.amps[:, 3] *= np.exp(1j * 3)  # phase on mode 1
    np.testing.assert_allclose(out1.amps, expected.amps, atol=1e-12)


def test_apply_unitary_full_space() -> None:
    st = FockState.fock2(1, 0, 6)
    U = np.kron(np.diag(np.exp(1j * np.arange(6))), np.eye(6))
    out = apply_unitary(st, U)
    expected = FockState.fock2(1, 0, 6)
    expected.amps[1, 0] *= np.exp(1j)
    np.testing.assert_allclose(out.amps, expected.amps, atol=1e-12)


def test_interferometer_preserves_norm() -> None:
    st = FockState.fock2(2, 1, 8)
    theta, phi = 0.4, -0.7
    U = np.array(
        [
            [np.cos(theta), np.exp(1j * phi) * np.sin(theta)],
            [-np.exp(-1j * phi) * np.sin(theta), np.cos(theta)],
        ]
    )
    out = interferometer(st, U)
    np.testing.assert_allclose(np.sum(abs(out.amps) ** 2), np.sum(abs(st.amps) ** 2), atol=1e-12)


def test_apply_unitary_density_full_space() -> None:
    d = FockDensity.from_pure(FockState.fock2(1, 1, 6))
    U = np.kron(np.eye(6), np.diag(np.exp(1j * np.arange(6))))
    out = apply_unitary(d, U)
    np.testing.assert_allclose(np.trace(out.rho), np.trace(d.rho), atol=1e-12)
    np.testing.assert_allclose(out.rho, out.rho.conj().T, atol=1e-12)


def test_apply_unitary_density() -> None:
    d = FockDensity.thermal(6, 0.5)
    U = np.diag(np.exp(1j * np.arange(6)))
    out = apply_unitary(d, U)
    np.testing.assert_allclose(out.rho, d.rho, atol=1e-14)  # thermal is diagonal
