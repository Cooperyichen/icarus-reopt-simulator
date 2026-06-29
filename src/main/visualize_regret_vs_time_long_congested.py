#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针对一个 arrival rate 序列（指定 seed），绘制不同 θ 下 Strategy 4 的累积 regret 随步数变化。
R(τ) = sum_{t=1}^{τ} (J_event(t) - J_full(t))，单调递增；斜率可衡量策略好坏。
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
UTIL_COL = 'max_link_utilization'
THRESHOLDS = [4, 6, 8, 10, 12]  # θ=8 在 strategy4/，其余在 strategy4_threshold_{θ}/strategy4/


def load_s1(results_base_dir, seed):
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy1', 'strategy1_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def load_s2(results_base_dir, seed):
    """加载 Strategy 2（保持比例）数据。"""
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy2', 'strategy2_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def load_s3(results_base_dir, seed):
    """加载 Strategy 3（全局最优路径比例）数据。"""
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy3', 'strategy3_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def load_s3_cap100_theoretical(results_base_dir, seed):
    """Strategy 3 容量约束 LP（仅理论）；若存在则优先于无约束 strategy3/。"""
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed),
        'strategy3_cap100_theoretical', 'strategy3_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def load_s3_preferred(results_base_dir, seed):
    """优先 cap100 理论结果，否则原始 strategy3_stats。"""
    df = load_s3_cap100_theoretical(results_base_dir, seed)
    if df is not None:
        return df
    return load_s3(results_base_dir, seed)


def load_s4(results_base_dir, seed, theta):
    if theta == 8:
        path = os.path.join(
            results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy4', 'strategy4_stats.csv'
        )
    else:
        path = os.path.join(
            results_base_dir, SEQUENCE_DIR_NAME, str(seed),
            f'strategy4_threshold_{theta}', 'strategy4', 'strategy4_stats.csv'
        )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def cumulative_regret(j_full, j_event):
    """j_full, j_event 为同长度的 array，返回累积 regret 数组 R[τ] = sum_{t=1}^{τ} (j_event - j_full)。"""
    diff = np.asarray(j_event, dtype=float) - np.asarray(j_full, dtype=float)
    return np.cumsum(diff)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Plot cumulative regret vs time for one sequence')
    parser.add_argument('--seed', type=int, default=0, help='Seed (sequence) to plot')
    parser.add_argument('--output', type=str, default=None,
                        help='Output path; default: 可视化结果展示/long congested sequence/regret_vs_time_seed{seed}.png')
    args = parser.parse_args()
    seed = args.seed

    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    if args.output:
        out_path = args.output
    else:
        out_path = os.path.join(output_dir, f'regret_vs_time_seed{seed}.png')

    s1_df = load_s1(results_base_dir, seed)
    if s1_df is None:
        print(f"缺少 seed {seed} 的 strategy1_stats.csv")
        return
    s1 = s1_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_full'})
    steps = s1['step_id'].values
    j_full = s1['j_full'].values.astype(float)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {
        's2': '#9467bd', 's3': '#17becf',
        '4': '#d62728', '6': '#1f77b4', '8': '#2ca02c', '10': '#ff7f0e', '12': '#8c564b',
    }

    # Strategy 2 (保持比例)
    s2_df = load_s2(results_base_dir, seed)
    if s2_df is not None:
        s2 = s2_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
        m = s1.merge(s2, on='step_id', how='inner').sort_values('step_id')
        if len(m) > 0:
            j_full_m = m['j_full'].values.astype(float)
            j_event_m = m['j_event'].values.astype(float)
            R = cumulative_regret(j_full_m, j_event_m)
            ax.plot(m['step_id'].values, R, label='Path Ratio Conservation', color=colors['s2'], linewidth=2)

    # Strategy 3：有 cap100 理论结果则用其覆盖原 strategy3，图例为 Global Optimal Proportions
    s3_df = load_s3_preferred(results_base_dir, seed)
    if s3_df is not None and UTIL_COL in s3_df.columns:
        s3 = s3_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
        m = s1.merge(s3, on='step_id', how='inner').sort_values('step_id')
        m = m.dropna(subset=['j_event'])
        if len(m) > 0:
            j_full_m = m['j_full'].values.astype(float)
            j_event_m = m['j_event'].values.astype(float)
            R = cumulative_regret(j_full_m, j_event_m)
            ax.plot(
                m['step_id'].values, R,
                label='Global Optimal Proportions',
                color=colors['s3'], linewidth=2,
            )

    for theta in THRESHOLDS:
        s4_df = load_s4(results_base_dir, seed, theta)
        if s4_df is None:
            print(f"  跳过 θ={theta}（无数据）")
            continue
        s4 = s4_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
        m = s1.merge(s4, on='step_id', how='inner').sort_values('step_id')
        if len(m) == 0:
            continue
        j_full_m = m['j_full'].values.astype(float)
        j_event_m = m['j_event'].values.astype(float)
        R = cumulative_regret(j_full_m, j_event_m)
        ax.plot(m['step_id'].values, R, label=rf'Event-driven ($\theta$={theta})',
                color=colors.get(str(theta), None), linewidth=2)

    ax.set_xlabel('Time step $t$')
    ax.set_ylabel(r'Cumulative regret $R(\tau) = \sum_{s=1}^{\tau} (J_{\mathrm{event}}(s) - J_{\mathrm{full}}(s))$')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"已保存: {out_path}")


if __name__ == '__main__':
    main()
