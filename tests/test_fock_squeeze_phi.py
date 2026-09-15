"""fock squeeze 的 phi 角（任务 09-14-fock-squeeze-phi）。

约定（decision 1）：fock 的 phi 是**振幅相**，与 ``FockState.squeezed`` 一致：

    xi = r·e^{i·phi}
    U(r, phi) = exp(½ (conj(xi)·a² − xi·a†²))

**不是** ``gaussian.gates.squeeze`` 的协方差旋转角 —— 二者的角差 2 倍
（``FockState.squeezed(2·φ)`` ≡ gaussian ``phi=φ``）。本文件锁死：
① phi 打通（gates / circuit / IR / ad）；② phi=0 行为逐位不变；
③ 2 倍关系未被"顺手统一"。
"""

from __future__ import annotations

import math
from math import factorial

import numpy as np
import pytest

from cvsim.fock import FockCircuit, FockState, ir_schema
from cvsim.fock.gates import _squeeze_U, squeeze
from cvsim.fock.ir import from_ir

R = 0.4
PHIS = [0.0, 0.3, 0.7, np.pi / 2, -1.1]

def _norm_align(a: np.ndarray, b: np.ndarray) -> float:
    """归一化后允许整体相位差的最大逐点误差。"""
    a = np.asarray(a, dtype=complex).ravel()
    b = np.asarray(b, dtype=complex).ravel()
    a = a / np.linalg.norm(a)
    k = np.vdot(b, a)
    return float(np.abs(a - k * b).max())

# -- ① phi 真的进了算符 -----------------------------------------------------

@pytest.mark.parametrize("phi", PHIS)
def test_squeeze_u_phi_matches_state_factory(phi: float) -> None:
    """``_squeeze_U(N, r, phi)|0⟩`` ≡ ``FockState.squeezed(N, r, phi)``。

    容差 1e-3：expm 在 cutoff=40 的截断残差，**与 phi 无关**（下面的
    ``test_residual_is_phi_independent`` 锁这一点）。
    """
    N = 40
    psi = _squeeze_U(N, R, phi)[:, 0]
    gold = FockState.squeezed(N, R, phi).amps
    assert _norm_align(psi, gold) < 1e-3

@pytest.mark.parametrize("phi", PHIS)
def test_residual_is_phi_independent(phi: float) -> None:
    """残差随 phi 不变 —— 否则说明 phi 的相位处理错了（而非数值截断）。"""
    N = 40
    base = _norm_align(_squeeze_U(N, R, 0.0)[:, 0], FockState.squeezed(N, R, 0.0).amps)
    got = _norm_align(_squeeze_U(N, R, phi)[:, 0], FockState.squeezed(N, R, phi).amps)
    assert abs(got - base) < 1e-12, f"phi={phi}: 残差 {got} vs phi=0 的 {base}"

@pytest.mark.parametrize("phi", PHIS)
def test_squeeze_gate_unitary(phi: float) -> None:
    U = _squeeze_U(12, R, phi)
    np.testing.assert_allclose(U @ U.conj().T, np.eye(12), atol=1e-10)

# -- ② phi=0 行为逐位不变 ---------------------------------------------------

def test_phi_zero_is_bit_identical_to_real_r_form() -> None:
    """φ=0 时与旧式 ``exp(½r(a²−a†²))`` **逐位相同**（不是"近似相同"）。

    这是本任务"零回归"的根据：所有不传 phi 的调用点行为不变。
    """
    from scipy.linalg import expm

    from cvsim.fock.circuit import annihilation

    N = 24
    a = annihilation(N)
    old = np.asarray(expm(0.5 * R * (a @ a - a.conj().T @ a.conj().T)))
    assert np.array_equal(old, _squeeze_U(N, R, 0.0))
    # gates.py 的第二份实现同样
    from cvsim.fock.gates import _squeeze_U as gates_squeeze_u

    assert np.array_equal(old, gates_squeeze_u(N, R))

def test_squeeze_gate_phi_zero_matches_default() -> None:
    st = FockState.vacuum(20)
    np.testing.assert_array_equal(squeeze(st, R).amps, squeeze(st, R, 0, 0.0).amps)

def test_squeeze_gate_phi_zero_matches_old_gold() -> None:
    """φ=0 的振幅与解析式 ``c_{2n} = √sech r (−1)^n √((2n)!)/(2^n n!) tanh^n r`` 对齐。"""
    N, r = 40, 0.6
    out = squeeze(FockState.vacuum(N), r).amps
    kk = np.arange(N // 2)
    c = np.zeros(N, dtype=complex)
    c[0::2] = (
        math.sqrt(1.0 / math.cosh(r))
        * (-1.0) ** kk
        * np.sqrt(np.array([factorial(2 * int(k)) for k in kk], dtype=float))
        / (2.0 ** kk * np.array([factorial(int(k)) for k in kk], dtype=float))
        * math.tanh(r) ** kk
    )
    c /= np.linalg.norm(c)
    # 容差 1e-5：expm 在 N=40 的截断残差（解析式本身精确）
    assert _norm_align(out, c) < 1e-5

# -- ③ 2 倍关系未被统一（约定哨兵） ----------------------------------------

@pytest.mark.parametrize("phi", [0.3, 0.9])
def test_fock_phi_is_double_the_gaussian_covariance_angle(phi: float) -> None:
    """fock ``phi`` = 2 × gaussian ``phi``（约定差异，**故意保留**）。

    若本测试失败 = 有人把 fock 的 phi 语义改成 gaussian 约定。那是破坏性
    变更：``tests/test_b9_bosonic_pnr.py`` 的 gold 对拍（fock 0.8 vs
    gaussian 0.4）会跟着失效，必须走独立任务 + 迁移说明。

    **覆盖边界**：本哨兵只走 ``FockState.squeezed``（态工厂）—— 若有人只把
    新增的 circuit/gates 路径改成 gaussian 约定而工厂不动，本测试仍绿。
    新路径由 ``test_squeeze_u_phi_matches_state_factory`` 兵住（该变异会把
    残差从 4.9e-10 推到 8.2e-02 → FAIL）。两者合并覆盖完整。
    """
    from cvsim.fock.circuit import annihilation
    from cvsim.gaussian.gates import squeeze as gaussian_squeeze
    from cvsim.gaussian.state import GaussianState

    N = 60
    a = annihilation(N)
    x = (a + a.conj().T) / np.sqrt(2)
    p = -1j * (a - a.conj().T) / np.sqrt(2)

    def fock_cov(fock_phi: float) -> np.ndarray:
        v = np.asarray(FockState.squeezed(N, R, fock_phi).amps, dtype=complex)
        f = lambda op: float(np.vdot(v, op @ v).real)  # noqa: E731
        return np.array([[f(x @ x), f((x @ p + p @ x) / 2)],
                         [f((x @ p + p @ x) / 2), f(p @ p)]])

    g = gaussian_squeeze(GaussianState.vacuum(1), R, 0, phi)
    gauss_cov = np.asarray(g.V)

    # fock(2φ) ≡ gaussian(φ)
    np.testing.assert_allclose(fock_cov(2 * phi), gauss_cov, atol=1e-10)
    # 并确认 fock(φ) ≢ gaussian(φ)（否则"2 倍"这个事实就不成立了）
    assert np.abs(fock_cov(phi) - gauss_cov).max() > 1e-3

# -- circuit 层 ------------------------------------------------------------

@pytest.mark.parametrize("phi", PHIS)
def test_circuit_squeeze_phi_matches_gate(phi: float) -> None:
    """``FockCircuit.squeeze(mode, r, phi)`` 编译执行 ≡ ``gates.squeeze``。"""
    N = 20
    c = FockCircuit(1, cutoff=N)
    c.squeeze(0, r=R, phi=phi)
    np.testing.assert_allclose(
        c.run().amps, squeeze(FockState.vacuum(N), R, phi=phi).amps, atol=1e-10
    )

def test_circuit_squeeze_phi_defaults_to_zero() -> None:
    N = 16
    a = FockCircuit(1, cutoff=N)
    a.squeeze(0, r=R)
    b = FockCircuit(1, cutoff=N)
    b.squeeze(0, r=R, phi=0.0)
    np.testing.assert_array_equal(a.run().amps, b.run().amps)

# -- IR 层 -----------------------------------------------------------------

def test_ir_schema_declares_phi() -> None:
    sq = ir_schema()["ops"]["squeeze"]
    assert set(sq["value_kind"]) == {"r", "phi"}
    assert sq["defaults"]["phi"] == 0.0

@pytest.mark.parametrize("phi", PHIS)
def test_from_ir_applies_phi(phi: float) -> None:
    """Lab payload（IR 带 phi）→ 执行结果 ≡ ``FockState.squeezed``。"""
    N = 40
    payload = {
        "schema": "circuit_v1", "backend": "fock", "nmode": 1, "cutoff": N,
        "ops": [{"id": "sq", "op": "squeeze", "params": {"r": R, "phi": phi}, "modes": [0]}],
        "view": {"wigner_mode": 0, "lim": 5.0, "n": 64}, "ui": {},
    }
    st = from_ir(payload).run()
    assert _norm_align(st.amps, FockState.squeezed(N, R, phi).amps) < 1e-8

def test_from_ir_without_phi_uses_default() -> None:
    """payload 不带 phi（旧文件）→ 走 default 0.0，行为不变。"""
    N = 20
    base = {"schema": "circuit_v1", "backend": "fock", "nmode": 1, "cutoff": N,
            "ops": [{"id": "sq", "op": "squeeze", "params": {"r": R}, "modes": [0]}],
            "view": {"wigner_mode": 0, "lim": 5.0, "n": 64}, "ui": {}}
    with_phi = {**base, "ops": [{**base["ops"][0], "params": {"r": R, "phi": 0.0}}]}
    np.testing.assert_array_equal(
        from_ir(base).run().amps, from_ir(with_phi).run().amps
    )

# -- 序列化不变量 -----------------------------------------------------------

def test_to_ir_always_carries_phi_zero() -> None:
    """``FockCircuit.squeeze(0, r)`` 的 ``to_ir()`` 恒带 ``phi: 0.0``。

    补 phi 前只写 ``r``（字节不变量已变，数值不变）。这里把新形态钉住，
    并确认三后端序列化形状一致（gaussian/bosonic 一直这么写）。
    """
    c = FockCircuit(1, cutoff=6)
    c.squeeze(0, r=R)
    sq = c.to_ir()["ops"][0]
    assert sq["op"] == "squeeze"
    assert sq["params"] == {"r": R, "phi": 0.0}
    # 显式传 0 与不传等价（同字节）
    c2 = FockCircuit(1, cutoff=6)
    c2.squeeze(0, r=R, phi=0.0)
    assert c2.to_ir()["ops"][0]["params"] == sq["params"]

# -- 相位在物理上真的变了（防止"存了参但没用"） ----------------------------

def test_phi_actually_changes_the_state() -> None:
    a = squeeze(FockState.vacuum(30), R, phi=0.0).amps
    b = squeeze(FockState.vacuum(30), R, phi=0.9).amps
    assert np.abs(a - b).max() > 1e-2, "phi 没起作用"
