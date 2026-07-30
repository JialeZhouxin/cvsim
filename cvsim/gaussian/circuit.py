"""Parameterized Gaussian circuit with measurement + feedforward (L4).

L2: define once, run with different parameters.
L3: ``c1 + c2``, ``c1 += c2``.
L4: ``measure_homodyne`` / ``measure_heterodyne`` + ``ParamRef`` feedforward.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cvsim.gaussian.channels import (
    amplifier,
    apply_gaussian_channel,
    loss,
    phase_noise,
)
from cvsim.gaussian.state import GaussianState
from cvsim.gaussian.gates import (
    beamsplitter,
    cx,
    cz,
    displace,
    fourier,
    interferometer,
    mach_zehnder,
    phase,
    squeeze,
    two_mode_squeeze,
)
from cvsim.gaussian.observables import (
    heterodyne_sample_and_condition,
    homodyne_sample_and_condition,
)


@dataclass(frozen=True)
class ParamRef:
    """Reference to a homodyne measurement outcome, scaled by gain.

    Used in circuit builder methods where a gate parameter depends on
    a prior measurement result.

    Usage::

        c.measure_homodyne(1, phi=0, name='m_x')
        c.displace(0, alpha=ParamRef('m_x', gain=0.5))
    """
    source: str
    gain: float = 1.0


class GaussianCircuit:
    """Declarative Gaussian circuit with parameter placeholders.

    Parameters can be fixed (number), symbolic (string name),
    or feedforward (``ParamRef`` referencing a measurement).

    Measurement + feedforward (L4)::

        c = GaussianCircuit(2)
        c.squeeze(1, r=0.5)                       # ancilla
        c.cz(0, 1, weight=1.0)                     # entangle
        c.measure_homodyne(1, phi=np.pi/2, name='m_p')
        c.displace(0, alpha=ParamRef('m_p', gain=0.5))  # feedback

        state, results = c.run()
        # results == {'m_p': -1.204...}
    """

    def __init__(self, nmode: int) -> None:
        if nmode < 1:
            raise ValueError("nmode must be >= 1")
        self.nmode = nmode
        # _ops entries: (name, orig_modes, fixed, params, refs)
        self._ops: list[tuple[str, tuple, dict, dict, dict]] = []

    # -- L3: circuit composition ------------------------------------------

    def __iadd__(self, other: GaussianCircuit) -> GaussianCircuit:
        if self.nmode != other.nmode:
            raise ValueError(
                f"nmode mismatch: {self.nmode} vs {other.nmode}"
            )
        self._ops.extend(other._ops)
        return self

    def __add__(self, other: GaussianCircuit) -> GaussianCircuit:
        c = GaussianCircuit(self.nmode)
        c._ops = list(self._ops)
        c += other
        return c

    # -- builder methods --------------------------------------------------

    def squeeze(self, mode: int, r: float | str = 0.0) -> GaussianCircuit:
        self._ops.append(self._partition('squeeze', [mode], r=r))
        return self

    def displace(
        self, mode: int,
        alpha: complex | str | ParamRef = 0.0,
    ) -> GaussianCircuit:
        self._ops.append(self._partition('displace', [mode], alpha=alpha))
        return self

    def phase(self, mode: int, theta: float | str = 0.0) -> GaussianCircuit:
        self._ops.append(self._partition('phase', [mode], theta=theta))
        return self

    def fourier(self, mode: int = 0) -> GaussianCircuit:
        """Fourier gate on ``mode`` (phase by π/2)."""
        self._ops.append(self._partition('fourier', [mode]))
        return self

    def beamsplitter(
        self, mode1: int, mode2: int,
        theta: float | str = np.pi / 4,
        phi: float | str = 0.0,
    ) -> GaussianCircuit:
        self._ops.append(
            self._partition('beamsplitter', [mode1, mode2], theta=theta, phi=phi)
        )
        return self

    def two_mode_squeeze(
        self, mode1: int, mode2: int, r: float | str = 0.0
    ) -> GaussianCircuit:
        self._ops.append(
            self._partition('two_mode_squeeze', [mode1, mode2], r=r)
        )
        return self

    def cz(
        self, mode1: int, mode2: int, weight: float | str = 0.0
    ) -> GaussianCircuit:
        self._ops.append(
            self._partition('cz', [mode1, mode2], weight=weight)
        )
        return self

    def cx(
        self, mode1: int, mode2: int, weight: float | str = 0.0
    ) -> GaussianCircuit:
        self._ops.append(
            self._partition('cx', [mode1, mode2], weight=weight)
        )
        return self

    def mach_zehnder(
        self,
        mode1: int,
        mode2: int,
        theta: float | str = np.pi / 4,
        phi: float | str = 0.0,
    ) -> GaussianCircuit:
        """Mach–Zehnder: BS(θ) → phase(φ) on mode1 → BS(π/4)."""
        self._ops.append(
            self._partition(
                'mach_zehnder', [mode1, mode2], theta=theta, phi=phi
            )
        )
        return self

    def interferometer(self, U: np.ndarray) -> GaussianCircuit:
        """Passive interferometer: full nmode×nmode unitary U."""
        U = np.asarray(U, dtype=complex)
        if U.shape != (self.nmode, self.nmode):
            raise ValueError(
                f"U shape {U.shape} incompatible with nmode={self.nmode}"
            )
        # Store U in fixed kwargs; modes = all logical modes (for mapping).
        self._ops.append(
            (
                'interferometer',
                tuple(range(self.nmode)),
                {'U': U},
                {},
                {},
            )
        )
        return self

    def loss(
        self, mode: int, T: float | str = 1.0, nbar: float = 0.0
    ) -> GaussianCircuit:
        self._ops.append(
            self._partition('loss', [mode], T=T, nbar=nbar)
        )
        return self

    def amplifier(
        self,
        mode: int | None = None,
        G: float | str = 1.0,
        nbar: float = 0.0,
    ) -> GaussianCircuit:
        """Phase-insensitive amplifier. ``mode=None`` ⇒ all logical modes."""
        modes = [] if mode is None else [mode]
        self._ops.append(
            self._partition('amplifier', modes, G=G, nbar=nbar)
        )
        return self

    def phase_noise(
        self,
        mode: int | None = None,
        sigma: float | str = 0.0,
    ) -> GaussianCircuit:
        """Phase diffusion (rotation-average). ``mode=None`` ⇒ all modes."""
        modes = [] if mode is None else [mode]
        self._ops.append(
            self._partition('phase_noise', modes, sigma=sigma)
        )
        return self

    def gaussian_channel(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        d: np.ndarray | None = None,
        *,
        validate: bool = True,
    ) -> GaussianCircuit:
        """General Gaussian CPTP map ``(X, Y, d)`` on the **current** mode count.

        ``X, Y`` must be ``(2m, 2m)`` where ``m`` is the number of modes still
        present at the point this op runs. After ``measure_homodyne`` removes
        modes, ``m`` shrinks — a full-size matrix built for the original
        ``nmode`` will raise at ``run()``. Prefer named ``loss`` / ``amplifier``
        / ``phase_noise`` when only some modes are affected.
        """
        X = np.asarray(X, dtype=float)
        Y = np.asarray(Y, dtype=float)
        if X.ndim != 2 or X.shape[0] != X.shape[1] or X.shape[0] % 2 != 0:
            raise ValueError(f"X must be (2m,2m); got {X.shape}")
        if Y.shape != X.shape:
            raise ValueError(f"Y shape {Y.shape} != X shape {X.shape}")
        m_xy = X.shape[0] // 2
        if d is not None:
            d = np.asarray(d, dtype=float)
            if d.shape != (2 * m_xy,):
                raise ValueError(
                    f"d must be ({2 * m_xy},); got {d.shape}"
                )
        # modes empty: full-state op; run() does not remap X/Y through mapping
        self._ops.append(
            (
                'gaussian_channel',
                (),
                {'X': X, 'Y': Y, 'd': d, 'validate': validate},
                {},
                {},
            )
        )
        return self

    def measure_homodyne(
        self, mode: int, phi: float, name: str
    ) -> GaussianCircuit:
        """Ideal Homodyne measurement: sample + condition + remove mode.

        At ``run()``, this produces a random outcome stored in
        ``results[name]``.  The measured mode is removed from the state;
        subsequent gates see a shifted mode index for modes above *mode*.
        """
        self._ops.append(
            self._partition(
                'measure_homodyne', [mode],
                _fixed_str_keys={'name'},
                phi=phi, name=name,
            )
        )
        return self

    def measure_heterodyne(
        self, mode: int, name: str
    ) -> GaussianCircuit:
        """Ideal Heterodyne measurement: sample β + condition + remove mode.

        POVM |β⟩⟨β|/π. Outcome stored in ``results[name]`` as ``complex``.
        Measured mode is removed (same mapping shift as Homodyne).
        """
        self._ops.append(
            self._partition(
                'measure_heterodyne', [mode],
                _fixed_str_keys={'name'},
                name=name,
            )
        )
        return self

    # -- execution --------------------------------------------------------

    def run(
        self,
        *,
        rng: np.random.Generator | None = None,
        **params: float,
    ) -> GaussianState | tuple[GaussianState, dict[str, float]]:
        """Execute circuit with given parameter values.

        Returns ``GaussianState`` if no measurements, else
        ``(GaussianState, results)``.

        *rng* seeds Homodyne sampling for reproducible measurements.
        """
        st = GaussianState.vacuum(self.nmode)
        mapping = list(range(self.nmode))
        results: dict[str, float] = {}

        for op_name, modes, fixed, pnames, refs in self._ops:
            kwargs = dict(fixed)
            for k, v in pnames.items():
                if v not in params:
                    raise ValueError(
                        f"Missing parameter '{v}' for {op_name}"
                    )
                kwargs[k] = params[v]

            if op_name == 'measure_homodyne':
                orig_mode = modes[0]
                phys_mode = mapping[orig_mode]
                phi_val = kwargs['phi']
                val, st = homodyne_sample_and_condition(
                    st, phys_mode, phi_val, rng=rng
                )
                results[kwargs['name']] = val
                st = st.remove_mode(phys_mode)
                # shift mappings for modes above the removed one
                for i in range(len(mapping)):
                    if mapping[i] > phys_mode:
                        mapping[i] -= 1
                mapping[orig_mode] = -1
            elif op_name == 'measure_heterodyne':
                orig_mode = modes[0]
                phys_mode = mapping[orig_mode]
                # heterodyne_condition already removes the measured mode
                val, st = heterodyne_sample_and_condition(
                    st, phys_mode, rng=rng
                )
                results[kwargs['name']] = val
                for i in range(len(mapping)):
                    if mapping[i] > phys_mode:
                        mapping[i] -= 1
                mapping[orig_mode] = -1
            elif op_name == 'gaussian_channel':
                # Full-state (X,Y): dimension must match modes still present.
                X = kwargs['X']
                if X.shape[0] != 2 * st.nmode:
                    raise ValueError(
                        f"gaussian_channel X/Y size {X.shape[0]} does not match "
                        f"current 2*nmode={2 * st.nmode} (mode removed by "
                        f"measurement? use loss/amplifier/phase_noise instead)"
                    )
                st = apply_gaussian_channel(
                    st,
                    X,
                    kwargs['Y'],
                    kwargs.get('d'),
                    validate=kwargs.get('validate', True),
                )
            else:
                # mode-less presets (amplifier/phase_noise with mode=None)
                if modes:
                    phys_modes = [mapping[m] for m in modes]
                    if any(p < 0 for p in phys_modes):
                        raise ValueError(
                            f"{op_name} references a mode already measured/removed"
                        )
                else:
                    phys_modes = []
                # resolve ParamRef → real value
                for k, v in refs.items():
                    if v.source not in results:
                        raise ValueError(
                            f"ParamRef '{k}' references '{v.source}' "
                            f"which has not been measured yet"
                        )
                    kwargs[k] = complex(results[v.source] * v.gain)

                st = self._apply(op_name, st, tuple(phys_modes), **kwargs)

        if results:
            return st, results
        return st

    # -- inspection -------------------------------------------------------

    def __repr__(self) -> str:
        lines = [f"GaussianCircuit({self.nmode})"]
        for op_name, modes, fixed, pnames, refs in self._ops:
            args = [str(m) for m in modes]
            for k, v in fixed.items():
                args.append(f"{k}={v}")
            for k, v in pnames.items():
                args.append(f"{k}=${{{v}}}")
            for k, v in refs.items():
                args.append(f"{k}=${{{v.source}}}*{v.gain}")
            lines.append(f"  .{op_name}({', '.join(args)})")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._ops)

    # -- internal --------------------------------------------------------

    @staticmethod
    def _partition(
        op_name: str,
        modes: list[int],
        *,
        _fixed_str_keys: frozenset[str] = frozenset(),
        **kwargs: float | str | ParamRef,
    ) -> tuple[str, tuple, dict, dict, dict]:
        fixed: dict = {}
        params: dict = {}
        refs: dict = {}
        for k, v in kwargs.items():
            if isinstance(v, ParamRef):
                refs[k] = v
            elif isinstance(v, str) and k not in _fixed_str_keys:
                params[k] = v
            else:
                fixed[k] = v
        return (op_name, tuple(modes), fixed, params, refs)

    _DISPATCH = {
        'squeeze': lambda st, m, **kw: squeeze(st, kw['r'], m[0]),
        'displace': lambda st, m, **kw: displace(st, kw['alpha'], m[0]),
        'phase': lambda st, m, **kw: phase(st, kw['theta'], m[0]),
        'fourier': lambda st, m, **kw: fourier(st, m[0]),
        'beamsplitter': lambda st, m, **kw: beamsplitter(
            st, m[0], m[1], kw['theta'], kw.get('phi', 0.0)
        ),
        'mach_zehnder': lambda st, m, **kw: mach_zehnder(
            st, m[0], m[1], kw['theta'], kw.get('phi', 0.0)
        ),
        'two_mode_squeeze': lambda st, m, **kw: two_mode_squeeze(
            st, kw['r'], m[0], m[1]
        ),
        'cz': lambda st, m, **kw: cz(st, kw['weight'], m[0], m[1]),
        'cx': lambda st, m, **kw: cx(st, kw['weight'], m[0], m[1]),
        'interferometer': lambda st, m, **kw: interferometer(st, kw['U']),
        'loss': lambda st, m, **kw: loss(st, kw['T'], m[0], kw.get('nbar', 0.0)),
        'amplifier': lambda st, m, **kw: amplifier(
            st, kw['G'], m[0] if m else None, kw.get('nbar', 0.0)
        ),
        'phase_noise': lambda st, m, **kw: phase_noise(
            st, kw['sigma'], m[0] if m else None
        ),
    }

    @staticmethod
    def _apply(
        op_name: str, st: GaussianState, modes: tuple, **kwargs: float
    ) -> GaussianState:
        return GaussianCircuit._DISPATCH[op_name](st, modes, **kwargs)
