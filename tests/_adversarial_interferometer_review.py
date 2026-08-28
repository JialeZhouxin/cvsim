"""Adversarial review tests for 07-29-phase1-interferometer-gates.

Run: py -3 tests/_adversarial_interferometer_review.py
"""

from __future__ import annotations

import traceback

import numpy as np
from numpy.linalg import det, norm

from cvsim.gaussian import (
    GaussianState,
    apply_interferometer,
    apply_mesh,
    beamsplitter,
    det_cov,
    displace,
    fourier,
    interferometer,
    mach_zehnder,
    mean_photon,
    phase,
    squeeze,
)
from cvsim.gaussian.analyse import is_physical
from cvsim.symplectic import (
    S_beamsplitter,
    S_from_unitary,
    S_mach_zehnder,
    S_phase,
    U_beamsplitter,
    compose_unitary_mesh,
    embed_U_2mode,
    is_symplectic,
    reck_decomposition,
)

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def haar(m: int, rng: np.random.Generator) -> np.ndarray:
    z = rng.normal(size=(m, m)) + 1j * rng.normal(size=(m, m))
    q, r = np.linalg.qr(z)
    d = np.diag(r)
    return q * (d / np.abs(d))


def main() -> None:
    print("\n=== A. Math / conventions ===")

    # A1: det(S)=+1 for unitary embed (passive Sp)
    try:
        rng = np.random.default_rng(42)
        ok_all = True
        dets = []
        for m in [1, 2, 3, 5, 7]:
            for _ in range(10):
                U = haar(m, rng) if m > 1 else np.array([[np.exp(1j * rng.uniform(0, 2 * np.pi))]])
                S = S_from_unitary(U)
                d = float(det(S))
                dets.append(d)
                if abs(d - 1.0) > 1e-8:
                    ok_all = False
        record(
            "A1 det(S)=+1 for S_from_unitary",
            ok_all,
            f"det range [{min(dets):.6g},{max(dets):.6g}]",
        )
    except Exception as e:
        record("A1 det(S)=+1", False, str(e))

    # A2: homomorphism S(U2 U1) = S(U2) S(U1)
    try:
        rng = np.random.default_rng(7)
        ok = True
        maxerr = 0.0
        for m in [2, 3, 4]:
            for _ in range(8):
                U1, U2 = haar(m, rng), haar(m, rng)
                S_prod = S_from_unitary(U2 @ U1)
                S_comp = S_from_unitary(U2) @ S_from_unitary(U1)
                err = float(norm(S_prod - S_comp))
                maxerr = max(maxerr, err)
                if err > 1e-10:
                    ok = False
        record("A2 S(U2U1)=S(U2)S(U1) homomorphism", ok, f"max||err||={maxerr:.3e}")
    except Exception as e:
        record("A2 homomorphism", False, str(e))

    # A3: S(U†)=S^{-1} and passive S orthogonal
    try:
        rng = np.random.default_rng(9)
        ok = True
        maxerr = 0.0
        for m in [2, 4]:
            U = haar(m, rng)
            S = S_from_unitary(U)
            Sinv_via_U = S_from_unitary(U.conj().T)
            Sinv = np.linalg.inv(S)
            e1 = float(norm(Sinv_via_U - Sinv))
            e2 = float(norm(S.T @ S - np.eye(2 * m)))
            maxerr = max(maxerr, e1, e2)
            if e1 > 1e-10 or e2 > 1e-10:
                ok = False
        record(
            "A3 S(U^dag)=S^{-1} and S orthogonal (passive)",
            ok,
            f"maxerr={maxerr:.3e}",
        )
    except Exception as e:
        record("A3 inverse/orthogonal", False, str(e))

    # A4: vacuum invariance
    try:
        rng = np.random.default_rng(11)
        ok = True
        for m in [1, 2, 3, 6]:
            U = haar(m, rng) if m > 1 else np.array([[np.exp(1j * 0.3)]])
            st = interferometer(GaussianState.vacuum(m), U)
            if not np.allclose(st.V, 0.5 * np.eye(2 * m), atol=1e-12):
                ok = False
            if not np.allclose(st.rbar, 0, atol=1e-12):
                ok = False
        record("A4 vacuum fixed by passive U", ok)
    except Exception as e:
        record("A4 vacuum fixed", False, str(e))

    # A5: total mean photon conserved
    try:
        rng = np.random.default_rng(13)
        ok = True
        maxdiff = 0.0
        for m in [2, 3, 4]:
            st = GaussianState.vacuum(m)
            for i in range(m):
                st = squeeze(st, 0.2 * (i + 1), mode=i)
                st = displace(st, 0.1 + 0.05j * (i + 1), mode=i)
            n_before = sum(mean_photon(st, mode=i) for i in range(m))
            U = haar(m, rng)
            st2 = interferometer(st, U)
            n_after = sum(mean_photon(st2, mode=i) for i in range(m))
            maxdiff = max(maxdiff, abs(n_before - n_after))
            if abs(n_before - n_after) > 1e-9:
                ok = False
            if not is_physical(st2):
                ok = False
        record(
            "A5 total <n> conserved under interferometer",
            ok,
            f"max|Δn|={maxdiff:.3e}",
        )
    except Exception as e:
        record("A5 photon conservation", False, traceback.format_exc(limit=2))

    # A6: Fourier quadrature map (x,p)->(-p,x)
    try:
        alpha = 0.7 + 0.4j
        st = displace(GaussianState.vacuum(1), alpha)
        stf = fourier(st)
        x, p = st.rbar
        exp = np.array([-p, x])
        ok = np.allclose(stf.rbar, exp, atol=1e-12)
        record("A6 fourier maps (x,p)->(-p,x)", ok, f"rbar={stf.rbar}, exp={exp}")
    except Exception as e:
        record("A6 fourier quadrature map", False, str(e))

    # A7: fourier^2 central inversion
    try:
        st = displace(GaussianState.vacuum(1), 0.5 - 0.3j)
        st2 = fourier(fourier(st))
        ok = np.allclose(st2.rbar, -st.rbar, atol=1e-12)
        record("A7 fourier^2 = central inversion", ok, f"rbar={st2.rbar}")
    except Exception as e:
        record("A7 fourier^2", False, str(e))

    print("\n=== B. Decomposition ===")

    # B1: diagonal phases
    try:
        ok = True
        for m in [2, 3, 4]:
            phases = np.exp(1j * np.linspace(0.1, 1.7, m))
            U = np.diag(phases)
            ops = reck_decomposition(U)
            U2 = compose_unitary_mesh(m, ops)
            if norm(U2 - U) > 1e-9:
                ok = False
        record("B1 diagonal phase unitary roundtrip", ok)
    except Exception as e:
        record("B1 diagonal", False, str(e))

    # B2: extreme BS
    try:
        U = U_beamsplitter(np.pi / 2, 0)
        ops = reck_decomposition(U)
        U2 = compose_unitary_mesh(2, ops)
        record(
            "B2 extreme BS theta=pi/2 roundtrip",
            norm(U2 - U) < 1e-9,
            f"err={norm(U2 - U):.3e}, nops={len(ops)}",
        )
    except Exception as e:
        record("B2 extreme BS", False, str(e))

    # B3: many Haar roundtrips + mesh
    try:
        rng = np.random.default_rng(21)
        ok = True
        maxerr = 0.0
        worst = None
        for m in [3, 4, 6, 8]:
            for trial in range(20):
                U = haar(m, rng)
                ops = reck_decomposition(U)
                U2 = compose_unitary_mesh(m, ops)
                err = float(norm(U2 - U))
                maxerr = max(maxerr, err)
                if err > 1e-7:
                    ok = False
                    worst = (m, trial, err)
                st0 = squeeze(GaussianState.vacuum(m), 0.55, mode=0)
                st0 = displace(st0, 0.2 + 0.1j, mode=1 if m > 1 else 0)
                a = interferometer(st0, U)
                b = apply_mesh(st0, ops)
                if not (
                    np.allclose(a.V, b.V, atol=1e-8) and np.allclose(a.rbar, b.rbar, atol=1e-8)
                ):
                    ok = False
                    worst = (m, trial, "mesh mismatch", float(norm(a.V - b.V)))
        record(
            "B3 many Haar roundtrip+mesh m<=8",
            ok,
            f"max Frobenius err={maxerr:.3e}; worst={worst}",
        )
    except Exception as e:
        record("B3 many Haar", False, traceback.format_exc(limit=3))

    # B5: non-unitary rejected
    try:
        raised = False
        try:
            reck_decomposition(np.array([[1.0, 2.0], [0.0, 1.0]], dtype=complex))
        except ValueError:
            raised = True
        record("B5 reck rejects non-unitary", raised)
    except Exception as e:
        record("B5", False, str(e))

    # B6: m=1
    try:
        U = np.array([[np.exp(1j * 1.234)]], dtype=complex)
        ops = reck_decomposition(U)
        U2 = compose_unitary_mesh(1, ops)
        record(
            "B6 m=1 phase-only decomposition",
            norm(U2 - U) < 1e-12,
            f"ops={ops}, err={norm(U2 - U):.3e}",
        )
    except Exception as e:
        record("B6 m=1", False, str(e))

    print("\n=== C. API robustness ===")

    # C1: almost unitary
    try:
        rng = np.random.default_rng(3)
        U = haar(4, rng)
        U_noisy = U + 1e-12 * rng.normal(size=U.shape) + 1e-12j * rng.normal(size=U.shape)
        try:
            S = S_from_unitary(U_noisy)
            ok_pass = is_symplectic(S)
            record("C1 almost-unitary 1e-12 accepted", ok_pass, "accepted")
        except ValueError as e:
            record("C1 almost-unitary 1e-12 accepted", False, f"rejected: {e}")
        U_bad = U + 1e-4 * rng.normal(size=U.shape)
        try:
            S_from_unitary(U_bad)
            record("C1b clearly non-unitary 1e-4 rejected", False, "incorrectly accepted")
        except ValueError:
            record("C1b clearly non-unitary 1e-4 rejected", True)
    except Exception as e:
        record("C1", False, str(e))

    # C2: validate_u=False escape hatch
    try:
        U = np.array([[1.0, 0.5], [0.0, 1.0]], dtype=complex)
        S = S_from_unitary(U, validate=False)
        sym = is_symplectic(S)
        st = interferometer(GaussianState.vacuum(2), U, validate_u=False)
        record(
            "C2 validate_u=False allows non-unitary (escape hatch)",
            True,
            f"is_symplectic={sym}, detV={det(st.V):.6g}",
        )
    except Exception as e:
        record("C2 validate_u=False", False, str(e))

    # C3: rectangular
    try:
        raised = False
        try:
            S_from_unitary(np.ones((2, 3), dtype=complex))
        except ValueError:
            raised = True
        record("C3 rectangular U rejected", raised)
    except Exception as e:
        record("C3", False, str(e))

    # C4: mode errors
    try:
        st = GaussianState.vacuum(2)
        r1 = r2 = r3 = False
        try:
            fourier(st, mode=2)
        except Exception:
            r1 = True
        try:
            mach_zehnder(st, 0, 0, 0.1, 0.2)
        except Exception:
            r2 = True
        try:
            mach_zehnder(st, 0, 5, 0.1, 0.2)
            r3 = False
        except Exception:
            r3 = True
        record(
            "C4 mode errors raise",
            r1 and r2 and r3,
            f"fourier_oor={r1}, mz_same={r2}, mz_oor={r3}",
        )
    except Exception as e:
        record("C4 mode errors", False, str(e))

    # C5: real orthogonal U
    try:
        th = 0.3
        U = np.array([[np.cos(th), np.sin(th)], [-np.sin(th), np.cos(th)]], dtype=float)
        S = S_from_unitary(U)
        ok = is_symplectic(S)
        st = interferometer(GaussianState.squeezed(0.4, nmode=2), U)
        record("C5 real orthogonal U accepted", ok and is_physical(st))
    except Exception as e:
        record("C5 real U", False, str(e))

    # C6: unknown mesh op
    try:
        raised = False
        try:
            apply_mesh(GaussianState.vacuum(2), [("nope",)])
        except ValueError:
            raised = True
        record("C6 apply_mesh unknown op raises", raised)
    except Exception as e:
        record("C6", False, str(e))

    # C7: alias
    try:
        record(
            "C7 apply_interferometer is interferometer",
            apply_interferometer is interferometer,
        )
    except Exception as e:
        record("C7", False, str(e))

    print("\n=== D. Gate semantics ===")

    # D1: MZ documented path vs vision wording
    try:
        st = squeeze(GaussianState.vacuum(2), 0.4, 0)
        theta, phi = 0.4, 0.6
        impl = mach_zehnder(st, 0, 1, theta, phi)
        man = beamsplitter(st, 0, 1, theta, 0)
        man = phase(man, phi, 0)
        man = beamsplitter(man, 0, 1, np.pi / 4, 0)
        match_doc = np.allclose(impl.V, man.V)
        tb = beamsplitter(st, 0, 1, np.pi / 4, 0)
        tb = phase(tb, phi, 0)
        tb = beamsplitter(tb, 0, 1, np.pi / 4, 0)
        match_textbook50 = np.allclose(impl.V, tb.V)
        record(
            "D1 MZ matches documented BS(θ)·R(φ)·BS(π/4)",
            match_doc,
            f"match_textbook_50_50={match_textbook50}; vision text says phase·BS·phase·BS vs code",
        )
    except Exception as e:
        record("D1 MZ semantics", False, str(e))

    # D2: special case
    try:
        st = displace(squeeze(GaussianState.vacuum(2), 0.5, 0), 0.3 + 0.2j, 0)
        mz = mach_zehnder(st, 0, 1, np.pi / 4, 0)
        man = beamsplitter(beamsplitter(st, 0, 1, np.pi / 4), 0, 1, np.pi / 4)
        record(
            "D2 MZ(θ=π/4,φ=0)=BS50^2",
            np.allclose(mz.V, man.V) and np.allclose(mz.rbar, man.rbar),
        )
    except Exception as e:
        record("D2 MZ special", False, str(e))

    # D3: multi-mode fourier isolation
    try:
        st = GaussianState.vacuum(3)
        st = displace(st, 1 + 0j, 0)
        st = displace(st, 0 + 1j, 1)
        st = displace(st, 0.5 + 0.5j, 2)
        st2 = fourier(st, mode=1)
        ok = np.allclose(st2.rbar[0], st.rbar[0]) and np.allclose(st2.rbar[2], st.rbar[2])
        x1, p1 = st.rbar[1], st.rbar[1 + 3]
        ok = ok and np.allclose(st2.rbar[1], -p1) and np.allclose(st2.rbar[1 + 3], x1)
        record("D3 fourier acts only on target mode", ok, f"rbar={st2.rbar}")
    except Exception as e:
        record("D3 multi-mode fourier", False, str(e))

    # D4: S_mach_zehnder composition order (matrix right-to-left)
    try:
        S = S_mach_zehnder(2, 0, 1, 0.31, 0.77)
        S1 = S_beamsplitter(2, 0, 1, 0.31, 0.0)
        S2 = S_phase(2, 0.77, 0)
        S3 = S_beamsplitter(2, 0, 1, np.pi / 4, 0.0)
        ok = np.allclose(S, S3 @ S2 @ S1)
        record("D4 S_mach_zehnder matrix order S3@S2@S1", ok)
    except Exception as e:
        record("D4 MZ matrix order", False, str(e))

    print("\n=== E. Physical stress ===")

    # E1: m=16
    try:
        rng = np.random.default_rng(99)
        m = 16
        U = haar(m, rng)
        S = S_from_unitary(U)
        ok_s = is_symplectic(S, atol=1e-7)
        st = GaussianState.vacuum(m)
        for i in range(0, m, 3):
            st = squeeze(st, 0.3, i)
        st2 = interferometer(st, U)
        ok_p = is_physical(st2)
        d0, d1 = det_cov(st), det_cov(st2)
        record(
            "E1 m=16 Haar interferometer physical",
            ok_s and ok_p and abs(d0 - d1) < 1e-8,
            f"det before/after={d0:.6e}/{d1:.6e}",
        )
    except Exception as e:
        record("E1 m=16", False, traceback.format_exc(limit=2))

    # E2: many random U purity
    try:
        rng = np.random.default_rng(101)
        m = 4
        st = squeeze(GaussianState.vacuum(m), 0.8, 0)
        d0 = det_cov(st)
        for _ in range(20):
            st = interferometer(st, haar(m, rng))
        d1 = det_cov(st)
        record(
            "E2 20x random U purity preserved",
            abs(d0 - d1) < 1e-8 and is_physical(st),
            f"det {d0} -> {d1}",
        )
    except Exception as e:
        record("E2", False, str(e))

    # E3: TMSV + BS photon balance
    try:
        r = 0.7
        st = GaussianState.tmsv(r)
        st = interferometer(st, U_beamsplitter(np.pi / 4, 0.0))
        n0, n1 = mean_photon(st, 0), mean_photon(st, 1)
        record(
            "E3 TMSV+BS50 photon balance",
            abs(n0 - n1) < 1e-10,
            f"n0={n0:.6f}, n1={n1:.6f}",
        )
    except Exception as e:
        record("E3 TMSV", False, str(e))

    # E4: block formula
    try:
        rng = np.random.default_rng(5)
        U = haar(3, rng)
        Ru, Iu = np.real(U), np.imag(U)
        S_ref = np.block([[Ru, -Iu], [Iu, Ru]])
        S = S_from_unitary(U)
        record("E4 block formula exact", np.allclose(S, S_ref))
    except Exception as e:
        record("E4", False, str(e))

    print("\n=== F. Exports ===")
    try:
        import cvsim.gaussian as g
        import cvsim.symplectic as syn

        need_s = [
            "S_from_unitary",
            "is_unitary",
            "validate_unitary",
            "reck_decomposition",
            "compose_unitary_mesh",
            "S_mach_zehnder",
            "U_beamsplitter",
            "embed_U_2mode",
        ]
        need_g = [
            "interferometer",
            "apply_interferometer",
            "fourier",
            "mach_zehnder",
            "apply_mesh",
        ]
        miss_s = [n for n in need_s if not hasattr(syn, n)]
        miss_g = [n for n in need_g if not hasattr(g, n)]
        record(
            "F1 required exports present",
            not miss_s and not miss_g,
            f"miss_s={miss_s}, miss_g={miss_g}",
        )
        has_in_g = hasattr(g, "S_from_unitary")
        record(
            "F2 S_from_unitary on cvsim.gaussian (optional)",
            True,
            f"present={has_in_g} (symplectic package is enough per vision)",
        )
    except Exception as e:
        record("F exports", False, str(e))

    print("\n=== G. Bug hunts ===")

    # G1: reck residual
    try:
        rng = np.random.default_rng(77)
        ok = True
        max_off = 0.0
        for m in [5, 7]:
            U = haar(m, rng)
            ops = reck_decomposition(U)
            err = float(norm(compose_unitary_mesh(m, ops) - U))
            max_off = max(max_off, err)
            if err > 1e-8:
                ok = False
        record("G1 reck residual m=5,7", ok, f"maxerr={max_off:.3e}")
    except Exception as e:
        record("G1", False, str(e))

    # G3: phase convention range
    try:
        ok = True
        for th in [0.0, 0.1, np.pi / 2, np.pi, 2.3, -0.8]:
            U = np.array([[np.exp(1j * th)]], dtype=complex)
            if not np.allclose(S_from_unitary(U), S_phase(1, th, 0), atol=1e-12):
                ok = False
        record("G3 phase convention full range", ok)
    except Exception as e:
        record("G3", False, str(e))

    # G4: BS embed isolates third mode
    try:
        S = S_beamsplitter(3, 0, 2, 0.4, 0.2)
        ok = np.allclose(S[1, :], np.eye(6)[1]) and np.allclose(S[4, :], np.eye(6)[4])
        U = embed_U_2mode(3, 0, 2, U_beamsplitter(0.4, 0.2))
        S2 = S_from_unitary(U)
        ok = ok and np.allclose(S, S2)
        record("G4 BS embed isolates third mode", ok)
    except Exception as e:
        record("G4", False, str(e))

    # G5: apply_mesh bs/phase path
    try:
        ops = [("bs", 0, 1, 0.3, 0.1), ("phase", 0, 0.5), ("bs", 0, 1, np.pi / 4, 0.0)]
        m = 2
        U = compose_unitary_mesh(m, ops)
        st0 = squeeze(GaussianState.vacuum(2), 0.45, 0)
        a = apply_mesh(st0, ops)
        b = interferometer(st0, U)
        record(
            "G5 apply_mesh bs/phase path == interferometer(compose)",
            np.allclose(a.V, b.V, atol=1e-10),
        )
    except Exception as e:
        record("G5", False, str(e))

    # G6: global phase note
    try:
        rng = np.random.default_rng(1)
        U = haar(3, rng)
        U2 = np.exp(1j * 0.91) * U
        st = squeeze(displace(GaussianState.vacuum(3), 0.4 + 0.2j, 1), 0.3, 0)
        a = interferometer(st, U)
        b = interferometer(st, U2)
        same = np.allclose(a.V, b.V, atol=1e-10) and np.allclose(a.rbar, b.rbar, atol=1e-10)
        record(
            "G6 global phase e^{iφ}U vs U on Gaussian",
            True,
            f"states_identical={same} "
            "(expected False: collective phase is physical in mode picture)",
        )
    except Exception as e:
        record("G6", False, str(e))

    # G7: dtype
    try:
        S = S_from_unitary(haar(2, np.random.default_rng(0)))
        record(
            "G7 S dtype float",
            np.issubdtype(S.dtype, np.floating),
            f"dtype={S.dtype}",
        )
    except Exception as e:
        record("G7", False, str(e))

    # G8: det(S) for det(U)=-1 style (special unitary vs U(m))
    try:
        # U with det -1 (still unitary): diag(1,...,-1)
        U = np.diag([1.0, 1.0, -1.0]).astype(complex)
        S = S_from_unitary(U)
        d = float(det(S))
        # Sp(2m) has det +1 always for connected component; real orthogonal with
        # det U=-1 still gives det S=+1 because of block structure
        record("G8 det(S) for det(U)=-1", abs(d - 1.0) < 1e-10, f"detS={d:.6g}")
    except Exception as e:
        record("G8", False, str(e))

    # G9: compose order documentation vs apply
    try:
        # If ops = [Op1, Op2], U should be Op2@Op1 and state apply Op1 then Op2
        th1, th2 = 0.2, 0.35
        ops = [("phase", 0, th1), ("phase", 0, th2)]
        U = compose_unitary_mesh(1, ops)
        U_exp = np.array([[np.exp(1j * (th1 + th2))]])
        st = displace(GaussianState.vacuum(1), 0.5)
        via_mesh = apply_mesh(st, ops)
        via_phase = phase(phase(st, th1), th2)
        ok = norm(U - U_exp) < 1e-12 and np.allclose(via_mesh.rbar, via_phase.rbar)
        record("G9 compose/apply order consistency", ok, f"U={U}")
    except Exception as e:
        record("G9", False, str(e))

    # Summary
    print("\n" + "=" * 60)
    npass = sum(1 for _, ok, _ in results if ok)
    nfail = sum(1 for _, ok, _ in results if not ok)
    print(f"TOTAL: {npass} PASS, {nfail} FAIL / {len(results)}")
    print("=" * 60)
    for name, ok, detail in results:
        if not ok:
            print(f"  FAIL: {name} :: {detail}")

    # Also print notes for review (non-fail findings)
    print("\n=== Non-fail observations ===")
    for name, ok, detail in results:
        if ok and detail:
            print(f"  NOTE: {name} :: {detail}")


if __name__ == "__main__":
    main()
