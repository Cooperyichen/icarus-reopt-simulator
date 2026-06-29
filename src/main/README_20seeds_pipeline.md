# 20 序列精确求解与结果汇总流程

## 1. 运行精确求解（耗时较长，约 1–2 小时）

```bash
cd src
python -m main.run_all_20seeds_precise
```

对 20 个可行序列依次运行：
- Strategy 1（基准）
- Strategy 2（Path ratio scaling）
- Strategy 4（θ=4, 6, 8, 10, 12）

结果写入 `results/multi_step_comparison/long congested sequence/{seed}/`。

## 2. 计算 gap、regret、inter-event time 并生成图表

```bash
python -m main.compute_gap_regret_interevent_20seeds
```

输出：
- `gap_regret_summary_20seeds.csv`：各 seed、strategy、θ 的 gap 与 regret
- `inter_event_summary_20seeds.csv`：各 seed、θ 的 inter-event time 统计
- `per_step_regret_20seeds.csv`：每步瞬时 regret（可选）
- `regret_vs_time_seed{N}.png`：各 seed 的 cumulative regret 图

## 3. 可选：仅对部分 seed 运行

```bash
python -m main.run_all_20seeds_precise --seeds 7,42,123,1234
```

## 4. 输出文件说明

| 文件 | 内容 |
|------|------|
| gap_regret_summary_20seeds.csv | seed, strategy, theta, gap, regret, num_steps |
| inter_event_summary_20seeds.csv | seed, theta, reopt_count, mean_dt, min_dt, max_dt, inter_event_times |
| per_step_regret_20seeds.csv | seed, step_id, strategy, theta, j_full, j_event, instantaneous_regret |
| regret_vs_time_seed{N}.png | Path ratio scaling + Strategy 4 (θ=4,6,8,10,12) 的 cumulative regret 曲线 |
