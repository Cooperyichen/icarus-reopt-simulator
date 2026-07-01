#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针对一个 arrival rate 序列（指定 seed），绘制不同 θ 下 Strategy 4 的「绝对值累加」随步数变化。
R_abs(τ) = sum_{t=1}^{τ} |J_event(t) - J_full(t)|，单调不减；斜率表示每步误差的累积。
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
THRESHOLDS = [6, 8, 10]


def load_s1(results_base_dir, seed):
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy1', 'strategy1_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


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


def load_s2(results_base_dir, seed):
    """Path ratio preservation (Strategy 2). 含超过100%的结果也使用。"""
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy2', 'strategy2_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def cumulative_abs_diff(j_full, j_event):
    """返回累积绝对值 R_abs[τ] = sum_{t=1}^{τ} |j_event(t) - j_full(t)|，单调不减。"""
    diff = np.asarray(j_event, dtype=float) - np.asarray(j_full, dtype=float)
    return np.cumsum(np.abs(diff))


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Plot cumulative absolute regret vs time')
    parser.add_argument('--seed', type=int, default=0, help='Seed (sequence) to plot')
    parser.add_argument('--output', type=str, default=None,
                        help='Output path; default: .../regret_abs_vs_time_seed{seed}.png')
    args = parser.parse_args()
    seed = args.seed

    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    if args.output:
        out_path = args.output
    else:
        out_path = os.path.join(output_dir, f'regret_abs_vs_time_seed{seed}.png')

    s1_df = load_s1(results_base_dir, seed)
    if s1_df is None:
        print(f"缺少 seed {seed} 的 strategy1_stats.csv")
        return
    s1 = s1_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_full'})

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {'6': '#1f77b4', '8': '#2ca02c', '10': '#ff7f0e'}

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
        R_abs = cumulative_abs_diff(j_full_m, j_event_m)
        ax.plot(m['step_id'].values, R_abs, label=rf'Strategy 4 ($\theta$={theta})',
                color=colors.get(str(theta), None), linewidth=2)

    # Path ratio preservation (Strategy 2), 含超过100%的结果也用
    s2_df = load_s2(results_base_dir, seed)
    if s2_df is not None and UTIL_COL in s2_df.columns:
        s2 = s2_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
        m = s1.merge(s2, on='step_id', how='inner').sort_values('step_id')
        if len(m) > 0:
            j_full_m = m['j_full'].values.astype(float)
            j_event_m = m['j_event'].values.astype(float)
            R_abs = cumulative_abs_diff(j_full_m, j_event_m)
            ax.plot(m['step_id'].values, R_abs, label='path ratio scaling', color='#9467bd', linewidth=2)
        else:
            print("  path ratio preservation: 无共同步，跳过")
    else:
        print("  path ratio preservation: 无数据，跳过")

    ax.set_xlabel('Time step $t$')
    ax.set_ylabel('Cumulative regret (%·steps)')
    ax.set_title(f'Cumulative regret vs time (Long congested sequence, seed={seed})')
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
