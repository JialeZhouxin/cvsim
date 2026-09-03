"""Golden schema-snapshot tests (ticket 1 of schema single-source).

`ir_schema()` per representation package is the authoritative entry point for
circuit_v1 schema knowledge (CONTEXT: 表示包 schema 快照). These tests freeze
the payload **shape** (key sets + value types) — not physics values; the op
tables themselves are already frozen by validate_ir round-trip tests.

Ticket 2 (Lab schema assembly) consumes these dicts; ticket 4 deletes the
mirrors. Lab code itself must not appear here (ticket 2's job).
"""

from __future__ import annotations

import cvsim.bosonic as bosonic
import cvsim.fock as fock
import cvsim.gaussian as gaussian

# -- shared shape contract ---------------------------------------------------

ARITIES = {"one", "two", "all", "any", "none"}
VALUE_KINDS = {"num", "complex", "matrix", "str", "kraus"}

def _check_ops_shape(ops: object) -> None:
    assert isinstance(ops, dict)
    assert ops, "ops table must not be empty"
    for name, meta in ops.items():
        assert isinstance(name, str) and name
        assert set(meta) == {"arity", "value_kind", "defaults"}, (name, set(meta))
        assert meta["arity"] in ARITIES, (name, meta["arity"])
        vk = meta["value_kind"]
        assert isinstance(vk, dict)
        assert all(isinstance(k, str) and v in VALUE_KINDS for k, v in vk.items()), name
        df = meta["defaults"]
        assert isinstance(df, dict)
        # defaults ⊆ value_kind keys; every no-default param must be listed in value_kind
        assert set(df) <= set(vk), name

def _payload_keys(payload: dict) -> None:
    assert set(payload) == {"ops", "initial", "core_ranges"}

# -- gaussian -----------------------------------------------------------------

def test_gaussian_ir_schema_shape():
    payload = gaussian.ir_schema()
    _payload_keys(payload)
    _check_ops_shape(payload["ops"])
    assert payload["initial"] is None
    # only core-enforced range: loss T ∈ [0, 1]
    assert payload["core_ranges"] == {"loss": {"T": [0.0, 1.0]}}

def test_gaussian_ir_schema_ops_match_op_meta():
    """Schema op names must equal the IR validator's op set (single source)."""
    from cvsim.gaussian.ir import OP_META

    payload = gaussian.ir_schema()
    assert set(payload["ops"]) == set(OP_META)
    assert payload["ops"]["measure_homodyne"] == {
        "arity": "one",
        "value_kind": {"phi": "num", "name": "str"},
        "defaults": {"phi": 0.0},
    }
    assert payload["ops"]["interferometer"]["arity"] == "all"

def test_gaussian_ir_schema_snapshot_is_deep():
    """Callers must not be able to mutate package-internal state."""
    p1 = gaussian.ir_schema()
    p1["ops"]["squeeze"]["value_kind"]["r"] = "HACK"
    p1["core_ranges"]["loss"]["T"][0] = 999
    p2 = gaussian.ir_schema()
    assert p2["ops"]["squeeze"]["value_kind"]["r"] == "num"
    assert p2["core_ranges"]["loss"]["T"][0] == 0.0

def test_gaussian_ir_schema_json_roundtrip():
    import json

    payload = gaussian.ir_schema()
    text = json.dumps(payload, sort_keys=True)
    assert json.loads(text) == payload

# -- fock ----------------------------------------------------------------------

def test_fock_ir_schema_shape():
    payload = fock.ir_schema()
    _payload_keys(payload)
    _check_ops_shape(payload["ops"])
    # fock initial semantics: per-mode number state (int), no name enum
    assert payload["initial"] == {"kind": "int", "min": 0}
    # fock loss param is named eta
    assert payload["core_ranges"] == {"loss": {"eta": [0.0, 1.0]}}

def test_fock_ir_schema_ops_match_op_meta():
    from cvsim.fock.ir import OP_META

    payload = fock.ir_schema()
    assert set(payload["ops"]) == set(OP_META)
    assert payload["ops"]["kerr"] == {
        "arity": "one",
        "value_kind": {"chi": "num"},
        "defaults": {"chi": 0.0},
    }
    assert payload["ops"]["apply_kraus"]["value_kind"] == {"kraus_ops": "kraus"}

def test_fock_ir_schema_snapshot_is_deep():
    p1 = fock.ir_schema()
    p1["initial"]["min"] = 5
    p2 = fock.ir_schema()
    assert p2["initial"]["min"] == 0

def test_fock_ir_schema_json_roundtrip():
    import json

    payload = fock.ir_schema()
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload

# -- bosonic --------------------------------------------------------------------

BOSONIC_INITIAL_SOURCES = ["gkp0", "gkp1", "gkp0_2d", "gkp1_2d"]

def test_bosonic_ir_schema_shape():
    payload = bosonic.ir_schema()
    _payload_keys(payload)
    _check_ops_shape(payload["ops"])
    assert payload["initial"] == {
        "kind": "enum",
        "sources": BOSONIC_INITIAL_SOURCES,
        "vacuum": None,
    }
    assert payload["core_ranges"] == {"loss": {"T": [0.0, 1.0]}}

def test_bosonic_ir_schema_ops_match_op_meta():
    from cvsim.bosonic.ir import OP_META

    payload = bosonic.ir_schema()
    assert set(payload["ops"]) == set(OP_META)
    assert payload["ops"]["gaussian_channel"]["defaults"] == {"d": None}
    assert payload["ops"]["measure_threshold"]["value_kind"] == {"name": "str"}

def test_bosonic_ir_schema_sources_match_registry():
    """ir_schema sources must equal the registry the circuit loader uses."""
    from cvsim.bosonic.ir import INITIAL_SOURCES

    assert list(INITIAL_SOURCES) == BOSONIC_INITIAL_SOURCES

def test_bosonic_ir_schema_snapshot_is_deep():
    p1 = bosonic.ir_schema()
    p1["initial"]["sources"].append("gkp9")
    p2 = bosonic.ir_schema()
    assert p2["initial"]["sources"] == BOSONIC_INITIAL_SOURCES

def test_bosonic_ir_schema_json_roundtrip():
    import json

    payload = bosonic.ir_schema()
    assert json.loads(json.dumps(payload, sort_keys=True)) == payload

# -- cross-package parity ---------------------------------------------------------

def test_three_backends_declared_ops_subset_consistency():
    """Shared param names carry the same value kind across packages.

    Packages are independent (ADR-0001) and may legitimately differ:
    arity (gaussian amplifier/phase_noise accept [] = all modes, fock is
    per-mode), param sets (fock loss is ``eta``-only, gaussian/bosonic loss
    carries ``T`` + ``nbar``), squeeze phi, fock-only kraus/kerr/apply_*.
    Only same-named params must agree in kind — this is the data-level
    seam ticket 2 merges over.
    """
    g = gaussian.ir_schema()["ops"]
    f = fock.ir_schema()["ops"]
    b = bosonic.ir_schema()["ops"]

    for name in set(g) & set(f):
        shared = set(g[name]["value_kind"]) & set(f[name]["value_kind"])
        for k in shared:
            assert g[name]["value_kind"][k] == f[name]["value_kind"][k], (name, k)

    for name in set(g) & set(b):
        shared = set(g[name]["value_kind"]) & set(b[name]["value_kind"])
        for k in shared:
            assert g[name]["value_kind"][k] == b[name]["value_kind"][k], (name, k)

    for name in set(f) & set(b):
        shared = set(f[name]["value_kind"]) & set(b[name]["value_kind"])
        for k in shared:
            assert f[name]["value_kind"][k] == b[name]["value_kind"][k], (name, k)

def test_schema_no_opmeta_instances_leak():
    """Pure data only — no OpMeta / dataclass instances in the payload."""
    import dataclasses

    def scan(obj: object) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                scan(v)
        elif isinstance(obj, list):
            for v in obj:
                scan(v)
        else:
            assert not dataclasses.is_dataclass(obj), type(obj)

    for mod in (gaussian, fock, bosonic):
        scan(mod.ir_schema())
