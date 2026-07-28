"""Parameterized Gaussian circuit: define once, run with different parameters."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.channels import loss
from cvsim.gaussian.state import GaussianState
from cvsim.gaussian.gates import (
    beamsplitter,
    cx,
    cz,
    displace,
    phase,
    squeeze,
    two_mode_squeeze,
)


class GaussianCircuit:
    """Declarative Gaussian circuit with parameter placeholders.

    Parameters can be fixed (number) or symbolic (string name).
    Symbolic parameters are resolved at ``run(**params)`` time.

    Usage::

        c = GaussianCircuit(2)
        c.squeeze(0, r='r1')
        c.cz(0, 1, weight='g')
        c.beamsplitter(0, 1, theta=np.pi/4)
        st = c.run(r1=0.5, g=0.3)   # run with specific values
    """

    def __init__(self, nmode: int) -> None:
        if nmode < 1:
            raise ValueError("nmode must be >= 1")
        self.nmode = nmode
        self._ops: list[tuple[str, tuple, dict, dict]] = []  # (name, modes, fixed, params)

    # -- builder methods -------------------------------------------------

    def squeeze(self, mode: int, r: float | str = 0.0) -> GaussianCircuit:
        self._ops.append(self._partition('squeeze', [mode], r=r))
        return self

    def displace(self, mode: int, alpha: complex | str = 0.0) -> GaussianCircuit:
        self._ops.append(self._partition('displace', [mode], alpha=alpha))
        return self

    def phase(self, mode: int, theta: float | str = 0.0) -> GaussianCircuit:
        self._ops.append(self._partition('phase', [mode], theta=theta))
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

    def loss(
        self, mode: int, T: float | str = 1.0, nbar: float = 0.0
    ) -> GaussianCircuit:
        self._ops.append(
            self._partition('loss', [mode], T=T, nbar=nbar)
        )
        return self

    # -- execution -------------------------------------------------------

    def run(self, **params: float) -> GaussianState:
        """Execute circuit with given parameter values.

        Each symbolic parameter name must be provided as a keyword argument.
        """
        st = GaussianState.vacuum(self.nmode)
        for op_name, modes, fixed, pnames in self._ops:
            kwargs = dict(fixed)
            for k, v in pnames.items():
                if v not in params:
                    raise ValueError(
                        f"Missing parameter '{v}' for {op_name}, "
                        f"provided: {list(params)}"
                    )
                kwargs[k] = params[v]

            st = self._apply(op_name, st, modes, **kwargs)
        return st

    # -- inspection -------------------------------------------------------

    def __repr__(self) -> str:
        lines = [f"GaussianCircuit({self.nmode})"]
        for op_name, modes, fixed, pnames in self._ops:
            args = [str(m) for m in modes]
            for k, v in fixed.items():
                args.append(f"{k}={v}")
            for k, v in pnames.items():
                args.append(f"{k}=${{{v}}}")
            lines.append(f"  .{op_name}({', '.join(args)})")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._ops)

    # -- internal --------------------------------------------------------

    @staticmethod
    def _partition(
        op_name: str, modes: list[int], **kwargs: float | str
    ) -> tuple[str, tuple, dict, dict]:
        fixed = {}
        params = {}
        for k, v in kwargs.items():
            if isinstance(v, str):
                params[k] = v
            else:
                fixed[k] = v
        return (op_name, tuple(modes), fixed, params)

    _DISPATCH = {
        'squeeze': lambda st, m, **kw: squeeze(st, kw['r'], m[0]),
        'displace': lambda st, m, **kw: displace(st, kw['alpha'], m[0]),
        'phase': lambda st, m, **kw: phase(st, kw['theta'], m[0]),
        'beamsplitter': lambda st, m, **kw: beamsplitter(
            st, m[0], m[1], kw['theta'], kw.get('phi', 0.0)
        ),
        'two_mode_squeeze': lambda st, m, **kw: two_mode_squeeze(
            st, kw['r'], m[0], m[1]
        ),
        'cz': lambda st, m, **kw: cz(st, kw['weight'], m[0], m[1]),
        'cx': lambda st, m, **kw: cx(st, kw['weight'], m[0], m[1]),
        'loss': lambda st, m, **kw: loss(st, kw['T'], m[0], kw.get('nbar', 0.0)),
    }

    @staticmethod
    def _apply(
        op_name: str, st: GaussianState, modes: tuple, **kwargs: float
    ) -> GaussianState:
        return GaussianCircuit._DISPATCH[op_name](st, modes, **kwargs)
