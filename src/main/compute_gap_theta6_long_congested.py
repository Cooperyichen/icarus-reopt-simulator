#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
计算 long congested sequence 上 Strategy 4（θ=6）相对 Strategy 1 的 gap 与 regret，
格式同 gap_regret_summary.csv，保存为 gap_regret_summary_theta6.csv。
使用 strategy4_threshold_6/strategy4/strategy4_stats.csv。
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
EPS = 1.0


def load_stats(results_base_dir, sequence_dir_name, seed, strategy_subdir, stats_name):
    path = os.path.join(
        results_base_dir, sequence_dir_name, str(seed), strategy_subdir, stats_name
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def compute_gap_regret_per_seed(s1_df, s4_df, util_col=UTIL_COL, eps=EPS):
    """gap = (1/T)*sum_t (Jevent-Jfull)/max(|Jfull|,ε), regret = sum_t (Jevent-Jfull)。"""
    s1 = s1_df[['step_id', util_col]].rename(columns={util_col: 's1_util'})
    s4 = s4_df[['step_id', util_col]].rename(columns={util_col: 's4_util'})
    m = s1.merge(s4, on='step_id', how='inner')
    if len(m) == 0:
        return np.nan, np.nan, 0
    jfull = m['s1_util'].values.astype(float)
    jevent = m['s4_util'].values.astype(float)
    denom = np.maximum(np.abs(jfull), eps)
    gap_terms = (jevent - jfull) / denom
    gap = float(np.mean(gap_terms))
    regret = float(np.sum(jevent - jfull))
    return gap, regret, len(m)


def main():
    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    s4_subdir = os.path.join('strategy4_threshold_6', 'strategy4')

    rows = []
    for seed in SEEDS:
        s1_df = load_stats(results_base_dir, SEQUENCE_DIR_NAME, seed, 'strategy1', 'strategy1_stats.csv')
        s4_df = load_stats(results_base_dir, SEQUENCE_DIR_NAME, seed, s4_subdir, 'strategy4_stats.csv')
        if s1_df is None:
            print(f"  seed {seed}: 缺少 strategy1_stats.csv，跳过")
            continue
        if s4_df is None:
            print(f"  seed {seed}: 缺少 strategy4_threshold_6 数据，跳过")
            continue
        gap, regret, num_steps = compute_gap_regret_per_seed(s1_df, s4_df)
        rows.append({'seed': seed, 'gap': gap, 'regret': regret, 'num_steps': num_steps})

    if not rows:
        print("未找到足够数据，无法计算 θ=6 的 gap/regret。")
        return

    df = pd.DataFrame(rows)
    out_path = os.path.join(output_dir, 'gap_regret_summary_theta6.csv')
    df.to_csv(out_path, index=False)
    print("=" * 60)
    print("Strategy 4（θ=6）vs Strategy 1 — Gap & Regret（long congested sequence）")
    print("=" * 60)
    print(df.to_string(index=False))
    print()
    print(f"  各序列平均 Gap（再平均）: {df['gap'].mean():.6f}")
    print(f"  各序列 Regret 之和:       {df['regret'].sum():.4f} (%·步)")
    print(f"已保存: {out_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()
