"""Golden Lab-response regression (payload-unification ticket, R7a).

The captured responses in ``responses/`` are the pre-refactor (dual-regime)
payloads served by all three backends. After the ADR-0008 switch every
endpoint assembles LabResult → ``serialize`` — these tests assert the served
JSON is byte-identical to the goldens, except the one declared additive
change (Q4: gaussian payloads gain ``backend: "gaussian"``).

Byte-identical means: same key set, same value types, same numeric repr —
floats come from the same deterministic pipeline (seed field drives the RNG),
so exact equality is expected and locks accidental wire-shape drift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "responses"
sys.path.insert(0, str(GOLDEN_DIR.parent))

from capture_golden import (  # noqa: E402
    BOSONIC_RUN,
    BOSONIC_SAMPLE,
    BOSONIC_STEPS,
    FOCK_BATCH_COUNTS,
    FOCK_BATCH_HISTO,
    FOCK_RUN,
    FOCK_SAMPLE,
    GAUSSIAN_RUN,
    GAUSSIAN_SAMPLE,
)

from cvsim.lab.server import app  # noqa: E402

client = TestClient(app)


def _golden(stem: str) -> dict[str, Any]:
    return json.loads((GOLDEN_DIR / f"{stem}.json").read_text(encoding="utf-8"))


def _assert_bytes_equal(body: dict[str, Any], stem: str) -> None:
    """Key-set + value equality (the JSON round-trip of 'byte-identical')."""
    golden = _golden(stem)
    assert set(body) == set(golden), (
        f"{stem}: key drift\n  got {sorted(body)}\n  want {sorted(golden)}"
    )
    assert body == golden, f"{stem}: value drift vs golden (run capture_golden.py to re-lock)"


def test_gaussian_run_golden():
    body = client.post("/run", json=GAUSSIAN_RUN).json()
    golden = _golden("gaussian_run")
    # Q4: the single declared additive change — gaussian self-identifies.
    assert "backend" not in golden
    assert body["backend"] == "gaussian"
    body_no_backend = {k: v for k, v in body.items() if k != "backend"}
    _assert_bytes_equal(body_no_backend, "gaussian_run")


def test_gaussian_sample_golden():
    body = client.post("/sample", json=GAUSSIAN_SAMPLE).json()
    assert body["backend"] == "gaussian"  # Q4 additive
    body_no_backend = {k: v for k, v in body.items() if k != "backend"}
    _assert_bytes_equal(body_no_backend, "gaussian_sample")


def test_fock_run_golden():
    _assert_bytes_equal(client.post("/run", json=FOCK_RUN).json(), "fock_run")


def test_fock_sample_golden():
    _assert_bytes_equal(client.post("/sample", json=FOCK_SAMPLE).json(), "fock_sample")


def test_fock_batch_histo_golden():
    _assert_bytes_equal(
        client.post("/batch", json={**FOCK_BATCH_HISTO, "shots": 200}).json(), "fock_batch_histo"
    )


def test_fock_batch_counts_golden():
    _assert_bytes_equal(
        client.post("/batch", json={**FOCK_BATCH_COUNTS, "shots": 50}).json(), "fock_batch_counts"
    )


def test_bosonic_run_golden():
    _assert_bytes_equal(client.post("/run", json=BOSONIC_RUN).json(), "bosonic_run")


def test_bosonic_run_steps_golden():
    _assert_bytes_equal(client.post("/run", json=BOSONIC_STEPS).json(), "bosonic_run_steps")


def test_bosonic_sample_golden():
    _assert_bytes_equal(client.post("/sample", json=BOSONIC_SAMPLE).json(), "bosonic_sample")


def test_golden_regen_guard():
    """The capture script must stay in sync with the goldens on disk
    (re-capturing into a dirty tree would silently re-lock drifted bytes)."""
    assert GOLDEN_DIR.is_dir() and len(list(GOLDEN_DIR.glob("*.json"))) == 9
    assert (GOLDEN_DIR.parent / "capture_golden.py").is_file()
