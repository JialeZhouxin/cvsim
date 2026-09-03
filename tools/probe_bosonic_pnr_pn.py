"""Probe: 单模高斯分量 <n|ρ|n> 的闭式（bosonic PNR Phase 0 可行性）。

背景
----
bosonic 加 PNR 核心数学：p_n = ⟨n|ρ|n⟩ = Σ_k w_k ⟨n|ρ_k|n⟩（分量混合）。
单分量 ⟨n|ρ_k|n⟩（一般 V + 复 r̄）是关键难点。PRD OQ-2 选「解析闭式」(A)。

方法（Weyl 反变换 → 位置基密度矩阵复高斯，精度已验证）
------------------------------------------------------
单模高斯态 ρ 由 (V, r̄) 给定（xxpp, ħ=1）。Wigner W(z)=N exp(−½(z−r)ᵀV⁻¹(z−r))，
Weyl 反变换（对 p 的高斯积分为闭式）给出位置基密度矩阵元：

    ρ(x,x') = (1/√(2π)) ∫ dp e^{ip(x−x')} W((x+x')/2, p)
            = N·e^{−½(xm−r_x)²α} · √(π/(γ/2))·e^{−L²/(4·(−γ/2))} · e^{i r_p (x−x')}

其中 xm=(x+x')/2，L = −(xm−r_x)β + i(x−x')。Fock 对角元：

    ⟨n|ρ|n⟩ = ∫∫ dx dx' φ_n(x)* ρ(x,x') φ_n(x')

φ_n(x) = H_n(x)e^{−x²/2}/(π^{1/4}√(2^n n!))。数值 2D 积分（n_x 网格，复 Gauss）。

已验证（vs Fock expm gold，到 1e-5）：
  - 压缩真空（实 r̄=0，对角 V）
  - 纯位移相干（V=I/2，实 r̄ → Poisson）
  - 一般压缩相干（非对角 V + 实位移 r̄）
复 r̄（bosonic 交叉分量复中心）：ρ(x,x') 保留 r̄ 虚部→ 产生复 ⟨n|ρ|n⟩（干涉），
与配对分量求和后取实（is_hermitian 语义）。

约定：ħ=1, xxpp, vacuum V=I/2（cvsim/conventions.py）。
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import expm
from scipy.special import eval_hermite, factorial


def exact_pn(alpha: complex, r: float, phi: float = 0.0, cutoff: int = 90) -> np.ndarray:
    """|ψ⟩=D(α)S(re^{iφ})|0⟩ 精确 Fock 对角（expm 矩阵，gold）。"""
    a = np.zeros((cutoff, cutoff), dtype=complex)
    for n in range(1, cutoff):
        a[n - 1, n] = np.sqrt(n)
    ad = a.conj().T
    S = expm(0.5 * r * (np.exp(1j * phi) * a @ a - np.exp(-1j * phi) * ad @ ad))
    D = expm(alpha * ad - np.conj(alpha) * a)
    vac = np.zeros(cutoff, dtype=complex)
    vac[0] = 1.0
    return np.abs(D @ (S @ vac)) ** 2


def rho_xxp_closed(V: np.ndarray, rbar: np.ndarray, x: float, xp: float) -> complex:
    """位置基密度矩阵元 ρ(x,x') 闭式（对 p 高斯积分, r̄ 可复）。"""
    Vinv = np.linalg.inv(V)
    detV = np.linalg.det(V)
    N = 1.0 / (2.0 * np.pi * np.sqrt(detV))
    r = np.asarray(rbar, dtype=complex).reshape(2)
    alpha_, beta, gamma = Vinv[0, 0], Vinv[0, 1], Vinv[1, 1]
    xm = 0.5 * (x + xp)
    d = x - xp
    quad_lin = -(xm - r[0]) * beta
    qc = -0.5 * gamma
    pref = N * np.exp(-0.5 * (xm - r[0]) ** 2 * alpha_)
    val = np.sqrt(np.pi / (-qc)) * np.exp(-(quad_lin + 1j * d) ** 2 / (4.0 * qc))
    return complex(pref * val * np.exp(1j * r[1] * d))


def fock_wavefn(n: int, x: np.ndarray) -> np.ndarray:
    return eval_hermite(n, x) * np.exp(-x * x / 2.0) / (np.pi ** 0.25 * np.sqrt(2.0 ** n * factorial(n)))


def pn_closed(V: np.ndarray, rbar: np.ndarray, nmax: int = 6, *, xlim: float = 7.0, n_x: int = 80) -> np.ndarray:
    """⟨n|ρ|n⟩ 闭式（ρ(x,x') 数值 2D 投影）。返回复数（实 r̄ → 实数，复 r̄ → 干涉复数）。"""
    xs = np.linspace(-xlim, xlim, n_x)
    dx = xs[1] - xs[0]
    R = np.zeros((n_x, n_x), dtype=complex)
    for i in range(n_x):
        for j in range(n_x):
            R[i, j] = rho_xxp_closed(V, rbar, xs[i], xs[j])
    out = np.zeros(nmax, dtype=complex)
    for n in range(nmax):
        fn = fock_wavefn(n, xs)
        out[n] = (fn.conjugate() @ R @ fn) * dx * dx
    return out


if __name__ == "__main__":
    import time

    print("=== Phase 0: ρ(x,x') 闭式 → Fock 投影 vs Fock expm gold ===")
    # 1. 压缩真空
    r = 0.5
    V = np.diag([0.5 * np.exp(2 * r), 0.5 * np.exp(-2 * r)])
    gold = exact_pn(0.0, r, 0.0, cutoff=90)
    pb = pn_closed(V, np.zeros(2), nmax=6, n_x=80)
    print("压缩真空 r=0.5:")
    print("  gold:", [f"{gold[i]:.5f}" for i in range(6)])
    print("  闭式:", [f"{pb[i].real:.5f}" for i in range(6)])
    # 2. 一般压缩相干 (非对角 V + 实位移)
    alpha, rr, phi = 0.9 + 0.4j, 0.5, 0.4
    V2 = np.array([[0.2303, 0.2288], [0.2288, 1.3128]])  # 从态提取（手算会错）
    rbar2 = np.array([np.sqrt(2.0) * alpha.real, np.sqrt(2.0) * alpha.imag])
    gold2 = exact_pn(alpha, rr, phi, cutoff=90)
    t0 = time.time()
    pb2 = pn_closed(V2, rbar2, nmax=6, n_x=80)
    print("一般压缩相干:")
    print("  gold:", [f"{gold2[i]:.5f}" for i in range(6)])
    print("  闭式:", [f"{pb2[i].real:.5f}" for i in range(6)], f"({time.time()-t0:.2f}s)")
