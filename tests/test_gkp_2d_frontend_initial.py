"""Lab 前端 GKP 2d Z 基初态源接通(09-02-gkp-2d-frontend-initial)。

`initial` 名单机制(spec §6.4)扩展两个名字:
- ``"gkp0_2d"`` → ``gkp0(lattice="2d", cross="full")``(Z 基逻辑 0,纯态位置梳)
- ``"gkp1_2d"`` → ``gkp1(lattice="2d", cross="full")``(Z 基逻辑 1,交替相位 (−1)^k)

cross="full" 必须:2d Z 基 0/1 差异只在交叉分量符号,对角混合态(cross="none")
无法区分逻辑态(docs/gkp-2d-square-lattice.md §2/§3)。

前端同步(cvsim/lab/static/editor.js):payload 校验白名单 + 下拉框选项,
由 tests/editor.test.mjs 回归(node --test);本文件钉 Python 侧契约。
"""

from __future__ import annotations

import pytest

from cvsim.bosonic import BosonicCircuit, pure_fidelity

pytestmark = pytest.mark.phaseB6


class TestGkp2dFrontendInitial:
    def test_initial_gkp2d_sources_build(self):
        """AC-1: 新名字构造成功,_initial_spec 保真,每模 49 组件。

        默认 grid_size=3 → M=2*3+1=7 峰/模,cross="full" → M^2=49 组件/模;
        双模 tensor 后 49*49=2401。
        """
        c = BosonicCircuit(2, initial=["gkp0_2d", "gkp1_2d"])
        assert c._initial_spec == ["gkp0_2d", "gkp1_2d"]
        assert c._initial is not None
        assert c._initial.n_components == 49 * 49  # tensor(49, 49) = 2401
        per_mode = [len(comp.rbar) // 2 for comp in c._initial.components]
        assert set(per_mode) == {2}

    def test_initial_gkp2d_ir_roundtrip(self):
        """AC-2: to_ir→from_ir→to_ir,initial 名单无损。"""
        c = BosonicCircuit(2, initial=["gkp0_2d", None])
        d = c.to_ir()
        assert d.get("initial") == ["gkp0_2d", None]
        c2 = BosonicCircuit.from_ir(d)
        assert c2._initial_spec == ["gkp0_2d", None]
        assert c2.to_ir() == d

    def test_initial_gkp2d_z_basis_orthogonal(self):
        """AC-3: 两电路分别取 gkp0_2d / gkp1_2d 初态,pure_fidelity ≈ 0。"""
        c0 = BosonicCircuit(1, initial=["gkp0_2d"])
        c1 = BosonicCircuit(1, initial=["gkp1_2d"])
        assert c0._initial is not None and c1._initial is not None
        f = pure_fidelity(c0._initial, c1._initial)
        assert f < 0.1

    def test_initial_gkp2d_single_mode_49_components(self):
        """AC-1(单模切面): 默认 grid_size=3 → M=7 → cross=full → M^2=49/模。"""
        c = BosonicCircuit(1, initial=["gkp0_2d"])
        assert c._initial is not None
        assert c._initial.n_components == 49

    def test_initial_unknown_name_lists_all(self):
        """AC-4: 未知名字 ValueError 文案含全部五个合法名。"""
        with pytest.raises(ValueError, match="gkp0_2d") as exc_info:
            BosonicCircuit(1, initial=["gkp9"])
        msg = str(exc_info.value)
        for name in ("None", "gkp0", "gkp1", "gkp0_2d", "gkp1_2d"):
            assert name in msg
