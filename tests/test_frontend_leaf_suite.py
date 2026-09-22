"""Frontend leaf contract layer must be wired into CI (ADR-0009 / review §4.2).

The ``tests/*.test.mjs`` files are the *only* machine check on the static
JavaScript leaves, and they never ran in CI: pytest collects just
``test_*.py`` (``pyproject`` ``python_files``) and node's directory mode does
not pick up ``.mjs`` at all — ``node --test tests/`` dies with
``Cannot find module .../tests``. The layer was a local ritual that could rot
unnoticed, which is precisely the failure ADR-0009 exists to prevent.

Two silent-rot modes are guarded here:

1. **CI unwired** — someone deletes/renames the job or its command; the suite
   goes back to never running.
2. **Test uncollected** — a new leaf test is added somewhere the glob does not
   reach (e.g. ``tests/frontend/x.test.mjs``), so it exists but never runs.
   The flat ``tests/*.test.mjs`` glob cannot see subdirectories.

Stdlib only (no ``pyyaml``: it is not in the ``dev`` extra CI installs), so the
workflow is read as text. That is deliberate — a real YAML parse would be
tighter, but it would add a dependency to the CI job this test protects.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

#: The glob the CI job passes to ``node --test``, shell-expanded so a new leaf
#: test is picked up with no workflow edit.
CI_GLOB = "tests/*.test.mjs"


def _workflow_text() -> str:
    assert WORKFLOW.is_file(), f"missing workflow: {WORKFLOW}"
    return WORKFLOW.read_text(encoding="utf-8")


def _discover_leaf_tests() -> list[Path]:
    """Every ``*.test.mjs`` in the repo (any depth), excluding vendored dirs.

    Walks with pruning rather than ``rglob``: ``rglob`` descends into ``.venv``
    (tens of thousands of files) before the filter runs, which made this test
    take ~9s instead of milliseconds.
    """
    skip = {".venv", "node_modules", ".git", ".worktrees", "__pycache__"}
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in skip]
        out.extend(Path(dirpath) / f for f in filenames if f.endswith(".test.mjs"))
    return sorted(out)


def test_ci_runs_the_leaf_suite() -> None:
    """The workflow must invoke ``node --test`` on the leaf tests."""
    text = _workflow_text()
    assert "node --test" in text, (
        "ci.yml no longer runs `node --test` — the whole frontend leaf contract "
        "layer (ADR-0009) would stop being checked in CI"
    )
    assert CI_GLOB in text, (
        f"ci.yml must run `node --test {CI_GLOB}`: node's directory mode does not "
        f"collect .mjs, so the files have to be named explicitly (glob is "
        f"shell-expanded). Found no {CI_GLOB!r}."
    )


def test_ci_job_is_wired_to_its_own_glob() -> None:
    """The glob must live in a real job step, not a comment or a dead branch."""
    lines = _workflow_text().splitlines()
    hits = [
        (i, ln)
        for i, ln in enumerate(lines, 1)
        if "node --test" in ln and CI_GLOB in ln and not ln.strip().startswith("#")
    ]
    assert hits, f"no active (non-comment) `node --test {CI_GLOB}` step in ci.yml"
    # A `run:` must precede it within the same step block.
    for lineno, _ in hits:
        window = "\n".join(lines[max(0, lineno - 3) : lineno])
        assert "run:" in window, (
            f"ci.yml:{lineno}: `node --test` appears outside a `run:` step — "
            f"it would never execute"
        )


def test_every_leaf_test_is_reachable_by_the_ci_glob() -> None:
    """Every ``*.test.mjs`` must sit exactly at ``tests/<name>.test.mjs``.

    The CI glob is flat: a test dropped into a subdirectory would be silently
    uncollected and would rot without ever failing CI.
    """
    found = _discover_leaf_tests()
    assert found, "no *.test.mjs found at all — the leaf layer vanished"

    unreachable = [p for p in found if p.parent != REPO / "tests"]
    assert not unreachable, (
        "these leaf tests are NOT matched by the CI glob "
        f"{CI_GLOB!r} and would never run: "
        + ", ".join(str(p.relative_to(REPO)) for p in unreachable)
        + " — move them into tests/ or widen the CI command"
    )

    # And the glob must genuinely cover the directory (guards a typo'd pattern).
    assert len(found) == len(list((REPO / "tests").glob("*.test.mjs"))), (
        "discovery disagreed with the tests/ glob"
    )


def test_leaf_tests_are_real_and_import_a_leaf() -> None:
    """Each file must be a node test that imports a static leaf.

    Keeps the suite from passing vacuously: a file with no ``node:test`` import
    registers no tests, and node exits 0 on it.
    """
    for path in _discover_leaf_tests():
        src = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO)
        assert re.search(r'\bfrom\s+"node:test"', src) or 'require("node:test")' in src, (
            f"{rel}: does not import node:test — it registers no tests and would "
            f"pass silently"
        )
        assert re.search(r'"\.\.?/.*cvsim/lab/static/[^"]+\.js"', src), (
            f"{rel}: imports no ../cvsim/lab/static/*.js leaf, so it does not "
            f"test the frontend at all"
        )


def test_leaf_test_count_matches_documented_baseline() -> None:
    """Review §4.2/§4.3 says 9 leaf tests; §3.3 后是 12. Keep the number honest.

    Not a magic constant to bump blindly: if this fails, either a leaf test was
    added (good — update the docs' count) or one was dropped (check why).
    """
    n = len(_discover_leaf_tests())
    assert n == 12, (
        f"expected 12 leaf tests (9 per review §4.2/§4.3 + the 3 leaves extracted "
        f"in §3.3: backend_panels/scan_panel/chart_frame), found {n}. If you added "
        f"or removed one, update the count in "
        f"docs/review-09-18-module-boundaries.md (§4.2/§3.3) and here."
    )
