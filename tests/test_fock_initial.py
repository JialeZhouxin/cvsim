"""F7 S2: FockCircuit initial-state API + IR ``initial`` field (atol 1e-12)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import FockCircuit, FockState
from cvsim.fock.ir import from_ir, to_ir, validate_ir

TOL = 1e-12


def test_initial_two_photon_matches_direct_fock2():
    """|1,1⟩ initial ≡ FockState.fock2 direct construction (atol 1e-12)."""
    c = FockCircuit(2, cutoff=8, initial=[1, 1])
    st = c.run()
    assert isinstance(st, FockState)
    assert st.amps.shape == (8, 8)
    direct = FockState.fock2(1, 1, 8)
    assert np.allclose(st.amps, direct.amps, atol=TOL)
    assert st.amps[1, 1] == 1.0
    assert np.sum(np.abs(st.amps) ** 2) == 1.0


def test_vacuum_default_unchanged():
    """initial=None (legacy files) ≡ vacuum, zero breakage."""
    c = FockCircuit(2, cutoff=6)
    st = c.run()
    assert st.amps[0, 0] == 1.0
    # explicit all-zero initial equals vacuum too
    c0 = FockCircuit(2, cutoff=6, initial=[0, 0])
    assert np.allclose(c0.run().amps, st.amps, atol=TOL)
    # to_ir omits all-zero initial (old files stay byte-equivalent)
    assert "initial" not in to_ir(FockCircuit(2, cutoff=6, initial=[0, 0]))


def test_initial_single_mode_and_gates():
    """initial works for 1-mode and gates act on it (displace |0⟩ → |1⟩ peak)."""
    c = FockCircuit(1, cutoff=10, initial=[2])
    st = c.displace(0, alpha=1e-9).run()
    assert np.argmax(np.abs(st.amps)) == 2


def test_initial_validation_fail_fast():
    with pytest.raises(ValueError, match="len"):
        FockCircuit(2, cutoff=8, initial=[1])  # wrong length
    with pytest.raises(ValueError, match="int"):
        FockCircuit(2, cutoff=8, initial=[1.5, 0])  # non-int
    with pytest.raises(ValueError, match=r"\[0, 8\)"):
        FockCircuit(2, cutoff=8, initial=[1, 8])  # n >= cutoff
    with pytest.raises(ValueError, match="int"):
        FockCircuit(2, cutoff=8, initial=[-1, 0])  # negative
    with pytest.raises(ValueError, match="list"):
        FockCircuit(2, cutoff=8, initial="11")  # not a list
    with pytest.raises(ValueError, match=r"\[0, 3\)"):
        # per-mode cutoffs: n_i validated against cutoffs[i]
        FockCircuit(2, cutoff=[8, 3], initial=[1, 3])


def test_initial_respects_per_mode_cutoffs():
    c = FockCircuit(2, cutoff=[8, 4], initial=[3, 2])
    st = c.run()
    assert st.amps.shape == (8, 4)
    assert st.amps[3, 2] == 1.0


def test_initial_iadd_mismatch_rejected():
    a = FockCircuit(2, cutoff=6, initial=[1, 1])
    b = FockCircuit(2, cutoff=6)  # vacuum
    with pytest.raises(ValueError, match="initial mismatch"):
        a += b
    c = FockCircuit(2, cutoff=6, initial=[1, 1])
    c.phase(0, theta=0.1)
    a += c  # same initial: OK
    assert len(a) == 1


def test_ir_roundtrip_with_initial():
    c = FockCircuit(2, cutoff=8, initial=[1, 1])
    c.beamsplitter(0, 1, theta=np.pi / 4)
    doc = to_ir(c)
    assert doc["initial"] == [1, 1]
    c2 = from_ir(doc)
    assert c2.initial == [1, 1]
    assert np.allclose(c2.run().amps, c.run().amps, atol=TOL)
    # IR validates initial too
    validate_ir(doc)
    validate_ir({**doc, "initial": [5, 0]})  # 5 < 8: valid
    with pytest.raises(ValueError, match="initial"):
        validate_ir({**doc, "initial": [9, 0]})  # 9 >= 8


def test_ir_legacy_no_initial_field_is_vacuum():
    """Old fock IR without initial field → vacuum (zero breakage)."""
    c = FockCircuit(2, cutoff=6)
    c.squeeze(0, r=0.3)
    doc = to_ir(c)
    assert "initial" not in doc
    st = from_ir(doc).run()
    assert np.allclose(st.amps, c.run().amps, atol=TOL)


def test_ir_accepts_lab_extension_fields():
    """view/seed/ui/backend top-level fields pass fock validate_ir (F7 bug fix)."""
    doc = to_ir(FockCircuit(1, cutoff=6))
    doc.update({"view": {"wigner_mode": 0}, "seed": 0, "ui": {}, "backend": "fock"})
    validate_ir(doc)  # must not raise
    c = from_ir(doc)
    assert c.nmode == 1


def test_initial_produces_exact_hom_bunching_zero():
    """HOM: |1,1⟩ + BS(π/4) → P(1,1)=0 (two-photon bunching), exact."""
    c = FockCircuit(2, cutoff=6, initial=[1, 1])
    c.beamsplitter(0, 1, theta=np.pi / 4)
    st = c.run()
    p = np.abs(st.amps) ** 2
    assert abs(p[1, 1]) < TOL
    assert abs(p[2, 0] - 0.5) < TOL and abs(p[0, 2] - 0.5) < TOL
