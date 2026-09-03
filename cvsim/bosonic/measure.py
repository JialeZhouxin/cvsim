"""Bosonic measurements (A4): homodyne + heterodyne + threshold.

Homodyne implementation lives in ``observables.py`` (CDF grid inversion
exact edge distribution, B3); this module re-exports it so
``cvsim.bosonic.homodyne_*`` import paths are unchanged.

Heterodyne (ADR-0007) is **exact**: the full component sum
Q(β) = Σ_k w_k Q_k(β) is evaluated on a 2D (x, p) grid, with complex
centres analytically continued — cross/interference components contribute
their fringe terms; Hermitian-pair closure guarantees Im ≈ 0. Sampling is
sequential CDF inversion (marginal x, then conditional p | x). Conditioning
reweights by the same per-component complex Gaussian kernel and removes the
measured mode. The old teaching cut (real-diagonal pool) is removed.

Threshold is outcome-only ({0,1}, no state update); the post-click state
leaves the Gaussian mixture manifold.
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.observables import (
    _SIG_EPS,
    _as_real,
    _check_mode,
)
from cvsim.bosonic.observables import (
    homodyne_condition as homodyne_condition,  # re-export: single implementation source
)
from cvsim.bosonic.observables import (
    homodyne_mean as homodyne_mean,
)
from cvsim.bosonic.observables import (
    homodyne_pdf as homodyne_pdf,
)
from cvsim.bosonic.observables import (
    homodyne_sample as homodyne_sample,
)
from cvsim.bosonic.observables import (
    homodyne_sample_and_condition as homodyne_sample_and_condition,
)
from cvsim.bosonic.observables import (
    homodyne_var as homodyne_var,
)
from cvsim.bosonic.state import BosonicState, Component

_IM_TOL = 1e-8
_PNR_RADIUS = 0.95
_LOG_MAX = float(np.log(np.finfo(float).max))
_LOG_MIN = float(np.log(np.nextafter(0.0, 1.0)))
# Sentinel: distinguish "modes not passed" (B9 single-mode path) from an
# explicit ``modes=None`` (all-modes joint). ``mode``/``modes`` are selected
# by this, keeping ``pnr_probs(state)`` and ``pnr_probs(state, mode=j)``
# byte-compatible with B9 while adding a joint tensor path.
_MODES_DEFAULT = object()
_MODE_DEFAULT = object()

# ---------------------------------------------------------------------------
# photon-number resolving measurement — probability only
# ---------------------------------------------------------------------------


def _pnr_cutoff(cutoff: object) -> int:
    """Validate PNR coefficient count without accepting bool as an integer."""
    if not isinstance(cutoff, (int, np.integer)) or isinstance(cutoff, bool) or cutoff < 1:
        raise ValueError(f"cutoff must be a positive int, got {cutoff!r}")
    return int(cutoff)


def _pnr_mode(state: BosonicState, mode: object) -> int:
    """Validate PNR mode and keep public invalid-mode errors consistent."""
    if not isinstance(mode, (int, np.integer)) or isinstance(mode, bool):
        raise IndexError(f"mode {mode!r} is not a valid mode index")
    mode_i = int(mode)
    _check_mode(state, mode_i)
    return mode_i


def _pnr_component_log_generating(
    V: np.ndarray, rbar: np.ndarray, t: complex
) -> complex:
    """Return complex logarithm of one Gaussian component's ``G(t)``.

    ``rbar.T`` is intentional: complex component centres use analytic
    transpose quadratic form, not a conjugate transpose. The logarithm keeps
    large complex-centre terms representable until component weights are
    applied; this matters for finite GKP cross components whose weight and
    generating function can separately underflow/overflow while their product
    is finite.
    """
    V = np.asarray(V, dtype=float)
    r = np.asarray(rbar, dtype=complex)
    if V.shape != (2, 2) or r.shape != (2,):
        raise ValueError(
            f"pnr component must have V shape (2, 2) and rbar shape (2,), got "
            f"{V.shape} and {r.shape}"
        )
    if not np.all(np.isfinite(V)) or not np.all(np.isfinite(r)):
        raise ValueError("pnr_probs: component V/rbar contains non-finite values")
    if float(np.min(np.linalg.eigvalsh(V))) <= 0.0:
        raise ValueError("pnr_probs: component covariance must be positive-definite")

    try:
        with np.errstate(all="raise"):
            A = np.linalg.inv(V)
            c = (1.0 - t) / (1.0 + t)
            B = A + 2.0 * c * np.eye(2)
            det_term = np.linalg.det(V) * np.linalg.det(B)
            Ab = A @ r
            exponent = -0.5 * (r @ Ab) + 0.5 * (Ab @ np.linalg.solve(B, Ab))
            log_prefactor = np.log(2.0) - np.log(1.0 + t) - 0.5 * np.log(det_term)
            value = complex(log_prefactor + exponent)
    except (FloatingPointError, np.linalg.LinAlgError, ZeroDivisionError) as exc:
        raise ValueError("pnr_probs: generating function is not representable") from exc
    if not np.all(np.isfinite([value.real, value.imag])):
        raise ValueError("pnr_probs: generating function produced a non-finite value")
    return value

def _pnr_joint_component_log_generating(
    A: np.ndarray, rbar: np.ndarray, ts: np.ndarray
) -> complex:
    """log G(t⃗) for one Gaussian component over a single multi-mode point.

    Kept as a scalar reference for the single-point path; the grid path uses
    ``_pnr_component_log_grid`` (batched over all Cauchy points). ``A = V⁻¹``.
    """
    return complex(_pnr_component_log_grid(A, rbar, ts.reshape(1, -1))[0])


def _pnr_component_log_grid(
    A: np.ndarray, rbar: np.ndarray, flat: np.ndarray
) -> np.ndarray:
    """Vectorised log G(t⃗) for one Gaussian component on a flat multi-axis grid.

    ``flat`` has shape ``(n_grid, k)``; each row is one Cauchy point
    ``t⃗ = (t_{j_1}, …, t_{j_k})``. Returns an ``(n_grid,)`` complex array of
    ``log G`` values. ``A = V⁻¹`` is t-independent (pre-inverted once).

    ``B = A + 2 Σ_j c_j P_j`` and ``quad = −½ r̄ᵀAr̄ + ½ (Ar̄)ᵀB⁻¹(Ar̄)``. The
    logarithm keeps large complex-centre terms representable until weights apply.
    """
    A = np.asarray(A, dtype=complex)
    r = np.asarray(rbar, dtype=complex)
    flat = np.asarray(flat, dtype=complex)
    dim = A.shape[0]
    if A.shape[0] != A.shape[1] or A.shape[0] % 2 != 0:
        raise ValueError("pnr joint component A=V⁻¹ must be square even-dimensional")
    if r.ndim != 1 or r.shape[0] != dim:
        raise ValueError("pnr joint component: A/rbar shape mismatch")
    if flat.ndim != 2 or flat.shape[1] != dim // 2:
        raise ValueError("pnr joint component: flat grid shape mismatch")
    if not np.all(np.isfinite(A)) or not np.all(np.isfinite(r)) or not np.all(np.isfinite(flat)):
        raise ValueError("pnr_probs: joint component contains non-finite values")
    if float(np.min(np.linalg.eigvalsh(A.real))) <= 0.0:
        raise ValueError("pnr_probs: component covariance must be positive-definite")
    k = flat.shape[1]
    n_grid = flat.shape[0]
    try:
        with np.errstate(all="raise"):
            c = (1.0 - flat) / (1.0 + flat)          # (n_grid, k)
            B = np.broadcast_to(A[None, :, :], (n_grid, dim, dim)).copy()
            eye2 = np.eye(2, dtype=complex)
            for jj in range(k):
                B[:, 2 * jj : 2 * jj + 2, 2 * jj : 2 * jj + 2] += (
                    (2.0 * c[:, jj])[:, None, None] * eye2
                )
            Ab = A @ r                                # (dim,)
            X = np.linalg.solve(B, Ab[None, :, None])[:, :, 0]  # (n_grid,dim)
            quad = -0.5 * (r @ Ab) + 0.5 * np.einsum("i,gi->g", Ab, X)
            detVB = np.linalg.det(B) / np.linalg.det(A.real)
            sq = np.sqrt(detVB)
            target = -np.angle(1.0 + flat).sum(axis=1)
            flip = np.abs(np.angle(sq) - target) > (np.pi / 2.0)
            sq[flip] = -sq[flip]
            prod1p = np.prod(1.0 + flat, axis=1)
            logG = k * np.log(2.0) - np.log(prod1p * sq) + quad
    except (FloatingPointError, np.linalg.LinAlgError, ZeroDivisionError) as exc:
        raise ValueError("pnr_probs: joint generating function is not representable") from exc
    if not np.all(np.isfinite(logG)):
        raise ValueError("pnr_probs: joint generating function produced a non-finite value")
    return np.asarray(logG, dtype=complex)

def _pnr_mode_seq(state: BosonicState, modes: object) -> tuple[int, ...]:
    """Validate a joint-mode selection tuple and return sorted unique indices."""
    if isinstance(modes, (bool, np.bool_)) or not isinstance(modes, (tuple, list, np.ndarray)):
        raise TypeError(f"modes must be a tuple or None, got {type(modes).__name__}")
    seq = tuple(int(x) for x in modes)
    if not seq:
        raise ValueError("modes must be a non-empty tuple of mode indices")
    for x in seq:
        if not isinstance(x, (int, np.integer)) or isinstance(x, bool):
            raise TypeError("modes elements must be integers; use mode= for a single mode")
    m = state.nmode
    for x in seq:
        if not 0 <= x < m:
            raise IndexError(f"mode {x} out of range for nmode={m}")
    if len(set(seq)) != len(seq):
        raise ValueError(f"modes contains duplicate indices: {seq}")
    return tuple(seq)



def _pnr_generating(state: BosonicState, mode: int, ts: np.ndarray) -> np.ndarray:
    """Evaluate weighted total generating function at Cauchy points.

    Component terms are summed after a per-point log-magnitude rescale. This
    preserves Hermitian interference while avoiding invalid intermediate
    ``0 * inf`` products from distant complex-centre components.
    """
    m = state.nmode
    indices = [mode, m + mode]
    out = np.zeros(ts.shape, dtype=complex)
    prepared = [
        (c.w, c.V[np.ix_(indices, indices)], c.rbar[indices])
        for c in state.components
        if c.w != 0.0
    ]
    for i, t in enumerate(ts):
        logs: list[complex] = []
        for weight, V, rbar in prepared:
            log_value = _pnr_component_log_generating(V, rbar, complex(t))
            log_weight = np.log(abs(weight)) + 1j * np.angle(weight)
            log_term = log_weight + log_value
            if not np.all(np.isfinite([log_term.real, log_term.imag])):
                raise ValueError("pnr_probs: weighted generating function is non-finite")
            logs.append(log_term)
        if not logs:
            continue
        scale = max(log_term.real for log_term in logs)
        scaled = sum(np.exp(log_term - scale) for log_term in logs)
        if not np.isfinite(scaled):
            raise ValueError("pnr_probs: weighted generating function is non-finite")
        if scaled == 0.0:
            continue
        total_log = scale + np.log(scaled)
        if not np.all(np.isfinite([total_log.real, total_log.imag])):
            raise ValueError("pnr_probs: total generating function is non-finite")
        if total_log.real < _LOG_MIN:
            continue
        if total_log.real > _LOG_MAX:
            raise ValueError("pnr_probs: total generating function is non-finite")
        try:
            with np.errstate(all="raise"):
                out[i] = np.exp(total_log)
        except FloatingPointError as exc:
            raise ValueError("pnr_probs: total generating function is non-finite") from exc
    if not np.all(np.isfinite(out)):
        raise ValueError("pnr_probs: total generating function is non-finite")
    return out

def _pnr_joint_generating(
    state: BosonicState, modes: tuple[int, ...], ts_grid: np.ndarray
) -> np.ndarray:
    """Vectorised weighted joint generating function on a multi-axis torus grid.

    ``ts_grid`` has shape ``(n_points,) * k`` and each index carries a complex
    t⃗ = (t_{j_1}, …, t_{j_k}). Per component, ``logG`` is evaluated on the
    selected-mode block (V/rbar sliced by each mode's (x, p) indices); weights
    are merged in log domain per grid point (replicates the B9
    ``_pnr_generating`` 0×inf discipline, vectorised).
    """
    m = state.nmode
    k = len(modes)
    # Collect per-(x,p) index blocks for the selected modes, in ``modes`` order.
    blk_indices = [x for mm in modes for x in (mm, m + mm)]
    prepared = [
        (c.w, c.V[np.ix_(blk_indices, blk_indices)], c.rbar[blk_indices])
        for c in state.components
        if c.w != 0.0
    ]
    # Pre-invert the component covariance once (it does not depend on t⃗); the
    # per-point kernel then handles only the t-dependent 2c·P shift. This avoids
    # re-inverting at every one of the n_points^k torus points × components.
    prepared = [
        (w, np.linalg.inv(Vc), rbar) for w, Vc, rbar in prepared
    ]
    if not prepared:
        raise ValueError("pnr_probs: state has no components with non-zero weight")
    # Vectorised kernel: process all grid points at once per component.
    # Each component's logG is a (n_points,)*k array; we add log-weight and
    # merge across components in log domain (replicates B9 0×inf discipline).
    shape = ts_grid.shape[:-1]
    flat = ts_grid.reshape(-1, k)          # (n_grid, k) complex
    n_grid = flat.shape[0]
    log_terms = np.empty((len(prepared), n_grid), dtype=complex)
    for pi, (weight, A, rbar) in enumerate(prepared):
        log_terms[pi] = _pnr_component_log_grid(A, rbar, flat)
        lw = np.log(abs(weight)) + 1j * np.angle(weight)
        log_terms[pi] += lw
    if not np.all(np.isfinite(log_terms)):
        raise ValueError("pnr_probs: joint weighted generating function is non-finite")
    scale = np.max(log_terms.real, axis=0)
    scaled = np.sum(np.exp(log_terms - scale), axis=0)
    total_log = scale + np.log(scaled)
    out_flat = np.zeros(n_grid, dtype=complex)
    finite = np.isfinite(total_log.real) & np.isfinite(total_log.imag)
    lo = total_log.real < _LOG_MIN
    hi = (total_log.real > _LOG_MAX) & finite
    ok = finite & (~lo) & (~hi)
    if np.any(hi):
        raise ValueError("pnr_probs: joint total generating function is non-finite")
    try:
        with np.errstate(all="raise"):
            out_flat[ok] = np.exp(total_log[ok])
    except FloatingPointError as exc:
        raise ValueError("pnr_probs: joint total generating function is non-finite") from exc
    if not np.all(np.isfinite(out_flat)):
        # Any *kept* point must be finite; points below _LOG_MIN are zero.
        kept = ok
        if np.any(~np.isfinite(out_flat[kept])):
            raise ValueError("pnr_probs: joint total generating function is non-finite")
    return out_flat.reshape(shape)

def _pnr_joint_n_points(cutoff: int) -> int:
    return max(128, 8 * cutoff)

def _pnr_joint_probs(
    state: BosonicState, modes: tuple[int, ...], cutoff: int
) -> np.ndarray:
    """Joint P(n⃗) on the selected modes via per-axis Cauchy extraction."""
    k = len(modes)
    n_points = _pnr_joint_n_points(cutoff)
    theta = 2.0 * np.pi * np.arange(n_points, dtype=float) / n_points
    # Multi-axis torus grid: shape (n_points,)*k, each point carrying a complex
    # t⃗ = (t_{j_1}, …, t_{j_k}) in a trailing (k,) axis.
    ts_grid = np.empty((n_points,) * k + (k,), dtype=complex)
    for idx_arr in np.ndindex(*((n_points,) * k)):
        ts = _PNR_RADIUS * np.exp(1j * theta[np.asarray(idx_arr)])
        ts_grid[idx_arr] = ts
    values = _pnr_joint_generating(state, modes, ts_grid)
    coeffs = np.fft.fftn(values) / (n_points**k)
    slices = tuple(slice(0, cutoff) for _ in range(k))
    probs = np.asarray(coeffs[slices])
    # Radius correction per axis: divide by radius**(n_1+…+n_k).
    ns = [np.arange(cutoff, dtype=float)] * k
    meshes = np.meshgrid(*ns, indexing="ij")
    corr = np.zeros_like(meshes[0])
    for gm in meshes:
        corr += gm
    probs = probs / (_PNR_RADIUS ** corr)
    if not np.all(np.isfinite(probs)):
        raise ValueError("pnr_probs: extracted joint probabilities are non-finite")
    imag_max = float(np.max(np.abs(probs.imag))) if probs.size else 0.0
    if imag_max > _IM_TOL:
        raise ValueError(f"pnr_probs has large imaginary part: max |Im|={imag_max:.3e}")
    probs = np.asarray(probs.real, dtype=np.float64)
    scale = max(1.0, float(np.max(np.abs(probs))))
    negative = probs < 0.0
    if np.any(negative):
        if float(np.min(probs)) < -1e-10 * scale:
            raise ValueError(
                f"pnr_probs produced a negative probability: min={float(np.min(probs)):.3e}"
            )
        probs[negative] = 0.0
    return probs

def _pnr_joint_sample(
    state: BosonicState, modes: tuple[int, ...], cutoff: int, rng: np.random.Generator
) -> tuple[int, ...]:
    """Sequential marginal-condition sampling on a joint PNR tensor.

    Draw n_1 from the marginal of mode 1 (all other modes summed), then
    n_2 from the conditional P(n_2 | n_1), and so on. Uses the joint
    ``pnr_probs`` tensor so each conditional is exact on the same lattice.
    """
    joint = _pnr_joint_probs(state, modes, cutoff)
    if joint.ndim == 1:
        total = float(np.sum(joint))
        if not np.isfinite(total) or total <= _SIG_EPS:
            raise ValueError("pnr_sample: probability mass within cutoff is ~0")
        return (int(rng.choice(joint.size, p=joint / total)),)
    seq: list[int] = []
    for _step in range(joint.ndim):
        # Marginal at this step: sum over all remaining (rightmost) axes.
        marg = joint
        if seq:
            # Slice to the already-chosen leading indices.
            idx = tuple(seq)
            marg = joint[idx]
        if marg.ndim > 1:
            marg = marg.sum(axis=tuple(range(1, marg.ndim)))
        total = float(np.sum(marg))
        if not np.isfinite(total) or total <= _SIG_EPS:
            raise ValueError("pnr_sample: probability mass within cutoff is ~0")
        pick = int(rng.choice(marg.size, p=marg / total))
        seq.append(pick)
    return tuple(seq)


def pnr_probs(
    state: BosonicState,
    mode: int | object = _MODE_DEFAULT,
    *,
    modes: tuple[int, ...] | int | None | object = _MODES_DEFAULT,
    cutoff: int = 30,
) -> np.ndarray:
    """Return first ``cutoff`` photon-number probabilities.

    Selecting a distribution
    ------------------------
    - ``mode=j`` (default): single-mode marginal over mode ``j`` (B9 path).
    - ``modes=None``: joint distribution over **all** modes, shape
      ``(cutoff,)*nmode``.
    - ``modes=(j, …, k)``: joint distribution over the selected mode subset,
      shape ``(cutoff,)*len(modes)``. A length-1 tuple is allowed and goes
      through the tensor path (``(cutoff,)``).

    ``mode`` and ``modes`` are mutually exclusive (``TypeError`` if both). The
    returned tensor is not renormalised; omitted tail mass is expected for
    finite ``cutoff``.

    Component generating functions are summed before Cauchy extraction, so
    complex centres and weights retain interference terms.
    """
    if modes is not _MODES_DEFAULT and mode is not _MODE_DEFAULT:
        raise TypeError("mode and modes are mutually exclusive")
    cutoff_i = _pnr_cutoff(cutoff)
    if modes is _MODES_DEFAULT:
        # B9 single-mode path (byte-compatible).
        mode_i = _pnr_mode(state, 0 if mode is _MODE_DEFAULT else mode)
        n_points = max(128, 8 * cutoff_i)
        theta = 2.0 * np.pi * np.arange(n_points, dtype=float) / n_points
        ts = _PNR_RADIUS * np.exp(1j * theta)
        values = _pnr_generating(state, mode_i, ts)
        coeffs = np.fft.fft(values)[:cutoff_i] / n_points
        coeffs = coeffs / (_PNR_RADIUS ** np.arange(cutoff_i, dtype=float))
        if not np.all(np.isfinite(coeffs)):
            raise ValueError("pnr_probs: extracted probabilities are non-finite")
        imag_max = float(np.max(np.abs(coeffs.imag))) if coeffs.size else 0.0
        if imag_max > _IM_TOL:
            raise ValueError(f"pnr_probs has large imaginary part: max |Im|={imag_max:.3e}")
        probs = np.asarray(coeffs.real, dtype=np.float64)
        scale = max(1.0, float(np.max(np.abs(probs))))
        negative = probs < 0.0
        if np.any(negative):
            if float(np.min(probs)) < -1e-10 * scale:
                raise ValueError(
                    f"pnr_probs produced a negative probability: min={float(np.min(probs)):.3e}"
                )
            probs[negative] = 0.0
        return probs

    # Joint path: resolve ``modes`` (None → all modes, tuple → subset).
    seq = tuple(range(state.nmode)) if modes is None else _pnr_mode_seq(state, modes)
    return _pnr_joint_probs(state, seq, cutoff_i)


def pnr_sample(
    state: BosonicState,
    mode: int | object = _MODE_DEFAULT,
    *,
    modes: tuple[int, ...] | int | None | object = _MODES_DEFAULT,
    cutoff: int = 30,
    rng: np.random.Generator | None = None,
) -> int | tuple[int, ...]:
    """Draw a photon-number outcome.

    - Single-mode path (no ``modes``): returns ``int`` (B9 compatible).
    - Joint path (``modes=None`` or a tuple): sequential marginal-condition
      sampling over the marginal / conditional tensors, returns
      ``tuple[int, ...]``.

    Finite-``cutoff`` mass is normalised within the returned distribution.
    """
    if modes is not _MODES_DEFAULT and mode is not _MODE_DEFAULT:
        raise TypeError("mode and modes are mutually exclusive")
    if rng is None:
        rng = np.random.default_rng()
    if modes is _MODES_DEFAULT:
        probs = pnr_probs(state, mode, cutoff=cutoff)
        total = float(np.sum(probs))
        if not np.isfinite(total) or total <= _SIG_EPS:
            raise ValueError("pnr_sample: probability mass within cutoff is ~0")
        probabilities = probs / total
        return int(rng.choice(probabilities.size, p=probabilities))

    seq = tuple(range(state.nmode)) if modes is None else _pnr_mode_seq(state, modes)
    return _pnr_joint_sample(state, seq, cutoff, rng)

# ---------------------------------------------------------------------------
# heterodyne — exact 2D Q-surface (ADR-0007)
# ---------------------------------------------------------------------------


def _xp_indices(nmode: int, mode: int) -> list[int]:
    """xxpp indices of (x_k, p_k) for logical mode k."""
    return [mode, nmode + mode]


def _as_beta(outcome: complex | float | np.ndarray) -> complex:
    """Normalize heterodyne outcome to complex β."""
    if isinstance(outcome, np.ndarray):
        if outcome.shape != (2,):
            raise ValueError(
                f"heterodyne real outcome must be shape (2,) [x,p], got {outcome.shape}"
            )
        return complex((outcome[0] + 1j * outcome[1]) / np.sqrt(2.0))
    return complex(outcome)


def _beta_to_xp(beta: complex) -> np.ndarray:
    """Map β → (x, p) with x = √2 Re β, p = √2 Im β (ħ=1)."""
    b = complex(beta)
    return np.array([np.sqrt(2.0) * b.real, np.sqrt(2.0) * b.imag], dtype=float)


def _q_edge_params(state: BosonicState, mode: int) -> list[tuple[np.ndarray, np.ndarray, complex]]:
    """Per-component (Σ_k, r̄_k, w_k) of the heterodyne Q kernel.

    Σ_k = V_A,k + I/2 (vacuum smearing of the 8-port detector, ħ=1);
    r̄_k is the (possibly complex) mode-A mean; w_k the complex weight.
    """
    m = _check_mode(state, mode)
    idx = _xp_indices(m, mode)
    out: list[tuple[np.ndarray, np.ndarray, complex]] = []
    for c in state.components:
        VA = c.V[np.ix_(idx, idx)]
        Sigma = VA + 0.5 * np.eye(2)
        Sigma = 0.5 * (Sigma + Sigma.T)
        out.append((Sigma, c.rbar[idx].copy(), c.w))
    return out


def _auto_grid_2d(
    params: list[tuple[np.ndarray, np.ndarray, complex]],
) -> tuple[np.ndarray, np.ndarray]:
    """Auto grid: δ ≤ σ_min/5 per axis, centroid ± 6σ_max.

    σ per axis from the Q-edge marginal std sqrt(Σ_ii); centroid from the
    real-part weighted mean (Hermitian closure cancels imaginary parts).

    ponytail: uniform grid, no 2D adaptivity — if small-ε GKP blows up the
    point count, upgrade to per-axis adaptive subdivision.
    """
    sig_x = [float(np.sqrt(S[0, 0])) for (S, _, _) in params]
    sig_p = [float(np.sqrt(S[1, 1])) for (S, _, _) in params]
    ws = np.array([w for (_, _, w) in params], dtype=complex)
    wsum = ws.sum()
    if abs(wsum) < _SIG_EPS:
        raise ValueError("heterodyne: weight sum ~ 0")
    rx = np.array([r[0].real for (_, r, _) in params])
    rp = np.array([r[1].real for (_, r, _) in params])
    cx = float(np.real(ws @ rx) / wsum.real)
    cp = float(np.real(ws @ rp) / wsum.real)
    dx = min(sig_x) / 5.0
    dp = min(sig_p) / 5.0
    nx = int(np.ceil(12.0 * max(sig_x) / dx)) + 1
    npp = int(np.ceil(12.0 * max(sig_p) / dp)) + 1
    xs = np.linspace(cx - 6.0 * max(sig_x), cx + 6.0 * max(sig_x), nx)
    ps = np.linspace(cp - 6.0 * max(sig_p), cp + 6.0 * max(sig_p), npp)
    return xs, ps


def heterodyne_pdf(
    state: BosonicState,
    mode: int = 0,
    *,
    n_grid: int | None = None,
    lim: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact Husimi Q(β) on a 2D grid: ``(xs, ps, Q)`` with ``Q[i, j] = Q(x_i, p_j)``.

    S(x,p) = Σ_k w_k Q_k(x,p), Q_k = N(z; r̄_k, Σ_k) with complex r̄_k
    (analytic continuation: cross components carry the fringe phase).
    Hermitian-pair closure ensures Im(S) ≈ 0 (checked, tol 1e-8).
    Q = max(Re S, 0); negative leaks warned with mass estimate.

    Grid auto (default): δ ≤ σ_min/5 per axis, centroid ± 6σ_max.
    Override ``n_grid``/``lim`` to force ``np.linspace(-lim, lim, n_grid)``
    on both axes (mirror of ``homodyne_pdf``).
    """
    import warnings

    if n_grid is not None and lim is not None:
        if n_grid < 3:
            raise ValueError("n_grid must be >= 3")
        xs = np.linspace(-lim, lim, int(n_grid))
        ps = np.linspace(-lim, lim, int(n_grid))
    elif n_grid is not None or lim is not None:
        raise ValueError("heterodyne_pdf: n_grid and lim must be both set or both None")
    else:
        params = _q_edge_params(state, mode)
        xs, ps = _auto_grid_2d(params)

    params = _q_edge_params(state, mode)
    S = np.zeros((xs.size, ps.size), dtype=complex)
    for Sigma, r, w in params:
        invS = np.linalg.inv(Sigma)
        ZX = xs[:, None] - r[0]  # (nx, 1) complex broadcast
        ZP = ps[None, :] - r[1]  # (1, np)
        expo = -0.5 * (invS[0, 0] * ZX * ZX + 2.0 * invS[0, 1] * ZX * ZP + invS[1, 1] * ZP * ZP)
        Qk = 2.0 * np.exp(expo) / (2.0 * np.pi * np.sqrt(np.linalg.det(Sigma)))
        S += w * Qk
    imag_max = float(np.max(np.abs(S.imag))) if S.size else 0.0
    if imag_max > _IM_TOL:
        raise ValueError(
            f"heterodyne_pdf: large imaginary part in Q surface (max |Im|={imag_max:.3e}); "
            "state is not Hermitian-closed"
        )
    Q = S.real.copy()
    neg = Q < 0.0
    if np.any(neg):
        n_neg = int(np.sum(neg))
        dxa = xs[1] - xs[0] if xs.size > 1 else 0.0
        dpa = ps[1] - ps[0] if ps.size > 1 else 0.0
        leak = float(-np.sum(Q[neg]) * dxa * dpa / 2.0)
        warnings.warn(
            f"heterodyne_pdf: {n_neg} grid points have Re(S)<0 "
            f"(leak mass ~{leak:.3e}); clipped to 0",
            stacklevel=2,
        )
        Q[neg] = 0.0
    return xs, ps, Q


def heterodyne_sample(
    state: BosonicState,
    mode: int = 0,
    *args: object,
    rng: np.random.Generator | None = None,
) -> complex:
    """Sample one heterodyne outcome β (exact, sequential CDF inversion).

    Marginal P(x) = Σ_j Q[i, j] then conditional P(p | x_i) = Q[i, :] / Σ_j;
    both inverted via uniform + searchsorted on the normalised CDF, then
    jittered uniformly within the cell (samples the piecewise-constant
    density — error O(δ²) instead of lattice spikes on grid points).

    Backward compat: legacy ``imag_tol`` positional/keyword is accepted and
    ignored (the teaching-cut pool no longer exists).
    """
    if args:
        # legacy imag_tol positional — ignore
        pass
    if rng is None:
        rng = np.random.default_rng()
    xs, ps, Q = heterodyne_pdf(state, mode)
    # marginal x
    Px = Q.sum(axis=1)
    total = Px.sum()
    if total <= _SIG_EPS:
        raise ValueError("heterodyne_sample: Q surface integrates to ~0")
    cdf_x = np.cumsum(Px) / total
    u1 = rng.uniform(0.0, 1.0)
    ix = int(np.clip(np.searchsorted(cdf_x, u1, side="right"), 0, xs.size - 1))
    # conditional p | x
    row = Q[ix, :]
    row_sum = row.sum()
    if row_sum <= _SIG_EPS:
        raise ValueError("heterodyne_sample: conditional P(p|x) ~ 0")
    cdf_p = np.cumsum(row) / row_sum
    u2 = rng.uniform(0.0, 1.0)
    ip = int(np.clip(np.searchsorted(cdf_p, u2, side="right"), 0, ps.size - 1))
    # within-cell jitter: piecewise-constant density sampling
    x = xs[ix] + (rng.uniform(0.0, 1.0) - 0.5) * (xs[1] - xs[0])
    p = ps[ip] + (rng.uniform(0.0, 1.0) - 0.5) * (ps[1] - ps[0])
    return complex((x + 1j * p) / np.sqrt(2.0))


def heterodyne_condition(
    state: BosonicState,
    mode: int,
    outcome: complex | float | np.ndarray,
) -> BosonicState:
    """Condition on heterodyne outcome β and **remove** the measured mode.

    Exact (ADR-0007): every component is conditioned with complex r̄
    (analytic continuation of the Gaussian formula), reweighted by the same
    per-component Q kernel value Q_k(β) — complex likelihood; weights
    renormalized to Σw = 1. Hermitian closure makes Σ_k w_k Q_k(β) real ≥ 0.

    Per component (Gaussian ``heterodyne_condition`` formula, mode removal +
    xxpp repack):

        Σ_A = V_A + I/2,  C = cov(B, A)
        V_B' = V_B − C Σ_A⁻¹ Cᵀ,   r̄_B' = r̄_B + C Σ_A⁻¹ (z − r̄_A)

    with r̄_A, r̄_B complex (the posterior stays in the manifold: V real
    symmetric, r̄ complex, w complex). K=1 matches the Gaussian
    ``heterodyne_condition`` exactly; a single-mode K=1 condition leaves a
    0-mode state (``nmode == 0``).
    """
    m = _check_mode(state, mode)
    beta = _as_beta(outcome)
    if abs(beta) > 30.0:
        raise ValueError(f"heterodyne outcome |β|={abs(beta):.3g} out of range (|β| ≤ 30)")
    z = _beta_to_xp(beta)

    idx_A = _xp_indices(m, mode)
    idx_B = [i for i in range(2 * m) if i not in idx_A]
    keep_modes = sorted(i for i in range(m) if i != mode)
    pack = list(keep_modes) + [m + k for k in keep_modes]
    pos = {ax: j for j, ax in enumerate(idx_B)}
    perm = [pos[ax] for ax in pack]

    kept: list[Component] = []
    raw_w: list[complex] = []
    for c in state.components:
        VA = c.V[np.ix_(idx_A, idx_A)]
        rA = c.rbar[idx_A]  # complex allowed
        Sigma = VA + 0.5 * np.eye(2)
        Sigma = 0.5 * (Sigma + Sigma.T)
        try:
            invS = np.linalg.inv(Sigma)
        except np.linalg.LinAlgError as exc:
            raise ValueError("heterodyne Σ_A = V_A + I/2 is singular") from exc
        dmu = z - rA  # complex residual
        wlik = np.exp(-0.5 * (dmu @ invS @ dmu)) / (
            2.0 * np.pi * np.sqrt(float(np.linalg.det(Sigma)))
        )
        raw_w.append(c.w * complex(wlik))
        VB = c.V[np.ix_(idx_B, idx_B)]
        C = c.V[np.ix_(idx_B, idx_A)]
        rB = c.rbar[idx_B]  # complex allowed
        VB_n = VB - C @ invS @ C.T
        rB_n = rB + C @ invS @ dmu  # complex update
        VB_n = 0.5 * (VB_n + VB_n.T)
        VB_n = VB_n[np.ix_(perm, perm)]
        rB_n = rB_n[perm]
        kept.append(Component(V=VB_n, rbar=rB_n, w=0.0 + 0.0j))

    s = sum(raw_w)
    if abs(s) < _SIG_EPS:
        raise ValueError("heterodyne_condition: weight sum ~ 0 after likelihood")
    for comp, w in zip(kept, raw_w, strict=True):
        comp.w = w / s
    return BosonicState(components=kept)


def heterodyne_sample_and_condition(
    state: BosonicState,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
) -> tuple[complex, BosonicState]:
    """Sample heterodyne β then condition (measured mode removed)."""
    beta = heterodyne_sample(state, mode, rng=rng)
    return beta, heterodyne_condition(state, mode, beta)


# ---------------------------------------------------------------------------
# threshold — outcome-only
# ---------------------------------------------------------------------------


def _vacuum_probability_complex(V: np.ndarray, rbar: np.ndarray, mode: int) -> complex:
    """⟨0|ρ|0⟩ of one Gaussian component, complex r̄ allowed.

    Same quadratic form as ``cvsim.bridge.vacuum_probability`` (ħ=1, xxpp):

        p₀ = exp(−½ r̄ᵀ (V+½I)⁻¹ r̄) / √det(V+½I)

    evaluated on the mode block with complex r̄. The bridge helper casts
    rbar to float (drops interference imaginary parts), so the complex
    quadratic form lives here; real r̄ gives exactly the bridge value.
    """
    V = np.asarray(V, dtype=float)
    rbar = np.asarray(rbar, dtype=complex)
    m = V.shape[0] // 2
    i = mode
    V1 = np.array([[V[i, i], V[i, m + i]], [V[m + i, i], V[m + i, m + i]]])
    r1 = np.array([rbar[i], rbar[m + i]])
    A = V1 + 0.5 * np.eye(2)
    if np.linalg.eigvalsh(A).min() <= 0.0:
        raise ValueError(f"V+½I on mode {mode} is not positive-definite")
    exponent = -0.5 * complex(r1 @ np.linalg.solve(A, r1))
    return complex(np.exp(exponent) / np.sqrt(np.linalg.det(A)))


def p_click(state: BosonicState, mode: int = 0) -> float:
    """Threshold (on/off) click probability p = 1 − Σ_k w_k ⟨0|ρ_k|0⟩.

    Per-component vacuum overlap may be complex (complex-mean interference
    components); the weighted sum is reduced to real with a strict
    imaginary-part tolerance check (raises if |Im| > 1e-8). K=1 matches
    the Gaussian p_click.

    **Outcome-only**: no state update — the post-click state leaves the
    Gaussian mixture manifold.
    """
    _check_mode(state, mode)
    total = 0.0 + 0.0j
    for c in state.components:
        total += c.w * _vacuum_probability_complex(c.V, c.rbar, mode)
    return 1.0 - _as_real(total, "p_click")


def sample_threshold(
    state: BosonicState,
    mode: int = 0,
    *,
    rng: np.random.Generator | None = None,
) -> bool:
    """Sample one threshold outcome: ``True`` = click, ``False`` = no click.

    Outcome-only (no state update, see :func:`p_click`).
    """
    if rng is None:
        rng = np.random.default_rng()
    return bool(rng.random() < p_click(state, mode))
