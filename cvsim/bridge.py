"""Bridges between representations (ADR-0001: root-level; rep packages stay
isolated from each other, only this root module imports both sides).

Two families live here:

1. Observable-valued bridge (Phase 5 F-BRIDGE): Fock-basis matrix elements
   and photon statistics of Gaussian states via closed forms. No state
   conversion.

2. State bridge (ADR-0012): ``bosonic_to_fock`` converts a bosonic
   (Gaussian-mixture) state into a truncated Fock density matrix;
   ``pnr_condition_bosonic`` / ``pnr_sample_and_condition_bosonic`` run
   photon-number conditioning end-to-end. Component kernel = Bloch–Messiah-
   lite matrix atoms, numerics pinned by ``tools/probe_bridge_kernel.py``
   (PIN RESULT: OK): pure components via sqrtm/eigh pairing + ladder expm
   chain; complex-r̄ components via B7 left/right split r_L − r_R = −Ω·V⁻¹·s
   (w·|ψ_L⟩⟨ψ_R|/⟨ψ_R|ψ_L⟩); 1-mode mixed components via the spectral route
   (ν = √det 2V, pₙ thermal weights). m ≥ 3 and 2-mode mixed components
   raise honestly (ADR-0012 future work).

Reference formula sources:
- coherent: ⟨n|α⟩ = e^{−|α|²/2} αⁿ/√n!
- squeezed: S(r) = exp(½r(a²−a†²)), real-r Fock convention includes
  (−1)^{n/2} (matches ``cvsim.fock.gates.squeeze``; verified numerically).
- thermal: ⟨n|ρ_th|n⟩ = n̄ⁿ/(n̄+1)^{n+1}
- vacuum prob: p₀ = exp(−½ r̄ᵀ (V+½I)⁻¹ r̄) / √det(V+½I) (single-mode, ħ=1, xxpp)
"""

from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.linalg import expm, logm, sqrtm

from cvsim.bosonic.state import BosonicState
from cvsim.conventions import omega  # noqa: F401 — convention anchor (xxpp ħ=1)
from cvsim.fock.density import FockDensity
from cvsim.fock.observables import pnr_condition as fock_pnr_condition
from cvsim.fock.observables import pnr_sample as fock_pnr_sample
from cvsim.fock.state import FockState


def coherent_element(n: int, alpha: complex) -> complex:
    """Fock amplitude ⟨n|α⟩ of a coherent state (any n ≥ 0)."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if n == 0:
        return complex(np.exp(-(abs(alpha) ** 2) / 2.0))
    return complex(np.exp(-(abs(alpha) ** 2) / 2.0) * alpha**n / math.sqrt(math.factorial(n)))


def squeezed_element(n: int, r: float, phi: float = 0.0) -> complex:
    """Fock amplitude ⟨n|S(r e^{iφ})|0⟩ (real r ≥ 0).

    Convention: matches ``cvsim.fock.gates.squeeze`` (real-r) at φ=0, i.e.
    includes the (−1)^{n/2} sign for even n. Odd n → 0.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if n % 2 == 1:
        return 0.0j
    z = math.tanh(r) * np.exp(1j * phi)  # complex squeezing parameter
    m = n // 2
    pref = math.sqrt(math.factorial(2 * m)) / (2**m * math.factorial(m) * math.sqrt(math.cosh(r)))
    return complex(((-1) ** m) * pref * z**m)


def thermal_diag(n: int, nbar: float) -> float:
    """Thermal diagonal ⟨n|ρ_th|n⟩ = n̄ⁿ/(n̄+1)^{n+1}."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if nbar < 0.0:
        raise ValueError(f"nbar must be >= 0, got {nbar}")
    return float(nbar**n / (nbar + 1.0) ** (n + 1))


def vacuum_probability(V: np.ndarray, rbar: np.ndarray, mode: int = 0) -> float:
    """P(0) = ⟨0|ρ|0⟩ of a Gaussian state on one mode (analytic, ħ=1, xxpp).

    Reduces V to the mode's 2×2 block and r̄ to its 2-vector, then

        p₀ = exp(−½ r̄ᵀ (V+½I)⁻¹ r̄) / √det(V+½I)

    Freeze checks: vacuum → 1; coherent |α⟩ → e^{−|α|²}; thermal n̄ → 1/(n̄+1).
    """
    V = np.asarray(V, dtype=float)
    rbar = np.asarray(rbar, dtype=float)
    m = V.shape[0] // 2
    if V.shape != (2 * m, 2 * m):
        raise ValueError(f"V must be (2m, 2m); got {V.shape}")
    if rbar.shape != (2 * m,):
        raise ValueError(f"rbar must be (2m,); got {rbar.shape}")
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    i = mode
    # xxpp: mode i block is (V[i,i], V[i,m+i]; V[m+i,i], V[m+i,m+i])
    V1 = np.array([[V[i, i], V[i, m + i]], [V[m + i, i], V[m + i, m + i]]])
    r1 = np.array([rbar[i], rbar[m + i]])
    A = V1 + 0.5 * np.eye(2)
    if np.linalg.eigvalsh(A).min() <= 0.0:
        raise ValueError(f"V+½I on mode {mode} is not positive-definite")
    exponent = -0.5 * float(r1 @ np.linalg.solve(A, r1))
    return float(np.exp(exponent) / np.sqrt(np.linalg.det(A)))


def fock_state_amplitude(n: int, state: FockState) -> complex:
    """Read amplitude ⟨n|ψ⟩ from a single-mode FockState (bridge test helper)."""
    amps = np.asarray(state.amps)
    if amps.ndim != 1:
        raise ValueError(f"single-mode only; got amps.ndim={amps.ndim} (ponytail)")
    if n < 0 or n >= amps.shape[0]:
        raise IndexError(f"n={n} outside cutoff={amps.shape[0]}")
    return complex(amps[n])


# -- State bridge: bosonic -> fock (ADR-0012) --------------------------------
#
# Component kernel (Bloch-Messiah-lite), pinned by tools/probe_bridge_kernel.py
# (PIN RESULT: OK):
# - pure components: sqrtm/eigh pairing + ladder expm chain on (N+pad) space;
# - complex-rbar components: B7 left/right operand split r_L - r_R = -Omega V^-1 s,
#   operator w*|psi_L><psi_R|/tr with tr = <psi_R|psi_L> (truncated numeric
#   denominator, not the analytic window S_ij);
# - 1-mode mixed components: spectral route (nu = sqrt(det 2V), thermal weights
#   2/(nu+1) q^n, q = (nu-1)/(nu+1)).
# No renormalization anywhere: each component contributes its exact truncated
# operator; trace = 1 - tail (fock factory / pnr_probs convention, vision §5).

_BRIDGE_PAD = 24
_UO_SIGN = -1


def _bridge_ladder(n: int) -> np.ndarray:
    a = np.zeros((n, n), dtype=complex)
    for k in range(1, n):
        a[k - 1, k] = np.sqrt(k)
    return a


def _bridge_embed(op: np.ndarray, k: int, m: int, n_p: int) -> np.ndarray:
    mats: list[np.ndarray] = [np.eye(n_p, dtype=complex)] * m
    mats[k] = op
    out = mats[0]
    for extra in mats[1:]:
        out = np.kron(out, extra)
    return out


def _bridge_truncate(psi: np.ndarray, n: int, m: int) -> np.ndarray:
    n_p = int(round(len(psi) ** (1.0 / m)))
    if m == 1:
        return psi[:n]
    return psi.reshape(n_p, n_p)[:n, :n].reshape(-1)


def _bridge_kernel_psi(
    V: np.ndarray, rbar: np.ndarray, n: int, *, pad: int = _BRIDGE_PAD
) -> np.ndarray:
    """Truncated Fock vector of one pure Gaussian component (m <= 2).

    |psi> = D-chain * U_passive * prod_k S_k(r_k) |0> on the (n+pad)-ladder
    space, truncated to n per mode. pad absorbs squeeze/displacement leakage
    (probe-pinned: pad=24 keeps gate-chain golds at the 1e-2 expm level).
    """
    V = np.asarray(V, dtype=float)
    m = V.shape[0] // 2
    if m not in (1, 2):
        raise ValueError(
            f"state bridge supports 1..2 modes; got {m} (ADR-0012 future work)"
        )
    V2 = V * 2.0
    Om = omega(m)
    if not np.allclose(V2 @ Om @ V2, Om, atol=1e-8):
        raise ValueError("component is not pure (2V not symplectic)")
    C = np.real(sqrtm(V2))
    lam, Q = np.linalg.eigh(C)
    squ = np.argsort(lam)[:m]  # m smallest eigenvalues = squeeze directions
    r = -np.log(lam[squ])  # >= 0 (fock S(+r): x squeezed)

    # passive O_1 via pairing search: x-slot <- squeezed eigvec,
    # p-slot <- anti-squeezed partner -Omega q; must reproduce V2 = O1 R2 O1^T
    O1 = None
    for perm in itertools.permutations(range(m)):
        cols = np.zeros((2 * m, 2 * m))
        for slot, eig_idx in enumerate(perm):
            q = Q[:, squ[eig_idx]]
            cols[:, slot] = q
            cols[:, m + slot] = -Om @ q
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
        raise ValueError("no valid Bloch-Messiah pairing found (numerical breakdown)")

    Xb = O1[:m, :m]
    Yb = O1[:m, m:]
    u_o = Xb + _UO_SIGN * 1j * Yb
    A = np.asarray(logm(u_o))

    n_p = n + pad
    a1 = _bridge_ladder(n_p)
    psi = np.zeros(n_p**m, dtype=complex)
    psi[0] = 1.0
    for k in range(m):
        sq_k = expm(0.5 * r[k] * (a1 @ a1 - a1.conj().T @ a1.conj().T))
        psi = _bridge_embed(sq_k, k, m, n_p) @ psi
    gp = np.zeros((n_p**m, n_p**m), dtype=complex)
    for j in range(m):
        for k in range(m):
            gp += A[j, k] * _bridge_embed(a1.conj().T, j, m, n_p) @ _bridge_embed(
                a1, k, m, n_p
            )
    psi = expm(gp) @ psi
    for k in range(m):
        gamma_k = (complex(rbar[k]) + 1j * complex(rbar[k + m])) / np.sqrt(2.0)
        if abs(gamma_k) > 0:
            disp_k = expm(gamma_k * a1.conj().T - np.conj(gamma_k) * a1)
            psi = _bridge_embed(disp_k, k, m, n_p) @ psi
    return _bridge_truncate(psi, n, m)


def _bridge_kernel_operand(
    V: np.ndarray, rbar: np.ndarray, n: int
) -> tuple[np.ndarray, np.ndarray, complex]:
    """B7 operand split of a (possibly complex-rbar) pure component.

    Component rbar = m + i*s encodes the operator w*|psi_L><psi_R|/<psi_R|psi_L>
    with (B7 convention) r_L - r_R = -Omega V^-1 s; real rbar -> |psi><psi|,
    tr = 1. The denominator is the truncated numeric overlap (window-exact
    ratio; never the analytic S_ij).
    """
    s = np.imag(rbar)
    if float(np.max(np.abs(s))) < 1e-12:
        psi = _bridge_kernel_psi(V, np.real(rbar), n)
        return psi, psi, 1.0 + 0.0j
    v_inv = np.linalg.inv(np.asarray(V, dtype=float))
    dr = -omega(len(s) // 2) @ v_inv @ s
    m_l = np.real(rbar) + 0.5 * dr
    m_r = np.real(rbar) - 0.5 * dr
    psi_l = _bridge_kernel_psi(V, m_l, n)
    psi_r = _bridge_kernel_psi(V, m_r, n)
    return psi_l, psi_r, complex(np.vdot(psi_r, psi_l))


def _bridge_kernel_mixed1(
    V: np.ndarray, rbar: np.ndarray, w: complex, n: int, *, pad: int = _BRIDGE_PAD
) -> np.ndarray:
    """1-mode mixed component via the spectral route (thermal-symmetric family).

    nu = sqrt(det 2V) >= 1; U' = 2V/nu must be symplectic; rho = U_chain
    diag(p_n) U_chain^dag with p_n = 2/(nu+1) q^n, q = (nu-1)/(nu+1)
    (nbar = (nu-1)/2). Diagonal analytic weights, no window renorm:
    trace = 1 - q^n (exact-truncation convention).
    """
    V2 = np.asarray(V, dtype=float) * 2.0
    nu2 = float(np.linalg.det(V2))
    if nu2 < 1.0 - 1e-8:
        raise ValueError("component noise below vacuum (det(2V) < 1)")
    nu = math.sqrt(nu2)
    Om = omega(1)
    up = V2 / nu
    if not np.allclose(up @ Om @ up, Om, atol=1e-8):
        raise ValueError(
            "mixed component outside the thermal-symmetric family (2V/nu not symplectic)"
        )
    c = np.real(sqrtm(up))
    lam, q_mat = np.linalg.eigh(c)
    k = int(np.argmin(lam))
    r_s = -math.log(lam[k])
    qv = q_mat[:, k]
    o1 = np.column_stack([qv, -Om @ qv])
    u_o = complex(o1[0, 0] + _UO_SIGN * 1j * o1[0, 1])
    a00 = complex(np.log(u_o))  # m=1 passive phase: scalar log

    n_p = n + pad
    a1 = _bridge_ladder(n_p)
    sq = expm(0.5 * r_s * (a1 @ a1 - a1.conj().T @ a1.conj().T))
    gp = a00 * (a1.conj().T @ a1)
    upass = expm(gp)
    gamma = (complex(rbar[0]) + 1j * complex(rbar[1])) / np.sqrt(2.0)
    if abs(gamma) > 0:
        disp = expm(gamma * a1.conj().T - np.conj(gamma) * a1)
    else:
        disp = np.eye(n_p, dtype=complex)
    chain = disp @ upass @ sq

    qq = (nu - 1.0) / (nu + 1.0)
    rho = np.zeros((n, n), dtype=complex)
    for idx in range(n):
        phi = np.zeros(n_p, dtype=complex)
        phi[idx] = 1.0
        phi = chain @ phi
        phi = _bridge_truncate(phi, n, 1)
        rho += (2.0 / (nu + 1.0)) * qq**idx * np.outer(phi, phi.conj())
    return w * rho


def _bridge_component_matrix(
    V: np.ndarray, rbar: np.ndarray, w: complex, n: int
) -> np.ndarray:
    """Fock matrix (n^m x n^m, row-major kron) of one mixture component."""
    V = np.asarray(V, dtype=float)
    m = V.shape[0] // 2
    rbar = np.asarray(rbar, dtype=complex)
    s = np.imag(rbar)
    V2 = V * 2.0
    pure = bool(np.allclose(V2 @ omega(m) @ V2, omega(m), atol=1e-8))
    if float(np.max(np.abs(s))) > 1e-12 and not pure:
        raise ValueError("complex rbar on a mixed component is out of scope (ADR-0012)")
    if pure:
        psi_l, psi_r, tr = _bridge_kernel_operand(V, rbar, n)
        if abs(tr) < 1e-12:
            raise ValueError("component operand trace ~ 0 (orthogonal L/R halves)")
        return w * np.outer(psi_l, psi_r.conj()) / tr
    if m == 1:
        return _bridge_kernel_mixed1(V, rbar, w, n)
    raise ValueError("2-mode mixed component is out of scope (ADR-0012 future work)")


def bosonic_to_fock(state: BosonicState, *, cutoff: int) -> FockDensity:
    """Convert a bosonic (Gaussian-mixture) state to a truncated Fock density.

    rho = sum_k w_k K(V_k, rbar_k) over components (ADR-0012 kernel, see
    module docstring). No renormalization: exact truncated elements, trace
    = 1 - tail (tail never guessed, vision §5). Modes limited to 1..2;
    complex-rbar mixed and 2-mode mixed components raise honestly.
    """
    if not state.components:
        raise ValueError("bosonic_to_fock: empty state (no components)")
    m = state.nmode
    if m not in (1, 2):
        raise ValueError(f"bosonic_to_fock supports 1..2 modes; got nmode={m}")
    if cutoff < 1:
        raise ValueError(f"cutoff must be >= 1; got {cutoff}")
    dim = cutoff**m
    rho = np.zeros((dim, dim), dtype=complex)
    for comp in state.components:
        rho += _bridge_component_matrix(comp.V, comp.rbar, comp.w, cutoff)
    return FockDensity(rho=rho, nmode=m)


def pnr_condition_bosonic(
    state: BosonicState, mode: int = 0, n: int = 0, *, cutoff: int = 30
) -> FockDensity:
    """Posterior after photon-number outcome ``n`` on ``mode`` (ADR-0012).

    Two-step bridge: ``bosonic_to_fock`` then fock ``pnr_condition`` — the
    PNR posterior lives in fock space (one-way bridge). Zero-probability
    outcomes raise honestly (fock path).
    """
    rho = bosonic_to_fock(state, cutoff=cutoff)
    out = fock_pnr_condition(rho, mode, n)
    if not isinstance(out, FockDensity):
        raise TypeError("pnr_condition_bosonic: expected FockDensity from density input")
    return out


def pnr_sample_and_condition_bosonic(
    state: BosonicState,
    mode: int = 0,
    *,
    cutoff: int = 30,
    rng: np.random.Generator | None = None,
) -> tuple[int, FockDensity]:
    """Sample a photon number on ``mode`` then condition, all in fock space.

    Returns ``(n, posterior)``. The Born marginal is the fock-space diagonal
    of the bridged density (same distribution as bosonic ``pnr_probs`` up to
    the truncation tail).
    """
    rho = bosonic_to_fock(state, cutoff=cutoff)
    outcome = fock_pnr_sample(rho, mode, rng=rng)
    out = fock_pnr_condition(rho, mode, outcome)
    if not isinstance(out, FockDensity):
        raise TypeError("pnr_sample_and_condition_bosonic: expected FockDensity")
    return outcome, out
