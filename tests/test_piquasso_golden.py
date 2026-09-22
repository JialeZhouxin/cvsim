"""Golden tests vs piquasso 8.0.1: Fock composite / 3+ modes / PNR conditioning.

NO piquasso import at test time — the data is frozen in
``tests/_golden/piquasso_fock_composite_golden.npz`` by
``tools/gen_piquasso_golden.py`` (see ``docs/piquasso-golden-roundtrip.md``).

WHY THIS FILE EXISTS
--------------------
``tests/test_sf_golden_f6.py`` is the only pre-existing external oracle, and
``tests/_golden/sf_fock_golden.npz`` covers **8 cases, <=2 modes, no measurement,
no conditioning, no channel** — exactly the parts cvsim has closed forms for
anyway. This file covers what SF's golden does not:

  * 3-mode and 4-mode non-Gaussian gate chains
  * the PNR joint distribution of a 3-mode composite
  * PNR post-selection (conditioning) on a 3-mode composite

piquasso was qualified against cvsim's own closed forms first
(``tools/qualify_piquasso_oracle.py``: 43 checks, all <=1e-12, including exact
conditioning), so it is entitled to act as an oracle here.

TOLERANCE
---------
``atol=1e-8``, matching the SF golden convention. The residual is dominated by
the **cutoff-semantics mismatch**, not by either implementation being wrong:

  piquasso ``Config(cutoff=N)`` truncates on TOTAL photon number (``sum_i n_i < N``)
  cvsim truncates PER MODE (a dense ``(N,)*m`` tensor).

cvsim additionally RENORMALISES the truncated state (norm is exactly 1) while
piquasso does not, so agreement improves as ``N`` grows. Measured residuals at the
frozen cutoffs are recorded in the generator's diagnostics; the largest is 8.6e-9.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from cvsim.fock.circuit import FockCircuit
from cvsim.fock.observables import pnr_condition

_GOLDEN = np.load(Path(__file__).parent / "_golden" / "piquasso_fock_composite_golden.npz")

PIQUASSO_LOCK = "8.0.1"
ATOL = 1e-8

# --- case definitions, mirroring tools/gen_piquasso_golden.py ---------------
# BS sign: cvsim(theta, phi) == piquasso(-theta, -phi), which means the cvsim
# side uses the UNNEGATED values that the generator feeds to piquasso negated.

CHAIN3_A = [
    ("squeeze", 0, {"r": 0.3}),
    ("displace", 1, {"alpha": 0.25 * np.exp(1j * 0.4)}),
    ("kerr", 2, {"chi": 0.2}),
    ("bs", (0, 1), {"theta": 0.5, "phi": 0.0}),
    ("bs", (1, 2), {"theta": 0.4, "phi": 0.0}),
    ("kerr", 0, {"chi": 0.1}),
]

CHAIN4 = [
    ("squeeze", 0, {"r": 0.25}),
    ("kerr", 1, {"chi": 0.2}),
    ("bs", (0, 1), {"theta": 0.4, "phi": 0.0}),
    ("bs", (2, 3), {"theta": 0.35, "phi": 0.0}),
    ("kerr", 2, {"chi": 0.15}),
    ("bs", (1, 2), {"theta": 0.3, "phi": 0.0}),
]

CHAIN3_B = [
    ("squeeze", 0, {"r": 0.4}),
    ("kerr", 1, {"chi": 0.5}),
    ("bs", (0, 1), {"theta": 0.6, "phi": 0.0}),
    ("bs", (1, 2), {"theta": 0.5, "phi": 0.0}),
]

CUT_CHAIN3_A = 40
CUT_CHAIN4 = 32
CUT_CHAIN3_B = 28
POST_MODE = 1
POST_K = (0, 1, 2)


def build(ops, nmode: int, cutoff: int) -> FockCircuit:
    """cvsim circuit mirroring the frozen piquasso program."""
    c = FockCircuit(nmode, cutoff=cutoff)
    for kind, modes, prm in ops:
        if kind == "squeeze":
            c.squeeze(modes, r=prm["r"], phi=prm.get("phi", 0.0))
        elif kind == "displace":
            c.displace(modes, alpha=prm["alpha"])
        elif kind == "kerr":
            c.kerr(modes, chi=prm["chi"])
        elif kind == "bs":
            c.beamsplitter(modes[0], modes[1], theta=prm["theta"], phi=prm.get("phi", 0.0))
        else:  # pragma: no cover
            raise ValueError(f"unknown op {kind!r}")
    return c


# --- ket goldens ------------------------------------------------------------


def test_chain3_ket_non_gaussian():
    """3-mode non-Gaussian chain: S@0, D@1, K@2, BS(0,1), BS(1,2), K@0.

    The first case in the repo with 3 modes AND two different non-Gaussian
    elements. SF's golden tops out at 2 modes.
    """
    amps = build(CHAIN3_A, 3, CUT_CHAIN3_A).run().amps
    np.testing.assert_allclose(amps, _GOLDEN["chain3_ket"], atol=ATOL)


def test_chain4_ket_non_gaussian():
    """4-mode non-Gaussian chain — the widest circuit cvsim is anchored on."""
    amps = build(CHAIN4, 4, CUT_CHAIN4).run().amps
    np.testing.assert_allclose(amps, _GOLDEN["chain4_ket"], atol=ATOL)


# --- PNR distribution -------------------------------------------------------


def test_chain3_pnr_joint_probabilities():
    """Full 3-mode PNR joint distribution p(n0,n1,n2) of the composite."""
    amps = build(CHAIN3_B, 3, CUT_CHAIN3_B).run().amps
    prob = np.abs(amps) ** 2
    np.testing.assert_allclose(prob, _GOLDEN["chain3_pnr_joint"], atol=ATOL)


def test_chain3_pnr_joint_is_normalised():
    """cvsim renormalises the truncated state; the golden records piquasso's
    (unrenormalised) tensor. Both must sum to 1 within the cutoff residual."""
    golden = _GOLDEN["chain3_pnr_joint"]
    assert golden.sum() == pytest.approx(1.0, abs=1e-9)
    amps = build(CHAIN3_B, 3, CUT_CHAIN3_B).run().amps
    assert float(np.sum(np.abs(amps) ** 2)) == pytest.approx(1.0, abs=1e-12)


# --- conditioning (the core gap) --------------------------------------------


@pytest.mark.parametrize("k", POST_K)
def test_chain3_pnr_conditioned_joint(k):
    """PNR post-selection on mode 1 of the 3-mode composite.

    Conditioning is the feature with NO closed form in cvsim: the posterior is not
    a textbook formula once a Kerr gate has acted on a multi-mode state. This is
    the case the SF golden cannot reach, and the one that motivated the whole
    exercise.
    """
    full = build(CHAIN3_B, 3, CUT_CHAIN3_B).run()
    post = pnr_condition(full, mode=POST_MODE, n=k)
    p = np.abs(post.amps) ** 2
    p = p / p.sum()  # piquasso golden is normalised by the selection probability
    np.testing.assert_allclose(p, _GOLDEN[f"chain3_post_k{k}_joint"], atol=ATOL)


def test_chain3_post_selection_probabilities():
    """Selection probabilities P(n1=k) — an independent scalar anchor."""
    full = build(CHAIN3_B, 3, CUT_CHAIN3_B).run()
    amps = full.amps
    # marginal over mode 1
    marg = np.sum(np.abs(amps) ** 2, axis=(0, 2))
    np.testing.assert_allclose(marg[list(POST_K)], _GOLDEN["chain3_post_selprobs"], atol=ATOL)


def test_chain3_post_selection_probabilities_sum_to_one():
    """The full marginal must be a probability distribution."""
    amps = build(CHAIN3_B, 3, CUT_CHAIN3_B).run().amps
    marg = np.sum(np.abs(amps) ** 2, axis=(0, 2))
    assert float(marg.sum()) == pytest.approx(1.0, abs=1e-12)
    assert np.all(marg >= 0)


# --- metadata ---------------------------------------------------------------


def test_golden_metadata():
    """npz metadata records the piquasso version lock + the cutoff semantics."""
    meta = json.loads(_GOLDEN["metadata"].item().decode("utf-8"))
    assert meta["piquasso"] == PIQUASSO_LOCK
    assert meta["hbar"] == 1
    assert "TOTAL photon number" in meta["cutoff_semantics"]
    assert set(meta["cases"]) == {
        "chain3_ket",
        "chain4_ket",
        "chain3_pnr_joint",
        "chain3_post",
    }


def test_golden_shapes_match_declared_cutoffs():
    """Guards against a regeneration that silently changes a cutoff."""
    assert _GOLDEN["chain3_ket"].shape == (CUT_CHAIN3_A,) * 3
    assert _GOLDEN["chain4_ket"].shape == (CUT_CHAIN4,) * 4
    assert _GOLDEN["chain3_pnr_joint"].shape == (CUT_CHAIN3_B,) * 3
    # post-selection removes the measured mode: 3 modes -> 2
    assert _GOLDEN["chain3_post_k0_joint"].shape == (CUT_CHAIN3_B,) * 2
