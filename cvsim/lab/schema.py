"""Lab schema assembly (schema 组装, ADR-0003 #3, spec ticket 2).

The core representation packages are the schema authority (their
``ir_schema()`` snapshots, ticket 1); this module is the Lab-side
**assembler**: it overlays the Lab op whitelists (a UI concept — which ops
each backend's workbench has unlocked), declares the Lab extension-field
boundaries (initial shapes / cutoff / view / sweep / shots / rounds, Q11)
and emits the ``GET /schema`` payload.

The frontend still reads its own mirrors (ops.js ``backends`` fields,
initial.js ``BOSONIC_SOURCES``) until ticket 3 switches the consumers;
``tests/test_lab_schema.py`` cross-asserts data-level equality in the
meantime (dual-write guardrail, Q9).
"""

from __future__ import annotations

import json
from typing import Any

from cvsim.bosonic import ir_schema as _bosonic_ir_schema
from cvsim.fock import ir_schema as _fock_ir_schema
from cvsim.gaussian import ir_schema as _gaussian_ir_schema
from cvsim.lab.ir import BOSONIC_WHITELIST, FOCK_WHITELIST, LAB_WHITELIST
from cvsim.lab.scan import SWEEPABLE_PARAMS

#: UI name per IR name where the two differ (Q3: IR names are canonical;
#: the two measurement ops are the only renames in the current UI). The
#: inverse of ops.js UI_TO_V1_OP — data-level, consumed by no frontend yet.
UI_NAME_BY_IR: dict[str, str] = {
    "measure_homodyne": "homodyne",
    "measure_heterodyne": "heterodyne",
}

#: Backend order (spec frozen): gaussian → fock → bosonic.
BACKENDS: list[str] = ["gaussian", "fock", "bosonic"]

#: Package ir_schema() per backend (resolution order = BACKENDS order).
_PKG_SCHEMAS: dict[str, Any] = {
    "gaussian": _gaussian_ir_schema,
    "fock": _fock_ir_schema,
    "bosonic": _bosonic_ir_schema,
}

_WHITELISTS: dict[str, frozenset[str]] = {
    "gaussian": LAB_WHITELIST,
    "fock": FOCK_WHITELIST,
    "bosonic": BOSONIC_WHITELIST,
}

#: Lab extension-field boundaries (Q11: Lab declares, core stays opaque).
#: Values are the bounds the Lab/server actually enforce — UI teaching
#: scales (slider ranges) stay in ops.js per Q6.
_EXTENSIONS: dict[str, Any] = {
    "cutoff": {"min": 1, "max": 30},  # fock-only, per-mode (index.html slider)
    "view": {"lim_max": 50.0, "lim_min_exclusive": 0, "n": [2, 512]},
    "sweep": {"n": [2, 200]},
    "sweepable": {op: sorted(params) for op, params in SWEEPABLE_PARAMS.items()},
    "shots": [1, 100000],
    "rounds": [1, 100],
}

def assemble_schema() -> dict[str, Any]:
    """Assemble the ``/schema`` payload from the three core ``ir_schema()``
    snapshots + Lab whitelists + Lab extension declarations.

    Fresh deep-copy per call (the core snapshots are already per-call fresh;
    the whitelists are only read). JSON-native end to end.
    """
    pkg_schemas = {b: _PKG_SCHEMAS[b]() for b in BACKENDS}

    # per-op backend membership: whitelist intersection, resolved to the op's
    # meta from its own package (first backend in BACKENDS order that lists it).
    ops: dict[str, Any] = {}
    for backend in BACKENDS:
        for op_name in sorted(_WHITELISTS[backend]):
            meta = pkg_schemas[backend]["ops"].get(op_name)
            if meta is None:
                # A whitelisted name without a core IR op would be exactly the
                # gkp0_2d-class mirror drift this ticket exists to prevent —
                # scream instead of silently omitting it from /schema.
                raise RuntimeError(
                    f"whitelist op {op_name!r} ({backend}) has no core ir_schema "
                    "entry — mirror drift; update the core package or the whitelist"
                )
            entry = ops.setdefault(
                op_name, {"backends": [], "meta": meta, "core_ranges": {}}
            )
            entry["backends"].append(backend)
            for param, rng in pkg_schemas[backend]["core_ranges"].get(op_name, {}).items():
                entry["core_ranges"][param] = rng
    out_ops: dict[str, Any] = {}
    for op_name, entry in ops.items():
        item: dict[str, Any] = {
            "backends": entry["backends"],
            "meta": entry["meta"],
        }
        ui_name = UI_NAME_BY_IR.get(op_name)
        if ui_name is not None:
            item["uiName"] = ui_name
        if entry["core_ranges"]:
            item["core_ranges"] = entry["core_ranges"]
        out_ops[op_name] = item

    return {
        "backends": list(BACKENDS),
        "ops": out_ops,
        "initial": {
            backend: pkg_schemas[backend]["initial"] for backend in BACKENDS
        },
        "extensions": {
            # rebuild nested structures so callers cannot mutate the module
            # constants via the returned payload.
            "cutoff": dict(_EXTENSIONS["cutoff"]),
            "view": {
                "lim_max": _EXTENSIONS["view"]["lim_max"],
                "lim_min_exclusive": _EXTENSIONS["view"]["lim_min_exclusive"],
                "n": list(_EXTENSIONS["view"]["n"]),
            },
            "sweep": {"n": list(_EXTENSIONS["sweep"]["n"])},
            "sweepable": {k: list(v) for k, v in _EXTENSIONS["sweepable"].items()},
            "shots": list(_EXTENSIONS["shots"]),
            "rounds": list(_EXTENSIONS["rounds"]),
        },
    }

def schema_doc() -> str:
    """`/schema` response body: the assembled payload as a JSON string."""
    return json.dumps(assemble_schema(), sort_keys=True)
