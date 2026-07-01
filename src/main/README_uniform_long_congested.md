# Uniform Long Congested Sequence 流程说明

## 已实现内容

1. **等方差均匀扰动**  
   `generate_arrival_rate_sequence.py` 中新增 `generate_arrival_rate_sequence_uniform(initial_rates, num_steps=50, variance=2500, seed)`，使用零均值均匀分布 U(-a,a)，其中 a=√(3×2500)=50√3，与高斯 N(0,50²) 方差一致。

2. **20 个序列**  
   `generate_uniform_long_congested_sequences.py` 使用 `feasible_long_congested_seeds_20.csv` 的 20 个 seed，生成并保存到  
   `results/multi_step_comparison/uniform long congested sequence/{seed}/arrival_rate_sequence_50_steps.csv`。

3. **Strategy 4 批处理**  
   `run_strategy4_uniform_long_congested.py` 对 uniform 序列跑 Strategy 4，θ∈{4,6,8,10,12}。  
   - 不带参数：20 seeds × 5 thetas = 100 次（耗时会较长）。  
   - `--seeds 2,3,4,5`：仅跑指定 seeds。  
   - `--thetas 6,8,10,12`：仅跑指定 thetas。

4. **Inter-event 直方图与拟合**  
   `visualize_uniform_long_congested_inter_event.py` 生成：  
   - `results/可视化结果展示/uniform long congested sequence/inter_event_histogram_multi_theta.png`（多 θ 直方图 + Gamma/Weibull 包络）  
   - `inter_event_envelope_fit_evaluation.csv`、`gamma_fit_suitability_summary.csv`。

5. **Gamma 参数 vs θ**  
   `visualize_uniform_gamma_params_vs_theta.py` 生成：  
   - `gamma_params_vs_theta.png`  
   - `gamma_params_vs_theta_comparison.csv`（与 long congested 的斜率/R² 对比）。

## 补全 100 次 Strategy 4 并重绘

在 `src` 目录下执行（无参数即 20 seeds × 5 thetas）：

```bash
python -m main.run_strategy4_uniform_long_congested
```

完成后重新生成图表与拟合评估：

```bash
python -m main.visualize_uniform_long_congested_inter_event
python -m main.visualize_uniform_gamma_params_vs_theta
```

当前已有部分数据（θ=4 多个 seed、θ=6 部分 seed），上述可视化已能基于现有数据出图；补全全部 100 次后，再跑一次上述两条命令即可得到基于 20 seeds × 5 thetas 的完整结果。

## Gap vs 序列前缀长度（与 long congested 对比）

计算 gap 需要每个 seed 下同时存在 **Strategy 1** 与 **Strategy 4** 的 `*_stats.csv`。uniform 序列默认只有 S4，需先跑 S1：

```bash
python -m main.run_strategy1_uniform_long_congested
```

然后生成「前缀 T=10/20/30/40/50 步」的 gap 曲线（与论文定义一致，仅对 `step_id≤T` 求平均）及对比图：

```bash
python -m main.visualize_gap_vs_sequence_length_long_uniform
```

输出目录：`results/可视化结果展示/gap_sequence_length_comparison/`（含 `gap_vs_sequence_length_long_uniform.png` 与 CSV）。
