"""Bosonic-representation consistency contract (Phase 5 C4).

Two layers (grill Q5):
1. **合同固化** — Bosonic 表示约定从文档变测试：vacuum 单分量、
   加权矩公式、loss 权重不变、单分量 == GaussianState。
2. **桥锚定** — cat / GKP 的 ⟨x⟩、Var(x) 三向对照：
   Bosonic 加权矩 == bridge 解析闭式 == Fock 截断数值。

纠缠量跨表示（log-neg 截断收敛）不做：ponytail — 需 Fock 密度矩阵
表示，见 cvsim/bridge.py docstring。
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import bridge
from cvsim.bosonic import (
    BosonicState,
    even_cat,
    gkp0,
    gkp1,
    loss,
    odd_cat,
)
from cvsim.bosonic.observables import (
    homodyne_mean,
    homodyne_var,
    weight_sum,
)
from cvsim.conventions import vacuum_cov, vacuum_mean
from cvsim.gaussian import GaussianState
from cvsim.gaussian.gates import apply_symplectic
from cvsim.gaussian.observables import homodyne_mean as g_hmean
from cvsim.gaussian.observables import homodyne_var as g_hvar
from cvsim.symplectic import S_squeeze

# ---------------------------------------------------------------------------
# 合同固化 1: vacuum 单分量
# ---------------------------------------------------------------------------


def test_vacuum_single_component() -> None:
    v = BosonicState.vacuum(2)
    assert v.n_components == 1
    c = v.components[0]
    np.testing.assert_allclose(c.V, vacuum_cov(2), atol=1e-12)
    np.testing.assert_allclose(c.rbar, vacuum_mean(2), atol=1e-12)
    assert c.w == 1.0


# ---------------------------------------------------------------------------
# 合同固化 2: 加权矩公式（手算 Σ wᵢ·μᵢ 对照 API）
# ---------------------------------------------------------------------------


def test_weighted_moment_formula() -> None:
    cat = even_cat(1.5)
    u = np.zeros(2, dtype=complex)
    u[0] = 1.0  # x quadrature, mode 0, phi=0
    mu_manual = sum(c.w * (u @ c.rbar) for c in cat.components).real
    x2_manual = sum(
        c.w * (float(u.real @ c.V @ u.real) + abs(u @ c.rbar) ** 2)
        for c in cat.components
    ).real
    assert abs(homodyne_mean(cat, 0, 0.0) - mu_manual) < 1e-12
    assert abs(homodyne_var(cat, 0, 0.0) - (x2_manual - mu_manual**2)) < 1e-12


def test_weight_sum_normalized() -> None:
    for st in (even_cat(1.0), odd_cat(1.0), gkp0(), gkp1()):
        assert abs(weight_sum(st) - 1.0) < 1e-12


# ---------------------------------------------------------------------------
# 合同固化 3: loss 不改变权重（分量 V/r̄ 按 X V Xᵀ + Y 变换）
# ---------------------------------------------------------------------------


def test_loss_weights_unchanged() -> None:
    cat = even_cat(1.5)
    w_before = [c.w for c in cat.components]
    T = 0.7
    after = loss(cat, T)
    w_after = [c.w for c in after.components]
    assert len(after.components) == len(cat.components)
    for wb, wa in zip(w_before, w_after, strict=True):
        assert abs(wb - wa) < 1e-12
    # per-component transformation X V Xᵀ + Y with X=√T·I, Y=(1−T)·½I
    for c_b, c_a in zip(cat.components, after.components, strict=True):
        np.testing.assert_allclose(
            c_a.V, T * c_b.V + (1.0 - T) * 0.5 * np.eye(2), atol=1e-12
        )
        np.testing.assert_allclose(c_a.rbar, np.sqrt(T) * c_b.rbar, atol=1e-12)


# ---------------------------------------------------------------------------
# 合同固化 4: 单分量 == Gaussian（from_gaussian 桥）
# ---------------------------------------------------------------------------


def test_single_component_equals_gaussian() -> None:
    g = apply_symplectic(
        GaussianState.vacuum(2),
        S_squeeze(2, r=np.log(2.0), mode=1),  # x→x/2 on mode 1 (xxpp)
        np.zeros(4),
    )
    b = BosonicState.from_gaussian(g)
    assert b.n_components == 1
    for phi in (0.0, np.pi / 4, np.pi / 2):
        np.testing.assert_allclose(
            homodyne_mean(b, 1, phi), g_hmean(g, 1, phi), atol=1e-12
        )
        np.testing.assert_allclose(
            homodyne_var(b, 1, phi), g_hvar(g, 1, phi), atol=1e-12
        )


# ---------------------------------------------------------------------------
# 桥锚定: cat ⟨x⟩/Var(x) 三向（Bosonic == bridge 解析 == Fock 截断）
# ---------------------------------------------------------------------------


def _fock_cat(alpha: float, even: bool, cutoff: int) -> np.ndarray:
    """Fock amplitudes of (|α⟩ ± |−α⟩)/√N via bridge coherent_element."""
    o = np.exp(-2.0 * alpha**2)
    norm = np.sqrt(2.0 * (1.0 + (1.0 if even else -1.0) * o))
    amps = np.zeros(cutoff, dtype=complex)
    for n in range(cutoff):
        amps[n] = (
            bridge.coherent_element(n, alpha)
            + (1.0 if even else -1.0) * bridge.coherent_element(n, -alpha)
        ) / norm
    return amps


def _x_ops(cutoff: int) -> tuple[np.ndarray, np.ndarray]:
    """⟨n|x̂|m⟩ and ⟨n|x̂²|m⟩ matrices (ħ=1)."""
    X = np.zeros((cutoff, cutoff))
    X2 = np.zeros((cutoff, cutoff))
    for m in range(cutoff):
        X[m, m - 1] += np.sqrt(m) / np.sqrt(2) if m > 0 else 0.0
        if m + 1 < cutoff:
            X[m, m + 1] += np.sqrt(m + 1) / np.sqrt(2)
    X2 = X @ X
    return X, X2


@pytest.mark.parametrize("even", [True, False])
def test_cat_mean_and_var_three_way(even: bool) -> None:
    alpha = 1.5
    st = even_cat(alpha) if even else odd_cat(alpha)
    # 1) Bosonic weighted moments
    mu_b = homodyne_mean(st, 0, 0.0)
    var_b = homodyne_var(st, 0, 0.0)
    # 2) bridge analytic closed form:
    #    ⟨x̂²⟩ = [(1+4α²) ± o] / [2(1 ± o)], o = ⟨α|−α⟩ = e^{−2α²}; ⟨x̂⟩ = 0 by symmetry
    o = np.exp(-2.0 * alpha**2)
    sign = 1.0 if even else -1.0
    mu_a, var_a = 0.0, ((1.0 + 4.0 * alpha**2) + sign * o) / (2.0 * (1.0 + sign * o))
    # 3) Fock truncated numerics (cutoff 40, tail < 1e-9 for α=1.5)
    cutoff = 40
    amps = _fock_cat(alpha, even, cutoff)
    X, X2 = _x_ops(cutoff)
    mu_f = float((amps.conj() @ X @ amps).real)
    var_f = float((amps.conj() @ X2 @ amps).real - mu_f**2)
    for tag, got in (("mu", mu_b), ("var", var_b)):
        np.testing.assert_allclose(got, mu_a if tag == "mu" else var_a,
                                   atol=1e-8, err_msg=f"bosonic vs analytic {tag}")
    np.testing.assert_allclose(mu_b, mu_f, atol=1e-8, err_msg="mean vs Fock")
    np.testing.assert_allclose(var_b, var_f, atol=1e-8, err_msg="var vs Fock")


# ---------------------------------------------------------------------------
# 桥锚定: GKP ⟨x⟩（对称性 / 半周期平移解析锚）+ 加权矩手算
# ---------------------------------------------------------------------------


def test_gkp0_mean_symmetric_zero() -> None:
    st = gkp0()  # 1d x-teeth, symmetric under x → −x
    mu_b = homodyne_mean(st, 0, 0.0)
    assert abs(mu_b) < 1e-8
    # weighted-sum manual recompute
    u = np.zeros(2, dtype=complex)
    u[0] = 1.0
    mu_manual = sum(c.w * (u @ c.rbar) for c in st.components).real
    assert abs(mu_b - mu_manual) < 1e-12


def test_gkp1_mean_half_period_anchor() -> None:
    # |1⟩_GKP = |0⟩_GKP shifted by δ/2 = √(2π)/2 in x
    st = gkp1()
    np.testing.assert_allclose(
        homodyne_mean(st, 0, 0.0), np.sqrt(2.0 * np.pi) / 2.0, atol=1e-6
    )
    # variance identical to gkp0 (pure shift)
    np.testing.assert_allclose(
        homodyne_var(st, 0, 0.0), homodyne_var(gkp0(), 0, 0.0), atol=1e-12
    )
