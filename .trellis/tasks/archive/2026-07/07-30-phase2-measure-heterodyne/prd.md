# F-MEASURE: Heterodyne

## Goal

高斯核心 Heterodyne：采样 + 条件化（+ circuit 接线）。

## Math (ħ=1, xxpp, V_vac=I/2)

- POVM $|\beta\rangle\langle\beta|/\pi$（Husimi Q）。
- 在 mode $k$ 的 $(x,p)$ 块上：outcome $z\sim\mathcal N(\bar r_k,\, V_{kk}+I_2/2)$。
- $\beta = (x + i p)/\sqrt{2}$（与 coherent factory 的 $\bar r$ 约定一致）。
- 条件化（对其余模）：  
  $V_B' = V_B - C^\mathsf T(V_A+I/2)^{-1}C$，  
  $\bar r_B' = \bar r_B + C^\mathsf T(V_A+I/2)^{-1}(z-\bar r_A)$，  
  然后 **remove** 被测模（双正交完全测量，不同于 `homodyne_condition` 保留奇异模）。

## API

```python
heterodyne_mean(state, mode=0) -> complex
heterodyne_cov_xp(state, mode=0) -> np.ndarray  # (2,2)
heterodyne_sample(state, mode=0, *, rng=None) -> complex
heterodyne_condition(state, mode, outcome: complex) -> GaussianState  # mode removed
heterodyne_sample_and_condition(...) -> tuple[complex, GaussianState]
# circuit
GaussianCircuit.measure_heterodyne(mode, name) -> self
```

## Freeze / tests

- vacuum: $\mathbb E[\beta]=0$，cov_xp $=I$；样本均值/方差蒙特卡洛
- coherent α: $\mathbb E[\beta]=\alpha$，cov_xp $=I$
- thermal n: cov_xp $=(n+1)I$
- TMSV heterodyne on mode0 → remaining mode thermal-like / correlations update
- circuit smoke: measure_heterodyne 写入 results[name] 为 complex

## Out of scope

- Threshold / PNR
- 不改 homodyne 语义
