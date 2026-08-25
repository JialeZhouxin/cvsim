"""BosonicCircuit: declarative circuit DSL (B5, ADR-0004 third consumer).

Mirrors ``GaussianCircuit``: op-list builder, parameter partitioning
(``circuit_common.partition``), segment compilation, circuit_v1 IR.
Physics is component-wise (K=1 vacuum start, gates do not add components).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from cvsim.bosonic.state import BosonicState
from cvsim.circuit_common import ParamRef, partition

if TYPE_CHECKING:
    from cvsim.bosonic.compile import CompiledBosonic


class BosonicCircuit:
    """Declarative Bosonic circuit with parameter placeholders.

    Parameters can be fixed (number), symbolic (string name), or feedforward
    (``ParamRef`` referencing a measurement). K=1 vacuum start; gates apply
    component-wise without adding components.

    Measurement + feedforward (L4)::

        c = BosonicCircuit(2)
        c.squeeze(1, r=0.5)
        c.cz(0, 1, weight=1.0)
        c.measure_homodyne(1, phi=np.pi/2, name='m_p')
        c.displace(0, alpha=ParamRef('m_p', gain=0.5))

        state, results = c.run()
    """

    def __init__(self, nmode: int, initial: BosonicState | list[str | None] | None = None) -> None:
        if nmode < 1:
            raise ValueError("nmode must be >= 1")
        self.nmode = nmode
        self._initial: BosonicState | None = None
        self._initial_spec: list[str | None] | None = None
        if initial is not None:
            if isinstance(initial, BosonicState):
                self._initial = initial
            elif isinstance(initial, list):
                if len(initial) != nmode:
                    raise ValueError(
                        f"initial: list length {len(initial)} != nmode {nmode} "
                        "(one state name per mode)"
                    )
                self._initial_spec = list(initial)
                self._initial = self._resolve_initial(initial)
            else:
                raise TypeError(
                    f"initial must be a BosonicState or a list of state names, "
                    f"got {type(initial).__name__}"
                )
        # _ops entries: (name, orig_modes, fixed, params, refs)
        self._ops: list[tuple[str, tuple, dict, dict, dict]] = []

    @staticmethod
    def _resolve_initial(initial: list) -> BosonicState:
        """Resolve a per-mode list of state-source names to a BosonicState.

        Items: ``None`` = vacuum, ``"gkp0"`` / ``"gkp1"``; tensor-multiplied
        component-wise for the multi-mode initial state (B6 R1).
        """
        from cvsim.bosonic.gkp import gkp0, gkp1
        from cvsim.bosonic.state import tensor_product

        states: list[BosonicState] = []
        for item in initial:
            if item is None:
                states.append(BosonicState.vacuum(1))
            elif item == "gkp0":
                states.append(gkp0())
            elif item == "gkp1":
                states.append(gkp1())
            else:
                raise ValueError(f"initial: unknown state source {item!r} (None|'gkp0'|'gkp1')")
        return tensor_product(states)

    # -- L3: circuit composition ------------------------------------------

    def __iadd__(self, other: BosonicCircuit) -> BosonicCircuit:
        if self.nmode != other.nmode:
            raise ValueError(f"nmode mismatch: {self.nmode} vs {other.nmode}")
        self._ops.extend(other._ops)
        return self

    def __add__(self, other: BosonicCircuit) -> BosonicCircuit:
        c = BosonicCircuit(self.nmode)
        c._ops = list(self._ops)
        c += other
        return c

    # -- builder methods (gates, 1:1 with GaussianCircuit) ----------------

    def squeeze(self, mode: int, r: float | str = 0.0, phi: float | str = 0.0) -> BosonicCircuit:
        self._ops.append(self._partition('squeeze', [mode], r=r, phi=phi))
        return self

    def displace(
        self, mode: int,
        alpha: complex | str | ParamRef = 0.0,
    ) -> BosonicCircuit:
        self._ops.append(self._partition('displace', [mode], alpha=alpha))
        return self

    def phase(self, mode: int, theta: float | str = 0.0) -> BosonicCircuit:
        self._ops.append(self._partition('phase', [mode], theta=theta))
        return self

    def fourier(self, mode: int = 0) -> BosonicCircuit:
        self._ops.append(self._partition('fourier', [mode]))
        return self

    def beamsplitter(
        self, mode1: int, mode2: int,
        theta: float | str = np.pi / 4,
        phi: float | str = 0.0,
    ) -> BosonicCircuit:
        self._ops.append(self._partition('beamsplitter', [mode1, mode2], theta=theta, phi=phi))
        return self

    def two_mode_squeeze(self, mode1: int, mode2: int, r: float | str = 0.0) -> BosonicCircuit:
        self._ops.append(self._partition('two_mode_squeeze', [mode1, mode2], r=r))
        return self

    def cz(self, mode1: int, mode2: int, weight: float | str = 0.0) -> BosonicCircuit:
        self._ops.append(self._partition('cz', [mode1, mode2], weight=weight))
        return self

    def cx(self, mode1: int, mode2: int, weight: float | str = 0.0) -> BosonicCircuit:
        self._ops.append(self._partition('cx', [mode1, mode2], weight=weight))
        return self

    def mach_zehnder(
        self, mode1: int, mode2: int,
        theta: float | str = np.pi / 4,
        phi: float | str = 0.0,
    ) -> BosonicCircuit:
        self._ops.append(self._partition('mach_zehnder', [mode1, mode2], theta=theta, phi=phi))
        return self

    def interferometer(self, U: np.ndarray) -> BosonicCircuit:
        U = np.asarray(U, dtype=complex).copy()
        if U.shape != (self.nmode, self.nmode):
            raise ValueError(f"U shape {U.shape} incompatible with nmode={self.nmode}")
        self._ops.append(('interferometer', tuple(range(self.nmode)), {'U': U}, {}, {}))
        return self

    # -- channels ---------------------------------------------------------

    def loss(self, mode: int, T: float | str = 1.0, nbar: float = 0.0) -> BosonicCircuit:
        self._ops.append(self._partition('loss', [mode], T=T, nbar=nbar))
        return self

    def amplifier(
        self, mode: int | None = None, G: float | str = 1.0, nbar: float = 0.0
    ) -> BosonicCircuit:
        modes = [] if mode is None else [mode]
        self._ops.append(self._partition('amplifier', modes, G=G, nbar=nbar))
        return self

    def phase_noise(self, mode: int | None = None, sigma: float | str = 0.0) -> BosonicCircuit:
        modes = [] if mode is None else [mode]
        self._ops.append(self._partition('phase_noise', modes, sigma=sigma))
        return self

    def gaussian_channel(
        self, X: np.ndarray, Y: np.ndarray, d: np.ndarray | None = None, *, validate: bool = True
    ) -> BosonicCircuit:
        X = np.asarray(X, dtype=float).copy()
        Y = np.asarray(Y, dtype=float).copy()
        if X.ndim != 2 or X.shape[0] != X.shape[1] or X.shape[0] % 2 != 0:
            raise ValueError(f"X must be (2m,2m); got {X.shape}")
        if Y.shape != X.shape:
            raise ValueError(f"Y shape {Y.shape} != X shape {X.shape}")
        m_xy = X.shape[0] // 2
        if d is not None:
            d = np.asarray(d, dtype=float).copy()
            if d.shape != (2 * m_xy,):
                raise ValueError(f"d must be ({2 * m_xy},); got {d.shape}")
        self._ops.append(
            ('gaussian_channel', (), {'X': X, 'Y': Y, 'd': d, 'validate': validate}, {}, {})
        )
        return self

    # -- measurements ------------------------------------------------------

    def measure_homodyne(self, mode: int, phi: float, name: str) -> BosonicCircuit:
        """Ideal Homodyne: sample + condition + remove mode.

        Outcome stored in ``results[name]`` as ``float``; measured mode
        removed (mode index shifts for later gates).
        """
        self._ops.append(
            self._partition(
                'measure_homodyne', [mode], _fixed_str_keys={'name'}, phi=phi, name=name
            )
        )
        return self

    def measure_heterodyne(self, mode: int, name: str) -> BosonicCircuit:
        """Ideal Heterodyne: sample β + condition + remove mode.

        Outcome stored in ``results[name]`` as ``complex``; measured mode
        removed (already dropped by ``heterodyne_condition``).
        """
        self._ops.append(
            self._partition('measure_heterodyne', [mode], _fixed_str_keys={'name'}, name=name)
        )
        return self

    def measure_threshold(self, mode: int, name: str) -> BosonicCircuit:
        """Threshold (on/off) — outcome-only, no state update, no mode removal."""
        self._ops.append(
            self._partition('measure_threshold', [mode], _fixed_str_keys={'name'}, name=name)
        )
        return self

    # -- execution --------------------------------------------------------

    def compile(self) -> CompiledBosonic:
        from cvsim.bosonic.compile import CompiledBosonic, _compile_segments
        segments, params = _compile_segments(self._ops, self.nmode)
        return CompiledBosonic(self.nmode, segments, params, initial=self._initial)

    def run(
        self, *, rng: np.random.Generator | None = None, **params: float
    ) -> BosonicState | tuple[BosonicState, dict[str, float]]:
        """Execute circuit. Returns ``BosonicState`` or ``(state, results)``."""
        return self.compile().run(rng=rng, **params)

    # -- serialization (circuit_v1 IR, ADR-0003) --------------------------

    def to_ir(self) -> dict:
        from cvsim.bosonic.ir import to_ir
        return to_ir(self)

    @classmethod
    def from_ir(cls, data: dict) -> BosonicCircuit:
        from cvsim.bosonic.ir import from_ir
        return from_ir(data)

    # -- inspection -------------------------------------------------------

    def __repr__(self) -> str:
        lines = [f"BosonicCircuit({self.nmode})"]
        for op_name, modes, fixed, pnames, refs in self._ops:
            args = [str(m) for m in modes]
            for k, v in fixed.items():
                if isinstance(v, np.ndarray):
                    args.append(f"{k}=<ndarray {v.shape}>")
                else:
                    args.append(f"{k}={v}")
            for k, v in pnames.items():
                args.append(f"{k}=${{{v}}}")
            for k, v in refs.items():
                args.append(f"{k}=${{{v.source}}}*{v.gain}")
            lines.append(f"  .{op_name}({', '.join(args)})")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._ops)

    # -- internal ---------------------------------------------------------

    @staticmethod
    def _partition(
        op_name: str, modes: list[int], *, _fixed_str_keys: frozenset[str] = frozenset(), **kwargs
    ) -> tuple:
        return partition(op_name, modes, _fixed_str_keys=_fixed_str_keys, **kwargs)
