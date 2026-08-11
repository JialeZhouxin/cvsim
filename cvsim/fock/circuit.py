"""FockCircuit: declarative Fock circuit on the shared DSL core (ADR-0004).

Mirror of ``GaussianCircuit`` (same 5-tuple ops, same compile/run single
execution path). Representation specifics (F3 decisions):

* merged segments apply Kronecker per-op via tensordot on the mode axes —
  never materialize the N^{2m} full-space unitary (perf budget, vision §5);
* two-mode gates require equal cutoffs on both modes (matrices are N²×N²);
* all measurements **condition** (posterior state update) — no mode removal
  (Fock homodyne/PNR/heterodyne keep the mode, unlike Gaussian homodyne).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.linalg import expm, logm

from cvsim.circuit_common import (
    CompiledCircuit,
    ParamRef,
    compile_segments,
    partition,
)
from cvsim.fock.channels import (
    amplifier as _ch_amplifier,
)
from cvsim.fock.channels import (
    apply_kraus as _ch_apply_kraus,
)
from cvsim.fock.channels import (
    loss as _ch_loss,
)
from cvsim.fock.channels import (
    phase_noise as _ch_phase_noise,
)
from cvsim.fock.density import FockDensity
from cvsim.fock.gates import annihilation
from cvsim.fock.observables import (
    heterodyne_sample_and_condition,
    homodyne_sample_and_condition,
    pnr_sample_and_condition,
)
from cvsim.fock.state import FockState

#: Ops that break a compile segment (channels + measurements; ADR-0002 d2).
_BREAK_OPS = frozenset(
    {
        'loss', 'amplifier', 'phase_noise', 'apply_kraus',
        'measure_pnr', 'measure_homodyne', 'measure_heterodyne',
    }
)
#: Fock measurements collapse the measured mode into the posterior —
#: the mode leaves the physical mapping (same shift semantics as Gaussian
#: homodyne). PNR conditioning differs from Gaussian remove-mode only in
#: what the *surviving* modes are (conditioned, not discarded).
_REMOVE_MODE_OPS = frozenset({'measure_pnr', 'measure_homodyne', 'measure_heterodyne'})
#: Unitary ops merged into a segment (Kronecker per-op application).
_MERGEABLE_OPS = frozenset(
    {
        'squeeze', 'displace', 'phase', 'kerr', 'beamsplitter',
        'two_mode_squeeze', 'cz', 'cx', 'mach_zehnder',
        'interferometer', 'apply_unitary',
    }
)


def _phase_diag(N: int, theta: float) -> np.ndarray:
    return np.diag(np.exp(1j * theta * np.arange(N)))


def _kerr_diag(N: int, chi: float) -> np.ndarray:
    return np.diag(np.exp(1j * chi * np.arange(N) ** 2))


def _squeeze_U(N: int, r: float) -> np.ndarray:
    a = annihilation(N)
    ad = a.conj().T
    return expm(0.5 * r * (a @ a - ad @ ad))


def _displace_U(N: int, alpha: complex) -> np.ndarray:
    a = annihilation(N)
    return expm(alpha * a.conj().T - np.conj(alpha) * a)


def _bs_U(N: int, theta: float, phi: float) -> np.ndarray:
    """BS(θ,φ) = exp[θ(e^{iφ} a0† a1 − h.c.)], (N²,N²) — gates convention."""
    a = annihilation(N)
    ad = a.conj().T
    G = theta * (np.exp(1j * phi) * np.kron(ad, a) - np.exp(-1j * phi) * np.kron(a, ad))
    return expm(G)


def _tms_U(N: int, r: float) -> np.ndarray:
    a = annihilation(N)
    ad = a.conj().T
    return expm(r * (np.kron(ad, ad) - np.kron(a, a)))


def _quadrature_matrices(N: int) -> tuple[np.ndarray, np.ndarray]:
    a = annihilation(N)
    x = (a + a.conj().T) / np.sqrt(2.0)
    p = (a - a.conj().T) / (1j * np.sqrt(2.0))
    return x, p


def _cz_U(N: int, weight: float) -> np.ndarray:
    x, _ = _quadrature_matrices(N)
    return expm(1j * weight * np.kron(x, x))


def _cx_U(N: int, weight: float) -> np.ndarray:
    x, p = _quadrature_matrices(N)
    return expm(1j * weight * np.kron(x, p))


def _mz_U(N: int, theta: float, phi: float) -> np.ndarray:
    """MZ(θ,φ) = BS(π/4,0)·(I⊗P(φ))·BS(θ,φ) — gates convention."""
    bs1 = _bs_U(N, theta, phi)
    ph = _phase_diag(N, phi)
    bs2 = _bs_U(N, np.pi / 4, 0.0)
    return bs2 @ np.kron(np.eye(N), ph) @ bs1


def _factor1(op_name: str, N: int, fixed: dict) -> np.ndarray:
    """Single-mode (N,N) unitary factor for a merged op."""
    if op_name == 'squeeze':
        return _squeeze_U(N, float(fixed['r']))
    if op_name == 'displace':
        return _displace_U(N, complex(fixed['alpha']))
    if op_name == 'phase':
        return _phase_diag(N, float(fixed.get('theta', 0.0)))
    if op_name == 'kerr':
        return _kerr_diag(N, float(fixed.get('chi', 0.0)))
    raise ValueError(f"_factor1: op {op_name} is not single-mode")


def _factor2(op_name: str, N: int, fixed: dict) -> np.ndarray:
    """Two-mode (N²,N²) unitary factor for a merged op (equal cutoffs)."""
    if op_name == 'beamsplitter':
        return _bs_U(N, float(fixed.get('theta', np.pi / 4)), float(fixed.get('phi', 0.0)))
    if op_name == 'two_mode_squeeze':
        return _tms_U(N, float(fixed['r']))
    if op_name == 'cz':
        return _cz_U(N, float(fixed['weight']))
    if op_name == 'cx':
        return _cx_U(N, float(fixed['weight']))
    if op_name == 'mach_zehnder':
        return _mz_U(N, float(fixed.get('theta', np.pi / 4)), float(fixed.get('phi', 0.0)))
    raise ValueError(f"_factor2: op {op_name} is not two-mode")


def _interferometer_U(Ns: tuple[int, ...], U: np.ndarray) -> np.ndarray:
    """Full-space m×m passive unitary: H = Σ (log U)_ij a_i† a_j → expm."""
    m = U.shape[0]
    a = [annihilation(N) for N in Ns]
    ad = [x.conj().T for x in a]
    H = np.zeros((np.prod(Ns), np.prod(Ns)), dtype=complex)
    L = logm(U)
    # H = Σ_ij L_ij a_i† a_j  (kron over all modes, identity elsewhere)
    for i in range(m):
        for j in range(m):
            term = np.eye(1, dtype=complex)
            for k in range(m):
                if k == i and k == j:
                    term = np.kron(term, ad[k] @ a[k])
                elif k == i:
                    term = np.kron(term, ad[k])
                elif k == j:
                    term = np.kron(term, a[k])
                else:
                    term = np.kron(term, np.eye(Ns[k], dtype=complex))
            H = H + L[i, j] * term
    return expm(H)


def _kron_apply(U1: np.ndarray, amps: np.ndarray, mode: int) -> np.ndarray:
    """Apply single-mode (N,N) U on axis `mode` of an m-mode amp tensor."""
    tr = np.tensordot(U1, amps, axes=([1], [mode]))
    return np.moveaxis(tr, 0, mode)


def _kron_apply2(
    U2: np.ndarray, amps: np.ndarray, m1: int, m2: int, N1: int, N2: int
) -> np.ndarray:
    """Apply two-mode U ((N1·N2)²) on axes (m1,m2) of an m-mode amp tensor."""
    U4 = U2.reshape(N1, N2, N1, N2)  # [out1, out2, in1, in2]
    a = np.moveaxis(amps, (m1, m2), (-2, -1))
    out = np.einsum('ijkl,...kl->...ij', U4, a)
    return np.moveaxis(out, (-2, -1), (m1, m2))


def _full_apply(U: np.ndarray, amps: np.ndarray) -> np.ndarray:
    """Apply a full-space (d,d) U (interferometer / apply_unitary all-mode)."""
    d = amps.size
    if U.shape != (d, d):
        raise ValueError(f"U shape {U.shape} incompatible with state dim {d}")
    return U @ amps.ravel()


class FockCircuit:
    """Declarative Fock circuit with parameter placeholders.

    Parameters can be fixed (number), symbolic (string name), or feedforward
    (``ParamRef`` referencing a measurement). Measurement + feedforward::

        c = FockCircuit(2, cutoff=12)
        c.squeeze(0, r=0.5)
        c.beamsplitter(0, 1)
        c.measure_pnr(1, name='m_n')
        c.displace(0, alpha=ParamRef('m_n', gain=0.1))  # feedback

        state, results = c.run()
        # results == {'m_n': 3}

    ``cutoff`` may be a per-mode list (equal cutoffs required on the modes
    of each two-mode gate).
    """

    def __init__(self, nmode: int, cutoff: int | list[int] = 10) -> None:
        if nmode < 1:
            raise ValueError("nmode must be >= 1")
        if isinstance(cutoff, int):
            cutoffs = [cutoff] * nmode
        else:
            cutoffs = list(cutoff)
            if len(cutoffs) != nmode:
                raise ValueError(f"cutoffs len {len(cutoffs)} != nmode {nmode}")
        if any(c < 1 for c in cutoffs):
            raise ValueError("cutoffs must be >= 1")
        self.nmode = nmode
        self.cutoffs = cutoffs
        self._ops: list[tuple[str, tuple, dict, dict, dict]] = []

    # -- composition ------------------------------------------------------

    def __iadd__(self, other: FockCircuit) -> FockCircuit:
        if self.nmode != other.nmode:
            raise ValueError(f"nmode mismatch: {self.nmode} vs {other.nmode}")
        if self.cutoffs != other.cutoffs:
            raise ValueError(f"cutoffs mismatch: {self.cutoffs} vs {other.cutoffs}")
        self._ops.extend(other._ops)
        return self

    def __add__(self, other: FockCircuit) -> FockCircuit:
        c = FockCircuit(self.nmode, self.cutoffs)
        c._ops = list(self._ops)
        c += other
        return c

    # -- builder: single-mode gates ---------------------------------------

    def squeeze(self, mode: int, r: float | str = 0.0) -> FockCircuit:
        self._ops.append(self._partition('squeeze', [mode], r=r))
        return self

    def displace(
        self, mode: int, alpha: complex | str | ParamRef = 0.0
    ) -> FockCircuit:
        self._ops.append(self._partition('displace', [mode], alpha=alpha))
        return self

    def phase(self, mode: int, theta: float | str = 0.0) -> FockCircuit:
        self._ops.append(self._partition('phase', [mode], theta=theta))
        return self

    def kerr(self, mode: int, chi: float | str = 0.0) -> FockCircuit:
        self._ops.append(self._partition('kerr', [mode], chi=chi))
        return self

    # -- builder: two-mode gates ------------------------------------------

    def beamsplitter(
        self,
        mode1: int,
        mode2: int,
        theta: float | str = np.pi / 4,
        phi: float | str = 0.0,
    ) -> FockCircuit:
        self._ops.append(
            self._partition('beamsplitter', [mode1, mode2], theta=theta, phi=phi)
        )
        return self

    def two_mode_squeeze(
        self, mode1: int, mode2: int, r: float | str = 0.0
    ) -> FockCircuit:
        self._ops.append(self._partition('two_mode_squeeze', [mode1, mode2], r=r))
        return self

    def cz(self, mode1: int, mode2: int, weight: float | str = 1.0) -> FockCircuit:
        self._ops.append(self._partition('cz', [mode1, mode2], weight=weight))
        return self

    def cx(self, mode1: int, mode2: int, weight: float | str = 1.0) -> FockCircuit:
        self._ops.append(self._partition('cx', [mode1, mode2], weight=weight))
        return self

    def mach_zehnder(
        self,
        mode1: int,
        mode2: int,
        theta: float | str = np.pi / 4,
        phi: float | str = 0.0,
    ) -> FockCircuit:
        self._ops.append(
            self._partition('mach_zehnder', [mode1, mode2], theta=theta, phi=phi)
        )
        return self

    def interferometer(self, U: np.ndarray) -> FockCircuit:
        """Passive interferometer: full nmode×nmode unitary U."""
        U = np.asarray(U, dtype=complex).copy()
        if U.shape != (self.nmode, self.nmode):
            raise ValueError(
                f"U shape {U.shape} incompatible with nmode={self.nmode}"
            )
        self._ops.append(
            ('interferometer', tuple(range(self.nmode)), {'U': U}, {}, {})
        )
        return self

    def apply_unitary(
        self, U: np.ndarray, modes: list[int] | None = None
    ) -> FockCircuit:
        """Generic truncated unitary on ``modes`` (all modes if None)."""
        U = np.asarray(U, dtype=complex).copy()
        if modes is None:
            modes = list(range(self.nmode))
        self._ops.append(
            ('apply_unitary', tuple(modes), {'U': U}, {}, {})
        )
        return self

    # -- builder: channels -------------------------------------------------

    def loss(self, mode: int, eta: float | str) -> FockCircuit:
        self._ops.append(self._partition('loss', [mode], eta=eta))
        return self

    def amplifier(
        self, mode: int, G: float | str, nbar: float | str = 0.0
    ) -> FockCircuit:
        self._ops.append(self._partition('amplifier', [mode], G=G, nbar=nbar))
        return self

    def phase_noise(self, mode: int, sigma: float | str) -> FockCircuit:
        self._ops.append(self._partition('phase_noise', [mode], sigma=sigma))
        return self

    def apply_kraus(
        self, mode: int, kraus_ops: list[np.ndarray]
    ) -> FockCircuit:
        self._ops.append(
            ('apply_kraus', [mode], {'kraus_ops': kraus_ops}, {}, {})
        )
        return self

    # -- builder: measurements ---------------------------------------------

    def measure_pnr(self, mode: int, name: str) -> FockCircuit:
        """PNR measurement: sample n, condition the posterior (mode kept)."""
        self._ops.append(
            self._partition(
                'measure_pnr', [mode], _fixed_str_keys={'name'}, name=name
            )
        )
        return self

    def measure_homodyne(self, mode: int, phi: float, name: str) -> FockCircuit:
        """Homodyne measurement: sample x_φ, condition (truncated projector).

        Mode is kept (Fock conditioning, unlike Gaussian remove-mode).
        """
        self._ops.append(
            self._partition(
                'measure_homodyne', [mode], _fixed_str_keys={'name'},
                phi=phi, name=name,
            )
        )
        return self

    def measure_heterodyne(self, mode: int, name: str) -> FockCircuit:
        """Heterodyne measurement: sample β (coherent POVM), condition."""
        self._ops.append(
            self._partition(
                'measure_heterodyne', [mode], _fixed_str_keys={'name'},
                name=name,
            )
        )
        return self

    # -- execution ---------------------------------------------------------

    def to_ir(self) -> dict:
        """Serialize to a circuit_v1 dict (ADR-0003; with ``cutoff``)."""
        from cvsim.fock.ir import to_ir

        return to_ir(self)

    @classmethod
    def from_ir(cls, data: dict) -> FockCircuit:
        """Rebuild from a circuit_v1 dict (ADR-0003)."""
        from cvsim.fock.ir import from_ir

        return from_ir(data)

    def compile(self) -> CompiledFock:
        """Structure-compile: segment ops (ADR-0002), resolve mode mapping."""
        segments, params = compile_segments(
            self._ops, self.nmode,
            break_ops=_BREAK_OPS, remove_mode_ops=_REMOVE_MODE_OPS,
        )
        return CompiledFock(self.nmode, self.cutoffs, segments, params)

    def run(self, *, rng=None, **params: float) -> Any:
        """Execute with parameter values (single path: compile then run).

        Returns ``FockState`` if no measurements, else
        ``(FockState, results)``.
        """
        return self.compile().run(rng=rng, **params)

    # -- inspection --------------------------------------------------------

    def __repr__(self) -> str:
        lines = [f"FockCircuit({self.nmode}, cutoff={self.cutoffs})"]
        for op_name, modes, fixed, pnames, refs in self._ops:
            args = [str(m) for m in modes]
            for k, v in fixed.items():
                if isinstance(v, np.ndarray):
                    args.append(f"{k}=<{v.shape}>")
                else:
                    args.append(f"{k}={v}")
            for k, v in pnames.items():
                args.append(f"{k}=${v}")
            for k, v in refs.items():
                args.append(f"{k}=@{v.source}")
            lines.append(f"  {op_name}({', '.join(args)})")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._ops)

    def _partition(
        self,
        op_name: str,
        modes: list[int],
        *,
        _fixed_str_keys: frozenset[str] = frozenset(),
        **kwargs: Any,
    ) -> tuple[str, tuple, dict, dict, dict]:
        return partition(op_name, modes, _fixed_str_keys=_fixed_str_keys, **kwargs)


class CompiledFock(CompiledCircuit):
    """Compiled Fock circuit: Kronecker per-op merged segments (ADR-0004)."""

    def __init__(
        self, nmode: int, cutoffs: list[int], segments: list, params: frozenset[str]
    ) -> None:
        super().__init__(nmode, segments, params)
        self.cutoffs = list(cutoffs)

    def _init_state(self) -> FockState:
        amps = np.zeros(tuple(self.cutoffs), dtype=complex)
        amps[(0,) * self.nmode] = 1.0
        return FockState(amps=amps)

    def _apply_merged(self, ops, nmode, values, st):
        if isinstance(st, FockDensity):
            return self._apply_merged_density(ops, values, st)
        amps = st.amps
        for op_name, modes, fixed, pnames, _refs in ops:
            fixed = dict(fixed)
            for k, v in pnames.items():
                if v not in values:
                    raise ValueError(f"Missing parameter '{v}' for {op_name}")
                fixed[k] = values[v]
            if op_name in ('interferometer',):
                amps = _full_apply(
                    _interferometer_U(tuple(self.cutoffs), fixed['U']), amps
                ).reshape(amps.shape)
            elif op_name == 'apply_unitary':
                U = fixed['U']
                msel = len(modes)
                if msel == 1:
                    if self.cutoffs[modes[0]] != U.shape[0]:
                        raise ValueError(
                            f"apply_unitary dim {U.shape[0]} != cutoff "
                            f"{self.cutoffs[modes[0]]} on mode {modes[0]}"
                        )
                    amps = _kron_apply(U, amps, modes[0])
                elif msel == 2:
                    n1, n2 = self.cutoffs[modes[0]], self.cutoffs[modes[1]]
                    if U.shape != (n1 * n2, n1 * n2):
                        raise ValueError(
                            f"apply_unitary dim {U.shape} incompatible with "
                            f"modes {modes} cutoffs ({n1},{n2})"
                        )
                    amps = _kron_apply2(U, amps, modes[0], modes[1], n1, n2)
                else:
                    amps = _full_apply(U, amps).reshape(amps.shape)
            else:
                N = self.cutoffs[modes[0]]
                if len(modes) == 1:
                    amps = _kron_apply(_factor1(op_name, N, fixed), amps, modes[0])
                else:
                    if self.cutoffs[modes[0]] != self.cutoffs[modes[1]]:
                        raise ValueError(
                            f"{op_name} requires equal cutoffs: "
                            f"{self.cutoffs[modes[0]]} vs {self.cutoffs[modes[1]]}"
                        )
                    amps = _kron_apply2(
                        _factor2(op_name, N, fixed), amps,
                        modes[0], modes[1], N, N,
                    )
        return FockState(amps=amps)

    def _apply_merged_density(self, ops, values, st) -> FockDensity:
        """ρ' = U ρ U† per merged op (Kronecker, no full-space material)."""
        rho = st.rho
        Ns = tuple(self.cutoffs)
        m = self.nmode
        for op_name, modes, fixed, pnames, _refs in ops:
            fixed = dict(fixed)
            for k, v in pnames.items():
                if v not in values:
                    raise ValueError(f"Missing parameter '{v}' for {op_name}")
                fixed[k] = values[v]
            if op_name == 'interferometer':
                U = _interferometer_U(Ns, fixed['U'])
                rho = U @ rho @ U.conj().T
                continue
            if op_name == 'apply_unitary':
                U = fixed['U']
                if len(modes) == 1:
                    rho = _kron_apply2_density(U, rho, m, modes[0], modes[0], Ns)
                else:
                    raise NotImplementedError(
                        f"apply_unitary density {len(modes)}-mode out of scope"
                    )
                continue
            if len(modes) == 1:
                U = _factor1(op_name, self.cutoffs[modes[0]], fixed)
                rho = _kron_apply2_density(U, rho, m, modes[0], modes[0], Ns)
            else:
                N = self.cutoffs[modes[0]]
                if self.cutoffs[modes[1]] != N:
                    raise ValueError(
                        f"{op_name} requires equal cutoffs: "
                        f"{N} vs {self.cutoffs[modes[1]]}"
                    )
                U = _factor2(op_name, N, fixed)
                rho = _kron_apply2_density(U, rho, m, modes[0], modes[1], Ns)
        return FockDensity(rho=rho, nmode=m)

    def _run_op(self, op, st, results, values, *, rng=None):
        op_name, modes, fixed, pnames, refs = op
        kwargs = dict(fixed)
        for k, v in pnames.items():
            if v not in values:
                raise ValueError(f"Missing parameter '{v}' for {op_name}")
            kwargs[k] = values[v]
        if op_name == 'measure_pnr':
            val, st = pnr_sample_and_condition(st, modes[0], rng=rng)
            results[kwargs['name']] = val
        elif op_name == 'measure_homodyne':
            val, st = homodyne_sample_and_condition(
                st, modes[0], kwargs['phi'], rng=rng
            )
            results[kwargs['name']] = val
        elif op_name == 'measure_heterodyne':
            val, st = heterodyne_sample_and_condition(st, modes[0], rng=rng)
            results[kwargs['name']] = val
        elif op_name in ('loss', 'amplifier', 'phase_noise', 'apply_kraus'):
            for k, v in refs.items():
                if v.source not in results:
                    raise ValueError(
                        f"ParamRef '{k}' references '{v.source}' "
                        f"which has not been measured yet"
                    )
                kwargs[k] = complex(results[v.source] * v.gain)
            if op_name == 'loss':
                st = _ch_loss(st, float(kwargs['eta']), modes[0])
            elif op_name == 'amplifier':
                st = _ch_amplifier(
                    st, float(kwargs['G']), modes[0],
                    float(kwargs.get('nbar', 0.0)),
                )
            elif op_name == 'phase_noise':
                st = _ch_phase_noise(st, float(kwargs['sigma']), modes[0])
            else:
                st = _ch_apply_kraus(st, kwargs['kraus_ops'], modes[0])
        else:
            # break op with ParamRef: a unitary gate with feedforward params
            for k, v in refs.items():
                if v.source not in results:
                    raise ValueError(
                        f"ParamRef '{k}' references '{v.source}' "
                        f"which has not been measured yet"
                    )
                kwargs[k] = complex(results[v.source] * v.gain)
            st = self._apply_merged(
                [(op_name, modes, kwargs, {}, {})], self.nmode, {}, st
            )
        return st, results


def _kron_apply2_density(
    U: np.ndarray, rho: np.ndarray, nmode: int,
    m1: int, m2: int, Ns: tuple[int, ...],
) -> np.ndarray:
    """ρ' = (U ⊗ I_rest) ρ (U† ⊗ I_rest) on modes (m1, m2).

    Single-mode when m1 == m2. U is (N^k, N^k) with k = 1 or 2.
    Dense tensor layout: axes [out0..out_{m-1}, in0..in_{m-1}].
    """
    k = 1 if m1 == m2 else 2
    N = Ns[m1]
    if k == 2 and Ns[m2] != N:
        raise ValueError("two-mode density op requires equal cutoffs")
    d = rho.shape[0]
    t = rho.reshape(Ns + Ns)
    sel = (m1, m2) if k == 2 else (m1,)
    rest = [a for a in range(nmode) if a not in sel]
    in_sel = tuple(a + nmode for a in sel)
    in_rest = [a + nmode for a in rest]
    order = list(sel) + rest + list(in_sel) + in_rest
    t2 = np.transpose(t, order)  # [out_sel, out_rest, in_sel, in_rest]
    R = int(np.prod([Ns[a] for a in rest]))
    t3 = t2.reshape(N**k, R, N**k, R)
    # ρ'[o; i] = Σ_ab U[o,a] ρ[a;b] conj(U[i,b]) — a,b summed, o=out sel, i=in sel
    out3 = np.einsum('oa,arbs,ib->oris', U, t3, U.conj())
    # split the raveled sel/in indices back (keep the R singletons for the
    # C-order relayout), then expand the rest block
    x = out3.reshape((N,) * k + (R,) + (N,) * k + (R,))
    rest_sizes = tuple(Ns[a] for a in rest)
    shape = (N,) * k + rest_sizes + (N,) * k + rest_sizes
    t4 = np.transpose(x.reshape(shape), np.argsort(order))
    return t4.reshape(d, d)
