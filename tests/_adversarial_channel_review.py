"""Adversarial review tests for 07-29-phase1-channel-general.

Run: PYTHONPATH=. py -3 tests/_adversarial_channel_review.py
"""
from __future__ import annotations

import sys
import traceback

import numpy as np

from cvsim.conventions import omega
from cvsim.gaussian import (
    GaussianState,
    amplifier,
    apply_gaussian_channel,
    apply_symplectic,
    displace,
    is_cp_channel,
    loss,
    mean_photon,
    phase_noise,
    squeeze,
    validate_channel,
)
from cvsim.gaussian.analyse import is_physical
from cvsim.symplectic import S_phase, S_squeeze

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    # Encode safely for Windows terminals that default to gbk.
    try:
        detail.encode(sys.stdout.encoding or "utf-8")
        safe_detail = detail
    except UnicodeEncodeError:
        safe_detail = detail.encode("ascii", errors="replace").decode("ascii")
    print(f"[{status}] {name}" + (f" — {safe_detail}" if safe_detail else ""))


def assert_allclose(name: str, a, b, atol: float = 1e-10) -> None:
    a = np.asarray(a)
    b = np.asarray(b)
    ok = np.allclose(a, b, atol=atol)
    record(name, ok, f"max|diff|={norm(a-b):.3e}" if not ok else "")


def norm(a) -> float:
    return float(np.linalg.norm(np.asarray(a)))


def main() -> None:
    print("\n=== A. CP condition / math conventions ===")

    # A1: CP condition must use Omega/2 because V_vac = I/2.
    # Code's check passes for pure loss; bare-Omega formula would reject T<1.
    try:
        ok = True
        for T in np.linspace(0.0, 1.0, 11):
            X = np.sqrt(T) * np.eye(2)
            Y = (1 - T) * 0.5 * np.eye(2)
            if not is_cp_channel(X, Y):
                ok = False
                break
        record("A1 pure-loss family passes code CP check", ok)
    except Exception as e:
        record("A1 pure-loss family passes code CP check", False, traceback.format_exc()[:80])

    # A2: bare-Omega CP condition rejects valid pure loss (documentation drift)
    try:
        O = omega(1)
        bad_Ts = []
        for T in [0.0, 0.25, 0.5, 0.75]:
            X = np.sqrt(T) * np.eye(2)
            Y = (1 - T) * 0.5 * np.eye(2)
            H = Y + 1j * O - 1j * (X @ O @ X.T)
            w = np.linalg.eigvalsh(0.5 * (H + H.conj().T))
            if not np.any(w < -1e-6):
                bad_Ts.append(T)
        record("A2 bare-Omega formula rejects valid pure loss", len(bad_Ts) == 0,
               f"failed at T={bad_Ts}" if bad_Ts else "")
    except Exception as e:
        record("A2 bare-Omega formula rejects valid pure loss", False, traceback.format_exc()[:80])

    # A3: true non-CP channels rejected
    try:
        ok = (
            not is_cp_channel(1.5 * np.eye(2), np.zeros((2, 2)))
            and not is_cp_channel(2.0 * np.eye(2), np.zeros((2, 2)))
            and not is_cp_channel(np.eye(2), -0.1 * np.eye(2))
            and not is_cp_channel(np.eye(3), np.eye(3))  # odd dim
        )
        record("A3 non-CP channels rejected", ok)
    except Exception as e:
        record("A3 non-CP channels rejected", False, traceback.format_exc()[:80])

    # A4: validate_channel raises clear ValueError
    try:
        validate_channel(np.eye(2), -0.1 * np.eye(2))
        record("A4 validate_channel raises on non-CP", False, "no exception")
    except ValueError as e:
        record("A4 validate_channel raises on non-CP", "non-CP" in str(e), str(e)[:80])
    except Exception as e:
        record("A4 validate_channel raises on non-CP", False, traceback.format_exc()[:80])

    # A5: unitary channel X=S, Y=0 equals apply_symplectic
    try:
        st = GaussianState.displaced_squeezed(0.3 + 0.2j, r=0.4, phi=0.1)
        S = S_phase(1, 0.5)
        via = apply_gaussian_channel(st, S, np.zeros((2, 2)), validate=False)
        direct = apply_symplectic(st, S, validate=False)
        assert_allclose("A5 unitary via (X,Y) equals apply_symplectic V", via.V, direct.V)
        assert_allclose("A5 unitary via (X,Y) equals apply_symplectic rbar", via.rbar, direct.rbar)
    except Exception as e:
        record("A5 unitary via (X,Y) equals apply_symplectic", False, traceback.format_exc()[:80])

    print("\n=== B. Preset channels (loss / amplifier / phase_noise) ===")

    # B1: loss identity / vacuum limits
    try:
        st = displace(GaussianState.vacuum(1), 0.5 + 0.2j)
        id_st = loss(st, 1.0)
        vac_st = loss(GaussianState.vacuum(2), 0.0)
        ok = (
            np.allclose(id_st.V, st.V, atol=1e-12)
            and np.allclose(id_st.rbar, st.rbar, atol=1e-12)
            and np.allclose(vac_st.V, 0.5 * np.eye(4), atol=1e-12)
            and np.allclose(vac_st.rbar, 0.0, atol=1e-12)
        )
        record("B1 loss T=1 identity / T=0 vacuum", ok)
    except Exception as e:
        record("B1 loss T=1 identity / T=0 vacuum", False, traceback.format_exc()[:80])

    # B2: coherent photon number after loss
    try:
        alpha = 0.9 + 0.4j
        T = 0.35
        st = loss(displace(GaussianState.vacuum(1), alpha), T)
        ok = abs(mean_photon(st) - T * abs(alpha) ** 2) < 1e-12
        record("B2 loss coherent photon scales as T|alpha|^2", ok)
    except Exception as e:
        record("B2 loss coherent photon scales as T|alpha|^2", False, traceback.format_exc()[:80])

    # B3: thermal loss photon number
    try:
        alpha = 0.6 + 0.0j
        T, nbar = 0.4, 1.5
        st = loss(displace(GaussianState.vacuum(1), alpha), T, nbar=nbar)
        expected = T * abs(alpha) ** 2 + (1 - T) * nbar
        ok = abs(mean_photon(st) - expected) < 1e-12
        record("B3 thermal loss photon number", ok)
    except Exception as e:
        record("B3 thermal loss photon number", False, traceback.format_exc()[:80])

    # B4: single-mode loss leaves others untouched
    try:
        st = displace(GaussianState.vacuum(2), 0.7, mode=0)
        st = displace(st, 0.5, mode=1)
        out = loss(st, 0.2, mode=0)
        ok = (
            abs(out.rbar[1] - st.rbar[1]) < 1e-12
            and abs(out.rbar[3] - st.rbar[3]) < 1e-12
            and abs(out.rbar[0] - np.sqrt(0.2) * st.rbar[0]) < 1e-12
        )
        record("B4 single-mode loss leaves other mode", ok)
    except Exception as e:
        record("B4 single-mode loss leaves other mode", False, traceback.format_exc()[:80])

    # B5: amplifier identity at G=1 and photon trend
    try:
        alpha = 0.5 + 0.3j
        G = 2.0
        st = amplifier(displace(GaussianState.vacuum(1), alpha), G)
        ok = (
            np.allclose(amplifier(st, 1.0).V, st.V, atol=1e-12)
            and abs(mean_photon(st) - (G * abs(alpha) ** 2 + (G - 1))) < 1e-12
        )
        record("B5 amplifier identity and photon trend", ok)
    except Exception as e:
        record("B5 amplifier identity and photon trend", False, traceback.format_exc()[:80])

    # B6: amplifier thermal nbar
    try:
        G, nbar = 2.0, 1.0
        st = amplifier(GaussianState.vacuum(1), G, nbar=nbar)
        expected = 0.5 * G + (G - 1) * (nbar + 0.5) - 0.5
        ok = abs(mean_photon(st) - expected) < 1e-12
        record("B6 amplifier thermal nbar", ok)
    except Exception as e:
        record("B6 amplifier thermal nbar", False, traceback.format_exc()[:80])

    # B7: phase_noise sigma=0 identity and sigma>0 damps coherences
    try:
        st = GaussianState.squeezed(0.8, phi=0.3)
        id_ph = phase_noise(st, 0.0)
        damped = phase_noise(st, 0.5)
        ok = (
            np.allclose(id_ph.V, st.V, atol=1e-12)
            and abs(damped.V[0, 1]) < abs(st.V[0, 1])
            and damped.is_physical()
        )
        record("B7 phase_noise identity and coherence damping", ok)
    except Exception as e:
        record("B7 phase_noise identity and coherence damping", False, traceback.format_exc()[:80])

    # B8: phase_noise large sigma -> vacuum
    try:
        st = displace(GaussianState.vacuum(1), 0.5 + 0.2j)
        out = phase_noise(st, 5.0)
        ok = (
            np.allclose(out.V, 0.5 * np.eye(2), atol=1e-6)
            and np.allclose(out.rbar, 0.0, atol=1e-5)
        )
        record("B8 phase_noise large sigma -> vacuum", ok)
    except Exception as e:
        record("B8 phase_noise large sigma -> vacuum", False, traceback.format_exc()[:80])

    # B9: phase_noise rbar damping factor exp(-sigma^2/2)
    try:
        alpha = 1.0 + 0.3j
        sigma = 0.7
        st = displace(GaussianState.vacuum(1), alpha)
        out = phase_noise(st, sigma)
        damp = np.exp(-sigma ** 2 / 2.0)
        ok = np.allclose(out.rbar, damp * st.rbar, atol=1e-12)
        record("B9 phase_noise rbar damping factor", ok)
    except Exception as e:
        record("B9 phase_noise rbar damping factor", False, traceback.format_exc()[:80])

    print("\n=== C. Composition law ===")

    # C1: two general channels compose as X=X2X1, Y=X2Y1X2^T+Y2
    try:
        st = GaussianState.displaced_squeezed(0.4 + 0.1j, r=0.3, phi=0.2)
        X1 = np.sqrt(0.7) * np.eye(2)
        Y1 = (1 - 0.7) * 0.5 * np.eye(2)
        X2 = np.sqrt(0.5) * np.eye(2)
        Y2 = (1 - 0.5) * 0.5 * np.eye(2)
        seq = apply_gaussian_channel(
            apply_gaussian_channel(st, X1, Y1, validate=False), X2, Y2, validate=False
        )
        X = X2 @ X1
        Y = X2 @ Y1 @ X2.T + Y2
        one = apply_gaussian_channel(st, X, Y, validate=False)
        assert_allclose("C1 composition law V", seq.V, one.V)
        assert_allclose("C1 composition law rbar", seq.rbar, one.rbar)
    except Exception as e:
        record("C1 composition law", False, traceback.format_exc()[:80])

    # C2: loss then amplifier compose to correct (X,Y)
    try:
        st = displace(GaussianState.vacuum(1), 0.6)
        T, G = 0.6, 2.0
        seq = amplifier(loss(st, T), G)
        X = np.sqrt(G * T) * np.eye(2)
        Y = (G * (1 - T) / 2 + (G - 1) / 2) * np.eye(2)
        one = apply_gaussian_channel(st, X, Y, validate=False)
        assert_allclose("C2 loss+amplifier compose V", seq.V, one.V)
        assert_allclose("C2 loss+amplifier compose rbar", seq.rbar, one.rbar)
    except Exception as e:
        record("C2 loss+amplifier compose", False, traceback.format_exc()[:80])

    # C3: thermal loss then thermal amplifier compose
    try:
        st = displace(GaussianState.vacuum(1), 0.6 + 0.2j)
        T, G, nbar_loss, nbar_amp = 0.4, 2.5, 0.3, 0.1
        seq = amplifier(loss(st, T, nbar=nbar_loss), G, nbar=nbar_amp)
        X = np.sqrt(G * T) * np.eye(2)
        Y = (
            G * (1 - T) * (nbar_loss + 0.5)
            + (G - 1) * (nbar_amp + 0.5)
        ) * np.eye(2)
        one = apply_gaussian_channel(st, X, Y, validate=False)
        assert_allclose("C3 thermal loss+amplifier compose V", seq.V, one.V)
        assert_allclose("C3 thermal loss+amplifier compose rbar", seq.rbar, one.rbar)
    except Exception as e:
        record("C3 thermal loss+amplifier compose", False, traceback.format_exc()[:80])

    print("\n=== D. API robustness / trust boundaries ===")

    # D1: validate=True rejects non-CP
    try:
        apply_gaussian_channel(GaussianState.vacuum(1), 2.0 * np.eye(2), np.zeros((2, 2)))
        record("D1 validate=True rejects non-CP", False, "no exception")
    except ValueError:
        record("D1 validate=True rejects non-CP", True)
    except Exception as e:
        record("D1 validate=True rejects non-CP", False, traceback.format_exc()[:80])

    # D2: validate=False escape hatch
    try:
        out = apply_gaussian_channel(
            GaussianState.vacuum(1), 2.0 * np.eye(2), np.zeros((2, 2)), validate=False
        )
        record("D2 validate=False escape hatch", out.nmode == 1)
    except Exception as e:
        record("D2 validate=False escape hatch", False, traceback.format_exc()[:80])

    # D3: shape mismatches raise
    try:
        st = GaussianState.vacuum(2)
        apply_gaussian_channel(st, np.eye(2), np.zeros((4, 4)), validate=False)
        record("D3 shape mismatch raises", False, "no exception")
    except ValueError:
        record("D3 shape mismatch raises", True)
    except Exception as e:
        record("D3 shape mismatch raises", False, traceback.format_exc()[:80])

    # D4: bad parameter rejection
    try:
        st = GaussianState.vacuum(1)
        ok = False
        for bad in [
            lambda: loss(st, 1.5),
            lambda: loss(st, -0.1),
            lambda: loss(st, 0.5, nbar=-1.0),
            lambda: amplifier(st, 0.5),
            lambda: amplifier(st, 2.0, nbar=-0.1),
            lambda: phase_noise(st, -0.1),
            lambda: loss(st, 0.5, mode=5),
        ]:
            try:
                bad()
            except (ValueError, IndexError):
                pass
            else:
                raise RuntimeError(f"bad param not rejected: {bad}")
        ok = True
        record("D4 bad parameter rejection", ok)
    except Exception as e:
        record("D4 bad parameter rejection", False, traceback.format_exc()[:80])

    print("\n=== E. Multi-mode / physicality ===")

    # E1: all-mode default equals acting on every mode
    try:
        st = GaussianState.coherent(1.0 + 0.5j, nmode=3, mode=1)
        a = loss(st, 0.5)
        b = loss(st, 0.5, mode=None)
        assert_allclose("E1 loss mode=None == all modes V", a.V, b.V)
        assert_allclose("E1 loss mode=None == all modes rbar", a.rbar, b.rbar)
    except Exception as e:
        record("E1 loss mode=None == all modes", False, traceback.format_exc()[:80])

    # E2: single-mode channel leaves unacted block
    try:
        st = GaussianState.coherent(1.0 + 0.0j, nmode=2, mode=0)
        st = displace(st, 0.5 + 0.2j, mode=1)
        out = loss(st, 0.3, mode=0)
        ok = (
            np.allclose(out.rbar[1], st.rbar[1], atol=1e-12)
            and np.allclose(out.rbar[3], st.rbar[3], atol=1e-12)
            and np.allclose(
                out.V[np.ix_([1, 3], [1, 3])], st.V[np.ix_([1, 3], [1, 3])], atol=1e-12
            )
        )
        record("E2 single-mode channel leaves other block", ok)
    except Exception as e:
        record("E2 single-mode channel leaves other block", False, traceback.format_exc()[:80])

    # E3: correlated Y (full 2m) CP and physical
    try:
        st = GaussianState.vacuum(2)
        X = np.eye(4) * 0.9
        Y = np.eye(4) * 0.095  # pure loss T=0.81
        out = apply_gaussian_channel(st, X, Y, validate=True)
        record("E3 correlated CP channel physical", out.is_physical())
    except Exception as e:
        record("E3 correlated CP channel physical", False, traceback.format_exc()[:80])

    # E4: large amplifier numerical stability
    try:
        G = 1e6
        out = amplifier(GaussianState.vacuum(1), G)
        ok = out.is_physical(atol=1e-8) and abs(out.V[0, 0] - (G - 0.5)) < 1e-6
        record("E4 large amplifier numerical stability", ok)
    except Exception as e:
        record("E4 large amplifier numerical stability", False, traceback.format_exc()[:80])

    print("\n=== F. Documentation / spec drift ===")

    # F1: apply_gaussian_channel docstring uses bare Omega formula (incorrect)
    try:
        import cvsim.gaussian.channels as ch
        ok = "Y + iΩ/2" in ch.apply_gaussian_channel.__doc__ or "Y + i\\Omega/2" in ch.apply_gaussian_channel.__doc__
        # A correct docstring would contain Omega/2; current docstring is known to contain bare Omega.
        record("F1 docstring states correct Omega/2 CP formula", ok)
    except Exception as e:
        record("F1 docstring states correct Omega/2 CP formula", False, traceback.format_exc()[:80])

    print("\n=== Summary ===")
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"TOTAL: {passed} PASS, {total - passed} FAIL / {total}")
    failures = [(name, detail) for name, ok, detail in results if not ok]
    if failures:
        print("\nFailures:")
        for name, detail in failures:
            print(f"  - {name}: {detail}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
