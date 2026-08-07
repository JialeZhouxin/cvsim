"""circuit_v1 IR: schema validation + to_ir/from_ir round-trip (ADR-0003)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from cvsim.gaussian import GaussianCircuit, ParamRef
from cvsim.gaussian.ir import OP_META, SCHEMA, from_ir, to_ir, validate_ir

ALL_OPS = {
    "squeeze", "displace", "phase", "fourier",
    "beamsplitter", "two_mode_squeeze", "cz", "cx",
    "mach_zehnder", "mz", "interferometer",
    "loss", "amplifier", "phase_noise", "gaussian_channel",
    "measure_homodyne", "measure_heterodyne",
}


def _u4() -> np.ndarray:
    """4×4 unitary (block-diagonal 2×2 beamsplitter matrices)."""
    c, s = np.cos(0.5), np.sin(0.5)
    b = np.array([[c, -s], [s, c]], dtype=complex)
    return np.kron(np.eye(2, dtype=complex), b)


def _big_circuit() -> GaussianCircuit:
    c = GaussianCircuit(4)
    c.squeeze(0, r=0.5, phi=0.3)
    c.displace(1, alpha=0.7 - 0.2j)
    c.phase(2, theta=0.4)
    c.fourier(0)
    c.beamsplitter(0, 1, theta=0.6, phi=0.1)
    c.two_mode_squeeze(2, 3, r=0.8)
    c.cz(0, 2, weight=0.5)
    c.cx(1, 3, weight=-0.3)
    c.mach_zehnder(0, 1, theta=0.7, phi=0.2)
    c.interferometer(_u4())
    c.loss(3, T=0.7, nbar=0.1)
    c.amplifier(0, G=1.5, nbar=0.2)
    c.phase_noise(1, sigma=0.05)
    m = 4
    c.gaussian_channel(
        np.eye(2 * m), np.zeros((2 * m, 2 * m)), np.zeros(2 * m)
    )
    return c


def _assert_same_state(a, b, atol: float = 1e-12) -> None:
    np.testing.assert_allclose(a.V, b.V, atol=atol)
    np.testing.assert_allclose(a.rbar, b.rbar, atol=atol)


# --- OP_META completeness -----------------------------------------------------

def test_op_meta_covers_all_builders():
    assert set(OP_META) == ALL_OPS
    assert SCHEMA == "circuit_v1"


# --- round-trip --------------------------------------------------------------

def test_roundtrip_all_ops():
    c = _big_circuit()
    c2 = from_ir(to_ir(c))
    assert len(c2) == len(c)
    _assert_same_state(c.run(), c2.run())


def test_roundtrip_is_json_native():
    """to_ir output survives json.dumps (complex → [re,im], U → pairs)."""
    c = _big_circuit()
    d = to_ir(c)
    text = json.dumps(d)
    d2 = json.loads(text)
    _assert_same_state(c.run(), from_ir(d2).run())


def test_roundtrip_symbolic_params_and_paramref():
    c = GaussianCircuit(2)
    c.squeeze(0, r="r1", phi="phi1")
    c.beamsplitter(0, 1, theta="th")
    c.measure_homodyne(1, phi=0.0, name="m_x")
    c.displace(0, alpha=ParamRef("m_x", gain=0.5))
    c2 = from_ir(to_ir(c))
    kwargs = {"r1": 0.5, "phi1": 0.2, "th": 0.8}
    st1, res1 = c.run(rng=np.random.default_rng(42), **kwargs)
    st2, res2 = c2.run(rng=np.random.default_rng(42), **kwargs)
    _assert_same_state(st1, st2)
    assert res1 == res2


def test_to_ir_structure():
    c = GaussianCircuit(2)
    c.squeeze(0, r="r")
    c.displace(1, alpha=1.5 + 0.5j)
    c.measure_homodyne(0, phi=0.3, name="m")
    d = to_ir(c)
    assert d == {
        "schema": "circuit_v1",
        "nmode": 2,
        "ops": [
            {"op": "squeeze", "modes": [0], "params": {"r": {"$param": "r"}, "phi": 0.0}},
            {"op": "displace", "modes": [1], "params": {"alpha": [1.5, 0.5]}},
            {"op": "measure_homodyne", "modes": [0], "params": {"phi": 0.3, "name": "m"}},
        ],
    }


def test_roundtrip_default_omission():
    """Omitted params = library defaults (golden default table)."""
    data = {
        "schema": "circuit_v1",
        "nmode": 2,
        "ops": [
            {"op": "loss", "modes": [0], "params": {"T": 0.5}},
            {"op": "beamsplitter", "modes": [0, 1], "params": {}},
            {"op": "amplifier", "modes": [], "params": {"G": 2.0}},
            {"op": "measure_homodyne", "modes": [1], "params": {"name": "m"}},
        ],
    }
    c = from_ir(data)
    ref = GaussianCircuit(2)
    ref.loss(0, T=0.5)
    ref.beamsplitter(0, 1)
    ref.amplifier(None, G=2.0)
    ref.measure_homodyne(1, 0.0, "m")
    _assert_same_state(
        c.run(rng=np.random.default_rng(1))[0],
        ref.run(rng=np.random.default_rng(1))[0],
    )


def test_mz_expands_to_bs_phase_bs():
    data = {
        "schema": "circuit_v1",
        "nmode": 2,
        "ops": [
            {"op": "squeeze", "modes": [0], "params": {"r": 0.5}},
            {"op": "mz", "modes": [0, 1], "params": {"theta": 0.6, "phi": 1.1}},
        ],
    }
    c = from_ir(data)
    assert len(c) == 4  # squeeze + bs + phase + bs expansion
    ref = GaussianCircuit(2)
    ref.squeeze(0, r=0.5)
    ref.beamsplitter(0, 1, theta=0.6, phi=0.0)
    ref.phase(0, theta=1.1)
    ref.beamsplitter(0, 1, theta=0.6, phi=0.0)
    _assert_same_state(c.run(), ref.run())


def test_ids_optional_and_unique():
    data = {
        "schema": "circuit_v1",
        "nmode": 1,
        "ops": [
            {"id": "a", "op": "squeeze", "modes": [0], "params": {"r": 0.5}},
            {"id": "b", "op": "phase", "modes": [0], "params": {"theta": 0.1}},
        ],
    }
    doc = validate_ir(data)
    assert [n.id for n in doc.ops] == ["a", "b"]
    data["ops"][1]["id"] = "a"
    with pytest.raises(ValueError, match="duplicate id 'a'"):
        validate_ir(data)


def test_extension_fields_accepted_and_ignored():
    data = {
        "schema": "circuit_v1",
        "nmode": 1,
        "seed": 7,
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
        "ui": {"anything": [1, 2]},
        "ops": [{"op": "squeeze", "modes": [0], "params": {"r": 0.5}}],
    }
    doc = validate_ir(data)
    assert doc.nmode == 1
    c = from_ir(data)
    ref = GaussianCircuit(1)
    ref.squeeze(0, r=0.5)
    _assert_same_state(c.run(), ref.run())


def test_unknown_top_level_field_rejected():
    data = {
        "schema": "circuit_v1",
        "nmode": 1,
        "ops": [{"op": "squeeze", "modes": [0], "params": {"r": 0.5}}],
        "edges": [],
    }
    with pytest.raises(ValueError, match=r"unknown top-level field 'edges'"):
        validate_ir(data)


# --- validation matrix ---------------------------------------------------------

def _doc(ops, **top):
    return {"schema": "circuit_v1", "nmode": 2, "ops": ops, **top}


@pytest.mark.parametrize("data,msg", [
    ({"schema": "circuit_v0", "nmode": 1, "ops": []}, "unsupported schema"),
    (_doc([], nmode=0), "nmode must be an int >= 1"),
    (_doc([], nmode=True), "nmode must be an int >= 1"),
    (_doc([], nmode=1.5), "nmode must be an int >= 1"),
    (_doc([], nmode=True), "nmode must be an int >= 1"),
])
def test_top_level_validation(data, msg):
    with pytest.raises(ValueError, match=msg):
        validate_ir(data)


def test_empty_circuit_roundtrip():
    """Empty ops list is a legitimate circuit (vacuum) — to_ir/from_ir must
    round-trip (OCR review medium: empty circuit was rejected on the way back)."""
    c = GaussianCircuit(3)
    doc = to_ir(c)
    assert doc["ops"] == []
    c2 = from_ir(doc)
    assert c2.nmode == 3
    s1, s2 = c.run(), c2.run()
    assert np.allclose(s1.V, s2.V, atol=1e-12)
    assert np.allclose(s1.rbar, s2.rbar, atol=1e-12)


def test_modes_out_of_range_rejected():
    """modes >= nmode fails at the trust boundary (OCR review medium)."""
    with pytest.raises(ValueError, match="out of range"):
        validate_ir(_doc([{"op": "displace", "modes": [5], "params": {"alpha": 1.0}}], nmode=2))


@pytest.mark.parametrize("op,modes,msg", [
    ("squeeze", [0, 1], "requires exactly 1 mode"),
    ("beamsplitter", [0], "requires exactly 2 modes"),
    ("amplifier", [0, 1], "at most 1 mode"),
    ("gaussian_channel", [0], "takes no modes"),
    ("squeeze", [-1], "non-negative int"),
    ("squeeze", [True], "non-negative int"),
])
def test_bad_modes(op, modes, msg):
    data = _doc([{"op": op, "modes": modes, "params": {}}])
    with pytest.raises(ValueError, match=msg):
        validate_ir(data)


def test_interferometer_modes_must_be_all_modes():
    data = {
        "schema": "circuit_v1",
        "nmode": 3,
        "ops": [{"op": "interferometer", "modes": [0, 1], "params": {"U": [[1, 0], [0, 1]]}}],
    }
    with pytest.raises(ValueError, match="requires modes == list\\(range\\(nmode\\)\\)"):
        validate_ir(data)


def test_interferometer_accepts_all_modes():
    n = 2
    data = {
        "schema": "circuit_v1",
        "nmode": n,
        "ops": [{"op": "interferometer", "modes": [0, 1],
                 "params": {"U": [[1, 0], [0, 1]]}}],
    }
    assert validate_ir(data).ops[0].op == "interferometer"


def test_unknown_op():
    data = _doc([{"op": "teleport", "modes": [0], "params": {}}])
    with pytest.raises(ValueError, match=r"unknown op 'teleport'"):
        validate_ir(data)


def test_unknown_param_name():
    data = _doc([{"op": "squeeze", "modes": [0], "params": {"r": 0.5, "g": 1.0}}])
    with pytest.raises(ValueError, match=r"unknown param 'g' for op 'squeeze'"):
        validate_ir(data)


@pytest.mark.parametrize("op,params,msg", [
    ("squeeze", {"r": "0.5"}, "must be a number"),
    ("squeeze", {"r": True}, "must be a number"),
    ("displace", {"alpha": [1, 2, 3]}, "must be a number or \\[re, im\\]"),
    ("displace", {"alpha": "abc"}, "must be a number or \\[re, im\\]"),
    ("displace", {"alpha": {"$param": ""}}, "\\$param must be a non-empty string"),
    ("squeeze", {"r": {"$ref": ""}}, "\\$ref source must be a non-empty string"),
    ("squeeze", {"r": {"$ref": "m", "gain": "x"}}, "\\$ref gain must be a number"),
    ("squeeze", {"r": {"$param": "x", "extra": 1}}, "\\$param must be the only key"),
    ("measure_heterodyne", {"name": {"$param": "x"}}, "\\$param not allowed"),
])
def test_bad_param_kinds(op, params, msg):
    data = _doc([{"op": op, "modes": [0], "params": params}])
    with pytest.raises(ValueError, match=msg):
        validate_ir(data)


def test_matrix_kind_validation():
    def doc(u):
        return _doc([{"op": "interferometer", "modes": [0, 1], "params": {"U": u}}])

    for u, msg in [
        ([], "non-empty array"),
        ([1, [2, 3]], "non-empty lists"),
        ([[1, 2], [3]], "ragged array"),
        ([[1, "x"], [3, 4]], "numbers or \\[re, im\\]"),
        ([[[1, 2], [3, 4]], [[5, 6]]], "ragged array"),
        ([[1, 2], [[3, 4], [5, 6]]], "mixed real/complex"),
    ]:
        with pytest.raises(ValueError, match=msg):
            validate_ir(doc(u))


def test_complex_matrix_roundtrip():
    """U with complex entries encodes as nested [re, im] pairs."""
    c = GaussianCircuit(2)
    c.interferometer(np.array([[1j, 0], [0, 1j]]))
    c2 = from_ir(json.loads(json.dumps(to_ir(c))))
    _assert_same_state(c.run(), c2.run())


def test_required_params_missing():
    data = _doc([{"op": "measure_heterodyne", "modes": [0], "params": {}}])
    with pytest.raises(ValueError, match=r"requires param 'name' \(no default\)"):
        validate_ir(data)
    data = _doc([{"op": "interferometer", "modes": [0, 1], "params": {}}])
    with pytest.raises(ValueError, match=r"requires param 'U' \(no default\)"):
        validate_ir(data)


def test_bad_id():
    data = _doc([{"id": 5, "op": "squeeze", "modes": [0], "params": {}}])
    with pytest.raises(ValueError, match="id must be a non-empty string"):
        validate_ir(data)


def test_squeeze_phi_symbolic_compile_roundtrip():
    """squeeze phi symbolic: compile path honours phi (compile.py fix)."""
    c = GaussianCircuit(1)
    c.squeeze(0, r="r", phi="ph")
    c2 = from_ir(to_ir(c))
    _assert_same_state(c.run(r=0.5, ph=0.4), c2.run(r=0.5, ph=0.4))


def test_amplifier_and_phase_noise_all_modes_roundtrip():
    c = GaussianCircuit(3)
    c.amplifier(None, G=1.5)
    c.phase_noise(None, sigma=0.1)
    d = to_ir(c)
    assert d["ops"][0]["modes"] == []
    assert d["ops"][1]["modes"] == []
    _assert_same_state(c.run(), from_ir(d).run())
