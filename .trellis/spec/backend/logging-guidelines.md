# Output & Debugging Conventions

> When code may print or log. (`cvsim` has no logging infrastructure — this file documents the actual conventions.)

---

## Overview

`cvsim` is a **library**: no `logging` calls, no `print` inside library modules. Output is allowed in exactly two places:

1. `cvsim/demos/*.py` — milestone self-checks (run via `python -m cvsim.demos.mX_*`)
2. The FastAPI lab server — framework-managed (uvicorn access logs), no custom logging config

---

## Library Modules: Zero Side-Effect Output

`grep` for `print(` / `logging` in `cvsim/gaussian/`, `cvsim/fock/`, `cvsim/bosonic/` returns nothing. Keep it that way:

- No `print()` for debugging — remove before commit (self-check list in `CODE_REVIEW_GUIDE.md` §1.2: "没有 print() 调试残余").
- No `logging` module — nothing in the codebase uses it yet.
- Return data to callers; let demos/tests present it.

## Demos: Print the Numbers You're Proving

`cvsim/demos/m1_gaussian_squeeze.py` … `m4_cross_rep.py`, `user_acceptance.py` print the milestone figures (means, variances, cross-representation comparisons) plus pass/fail lines, then exit. Pattern:

- `print()` is fine in demos; that is their job.
- Each demo ends with an explicit check summary and non-zero exit on failure (AC scripts).

## Lab Server: Use Framework Defaults

`cvsim/lab/server.py` adds no logging configuration; uvicorn's default access/error logs are the convention. If the server ever needs structured logs:

- Add stdlib `logging` to `server.py` only — never to library modules.
- Follow the existing minimal style: no third-party log formatters.

---

## Anti-Patterns

| Pattern | Why it fails here |
|---------|-------------------|
| `print()` in `cvsim/gaussian|fock|bosonic` | Library impurity; breaks `pytest -q` output and review checklist |
| Adding a logging framework now | Zero users; YAGNI until server actually needs structured logs |
| Debug prints left in lab JS + Python | Same rule as backend: remove before commit |

## Verification

```bash
grep -rn "print(\|logging" cvsim/gaussian cvsim/fock cvsim/bosonic   # expect nothing
ruff check cvsim/
```
