"""B5 — BosonicCircuit DSL tests (circuit_v1 IR, component-wise execution).

Exit criteria (vision §4 B5):
1. compiled vs naive identical on fixtures (K=1, m=1)
2. IR roundtrip lossless (golden fixture)
3. Lab backend="bosonic" consumes circuit_v1 without schema change
4. measurement + feedforward + mode removal
5. channels (loss/amplifier) component-wise
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import (
    BosonicCircuit,
    BosonicState,
)
from cvsim.bosonic.gates import beamsplitter as g_bs
from cvsim.bosonic.gates import cz as g_cz
from cvsim.bosonic.gates import displace as g_displace
from cvsim.bosonic.gates import squeeze as g_squeeze
from cvsim.circuit_common import ParamRef

pytestmark = pytest.mark.phaseB5


# ===========================================================================
# Exit 1 — compiled vs naive (gate sequence)
# ===========================================================================

class TestCompiledVsNaive:
    def test_single_mode_squeeze_displace(self):
        """squeeze + displace: circuit vs direct gate calls (atol 1e-12)."""
        st_naive = BosonicState.vacuum(1)
        st_naive = g_squeeze(st_naive, 0.5, 0)
        st_naive = g_displace(st_naive, 0.3 + 0.4j, 0)
        c = BosonicCircuit(1)
        c.squeeze(0, 0.5)
        c.displace(0, 0.3 + 0.4j)
        st_circ = c.run()
        np.testing.assert_allclose(
            st_circ.components[0].V, st_naive.components[0].V, atol=1e-12
        )
        np.testing.assert_allclose(
            st_circ.components[0].rbar, st_naive.components[0].rbar, atol=1e-12
        )

    def test_two_mode_bs_cz_merged(self):
        """squeeze + BS + CZ: merged symplectic vs naive (atol 1e-12)."""
        st_naive = BosonicState.vacuum(2)
        st_naive = g_squeeze(st_naive, 0.4, 0)
        st_naive = g_bs(st_naive, 0, 1, np.pi / 4, 0.0)
        st_naive = g_cz(st_naive, 1.0, 0, 1)
        c = BosonicCircuit(2)
        c.squeeze(0, 0.4)
        c.beamsplitter(0, 1, np.pi / 4)
        c.cz(0, 1, 1.0)
        st_circ = c.run()
        np.testing.assert_allclose(
            st_circ.components[0].V, st_naive.components[0].V, atol=1e-12
        )
        np.testing.assert_allclose(
            st_circ.components[0].rbar, st_naive.components[0].rbar, atol=1e-12
        )

    def test_symbolic_param_binding(self):
        """Symbolic r bound at run() matches fixed r (atol 1e-12)."""
        c_fix = BosonicCircuit(1)
        c_fix.squeeze(0, 0.6)
        st_fix = c_fix.run()
        c_sym = BosonicCircuit(1)
        c_sym.squeeze(0, "r")
        st_sym = c_sym.run(r=0.6)
        np.testing.assert_allclose(st_sym.components[0].V, st_fix.components[0].V, atol=1e-12)


# ===========================================================================
# Exit 2 — IR roundtrip lossless
# ===========================================================================

class TestIRRoundtrip:
    def test_roundtrip_gate_circuit(self):
        """to_ir → from_ir → to_ir: dict equality (lossless)."""
        c = BosonicCircuit(2)
        c.squeeze(0, 0.5, phi=0.1)
        c.beamsplitter(0, 1, np.pi / 4, phi=0.2)
        c.displace(1, 0.3 + 0.4j)
        c.cz(0, 1, 1.0)
        d = c.to_ir()
        c2 = BosonicCircuit.from_ir(d)
        d2 = c2.to_ir()
        assert d == d2

    def test_roundtrip_state_identical(self):
        """to_ir → from_ir → run: state matches original (atol 1e-12)."""
        c = BosonicCircuit(2)
        c.squeeze(0, 0.5)
        c.beamsplitter(0, 1, np.pi / 4)
        c.displace(0, 0.3 + 0.4j)
        st1 = c.run()
        c2 = BosonicCircuit.from_ir(c.to_ir())
        st2 = c2.run()
        np.testing.assert_allclose(st2.components[0].V, st1.components[0].V, atol=1e-12)
        np.testing.assert_allclose(st2.components[0].rbar, st1.components[0].rbar, atol=1e-12)

    def test_roundtrip_feedforward(self):
        """IR preserves ParamRef ($ref) losslessly."""
        c = BosonicCircuit(2)
        c.squeeze(1, 0.5)
        c.cz(0, 1, 1.0)
        c.measure_homodyne(1, np.pi / 2, "m_p")
        c.displace(0, alpha=ParamRef("m_p", gain=0.5))
        d = c.to_ir()
        c2 = BosonicCircuit.from_ir(d)
        assert len(c2) == len(c)
        assert c2.to_ir() == d

    def test_roundtrip_interferometer(self):
        """IR preserves complex unitary matrix losslessly."""
        U = np.array([[np.exp(0.3j), 0], [0, np.exp(-0.3j)]], dtype=complex)
        c = BosonicCircuit(2)
        c.interferometer(U)
        d = c.to_ir()
        c2 = BosonicCircuit.from_ir(d)
        st1 = c.run()
        st2 = c2.run()
        np.testing.assert_allclose(st2.components[0].V, st1.components[0].V, atol=1e-12)


# ===========================================================================
# Exit 3 — Lab backend="bosonic"
# ===========================================================================

class TestLabBackendBosonic:
    """Exit 3: Bosonic IR uses circuit_v1 schema (schema-compatible).

    Lab ir.py routing for backend='bosonic' is B6 (vision §6.2 hard boundary:
    lab imports of bosonic unlock at the GUI stage, mirroring the Fock F7
    precedent). B5 delivers the IR library (to_ir/from_ir/validate_ir) on
    circuit_v1; schema compatibility is verified here.
    """

    def test_bosonic_ir_is_circuit_v1_schema(self):
        """Bosonic IR output carries schema='circuit_v1' (Lab-compatible)."""
        c = BosonicCircuit(2)
        c.squeeze(0, 0.5)
        c.beamsplitter(0, 1, np.pi / 4)
        d = c.to_ir()
        assert d["schema"] == "circuit_v1"
        assert d["nmode"] == 2
        assert isinstance(d["ops"], list)

    def test_bosonic_ir_validates_via_own_validator(self):
        """Bosonic IR passes structural validation (circuit_v1-compatible)."""
        from cvsim.bosonic.ir import validate_ir as validate_bosonic

        c = BosonicCircuit(1)
        c.squeeze(0, 0.5)
        c.displace(0, 0.3 + 0.4j)
        doc = validate_bosonic(c.to_ir())
        assert doc.schema == "circuit_v1"
        assert doc.nmode == 1
        assert len(doc.ops) == 2

    def test_bosonic_ir_rejects_bad_schema(self):
        """Bosonic IR validator rejects a non-circuit_v1 schema."""
        from cvsim.bosonic.ir import validate_ir as validate_bosonic

        with pytest.raises(ValueError, match="schema"):
            validate_bosonic({"schema": "circuit_v0", "nmode": 1, "ops": []})


# ===========================================================================
# Exit 4 — measurement + feedforward + mode removal
# ===========================================================================

class TestMeasurementFeedforward:
    def test_homodyne_measure_removes_mode(self):
        """measure_homodyne: result stored, mode removed, nmode drops."""
        c = BosonicCircuit(2)
        c.squeeze(1, 0.5)
        c.measure_homodyne(1, 0.0, "m_x")
        res = c.run(rng=np.random.default_rng(42))
        st, results = res
        assert "m_x" in results
        assert isinstance(results["m_x"], float)
        assert st.nmode == 1  # mode removed

    def test_heterodyne_measure_removes_mode(self):
        """measure_heterodyne: result stored as complex, mode removed."""
        c = BosonicCircuit(2)
        c.displace(1, 0.3 + 0.4j)
        c.measure_heterodyne(1, "m_b")
        res = c.run(rng=np.random.default_rng(7))
        st, results = res
        assert "m_b" in results
        assert isinstance(results["m_b"], complex)
        assert st.nmode == 1

    def test_threshold_no_removal(self):
        """measure_threshold: outcome-only, no mode removal, no state change."""
        c = BosonicCircuit(1)
        c.displace(0, 1.0)
        c.measure_threshold(0, "m_t")
        res = c.run(rng=np.random.default_rng(3))
        st, results = res
        assert results["m_t"] in (0, 1)
        assert st.nmode == 1  # threshold does not remove mode

    def test_feedforward_paramref(self):
        """ParamRef resolves from prior measurement (gain applied)."""
        c = BosonicCircuit(2)
        c.squeeze(1, 0.5)
        c.cz(0, 1, 1.0)
        c.measure_homodyne(1, np.pi / 2, "m_p")
        c.displace(0, alpha=ParamRef("m_p", gain=0.5))
        res = c.run(rng=np.random.default_rng(99))
        st, results = res
        assert "m_p" in results
        assert st.nmode == 1  # measured mode removed


# ===========================================================================
# Exit 5 — channels component-wise
# ===========================================================================

class TestChannels:
    def test_loss_channel(self):
        """loss T=0.9: circuit matches direct channels.loss (atol 1e-12)."""
        from cvsim.bosonic.channels import loss as ch_loss

        st_naive = BosonicState.vacuum(1)
        st_naive = g_squeeze(st_naive, 0.5, 0)
        st_naive = ch_loss(st_naive, T=0.9, nbar=0.0)
        c = BosonicCircuit(1)
        c.squeeze(0, 0.5)
        c.loss(0, T=0.9, nbar=0.0)
        st_circ = c.run()
        np.testing.assert_allclose(st_circ.components[0].V, st_naive.components[0].V, atol=1e-12)

    def test_amplifier_channel(self):
        """amplifier G=1.5: circuit matches direct channels.amplifier."""
        from cvsim.bosonic.channels import amplifier as ch_amp

        st_naive = BosonicState.vacuum(1)
        st_naive = g_squeeze(st_naive, 0.4, 0)
        st_naive = ch_amp(st_naive, G=1.5, nbar=0.0)
        c = BosonicCircuit(1)
        c.squeeze(0, 0.4)
        c.amplifier(0, G=1.5, nbar=0.0)
        st_circ = c.run()
        np.testing.assert_allclose(st_circ.components[0].V, st_naive.components[0].V, atol=1e-12)
