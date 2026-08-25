"""F-COMPILE: compiled vs naive execution identity (ADR-0002, PRD fixtures 1-3)."""

import numpy as np
import pytest

from cvsim.gaussian import GaussianCircuit, ParamRef
from cvsim.gaussian.channels import apply_gaussian_channel, loss, phase_noise
from cvsim.gaussian.compile import (
    _compile_segments,
    _instantiate,
    _run_op,
)
from cvsim.gaussian.gates import (
    apply_symplectic,
    beamsplitter,
    cx,
    cz,
    displace,
    fourier,
    mach_zehnder,
    phase,
    squeeze,
    two_mode_squeeze,
)
from cvsim.gaussian.observables import (
    heterodyne_sample_and_condition,
    homodyne_sample_and_condition,
)
from cvsim.gaussian.state import GaussianState

# -- naive reference executor (independent of the compile path) -----------


def _naive_apply(op_name, st, modes, **kwargs):
    """Independent per-op application using gate/channel functions."""
    if op_name == "squeeze":
        return squeeze(st, kwargs["r"], modes[0])
    if op_name == "displace":
        return displace(st, kwargs["alpha"], modes[0])
    if op_name == "phase":
        return phase(st, kwargs["theta"], modes[0])
    if op_name == "fourier":
        return fourier(st, modes[0])
    if op_name == "beamsplitter":
        return beamsplitter(st, modes[0], modes[1], kwargs["theta"], kwargs.get("phi", 0.0))
    if op_name == "mach_zehnder":
        return mach_zehnder(st, modes[0], modes[1], kwargs["theta"], kwargs.get("phi", 0.0))
    if op_name == "two_mode_squeeze":
        return two_mode_squeeze(st, kwargs["r"], modes[0], modes[1])
    if op_name == "cz":
        return cz(st, kwargs["weight"], modes[0], modes[1])
    if op_name == "cx":
        return cx(st, kwargs["weight"], modes[0], modes[1])
    if op_name == "interferometer":
        return apply_symplectic(st, _naive_interferometer_s(st.nmode, kwargs["U"]), validate=False)
    if op_name == "loss":
        return loss(st, kwargs["T"], modes[0], kwargs.get("nbar", 0.0))
    if op_name == "phase_noise":
        return phase_noise(st, kwargs["sigma"], modes[0] if modes else None)
    if op_name == "amplifier":
        from cvsim.gaussian.channels import amplifier

        return amplifier(st, kwargs["G"], modes[0] if modes else None, kwargs.get("nbar", 0.0))
    raise ValueError(f"naive: unknown op {op_name!r}")


def _naive_interferometer_s(nmode, U):
    from cvsim.symplectic import S_from_unitary

    return S_from_unitary(U, validate=False)


def naive_run(circ, *, rng=None, **params):
    """Op-by-op executor mirroring the pre-compile interpreter semantics."""
    st = GaussianState.vacuum(circ.nmode)
    mapping = list(range(circ.nmode))
    results = {}
    for op_name, modes, fixed, pnames, refs in circ._ops:
        kwargs = dict(fixed)
        for k, v in pnames.items():
            if v not in params:
                raise ValueError(f"Missing parameter '{v}' for {op_name}")
            kwargs[k] = params[v]
        if op_name == "measure_homodyne":
            phys = mapping[modes[0]]
            val, st = homodyne_sample_and_condition(st, phys, kwargs["phi"], rng=rng)
            results[kwargs["name"]] = val
            st = st.remove_mode(phys)
            for i in range(len(mapping)):
                if mapping[i] > phys:
                    mapping[i] -= 1
            mapping[modes[0]] = -1
        elif op_name == "measure_heterodyne":
            phys = mapping[modes[0]]
            val, st = heterodyne_sample_and_condition(st, phys, rng=rng)
            results[kwargs["name"]] = val
            for i in range(len(mapping)):
                if mapping[i] > phys:
                    mapping[i] -= 1
            mapping[modes[0]] = -1
        elif op_name == "gaussian_channel":
            if kwargs["X"].shape[0] != 2 * st.nmode:
                raise ValueError("naive: X size mismatch")
            st = apply_gaussian_channel(
                st,
                kwargs["X"],
                kwargs["Y"],
                kwargs.get("d"),
                validate=kwargs.get("validate", True),
            )
        else:
            if modes:
                phys = tuple(mapping[m] for m in modes)
                assert all(p >= 0 for p in phys)
            else:
                phys = ()
            for k, v in refs.items():
                if v.source not in results:
                    raise ValueError(f"ParamRef '{k}' references '{v.source}'")
                kwargs[k] = complex(results[v.source] * v.gain)
            st = _naive_apply(op_name, st, phys, **kwargs)
    return st, results


def _assert_states_close(a, b, atol=1e-9):
    np.testing.assert_allclose(a.V, b.V, atol=atol, rtol=0.0)
    np.testing.assert_allclose(a.rbar, b.rbar, atol=atol, rtol=0.0)


# -- fixture 1: vision exit metric, random depth-100 passive, m=32 ---------


def test_compile_random_passive_m32_depth100():
    rng = np.random.default_rng(20260806)
    c = GaussianCircuit(32)
    for _ in range(100):
        kind = rng.integers(0, 3)
        if kind == 0:
            i, j = rng.choice(32, 2, replace=False)
            c.beamsplitter(int(i), int(j), float(rng.uniform(0, np.pi)))
        elif kind == 1:
            c.phase(int(rng.integers(0, 32)), float(rng.uniform(0, 2 * np.pi)))
        else:
            c.fourier(int(rng.integers(0, 32)))
    compiled = c.compile()
    st_c, _ = naive_run(c)
    st_p = compiled.run()
    assert compiled.params == frozenset()
    _assert_states_close(st_p, st_c, atol=1e-9)


# -- fixture 2: mixed segments, per-segment intermediate states ------------


def test_compile_mixed_segments_intermediate_states():
    eta = 0.8
    X = np.sqrt(eta) * np.eye(4)
    Y = (1 - eta) / 2 * np.eye(4)
    c = GaussianCircuit(3)
    c.squeeze(0, r=0.4)
    c.beamsplitter(0, 1, theta=0.6, phi=0.2)
    c.loss(1, T=0.8)
    c.squeeze(2, r=-0.3)
    c.measure_homodyne(2, phi=0.0, name="m_x")
    c.displace(0, alpha=ParamRef("m_x", gain=0.3))
    c.cz(0, 1, weight=0.7)
    c.gaussian_channel(X, Y)
    c.phase(0, theta=1.1)

    segs, params = _compile_segments(c._ops, c.nmode)
    assert params == frozenset()
    # merged / op alternation with the expected break points
    kinds = [s[0] for s in segs]
    assert kinds[0] == "merged" and len(segs[0][2]) == 2  # sq+bs
    assert segs[1][0] == "op" and segs[1][1][0] == "loss"  # loss
    assert segs[2][0] == "merged" and len(segs[2][2]) == 1  # squeeze(2)
    assert segs[3][0] == "op" and segs[3][1][0] == "measure_homodyne"
    assert segs[4][0] == "op" and segs[4][1][0] == "displace"  # ParamRef
    assert segs[5][0] == "merged" and len(segs[5][2]) == 1  # cz
    assert segs[6][0] == "op" and segs[6][1][0] == "gaussian_channel"
    assert segs[7][0] == "merged" and len(segs[7][2]) == 1  # phase
    assert segs[7][2][0][1] == (0,)  # mode 0 untouched

    # drive compiled segments step-by-step vs naive op-by-op, same rng
    rng_c = np.random.default_rng(123)
    rng_n = np.random.default_rng(123)
    st_c = GaussianState.vacuum(3)
    st_n = GaussianState.vacuum(3)
    n_naive_mapping = list(range(3))
    results_c: dict = {}
    results_n: dict = {}
    naive_ops = iter(c._ops)
    n_naive = 0
    for seg in segs:
        if seg[0] == "merged":
            _, nmode, ops = seg
            S, d = _instantiate(ops, nmode, {})
            st_c = apply_symplectic(st_c, S, d, validate=False)
        else:
            st_c, results_c = _run_op(seg[1], st_c, results_c, {}, rng=rng_c)
        # naive catches up: run until the same op count as compiled side
        target = n_naive + (len(seg[2]) if seg[0] == "merged" else 1)
        while n_naive < target:
            op = next(naive_ops)
            op_name, modes, fixed, pnames, refs = op
            kwargs = dict(fixed)
            if op_name == "measure_homodyne":
                phys = n_naive_mapping[modes[0]]
                val, st_n = homodyne_sample_and_condition(st_n, phys, kwargs["phi"], rng=rng_n)
                results_n[kwargs["name"]] = val
                st_n = st_n.remove_mode(phys)
                _shift(n_naive_mapping, phys)
                n_naive_mapping[modes[0]] = -1
            elif op_name == "measure_heterodyne":
                phys = n_naive_mapping[modes[0]]
                val, st_n = heterodyne_sample_and_condition(st_n, phys, rng=rng_n)
                results_n[kwargs["name"]] = val
                _shift(n_naive_mapping, phys)
                n_naive_mapping[modes[0]] = -1
            elif op_name == "gaussian_channel":
                st_n = apply_gaussian_channel(
                    st_n,
                    kwargs["X"],
                    kwargs["Y"],
                    kwargs.get("d"),
                    validate=kwargs.get("validate", True),
                )
            else:
                phys = tuple(n_naive_mapping[m] for m in modes) if modes else ()
                for k, v in refs.items():
                    kwargs[k] = complex(results_n[v.source] * v.gain)
                st_n = _naive_apply(op_name, st_n, phys, **kwargs)
            n_naive += 1
        _assert_states_close(st_c, st_n, atol=1e-9)
        assert results_c == results_n


def _shift(mapping, phys):
    for i in range(len(mapping)):
        if mapping[i] > phys:
            mapping[i] -= 1


def test_compile_mixed_segments_full_run_matches_naive():
    eta = 0.8
    X = np.sqrt(eta) * np.eye(4)
    Y = (1 - eta) / 2 * np.eye(4)
    c = GaussianCircuit(3)
    c.squeeze(0, r=0.4)
    c.beamsplitter(0, 1, theta=0.6)
    c.loss(1, T=0.8)
    c.measure_homodyne(1, phi=np.pi / 2, name="m_p")
    c.displace(0, alpha=ParamRef("m_p", gain=0.3))
    c.cx(0, 2, weight=0.5)
    c.gaussian_channel(X, Y)
    c.phase(0, theta=0.9)
    rng_c = np.random.default_rng(42)
    rng_n = np.random.default_rng(42)
    st_c, res_c = c.run(rng=rng_c)
    st_n, res_n = naive_run(c, rng=rng_n)
    assert res_c == res_n
    _assert_states_close(st_c, st_n, atol=1e-9)


# -- fixture 3: parameterized segment, same structure two runs -------------


def test_compile_parameterized_segment_reused():
    c = GaussianCircuit(4)
    c.squeeze(0, r="r0")
    c.beamsplitter(0, 1, theta=0.5)
    c.two_mode_squeeze(2, 3, r="r23")
    c.phase(1, theta="theta1")
    c.cz(2, 3, weight=0.8)
    compiled = c.compile()
    assert compiled.params == frozenset({"r0", "r23", "theta1"})
    for r0, r23, theta1 in [(0.4, 0.1, 0.7), (1.2, -0.5, 2.1)]:
        st_p = compiled.run(r0=r0, r23=r23, theta1=theta1)
        st_n, _ = naive_run(c, r0=r0, r23=r23, theta1=theta1)
        _assert_states_close(st_p, st_n, atol=1e-9)


def test_compile_parameterized_missing_param_raises():
    c = GaussianCircuit(2)
    c.squeeze(0, r="r0")
    compiled = c.compile()
    with pytest.raises(ValueError, match="Missing parameter 'r0'"):
        compiled.run()


def test_compile_displace_merge_order_phase_then_displace():
    """[phase, displace] merged: displacement must NOT be rotated by phase."""
    c = GaussianCircuit(2)
    c.phase(0, theta=0.3)
    c.displace(0, alpha=0.5 + 0.2j)
    c.beamsplitter(0, 1, theta=0.4)
    segs, _ = _compile_segments(c._ops, c.nmode)
    assert segs[0][0] == "merged" and len(segs[0][2]) == 3
    st_p = c.run()
    st_n, _ = naive_run(c)
    _assert_states_close(st_p, st_n, atol=1e-12)


def test_compile_displace_merge_order_displace_then_phase():
    """[displace, phase] merged: displacement must be rotated by later phase."""
    c = GaussianCircuit(2)
    c.displace(0, alpha=0.5 + 0.2j)
    c.phase(0, theta=0.3)
    segs, _ = _compile_segments(c._ops, c.nmode)
    assert segs[0][0] == "merged" and len(segs[0][2]) == 2
    st_p = c.run()
    st_n, _ = naive_run(c)
    _assert_states_close(st_p, st_n, atol=1e-12)


def test_compile_interferometer_copies_input_array():
    """Mutating U after build must not change the circuit (snapshot semantics)."""
    U = np.eye(2, dtype=complex)
    c = GaussianCircuit(2)
    c.interferometer(U)
    U[0, 1] = 0.5j  # mutate caller's array
    st_p = c.run()
    c2 = GaussianCircuit(2)
    c2.interferometer(np.eye(2, dtype=complex))
    st_ref = c2.run()
    _assert_states_close(st_p, st_ref, atol=1e-12)


def test_compile_interferometer_segment():
    c = GaussianCircuit(4)
    c.beamsplitter(0, 1, theta=0.3)
    U = np.eye(4, dtype=complex)
    U[2, 3] = 1
    U[3, 2] = 1
    U[2, 2] = U[3, 3] = 0
    c.interferometer(U)
    st_p = c.run()
    st_n, _ = naive_run(c)
    _assert_states_close(st_p, st_n, atol=1e-12)


def test_compile_interferometer_rejects_nonunitary():
    """Compiled path must keep gates.interferometer's unitary validation."""
    c = GaussianCircuit(2)
    c.interferometer(np.array([[1.0, 0.5], [0.0, 1.0]], dtype=complex))
    with pytest.raises(ValueError, match="unitary"):
        c.run()


# -- semantics --------------------------------------------------------------


def test_compile_empty_circuit_returns_vacuum():
    c = GaussianCircuit(2)
    compiled = c.compile()
    assert compiled.nmode == 2
    assert compiled.params == frozenset()
    st = compiled.run()
    np.testing.assert_allclose(st.V, np.eye(4) / 2)
    np.testing.assert_allclose(st.rbar, np.zeros(4))


def test_compile_run_type_with_and_without_measurement():
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.3)
    st = c.compile().run()
    assert isinstance(st, GaussianState)

    c2 = GaussianCircuit(2)
    c2.squeeze(1, r=0.3)
    c2.measure_homodyne(1, phi=0.0, name="m")
    out = c2.compile().run(rng=np.random.default_rng(1))
    assert isinstance(out, tuple) and isinstance(out[0], GaussianState)
    assert "m" in out[1]


def test_compile_paramref_unmeasured_source_raises():
    c = GaussianCircuit(2)
    c.displace(0, alpha=ParamRef("nope", gain=1.0))
    with pytest.raises(ValueError, match="'nope' which has not been measured"):
        c.compile().run()


def test_compile_repr_smoke():
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.3)
    c.loss(0, T=0.9)
    r = repr(c.compile())
    assert "merged" in r and "loss" in r


def test_compile_heterodyne_matches_naive():
    c = GaussianCircuit(2)
    c.squeeze(1, r=0.5)
    c.measure_heterodyne(1, name="h")
    c.displace(0, alpha=ParamRef("h", gain=0.2))
    rng_c = np.random.default_rng(9)
    rng_n = np.random.default_rng(9)
    st_c, res_c = c.run(rng=rng_c)
    st_n, res_n = naive_run(c, rng=rng_n)
    assert res_c == res_n
    _assert_states_close(st_c, st_n, atol=1e-9)
