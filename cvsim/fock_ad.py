"""Differentiable Fock designer chain (Phase F4).

jnp mirror of the numpy Fock gate formulas in ``cvsim/fock/gates.py``
(``_squeeze_U`` / ``beamsplitter`` / ``kerr``) plus the loss superoperator
built from the numpy pre-built Kraus operators of
``cvsim/fock/channels.py``, kept minimal for the optimisation notebook:

    params → U (gates, backend=) → |ψ⟩ → ρ = ψψ† → loss(η) → cat fidelity

Formulas live upstream in ``gates.py`` / ``channels.py`` (single source of
truth); this module mirrors them on jnp so ``jax.grad`` can trace the
parameter path through squeeze/BS/Kerr weights. The numpy backend resolves
to the same math via ``cvsim.backend`` — both paths share the tests
(vision F4 exit 2). Honesty: ``squeeze_u`` reuses ``gates._squeeze_U``
directly; ``bs_u``/``kerr_diag`` duplicate formulas (no standalone numpy
helper upstream) — guarded by identity tests against the gates.

Module placement: top-level (not inside ``cvsim/fock``) because ADR-0001
forbids rep packages from importing ``cvsim.backend`` — same pattern as
Gaussian's ``cvsim/ad.py``.

Honesty notes:
- ``cat_fidelity`` targets the even cat state (|α⟩ + |−α⟩)/N (mirror of
  ``FockState.cat``); loss Kraus ops are pre-built in numpy and applied via
  jnp einsum ``'kam,mn,kbn->ab'`` — rebuilding Kraus inside jax is not
  traceable (vmap+arange hits ConcretizationError, verified 2026-08-12).
- Truncation honesty: cat fidelity is computed in the truncated basis
  (cutoff); large r/alpha leak — see ``cvsim.fock`` leakage API.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import expm as _expm_np

from cvsim.backend import _get_xp, _set
from cvsim.fock import channels
from cvsim.fock.gates import _squeeze_U


def _expm(xp, G: np.ndarray) -> np.ndarray:
    """Matrix exponential: scipy for numpy; jax.scipy.linalg for jax (lazy)."""
    if xp is np:
        return _expm_np(G)
    import jax.scipy.linalg as jsl  # lazy: jax touched only on the jax path
    return jsl.expm(G)

def _annihilation(xp, N: int) -> np.ndarray:
    """Truncated a with a|n⟩ = √n |n−1⟩ — mirror of ``gates.annihilation``."""
    return xp.diag(xp.sqrt(xp.arange(1.0, N)), 1).astype(complex)

def squeeze_u(backend: str, N: int, r: float) -> np.ndarray:
    """Single-mode squeeze unitary S(r) = exp(½r(a² − a†²)), shape (N, N).

    numpy backend reuses the source of truth ``gates._squeeze_U``;
    jax mirrors the same formula on jnp (differentiable in r).
    """
    xp = _get_xp(backend)
    if xp is np:
        return _squeeze_U(N, r)
    a = _annihilation(xp, N)
    return _expm(xp, 0.5 * r * (a @ a - a.conj().T @ a.conj().T))

def bs_u(backend: str, N: int, theta: float, phi: float = 0.0) -> np.ndarray:
    """Two-mode BS(θ, φ) = exp[θ(e^{iφ} a0† a1 − h.c.)], shape (N², N²).

    Mirror of the generator in ``gates.beamsplitter`` (no standalone helper
    upstream, so the formula is duplicated here and guarded by identity
    tests against the gate); jax path is the same formula on jnp
    (kron + expm), differentiable in θ/φ.
    """
    xp = _get_xp(backend)
    a = _annihilation(xp, N)
    eye = xp.eye(N, dtype=complex)
    a0 = xp.kron(a, eye)
    a1 = xp.kron(eye, a)
    eip = xp.exp(1j * phi)
    G = theta * (eip * a0.conj().T @ a1 - xp.conj(eip) * a1.conj().T @ a0)
    return _expm(xp, G)

def kerr_diag(backend: str, N: int, chi: float) -> np.ndarray:
    """Kerr phases diag(e^{iχ n²}) — |n⟩ ↦ e^{iχ n²}|n⟩ (mirror of gates.kerr).

    Diagonal by construction; same formula on both backends.
    """
    xp = _get_xp(backend)
    n = xp.arange(N)
    return xp.diag(xp.exp(1j * chi * n * n))

def _cat_amps(xp, N: int, alpha: complex) -> np.ndarray:
    """Even cat (|α⟩ + |−α⟩)/√(2(1+e^{−2|α|²})) amplitudes, normalized.

    c_n = e^{−|α|²/2}·(1+(−1)ⁿ)·αⁿ/√n! / √(2(1+e^{−2|α|²})) — mirror of
    ``FockState.cat`` (odd n vanish).
    """
    n = xp.arange(N)
    fact = xp.concatenate([xp.ones(1), xp.cumprod(xp.arange(1.0, N))])
    return (
        xp.exp(-abs(alpha) ** 2 / 2.0)
        / xp.sqrt(2.0 * (1.0 + xp.exp(-2.0 * abs(alpha) ** 2)))
        * (1.0 + (-1.0) ** n)
        * alpha**n
        / xp.sqrt(fact)
    )

def _loss_superop(xp, rho: np.ndarray, T: float) -> np.ndarray:
    """ρ' = Σ_k E_k ρ E_k† (1-mode loss, transmissivity T).

    Kraus ops pre-built in numpy as a constant tensor (mirror of
    ``channels._kraus_ops`` / ``_apply_kraus_1mode``), applied by einsum
    ``'kam,mn,kbn->ab'`` so the jax path stays traceable.
    """
    N = rho.shape[0]
    K = np.stack(channels._kraus_ops(N, T))
    return xp.einsum("kam,mn,kbn->ab", K, rho, xp.conj(K))

def cat_fidelity(
    backend: str, r: float, chi: float, *, alpha: complex, T: float = 1.0,
    cutoff: int = 12,
) -> float:
    """Fidelity of squeeze(r) → Kerr(χ) → loss(T) state vs even cat |α⟩+|−α⟩.

    Chain: |ψ⟩ = K(χ)·S(r)|0⟩, ρ = |ψ⟩⟨ψ| → loss(T) → F = ⟨cat|ρ|cat⟩.

    The cat amplitudes are inlined on jnp (5 lines, see ``_cat_amps``) so
    ``jax.grad`` can trace the full chain; the numpy path is the same math
    and is guarded by identity tests against ``FockState.cat``.

    Honesty: F is a truncated-basis fidelity (cutoff); check leakage for
    large r/alpha via ``cvsim.fock`` leakage API.
    """
    xp = _get_xp(backend)
    vac = xp.zeros(cutoff, dtype=complex)
    vac = _set(xp, vac, (0,), 1.0)
    psi = kerr_diag(backend, cutoff, chi) @ (squeeze_u(backend, cutoff, r) @ vac)
    rho = xp.outer(psi, xp.conj(psi))
    if T < 1.0:
        rho = _loss_superop(xp, rho, T)
    cat = _cat_amps(xp, cutoff, alpha)
    return xp.real(xp.conj(cat) @ rho @ cat)

def bs_overlap(backend: str, theta: float, *, cutoff: int = 8) -> float:
    """|⟨0,1| BS(θ) |1,0⟩|² = sin²θ — BS gradient test chain.

    |1,0⟩ → BS(θ) → amplitude of |0,1⟩ (row-major vec index n0·N + n1).
    """
    xp = _get_xp(backend)
    N = cutoff
    psi = xp.zeros((N, N), dtype=complex)
    psi = _set(xp, psi, (1, 0), 1.0)
    vec = psi.reshape(N * N)
    out = bs_u(backend, N, theta) @ vec
    return xp.abs(out[1]) ** 2  # |⟨0,1|ψ⟩|²
