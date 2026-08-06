"""Circuit compiler: segment ops, merge affine unitary layers into (S, d).

Architecture: docs/adr/0002. Segments are either ``('merged', nmode, ops)``
(compile-time constants, instantiated to one (S, d) per run) or
``('op', op)`` (channel / measurement / ParamRef op, executed op-by-op).
Mode references are resolved to physical coordinates at compile time via a
static simulation of the measurement-mode-removal mapping (measurement
removes a deterministic number of modes, so the mapping is RNG-independent).
"""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.channels import apply_gaussian_channel
from cvsim.gaussian.gates import apply_symplectic
from cvsim.gaussian.observables import (
    heterodyne_sample_and_condition,
    homodyne_sample_and_condition,
)
from cvsim.gaussian.state import GaussianState
from cvsim.symplectic import (
    S_beamsplitter,
    S_CX,
    S_CZ,
    S_from_unitary,
    S_mach_zehnder,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    d_displace,
)

# Ops that break a compile segment (ADR-0002 decision 2).
_BREAK_OPS = frozenset(
    {'loss', 'amplifier', 'phase_noise', 'gaussian_channel',
     'measure_homodyne', 'measure_heterodyne'}
)
# Affine unitary ops that can be merged into a single (S, d).
_MERGEABLE_OPS = frozenset(
    {'squeeze', 'displace', 'phase', 'fourier', 'beamsplitter',
     'mach_zehnder', 'two_mode_squeeze', 'cz', 'cx', 'interferometer'}
)


def _factor(op: tuple, nmode: int) -> tuple[np.ndarray, np.ndarray]:
    """(S, d) factor for one merged op at physical mode coordinates."""
    op_name, modes, fixed, _pnames, _refs = op
    kw = dict(fixed)
    m0 = modes[0] if modes else None
    m1 = modes[1] if len(modes) > 1 else None
    if op_name == 'squeeze':
        S = S_squeeze(nmode, kw['r'], m0)
        if kw.get('phi', 0.0) != 0.0:
            phi = kw['phi']
            S = S_phase(nmode, phi, m0) @ S @ S_phase(nmode, -phi, m0)
        return S, np.zeros(2 * nmode)
    if op_name == 'displace':
        return np.eye(2 * nmode), d_displace(nmode, kw['alpha'], m0)
    if op_name == 'phase':
        return S_phase(nmode, kw['theta'], m0), np.zeros(2 * nmode)
    if op_name == 'fourier':
        return S_phase(nmode, 0.5 * np.pi, m0), np.zeros(2 * nmode)
    if op_name == 'beamsplitter':
        return S_beamsplitter(
            nmode, m0, m1, kw['theta'], kw.get('phi', 0.0)
        ), np.zeros(2 * nmode)
    if op_name == 'mach_zehnder':
        return S_mach_zehnder(
            nmode, m0, m1, kw['theta'], kw.get('phi', 0.0)
        ), np.zeros(2 * nmode)
    if op_name == 'two_mode_squeeze':
        return S_two_mode_squeeze(nmode, kw['r'], m0, m1), np.zeros(2 * nmode)
    if op_name == 'cz':
        return S_CZ(nmode, kw['weight'], m0, m1), np.zeros(2 * nmode)
    if op_name == 'cx':
        return S_CX(nmode, kw['weight'], m0, m1), np.zeros(2 * nmode)
    if op_name == 'interferometer':
        # keep the unitary validation of gates.interferometer (validate_u=True)
        return S_from_unitary(kw['U'], validate=True), np.zeros(2 * nmode)
    raise ValueError(f"not a mergeable op: {op_name!r}")


def _instantiate(ops: list[tuple], nmode: int, values: dict) -> tuple[np.ndarray, np.ndarray]:
    """Merge segment ops into (S, d) with parameter values bound."""
    S = np.eye(2 * nmode)
    d = np.zeros(2 * nmode)
    for op in ops:
        op_name, modes, fixed, pnames, refs = op
        if pnames:
            kw = dict(fixed)
            for k, v in pnames.items():
                if v not in values:
                    raise ValueError(f"Missing parameter '{v}' for {op_name}")
                kw[k] = values[v]
            op = (op_name, modes, kw, {}, {})
        Si, di = _factor(op, nmode)
        S = Si @ S
        d = Si @ d + di
    return S, d


def _compile_segments(
    ops: list[tuple],
    nmode: int,
) -> tuple[list, frozenset[str]]:
    """Static segmentation with mode mapping resolved to physical coords.

    Returns ``(segments, params)`` where params = union of bindable
    parameter names (strings in ``pnames``).
    """
    # ops from GaussianCircuit._ops: (name, orig_modes, fixed, pnames, refs)
    mapping = list(range(nmode))
    segments: list = []
    merged: list = []
    params: set[str] = set()
    merged_nmode = nmode

    def flush() -> None:
        nonlocal merged
        if merged:
            segments.append(('merged', merged_nmode, merged))
            merged = []

    for op in ops:
        op_name, modes, fixed, pnames, refs = op
        params.update(pnames.values())
        if op_name in _BREAK_OPS or refs:
            flush()
            if modes:
                phys = [mapping[m] for m in modes]
                if any(p < 0 for p in phys):
                    raise ValueError(
                        f"{op_name} references a mode already measured/removed"
                    )
            else:
                phys = []
            segments.append(
                ('op', (op_name, tuple(phys), fixed, pnames, refs))
            )
            if op_name in ('measure_homodyne', 'measure_heterodyne'):
                phys_mode = mapping[modes[0]]
                nmode -= 1
                for i in range(len(mapping)):
                    if mapping[i] > phys_mode:
                        mapping[i] -= 1
                mapping[modes[0]] = -1
            continue
        # mergeable affine unitary
        if not merged:
            merged_nmode = nmode
        if modes:
            phys = [mapping[m] for m in modes]
            if any(p < 0 for p in phys):
                raise ValueError(
                    f"{op_name} references a mode already measured/removed"
                )
        else:
            phys = []
        merged.append((op_name, tuple(phys), fixed, pnames, refs))
    flush()
    return segments, frozenset(params)


def _run_op(
    op: tuple,
    st: GaussianState,
    results: dict[str, float],
    values: dict,
    *,
    rng: np.random.Generator | None = None,
) -> tuple[GaussianState, dict[str, float]]:
    """Execute one break-point op (channel / measure / ParamRef op).

    Values already bound for ``pnames``; ParamRef resolved from ``results``.
    """
    op_name, modes, fixed, pnames, refs = op
    kwargs = dict(fixed)
    for k, v in pnames.items():
        if v not in values:
            raise ValueError(f"Missing parameter '{v}' for {op_name}")
        kwargs[k] = values[v]
    if op_name == 'measure_homodyne':
        phys_mode = modes[0]
        val, st = homodyne_sample_and_condition(
            st, phys_mode, kwargs['phi'], rng=rng
        )
        results[kwargs['name']] = val
        st = st.remove_mode(phys_mode)
    elif op_name == 'measure_heterodyne':
        phys_mode = modes[0]
        val, st = heterodyne_sample_and_condition(
            st, phys_mode, rng=rng
        )
        results[kwargs['name']] = val
    elif op_name == 'gaussian_channel':
        X = kwargs['X']
        if X.shape[0] != 2 * st.nmode:
            raise ValueError(
                f"gaussian_channel X/Y size {X.shape[0]} does not match "
                f"current 2*nmode={2 * st.nmode} (mode removed by "
                f"measurement? use loss/amplifier/phase_noise instead)"
            )
        st = apply_gaussian_channel(
            st, X, kwargs['Y'], kwargs.get('d'),
            validate=kwargs.get('validate', True),
        )
    else:
        for k, v in refs.items():
            if v.source not in results:
                raise ValueError(
                    f"ParamRef '{k}' references '{v.source}' "
                    f"which has not been measured yet"
                )
            kwargs[k] = complex(results[v.source] * v.gain)
        st = _apply(op_name, st, tuple(modes), **kwargs)
    return st, results


class CompiledGaussian:
    """Compiled circuit: immutable segment snapshot; run() instantiates.

    Public surface: ``nmode``, ``params``, ``run(**values)``.
    """

    def __init__(self, nmode: int, segments: list, params: frozenset[str]) -> None:
        self.nmode = nmode
        self.params = params
        self._segments = list(segments)

    def run(
        self,
        *,
        rng: np.random.Generator | None = None,
        **values: float,
    ) -> GaussianState | tuple[GaussianState, dict[str, float]]:
        """Execute compiled segments. Same semantics as ``GaussianCircuit.run``."""
        st = GaussianState.vacuum(self.nmode)
        results: dict[str, float] = {}
        for seg in self._segments:
            if seg[0] == 'merged':
                _, nmode, ops = seg
                S, d = _instantiate(ops, nmode, values)
                st = apply_symplectic(st, S, d, validate=False)
                continue
            st, results = _run_op(seg[1], st, results, values, rng=rng)
        if results:
            return st, results
        return st

    def __repr__(self) -> str:
        lines = [f"CompiledGaussian({self.nmode})"]
        for seg in self._segments:
            if seg[0] == 'merged':
                lines.append(f"  merged({len(seg[2])} ops)")
            else:
                op_name, modes, fixed, pnames, refs = seg[1]
                args = [str(m) for m in modes]
                args += [f"{k}={v}" for k, v in fixed.items()]
                args += [f"{k}=${{{v}}}" for k, v in pnames.items()]
                args += [f"{k}=${{{v.source}}}*{v.gain}" for k, v in refs.items()]
                lines.append(f"  .{op_name}({', '.join(args)})")
        return "\n".join(lines)


_DISPATCH = {
    'squeeze': lambda st, m, **kw: _squeeze_gate(st, m, kw['r']),
    'displace': lambda st, m, **kw: _displace_gate(st, m, kw['alpha']),
    'phase': lambda st, m, **kw: _phase_gate(st, m, kw['theta']),
    'fourier': lambda st, m, **kw: _phase_gate(st, m, 0.5 * np.pi),
    'beamsplitter': lambda st, m, **kw: _bs_gate(
        st, m[0], m[1], kw['theta'], kw.get('phi', 0.0)
    ),
    'mach_zehnder': lambda st, m, **kw: _mz_gate(
        st, m[0], m[1], kw['theta'], kw.get('phi', 0.0)
    ),
    'two_mode_squeeze': lambda st, m, **kw: _tms_gate(st, m[0], m[1], kw['r']),
    'cz': lambda st, m, **kw: _cz_gate(st, m[0], m[1], kw['weight']),
    'cx': lambda st, m, **kw: _cx_gate(st, m[0], m[1], kw['weight']),
    'interferometer': lambda st, m, **kw: _interf_gate(st, kw['U']),
    'loss': lambda st, m, **kw: _loss_gate(
        st, kw['T'], m[0], kw.get('nbar', 0.0)
    ),
    'amplifier': lambda st, m, **kw: _amp_gate(
        st, kw['G'], m[0] if m else None, kw.get('nbar', 0.0)
    ),
    'phase_noise': lambda st, m, **kw: _pn_gate(
        st, kw['sigma'], m[0] if m else None
    ),
}


def _apply(op_name: str, st: GaussianState, modes: tuple, **kwargs) -> GaussianState:
    """Dispatch one op (channels + dynamic unitary ops)."""
    return _DISPATCH[op_name](st, modes, **kwargs)


def _squeeze_gate(st, m, r):
    return apply_symplectic(
        st, _factor(('squeeze', m, {'r': r, 'phi': 0.0}, {}, {}), st.nmode)[0],
        validate=False,
    )


def _displace_gate(st, m, alpha):
    return apply_symplectic(
        st, np.eye(2 * st.nmode), d_displace(st.nmode, alpha, m[0]),
        validate=False,
    )


def _phase_gate(st, m, theta):
    return apply_symplectic(
        st, S_phase(st.nmode, theta, m[0]), validate=False
    )


def _bs_gate(st, m1, m2, theta, phi):
    return apply_symplectic(
        st, S_beamsplitter(st.nmode, m1, m2, theta, phi), validate=False
    )


def _mz_gate(st, m1, m2, theta, phi):
    return apply_symplectic(
        st, S_mach_zehnder(st.nmode, m1, m2, theta, phi), validate=False
    )


def _tms_gate(st, m1, m2, r):
    return apply_symplectic(
        st, S_two_mode_squeeze(st.nmode, r, m1, m2), validate=False
    )


def _cz_gate(st, m1, m2, weight):
    return apply_symplectic(st, S_CZ(st.nmode, weight, m1, m2), validate=False)


def _cx_gate(st, m1, m2, weight):
    return apply_symplectic(st, S_CX(st.nmode, weight, m1, m2), validate=False)


def _interf_gate(st, U):
    return apply_symplectic(
        st, S_from_unitary(U, validate=True), validate=False
    )


def _loss_gate(st, T, mode, nbar):
    from cvsim.gaussian.channels import loss as loss_fn
    return loss_fn(st, T, mode, nbar)


def _amp_gate(st, G, mode, nbar):
    from cvsim.gaussian.channels import amplifier as amp_fn
    return amp_fn(st, G, mode, nbar)


def _pn_gate(st, sigma, mode):
    from cvsim.gaussian.channels import phase_noise as pn_fn
    return pn_fn(st, sigma, mode)
