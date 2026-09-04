"""Ticket 4 regression drill (issue #4 acceptance item 3, gkp0_2d class).

Incident shape being simulated: a new op lands in a core ``ir.py``
(``OP_META`` + registry) and nobody touches the Lab layer. Pre-ticket the
op then vanished from the Lab loader whitelist -> 422 round-trip
(``e907db9`` -> ``cc0e297``). Post-ticket the whitelists are *derived*
(``cvsim.lab.schema``: core ``ir_schema()`` minus an explicit UI-hidden
set), so the derivation re-runs from the new snapshot on the next process
and the op flows into the loader, ``/schema`` and the 422 ``allowed`` set
automatically — the "core added, whitelist forgotten" drift is
structurally impossible.

This module locks the structure: the derived whitelist equals
``core_ops - UI-hidden`` per backend, and a *fresh* derivation over a
patched snapshot (exactly what a module import does) auto-includes a
newly added core op.
"""

from __future__ import annotations

from unittest.mock import patch

import cvsim.lab.schema as lab_schema
from cvsim.lab.schema import (
    _PKG_SCHEMAS,
    _UI_HIDDEN,
    _derive_whitelist,
    assemble_schema,
)

FAKE = "gkp0_2d_probe"


def test_whitelist_is_core_minus_ui_hidden():
    """Derived whitelists = core ``ir_schema()`` ops − UI-hidden set."""
    for backend in ("gaussian", "fock", "bosonic"):
        core = set(_PKG_SCHEMAS[backend]()["ops"])
        expected = frozenset(core - _UI_HIDDEN[backend])
        derived = _derive_whitelist(backend)
        assert derived == expected, backend
        # hidden names must all exist in core (fail-fast on drift)
        assert _UI_HIDDEN[backend] <= core, backend


def test_new_core_op_flows_into_derived_whitelist_and_schema():
    """The gkp0_2d-class drill: patch the core snapshot with a new op,
    re-run the derivation (what a fresh process does at import), and the
    op is in the whitelist and ``/schema`` with no Lab-layer edit."""
    real = _PKG_SCHEMAS["gaussian"]

    def patched() -> dict:
        d = real()
        d["ops"][FAKE] = {
            "arity": "one",
            "value_kind": {"x": "num"},
            "defaults": {"x": 0.0},
        }
        return d

    with patch.dict(_PKG_SCHEMAS, {"gaussian": patched}):
        wl = _derive_whitelist("gaussian")
        assert FAKE in wl  # pre-ticket this was the 422 round-trip
        # a fresh process re-runs the module body, rebuilding the
        # whitelist map — simulate exactly that here.
        with patch.dict(
            lab_schema._WHITELISTS, {"gaussian": wl}
        ):
            doc = assemble_schema()
        assert doc["ops"][FAKE]["backends"] == ["gaussian"]
