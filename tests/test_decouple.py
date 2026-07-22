"""Decouple: B ↛ G; shared symplectic; duck from_gaussian."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from cvsim.bosonic import BosonicState
from cvsim.conventions import vacuum_cov, vacuum_mean
from cvsim.symplectic import S_squeeze


def test_duck_from_gaussian():
    duck = SimpleNamespace(
        V=vacuum_cov(1),
        rbar=vacuum_mean(1).astype(complex),
    )
    st = BosonicState.from_gaussian(duck)
    assert st.n_components == 1
    assert abs(st.components[0].w - 1.0) < 1e-15
    assert np.allclose(st.components[0].V, vacuum_cov(1))


def test_shared_symplectic_import():
    S = S_squeeze(1, 0.3)
    from cvsim.gaussian.symplectic import S_squeeze as S2

    assert np.allclose(S, S2(1, 0.3))


def test_bosonic_source_no_gaussian_import():
    root = Path(__file__).resolve().parents[1] / "cvsim" / "bosonic"
    bad = []
    for p in root.rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        if "cvsim.gaussian" in text:
            bad.append(str(p.relative_to(root.parent.parent)))
    assert bad == [], f"bosonic still imports gaussian: {bad}"
