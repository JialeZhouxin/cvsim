"""GBS 教学实证：从 (V, rbar) -> 联合概率分布 -> 采样。

回答三个问题：
1. 2^n 个"态"的理解对不对（threshold vs PNR）
2. 怎么从均值和协方差算出联合概率分布
3. 怎么随机采样，采样频率 vs 理论分布
"""
import math

import numpy as np
from thewalrus import hafnian_repeated
from thewalrus.quantum import Amat, Qmat, density_matrix

from cvsim.gaussian import GaussianCircuit, export_cov_for_walrus

# ---------- 1. 电路 -> 高斯态 -> thewalrus 格式 ----------
cir = GaussianCircuit(2)
cir.squeeze(0, 1.0)          # 只压缩模式 0（模式 1 保持真空）
cir.beamsplitter(0, 1, theta=np.pi / 4, phi=0.0)  # 50:50 干涉 -> 纠缠
st = cir.compile().run()
sigma, mu = export_cov_for_walrus(st)
m = sigma.shape[0] // 2
print(f"1. 电路输出: m={m} 模, sigma={sigma.shape}, mu={mu}")

# ---------- 2. 联合概率: hafnian 公式 ----------
# P(n) = haf(A_n) / (prod ni! * sqrt|Q|)   （零均值；双份 A 已含共轭配对）
# Q: 2m x 2m 复数协方差（前 m 个是 a 空间，后 m 个是 a† 空间）
# A = X*(I - Q^-1)，A_n = A 按 rpt=[n1..nm, n1..nm] 复制
Q = Qmat(sigma, hbar=2)
A = Amat(sigma, hbar=2)
sqrt_detQ = np.sqrt(np.abs(np.linalg.det(Q)))
print(f"2. Q 矩阵 ({Q.shape[0]}x{Q.shape[0]} 双份结构):\n   Q={np.round(Q,3).tolist()}")
print(f"   A = X(I-Q^-1)* = {np.round(A,3).tolist()}")

CUT = 4  # 光子数截断（0..CUT）
p_theory = np.zeros((CUT + 1, CUT + 1))
for n1 in range(CUT + 1):
    for n2 in range(CUT + 1):
        n = [n1, n2]
        rpt = n + n            # [n1, n2, n1, n2]: a 空间 + a† 空间
        haf = hafnian_repeated(A, rpt)
        denom = np.prod([math.factorial(k) for k in n]) * sqrt_detQ
        p_theory[n1, n2] = float(np.real(haf)) / denom
print(f"   Sum  P(n1,n2) (截断 CUT={CUT}) = {p_theory.sum():.4f}  (应~1)")
print(f"   最大项 P(0,0)={p_theory[0,0]:.4f}, P(2,0)={p_theory[2,0]:.4f}, "
      f"P(1,1)={p_theory[1,1]:.4f} (总光子数奇 -> 0)")

# ---------- 3. 对拍: thewalrus density_matrix 对角 = ground truth ----------
dm = density_matrix(mu, sigma, cutoff=CUT + 1, hbar=2)  # cutoff = 维度数
# dm 形状 (CUT+1,)*2m；对角元素 = dm[n1,n1,n2,n2]
p_ref = np.zeros((CUT + 1, CUT + 1))
for n1 in range(CUT + 1):
    for n2 in range(CUT + 1):
        p_ref[n1, n2] = np.real(dm[n1, n1, n2, n2])
print(f"3. thewalrus 对拍: P(2,2)={p_ref[2,2]:.4f}, P(1,1)={p_ref[1,1]:.4f}, "
      f"最大偏差={np.abs(p_theory - p_ref).max():.2e}")

# ---------- 4. 采样: 按联合分布直接权重采样 20000 次 -> 频率 vs 理论 ----------
# 原理：P(n) 已知（第 2 节），np.random.choice 按权重抽取即可。
# 截断 CUT 外概率漏掉 -> 用截断内归一化（教学演示）；大规模时 thewalrus
# 的条件采样器（hafnian_sample_state）才有性能优势。
rng = np.random.default_rng(42)
flat = np.clip(p_theory.ravel(), 0.0, None)  # 浮点噪声微负值 -> 0
flat = flat / flat.sum()
idx = rng.choice(len(flat), size=20000, p=flat)
samples = np.array(np.unravel_index(idx, p_theory.shape)).T  # (20000, 2) 光子数
hist, _, _ = np.histogram2d(samples[:, 0], samples[:, 1], bins=range(CUT + 2))
freq = hist / len(samples)
print("4. 直接权重采样 20000 次频率 vs 理论:")
for n1 in range(3):
    for n2 in range(3):
        print(f"   P({n1},{n2}): 理论 {p_ref[n1,n2]:.4f} | 频率 {freq[n1,n2]:.4f}")

# ---------- 5. threshold 探测: 每模只有 0/1 -> 正好 2^m 个 click pattern ----------
# click = "该模至少 1 个光子"。threshold 分布 = PNR 分布粗粒化：
# P(S) = sum_{n: n_i>0 iff i in S} P(n)
# （大模数时 thewalrus 有高效的 torontonian_sample_state 直接采样）
n_pattern = 1 << m
p_click_pattern = np.zeros(n_pattern)
for S in range(n_pattern):
    for n1 in range(CUT + 1):
        for n2 in range(CUT + 1):
            click = (n1 > 0, n2 > 0)
            want = tuple(bool((S >> i) & 1) for i in range(m))
            if click == want:
                p_click_pattern[S] += p_theory[n1, n2]
print(f"5. threshold 探测: {m} 模 -> {n_pattern} 个 click 模式, "
      f"Sum P = {p_click_pattern.sum():.4f}")
for S in range(n_pattern):
    print(f"   pattern {S:0{m}b}: P = {p_click_pattern[S]:.4f}")
