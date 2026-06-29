#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按最新输出数据计算 seeds 7, 42, 123, 1234 的 gap 与 regret，
每个 seed 下包含不同 θ 值（6, 8, 10）对应的 gap。

定义：gap = (1/T)*sum_t (Jevent-Jfull)/max(|Jfull|,ε), regret = sum_t (Jevent-Jfull)
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEEDS = [7, 42, 123, 1234]
THRESHOLDS = [6, 8, 10]
SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
UTIL_COL = 'max_link_utilization'
EPS = 1.0


def get_s4_path(results_base_dir, seed, theta):
    """返回 S4 对应 θ 的 stats 文件路径。"""
    if theta == 8:
        return os.path.join(
            results_base_dir, SEQUENCE_DIR_NAME, str(seed),
            'strategy4', 'strategy4_stats.csv'
        )
    return os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed),
        f'strategy4_threshold_{theta}', 'strategy4', 'strategy4_stats.csv'
    )


def compute_gap_regret(s1_df, s4_df, util_col=UTIL_COL, eps=EPS):
    """gap = (1/T)*sum_t (Jevent-Jfull)/max(|Jfull|,ε), regret = sum_t (Jevent-Jfull)"""
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
        s1_path = os.path.join(
            results_base_dir, SEQUENCE_DIR_NAME, str(seed),
            'strategy1', 'strategy1_stats.csv'
        )
        if not os.path.isfile(s1_path):
            print(f"  seed {seed}: 缺少 strategy1_stats.csv，跳过")
            continue
        s1_df = pd.read_csv(s1_path)

        for theta in THRESHOLDS:
            s4_path = get_s4_path(results_base_dir, seed, theta)
            if not os.path.isfile(s4_path):
                print(f"  seed {seed} θ={theta}: 缺少 S4 数据，跳过")
                continue
            s4_df = pd.read_csv(s4_path)
            gap, regret = compute_gap_regret(s1_df, s4_df)
            rows.append({
                'seed': seed,
                'theta': theta,
                'gap': gap,
                'regret': regret,
                'num_steps': len(s1_df)
            })

    if not rows:
        print("未找到足够数据。")
        return

    df = pd.DataFrame(rows)

    print("=" * 70)
    print("Gap & Regret（seeds 7, 42, 123, 1234 × θ=6,8,10）")
    print("定义: gap = (1/T)*sum((Jevent-Jfull)/max(|Jfull|,ε)), regret = sum(Jevent-Jfull)")
    print("=" * 70)
    print(df.to_string(index=False))
    print()
    for seed in SEEDS:
        sub = df[df['seed'] == seed]
        if len(sub) > 0:
            print(f"  seed {seed}: gap_mean={sub['gap'].mean():.6f}, regret_sum={sub['regret'].sum():.2f}")
    print()
    print(f"  全表平均 Gap: {df['gap'].mean():.6f}")
    print(f"  全表 Regret 之和: {df['regret'].sum():.2f} (%·步)")
    print("=" * 70)

    out_path = os.path.join(output_dir, 'gap_regret_summary_multi_theta.csv')
    df.to_csv(out_path, index=False)
    print(f"已保存: {out_path}")


if __name__ == '__main__':
    main()
