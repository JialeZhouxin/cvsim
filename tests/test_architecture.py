"""Architecture contract (ADR-0001): representation packages stay isolated.

AST-based — the test parses sources, never imports cvsim.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CVSIM = REPO / "cvsim"

REP_PACKAGES = ("cvsim.gaussian", "cvsim.fock", "cvsim.bosonic")
ALLOWED_ROOT_IMPORTS = (
    "cvsim.conventions",
    "cvsim.symplectic",
    "cvsim.circuit_common",  # ADR-0004: 共享 DSL 核（gaussian/fock 共用）
)
FORBIDDEN_IMPORTS = ("cvsim.lab", "cvsim.demos", "cvsim.wigner")


def _cvsim_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "cvsim":
                    out.append("cvsim")  # bare import: allowlist violation
                elif a.name.startswith("cvsim."):
                    out.append(a.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module == "cvsim":
                # `from cvsim import lab` → cvsim.lab, no bypass
                out.extend(f"cvsim.{a.name}" for a in node.names)
            else:
                out.append(node.module)
        elif isinstance(node, ast.ImportFrom) and node.level >= 2:
            out.append("cvsim")  # relative import crossing into parent
    return out


def _rep_modules():
    for pkg in REP_PACKAGES:
        pkg_dir = CVSIM / pkg.split(".")[-1]
        for py in sorted(pkg_dir.glob("**/*.py")):
            yield py, pkg


@pytest.mark.parametrize("path,pkg", list(_rep_modules()), ids=lambda v: str(v))
def test_rep_packages_isolated(path: Path, pkg: str) -> None:
    imports = _cvsim_imports(path)
    for other in REP_PACKAGES:
        if other == pkg:
            continue
        assert not any(i == other or i.startswith(other + ".") for i in imports), (
            f"{path} imports {other} (cross-rep forbidden)"
        )
    for bad in FORBIDDEN_IMPORTS:
        assert not any(i == bad or i.startswith(bad + ".") for i in imports), (
            f"{path} imports {bad} (forbidden)"
        )
    for i in imports:
        if (i == "cvsim" or i.startswith("cvsim.")) and not i.startswith(pkg + "."):
            assert i in ALLOWED_ROOT_IMPORTS, f"{path} imports {i} outside allowlist"


@pytest.mark.parametrize("pkg", REP_PACKAGES)
def test_rep_package_has_modules(pkg: str) -> None:
    """Guard against silent-pass: empty/missing dir would parametrize to zero."""
    pkg_dir = CVSIM / pkg.split(".")[-1]
    assert any(pkg_dir.glob("*.py")), f"{pkg_dir} missing or empty"
