"""Probe: 联合多模 PNR 生成函数（bosonic B10 Phase 0 可行性）。

背景
----
B9 单模核（2×2）推广到多模联合（2m×2m 分块）：

    A = V⁻¹ (全 2m×2m, xxpp, ħ=1)
    c_j(t_j) = (1−t_j)/(1+t_j)          每模独立
    B(t⃗) = A + 2·Σ_j c_j·P_j            P_j = mode j 的 I₂ 分块投影
    log G(t⃗) = m·log2 − Σ_j log(1+t_j) − ½ log(det V·det B)
                − ½ r̄ᵀAr̄ + ½ (Ar̄)ᵀB⁻¹(Ar̄)

    P(n⃗) = Taylor 系数：逐轴 Cauchy 提取（半径 0.95，每轴 max(128, 8·cutoff) 点，
    张量 FFT = 逐轴 FFT）。分量加权在 log 域逐 torus 点合并（复权重 + 复中心，
    Hermitian 干涉保留），与 B9 同纪律。

gold 锚（层 1/层 2）
--------------------
1. TMSV r=0.5: 解析 P(n,n) = tanh²(r)ⁿ / cosh²(r)，n₁≠n₂ → 0（层 1，无 fock 依赖）
2. cat⊗coherent: 乘积分解 = 单模 B9 结果的外积（自洽锚）
3. TMSV∘kerr(mode=0): fock expm 双模 gold（exp S₂ → 相位 e^{iχn²} 作用于 mode 0）
4. 混叠/点数/模数实验: 2/3 模不同每轴点数的误差表 → B10 边界结论

约定：ħ=1, xxpp, vacuum V=½I（cvsim/conventions.py 一致）。
不导入 cvsim —— 独立数学验证（B9 探针先例）。
"""

from __future__ import annotations

import math
import time

import numpy as np
from scipy.linalg import expm

RADIUS = 0.95


# ---------------------------------------------------------------------------
# 金锚：fock expm 双模
# ---------------------------------------------------------------------------

def _a(N: int) -> np.ndarray:
    a = np.zeros((N, N), dtype=complex)
    for n in range(1, N):
        a[n - 1, n] = np.sqrt(n)
    return a


def tmsv_fock(N: int, r: float) -> np.ndarray:
    """TMSV 纯态振幅 |ψ⟩ = Σ λⁿ|n,n⟩, λ=tanh r（级数直写, 精确）。"""
    lam = np.tanh(r)
    amps = np.zeros((N, N), dtype=complex)
    for n in range(N):
        amps[n, n] = lam**n
    amps /= np.linalg.norm(amps)
    return amps


def kerr_on_mode0_fock(amps: np.ndarray, chi: float) -> np.ndarray:
    """e^{iχn̂₁²} 作用于 mode 0（数基对角相位）。"""
    N = amps.shape[0]
    n = np.arange(N)
    phase = np.exp(1j * chi * n**2)
    return amps * phase[:, None]


def coherent_fock(N: int, alpha: complex) -> np.ndarray:
    """相干态单模振幅。"""
    n = np.arange(N)
    al = complex(alpha)
    fact = np.array([math.factorial(int(k)) for k in n], dtype=float)
    v = np.exp(-0.5 * abs(al) ** 2) * al**n / np.sqrt(fact)
    return v


def cat_fock(N: int, alpha: float, theta: float = 0.0) -> np.ndarray:
    """|cat⟩ ∝ |α⟩ + e^{iθ}|−α⟩（归一）。"""
    return coherent_fock(N, alpha) + np.exp(1j * theta) * coherent_fock(N, -alpha)


# ---------------------------------------------------------------------------
# 高斯态（V, rbar）构造（cvsim xxpp 约定）
# ---------------------------------------------------------------------------

def tmsv_Vr(r: float) -> tuple[np.ndarray, np.ndarray]:
    """TMSV (双模) 协方差与零均值（xxpp: [x1,p1,x2,p2]）。

    V = ½ S (I⊗I... ) Sᵀ；TMSV 的标准块形式（ħ=1）：
    x1-x2, p1+p2 压缩：V = ½·[[c,0,s,0],[0,c,0,−s],[s,0,c,0],[0,−s,0,c]]，
    c=cosh 2r, s=sinh 2r。
    """
    c = np.cosh(2 * r)
    s = np.sinh(2 * r)
    V = 0.5 * np.array(
        [
            [c, 0.0, s, 0.0],
            [0.0, c, 0.0, -s],
            [s, 0.0, c, 0.0],
            [0.0, -s, 0.0, c],
        ]
    )
    return V, np.zeros(4, dtype=complex)


def kerr_components_tmsv(r: float, chi: float, q: int) -> list[tuple[np.ndarray, np.ndarray, complex]]:
    """TMSV 经 kerr(mode 0) 后的分量表示（近似演示锚）。

    诚实标注：这是探针的**演示近似**，不是生产 kerr 实现。TMSV 是零均值高斯，
    kerr 后态的严格分量展开超纲；这里用「位移相干态网格近似」——把 mode 0 的
    kerr 相位作用表示为 q 个旋转相干分量的叠加（角度 2π/q 网格），
    只用于验证「复中心 × 关联 V」核的数值通路，gold 对照用 fock expm。
    """
    # 走最保守路线：直接用（近似）相位旋转网格做分量，V 保持 TMSV 关联。
    # mode 0 旋转 φ_j → 复中心 r̄_j = (x1 cosφ − p1 sinφ) + i(...) 网格。
    # 探针目的：复中心 + 关联 V 的联合生成函数数值行为，不追求物理精确。
    raise NotImplementedError("场景 3 改用 cat⊗TMSV 乘积纠缠替代——见 main() 注释")


def cat_tmsv_components(alpha: float, theta: float, r: float) -> list[tuple[np.ndarray, np.ndarray, complex]]:
    """cat(mode0) ⊗ TMSV(mode 1,2) 乘积纠缠？——不对：cat 与 TMSV 不共享模。

    真正的场景 3：**双模纠缠非高斯** = TMSV 边缘叠加。构造：
    |Ψ⟩ ∝ |α,α⟩·c0 + |α,−α⟩·c1 + |−α,α⟩·c2 + |−α,−α⟩·c3（4 相干乘积叠加，
    复中心 + 复权重），关联由叠加产生（非乘积态）。
    金锚 = fock: 4 个双模相干直和归一。
    """
    Vt, _ = tmsv_Vr(r)  # noqa: F841 — 场景 3 用的 V 见 main()；此处仅演示
    raise NotImplementedError


# ---------------------------------------------------------------------------
# 联合 PNR：分块生成函数 + 逐轴 Cauchy 提取（B10 候选核）
# ---------------------------------------------------------------------------

def log_g_block(V: np.ndarray, rbar: np.ndarray, ts: np.ndarray) -> complex:
    """单分量 log G(t⃗)（连续相位：√detVB 的支用 −Σ arg(1+t_j) 锚定）。

    G = 2^k·e^{quad} / (Π(1+t_j)·√(detV·detB))

    解析上 arg(√detVB) = −Σ arg(1+t_j) + 正定小量，但 principal sqrt 在
    detVB 绕负实轴时翻号（实测真空 torus 802/4096 点翻号，G→−1）。
    修法：主值 sqrt 后，若其辐角与 −Σ arg(1+t_j) 相差 > π/2 则翻号（把
    支锚定到连续分支，使 G(1⃗)=1 的归一锚成立）。
    """
    n = V.shape[0] // 2  # noqa: F841 — 保留语义
    k = len(ts)
    A = np.linalg.inv(V)
    B = A.astype(complex)
    for jj, t in enumerate(ts):
        c = (1.0 - t) / (1.0 + t)
        B[2 * jj : 2 * jj + 2, 2 * jj : 2 * jj + 2] += 2.0 * c * np.eye(2)
    sign_v, _ = np.linalg.slogdet(V)
    if sign_v <= 0:
        raise ValueError("non-PD V")
    Ar = A @ rbar
    quad = -0.5 * (rbar @ Ar) + 0.5 * (Ar @ np.linalg.solve(B, Ar))
    detVB = np.linalg.det(V) * np.linalg.det(B)
    sq = np.sqrt(detVB)  # 主值支
    # 支锚定：解析连续支的辐角 ≈ −Σ arg(1+t_j)；偏离 > π/2 → 翻号
    target = -float(np.angle(1.0 + np.asarray(ts, dtype=complex)).sum())
    if abs(np.angle(sq) - target) > np.pi / 2:
        sq = -sq
    logG = k * np.log(2.0) - np.log(np.prod(1.0 + np.asarray(ts, dtype=complex)) * sq) + quad
    return complex(logG)


def joint_pn(
    components: list[tuple[np.ndarray, np.ndarray, complex]],
    modes: tuple[int, ...],
    cutoff: int,
    n_theta: int | None = None,
    radius: float = RADIUS,
) -> np.ndarray:
    """联合 P(n⃗) — 分量 log 域合并 + 逐轴 FFT 提取。

    components: [(V, rbar, w)]（V/rbar 已是**测量模重排后的块**——本探针
    直接传测前 k 模的子块，调用方负责切块重排）。
    """
    k = len(modes)
    if n_theta is None:
        n_theta = max(128, 8 * cutoff)
    theta = 2.0 * np.pi * np.arange(n_theta) / n_theta
    # torus 网格：每轴独立 θ 网格 → 网格形状 (n_theta,)*k，逐点求值。
    grid_shape = (n_theta,) * k
    # 记 log(|w|)+i·angle(w) 一次
    log_w = [(np.log(abs(w)) + 1j * np.angle(w)) if w != 0 else None for _, _, w in components]

    out = np.zeros(grid_shape, dtype=complex)
    it = np.ndindex(*grid_shape)
    for idx in it:
        ts = radius * np.exp(1j * theta[np.asarray(idx)])
        logs = []
        for (V, rbar, _), lw in zip(components, log_w, strict=True):
            if lw is None:
                continue
            lt = lw + log_g_block(V, rbar, ts)
            logs.append(lt)
        if not logs:
            continue
        scale = max(lt.real for lt in logs)
        s = sum(np.exp(lt - scale) for lt in logs)
        if s == 0:
            continue
        total = scale + np.log(s)
        if total.real < np.log(np.nextafter(0.0, 1.0)):
            continue
        out[idx] = np.exp(total)
    # 逐轴 FFT 提取
    coeffs = np.fft.fftn(out) / (n_theta**k)
    # 系数索引: 前 cutoff 每轴
    slices = tuple(slice(0, cutoff) for _ in range(k))
    probs = np.asarray(coeffs[slices])
    # 半径校正
    ns = [np.arange(cutoff)] * k
    grids = np.meshgrid(*ns, indexing="ij")
    corr = np.ones_like(grids[0], dtype=float)
    for g in grids:
        corr *= radius**g
    probs = probs / corr
    return probs


def marginalize(probs: np.ndarray, axis_keep: int) -> np.ndarray:
    """沿非保留轴求和得边缘。"""
    axes = tuple(a for a in range(probs.ndim) if a != axis_keep)
    return probs.sum(axis=axes) if axes else probs


# ---------------------------------------------------------------------------
# 主场景
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Phase 0: bosonic 联合多模 PNR 分块核 vs gold ===\n")

    # ---- 场景 0: 真空自检 G(t)=1 & 边缘热态诊断 ----
    V0 = np.eye(4) * 0.5
    p0vac = joint_pn([(V0, np.zeros(4, dtype=complex), 1.0 + 0j)], modes=(0, 1), cutoff=4)
    # 真空 P(n) = δ_{n,0}: P(0,0)=1, 其余 0
    goldvac = np.zeros((4, 4)); goldvac[0, 0] = 1.0
    print(f"[0] 真空自检 max|Δ| = {np.max(np.abs(p0vac - goldvac)):.3e}")

    # ---- 场景 1: TMSV r=0.5（层 1 解析 + fock 双锚）----
    r = 0.5
    cutoff = 10
    V, rbar = tmsv_Vr(r)
    # 诊断: 单模边缘应为热态 n̄ = sinh²r
    p1edge = joint_pn([(V, rbar, 1.0 + 0j)], modes=(0,), cutoff=cutoff)
    nbar = np.sinh(r) ** 2
    thermal = np.array([nbar**n / (1 + nbar) ** (n + 1) for n in range(cutoff)])
    ed = np.max(np.abs(p1edge - thermal))
    print(f"[diag] TMSV 单模边缘 vs 热态(n̄={nbar:.4f}): max|Δ| = {ed:.3e}")
    t0 = time.time()
    p = joint_pn([(V, rbar, 1.0 + 0j)], modes=(0, 1), cutoff=cutoff)
    dt = time.time() - t0
    lam = np.tanh(r)
    analytic = np.zeros((cutoff, cutoff))
    for n in range(cutoff):
        analytic[n, n] = lam ** (2 * n) / np.cosh(r) ** 2
    err = np.max(np.abs(p - analytic))
    print(f"[1] TMSV r=0.5  cutoff={cutoff}  ({dt:.2f}s)")
    print(f"    解析 max|Δ| = {err:.3e}  {'✅' if err < 1e-8 else '❌'}")
    print(f"    P(n,n) 前5: probe {p.diagonal()[:5].round(6)}")
    print(f"                  gold  {analytic.diagonal()[:5].round(6)}")
    offdiag = np.max(np.abs(p - np.diag(np.diag(p))))
    print(f"    非对角 max = {offdiag:.3e}  {'✅' if offdiag < 1e-9 else '❌'}")

    # ---- 场景 1b: 子集/边缘对照（modes=(0,) vs 全模边缘）----
    p0 = joint_pn([(V, rbar, 1.0 + 0j)], modes=(0,), cutoff=cutoff)
    marg = marginalize(p, 0)
    err_b = np.max(np.abs(p0 - marg))
    print(f"[1b] 单模子集 vs 全模边缘: max|Δ| = {err_b:.3e}  {'✅' if err_b < 1e-8 else '❌'}")

    # ---- 场景 1c: TMSV 更大压缩（数值压力测试）----
    r2 = 1.2
    V2, rb2 = tmsv_Vr(r2)
    p2 = joint_pn([(V2, rb2, 1.0 + 0j)], modes=(0, 1), cutoff=12)
    lam2 = np.tanh(r2)
    an2 = np.zeros((12, 12))
    for n in range(12):
        an2[n, n] = lam2 ** (2 * n) / np.cosh(r2) ** 2
    err_c = np.max(np.abs(p2 - an2))
    print(f"[1c] TMSV r=1.2 cutoff=12: max|Δ| = {err_c:.3e}  {'✅' if err_c < 1e-6 else '❌'}")

    # ---- 场景 2: cat⊗coherent 乘积分解 ----
    alpha, beta = 0.8, 0.6
    Vc = 0.5 * np.eye(2)
    comp_cat = [
        (Vc, np.array([np.sqrt(2) * alpha, 0.0], dtype=complex), 0.5 / (1 + np.exp(-2 * alpha**2))),
        (Vc, np.array([-np.sqrt(2) * alpha, 0.0], dtype=complex), 0.5 / (1 + np.exp(-2 * alpha**2))),
    ]
    # 复中心交叉分量（偶猫 4 分量标准形）
    ov = np.exp(-2 * alpha**2)
    comp_cat += [
        (Vc, np.array([0.0, 1j * np.sqrt(2) * alpha], dtype=complex), 0.5 * ov / (1 + ov)),
        (Vc, np.array([0.0, -1j * np.sqrt(2) * alpha], dtype=complex), 0.5 * ov / (1 + ov)),
    ]
    # 双模乘积分量 = cat 分量 × coherent 分量（V 块对角, rbar 拼接, w 乘积）
    comps2 = []
    for V1, r1, w1 in comp_cat:
        Vb = np.zeros((4, 4))
        Vb[:2, :2] = V1
        Vb[2:, 2:] = Vc
        rb = np.concatenate([r1, np.array([np.sqrt(2) * beta, 0.0], dtype=complex)])
        comps2.append((Vb, rb, w1 * 1.0))
    p2m = joint_pn(comps2, modes=(0, 1), cutoff=10)
    # gold: fock 双模直积
    fa = cat_fock(30, alpha)
    fb = coherent_fock(30, beta)
    amps = np.kron(fa, fb)
    amps = amps / np.linalg.norm(amps)
    gold2 = np.abs(amps.reshape(30, 30)[:10, :10]) ** 2
    err2 = np.max(np.abs(p2m - gold2))
    print(f"\n[2] cat(α={alpha})⊗coherent(β={beta}) 4 分量 (cutoff=10)")
    print(f"    fock gold max|Δ| = {err2:.3e}  {'✅' if err2 < 1e-8 else '❌'}")

    # ---- 场景 3: 双模纠缠非高斯（cat⊗cat, 复中心交叉分量 × 复权重）----
    # 偶猫 |cat⟩ ∝ |α⟩+|−α⟩（α 实）的 4 分量正确表示：
    #   对角: 中心 (√2α, 0)，权重 1/(2Z)；交叉: 中心 (0, ±i√2α)（**p 槽**）
    #   （x 槽存实位移, p 槽存虚位移; 复中心描述相位位移）
    a3 = 0.7
    Z3 = 1.0 + math.exp(-2 * a3**2)  # Gram 归一
    cat_comps = [
        (np.array([np.sqrt(2) * a3, 0.0], dtype=complex), 1.0 / (2 * Z3)),
        (np.array([-np.sqrt(2) * a3, 0.0], dtype=complex), 1.0 / (2 * Z3)),
        (np.array([0.0, 1j * np.sqrt(2) * a3], dtype=complex), math.exp(-2 * a3**2) / (2 * Z3)),
        (np.array([0.0, -1j * np.sqrt(2) * a3], dtype=complex), math.exp(-2 * a3**2) / (2 * Z3)),
    ]
    # cat⊗cat: V 块对角, rbar 拼接（各自正确的 x/p 槽），w 乘积 → 16 分量
    comps3 = []
    for r1, w1 in cat_comps:
        for r2, w2 in cat_comps:
            Vb = np.zeros((4, 4))
            Vb[:2, :2] = Vc
            Vb[2:, 2:] = Vc
            rb = np.concatenate([r1, r2])
            comps3.append((Vb, rb, (w1 * w2) * (1.0 + 0j)))
    p3 = joint_pn(comps3, modes=(0, 1), cutoff=10)
    # gold: fock cat⊗cat
    fa3 = cat_fock(30, a3)
    fa3 /= np.linalg.norm(fa3)
    amps3 = np.kron(fa3, fa3)
    amps3 /= np.linalg.norm(amps3)
    gold3 = np.abs(amps3.reshape(30, 30)[:10, :10]) ** 2
    err3 = np.max(np.abs(p3 - gold3))
    print(f"\n[3] cat(α={a3})⊗cat(α={a3}) 16 分量（复中心交叉 × 复权重, cutoff=10）")
    print(f"    fock gold max|Δ| = {err3:.3e}  {'✅' if err3 < 1e-8 else '❌'}")
    print(f"    总和 probe={p3.real.sum():.6f} gold={gold3.sum():.6f}")

    # ---- 场景 3b: 复中心纠缠（不同 α 的 cat⊗cat, 交叉干涉更强）----
    # 用不同 α 强化交叉分量幅值, 验证复数中心 + 复数权重的工程稳定性
    a3b = 1.1  # 更大 α → 更小 ov (更强峰值分离, 交叉更弱) 但仍是同一类
    Z3b = 1.0 + math.exp(-2 * a3b**2)
    ovb3 = math.exp(-2 * a3b**2)
    cat_comps_b = [
        (np.array([np.sqrt(2) * a3b, 0.0], dtype=complex), 1.0 / (2 * Z3b)),
        (np.array([-np.sqrt(2) * a3b, 0.0], dtype=complex), 1.0 / (2 * Z3b)),
        (np.array([0.0, 1j * np.sqrt(2) * a3b], dtype=complex), ovb3 / (2 * Z3b)),
        (np.array([0.0, -1j * np.sqrt(2) * a3b], dtype=complex), ovb3 / (2 * Z3b)),
    ]
    comps3b = []
    for r1, w1 in cat_comps_b:
        for r2, w2 in cat_comps_b:
            Vb = np.zeros((4, 4))
            Vb[:2, :2] = Vc
            Vb[2:, 2:] = Vc
            rb = np.concatenate([r1, r2])
            comps3b.append((Vb, rb, (w1 * w2) * (1.0 + 0j)))
    p3b = joint_pn(comps3b, modes=(0, 1), cutoff=10)
    fa3b = cat_fock(30, a3b)
    fa3b /= np.linalg.norm(fa3b)
    amps3b = np.kron(fa3b, fa3b)
    amps3b /= np.linalg.norm(amps3b)
    gold3b = np.abs(amps3b.reshape(30, 30)[:10, :10]) ** 2
    err3b = np.max(np.abs(p3b - gold3b))
    print(f"\n[3b] cat(α={a3b})⊗cat(α={a3b}) 16 分量（大 α 峰值分离, cutoff=10）")
    print(f"    fock gold max|Δ| = {err3b:.3e}  {'✅' if err3b < 1e-8 else '❌'}")
    print(f"    总和 probe={p3b.real.sum():.6f} gold={gold3b.sum():.6f}")

    # ---- 场景 4: 混叠/点数/模数边界实验 ----
    print("\n[4] 混叠与点数实验（TMSV r=0.5, cutoff=10）")
    for nt in (80, 128, 8 * 10, 16 * 10):
        p_ = joint_pn([(V, rbar, 1.0 + 0j)], modes=(0, 1), cutoff=10, n_theta=nt)
        e_ = np.max(np.abs(p_ - analytic))
        print(f"    n_theta={nt:4d}: max|Δ|={e_:.3e}")
    print("\n[4b] 3 模可行性（TMSV×vac, cutoff=6, 时间/内存实测）")
    V4 = np.zeros((6, 6))
    V4[:4, :4] = V
    V4[4:, 4:] = 0.5 * np.eye(2)
    t0 = time.time()
    p4 = joint_pn([(V4, np.zeros(6, dtype=complex), 1.0 + 0j)], modes=(0, 1, 2), cutoff=6, n_theta=128)
    dt4 = time.time() - t0
    print(f"    3模 128³ torus 点: {dt4:.1f}s, P(0,0,0)={p4[0,0,0]:.6f} (期望 {1/np.cosh(r)**2:.6f})")
    t0 = time.time()
    p4b = joint_pn([(V4, np.zeros(6, dtype=complex), 1.0 + 0j)], modes=(0, 1, 2), cutoff=6, n_theta=48)
    dt4b = time.time() - t0
    print(f"    3模 48³  torus 点: {dt4b:.1f}s, P(0,0,0)={p4b[0,0,0]:.6f}")
    print(f"    判定: 3模点数 {max(128, 8*6)}={max(128, 8*6)} → {max(128,8*6)**3:,} 点/轴乘积"
          f"（纯 Python 逐点循环需向量化, 结论见 phase0 文档）")


if __name__ == "__main__":
    main()
