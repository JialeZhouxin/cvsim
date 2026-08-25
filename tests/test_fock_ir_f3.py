"""F3 IR: FockCircuit to_ir/from_ir round-trip on circuit_v1 (ADR-0003)."""

from __future__ import annotations

import json

import numpy as np
import pytest

from cvsim.circuit_common import ParamRef
from cvsim.fock.circuit import FockCircuit
from cvsim.fock.ir import OP_META, validate_ir


def _json_dumpable(doc: dict) -> None:
    json.dumps(doc)  # must not raise (complex/ndarray encoded)


def test_roundtrip_full_circuit() -> None:
    c = FockCircuit(2, cutoff=6)
    c.squeeze(0, r=0.3)
    c.displace(1, alpha=0.2 - 0.1j)
    c.kerr(0, chi=0.05)
    c.beamsplitter(0, 1, theta=0.5, phi=0.2)
    c.two_mode_squeeze(0, 1, r=0.15)
    c.loss(1, eta=0.7)
    c.amplifier(0, G=1.2, nbar=0.0)  # nbar>0: F3 honest NotImpl
    c.phase_noise(1, sigma=0.05)
    c.cz(0, 1, weight=0.4)
    c.cx(1, 0, weight=0.3)
    c.mach_zehnder(0, 1, theta=0.6, phi=0.1)
    doc = c.to_ir()
    _json_dumpable(doc)
    c2 = FockCircuit.from_ir(doc)
    assert c2.nmode == 2
    assert list(c2.cutoffs) == [6, 6]
    assert len(c2._ops) == len(c._ops)
    for (a, b) in zip(c._ops, c2._ops, strict=False):
        assert a[0] == b[0] and a[1] == b[1]
        assert a[3] == b[3]  # symbolic params
        assert a[4] == b[4]  # refs
    # physics parity after re-build
    st1 = c.run(rng=np.random.default_rng(7))
    st2 = c2.run(rng=np.random.default_rng(7))
    np.testing.assert_allclose(st1.rho, st2.rho, atol=1e-14)


def test_roundtrip_per_mode_cutoff_and_paramref() -> None:
    c = FockCircuit(3, cutoff=[5, 7, 6])
    c.measure_pnr(0, name="n0")
    c.displace(1, alpha=ParamRef("n0", gain=0.1))
    doc = c.to_ir()
    _json_dumpable(doc)
    assert doc["cutoff"] == [5, 7, 6]
    c2 = FockCircuit.from_ir(doc)
    assert list(c2.cutoffs) == [5, 7, 6]
    c3 = FockCircuit.from_ir(c2.to_ir())
    assert list(c3.cutoffs) == [5, 7, 6]
    # ParamRef survives
    disp = c3._ops[-1]
    assert disp[0] == "displace"
    ref = disp[4]["alpha"]
    assert isinstance(ref, ParamRef) and ref.source == "n0"
    np.testing.assert_allclose(ref.gain, 0.1)


def test_roundtrip_interferometer_and_apply_unitary() -> None:
    rng = np.random.default_rng(0)
    U = rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3))
    U, _ = np.linalg.qr(U)
    c = FockCircuit(3, cutoff=4)
    c.interferometer(U)
    c2 = FockCircuit.from_ir(c.to_ir())
    np.testing.assert_allclose(c2._ops[0][2]["U"], U, atol=1e-12)
    # apply_unitary (k-local on 2 of 3 modes)
    W = rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4))
    W, _ = np.linalg.qr(W)
    c.apply_unitary(W, modes=[1, 2])
    c3 = FockCircuit.from_ir(c.to_ir())
    np.testing.assert_allclose(c3._ops[1][2]["U"], W, atol=1e-12)
    assert c3._ops[1][1] == (1, 2)


def test_roundtrip_kraus_ops() -> None:
    K = [
        np.array([[0.8, 0.0], [0.0, 0.6]], dtype=complex),
        np.array([[0.0, 0.6], [0.0, 0.0]], dtype=complex),
    ]
    c = FockCircuit(1, cutoff=4)
    c.apply_kraus(0, K)
    c2 = FockCircuit.from_ir(c.to_ir())
    ops = c2._ops[0][2]["kraus_ops"]
    assert len(ops) == 2
    np.testing.assert_allclose(ops[0], K[0], atol=1e-12)
    np.testing.assert_allclose(ops[1], K[1], atol=1e-12)


def test_roundtrip_measurements() -> None:
    c = FockCircuit(2, cutoff=6)
    c.measure_pnr(0, name="a")
    c.measure_homodyne(1, phi=0.3, name="x")
    c.measure_heterodyne(0, name="b")
    c2 = FockCircuit.from_ir(c.to_ir())
    names = [(o[0], o[2]) for o in c2._ops]
    assert names == [
        ("measure_pnr", {"name": "a"}),
        ("measure_homodyne", {"phi": 0.3, "name": "x"}),
        ("measure_heterodyne", {"name": "b"}),
    ]


def test_validate_rejects_bad_docs() -> None:
    with pytest.raises(ValueError):
        validate_ir({"schema": "circuit_v2", "nmode": 1, "ops": []})
    with pytest.raises(ValueError):
        validate_ir({"schema": "circuit_v1", "nmode": 1, "ops": [], "bogus": 1})
    with pytest.raises(ValueError):
        validate_ir({"schema": "circuit_v1", "nmode": 2, "cutoff": [3], "ops": []})
    with pytest.raises(ValueError):
        validate_ir(
            {"schema": "circuit_v1", "nmode": 1, "ops": [{"op": "kerr", "params": {"nope": 1}}]}
        )
    with pytest.raises(ValueError):
        validate_ir(
            {"schema": "circuit_v1", "nmode": 1, "ops": [{"op": "beamsplitter", "modes": [0]}]}
        )


def test_gaussian_side_ignores_cutoff() -> None:
    """cutoff is an allowed extension — gaussian from_ir must not choke on it."""
    from cvsim.gaussian.ir import from_ir as g_from_ir

    doc = {
        "schema": "circuit_v1",
        "nmode": 1,
        "cutoff": 6,
        "ops": [{"op": "squeeze", "modes": [0], "params": {"r": 0.3}}],
    }
    cir = g_from_ir(doc)
    assert cir.nmode == 1


def test_op_meta_covers_all_circuit_ops() -> None:
    c = FockCircuit(2, cutoff=6)
    for name in (
        "squeeze", "displace", "phase", "kerr", "beamsplitter",
        "two_mode_squeeze", "cz", "cx", "mach_zehnder", "interferometer",
        "apply_unitary", "loss", "amplifier", "phase_noise", "apply_kraus",
        "measure_pnr", "measure_homodyne", "measure_heterodyne",
    ):
        assert name in OP_META, name
