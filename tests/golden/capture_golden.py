"""Golden Lab-response capture (payload-unification ticket, R7a).

Posts representative circuits for all three backends to the live FastAPI app
(before the LabResult refactor) and stores each raw JSON response under
``tests/golden/responses/``. Re-run with ``--check`` to compare byte-for-byte
(tests/test_lab_golden.py does this via its own runner, not this CLI).

Scenes (deterministic: seed field drives the RNG, no wall-clock inputs):
- gaussian  /run + /sample   (main scene: TMSV + loss + BS, heterodyne sample)
- fock      /run + /sample + /batch ×2 branches (histogram + measured-counts)
- bosonic   /run + /sample + /run detail=steps (GKP QEC round + steps view)

Every circuit is a fixed dict in this file — no fixtures, no drift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # GBK console guard

from fastapi.testclient import TestClient  # noqa: E402

from cvsim.lab.server import app  # noqa: E402

GOLDEN_DIR = Path(__file__).resolve().parent / "responses"

GAUSSIAN_RUN = {
    "schema": "circuit_v1",
    "nmode": 2,
    "seed": 0,
    "ops": [
        {"id": "s0", "op": "two_mode_squeeze", "modes": [0, 1], "params": {"r": 0.6}},
        {"id": "l0", "op": "loss", "modes": [0], "params": {"T": 0.8, "nbar": 0.0}},
        {
            "id": "bs",
            "op": "beamsplitter",
            "modes": [0, 1],
            "params": {"theta": np.pi / 4, "phi": 0.0},
        },
    ],
    "view": {"wigner_mode": 0, "lim": 5.0, "n": 32},
    "ui": {},
}

GAUSSIAN_SAMPLE = {
    **GAUSSIAN_RUN,
    "seed": 7,
    "ops": GAUSSIAN_RUN["ops"]
    + [{"id": "h", "op": "measure_heterodyne", "modes": [0], "params": {"name": "m0"}}],
}

FOCK_RUN = {
    "schema": "circuit_v1",
    "backend": "fock",
    "nmode": 2,
    "cutoff": 10,
    "initial": [1, 1],
    "seed": 0,
    "ops": [
        {"id": "bs", "op": "beamsplitter", "modes": [0, 1], "params": {"theta": np.pi / 4}},
    ],
    "view": {"wigner_mode": 0, "lim": 5.0, "n": 32, "joint_modes": [0, 1]},
    "ui": {},
}

FOCK_SAMPLE = {**FOCK_RUN, "seed": 42}

FOCK_BATCH_HISTO = {**FOCK_RUN, "seed": 0}

FOCK_BATCH_COUNTS = {
    **FOCK_RUN,
    "seed": 1,
    "view": {"wigner_mode": 0, "lim": 5.0, "n": 32},
    "ops": [
        {"id": "bs", "op": "beamsplitter", "modes": [0, 1], "params": {"theta": np.pi / 4}},
        {"id": "n0", "op": "measure_pnr", "modes": [0], "params": {"name": "n0"}},
        {"id": "n1", "op": "measure_pnr", "modes": [1], "params": {"name": "n1"}},
    ],
}

BOSONIC_RUN = {
    "schema": "circuit_v1",
    "backend": "bosonic",
    "nmode": 1,
    "initial": ["gkp0"],
    "seed": 0,
    "ops": [
        {"id": "sq", "op": "squeeze", "modes": [0], "params": {"r": 0.2, "phi": 0.0}},
        {"id": "l0", "op": "loss", "modes": [0], "params": {"T": 0.9, "nbar": 0.0}},
    ],
    "view": {"wigner_mode": 0, "lim": 5.0, "n": 32},
    "ui": {},
}

BOSONIC_SAMPLE = {
    **BOSONIC_RUN,
    "seed": 3,
    "ops": BOSONIC_RUN["ops"]
    + [{"id": "h", "op": "measure_homodyne", "modes": [0], "params": {"phi": 0.0, "name": "m0"}}],
}

BOSONIC_STEPS = {**BOSONIC_RUN, "detail": "steps"}


def _scenes() -> list[tuple[str, str, dict]]:
    """(filename stem, endpoint, body) — every golden response captured here."""
    return [
        ("gaussian_run", "/run", GAUSSIAN_RUN),
        ("gaussian_sample", "/sample", GAUSSIAN_SAMPLE),
        ("fock_run", "/run", FOCK_RUN),
        ("fock_sample", "/sample", FOCK_SAMPLE),
        ("fock_batch_histo", "/batch", {**FOCK_BATCH_HISTO, "shots": 200}),
        ("fock_batch_counts", "/batch", {**FOCK_BATCH_COUNTS, "shots": 50}),
        ("bosonic_run", "/run", BOSONIC_RUN),
        ("bosonic_run_steps", "/run", BOSONIC_STEPS),
        ("bosonic_sample", "/sample", BOSONIC_SAMPLE),
    ]


def capture() -> dict[str, int]:
    client = TestClient(app)
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for stem, endpoint, body in _scenes():
        r = client.post(endpoint, json=body)
        assert r.status_code == 200, f"{stem}: {endpoint} → {r.status_code} {r.text[:300]}"
        payload = r.json()
        (GOLDEN_DIR / f"{stem}.json").write_text(
            json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        counts[stem] = r.status_code
    return counts


if __name__ == "__main__":
    results = capture()
    for name, status in sorted(results.items()):
        print(f"{name}: {status}")
    print(f"captured {len(results)} golden responses → {GOLDEN_DIR}")
