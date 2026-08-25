"""Phase F6 golden tests: Fock vs Strawberry Fields fock backend (no SF import).

Reads ``tests/_golden/sf_fock_golden.npz`` — generated once by
``tools/gen_sf_golden.py`` inside an SF venv (SF 0.23.0 / thewalrus 0.22.0,
2026-08-12). Every check is a full *complex* density-matrix comparison
(relative phase included), atol=1e-9.

cvsim ``FockDensity.rho`` — (N^m, N^m) complex, C-order — is compared
element-wise against SF ``state.dm()``, which doubles as the
density-export-format check (vision F6 exit criterion 3 /
docs/sf-roundtrip-fock.md).

BS sign mapping (empirically verified full-tensor, max|d|=1.1e-16):
cvsim ``beamsplitter(theta, phi)`` == SF ``BSgate(-theta, -phi)`` — the
cvsim side below uses negated BS parameters.
"""

from pathlib import Path

import numpy as np

from cvsim.fock.density import FockDensity
from cvsim.fock.gates import (
    beamsplitter,
    displace,
    kerr,
    phase,
    squeeze,
    two_mode_squeeze,
)
from cvsim.fock.state import FockState

SF_LOCK = "SF 0.23.0 / thewalrus 0.22.0"
GEN_DATE = "2026-08-12"

_GOLDEN = np.load(Path(__file__).parent / "_golden" / "sf_fock_golden.npz")


def _check(rho: np.ndarray, key: str) -> None:
    np.testing.assert_allclose(rho, _GOLDEN[key], atol=1e-9)


def test_squeezed_r05():
    """S(0.5)|0> dm — SF fock backend cutoff 50 (2026-08-12)."""
    rho = FockDensity.from_pure(FockState.squeezed(50, 0.5)).rho
    _check(rho, "squeezed_r05")


def test_displaced():
    """D(0.4,0.3)|0> = |0.4 e^{0.3i}> dm — SF cutoff 12 (2026-08-12)."""
    rho = FockDensity.from_pure(displace(FockState.vacuum(12), 0.4 * np.exp(1j * 0.3))).rho
    _check(rho, "displaced")


def test_rotated():
    """R(0.6)|1> dm — SF cutoff 10 (2026-08-12)."""
    rho = FockDensity.from_pure(phase(FockState.fock(1, 10), 0.6)).rho
    _check(rho, "rotated")


def test_kerr():
    """K(0.1)|1> dm — SF cutoff 10 (2026-08-12)."""
    rho = FockDensity.from_pure(kerr(FockState.fock(1, 10), 0.1)).rho
    _check(rho, "kerr")


def test_bs_11():
    """BS(pi/4,0.2)|1,1> dm — cvsim beamsplitter(-pi/4,-0.2) (BS sign mapping)."""
    rho = FockDensity.from_pure(beamsplitter(FockState.fock2(1, 1, 10), -np.pi / 4, -0.2)).rho
    _check(rho, "bs_11")


def test_s2_00():
    """S2(0.5)|0,0> ket — SF cutoff 30 (2026-08-12)."""
    amps = two_mode_squeeze(FockState.vacuum(30, 2), 0.5).amps.ravel()
    _check(amps, "s2_00")


def test_chain():
    """Same physical experiment — S(0.4)@m0, D(0.3,0.2)@m0, D(0.2,0.5)@m1,
    BS(0.8,0.4), K(0.1)@m1; SF cutoff 45; cvsim BS params negated; ket storage
    (2026-08-12).
    """
    st = FockState.vacuum(45, 2)
    st = squeeze(st, 0.4, mode=0)
    st = displace(st, 0.3 * np.exp(1j * 0.2), mode=0)
    st = displace(st, 0.2 * np.exp(1j * 0.5), mode=1)
    st = beamsplitter(st, -0.8, -0.4)
    st = kerr(st, 0.1, mode=1)
    _check(st.amps.ravel(), "chain")


def test_thermal_dm():
    """Thermal nbar=1.0 dm — SF cutoff 10 (2026-08-12)."""
    rho = FockDensity.thermal(10, 1.0).rho
    _check(rho, "thermal_dm")


def test_golden_metadata():
    """npz metadata records the SF/thewalrus version lock + generation date."""
    import json

    meta = json.loads(_GOLDEN["metadata"].item().decode("utf-8"))
    assert meta["strawberryfields"] == "0.23.0"
    assert meta["thewalrus"] == "0.22.0"
    assert meta["engine"] == "fock"
    assert meta["generated"] == GEN_DATE
    assert set(meta["cases"]) == {
        "squeezed_r05",
        "displaced",
        "rotated",
        "kerr",
        "bs_11",
        "s2_00",
        "chain",
        "thermal_dm",
    }
