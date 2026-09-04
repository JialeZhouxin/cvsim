"""Schema assembly + `GET /schema` (tickets 2+4 of schema single-source).

Golden payload shape (spec `.scratch/schema-single-source/spec.md`, design
frozen) + 422 error-text invariants. Ticket 4 retired the ticket-2
data-level cross assertions: the dual-write mirrors (ops.js `backends`
fields / initial.js `BOSONIC_SOURCES`) are deleted and the whitelists are
now *derived* in `cvsim.lab.schema` (core `ir_schema()` minus the
UI-hidden set) — mirror drift is structurally impossible, so there is no
second side left to cross-assert against.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cvsim.lab.ir import LAB_WHITELIST
from cvsim.lab.schema import assemble_schema, schema_doc
from cvsim.lab.server import app

client = TestClient(app)

STATIC_DIR = Path(__file__).resolve().parents[1] / "cvsim" / "lab" / "static"

# -- assemble_schema: payload shape ------------------------------------------

def test_assemble_schema_top_level_keys():
    payload = assemble_schema()
    assert set(payload) == {"backends", "ops", "initial", "extensions"}
    assert payload["backends"] == ["gaussian", "fock", "bosonic"]

def test_ops_primary_keys_are_whitelist_union():
    """ops = union of the three whitelists (unlocked subset only)."""
    from cvsim.lab.ir import BOSONIC_WHITELIST, FOCK_WHITELIST

    payload = assemble_schema()
    expected = set(LAB_WHITELIST) | set(FOCK_WHITELIST) | set(BOSONIC_WHITELIST)
    assert set(payload["ops"]) == expected

def test_ops_not_unlocked_are_absent():
    """Core-only ops (apply_unitary/apply_kraus) are valid IR but not in any
    whitelist — the Lab has not unlocked them, so /schema does not carry them."""
    payload = assemble_schema()
    assert "apply_unitary" not in payload["ops"]
    assert "apply_kraus" not in payload["ops"]
    # v0 sources are UI concepts (ops.js), not IR ops — absent too.
    assert "vacuum" not in payload["ops"]
    assert "tmsv" not in payload["ops"]

def test_per_op_keys_and_backends():
    payload = assemble_schema()
    ops = payload["ops"]

    # keys: uiName present only when IR name ≠ UI name; core_ranges only when
    # the core enforces a range for that op (else the key is omitted).
    assert set(ops["measure_homodyne"]) == {"uiName", "backends", "meta"}
    assert ops["measure_homodyne"]["uiName"] == "homodyne"
    assert ops["measure_heterodyne"]["uiName"] == "heterodyne"
    # same-name ops: no uiName key at all (同名省略)
    for name in ("squeeze", "loss", "mz", "mach_zehnder", "kerr"):
        assert "uiName" not in ops[name], name

    assert set(ops["loss"]["backends"]) == {"gaussian", "fock", "bosonic"}
    assert set(ops["mz"]["backends"]) == {"gaussian"}
    assert set(ops["mach_zehnder"]["backends"]) == {"fock", "bosonic"}
    assert set(ops["kerr"]["backends"]) == {"fock"}
    assert set(ops["interferometer"]["backends"]) == {"bosonic"}
    assert set(ops["gaussian_channel"]["backends"]) == {"bosonic"}

def test_per_op_meta_from_core_ir_schema():
    """meta comes from the package's ir_schema() — the core is the authority."""
    ops = assemble_schema()["ops"]
    assert ops["squeeze"]["meta"] == {
        "arity": "one",
        "value_kind": {"r": "num", "phi": "num"},
        "defaults": {"r": 0.0, "phi": 0.0},
    }
    # bosonic-only op carries bosonic meta (incl. d: None default)
    assert ops["gaussian_channel"]["meta"]["defaults"] == {"d": None}
    # bosonic ir_schema has no 'mz' — gaussian meta must be used there
    assert ops["mz"]["meta"]["arity"] == "two"
    assert ops["mz"]["meta"]["value_kind"] == {"theta": "num", "phi": "num"}

def test_core_ranges_merged_per_op():
    """core_ranges: gaussian loss.T + fock loss.eta merge into one entry."""
    payload = assemble_schema()
    assert payload["ops"]["loss"]["core_ranges"] == {
        "T": [0.0, 1.0],
        "eta": [0.0, 1.0],
    }
    # ops without core ranges: key omitted entirely (spec: 无则省略)
    assert "core_ranges" not in payload["ops"]["squeeze"]
    assert "core_ranges" not in payload["ops"]["measure_homodyne"]

def test_initial_registry_forwarded_from_core():
    payload = assemble_schema()
    assert payload["initial"] == {
        "fock": {"kind": "int", "min": 0},
        "bosonic": {
            "kind": "enum",
            "sources": ["gkp0", "gkp1", "gkp0_2d", "gkp1_2d"],
            "vacuum": None,
        },
        "gaussian": None,
    }

def test_extensions_lab_declared():
    payload = assemble_schema()
    ext = payload["extensions"]
    assert ext["cutoff"] == {"min": 1, "max": 30}
    assert ext["view"]["n"] == [2, 512]
    assert ext["view"]["lim_max"] == 50.0
    assert ext["sweep"]["n"] == [2, 200]
    assert ext["shots"] == [1, 100000]
    assert ext["rounds"] == [1, 100]
    # sweepable: IR-name keyed, forwarded from scan.py SWEEPABLE_PARAMS
    assert ext["sweepable"]["squeeze"] == ["r"]
    assert ext["sweepable"]["loss"] == ["T"]
    assert sorted(ext["sweepable"]["mz"]) == ["phi", "theta"]
    assert "phase" in ext["sweepable"]  # pre-existing (latent phi/theta bug is out of scope)

def test_payload_is_json_native_and_deep():
    p1 = assemble_schema()
    p1["ops"]["loss"]["core_ranges"]["T"][0] = 999
    p1["initial"]["bosonic"]["sources"].append("gkp9")
    p2 = assemble_schema()
    assert p2["ops"]["loss"]["core_ranges"]["T"][0] == 0.0
    assert "gkp9" not in p2["initial"]["bosonic"]["sources"]
    assert json.loads(json.dumps(p2, sort_keys=True)) == p2

def test_schema_doc_is_json_string():
    doc = schema_doc()
    assert isinstance(doc, str)
    parsed = json.loads(doc)
    assert parsed == assemble_schema()

# -- GET /schema endpoint ------------------------------------------------------

def test_get_schema_endpoint():
    r = client.get("/schema")
    assert r.status_code == 200
    assert r.json() == assemble_schema()

def test_get_schema_content_type_json():
    r = client.get("/schema")
    assert "application/json" in r.headers["content-type"]

# -- 422 text contract (structured errors, single message template) ----------

def _detail(body: dict) -> str:
    r = client.post("/run", json=body)
    assert r.status_code == 422
    return r.json()["detail"]

def test_422_whitelist_message_format_unified():
    """Three whitelists, one message template; allowed list sorted."""
    msg_g = _detail_for(
        {"schema": "circuit_v1", "nmode": 2,
         "ops": [{"op": "cz", "modes": [0, 1], "params": {"weight": 1.0}}]}
    )
    msg_f = _detail_for(
        {"schema": "circuit_v1", "nmode": 1, "backend": "fock",
         "ops": [{"op": "fourier", "modes": [0], "params": {}}]}
    )
    msg_b = _detail_for(
        {"schema": "circuit_v1", "nmode": 1, "backend": "bosonic",
         "ops": [{"op": "kerr", "modes": [0], "params": {"chi": 0.1}}]}
    )
    for msg, backend in ((msg_g, "lab"), (msg_f, "fock"), (msg_b, "bosonic")):
        # one shared template: prefix + not-in-whitelist + sorted allowed
        assert " not in " in msg
        assert f"{backend}" in msg.lower()
        assert "whitelist: [" in msg
        # allowed list is the sorted whitelist
        allowed = msg.rsplit("whitelist: ", 1)[1]
        assert allowed.startswith("[") and allowed.endswith("]")
        names = [s.strip().strip("'") for s in allowed[1:-1].split(",")]
        assert names == sorted(names)

def _detail_for(body: dict) -> str:
    r = client.post("/run", json=body)
    assert r.status_code == 422, r.text
    return r.json()["detail"]

def test_422_bosonic_initial_semantics_text_unchanged():
    """Fock-int initial → bosonic keeps its diagnosable message (ebcdf4c)."""
    msg = _detail_for(
        {"schema": "circuit_v1", "nmode": 2, "backend": "bosonic",
         "initial": [0, 3], "ops": []}
    )
    assert "Fock photon numbers" in msg

def test_422_bosonic_generic_initial_message_unchanged():
    msg = _detail_for(
        {"schema": "circuit_v1", "nmode": 1, "backend": "bosonic",
         "initial": ["even_cat"], "ops": []}
    )
    assert msg == (
        "initial must be a list of null/'gkp0'/'gkp1'/'gkp0_2d'/'gkp1_2d' per mode"
    )

def test_422_fock_initial_message_unchanged():
    """Core fock IR validation fires first (stricter/equal to the Lab check)."""
    msg = _detail_for(
        {"schema": "circuit_v1", "nmode": 2, "backend": "fock",
         "initial": [1.5, 0], "ops": []}
    )
    assert msg == "initial must be a list of nmode=2 ints, got [1.5, 0]"
    msg2 = _detail_for(
        {"schema": "circuit_v1", "nmode": 2, "backend": "fock",
         "initial": [-1, 0], "ops": []}
    )
    assert "initial[0]=-1 must be in [0, 10)" in msg2

def test_422_gaussian_whitelist_message_semantics_unchanged():
    """Semantic content kept: op name + whitelist mention (format unified)."""
    msg = _detail_for(
        {"schema": "circuit_v0", "nodes": [{"id": "x", "op": "cz", "params": {}}]}
    )
    assert "unknown op" in msg  # v0 translation errors untouched

def test_422_fock_whitelist_message_contains_op():
    msg = _detail_for(
        {"schema": "circuit_v1", "nmode": 2, "backend": "fock",
         "ops": [{"id": "x", "op": "interferometer", "modes": [0, 1],
                  "params": {"U": [[1, 0], [0, 1]]}}]}
    )
    assert "interferometer" in msg
    assert "whitelist" in msg

def test_422_whitelist_byte_identical_node_id():
    """Byte-identity golden: the rendered /run detail equals the ir.py raise
    text verbatim, incl. the node id (ops[x], not ops[?]) — the structured
    {code, where, op, allowed} template reproduces it exactly."""
    from cvsim.lab.ir import CircuitV0Error, load_circuit

    body = {"schema": "circuit_v1", "nmode": 2, "backend": "fock",
            "ops": [{"id": "x", "op": "interferometer", "modes": [0, 1],
                     "params": {"U": [[1, 0], [0, 1]]}}]}
    with pytest.raises(CircuitV0Error) as exc_info:
        load_circuit(body)
    raise_text = str(exc_info.value)
    # and through HTTP: rendered text == raise text (id preserved)
    assert _detail_for(body) == raise_text
    assert raise_text.startswith("ops[x]:")

    # no-id node → ops[?] prefix, still byte-identical
    body_noid = {"schema": "circuit_v1", "nmode": 2, "backend": "fock",
                 "ops": [{"op": "interferometer", "modes": [0, 1],
                          "params": {"U": [[1, 0], [0, 1]]}}]}
    with pytest.raises(CircuitV0Error) as exc2:
        load_circuit(body_noid)
    assert _detail_for(body_noid) == str(exc2.value)
    assert _detail_for(body_noid).startswith("ops[?]:")
