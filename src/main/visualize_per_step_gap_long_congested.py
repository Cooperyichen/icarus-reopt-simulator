#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针对 long congested sequence 指定 seed，绘制每步 max link utilization，
并标注重优化步。风格类似 max_link_utilization_theoretical_comparison.png。
支持两种模式：utilization（真实水平）或 gap（与最优解的差值）
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import seaborn as sns

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
UTIL_COL = 'max_link_utilization'
# 仅展示 θ∈{4,8} 的条带与 Event-driven 曲线（不含 6、10、12）
THRESHOLDS = [4, 8]

# 风格参考 max_link_utilization_theoretical_comparison.png
sns.set_theme(style="whitegrid")
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14

COLORS = {
    '4': '#d62728',
    '8': '#2ca02c',
}
FULL_OPTIM_COLOR = '#0d47a1'
S3_COLOR = '#17becf'


def load_s1(results_base_dir, seed):
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy1', 'strategy1_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def load_s3(results_base_dir, seed):
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy3', 'strategy3_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def load_s3_cap100_theoretical(results_base_dir, seed):
    path = os.path.join(
        results_base_dir, SEQUENCE_DIR_NAME, str(seed),
        'strategy3_cap100_theoretical', 'strategy3_stats.csv'
    )
    if not os.path.isfile(path):
        return None
    return pd.read_csv(path)


def load_s3_preferred(results_base_dir, seed):
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


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Plot per-step max link utilization')
    parser.add_argument('--seed', type=int, default=7, help='Seed (sequence) to plot')
    parser.add_argument('--metric', choices=['utilization', 'gap'], default='utilization',
                        help='utilization: 真实 link utilization (%); gap: 与最优解的差值')
    parser.add_argument('--output', type=str, default=None,
                        help='Output path; default based on metric')
    args = parser.parse_args()
    seed = args.seed
    use_utilization = args.metric == 'utilization'

    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)
    if args.output:
        out_path = args.output
    else:
        suffix = 'utilization' if use_utilization else 'gap'
        out_path = os.path.join(output_dir, f'per_step_{suffix}_seed{seed}.png')

    s1_df = load_s1(results_base_dir, seed)
    if s1_df is None:
        print(f"缺少 seed {seed} 的 strategy1_stats.csv")
        return
    s1 = s1_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_full'})
    j_full = s1['j_full'].values.astype(float)

    fig, ax = plt.subplots(figsize=(12, 7))

    # Utilization: shaded bands [J_full, J_full+θ] (percentage points), per θ, behind curves
    if use_utilization:
        for theta in THRESHOLDS:
            s4_df = load_s4(results_base_dir, seed, theta)
            if s4_df is None:
                continue
            s4 = s4_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
            m = s1.merge(s4, on='step_id', how='inner').sort_values('step_id')
            if len(m) == 0:
                continue
            steps = m['step_id'].values
            jf = m['j_full'].values.astype(float)
            hi = np.minimum(jf + float(theta), 100.0)
            color = COLORS.get(str(theta), '#333333')
            ax.fill_between(
                steps, jf, hi, facecolor=color, alpha=0.14, linewidth=0, zorder=1,
            )

    # Strategy 3 (Global Optimal Proportions)
    s3_df = load_s3_preferred(results_base_dir, seed)
    if s3_df is not None and UTIL_COL in s3_df.columns:
        s3 = s3_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
        m = s1.merge(s3, on='step_id', how='inner').sort_values('step_id')
        m = m.dropna(subset=['j_event'])
        if len(m) > 0:
            y_vals = m['j_event'].values.astype(float) if use_utilization else (
                m['j_event'].values.astype(float) - m['j_full'].values.astype(float))
            if use_utilization:
                y_plot = np.minimum(y_vals, 100.0)
                ax.plot(
                    m['step_id'].values, y_plot, label='Global Optimal Proportions',
                    color=S3_COLOR, marker='s', linestyle='--', linewidth=2, markersize=6, zorder=3,
                )
                over_100 = y_vals > 100
                if np.any(over_100):
                    ax.scatter(
                        m.loc[over_100, 'step_id'].values, np.full(np.sum(over_100), 100.0),
                        s=120, marker='^', color=S3_COLOR, edgecolors='black',
                        linewidth=1.5, zorder=6,
                    )
            else:
                ax.plot(
                    m['step_id'].values, y_vals, label='Global Optimal Proportions',
                    color=S3_COLOR, marker='s', linestyle='--', linewidth=2, markersize=6, zorder=3,
                )

    # Event-driven (each θ); utilization>100% 时抹平为 100% 并标出
    for theta in THRESHOLDS:
        s4_df = load_s4(results_base_dir, seed, theta)
        if s4_df is None:
            print(f"  跳过 θ={theta}（无数据）")
            continue
        s4 = s4_df[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
        m = s1.merge(s4, on='step_id', how='inner').sort_values('step_id')
        if len(m) == 0:
            continue
        y_vals = m['j_event'].values.astype(float) if use_utilization else (
            m['j_event'].values.astype(float) - m['j_full'].values.astype(float))
        color = COLORS.get(str(theta), None)
        if use_utilization:
            y_plot = np.minimum(y_vals, 100.0)
            ax.plot(
                m['step_id'].values, y_plot, label=rf'Event-driven ($\theta$={theta})',
                color=color, marker='D', linestyle=':', linewidth=2, markersize=7, alpha=0.95, zorder=4,
            )
            over_100 = y_vals > 100
            if np.any(over_100):
                ax.scatter(
                    m.loc[over_100, 'step_id'].values, np.full(np.sum(over_100), 100.0),
                    s=120, marker='^', color=color, edgecolors='black',
                    linewidth=1.5, zorder=6,
                )
        else:
            ax.plot(
                m['step_id'].values, y_vals, label=rf'Event-driven ($\theta$={theta})',
                color=color, marker='D', linestyle=':', linewidth=2, markersize=7, alpha=0.95, zorder=4,
            )

    # full optimization baseline (draw on top)
    if use_utilization:
        s1_vals = j_full
        ax.plot(
            s1['step_id'].values, s1_vals, label='full optimization',
            color=FULL_OPTIM_COLOR, marker='o', linestyle='-', linewidth=2.5, markersize=6, zorder=5,
        )
    else:
        ax.plot(
            s1['step_id'].values, np.zeros(len(s1)), label='full optimization',
            color=FULL_OPTIM_COLOR, marker='o', linestyle='-', linewidth=2.5, markersize=6, zorder=5,
        )

    handles, labels = ax.get_legend_handles_labels()
    if use_utilization:
        over_handle = Line2D(
            [0], [0], marker='^', color='gray', linestyle='None',
            markersize=10, markeredgecolor='black', markeredgewidth=1.5,
            label='Utilization > 100% (capped)', markerfacecolor='gray',
        )
        handles.append(over_handle)
        labels.append('Utilization > 100% (capped)')
        band_lbl = r'Shaded: $[J_{\mathrm{full}},\,\min\{J_{\mathrm{full}}+\theta,\,100\%\}]$'
        handles.append(mpatches.Patch(facecolor='0.5', edgecolor='none', alpha=0.25, label=band_lbl))
        labels.append(band_lbl)

    ax.set_xlabel('Time Step', fontsize=12, fontweight='bold')
    ylabel = 'Max Link Utilization (%)' if use_utilization else 'Per-step Max Link Utilization Gap vs Optimal (%)'
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    ax.legend(handles, labels, loc='best', framealpha=0.9, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.set_xlim(left=0)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"已保存: {out_path}")


if __name__ == '__main__':
    main()
