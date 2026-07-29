"""Shared xxpp symplectic generators (ħ=1). Used by Gaussian + Bosonic.

Not a fourth simulator — shared foundation under G/B gates.
Prefer this module over cvsim.gaussian.symplectic (compat shim).
"""

from __future__ import annotations

import numpy as np

from cvsim.conventions import omega


def is_symplectic(S: np.ndarray, *, atol: float = 1e-8) -> bool:
    """Return True if S Ω Sᵀ ≈ Ω (xxpp convention).

    Uses component-wise absolute tolerance ``atol`` via ``numpy.allclose``
    (rtol=0 effectively for the residual when entries are O(1)). This is an
    *engineering default*: residuals of the form S Ω Sᵀ − Ω can be amplified
    or attenuated depending on the perturbation direction and ‖S‖, so a matrix
    that is "structurally almost symplectic" may pass or fail near the
    boundary. Callers that need scale-aware checks should set ``atol``
    explicitly (e.g. ``atol=1e-8 * max(1.0, ‖S‖²)``) or use a relative metric.
    """
    S = np.asarray(S, dtype=float)
    if S.ndim != 2 or S.shape[0] != S.shape[1] or S.shape[0] % 2 != 0:
        return False
    m = S.shape[0] // 2
    Om = omega(m)
    return np.allclose(S @ Om @ S.T, Om, atol=atol, rtol=0.0)


def validate_symplectic(S: np.ndarray, *, atol: float = 1e-8) -> None:
    """Raise ValueError if S is not symplectic (see ``is_symplectic`` for atol)."""
    S = np.asarray(S, dtype=float)
    if S.ndim != 2 or S.shape[0] != S.shape[1] or S.shape[0] % 2 != 0:
        raise ValueError(
            f"S must be square with even dimension, got shape {getattr(S, 'shape', None)}"
        )
    if not is_symplectic(S, atol=atol):
        raise ValueError("S is not symplectic: S Ω Sᵀ ≠ Ω (xxpp)")


def d_displace(nmode: int, alpha: complex, mode: int = 0) -> np.ndarray:
    """Displacement vector d: d_x=√2 Re α, d_p=√2 Im α."""
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    alpha = complex(alpha)
    d = np.zeros(2 * nmode, dtype=float)
    d[mode] = np.sqrt(2.0) * alpha.real
    d[nmode + mode] = np.sqrt(2.0) * alpha.imag
    return d


def S_squeeze(nmode: int, r: float, mode: int = 0) -> np.ndarray:
    """Single-mode squeeze: x→e^{-r}x, p→e^{r}p."""
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    S = np.eye(2 * nmode)
    S[mode, mode] = np.exp(-r)
    S[nmode + mode, nmode + mode] = np.exp(r)
    return S


def S_phase(nmode: int, theta: float, mode: int = 0) -> np.ndarray:
    """Single-mode phase rotation in (x,p) plane."""
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    c, s = np.cos(theta), np.sin(theta)
    S = np.eye(2 * nmode)
    i, p = mode, nmode + mode
    S[i, i], S[i, p] = c, -s
    S[p, i], S[p, p] = s, c
    return S


def S_beamsplitter(
    nmode: int,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> np.ndarray:
    """Two-mode BS from unitary U embedded as xxpp symplectic.

    U = [[c, e^{iφ}s], [-e^{-iφ}s, c]], then
    S = [[Re U, -Im U], [Im U, Re U]] on the two-mode subspace.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    for m in (mode1, mode2):
        if not 0 <= m < nmode:
            raise IndexError(f"mode {m} out of range for nmode={nmode}")

    c, s = np.cos(theta), np.sin(theta)
    eip = np.exp(1j * phi)
    U = np.array(
        [[c, eip * s], [-np.conj(eip) * s, c]],
        dtype=complex,
    )
    Ru, Iu = U.real, U.imag

    ReU = np.eye(nmode)
    ImU = np.zeros((nmode, nmode))
    pair = [mode1, mode2]
    for a in range(2):
        for b in range(2):
            ReU[pair[a], pair[b]] = Ru[a, b]
            ImU[pair[a], pair[b]] = Iu[a, b]

    return np.block([[ReU, -ImU], [ImU, ReU]])


def S_two_mode_squeeze(
    nmode: int, r: float, mode1: int, mode2: int
) -> np.ndarray:
    """Two-mode squeeze S₂(r) in xxpp (real r), EPR form.

    On (x_i, x_j, p_i, p_j):
      x_i' = ch x_i + sh x_j,  x_j' = sh x_i + ch x_j
      p_i' = ch p_i - sh p_j,  p_j' = -sh p_i + ch p_j
    Vacuum: ⟨n_i⟩=⟨n_j⟩=sinh²r; cross ⟨x_i x_j⟩, ⟨p_i p_j⟩ ≠ 0.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    for m in (mode1, mode2):
        if not 0 <= m < nmode:
            raise IndexError(f"mode {m} out of range for nmode={nmode}")

    ch, sh = np.cosh(r), np.sinh(r)
    S = np.eye(2 * nmode)
    i, j = mode1, mode2
    pi, pj = nmode + i, nmode + j
    idx = [i, j, pi, pj]
    block = np.array(
        [
            [ch, sh, 0.0, 0.0],
            [sh, ch, 0.0, 0.0],
            [0.0, 0.0, ch, -sh],
            [0.0, 0.0, -sh, ch],
        ],
        dtype=float,
    )
    for a in range(4):
        for b in range(4):
            S[idx[a], idx[b]] = block[a, b]
    return S


def S_CZ(nmode: int, weight: float, mode1: int, mode2: int) -> np.ndarray:
    """Controlled-Z symplectic in xxpp: CZ = exp(i·weight·x̂₁·x̂₂).

    Action: x unchanged; p₁ → p₁ + weight·x₂, p₂ → p₂ + weight·x₁.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    for m in (mode1, mode2):
        if not 0 <= m < nmode:
            raise IndexError(f"mode {m} out of range for nmode={nmode}")

    S = np.eye(2 * nmode)
    i, j = mode1, mode2
    S[nmode + i, j] = weight
    S[nmode + j, i] = weight
    return S


def S_CX(nmode: int, weight: float, mode1: int, mode2: int) -> np.ndarray:
    """Controlled-X symplectic in xxpp: CX = exp(-i·weight·x̂₁·p̂₂).

    Action: x₁ unchanged, x₂ → x₂ + weight·x₁;
    p₁ → p₁ - weight·p₂, p₂ unchanged.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    for m in (mode1, mode2):
        if not 0 <= m < nmode:
            raise IndexError(f"mode {m} out of range for nmode={nmode}")

    S = np.eye(2 * nmode)
    i, j = mode1, mode2
    S[j, i] = weight
    S[nmode + i, nmode + j] = -weight
    return S


# ---------------------------------------------------------------------------
# Passive interferometers: U(m) → Sp(2m) embed (xxpp)
# ---------------------------------------------------------------------------


def is_unitary(U: np.ndarray, *, atol: float = 1e-8) -> bool:
    """Return True if U†U ≈ I and UU† ≈ I."""
    U = np.asarray(U, dtype=complex)
    if U.ndim != 2 or U.shape[0] != U.shape[1]:
        return False
    m = U.shape[0]
    eye = np.eye(m, dtype=complex)
    return bool(
        np.allclose(U.conj().T @ U, eye, atol=atol)
        and np.allclose(U @ U.conj().T, eye, atol=atol)
    )


def validate_unitary(U: np.ndarray, *, atol: float = 1e-8) -> None:
    """Raise ValueError if U is not unitary."""
    U = np.asarray(U, dtype=complex)
    if U.ndim != 2 or U.shape[0] != U.shape[1]:
        raise ValueError(f"U must be square, got shape {U.shape}")
    if not is_unitary(U, atol=atol):
        raise ValueError("U is not unitary: U†U ≠ I")


def S_from_unitary(
    U: np.ndarray, *, validate: bool = True, atol: float = 1e-8
) -> np.ndarray:
    """Embed passive unitary U (m×m complex) as xxpp symplectic S (2m×2m).

    With â → U â:

        S = [[Re U, -Im U],
             [Im U,  Re U]]

    Same layout as ``S_beamsplitter``'s 2-mode block.
    """
    U = np.asarray(U, dtype=complex)
    if validate:
        validate_unitary(U, atol=atol)
    elif U.ndim != 2 or U.shape[0] != U.shape[1]:
        raise ValueError(f"U must be square, got shape {U.shape}")
    Ru, Iu = np.real(U), np.imag(U)
    return np.asarray(np.block([[Ru, -Iu], [Iu, Ru]]), dtype=float)


def U_beamsplitter(theta: float, phi: float = 0.0) -> np.ndarray:
    """2×2 unitary matching ``S_beamsplitter`` convention.

    U = [[c, e^{iφ} s], [-e^{-iφ} s, c]] with c=cos θ, s=sin θ.
    """
    c, s = np.cos(theta), np.sin(theta)
    eip = np.exp(1j * phi)
    return np.array([[c, eip * s], [-np.conj(eip) * s, c]], dtype=complex)


def embed_U_2mode(m: int, mode1: int, mode2: int, U2: np.ndarray) -> np.ndarray:
    """Embed a 2×2 unitary on (mode1, mode2) into m×m."""
    U = np.eye(m, dtype=complex)
    U[np.ix_([mode1, mode2], [mode1, mode2])] = np.asarray(U2, dtype=complex)
    return U


def _nulling_T_for_column(v0: complex, v1: complex, atol: float) -> np.ndarray:
    """Unitary T with first column parallel to (v0, v1).

    Then T† @ (v0, v1) has vanishing second component.
    """
    v = np.array([v0, v1], dtype=complex)
    nrm = np.linalg.norm(v)
    if nrm < atol:
        return np.eye(2, dtype=complex)
    e0 = v / nrm
    e1 = np.array([-np.conj(e0[1]), np.conj(e0[0])], dtype=complex)
    return np.column_stack([e0, e1])


def reck_decomposition(U: np.ndarray, *, atol: float = 1e-10) -> list[tuple]:
    """Reck triangular factorization into 2-mode unitaries + diagonal phases.

    Returns ops in **state-apply order** (first list element applied first):

        compose_unitary_mesh(m, ops) ≈ U

    so that successive ``a ← Op a`` yields ``a ← U a``.

    Each op is one of:

    - ``("u2", i, j, U2)`` — embed 2×2 unitary U2 on modes (i, j)
    - ``("phase", i, theta)`` — mode i multiplied by e^{+i theta} (``S_phase`` angle)
    - ``("bs", i, j, theta, phi)`` — also accepted by ``compose_unitary_mesh``

    Algorithm: left-multiply peels ``U ← T† U`` to null ``U[j,i]`` (j>i), giving
    matrix factorization ``U = T1 T2 … Tk D``. State-apply order is therefore
    ``D``, then ``Tk … T1`` (right-to-left). Phase-1 ships Reck (vision OK).
    """
    U = np.asarray(U, dtype=complex).copy()
    validate_unitary(U, atol=max(atol, 1e-8))
    m = U.shape[0]
    ts: list[tuple] = []

    # Peel from the left: U ← T† @ U nulls U[j, i]; then U_old = T @ U_new
    for i in range(m - 1):
        for j in range(m - 1, i, -1):
            T = _nulling_T_for_column(U[i, i], U[j, i], atol)
            Tfull = embed_U_2mode(m, i, j, T)
            U = Tfull.conj().T @ U
            ts.append(("u2", i, j, T.copy()))

    phases: list[tuple] = []
    for k in range(m):
        pk = U[k, k]
        # Match S_phase(theta): â → e^{+i theta} â ⇔ S_from_unitary(diag(e^{iθ}))
        theta_k = float(np.angle(pk)) if abs(pk) > atol else 0.0
        phases.append(("phase", k, theta_k))

    # U = T1…Tk D  => apply D first, then Tk…T1
    return phases + list(reversed(ts))


def compose_unitary_mesh(m: int, ops: list[tuple]) -> np.ndarray:
    """Compose mesh ops into m×m unitary.

    ``ops`` are in state-apply order (first applied first). The resulting matrix
    satisfies a ↦ U a with U = Op_n @ … @ Op_1.

    Phase op ``("phase", i, theta)`` means ``S_phase`` angle: mode factor e^{+iθ}.
    """
    U = np.eye(m, dtype=complex)
    for op in ops:
        kind = op[0]
        if kind == "u2":
            _, i, j, U2 = op
            Op = embed_U_2mode(m, i, j, U2)
        elif kind == "bs":
            _, i, j, theta, phi = op
            Op = embed_U_2mode(m, i, j, U_beamsplitter(theta, phi))
        elif kind == "phase":
            _, i, theta = op
            Op = np.eye(m, dtype=complex)
            Op[i, i] = np.exp(1j * theta)
        else:
            raise ValueError(f"unknown mesh op {kind!r}")
        # first applied is rightmost in matrix product… wait:
        # a1=Op1 a, a2=Op2 a1 => U = Op2 Op1 = Op_n @ … @ Op_1
        U = Op @ U
    return U


def clements_decomposition(
    U: np.ndarray, *, atol: float = 1e-10
) -> list[tuple]:
    """Vision name: Phase-1 implements Reck mesh under this alias.

    Rectangular Clements can replace the body later if ops stay compose-compatible.
    """
    return reck_decomposition(U, atol=atol)


def S_mach_zehnder(
    nmode: int,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> np.ndarray:
    """Mach–Zehnder symplectic on (mode1, mode2).

    Fixed decomposition:

        S = S_BS(π/4, 0) @ S_phase(φ, mode1) @ S_BS(θ, 0)

    i.e. BS(θ) then internal phase φ on mode1 then 50:50 BS.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    S1 = S_beamsplitter(nmode, mode1, mode2, theta, 0.0)
    S2 = S_phase(nmode, phi, mode1)
    S3 = S_beamsplitter(nmode, mode1, mode2, np.pi / 4, 0.0)
    return S3 @ S2 @ S1
