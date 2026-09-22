"""Three-representation ``validate_ir`` parity guard (ADR-0001 mirror discipline).

The representation packages may not import each other (ADR-0001), so the three
``*.ir.validate_ir`` implementations are **required** mirrors of one contract:
one payload can reach any backend via the ``backend`` field, so the same
document must be accepted or rejected identically. Nothing enforced that; the
fock copy silently lost whole check groups (mode range, param value kinds) and
accepted payloads the other two reject — negative mode indices wrapped around
and produced wrong physics.

This test is the machine-checked version of "the mirrors agree". It is
dependency-free (imports the three validators only).

Deliberate, structural differences are enumerated in ``_KNOWN_DIVERGENCES``
and must be *ops*, never check groups: an op that exists in one
representation only is a legitimate rep fact, a check one rep skips is drift.
"""

from __future__ import annotations

from typing import Any

import pytest

from cvsim.bosonic.ir import OP_META as _B_META
from cvsim.bosonic.ir import validate_ir as bosonic_validate
from cvsim.fock.ir import OP_META as _F_META
from cvsim.fock.ir import validate_ir as fock_validate
from cvsim.gaussian.ir import OP_META as _G_META
from cvsim.gaussian.ir import validate_ir as gaussian_validate

VALIDATORS = {
    "gaussian": gaussian_validate,
    "fock": fock_validate,
    "bosonic": bosonic_validate,
}

OP_TABLES = {"gaussian": _G_META, "fock": _F_META, "bosonic": _B_META}

_ALL_OPS = set().union(*(set(t) for t in OP_TABLES.values()))

#: Ops declared by all three representations — the shared contract surface.
#: Divergences on these are drift. Derived (never hand-listed) so that a newly
#: shared op is automatically covered.
SHARED_OPS = frozenset(
    op for op in _ALL_OPS if all(op in t for t in OP_TABLES.values())
)

#: Ops declared by one or two representations. These are rep capabilities, not
#: drift: ``apply_kraus``/``apply_unitary``/``kerr``/``measure_pnr`` are
#: fock-only (no gaussian/bosonic builder), and ``fourier``/``mz``/
#: ``gaussian_channel``/``measure_threshold`` are not fock ops. A divergence
#: may only be excused when the offending op is not in ``SHARED_OPS``.
REP_ONLY_OPS = frozenset(_ALL_OPS - SHARED_OPS)


def _outcome(name: str, doc: dict[str, Any]) -> str:
    """'accept' / 'reject' — anything else (TypeError, IndexError, …) is a
    protocol violation: the Lab only maps ValueError-family to 422."""
    try:
        VALIDATORS[name](doc)
    except ValueError:
        return "reject"
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(
            f"{name}.validate_ir raised {type(exc).__name__} on {doc!r}: {exc!r} "
            f"(must raise ValueError — the Lab's 422 contract)"
        ) from exc
    return "accept"


def _doc(ops: list[dict[str, Any]], nmode: int = 2, **extra: Any) -> dict[str, Any]:
    return {"schema": "circuit_v1", "nmode": nmode, "ops": ops, **extra}


def _op(name: str, modes: list[Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"op": name, "modes": modes, "params": {} if params is None else params}


#: Payloads whose fate the three validators must agree on. Every entry is a
#: *check* every representation is expected to perform, using ops all three
#: declare (``squeeze`` / ``beamsplitter`` / ``interferometer``), so no entry
#: can be excused as rep-specific.
SHARED_CASES: list[tuple[str, dict[str, Any]]] = [
    # -- mode indices ------------------------------------------------------
    ("negative mode", _doc([_op("squeeze", [-1], {"r": 0.1})])),
    ("bool mode", _doc([_op("squeeze", [True], {"r": 0.1})])),
    ("mode >= nmode", _doc([_op("squeeze", [5], {"r": 0.1})])),
    ("float mode", _doc([_op("squeeze", [0.5], {"r": 0.1})])),
    ("modes not a list", _doc([_op("squeeze", 0, {"r": 0.1})])),  # type: ignore[arg-type]
    ("modes absent", _doc([{"op": "squeeze", "params": {"r": 0.1}}])),
    # -- arity -------------------------------------------------------------
    ("one-arity zero modes", _doc([_op("squeeze", [], {"r": 0.1})])),
    ("one-arity two modes", _doc([_op("squeeze", [0, 1], {"r": 0.1})])),
    ("two-arity one mode", _doc([_op("beamsplitter", [0], {"theta": 0.1, "phi": 0.0})])),
    (
        "all-arity wrong range",
        _doc(
            [_op("interferometer", [0], {"U": [[1, 0], [0, 1]]})],
            nmode=2,
        ),
    ),
    # -- param containers / presence --------------------------------------
    ("params is a str", _doc([{**_op("squeeze", [0]), "params": "r"}])),
    ("params absent", _doc([{"op": "squeeze", "modes": [0]}])),
    ("unknown param name", _doc([_op("squeeze", [0], {"bogus": 1.0})])),
    ("required param missing", _doc([_op("interferometer", [0, 1], {})])),
    # -- param value kinds -------------------------------------------------
    ("num given str", _doc([_op("squeeze", [0], {"r": "oops"})])),
    ("num given list", _doc([_op("squeeze", [0], {"r": [1, 2]})])),
    ("num given bool", _doc([_op("squeeze", [0], {"r": True})])),
    ("unknown dict form", _doc([_op("squeeze", [0], {"r": {"weird": 1}})])),
    ("$param non-str", _doc([_op("squeeze", [0], {"r": {"$param": 5}})])),
    ("$param extra key", _doc([_op("squeeze", [0], {"r": {"$param": "g", "x": 1}})])),
    ("$ref gain str", _doc([_op("squeeze", [0], {"r": {"$ref": "n0", "gain": "big"}})])),
    ("$ref unknown key", _doc([_op("squeeze", [0], {"r": {"$ref": "n0", "zz": 1}})])),
    ("$param on complex ok", _doc([_op("displace", [0], {"alpha": {"$param": "a"}})])),
    ("matrix ragged", _doc([_op("interferometer", [0, 1], {"U": [[1, 0], [0]]})])),
    ("matrix is a str", _doc([_op("interferometer", [0, 1], {"U": "nope"})])),
    (
        "matrix empty",
        _doc([_op("interferometer", [0, 1], {"U": []})]),
    ),
    # -- ids ---------------------------------------------------------------
    ("empty id", _doc([{**_op("squeeze", [0], {"r": 0.1}), "id": ""}])),
    ("non-str id", _doc([{**_op("squeeze", [0], {"r": 0.1}), "id": 5}])),
    (
        "duplicate id",
        _doc(
            [
                {**_op("squeeze", [0], {"r": 0.1}), "id": "a"},
                {**_op("squeeze", [1], {"r": 0.1}), "id": "a"},
            ]
        ),
    ),
    # -- top-level / extension fields --------------------------------------
    ("view is a list", _doc([_op("squeeze", [0], {"r": 0.1})], view=[1])),
    ("ui is a list", _doc([_op("squeeze", [0], {"r": 0.1})], ui=[1])),
    ("seed negative", _doc([_op("squeeze", [0], {"r": 0.1})], seed=-1)),
    ("seed is bool", _doc([_op("squeeze", [0], {"r": 0.1})], seed=True)),
    ("seed is str", _doc([_op("squeeze", [0], {"r": 0.1})], seed="0")),
    ("unknown top-level field", _doc([_op("squeeze", [0], {"r": 0.1})], bogus=1)),
    ("nmode zero", _doc([], nmode=0)),
    ("nmode is bool", _doc([], nmode=True)),
    ("nmode is str", _doc([], nmode="2")),
    ("ops is a dict", _doc([]) | {"ops": {"a": 1}}),
    ("op entry not a dict", _doc([42])),  # type: ignore[list-item]
    ("op name unknown", _doc([_op("not_an_op", [0])])),
    ("op name is int", _doc([{"op": 5, "modes": [0], "params": {}}])),
    ("bad schema", {**_doc([]), "schema": "circuit_v2"}),
    ("payload not a dict", "nope"),  # type: ignore[list-item]
    # -- documents that must be ACCEPTED (guard against over-rejection) ----
    ("valid squeeze", _doc([_op("squeeze", [0], {"r": 0.3, "phi": 0.1})])),
    ("valid beamsplitter", _doc([_op("beamsplitter", [0, 1], {"theta": 0.5, "phi": 0.2})])),
    ("valid interferometer", _doc([_op("interferometer", [0, 1], {"U": [[1, 0], [0, 1]]})])),
    ("valid empty ops", _doc([])),
    ("valid $param", _doc([_op("squeeze", [0], {"r": {"$param": "g"}})])),
    ("valid $ref", _doc([_op("squeeze", [0], {"r": {"$ref": "n0", "gain": 0.5}})])),
    ("valid measure name", _doc([_op("measure_homodyne", [0], {"phi": 0.0, "name": "hd"})])),
]


def test_shared_cases_only_use_shared_ops() -> None:
    """Every catalogue payload must use ops all three reps declare.

    Otherwise a case could "diverge" merely because one rep does not know the
    op, which is a rep fact rather than drift — exactly the confusion that let
    the real gaps hide. Cases whose *subject* is a malformed op name are
    exempt: there the unknown name is the input under test, not a rep choice.
    """
    malformed = {"op name unknown", "op name is int"}
    for label, doc in SHARED_CASES:
        if not isinstance(doc, dict) or label in malformed:
            continue
        for node in doc.get("ops", []):
            if isinstance(node, dict) and "op" in node:
                assert node["op"] in SHARED_OPS, (
                    f"{label!r} uses rep-only op {node['op']!r}; shared-check cases "
                    f"must stick to {sorted(SHARED_OPS)}"
                )


@pytest.mark.parametrize("label,doc", SHARED_CASES, ids=[c[0] for c in SHARED_CASES])
def test_three_validators_agree(label: str, doc: dict[str, Any]) -> None:
    """Same payload -> same accept/reject verdict in all three representations."""
    outcomes = {name: _outcome(name, doc) for name in VALIDATORS}
    assert len(set(outcomes.values())) == 1, (
        f"{label}: validators disagree -> {outcomes} (payload={doc!r}); "
        f"a shared check has drifted apart"
    )


def test_shared_cases_cover_both_verdicts() -> None:
    """The catalogue must actually exercise accept and reject.

    Without this, a validator that rejected everything (or nothing) would make
    the parity test pass vacuously.
    """
    verdicts = {_outcome("gaussian", doc) for _, doc in SHARED_CASES}
    assert verdicts == {"accept", "reject"}, verdicts


def test_rep_only_ops_are_derived_not_stale() -> None:
    """``SHARED_OPS`` / ``REP_ONLY_OPS`` must partition the union of the tables."""
    assert not (SHARED_OPS & REP_ONLY_OPS)
    assert SHARED_OPS | REP_ONLY_OPS == _ALL_OPS
    assert SHARED_OPS, "no shared ops — the mirror contract would be untested"
    assert REP_ONLY_OPS, "no rep-only ops — the excuse set would be untested"


def test_fock_only_arity_is_not_gaussian_any() -> None:
    """fock 'subset' must stay distinct from gaussian/bosonic 'any'.

    'any' in gaussian/bosonic means at most 1 mode (amplifier/phase_noise take
    ``mode: int | None``); fock's apply_unitary is k-local. They shared the
    label 'any' until the parity work, which is precisely how apply_unitary
    went unvalidated.
    """
    from cvsim.bosonic.ir import OP_META as B_META
    from cvsim.fock.ir import OP_META as F_META
    from cvsim.gaussian.ir import OP_META as G_META

    assert F_META["apply_unitary"].arity == "subset"
    for table in (G_META, B_META):
        assert "subset" not in {m.arity for m in table.values()}
        assert "any" in {m.arity for m in table.values()}
    assert "any" not in {m.arity for m in F_META.values()}
@pytest.mark.parametrize(
    "modes",
    [[], [0], [1, 2], [0, 1, 2]],
    ids=["all", "single", "k-local", "full"],
)
def test_fock_subset_arity_accepts_distinct_subsets(modes: list[int]) -> None:
    """apply_unitary legitimately takes any set of distinct modes ([] = all)."""
    dim = 3 ** len(modes) if modes else 27
    U = [[[1.0, 0.0] if i == j else [0.0, 0.0] for j in range(dim)] for i in range(dim)]
    doc = _doc([_op("apply_unitary", modes, {"U": U})], nmode=3)
    assert _outcome("fock", doc) == "accept"


def test_fock_subset_arity_rejects_duplicate_modes() -> None:
    """Duplicate modes build fine, then crash run() with 'repeated axis'."""
    doc = _doc([_op("apply_unitary", [0, 0], {"U": [[[1.0, 0.0]]]})], nmode=3)
    assert _outcome("fock", doc) == "reject"
