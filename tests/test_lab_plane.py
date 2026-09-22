"""Cross-mode Wigner plane + duan_sum acceptance (09-22-lab-wigner-plane).

Covers the wire contract end to end (``POST /run``) for the four ``view.plane``
presets, the honest-422 surface, and the AC12 singular-state function-layer
case that the v1 circuit path cannot reach.

Numbers are re-derived from the covariance matrix rather than copied from a
recorded run, so a physics regression fails here instead of being blessed.
"""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from cvsim.gaussian import GaussianState
from cvsim.lab.gaussian_backend import _build_result
from cvsim.lab.ir import View
from cvsim.lab.server import app

client = TestClient(app, raise_server_exceptions=False)

TMSV = [{"id": "t", "op": "two_mode_squeeze", "params": {"r": 0.8}, "modes": [0, 1]}]
SEPARABLE = [
    {"id": "a", "op": "squeeze", "params": {"r": 0.8, "phi": 0}, "modes": [0]},
    {"id": "b", "op": "squeeze", "params": {"r": 0.8, "phi": 0}, "modes": [1]},
]


def run(ops=None, view=None, nmode=2, backend=None):
    payload = {
        "schema": "circuit_v1", "seed": 0, "nmode": nmode,
        "ops": ops or [], "view": view or {"wigner_mode": 0, "lim": 5.0, "n": 16},
    }
    if backend:
        payload["backend"] = backend
    return client.post("/run", json=payload)


def plane_view(plane, modes=(0, 1), **kw):
    return {"wigner_mode": 0, "lim": 5.0, "n": 16, "plane": plane,
            "joint_modes": list(modes), **kw}


def covariance(kind: str) -> np.ndarray:
    """Independently reconstructed (4,4) xxpp covariance for the two scenes.

    ħ=1 in xxpp means the vacuum is ``I/2``, so the TMSV entries are
    ``cosh(2r)/2`` and ``sinh(2r)/2`` — the factors of 1/2 are the whole point
    of this helper: dropping them is a silent 2x physics error.

    Used by the diagonal checks below; the plane tests re-derive their own
    sub-covariance from the response's ``V`` so they stay independent of the
    construction used here.
    """
    c, s = np.cosh(1.6) / 2, np.sinh(1.6) / 2
    if kind == "tmsv":
        # xxpp ordering is [x0, x1, p0, p1]: the two-mode-squeezing correlations
        # live at V[0,1] (x0↔x1, positive) and V[2,3] (p0↔p1, negative). Putting
        # them at V[0,2] would be an x↔p mixup — it type-checks and is wrong.
        return np.array([
            [c, s, 0, 0],
            [s, c, 0, 0],
            [0, 0, c, -s],
            [0, 0, -s, c],
        ])
    e = np.exp(0.8)
    # two independent x-squeezed modes, xxpp blocks: [x0, x1, p0, p1]. Both modes
    # are squeezed identically, so the x-block is small and the p-block is large.
    return np.diag([e**-2 / 2, e**-2 / 2, e**2 / 2, e**2 / 2])


def test_covariance_helper_matches_backend():
    """The hand-built covariance must equal what the backend actually returns —
    otherwise the helper is a private fiction and the checks above are vacuous."""
    for kind, ops in (("tmsv", TMSV), ("separable", SEPARABLE)):
        V = np.array(run(ops, {"wigner_mode": 0, "lim": 5.0, "n": 16}).json()["V"], dtype=float)
        assert np.allclose(V, covariance(kind), atol=1e-12), kind


# --- AC3/AC4: the presets describe the plane the labels claim ---------------


def test_xx_plane_matches_hand_built_subcovariance():
    """xx plane: axes are (x0, x1) → C = V[[0,1]][:, [0,1]]."""
    r = run(TMSV, plane_view("xx"))
    assert r.status_code == 200, r.text
    V = np.array(r.json()["V"], dtype=float)
    C = V[np.ix_([0, 1], [0, 1])]
    # TMSV r=0.8: var(x0) = var(x1) = cosh(2r)/2 = 1.2887, corr = tanh(2r) = 0.9217
    assert C[0, 0] == pytest.approx(np.cosh(1.6) / 2, rel=1e-12)
    assert C[0, 1] == pytest.approx(np.sinh(1.6) / 2, rel=1e-12)
    assert C[0, 1] / np.sqrt(C[0, 0] * C[1, 1]) == pytest.approx(0.9217, abs=1e-4)


def test_pp_plane_is_anticorrelated():
    r = run(TMSV, plane_view("pp"))
    assert r.status_code == 200, r.text
    V = np.array(r.json()["V"], dtype=float)
    C = V[np.ix_([2, 3], [2, 3])]
    assert C[0, 1] == pytest.approx(-np.sinh(1.6) / 2, rel=1e-12)
    assert C[0, 1] / np.sqrt(C[0, 0] * C[1, 1]) == pytest.approx(-0.9217, abs=1e-4)


def test_epr_plane_is_squeezed_below_vacuum():
    """EPR rows carry 1/√2, so the vacuum reference stays 1/2 per axis."""
    # n must be ODD here: an even grid never samples the origin, so W.max() is
    # strictly below the prefactor and a "peak == prefactor" check would fail
    # for a reason that has nothing to do with the physics.
    r = run(TMSV, plane_view("epr", n=17))
    assert r.status_code == 200, r.text
    body = r.json()
    k, j = 0, 1
    V = np.array(body["V"], dtype=float)
    s = 1 / np.sqrt(2)
    A = np.array([[s, -s, 0, 0], [0, 0, s, s]])
    C = A @ V @ A.T
    assert np.linalg.det(C) == pytest.approx(0.010190550994591532, rel=1e-9)
    # axis std 0.31772 vs vacuum 0.70711 → visibly squeezed
    assert np.sqrt(C[0, 0]) == pytest.approx(0.31772356, abs=1e-6)
    assert np.sqrt(0.5) == pytest.approx(0.70710678, abs=1e-8)
    assert np.sqrt(C[0, 0]) < np.sqrt(0.5)
    # odd n ⇒ a grid point sits exactly on the mean, so the peak is the prefactor
    W = np.array(body["wigner"]["W"], dtype=float)
    assert body["wigner"]["x"][len(body["wigner"]["x"]) // 2] == 0.0
    assert W.max() == pytest.approx(1 / (np.pi * np.sqrt(np.linalg.det(2 * C))), rel=1e-12)


def test_presets_differ_from_single_and_from_each_other():
    """A plane selector that silently falls back to single would still pass a
    'returns 200' check, so compare the actual grids."""
    grids = {}
    for plane in ("single", "xx", "pp", "epr"):
        v = {"wigner_mode": 0, "lim": 5.0, "n": 16}
        if plane != "single":
            v.update(plane=plane, joint_modes=[0, 1])
        r = run(TMSV, v)
        assert r.status_code == 200, r.text
        grids[plane] = np.array(r.json()["wigner"]["W"], dtype=float)
    assert not np.array_equal(grids["xx"], grids["single"])
    assert not np.array_equal(grids["epr"], grids["single"])
    # xx and pp are the same TMSV seen through opposite signs of correlation:
    # C_pp = C_xx with the off-diagonal negated, so W_pp(q1,q2) = W_xx(q1,-q2).
    # Concretely the two pictures are single-axis mirror images (the grid is
    # symmetric under q1<->q2 so either axis does it), and NOT transposes —
    # a transposed implementation would be a real bug worth catching here.
    assert not np.array_equal(grids["xx"], grids["pp"])
    assert np.allclose(grids["xx"], grids["pp"][:, ::-1]), "xx must mirror pp in q2"
    assert not np.allclose(grids["xx"], grids["pp"].T), "xx/pp must not be transposes"
    # both are symmetric: the 45°-rotated EPR axes are their eigenvectors
    assert np.allclose(grids["xx"], grids["xx"].T)
    assert np.allclose(grids["pp"], grids["pp"].T)


# --- AC7: axes metadata + unchanged x/p payload -----------------------------


def test_axes_present_only_for_cross_mode_planes():
    r = run(TMSV, {"wigner_mode": 0, "lim": 5.0, "n": 16})
    assert "axes" not in r.json()["wigner"], "single plane must stay byte-compatible"
    for plane, labels in (
        ("xx", ["x0", "x1"]),
        ("pp", ["p0", "p1"]),
        ("epr", ["(x0−x1)/√2", "(p0+p1)/√2"]),
    ):
        body = run(TMSV, plane_view(plane)).json()
        axes = body["wigner"]["axes"]
        assert axes["plane"] == plane
        assert axes["modes"] == [0, 1]
        assert axes["labels"] == labels


def test_grid_axis_vectors_are_unchanged_by_plane():
    """x/p keys keep carrying the linspace coordinates (frontend reads them)."""
    body = run(TMSV, plane_view("epr")).json()["wigner"]
    expected = np.linspace(-5.0, 5.0, 16).tolist()
    assert body["x"] == pytest.approx(expected)
    assert body["p"] == pytest.approx(expected)


def test_plane_on_three_modes_accepts_non_adjacent_pair():
    r = run(TMSV, plane_view("epr", modes=(0, 2)), nmode=3)
    assert r.status_code == 200, r.text
    assert r.json()["wigner"]["axes"]["modes"] == [0, 2]


# --- AC8: duan_sum ----------------------------------------------------------


def test_duan_sum_reference_values():
    """vacuum 2.0, separable > 2, TMSV r=0.8 = 0.4038 (EPR criterion < 2)."""
    for kind, ops, expect in (
        ("vacuum", None, 2.0),
        ("separable", SEPARABLE, 5.1549289423897715),
        ("tmsv", TMSV, 0.4037930359893105),
    ):
        body = run(ops, plane_view("xx")).json()
        assert body["meters"]["duan_sum"] == pytest.approx(expect, abs=1e-3), kind
    # entangled < 2 <= separable — the physical meaning of the number
    entangled = run(TMSV, plane_view("xx")).json()["meters"]["duan_sum"]
    separable = run(SEPARABLE, plane_view("xx")).json()["meters"]["duan_sum"]
    assert entangled < 2.0 <= separable


def test_duan_sum_is_on_demand_not_a_null_placeholder():
    """R-A2: no pair → key absent (a None placeholder would break the goldens)."""
    body = run(TMSV, {"wigner_mode": 0, "lim": 5.0, "n": 16}).json()
    assert "duan_sum" not in body["meters"]
    with_pair = run(TMSV, plane_view("xx")).json()
    assert "duan_sum" in with_pair["meters"]


def test_duan_sum_absent_when_a_pair_mode_is_measured_away():
    """A pair that stops naming two live modes must not be silently recomputed."""
    ops = [*TMSV, {"id": "h", "op": "measure_homodyne",
                   "params": {"phi": 0, "name": "h0"}, "modes": [0]}]
    r = run(ops, {"wigner_mode": 0, "lim": 5.0, "n": 16, "joint_modes": [0, 1]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nmode"] == 1
    assert "duan_sum" not in body["meters"]


# --- AC11: honest 422 for every malformed plane request --------------------


@pytest.mark.parametrize("tag,view,nmode,backend,needle", [
    ("missing pair", {"wigner_mode": 0, "plane": "epr"}, 2, None, "requires view.joint_modes"),
    ("unknown preset", {"wigner_mode": 0, "plane": "zz"}, 2, None, "must be one of"),
    ("pair out of range", plane_view("xx", modes=(0, 5)), 2, None, "out of range"),
    ("plane needs 2 modes", plane_view("xx"), 1, None, "requires nmode >= 2"),
    ("fock rejects plane", plane_view("epr"), 2, "fock", "only supported by the gaussian"),
    ("bosonic rejects plane", plane_view("xx"), 2, "bosonic", "only supported by the gaussian"),
])
def test_plane_rejections_are_422(tag, view, nmode, backend, needle):
    r = run(None, view, nmode=nmode, backend=backend)
    assert r.status_code == 422, f"{tag}: got {r.status_code} {r.text[:200]}"
    assert needle in r.json()["detail"], f"{tag}: {r.json()['detail']!r}"


def test_pair_oob_is_422_not_a_silent_500():
    """_plane_axes raises CircuitV0Error, which subclasses ValueError — if it is
    called inside the singular-view try block it degrades to a fake 200, and if
    the pair is consumed without validation it becomes a 500. Lock the 422."""
    r = run(None, plane_view("xx", modes=(5, 7)))
    assert r.status_code == 422, r.text
    assert "out of range" in r.json()["detail"]


def test_same_mode_pair_and_negative_pair_rejected_at_load():
    for modes in ([1, 1], [0, -1], [0], [0, 1, 2]):
        r = run(None, {"wigner_mode": 0, "plane": "xx", "joint_modes": modes})
        assert r.status_code == 422, f"{modes}: {r.status_code}"


def test_single_plane_still_tolerates_an_unused_oob_pair():
    """Backward compatibility: with plane="single" the pair is not the plot's
    coordinates, so an out-of-range pair stays ignored (200) rather than
    turning into a new error class — but it must not fabricate duan_sum."""
    r = run(TMSV, {"wigner_mode": 0, "lim": 5.0, "n": 16, "joint_modes": [5, 7]})
    assert r.status_code == 200, r.text
    assert "duan_sum" not in r.json()["meters"]


# --- AC12: singular state is a function-layer fact --------------------------


def test_singular_state_has_no_wigner_and_says_so():
    """The v1 circuit path cannot produce a singular view (homodyne removes the
    conditioned mode outright), so assert the contract at the function layer."""
    V = np.array([[0.5, 0.0], [0.0, 0.0]])  # det V = 0
    state = GaussianState(V=V, rbar=np.zeros(2))
    result = _build_result(state, View(wigner_mode=0, lim=5.0, n=16), [])
    assert result.wigner is None, "singular state must not fabricate a grid"
    assert result.meters["singular"] is True
    assert result.meters["purity"] is None
    # mean_photon stays computable and honest
    assert result.meters["mean_photon"] is not None
