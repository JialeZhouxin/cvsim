"""ADR-0012 Phase-0 probe: pin the Gaussian-to-Fock component kernel.

Kernel route (Bloch-Messiah-lite, all atoms exact):
  1. V2 = 2V must be SPD and symplectic (V2 Om V2 = Om) — purity gate.
  2. C = sqrtm(V2) (symmetric root);  eigh(C) -> (lam, Q).
  3. Squeeze params: anti-squeezed eigenvalues lam > 1 (m of them),
     r_k = ln lam_k.  Partner of q is Om q (eigenvalue 1/lam).
  4. Passive O_1: columns (x_k <- q_k, p_k <- Om q_k) for the pairing of
     anti-eigenvectors to mode slots that makes O_1 orthogonal-symplectic
     and O_1 diag(lam^2) O_1^T = V2  (finite permutation search, pinned).
  5. Fock lift:  |psi> = U_passive * prod_k S_k(r_k) |0>,
       S_k     = expm(0.5 r_k (a_k^2 - a_k^dag^2))   (per-mode expm)
       U_pass  = expm(a^dag A a),  A = logm(U_O),  U_O from O_1 blocks
                 (X -/+ iY sign pinned by gold)
     on (N+pad)^m ladder space (pad absorbs truncation; squeeze expm is
     nilpotent-exact anyway).
  6. Displacement chain per mode (canonical D(gamma)), truncate, normalize.
  rho_k = w |psi><psi|.

Golds: bridge closed forms (coherent/squeezed/thermal_diag), fock-native gate
chains (squeeze/phase/two-mode-squeeze/beamsplitter), exact TMSV coefficients,
the end-to-end heralding preview (TMSV -> kernel -> fock pnr_condition), the
even-cat complex-r̄ operand assembly (Schrödinger split vs fock cat gold), and
mixed-component spectral route (p_n diagonal + purity vs bosonic analytic).
Exit 0 = pinned + validated.
"""

import itertools
import math

import numpy as np
from scipy.linalg import expm, logm, sqrtm

from cvsim.bridge import coherent_element, squeezed_element, thermal_diag
from cvsim.bosonic.analyse import purity as bosonic_purity
from cvsim.bosonic.cat import even_cat
from cvsim.bosonic.state import BosonicState, Component
from cvsim.fock.density import FockDensity
from cvsim.fock.gates import beamsplitter as f_bs
from cvsim.fock.gates import displace as f_displace
from cvsim.fock.gates import phase as f_phase
from cvsim.fock.gates import squeeze as f_squeeze
from cvsim.fock.gates import two_mode_squeeze as f_tmsv
from cvsim.fock.observables import pnr_condition as fock_pnr
from cvsim.fock.state import FockState

TOL = 1e-7
LOOSE = 3e-2  # fock-gate golds at small cutoff carry their own expm artifacts


def _ladder(N: int) -> np.ndarray:
    a = np.zeros((N, N), dtype=complex)
    for n in range(1, N):
        a[n - 1, n] = np.sqrt(n)
    return a


def _omega(m: int) -> np.ndarray:
    Om = np.zeros((2 * m, 2 * m))
    Om[:m, m:] = np.eye(m)
    Om[m:, :m] = -np.eye(m)
    return Om


def _embed(op: np.ndarray, k: int, m: int, Np: int) -> np.ndarray:
    mats = [np.eye(Np, dtype=complex)] * m
    mats[k] = op
    out = mats[0]
    for extra in mats[1:]:
        out = np.kron(out, extra)
    return out


def kernel_psi(V: np.ndarray, rbar: np.ndarray, N: int, pad: int = 24,
               uo_sign: int = -1) -> np.ndarray:
    """Truncated Fock state vector of one pure Gaussian component."""
    m = V.shape[0] // 2
    if m not in (1, 2):
        raise ValueError("kernel probe supports m in {1,2}")
    V2 = np.asarray(V, dtype=float) * 2.0
    Om = _omega(m)
    if not np.allclose(V2 @ Om @ V2, Om, atol=1e-8):
        raise ValueError("V2 is not symplectic (mixed component?)")
    C = np.real(sqrtm(V2))
    lam, Q = np.linalg.eigh(C)
    order = np.argsort(lam)
    squ = order[:m]  # m smallest: squeeze directions (fock S(+r): x squeezed)
    r = -np.log(lam[squ])  # >= 0

    # passive O_1 via pairing search
    O1 = None
    for perm in itertools.permutations(range(m)):
        cols = np.zeros((2 * m, 2 * m))
        for slot, eig_idx in enumerate(perm):
            q = Q[:, squ[eig_idx]]  # squeezed direction -> x slot
            cols[:, slot] = q
            cols[:, m + slot] = -Om @ q  # anti-squeezed partner -> p slot
        if not np.allclose(cols.T @ cols, np.eye(2 * m), atol=1e-8):
            continue
        if not np.allclose(cols.T @ Om @ cols, Om, atol=1e-8):
            continue
        R2 = np.zeros((2 * m, 2 * m))
        for slot in range(m):
            R2[slot, slot] = np.exp(-2 * r[perm[slot]])
            R2[m + slot, m + slot] = np.exp(2 * r[perm[slot]])
        if np.allclose(cols @ R2 @ cols.T, V2, atol=1e-8):
            O1 = cols
            break
    if O1 is None:
        raise ValueError("no valid Bloch-Messiah pairing found")

    Xb = O1[:m, :m]
    Yb = O1[:m, m:]
    U_O = Xb + uo_sign * 1j * Yb
    A = logm(U_O)

    Np = N + pad
    a1 = _ladder(Np)
    psi = np.zeros(Np**m, dtype=complex)
    psi[0] = 1.0
    # per-mode squeezers first (state = U_pass * S_prod |0>)
    for k in range(m):
        Sk = expm(0.5 * r[k] * (a1 @ a1 - a1.conj().T @ a1.conj().T))
        psi = _embed(Sk, k, m, Np) @ psi
    # passive lift
    Gp = np.zeros((Np**m, Np**m), dtype=complex)
    for j in range(m):
        for k in range(m):
            Gp += A[j, k] * _embed(a1.conj().T, j, m, Np) @ _embed(a1, k, m, Np)
    psi = expm(Gp) @ psi
    # displacement chain
    for k in range(m):
        gamma_k = (complex(rbar[k]) + 1j * complex(rbar[k + m])) / np.sqrt(2.0)
        if abs(gamma_k) > 0:
            Dk = expm(gamma_k * a1.conj().T - np.conj(gamma_k) * a1)
            psi = _embed(Dk, k, m, Np) @ psi
    return _truncate(psi, N, m)


def _truncate(psi: np.ndarray, N: int, m: int) -> np.ndarray:
    Np = int(round(len(psi) ** (1.0 / m)))
    if m == 1:
        return psi[:N]
    return psi.reshape(Np, Np)[:N, :N].reshape(-1)


def kernel_density(V: np.ndarray, rbar: np.ndarray, w: complex, N: int,
                   **kw) -> np.ndarray:
    psi = kernel_psi(V, rbar, N, **kw)
    nrm = float(np.real(np.vdot(psi, psi)))
    return w * np.outer(psi, psi.conj()) / nrm

def kernel_operand(V: np.ndarray, rbar: np.ndarray, N: int,
                   **kw) -> tuple[np.ndarray, np.ndarray, complex]:
    """B7 operand split of a (possibly complex-r̄) component.

    Component r̄ = m + i·s encodes the operator w·|ψ_L⟩⟨ψ_R|/⟨ψ_R|ψ_L⟩ with
    (analyse.py B7 convention) r_L − r_R = −Ω·V⁻¹·s; real r̄ → |ψ⟩⟨ψ|, tr 1.
    """
    s = np.imag(rbar)
    if float(np.max(np.abs(s))) < 1e-12:
        psi = kernel_psi(V, np.real(rbar), N, **kw)
        return psi, psi, 1.0 + 0.0j
    Vinv = np.linalg.inv(np.asarray(V, dtype=float))
    dr = -_omega(len(s) // 2) @ Vinv @ s
    mL = np.real(rbar) + 0.5 * dr
    mR = np.real(rbar) - 0.5 * dr
    psi_l = kernel_psi(V, mL, N, **kw)
    psi_r = kernel_psi(V, mR, N, **kw)
    return psi_l, psi_r, complex(np.vdot(psi_r, psi_l))

def kernel_component(V: np.ndarray, rbar: np.ndarray, w: complex, N: int,
                     **kw) -> np.ndarray:
    psi_l, psi_r, tr = kernel_operand(V, rbar, N, **kw)
    if abs(tr) < 1e-12:
        raise ValueError("component operand trace ~ 0")
    return w * np.outer(psi_l, psi_r.conj()) / tr

def kernel_mixed1(V: np.ndarray, rbar: np.ndarray, w: complex, N: int,
                  pad: int = 24, uo_sign: int = -1) -> np.ndarray:
    """m=1 mixed component via spectral route.

    ν = √det(2V) ≥ 1; U' = 2V/ν (must be symplectic — thermal-symmetric
    family); ρ = U_chain · diag(p_n) · U_chain† with p_n = (1/ν)·qⁿ,
    q = (ν−1)/ν, U_chain the Bloch-Messiah/displacement chain of the pure
    core U' (eigenbasis = displaced/rotated/squeezed Fock states).
    """
    V = np.asarray(V, dtype=float)
    V2 = V * 2.0
    nu2 = float(np.linalg.det(V2))
    if nu2 < 1.0 - 1e-8:
        raise ValueError("det(2V) < 1: below-vacuum noise")
    nu = math.sqrt(nu2)
    Om = _omega(1)
    up = V2 / nu
    if not np.allclose(up @ Om @ up, Om, atol=1e-8):
        raise ValueError("2V/ν not symplectic (non-thermal mixed component)")
    c = np.real(sqrtm(up))
    lam, q_mat = np.linalg.eigh(c)
    k = int(np.argmin(lam))
    r_s = -math.log(lam[k])
    qv = q_mat[:, k]
    o1 = np.column_stack([qv, -Om @ qv])
    u_o = complex(o1[0, 0] + uo_sign * 1j * o1[0, 1])
    a00 = complex(np.log(u_o))  # m=1 passive phase: scalar log

    n_p = N + pad
    a1 = _ladder(n_p)
    sq = expm(0.5 * r_s * (a1 @ a1 - a1.conj().T @ a1.conj().T))
    gp = a00 * (a1.conj().T @ a1)
    upass = expm(gp)
    gamma = (complex(rbar[0]) + 1j * complex(rbar[1])) / np.sqrt(2.0)
    disp = expm(gamma * a1.conj().T - np.conj(gamma) * a1) if abs(gamma) > 0 else np.eye(n_p, dtype=complex)
    chain = disp @ upass @ sq

    qq = (nu - 1.0) / (nu + 1.0)  # n̄/(n̄+1) with ν = 2n̄+1
    rho = np.zeros((N, N), dtype=complex)
    for n in range(N):
        phi = np.zeros(n_p, dtype=complex)
        phi[n] = 1.0
        phi = chain @ phi
        phi = _truncate(phi, N, 1)
        phi = phi / np.sqrt(np.real(np.vdot(phi, phi)))  # window renormalize
        rho += (2.0 / (nu + 1.0)) * qq**n * np.outer(phi, phi.conj())
    rho /= np.real(np.trace(rho))  # window trace-normalize (tail dropped)
    return w * rho


def gold(psi: np.ndarray) -> np.ndarray:
    return np.outer(psi, psi.conj())


def main() -> None:
    ok = True

    # 1. coherent (complex alpha) vs bridge closed form — tight
    N = 10
    alpha = 0.9 + 0.4j
    V = 0.5 * np.eye(2)
    rbar = np.array([np.sqrt(2) * alpha.real, np.sqrt(2) * alpha.imag], dtype=complex)
    amps = np.array([coherent_element(n, alpha) for n in range(N)])
    amps = amps / np.linalg.norm(amps)
    rho = kernel_density(V, rbar, 1.0, N)
    err = float(np.max(np.abs(rho - gold(amps))))
    print(f"1 coherent(0.9+0.4j)   maxdiff = {err:.2e}")
    ok &= err < TOL

    # 2. x-squeezed vs bridge closed form (window-renormalized) — tight
    r = 0.8
    V = np.diag([np.exp(-2 * r), np.exp(2 * r)]) * 0.5
    sn = np.array([squeezed_element(n, r) for n in range(N)])
    gold_sn = sn / np.linalg.norm(sn)
    for uos in (-1, 1):
        rho = kernel_density(V, np.zeros(2, dtype=complex), 1.0, N, uo_sign=uos)
        err = float(np.max(np.abs(rho - gold(gold_sn))))
        print(f"2 squeezed(r=0.8) uo={uos:+d}  maxdiff = {err:.2e}")
        ok &= err < TOL

    # 3. thermal -> must raise (mixed component)
    V = (2 * 0.7 + 1) * 0.5 * np.eye(2)
    try:
        kernel_density(V, np.zeros(2, dtype=complex), 1.0, N)
        print("3 thermal              FAIL: no error raised")
        ok = False
    except ValueError as exc:
        print(f"3 thermal              raises: {exc}")

    # 4. rotated squeeze: kernel vs fock chain R(phi) S(r) — loose (gold
    #    artifacts at N=10) + tight anchor p0 = 1/cosh(r)
    N4, r4, th = 14, 0.6, 0.7
    Rth = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    V = Rth @ (np.diag([np.exp(-2 * r4), np.exp(2 * r4)]) * 0.5) @ Rth.T
    st4 = f_phase(f_squeeze(FockState.vacuum(N4), r4), -th)
    st4b = f_phase(f_squeeze(FockState.vacuum(N4), r4), th)
    for uos in (-1, 1):
        rho = kernel_density(V, np.zeros(2, dtype=complex), 1.0, N4, uo_sign=uos)
        e_a = float(np.max(np.abs(rho - gold(st4.amps))))
        e_b = float(np.max(np.abs(rho - gold(st4b.amps))))
        # analytic window-normalized p0: p0 = 1 / sum_m C(2m,m)/4^m tanh^{2m} r
        ms = np.arange(N4 // 2)
        s_win = float(np.sum(
            np.array([math.comb(2 * m, m) / 4**m for m in ms])
            * np.tanh(r4) ** (2 * ms)))
        p0_expect = 1.0 / s_win
        p0 = rho[0, 0].real
        e_p0 = abs(p0 - p0_expect)
        print(f"4 rotated uo={uos:+d}     vs phi=-th: {e_a:.2e}  vs phi=+th: {e_b:.2e}  |p0-analytic|: {e_p0:.2e}")
        ok &= min(e_a, e_b) < LOOSE and e_p0 < TOL

    # 5. TMSV: exact coefficients (tight) + fock gate convention (loose)
    N2 = 20
    r5 = 0.9
    V = _tmsv_V2(r5) / 2.0
    exact = np.array([np.tanh(r5) ** n / np.cosh(r5) for n in range(N2)])
    for uos in (-1, 1):
        rho = kernel_density(V, np.zeros(4, dtype=complex), 1.0, N2, uo_sign=uos)
        # window-renormalized exact diagonal (tight)
        win = sum(abs(exact[n]) ** 2 for n in range(N2))
        diag_exact = np.array([abs(exact[n]) ** 2 / win for n in range(N2)])
        diag_k = np.array([rho[n * N2 + n, n * N2 + n].real for n in range(N2)])
        err_d = float(np.max(np.abs(diag_k - diag_exact)))
        st = FockState(amps=np.zeros((N2, N2), dtype=complex))
        st.amps[0, 0] = 1.0
        st5 = f_tmsv(st, r5, 0, 1)
        gold5 = np.multiply.outer(st5.amps, st5.amps.conj()).reshape(N2**2, -1)
        err_g = float(np.max(np.abs(rho - gold5)))
        print(f"5 TMSV uo={uos:+d}        diag-vs-exact = {err_d:.2e}  vs fock gate = {err_g:.2e}")
        ok &= err_d < TOL and err_g < LOOSE

    # 6. end-to-end heralding preview: TMSV -> kernel -> fock pnr_condition
    #    measuring mode0 n=2 must leave mode1 in pure |2> (TMSV = sum |l,l>)
    N2b = 20
    r6 = 0.7
    V = _tmsv_V2(r6) / 2.0
    rho6 = kernel_density(V, np.zeros(4, dtype=complex), 1.0, N2b, uo_sign=-1)
    P = np.zeros((N2b**2, N2b**2))
    for k in range(N2b):
        P[2 * N2b + k, 2 * N2b + k] = 1.0  # |2><2| on mode0 x I on mode1
    prob = float(np.trace(P @ rho6).real)
    residual = P @ rho6 @ P / prob
    expect = np.zeros(N2b**2)
    expect[2 * N2b + 2] = 1.0
    err = float(np.max(np.abs(np.real(np.diag(residual)) - expect)))
    print(f"6 herald n=2 residual  P(|2><2|) diag maxdiff = {err:.2e}  p={prob:.6f}")
    ok &= err < 1e-6
    exact_p = float(np.tanh(r6) ** 4 / np.cosh(r6) ** 2)
    win = sum((np.tanh(r6) ** n / np.cosh(r6)) ** 2 for n in range(N2b))
    print(f"   p vs window-exact tanh^4/cosh^2/win: {prob:.10f} vs {exact_p / win:.10f}")
    ok &= abs(prob - exact_p / win) < 1e-8

    # 7. product 2-mode: independent squeezes(+disp) -> passive BS rotation.
    #    V built with grouped-xxpp rotation matching fock beamsplitter(theta,0).
    r0, r1, bth = 0.6, 0.5, 0.5
    N7 = 20
    v0x, v0p = np.exp(-2 * r0) / 2, np.exp(2 * r0) / 2
    v1x, v1p = np.exp(-2 * r1) / 2, np.exp(2 * r1) / 2
    Vprod = np.array([
        [v0x, 0, 0, 0],
        [0, v1x, 0, 0],
        [0, 0, v0p, 0],
        [0, 0, 0, v1p],
    ])
    c7, s7 = np.cos(bth), np.sin(bth)
    # Heisenberg U^dag x U for fock beamsplitter(theta, 0): x' = M x with
    # M = [[c, s], [-s, c]] (sign pinned against measured fock-gold covariance)
    Rb = np.array([[c7, s7], [-s7, c7]])
    Sbs = np.zeros((4, 4))
    Sbs[:2, :2] = Rb
    Sbs[2:, 2:] = Rb
    V7 = Sbs @ Vprod @ Sbs.T
    g0, g1 = 0.3 + 0.2j, -0.4 + 0.1j
    rb7 = np.array([np.sqrt(2) * g0.real, np.sqrt(2) * g1.real,
                    np.sqrt(2) * g0.imag, np.sqrt(2) * g1.imag])
    st7 = FockState.vacuum(N7)
    # FockState.vacuum is 1-mode; build 2-mode product explicitly
    st7 = FockState(amps=np.zeros((N7, N7), dtype=complex))
    st7.amps[0, 0] = 1.0
    st7 = f_squeeze(st7, r0, 0)
    st7 = f_squeeze(st7, r1, 1)
    st7 = f_bs(st7, bth, 0.0)
    st7 = f_displace(st7, g0, 0)
    st7 = f_displace(st7, g1, 1)
    ga7 = st7.amps / np.linalg.norm(st7.amps.ravel())
    gold7 = np.multiply.outer(ga7, ga7.conj()).reshape(N7**2, -1)
    rho7 = kernel_density(V7, rb7, 1.0, N7)
    e7 = float(np.max(np.abs(rho7 - gold7)))
    print(f"7 product-BS-disp    vs fock chain: {e7:.2e}")
    ok &= e7 < LOOSE

    # 8. complex-weight coherent mixture gauge: two components same V(vacuum),
    #    rbar +/- sqrt2*alpha, weights w0=0.6, w1=0.4*i -> rho = sum w |psi><psi|
    N8 = 12
    al = 0.8
    w0, w1 = 0.6, 0.4j
    rho8 = np.zeros((N8, N8), dtype=complex)
    for w, sgn in ((w0, 1.0), (w1, -1.0)):
        rbc = np.array([np.sqrt(2) * sgn * al, 0.0], dtype=complex)
        rho8 += kernel_density(0.5 * np.eye(2), rbc, w, N8)
    amps_p = np.array([coherent_element(n, al) for n in range(N8)])
    amps_m = np.array([coherent_element(n, -al) for n in range(N8)])
    amps_p /= np.linalg.norm(amps_p)
    amps_m /= np.linalg.norm(amps_m)
    gp = np.multiply.outer(amps_p, amps_p.conj())
    gm = np.multiply.outer(amps_m, amps_m.conj())
    e8 = float(np.max(np.abs(rho8 - w0 * gp - w1 * gm)))
    print(f"8 complex-w mixture  vs analytic: {e8:.2e}")
    ok &= e8 < TOL

    # 9. even_cat(α): 4-component assembly with complex-r̄ cross operands
    #    vs window-consistent fock cat gold (Schrödinger-split convention).
    N9, al9 = 12, 0.8
    rho9 = np.zeros((N9, N9), dtype=complex)
    for c_k in even_cat(al9).components:
        rho9 += kernel_component(c_k.V, c_k.rbar, c_k.w, N9)
    p9 = np.array([coherent_element(n, al9) for n in range(N9)])
    m9 = np.array([coherent_element(n, -al9) for n in range(N9)])
    p9 /= np.linalg.norm(p9)
    m9 /= np.linalg.norm(m9)
    tr_pm = complex(np.vdot(p9, m9))  # ⟨p|m⟩
    gp9 = np.outer(p9, p9.conj())
    gm9 = np.outer(m9, m9.conj())
    gpm = np.outer(m9, p9.conj()) / tr_pm
    gmp = np.outer(p9, m9.conj()) / np.conj(tr_pm)
    comps = even_cat(al9).components
    rho9_gold = (comps[0].w * gp9 + comps[1].w * gm9
                 + comps[2].w * gpm + comps[3].w * gmp)
    e9 = float(np.max(np.abs(rho9 - rho9_gold)))
    herm9 = float(np.max(np.abs(rho9 - rho9.conj().T)))
    tr9 = float(np.real(np.trace(rho9)))
    print(f"9 even-cat assembly  vs window gold: {e9:.2e}  herm: {herm9:.2e}  tr={tr9:.8f}")
    ok &= e9 < TOL and herm9 < TOL and abs(tr9 - 1.0) < 1e-6

    # 10. mixed m=1 thermal: spectral-route diagonal vs window-renormalized
    #     thermal_diag gold. N=40 so p_n tail ~ 4e-9.
    N10, nbar = 40, 0.7
    V10 = (2 * nbar + 1) * 0.5 * np.eye(2)
    rho10 = kernel_mixed1(V10, np.zeros(2, dtype=complex), 1.0, N10)
    p_raw = np.array([thermal_diag(n, nbar) for n in range(N10)])
    p_expect = p_raw / float(np.sum(p_raw))  # window-renormalized gold
    e10 = float(np.max(np.abs(np.real(np.diag(rho10)) - p_expect)))
    print(f"10 thermal mixed     diag vs thermal_diag: {e10:.2e}")
    ok &= e10 < TOL

    # 10b. thermalized squeezed: Tr ρ² vs bosonic analytic purity 1/(2n̄+1).
    r10, nbar_b = 0.5, 0.8
    Vs = np.diag([np.exp(-2 * r10), np.exp(2 * r10)]) * 0.5
    V10b = (2 * nbar_b + 1) * Vs
    rho10b = kernel_mixed1(V10b, np.zeros(2, dtype=complex), 1.0, N10)
    tr2_k = float(np.real(np.trace(rho10b @ rho10b)))
    tr2_a = 1.0 / (2 * nbar_b + 1)
    st_b = BosonicState(components=[Component(V=V10b, rbar=np.zeros(2, dtype=complex), w=1.0)])
    tr2_bos = bosonic_purity(st_b)
    e10b = abs(tr2_k - tr2_a)
    print(f"10b therm-squeezed   Tr(rho^2) kernel={tr2_k:.10f} analytic={tr2_a:.10f} bosonic={tr2_bos:.10f}  diff={e10b:.2e}")
    ok &= e10b < 1e-7 and abs(tr2_bos - tr2_a) < 1e-9

    print("PIN RESULT:", "OK" if ok else "MISMATCH")
    raise SystemExit(0 if ok else 1)


def _tmsv_V2(r: float) -> np.ndarray:
    """TMSV covariance 2V (xxpp grouped, x1-x2 correlated, p1-p2 anti)."""
    c = np.cosh(2 * r)
    s = np.sinh(2 * r)
    return np.array([
        [c, s, 0, 0],
        [s, c, 0, 0],
        [0, 0, c, -s],
        [0, 0, -s, c],
    ])


if __name__ == "__main__":
    main()