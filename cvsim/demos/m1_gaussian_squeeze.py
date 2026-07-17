"""M1 AC: vacuum → single-mode squeeze → print V; check det V and ⟨n⟩=sinh²r."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian import GaussianState, det_cov, mean_photon, squeeze

ATOL = 1e-10


def main() -> None:
    r = 0.8
    state = squeeze(GaussianState.vacuum(1), r=r, mode=0)
    V = state.V
    det = det_cov(state)
    n = mean_photon(state)
    n_exact = np.sinh(r) ** 2

    print("M1 Gaussian squeeze")
    print(f"  r = {r}")
    print(f"  V =\n{V}")
    print(f"  det(V) = {det}  (expect 0.25)")
    print(f"  <n>    = {n}  (expect sinh^2(r) = {n_exact})")

    # AC1.1 print V (above)
    # AC1.2 pure-state det
    assert abs(det - 0.25) < ATOL, f"det V={det} not ~1/4"
    # AC1.3 analytic <n>
    assert abs(n - n_exact) < ATOL, f"<n>={n} != sinh^2={n_exact}"
    # structure check: vacuum squeeze diagonal
    expect = 0.5 * np.diag([np.exp(-2 * r), np.exp(2 * r)])
    assert np.allclose(V, expect, atol=ATOL), "V not ½ diag(e^{-2r}, e^{2r})"

    print("OK: AC1.1–1.3 passed")


if __name__ == "__main__":
    main()
