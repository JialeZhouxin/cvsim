"""Bosonic circuit compilation (B5, ADR-0004).

Mirrors the Gaussian compile path: segment compilation, symplectic
factor instantiation (reuses ``cvsim.symplectic``), and per-op dispatch.
Physics is component-wise — ``_apply_merged`` runs ``apply_symplectic``
over all components (K=1 vacuum start, gates do not add components).
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.channels import _apply_affine, amplifier as _amp, loss as _loss, phase_noise as _pn
from cvsim.bosonic.gates import apply_symplectic
from cvsim.bosonic.measure import (
    heterodyne_sample_and_condition,
    sample_threshold,
)
from cvsim.bosonic.observables import homodyne_sample_and_condition
from cvsim.bosonic.state import BosonicState, Component
from cvsim.circuit_common import CompiledCircuit, compile_segments
from cvsim.symplectic import (
    S_CX,
    S_CZ,
    S_beamsplitter,
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
     'measure_homodyne', 'measure_heterodyne', 'measure_threshold'}
)
# Measurement ops that remove their mode from the physical mapping.
_REMOVE_MODE_OPS = frozenset({'measure_homodyne', 'measure_heterodyne'})
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
        return S_beamsplitter(nmode, m0, m1, kw['theta'], kw.get('phi', 0.0)), np.zeros(2 * nmode)
    if op_name == 'mach_zehnder':
        return S_mach_zehnder(nmode, m0, m1, kw['theta'], kw.get('phi', 0.0)), np.zeros(2 * nmode)
    if op_name == 'two_mode_squeeze':
        return S_two_mode_squeeze(nmode, kw['r'], m0, m1), np.zeros(2 * nmode)
    if op_name == 'cz':
        return S_CZ(nmode, kw['weight'], m0, m1), np.zeros(2 * nmode)
    if op_name == 'cx':
        return S_CX(nmode, kw['weight'], m0, m1), np.zeros(2 * nmode)
    if op_name == 'interferometer':
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
        if Si.shape != S.shape:
            raise ValueError(
                f"merge shape drift: factor {Si.shape} != segment S {S.shape} "
                f"(nmode={nmode}) — compile-time mode count mismatch"
            )
        S = Si @ S
        d = Si @ d + di
    return S, d


def _apply_channel_affine(st: BosonicState, X: np.ndarray, Y: np.ndarray, d: np.ndarray | None) -> BosonicState:
    """Per-component V ← X V Xᵀ + Y, r̄ ← X r̄ + d (if given), w unchanged.

    Extends ``channels._apply_affine`` with the displacement ``d`` (needed by
    ``gaussian_channel`` circuit op). Kept local to avoid touching channels.py.
    """
    out: list[Component] = []
    dd = np.zeros(X.shape[0]) if d is None else np.asarray(d, dtype=float)
    for c in st.components:
        V = X @ c.V @ X.T + Y
        V = 0.5 * (V + V.T)
        rbar = X @ c.rbar + dd
        out.append(Component(V=V, rbar=rbar, w=c.w))
    return BosonicState(components=out)


def _run_op(
    op: tuple,
    st: BosonicState,
    results: dict[str, float],
    values: dict,
    *,
    rng: np.random.Generator | None = None,
) -> tuple[BosonicState, dict[str, float]]:
    """Execute one break-point op (channel / measure / ParamRef op)."""
    op_name, modes, fixed, pnames, refs = op
    kwargs = dict(fixed)
    for k, v in pnames.items():
        if v not in values:
            raise ValueError(f"Missing parameter '{v}' for {op_name}")
        kwargs[k] = values[v]
    if op_name == 'measure_homodyne':
        phys_mode = modes[0]
        outcomes, post = homodyne_sample_and_condition(
            st, phys_mode, kwargs['phi'], rng=rng, shots=1
        )
        results[kwargs['name']] = float(outcomes[0])
        st = post.remove_mode(phys_mode)
    elif op_name == 'measure_heterodyne':
        phys_mode = modes[0]
        beta, post = heterodyne_sample_and_condition(st, phys_mode, rng=rng)
        results[kwargs['name']] = complex(beta)
        st = post  # heterodyne_condition already removes the mode
    elif op_name == 'measure_threshold':
        val = sample_threshold(st, modes[0], rng=rng)
        results[kwargs['name']] = int(val)
    elif op_name == 'gaussian_channel':
        X = kwargs['X']
        if X.shape[0] != 2 * st.nmode:
            raise ValueError(
                f"gaussian_channel X/Y size {X.shape[0]} does not match "
                f"current 2*nmode={2 * st.nmode} (mode removed by "
                f"measurement? use loss/amplifier/phase_noise instead)"
            )
        st = _apply_channel_affine(
            st, X, kwargs['Y'], kwargs.get('d'),
        )
    else:
        # channel (loss/amplifier/phase_noise) or ParamRef feedforward gate
        for k, v in refs.items():
            if v.source not in results:
                raise ValueError(
                    f"ParamRef '{k}' references '{v.source}' "
                    f"which has not been measured yet"
                )
            kwargs[k] = complex(results[v.source] * v.gain)
        if op_name == 'loss':
            st = _loss(st, kwargs['T'], modes[0] if modes else None, kwargs.get('nbar', 0.0))
        elif op_name == 'amplifier':
            st = _amp(st, kwargs['G'], modes[0] if modes else None, kwargs.get('nbar', 0.0))
        elif op_name == 'phase_noise':
            st = _pn(st, kwargs['sigma'], modes[0] if modes else None)
        else:
            # ParamRef feedforward gate: re-merge as a single-op merged segment
            st = _apply_merged([(op_name, modes, kwargs, {}, {})], st.nmode, values, st)
    return st, results


def _apply_merged(ops: list[tuple], nmode: int, values: dict, st: BosonicState) -> BosonicState:
    S, d = _instantiate(ops, nmode, values)
    return apply_symplectic(st, S, d)


def _compile_segments(ops: list[tuple], nmode: int) -> tuple[list, frozenset[str]]:
    return compile_segments(ops, nmode, break_ops=_BREAK_OPS, remove_mode_ops=_REMOVE_MODE_OPS)


class CompiledBosonic(CompiledCircuit):
    """Compiled Bosonic circuit: immutable segment snapshot; run() instantiates.

    Public surface: ``nmode``, ``params``, ``run(**values)`` (ADR-0004).
    ``initial`` (B6) is the — optional — prepared initial state (vacuum when
    None); K=1-vacuum semantics of B5 are preserved for default circuits.
    """

    def __init__(
        self,
        nmode: int,
        segments: list,
        params: frozenset[str],
        initial: BosonicState | None = None,
    ) -> None:
        super().__init__(nmode, segments, params)
        self._initial = initial

    def _init_state(self) -> BosonicState:
        if self._initial is not None:
            if self._initial.nmode != self.nmode:
                raise ValueError(
                    f"initial state nmode {self._initial.nmode} != circuit nmode {self.nmode}"
                )
            return self._initial
        return BosonicState.vacuum(self.nmode)

    def _apply_merged(self, ops: list[tuple], nmode: int, values: dict, st: BosonicState) -> BosonicState:
        return _apply_merged(ops, nmode, values, st)

    def _run_op(self, op, st, results, values, *, rng=None):
        return _run_op(op, st, results, values, rng=rng)

    def run_steps(self, *, rng=None, **values):
        """Run compiled segments capturing a per-break-point snapshot (B6).

        Returns ``(final_state, results, steps)`` where ``steps`` is a list of
        ``(op_name, state)`` after each channel/measurement break point.
        Merged gate segments are not snapshotted (no intermediate inspection
        inside a gate run).
        """
        st = self._init_state()
        results: dict = {}
        steps: list[tuple[str, BosonicState]] = []
        for seg in self._segments:
            if seg[0] == "merged":
                _, nmode, ops = seg
                st = self._apply_merged(ops, nmode, values, st)
                continue
            op = seg[1]
            st, results = self._run_op(op, st, results, values, rng=rng)
            steps.append((str(op[0]), st))
        return st, results, steps
