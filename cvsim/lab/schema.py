"""Lab schema assembly (schema 组装, ADR-0003 #3, spec ticket 2).

The core representation packages are the schema authority (their
``ir_schema()`` snapshots, ticket 1); this module is the Lab-side
**assembler**: it **derives** the Lab op whitelists (a UI concept — which
ops each backend's workbench exposes) as *core ops minus an explicit
UI-hidden set* (ticket 4: a newly added core op now flows into the loader
and ``/schema`` automatically — the gkp0_2d-class "core added, whitelist
forgotten" drift is structurally impossible), declares the Lab
extension-field boundaries (initial shapes / cutoff / view / sweep /
shots / rounds, Q11) and emits the ``GET /schema`` payload.

Single declaration point (ticket 4): the whitelists and
``SWEEPABLE_PARAMS`` are *declared here*; ``lab.ir`` and ``lab.scan``
import them back as derived views (the ticket-2 import edge is reversed
— schema depends only on the three core packages, no lab-internal
cycle). The 422 whitelist texts stay byte-identical (golden tests lock
them); UI teaching scales (label/tip/slider ranges/palette grouping)
stay in ops.js (Q2/Q6).
"""

from __future__ import annotations

import json
from typing import Any

from cvsim.bosonic import ir_schema as _bosonic_ir_schema
from cvsim.fock import ir_schema as _fock_ir_schema
from cvsim.gaussian import ir_schema as _gaussian_ir_schema

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

#: Per-backend **UI-hidden** core ops (ticket 4). The whitelist is now
#: *derived* as core ``ir_schema()`` ops minus this set — the declaration
#: states only the UI decision (ops the workbench deliberately keeps off
#: its palette/loader); a newly added core op requires no change here.
#:
#: - gaussian: v1-era deferrals kept off the v0-legacy Lab workbench
#:   (cz/cx/interferometer/phase_noise/gaussian_channel/mach_zehnder) +
#:   measure_threshold (B6 unlocked it for fock/bosonic only).
#: - fock: apply_unitary/apply_kraus (matrix editor deferred, F7
#:   anti-whitelist creed) + interferometer.
#: - bosonic: none — B6 unlocked the full gate/channel/measure set
#:   wholesale (no historical v0 UI restriction to honor).
_UI_HIDDEN: dict[str, frozenset[str]] = {
    "gaussian": frozenset(
        {
            "cx",
            "cz",
            "gaussian_channel",
            "interferometer",
            "mach_zehnder",
            "measure_threshold",
            "phase_noise",
        }
    ),
    "fock": frozenset({"apply_unitary", "apply_kraus", "interferometer"}),
    "bosonic": frozenset(),
}


def _derive_whitelist(backend: str) -> frozenset[str]:
    """Core ``ir_schema()`` op names minus the UI-hidden set (ticket 4).

    Module-level one-shot over op *names* (the per-package op set is
    static knowledge in a same-package/same-process world, Q7);
    :func:`assemble_schema` still re-calls ``ir_schema()`` for fresh full
    payloads. A hidden name without a core entry is exactly the drift
    class this ticket exists to kill — scream instead of silently
    shrinking the whitelist.
    """
    hidden = _UI_HIDDEN[backend]
    ops = set(_PKG_SCHEMAS[backend]()["ops"])
    unknown = hidden - ops
    if unknown:
        raise RuntimeError(
            f"UI-hidden ops {sorted(unknown)} not in {backend} core "
            "ir_schema — update _UI_HIDDEN after the core change"
        )
    return frozenset(ops - hidden)


#: Bosonic initial sources — derived from the bosonic core
#: ``ir_schema()`` initial registry (ticket 1 data-driven table; ticket 4
#: single declaration point — ``lab.ir._load_bosonic`` and
#: ``initial.js`` (via /schema) read this, no hand-written mirror).
BOSONIC_SOURCES: tuple[str, ...] = tuple(
    _PKG_SCHEMAS["bosonic"]()["initial"]["sources"]
)

#: Lab op whitelists (UI concept, ADR-0003 #3) — derived views over the
#: core snapshots (ticket 4), equal to the pre-ticket hand-written sets
#: (golden 422 texts stay byte-identical). Consumed by the ``lab.ir``
#: loader paths, ``lab.scan`` (sweepable pairing) and
#: ``server._whitelist_label``.
LAB_WHITELIST: frozenset[str] = _derive_whitelist("gaussian")
FOCK_WHITELIST: frozenset[str] = _derive_whitelist("fock")
BOSONIC_WHITELIST: frozenset[str] = _derive_whitelist("bosonic")

_WHITELISTS: dict[str, frozenset[str]] = {
    "gaussian": LAB_WHITELIST,
    "fock": FOCK_WHITELIST,
    "bosonic": BOSONIC_WHITELIST,
}

#: Real-numeric params sweepable by /scan (declaration moved here from
#: lab/scan.py, ticket 4 — single point; scan.py imports this back;
#: mirrors ops.js ``sweep`` metadata). Complex params (alpha) and
#: structural params (nmode) are excluded.
SWEEPABLE_PARAMS: dict[str, frozenset[str]] = {
    "squeeze": frozenset({"r"}),
    "phase": frozenset({"phi"}),
    "loss": frozenset({"T"}),
    "beamsplitter": frozenset({"theta"}),
    "two_mode_squeeze": frozenset({"r"}),
    "amplifier": frozenset({"G"}),
    "mz": frozenset({"theta", "phi"}),
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
    snapshots + the derived Lab whitelists + Lab extension declarations.

    Fresh deep-copy per call (the core snapshots are already per-call fresh;
    the whitelists are only read). JSON-native end to end.
    """
    pkg_schemas = {b: _PKG_SCHEMAS[b]() for b in BACKENDS}

    # per-op backend membership: derived whitelist (core − UI-hidden, so
    # every listed name has a core entry by construction), resolved to the
    # op's meta from its own package (first backend in BACKENDS order).
    ops: dict[str, Any] = {}
    for backend in BACKENDS:
        for op_name in sorted(_WHITELISTS[backend]):
            meta = pkg_schemas[backend]["ops"][op_name]
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
