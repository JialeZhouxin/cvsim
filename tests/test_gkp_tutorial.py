"""GKP feedforward tutorial (Phase 5 C3) key numeric regressions.

Locks the numbers asserted inside tutorials/06_gkp_feedforward.ipynb:
readout ≈ ε, correction shrinks residual, residual std ≈ e^{-r}/√2.
"""

from __future__ import annotations

import numpy as np

from cvsim.gaussian import GaussianCircuit, ParamRef


def gkp_detect_correct(eps: float, r: float, gain: float = -1.0 / np.sqrt(2),
                       seed: int = 0) -> tuple[float, float]:
    c = GaussianCircuit(2)
    c.squeeze(0, r=r)                              # data: x-squeezed GKP|0> approx
    c.fourier(1); c.squeeze(1, r=r); c.fourier(1)  # ancilla: p-squeezed
    c.displace(0, alpha=eps / np.sqrt(2))          # inject x error eps
    c.cz(0, 1, weight=1.0)                         # propagate x1 -> p2
    c.measure_homodyne(1, phi=np.pi / 2, name="m_p")
    c.displace(0, alpha=ParamRef("m_p", gain=gain))  # feedforward correction
    st, res = c.compile().run(rng=np.random.default_rng(seed))
    return res["m_p"], st.rbar[0] * np.sqrt(2)


def test_readout_mean_tracks_error() -> None:
    # calibration: mean readout ≈ injected ε (200 seeds, r=2)
    eps, r = 0.2, 2.0
    readouts = [gkp_detect_correct(eps, r, gain=0.0, seed=s)[0]
                for s in range(200)]
    assert abs(np.mean(readouts) - eps) < 0.05
    # readout std ≈ e^{-r} (data squeeze noise + ancilla noise, independent)
    assert abs(np.std(readouts) - np.exp(-r)) < 0.3 * np.exp(-r)


def test_correction_reduces_residual() -> None:
    # same seed: corrected |x| strictly smaller than uncorrected
    for seed in range(8):
        _, x_nc = gkp_detect_correct(0.2, 2.0, gain=0.0, seed=seed)
        _, x_c = gkp_detect_correct(0.2, 2.0, gain=-1.0 / np.sqrt(2), seed=seed)
        assert abs(x_c) < abs(x_nc), f"seed={seed}: {x_c} vs {x_nc}"


def test_residual_std_tracks_e_minus_r() -> None:
    # residual std ≈ e^{-r}/√2 (readout noise floor), within 50% headroom
    for r in [1.0, 1.5, 2.0, 2.5]:
        xs = [gkp_detect_correct(0.2, r, seed=s)[1] for s in range(200)]
        theory = np.exp(-r) / np.sqrt(2)
        assert np.std(xs) < 1.5 * theory, f"r={r}: {np.std(xs)} vs {theory}"
        assert np.std(xs) > 0.5 * theory, f"r={r}: {np.std(xs)} vs {theory}"


def test_uncorrected_residual_stays_at_eps() -> None:
    # without correction the injected error survives: x_after ≈ ε (r=2, no readout noise in data? data x-noise σ=e^{-r}/√2=0.096, so allow 3σ)
    eps, r = 0.2, 2.0
    xs = [gkp_detect_correct(eps, r, gain=0.0, seed=s)[1] for s in range(50)]
    assert abs(np.mean(xs) - eps) < 3 * np.exp(-r) / np.sqrt(2)


def test_notebook_build_is_stable() -> None:
    # rebuilding from _build_06.py must reproduce the committed notebook
    import json
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, "tutorials/_build_06.py"],
                   cwd=root, check=True, capture_output=True)
    nb = json.loads((root / "tutorials/06_gkp_feedforward.ipynb").read_text(
        encoding="utf-8"))
    assert nb["nbformat"] == 4
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) == 4  # 1 helper def + 3 assert blocks
