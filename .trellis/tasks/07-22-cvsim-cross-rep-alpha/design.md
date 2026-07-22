# Design · α

## m4 结构

```text
t4_squeeze_n          # 已有
t1_coherent_loss      # 已有
t5_s2_n               # 新 G/F
t6_thermal_n          # 新 G/B
t7_homodyne_mean      # 新 G/F
main: 全跑 + OK
```

## Notes 补丁位置

- `02-Gaussian表示原理.md`：§loss 附近加 n̄  
- `01-Fock表示原理.md`：Homodyne 子弹 1–2 句矩  
- `术语表.md`：热损耗  
- 根 `README.md` / `cvsim/README.md`：m4 场景列表

## test

```python
# tests/test_m4_cross_rep.py
def test_m4_main():
    from cvsim.demos.m4_cross_rep import main
    main()  # asserts inside
```
