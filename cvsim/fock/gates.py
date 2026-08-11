"""Fock gates: single-mode D/R/S/Kerr (+mode=); two-mode BS; 1-mode ρ via UρU†."""

from __future__ import annotations

import numpy as np
from scipy.linalg import expm, logm

from cvsim.fock.density import FockDensity
from cvsim.fock.state import FockState

FockLike1 = FockState | FockDensity


def annihilation(cutoff: int) -> np.ndarray:
    """Truncated a: a|n⟩ = √n |n-1⟩, shape (N, N)."""
    a = np.zeros((cutoff, cutoff), dtype=complex)
    for n in range(1, cutoff):
        a[n - 1, n] = np.sqrt(n)
    return a


def _check_mode_pure(state: FockState, mode: int) -> None:
    if not 0 <= mode < state.nmode:
        raise IndexError(f"mode {mode} out of range for nmode={state.nmode}")


def _apply_1mode_U_pure(state: FockState, U: np.ndarray, mode: int = 0) -> FockState:
    _check_mode_pure(state, mode)
    if state.nmode == 1:
        return FockState(amps=U @ state.amps)
    if mode == 0:
        return FockState(amps=U @ state.amps)
    # mode 1: c'_{n0,m} = Σ_n1 U_{m n1} c_{n0 n1}
    return FockState(amps=state.amps @ U.T)


def _apply_U_density(state: FockDensity, U: np.ndarray) -> FockDensity:
    """ρ' = U ρ U† (1-mode only)."""
    if state.nmode != 1:
        raise ValueError("2-mode density gates out of scope")
    rho = U @ state.rho @ U.conj().T
    rho = 0.5 * (rho + rho.conj().T)
    return FockDensity(rho=rho, nmode=1)


def _diag_phase_pure(state: FockState, phases: np.ndarray, mode: int = 0) -> FockState:
    """Multiply Fock levels on `mode` by phases[n]."""
    _check_mode_pure(state, mode)
    if state.nmode == 1:
        return FockState(amps=state.amps * phases)
    if mode == 0:
        return FockState(amps=state.amps * phases[:, None])
    return FockState(amps=state.amps * phases[None, :])


def _squeeze_U(N: int, r: float) -> np.ndarray:
    a = annihilation(N)
    ad = a.conj().T
    G = 0.5 * r * (a @ a - ad @ ad)
    return expm(G)


def _displace_U(N: int, alpha: complex) -> np.ndarray:
    a = annihilation(N)
    ad = a.conj().T
    alpha = complex(alpha)
    G = alpha * ad - np.conj(alpha) * a
    return expm(G)


def squeeze(state: FockLike1, r: float, mode: int = 0) -> FockLike1:
    """Single-mode squeeze S(r) = exp(½ r (a² − a†²)) for real r.

    FockDensity: ρ' = U ρ U† (1-mode only; mode must be 0).
    """
    if isinstance(state, FockDensity):
        if state.nmode != 1 or mode != 0:
            raise IndexError("FockDensity gates: 1-mode only; mode must be 0")
        return _apply_U_density(state, _squeeze_U(state.cutoff, r))
    return _apply_1mode_U_pure(state, _squeeze_U(state.cutoff, r), mode)


def phase(state: FockLike1, theta: float, mode: int = 0) -> FockLike1:
    """Phase shift: |n⟩ → e^{i n θ} |n⟩."""
    if isinstance(state, FockDensity):
        if state.nmode != 1 or mode != 0:
            raise IndexError("FockDensity gates: 1-mode only; mode must be 0")
        n = np.arange(state.cutoff)
        phases = np.exp(1j * theta * n)
        U = np.diag(phases)
        return _apply_U_density(state, U)
    n = np.arange(state.cutoff)
    return _diag_phase_pure(state, np.exp(1j * theta * n), mode)


def displace(state: FockLike1, alpha: complex, mode: int = 0) -> FockLike1:
    """Displacement D(α) = exp(α a† − α* a)."""
    if isinstance(state, FockDensity):
        if state.nmode != 1 or mode != 0:
            raise IndexError("FockDensity gates: 1-mode only; mode must be 0")
        return _apply_U_density(state, _displace_U(state.cutoff, alpha))
    return _apply_1mode_U_pure(state, _displace_U(state.cutoff, alpha), mode)


def kerr(state: FockLike1, chi: float, mode: int = 0) -> FockLike1:
    """Kerr: |n⟩ → e^{i χ n²} |n⟩. Density: UρU† (1-mode)."""
    if isinstance(state, FockDensity):
        if state.nmode != 1 or mode != 0:
            raise IndexError("FockDensity gates: 1-mode only; mode must be 0")
        n = np.arange(state.cutoff)
        U = np.diag(np.exp(1j * chi * n * n))
        return _apply_U_density(state, U)
    n = np.arange(state.cutoff)
    return _diag_phase_pure(state, np.exp(1j * chi * n * n), mode)


def beamsplitter(state: FockState, theta: float, phi: float = 0.0) -> FockState:
    """Two-mode BS(θ, φ) = exp[θ(e^{iφ} a0† a1 − h.c.)]. Requires nmode==2."""
    if state.nmode != 2:
        raise ValueError("beamsplitter requires two-mode state")
    N = state.cutoff
    a = annihilation(N)
    I = np.eye(N, dtype=complex)
    a0 = np.kron(a, I)
    a1 = np.kron(I, a)
    ad0 = a0.conj().T
    ad1 = a1.conj().T
    eip = np.exp(1j * phi)
    G = theta * (eip * ad0 @ a1 - np.conj(eip) * ad1 @ a0)
    vec = state.amps.reshape(N * N)
    out = expm(G) @ vec
    return FockState(amps=out.reshape(N, N))

def two_mode_squeeze(
    state: FockState, r: float, mode1: int = 0, mode2: int = 1
) -> FockState:
    """Two-mode squeeze S2(r) = exp[r(a_i† a_j† - a_i a_j)] (real r). Requires nmode==2.

    Aligns with Gaussian xxpp S2: vacuum mean n_i = sinh^2 r (cutoff large).
    """
    if state.nmode != 2:
        raise ValueError("two_mode_squeeze requires two-mode state")
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    if {mode1, mode2} != {0, 1}:
        raise ValueError("two_mode_squeeze: modes must be 0 and 1")
    N = state.cutoff
    a = annihilation(N)
    I = np.eye(N, dtype=complex)
    a0 = np.kron(a, I)
    a1 = np.kron(I, a)
    ad0 = a0.conj().T
    ad1 = a1.conj().T
    G = r * (ad0 @ ad1 - a0 @ a1)
    vec = state.amps.reshape(N * N)
    out = expm(G) @ vec
    return FockState(amps=out.reshape(N, N))



def _quadrature_matrices(N: int) -> tuple[np.ndarray, np.ndarray]:
    """Position/momentum matrices x̂, p̂ in Fock basis (ħ=1).

    ⟨n|x̂|m⟩ = (√(m+1) δ_{n,m+1} + √m δ_{n,m−1}) / √2,  p̂ = (a − a†)/(i√2).
    """
    a = annihilation(N)
    x = (a + a.conj().T) / np.sqrt(2.0)
    p = (a - a.conj().T) / (1j * np.sqrt(2.0))
    return x, p


def cz(state: FockState, weight: float, mode1: int = 0, mode2: int = 1) -> FockState:
    """Controlled-Z CZ(g) = exp(i·g·x̂⊗x̂) (continuous-variable, matches Gaussian cz).

    Fock matrix via expm on the N²×N² space. Requires nmode==2.
    """
    if state.nmode != 2:
        raise ValueError("cz requires two-mode state")
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    if {mode1, mode2} != {0, 1}:
        raise ValueError("cz: modes must be 0 and 1")
    N = state.cutoff
    x, _ = _quadrature_matrices(N)
    U = expm(1j * weight * np.kron(x, x))
    vec = state.amps.reshape(N * N)
    return FockState(amps=(U @ vec).reshape(N, N))


def cx(state: FockState, weight: float, mode1: int = 0, mode2: int = 1) -> FockState:
    """Controlled-X CX(g) = exp(i·g·x̂⊗p̂) (continuous-variable, matches Gaussian cx).

    Fock matrix via expm on the N²×N² space. Requires nmode==2.
    """
    if state.nmode != 2:
        raise ValueError("cx requires two-mode state")
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    if {mode1, mode2} != {0, 1}:
        raise ValueError("cx: modes must be 0 and 1")
    N = state.cutoff
    x, p = _quadrature_matrices(N)
    U = expm(1j * weight * np.kron(x, p))
    vec = state.amps.reshape(N * N)
    return FockState(amps=(U @ vec).reshape(N, N))


def mach_zehnder(
    state: FockState, theta: float, phi: float = 0.0, mode1: int = 0, mode2: int = 1
) -> FockState:
    """Mach–Zehnder: BS(θ,φ) → phase(φ) on mode1 → BS(π/4) (Gaussian convention).

    U = BS(π/4,0)·(I⊗P(φ))·BS(θ,φ) applied on the N²×N² space. Requires nmode==2.
    """
    if state.nmode != 2:
        raise ValueError("mach_zehnder requires two-mode state")
    N = state.cutoff
    I = np.eye(N, dtype=complex)
    a = annihilation(N)
    a0 = np.kron(a, I)
    a1 = np.kron(I, a)
    def G_bs(th: float, ph: float) -> np.ndarray:
        eip = np.exp(1j * ph)
        return th * (eip * a0.conj().T @ a1 - np.conj(eip) * a1.conj().T @ a0)

    n = np.arange(N)
    P = np.diag(np.exp(1j * phi * n))
    U = expm(G_bs(np.pi / 4.0, 0.0)) @ np.kron(I, P) @ expm(G_bs(theta, phi))
    vec = state.amps.reshape(N * N)
    return FockState(amps=(U @ vec).reshape(N, N))


def interferometer(state: FockState, U: np.ndarray) -> FockState:
    """Passive linear interferometer: U (2×2 unitary) mixing both modes.

    Full-space generator H = Σ_{ij} (log U)_{ij} a_i† a_j (logm well-defined
    for unitary U); U_full = expm(H). Requires nmode==2 (m≤2: dense anchor).
    """
    if state.nmode != 2:
        raise ValueError("interferometer requires two-mode state (dense m≤2 anchor)")
    U = np.asarray(U, dtype=complex)
    if U.shape != (2, 2):
        raise ValueError(f"U must be 2x2, got {U.shape}")
    if not np.allclose(U @ U.conj().T, np.eye(2), atol=1e-10):
        raise ValueError("U must be unitary")
    N = state.cutoff
    I = np.eye(N, dtype=complex)
    a = annihilation(N)
    a0 = np.kron(a, I)
    a1 = np.kron(I, a)
    K = np.linalg.slogdet(U)
    logU = logm(U)
    H = logU[0, 0] * (a0.conj().T @ a0) + logU[0, 1] * (a0.conj().T @ a1) + \
        logU[1, 0] * (a1.conj().T @ a0) + logU[1, 1] * (a1.conj().T @ a1)
    vec = state.amps.reshape(N * N)
    return FockState(amps=(expm(H) @ vec).reshape(N, N))


def apply_unitary(
    state: FockState | FockDensity, U: np.ndarray, modes: list[int] | None = None
) -> FockState | FockDensity:
    """Apply an arbitrary truncated-space unitary U to the state.

    - 1-mode state: U is (N, N), acts on the single mode.
    - 2-mode state with ``modes=[m]``: U is (N, N), acts on mode m
      (tensor I on the other).
    - 2-mode state with ``modes=None``: U is (N², N²), acts on the full space.
    """
    U = np.asarray(U, dtype=complex)
    if isinstance(state, FockDensity):
        if state.nmode != 1:
            raise ValueError("apply_unitary: FockDensity full-space path not implemented (m≤1)")
        if U.shape != (state.cutoff, state.cutoff):
            raise ValueError(f"U must be ({state.cutoff},{state.cutoff}) for 1-mode density")
        return _apply_U_density(state, U)
    N = state.cutoff
    if state.nmode == 1:
        if U.shape != (N, N):
            raise ValueError(f"U must be ({N},{N}) for 1-mode state")
        return FockState(amps=U @ state.amps)
    # nmode == 2
    if modes is None:
        if U.shape != (N * N, N * N):
            raise ValueError(f"U must be ({N*N},{N*N}) for full-space 2-mode")
        vec = state.amps.reshape(N * N)
        return FockState(amps=(U @ vec).reshape(N, N))
    if len(modes) != 1:
        raise ValueError("apply_unitary: single mode per call (2-mode states)")
    m = modes[0]
    if m not in (0, 1):
        raise IndexError(f"mode {m} out of range for nmode=2")
    if U.shape != (N, N):
        raise ValueError(f"U must be ({N},{N}) for single-mode application")
    if m == 0:
        return FockState(amps=U @ state.amps)
    return FockState(amps=state.amps @ U.T)
