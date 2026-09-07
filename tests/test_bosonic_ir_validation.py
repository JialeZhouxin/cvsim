"""Bosonic circuit_v1 IR validation + encode/decode coverage (2026-09-07).

Companion to ``tests/test_b5_bosonic_circuit.py`` (DSL) — this file covers
``cvsim/bosonic/ir.py`` validation paths: ``validate_ir`` structural errors,
``_check_value``/``_check_matrix`` illegal-value catalogue, and the
encode/decode FUNC branches ($param/$ref/complex-scalar/matrix).

Gaussian IR has a dedicated ``test_ir.py``; Bosonic gets its own here
(B5 exit 3: same circuit_v1 schema).
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import BosonicCircuit
from cvsim.bosonic.ir import from_ir, ir_schema, to_ir, validate_ir
from cvsim.circuit_common import ParamRef

SCHEMA = "circuit_v1"


def _valid(op: dict) -> dict:
    """Base valid document for surgery-in-place tests."""
    return {"schema": SCHEMA, "nmode": 1, "ops": [op]}


# ===========================================================================
# validate_ir — structural catalogue (parametrized)
# ===========================================================================


class TestValidateIrStructural:
    @pytest.mark.parametrize(
        "data",
        [
            pytest.param("not a dict", id="payload-not-dict"),
            pytest.param({"schema": "v0", "nmode": 1, "ops": []}, id="bad-schema"),
            pytest.param({"schema": SCHEMA, "nmode": 0, "ops": []}, id="nmode-zero"),
            pytest.param({"schema": SCHEMA, "nmode": True, "ops": []}, id="nmode-bool"),
            pytest.param({"schema": SCHEMA, "nmode": 1, "ops": [], "bogus": 1}, id="unknown-field"),
            pytest.param(
                {"schema": SCHEMA, "nmode": 1, "ops": [], "view": "x"}, id="view-not-dict"
            ),
            pytest.param({"schema": SCHEMA, "nmode": 1, "ops": [], "seed": -1}, id="seed-negative"),
            pytest.param({"schema": SCHEMA, "nmode": 1, "ops": [], "seed": True}, id="seed-bool"),
            pytest.param({"schema": SCHEMA, "nmode": 1, "ops": [], "ui": "x"}, id="ui-not-dict"),
            pytest.param(
                {"schema": SCHEMA, "nmode": 1, "ops": [], "detail": "full"}, id="detail-bad"
            ),
            pytest.param({"schema": SCHEMA, "nmode": 1, "ops": "x"}, id="ops-not-list"),
        ],
        ids=lambda params: params[0] if isinstance(params, list) else "",
    )
    def test_structural_raises(self, data: dict) -> None:
        with pytest.raises(ValueError):
            validate_ir(data)

    def test_detail_steps_accepted(self) -> None:
        """detail='steps' is legal (extension field)."""
        doc = validate_ir({"schema": SCHEMA, "nmode": 1, "ops": [], "detail": "steps"})
        assert len(doc.ops) == 0

    def test_extension_fields_accepted(self) -> None:
        """view/seed/ui/cutoff/backend/initial are legal extension fields."""
        doc = validate_ir(
            {
                "schema": SCHEMA,
                "nmode": 1,
                "ops": [],
                "view": {"lim": 5.0},
                "seed": 0,
                "ui": {"staff": []},
                "cutoff": 30,
                "backend": "bosonic",
                "initial": None,
            }
        )
        assert doc.nmode == 1


class TestValidateOpLevel:
    """Per-op validation errors (parametrized over malformed op dicts)."""

    @pytest.mark.parametrize(
        "op",
        [
            pytest.param(None, id="op-not-dict"),
            pytest.param({"op": "bogus", "modes": [], "params": {}}, id="unknown-op"),
            pytest.param({"op": "squeeze", "modes": [], "params": {}}, id="missing-modes"),
            pytest.param({"op": "squeeze", "modes": [0], "params": {}, "id": ""}, id="empty-id"),
            pytest.param({"op": "squeeze", "modes": [0], "params": {}, "id": 3}, id="id-not-str"),
        ],
        ids=repr,
    )
    def test_op_errors(self, op: dict) -> None:
        with pytest.raises(ValueError):
            validate_ir({"schema": SCHEMA, "nmode": 1, "ops": [op]})

    def test_duplicate_id_raises(self) -> None:
        """Two ops with the same id → ValueError (second occurrence)."""
        with pytest.raises(ValueError, match="duplicate id"):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 1,
                    "ops": [
                        {"id": "same", "op": "squeeze", "modes": [0], "params": {}},
                        {"id": "same", "op": "phase", "modes": [0], "params": {}},
                    ],
                }
            )

    def test_id_none_and_omitted_ok(self) -> None:
        """id is optional; None/omitted both legal."""
        doc = validate_ir(
            {
                "schema": SCHEMA,
                "nmode": 1,
                "ops": [
                    {"op": "squeeze", "modes": [0], "params": {}, "id": None},
                    {"op": "phase", "modes": [0], "params": {}},
                ],
            }
        )
        assert len(doc.ops) == 2

    # -- arity failures -----------------------------------------------------

    @pytest.mark.parametrize(
        "op,modes",
        [
            ("squeeze", 0),  # modes must be a list
            ("squeeze", []),  # one-arity needs 1
            ("squeeze", [0, 1]),
            ("beamsplitter", [0]),  # two-arity needs 2
            ("beamsplitter", [0, 1, 2]),
            ("interferometer", [0]),  # all-arity needs range(nmode)
            ("gaussian_channel", [0]),  # none-arity takes none
            ("amplifier", [0, 1]),  # any-arity at most 1
        ],
        ids=lambda x: str(x),
    )
    def test_arity_failures(self, op: str, modes: list) -> None:
        with pytest.raises(ValueError):
            validate_ir(
                {"schema": SCHEMA, "nmode": 2, "ops": [{"op": op, "modes": modes, "params": {}}]}
            )

    def test_mode_negative(self) -> None:
        with pytest.raises(ValueError, match="mode index"):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 1,
                    "ops": [{"op": "squeeze", "modes": [-1], "params": {}}],
                }
            )

    def test_mode_out_of_range(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 1,
                    "ops": [{"op": "squeeze", "modes": [1], "params": {}}],
                }
            )

    def test_mode_bool(self) -> None:
        with pytest.raises(ValueError, match="mode index"):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 1,
                    "ops": [{"op": "squeeze", "modes": [True], "params": {}}],
                }
            )

    def test_params_not_dict(self) -> None:
        with pytest.raises(ValueError, match="params must be an object"):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 1,
                    "ops": [{"op": "squeeze", "modes": [0], "params": "x"}],
                }
            )

    def test_unknown_param(self) -> None:
        with pytest.raises(ValueError, match="unknown param"):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 1,
                    "ops": [{"op": "squeeze", "modes": [0], "params": {"bogus": 1}}],
                }
            )

    def test_missing_required_param(self) -> None:
        # measure_heterodyne has no defaults; name is required
        with pytest.raises(ValueError, match="requires param"):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 1,
                    "ops": [{"op": "measure_heterodyne", "modes": [0], "params": {}}],
                }
            )


class TestCheckValue:
    """_check_value catalogue (parametrized)."""

    @pytest.mark.parametrize(
        "op,param,value",
        [
            # $param for non-num/complex
            ("measure_homodyne", "name", {"$param": "x"}),
            # $param extra keys
            ("squeeze", "r", {"$param": "x", "y": 1}),
            # $param bad name
            ("squeeze", "r", {"$param": ""}),
            ("squeeze", "r", {"$param": 3}),
            # $ref misuse
            ("measure_homodyne", "name", {"$ref": "m"}),
            # $ref extra keys
            ("squeeze", "r", {"$ref": "m", "x": 1}),
            # $ref bad source
            ("squeeze", "r", {"$ref": ""}),
            ("squeeze", "r", {"$ref": 3}),
            # $ref bad gain
            ("squeeze", "r", {"$ref": "m", "gain": "x"}),
            # unknown dict form
            ("squeeze", "r", {"foo": 1}),
            # num bad
            ("squeeze", "r", "x"),
            ("squeeze", "r", True),
            # complex bad
            ("displace", "alpha", [1, 2, 3]),
            # str bad
            ("measure_homodyne", "name", ""),
            ("measure_homodyne", "name", 3),
        ],
        ids=lambda v: str(v),
    )
    def test_value_raises(self, op: str, param: str, value) -> None:
        with pytest.raises(ValueError):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 1,
                    "ops": [{"op": op, "modes": [0], "params": {param: value}}],
                }
            )

    def test_param_and_ref_accepted(self) -> None:
        """Legal $param for num and $ref for complex pass validation."""
        doc = validate_ir(
            {
                "schema": SCHEMA,
                "nmode": 1,
                "ops": [
                    {"op": "squeeze", "modes": [0], "params": {"r": {"$param": "r"}}},
                    {
                        "op": "displace",
                        "modes": [0],
                        "params": {"alpha": {"$ref": "m", "gain": 0.5}},
                    },
                ],
            }
        )
        assert len(doc.ops) == 2


class TestCheckMatrix:
    """_check_matrix catalogue (parametrized)."""

    @pytest.mark.parametrize(
        "U",
        [
            pytest.param({}, id="not-list"),
            pytest.param([], id="empty"),
            pytest.param([[1, 2], 5], id="row-not-list"),
            pytest.param([[1, 2], [3]], id="ragged"),
            pytest.param([[1, 2], [3, "x"]], id="bad-entry"),
            pytest.param([[1, 2], [[1, 0], [0, 1]]], id="mixed-real-complex"),
            pytest.param([["a", "b"]], id="nested-not-pair"),
        ],
        ids=lambda v: str(v),
    )
    def test_matrix_raises(self, U) -> None:
        with pytest.raises(ValueError):
            validate_ir(
                {
                    "schema": SCHEMA,
                    "nmode": 2,
                    "ops": [{"op": "interferometer", "modes": [0, 1], "params": {"U": U}}],
                }
            )

    def test_flat_real_vector_accepted(self) -> None:
        """d: flat real vector is a legal matrix-kind value."""
        doc = validate_ir(
            {
                "schema": SCHEMA,
                "nmode": 1,
                "ops": [
                    {
                        "op": "gaussian_channel",
                        "modes": [],
                        "params": {"X": [[1, 0], [0, 1]], "Y": [[0, 0], [0, 0]], "d": [0.1, 0.2]},
                    }
                ],
            }
        )
        assert len(doc.ops) == 1

    def test_complex_matrix_accepted(self) -> None:
        """[[re,im],...] nested form legal for complex matrix."""
        U = [[[1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [1.0, 0.0]]]
        validate_ir(
            {
                "schema": SCHEMA,
                "nmode": 2,
                "ops": [{"op": "interferometer", "modes": [0, 1], "params": {"U": U}}],
            }
        )


# ===========================================================================
# FUNC branches — encode/decode + build_op
# ===========================================================================


class TestEncodeDecodeRoundtrip:
    def test_symbolic_param_roundtrip(self):
        """$param emit + decode roundtrip (symbolic r)."""
        c = BosonicCircuit(1)
        c.squeeze(0, "r")
        d = to_ir(c)
        assert d["ops"][0]["params"]["r"] == {"$param": "r"}
        c2 = from_ir(d)
        assert to_ir(c2) == d
        st = c2.run(r=0.5)
        assert st.nmode == 1

    def test_ref_roundtrip(self):
        """$ref emit + decode roundtrip (ParamRef)."""
        c = BosonicCircuit(1)
        c.displace(0, ParamRef("m", gain=0.5))
        d = to_ir(c)
        c2 = from_ir(d)
        assert to_ir(c2) == d

    def test_complex_bare_number_decode(self):
        """complex bare number (e.g. alpha=0.0 default) decodes to complex.

        Note: roundtrip is semantic, not byte-identical — 0.0 decodes to
        [0.0, 0.0] on re-encode.
        """
        c = BosonicCircuit(1)
        c.displace(0)  # alpha=0.0 default → to_ir emits 0.0
        d = to_ir(c)
        assert d["ops"][0]["params"]["alpha"] == 0.0
        c2 = from_ir(d)
        # alpha decodes to complex(0,0); re-encode canonicalizes to [0.0, 0.0]
        assert to_ir(c2)["ops"][0]["params"]["alpha"] == [0.0, 0.0]
        st = c2.run()
        assert st.nmode == 1

    def test_np_generic_encode(self):
        """np.float64 param goes through _encode np.generic branch."""
        c = BosonicCircuit(1)
        c.squeeze(0, np.float64(0.5))
        d = to_ir(c)
        assert d["ops"][0]["params"]["r"] == 0.5

    def test_measure_build_ops(self):
        """_build_op measure_heterodyne / measure_threshold branches.

        Roundtrip is semantic: complex 1.0 re-encodes as [1.0, 0.0].
        """
        c = BosonicCircuit(1)
        c.displace(0, 1.0)
        c.measure_heterodyne(0, "m_b")
        c.measure_threshold(0, "m_t")
        d = to_ir(c)
        ops = {o["op"]: o for o in d["ops"]}
        assert "measure_heterodyne" in ops
        assert "measure_threshold" in ops
        c2 = from_ir(d)
        assert to_ir(c2)["ops"][0]["params"]["alpha"] == [1.0, 0.0]
        # serealized op names preserved
        assert {o["op"] for o in to_ir(c2)["ops"]} == {
            "displace",
            "measure_heterodyne",
            "measure_threshold",
        }


class TestBuildOpBranches:
    """_build_op: all op branches rebuild from IR (roundtrip equality)."""

    def _assert_roundtrip(self, c: BosonicCircuit) -> None:
        d = to_ir(c)
        c2 = from_ir(d)
        assert to_ir(c2) == d

    def test_phase_fourier_branches(self):
        c = BosonicCircuit(1)
        c.phase(0, 0.3)
        c.fourier(0)
        self._assert_roundtrip(c)

    def test_two_mode_squeeze_mz_cx_branches(self):
        c = BosonicCircuit(2)
        c.two_mode_squeeze(0, 1, 0.4)
        c.mach_zehnder(0, 1)
        c.cx(0, 1, 0.7)
        self._assert_roundtrip(c)

    def test_amplifier_phase_noise_branches(self):
        c = BosonicCircuit(1)
        c.amplifier(G=1.5)
        c.phase_noise(sigma=0.2)
        self._assert_roundtrip(c)


class TestSchemaSnapshot:
    def test_ir_schema_shape(self):
        """ir_schema(): op table + initial registry + core ranges."""
        s = ir_schema()
        assert "ops" in s
        assert "squeeze" in s["ops"]
        assert s["ops"]["squeeze"]["arity"] == "one"
        assert set(s["ops"]["squeeze"]["value_kind"]) == {"r", "phi"}
        assert s["ops"]["squeeze"]["defaults"] == {"r": 0.0, "phi": 0.0}
        assert "initial" in s
        # vacuum is the special key; sources are the named GKP builders
        assert s["initial"]["vacuum"] is None
        assert "gkp0" in s["initial"]["sources"]
        assert "core_ranges" in s
