#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 long congested sequence 的 6 个序列上，计算 Strategy 4 相对 Strategy 1 的 gap 与 regret。

定义按 PlotsToBePut.pdf（Event-Driven Re-Optimization, Section 3.3）：
- Jfull(t) = Strategy 1 在 t 步的目标值（每步重优化）
- Jevent(t) = Strategy 4 在 t 步的目标值（事件驱动）
- 指标：max_link_utilization（%），即优化目标值
- 平均归一化 gap: gap = (1/T) * sum_t (Jevent(t) - Jfull(t)) / max(|Jfull(t)|, ε)
- 时间积分 regret: R = sum_t (Jevent(t) - Jfull(t))

要求：各 seed 下已有 strategy1/strategy1_stats.csv 与 strategy4/strategy4_stats.csv。
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEEDS = [0, 1, 7, 42, 123, 1234]
SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
UTIL_COL = 'max_link_utilization'


def load_stats(results_base_dir, sequence_dir_name, seed, strategy_subdir, stats_name):
    """加载指定 seed 与策略的 stats CSV，返回 DataFrame，若不存在返回 None。"""
    path = os.path.join(
        results_base_dir, sequence_dir_name, str(seed), strategy_subdir, stats_name
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


EPS = 1.0  # 避免分母为 0，PlotsToBePut.pdf 中的 ε


def compute_gap_regret_per_seed(s1_df, s4_df, util_col=UTIL_COL, eps=EPS):
    """
    按 PlotsToBePut.pdf 定义计算单序列 gap 与 regret。
    gap = (1/T) * sum_t (Jevent(t) - Jfull(t)) / max(|Jfull(t)|, ε)
    R   = sum_t (Jevent(t) - Jfull(t))
    """
    s1 = s1_df[['step_id', util_col]].rename(columns={util_col: 's1_util'})
    s4 = s4_df[['step_id', util_col]].rename(columns={util_col: 's4_util'})
    m = s1.merge(s4, on='step_id', how='inner')
    if len(m) == 0:
        return np.nan, np.nan
    jfull = m['s1_util'].values.astype(float)
    jevent = m['s4_util'].values.astype(float)
    denom = np.maximum(np.abs(jfull), eps)
    gap_terms = (jevent - jfull) / denom
    gap = float(np.mean(gap_terms))
    regret = float(np.sum(jevent - jfull))
    return gap, regret


def main():
    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)

    rows = []
    for seed in SEEDS:
        s1_df = load_stats(results_base_dir, SEQUENCE_DIR_NAME, seed, 'strategy1', 'strategy1_stats.csv')
        s4_df = load_stats(results_base_dir, SEQUENCE_DIR_NAME, seed, 'strategy4', 'strategy4_stats.csv')
        if s1_df is None:
            print(f"  seed {seed}: 缺少 strategy1_stats.csv，跳过")
            continue
        if s4_df is None:
            print(f"  seed {seed}: 缺少 strategy4_stats.csv，跳过")
            continue
        gap, regret = compute_gap_regret_per_seed(s1_df, s4_df)
        rows.append({'seed': seed, 'gap': gap, 'regret': regret, 'num_steps': len(s1_df)})

    if not rows:
        print("未找到任一 seed 的 S1 与 S4 数据，无法计算 gap/regret。请先运行 run_strategy1_long_congested 与 run_strategy4_long_congested。")
        return

    df = pd.DataFrame(rows)
    avg_gap = df['gap'].mean()
    total_regret = df['regret'].sum()

    print("=" * 60)
    print("Strategy 4 vs Strategy 1（long congested sequence）")
    print("定义见 PlotsToBePut.pdf: gap = (1/T)*sum((Jevent-Jfull)/max(|Jfull|,ε)), R = sum(Jevent-Jfull)")
    print("=" * 60)
    print(df.to_string(index=False))
    print()
    print(f"  各序列平均 Gap（再平均）: {avg_gap:.6f} (无量纲)")
    print(f"  各序列 Regret 之和:       {total_regret:.4f} (%·步)")
    print("=" * 60)

    out_path = os.path.join(output_dir, 'gap_regret_summary.csv')
    df.to_csv(out_path, index=False)
    print(f"已保存: {out_path}")


if __name__ == '__main__':
    main()
