"""Fock state: truncated amplitudes, 1-mode (N,) or 2-mode (N,N).

Factories carry the analytic truncation tail (``tail``) so leakage checks
(ADR-0004 / vision-fock-simulator §5) can be exact for factory states and
honest ("unknown") otherwise.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass

import numpy as np
from scipy.special import factorial, gammainc


@dataclass
class FockState:
    """Pure Fock state in truncated basis.

    amps.ndim == 1: single mode, shape (cutoff,)
    amps.ndim == 2: two mode, shape (cutoff, cutoff), c[n0, n1]

    ``tail``: analytic truncation leakage of the *untruncated* state
    (tail probability Σ_{n≥cutoff} |c_n|²), exact for factory states,
    ``None`` otherwise (unknown — never guessed, vision §5).
    """

    amps: np.ndarray
    tail: float | None = None
    _source: tuple | None = None  # ('name', args) — rebuild for estimate_leakage

    def __post_init__(self) -> None:
        self.amps = np.asarray(self.amps, dtype=complex)
        m = self.amps.ndim
        if not 1 <= m <= 4:
            raise ValueError("amps ndim must be 1..4 (dense m≤4; sparse F3)")
        if any(n < 1 for n in self.amps.shape):
            raise ValueError(f"amps axes must be positive (got {self.amps.shape})")

    @property
    def cutoff(self) -> int:
        return int(self.amps.shape[0])

    @property
    def nmode(self) -> int:
        return self.amps.ndim

    @classmethod
    def vacuum(cls, cutoff: int, nmode: int = 1) -> FockState:
        if cutoff < 1:
            raise ValueError("cutoff must be >= 1")
        if not 1 <= nmode <= 4:
            raise ValueError("nmode must be 1..4 (dense m≤4; sparse F3)")
        amps = np.zeros((cutoff,) * nmode, dtype=complex)
        amps[(0,) * nmode] = 1.0
        return cls(amps=amps, tail=0.0)

    @classmethod
    def fock(cls, n: int, cutoff: int) -> FockState:
        if not 0 <= n < cutoff:
            raise ValueError(f"n={n} out of range for cutoff={cutoff}")
        amps = np.zeros(cutoff, dtype=complex)
        amps[n] = 1.0
        return cls(amps=amps, tail=0.0)

    @classmethod
    def fock2(cls, n0: int, n1: int, cutoff: int) -> FockState:
        if not (0 <= n0 < cutoff and 0 <= n1 < cutoff):
            raise ValueError("occupation out of cutoff")
        amps = np.zeros((cutoff, cutoff), dtype=complex)
        amps[n0, n1] = 1.0
        return cls(amps=amps, tail=0.0)

    @classmethod
    def coherent(cls, cutoff: int, alpha: complex) -> FockState:
        """Coherent state |α⟩ in truncated basis (renormalized to cutoff).

        Exact analytic tail: Σ_{n≥N} e^{−|α|²}|α|^{2n}/n! = P(N, |α|²)
        (regularized *lower* incomplete gamma, stable for large α).
        """
        alpha = complex(alpha)
        c = _coherent_amps(cutoff, alpha)
        tail = float(gammainc(cutoff, abs(alpha) ** 2))
        return cls(amps=c, tail=tail, _source=('coherent', (alpha,)))

    @classmethod
    def squeezed(cls, cutoff: int, r: float, phi: float = 0.0) -> FockState:
        """Squeezed vacuum S(r, φ)|0⟩ in truncated basis (renormalized).

        c_{2n} = √sech r · (−1)^n √((2n)!)/(2^n n!) · (e^{iφ} tanh r)^n,
        odd coefficients vanish. Tail = 1 − ‖c‖² computed from the exact
        (untruncated-normalized) coefficients before renormalization.
        """
        r = float(r)
        kk = np.arange((cutoff + 1) // 2)
        t = math.tanh(r) * np.exp(1j * float(phi))
        c = np.zeros(cutoff, dtype=complex)
        c[0::2] = (
            math.sqrt(1.0 / math.cosh(r))
            * (-1.0) ** kk
            * np.sqrt(factorial(2 * kk)) / (2.0 ** kk * factorial(kk))
            * t ** kk
        )
        tail = 1.0 - float(np.sum(abs(c) ** 2))
        c /= np.sqrt(1.0 - tail)
        return cls(amps=c, tail=tail, _source=('squeezed', (r, phi)))

    @classmethod
    def cat(cls, cutoff: int, alpha: complex, even: bool = True) -> FockState:
        """Even/odd cat state (|α⟩ ± |−α⟩)/√N in truncated basis (renormalized).

        N² = 2(1 ± e^{−2|α|²}); tail = 1 − ‖c‖² from exact coefficients.
        """
        alpha = complex(alpha)
        sign = 1.0 if even else -1.0
        c = _coherent_amps(cutoff, alpha) + sign * _coherent_amps(cutoff, -alpha)
        c /= math.sqrt(2.0 * (1.0 + sign * math.exp(-2.0 * abs(alpha) ** 2)))
        tail = 1.0 - float(np.sum(abs(c) ** 2))
        c /= np.sqrt(1.0 - tail)
        return cls(amps=c, tail=tail, _source=('cat', (alpha, even)))

    def copy(self) -> FockState:
        return FockState(self.amps.copy(), self.tail, self._source)


def _coherent_amps(cutoff: int, alpha: complex) -> np.ndarray:
    """|α⟩ amplitudes by recurrence, overflow-safe.

    c_0 = 1, c_n = c_{n−1}·α/√n (the e^{−|α|²/2} global factor is dropped —
    it cancels under renormalization and would underflow for large |α|).
    Periodic rescaling keeps |c| bounded (safe up to |α|² ~ 1e8).
    """
    c = np.zeros(cutoff, dtype=complex)
    c[0] = 1.0 + 0.0j
    for n in range(1, cutoff):
        c[n] = c[n - 1] * alpha / np.sqrt(n)
        if n % 64 == 0:
            c /= np.max(np.abs(c))
    c /= np.linalg.norm(c)
    return c


# -- truncation engineering (vision §5 / ADR-0004) -------------------------


def truncation_leakage(state: FockState) -> float | None:
    """Exact analytic truncation leakage for factory states; ``None`` otherwise."""
    return state.tail


def check_leakage(
    state: FockState,
    *,
    validate: bool = False,
    warn_threshold: float = 1e-6,
    fail_threshold: float = 1e-3,
) -> None:
    """Warn/raise on truncation leakage (vision §5 rule 2–3).

    Unknown leakage (``tail is None``) is skipped — never guessed.
    Leakage > ``fail_threshold`` raises; ``validate=True`` also raises above
    ``warn_threshold`` (strict mode, mirrors ``validate_state(validate=)``).
    """
    leak = state.tail
    if leak is None:
        return
    if leak > fail_threshold or (validate and leak > warn_threshold):
        raise ValueError(
            f"truncation leakage {leak:.3g} exceeds fail threshold "
            f"{fail_threshold if leak > fail_threshold else warn_threshold}"
        )
    if leak > warn_threshold:
        warnings.warn(
            f"truncation leakage {leak:.3g} above warn threshold {warn_threshold}",
            RuntimeWarning,
            stacklevel=2,
        )


def estimate_leakage(state: FockState, cutoff2: int) -> float:
    """Higher-cutoff comparison estimate of truncation leakage.

    Rebuilds a factory state at ``cutoff2 > state.cutoff`` and returns the
    probability mass beyond ``state.cutoff`` (vision §5 rule 1, explicit tool).
    Requires a factory state (analytic reconstruction); raises otherwise.
    """
    if state._source is None:
        raise ValueError(
            "estimate_leakage requires a factory state (coherent/squeezed/cat)"
        )
    name, args = state._source
    if cutoff2 <= state.cutoff:
        raise ValueError(f"cutoff2 must be > state.cutoff ({state.cutoff})")
    if name == 'coherent':
        st2 = FockState.coherent(cutoff2, args[0])
    elif name == 'squeezed':
        st2 = FockState.squeezed(cutoff2, args[0], args[1])
    elif name == 'cat':
        st2 = FockState.cat(cutoff2, args[0], args[1])
    else:  # pragma: no cover — future factories must register here
        raise ValueError(f"no rebuild path for factory {name!r}")
    return 1.0 - float(np.sum(abs(st2.amps[: state.cutoff]) ** 2))
