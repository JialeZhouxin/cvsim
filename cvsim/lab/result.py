"""LabResult — the unified Lab result snapshot (ADR-0008, payload-unification).

Single response contract for all three backend runners (``run_circuit`` /
``sample_circuit`` / ``run_fock_circuit`` / ``run_bosonic_circuit``): every
runner assembles a :class:`LabResult` and :func:`serialize` is the ONE place
that turns it into the JSON dict the endpoints return. Before this module the
gaussian path went RunResult → ``server._payload`` → dict while fock/bosonic
each hand-built payload dicts; the wigner ``{x, p, W}`` slice was repeated 4×
and the measured-outcome collector was fock-private (bosonic imported it
cross-package).

Two invariants hold by construction:

- **JSON-ready at construction** — every field is already a plain Python
  value (lists of floats, dicts, bools). A LabResult that exists cannot fail
  to serialize; :func:`serialize` is dumb assembly. Converters
  (:func:`_wigner_slice`, :func:`_measured_from_results`) live here as private
  helpers — they are result-shape knowledge, not per-backend knowledge.
- **Meter support matrix** — the keys each representation can honestly
  compute are *declared* below (core trio + per-representation extensions).
  Key sets are NOT aligned across backends: the differences are physical
  facts, never papered over with fabricated ``None``. Guards assert every
  backend's meters keys ⊆ the declared row.

This module sits at the bottom of the ``cvsim.lab`` dependency graph: it
imports only numpy, so ir.py / the three backends / server.py can all import
it with zero cycles. Response-side knowledge lives here (not in
``schema.py`` — that is the request-side assembly layer); ``schema.py``
embeds the matrix into ``GET /schema`` by reference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

#: Public core meters — every backend runner must be able to compute these
#: (or None where the state makes them undefined, e.g. purity of a
#: post-homodyne bosonic state; None is honest absence, fabricated data is not).
METER_CORE: frozenset[str] = frozenset({"purity", "mean_photon", "mean_photon_per_mode"})

#: Meter support matrix (ADR-0008 decision 3): per-backend extension keys on
#: top of ``METER_CORE``. gaussian: PPT log-negativity + singular-view flag;
#: fock: truncation leakage. bosonic has no extensions (its honest set is
#: exactly the core trio). Declared once, embedded into ``GET /schema`` by
#: ``schema.assemble_schema``; frontend consumption is a follow-up ticket (R6).
METER_EXTENSIONS: dict[str, frozenset[str]] = {
    "gaussian": frozenset({"log_negativity", "duan_sum", "singular"}),
    "fock": frozenset({"leakage"}),
    "bosonic": frozenset(),
}

#: Full supported set per backend (core ∪ extensions) — the guard reference.
METER_SUPPORT: dict[str, frozenset[str]] = {
    backend: METER_CORE | ext for backend, ext in METER_EXTENSIONS.items()
}

#: Public core keys of the LabResult contract (ADR-0008 decision 1). The
#: gaussian legacy response gains ``backend`` here (Q4: every payload
#: self-identifies; additive, tests updated in the same ticket).
#: (R6 closed 2026-09: frontend consumes the /schema matrix via
#: ``schema_store.meterKeys`` + ``renderMetersPanel`` — matrix-driven rows,
#: missing-key/None renders honest "—", per-mode ⟨n⟩ row added.)
LAB_RESULT_CORE_KEYS: frozenset[str] = frozenset(
    {"schema", "backend", "nmode", "wigner", "meters", "measured", "seed", "sampled"}
)


def _wigner_slice(
    w: tuple[np.ndarray, np.ndarray, np.ndarray] | None,
    axes: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Single wigner-grid → ``{x, p, W}`` JSON slice (the one legal copy of
    this knowledge in the repo; previously duplicated 4×). ``None`` passes
    through (singular view / empty state → honest null).

    ``axes`` is only present for a cross-mode plane (R8), which cannot be
    described by the ``{x, p}`` key names alone. Omitting the argument keeps the
    legacy byte shape — the default single-mode response is unchanged."""
    if w is None:
        return None
    X, P, W = w
    out: dict[str, Any] = {"x": X[0].tolist(), "p": P[:, 0].tolist(), "W": W.tolist()}
    if axes is not None:
        out["axes"] = axes
    return out


def _measured_from_results(raw: dict[str, Any], results: dict[str, Any]) -> list[dict[str, Any]]:
    """Measurement outcomes in node order (name-keyed results dict → list).

    Representation-agnostic by design (only walks raw ops + the results dict
    and converts complex/np JSON scalars) — promoted from fock_backend's
    private ``_fock_measured``, which bosonic wrongly imported cross-package.
    """
    out: list[dict[str, Any]] = []
    for node in raw.get("ops", []):
        if not isinstance(node, dict) or not node.get("op", "").startswith("measure_"):
            continue
        params = node.get("params") or {}
        name = params.get("name")
        if name is None or name not in results:
            continue
        val = results[name]
        if isinstance(val, complex):
            val = [val.real, val.imag]
        elif isinstance(val, np.generic):
            val = val.item()
        out.append({"op": node["op"], "mode": node["modes"][0], "name": name, "outcome": val})
    return out


@dataclass
class LabResult:
    """Unified Lab result snapshot (one per backend runner invocation).

    All fields are JSON-ready at construction — see the module docstring for
    why that is an invariant, not a convention. Per-representation extension
    payloads (fock ``cutoffs``/``dist``/``joint``, bosonic ``steps``) ride in
    :attr:`extensions` instead of widening this class into a junk drawer of
    always-None fields.

    ``seed``/``sampled`` are contract core keys carried as data (not serialize
    arguments) so a LabResult round-trips without external context; ``/run``
    mean-path results carry ``seed=None, sampled=False`` and serialize omits
    the falsy pair — byte-identical to the pre-unification responses.
    """

    backend: str
    nmode: int
    wigner: dict[str, Any] | None
    meters: dict[str, Any]
    measured: list[dict[str, Any]]
    extensions: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None
    sampled: bool = False


def serialize(result: LabResult, schema: str) -> dict[str, Any]:
    """LabResult → response dict (the single serializer, all endpoints).

    ``schema`` is the wire schema tag (``cvsim.lab.ir.SCHEMA``); it stays an
    argument so this module needs no import from ir.py (dependency bottom).
    ``seed``/``sampled`` are emitted only when set (sample path) — the mean
    path's payload has neither key, byte-identical to pre-unification.
    """
    payload: dict[str, Any] = {
        "schema": schema,
        "backend": result.backend,
        "nmode": result.nmode,
        "wigner": result.wigner,
        "meters": result.meters,
        "measured": result.measured,
        **result.extensions,
    }
    if result.seed is not None:
        payload["seed"] = result.seed
    if result.sampled:
        payload["sampled"] = True
    return payload


def check_meters(backend: str, meters: dict[str, Any]) -> None:
    """Guard: a backend's meters keys ⊆ its declared matrix row (R5).

    Structural, called from the runner assembly paths — an undeclared key
    means the matrix in this module was not updated with the runner and the
    drift the matrix exists to prevent has already happened.
    """
    unknown = set(meters) - METER_SUPPORT[backend]
    if unknown:
        raise RuntimeError(
            f"meters keys {sorted(unknown)} not declared in the meter support "
            f"matrix for backend {backend!r} — update result.py"
        )
