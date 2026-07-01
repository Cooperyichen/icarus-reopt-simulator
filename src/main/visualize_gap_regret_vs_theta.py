#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
绘制 gap 和 regret 随 θ 变化的带误差棒折线图。
使用 95% 置信区间作为误差棒。
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from scipy import stats as scipy_stats

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
CONFIDENCE = 0.95


def main():
    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    gr_path = os.path.join(output_dir, 'gap_regret_summary_20seeds.csv')

    if not os.path.isfile(gr_path):
        print(f"✗ 缺少 gap_regret_summary_20seeds.csv，请先运行 compute_gap_regret_interevent_20seeds")
        return

    df = pd.read_csv(gr_path)
    s4 = df[df['strategy'] == 'strategy4'].copy()
    s4 = s4.dropna(subset=['theta'])
    s4['theta'] = s4['theta'].astype(int)

    thetas = sorted(s4['theta'].unique())
    gap_means, gap_stds, gap_cis = [], [], []
    regret_means, regret_stds, regret_cis = [], [], []

    for theta in thetas:
        sub = s4[s4['theta'] == theta]
        n = len(sub)
        if n < 2:
            gap_means.append(sub['gap'].mean())
            gap_stds.append(0)
            gap_cis.append(0)
            regret_means.append(sub['regret'].mean())
            regret_stds.append(0)
            regret_cis.append(0)
            continue

        # Gap
        g = sub['gap'].values
        mean_g = np.mean(g)
        std_g = np.std(g, ddof=1)
        t_val = scipy_stats.t.ppf((1 + CONFIDENCE) / 2, df=n - 1)
        ci_half = t_val * (std_g / np.sqrt(n))
        gap_means.append(mean_g)
        gap_stds.append(std_g)
        gap_cis.append(ci_half)

        # Regret
        r = sub['regret'].values
        mean_r = np.mean(r)
        std_r = np.std(r, ddof=1)
        ci_half_r = t_val * (std_r / np.sqrt(n))
        regret_means.append(mean_r)
        regret_stds.append(std_r)
        regret_cis.append(ci_half_r)

    gap_means = np.array(gap_means)
    gap_cis = np.array(gap_cis)
    regret_means = np.array(regret_means)
    regret_cis = np.array(regret_cis)

    def _gap_band_stats(strategy_key):
        g = df[df['strategy'] == strategy_key]['gap'].dropna().astype(float).values
        if len(g) == 0:
            return None
        return {'mean': float(np.mean(g)), 'gmin': float(np.min(g)), 'gmax': float(np.max(g))}

    s2_stats = _gap_band_stats('path_ratio_scaling')
    s3_stats = _gap_band_stats('strategy3')
    s2_color, s3_color = '#ff7f0e', '#9467bd'
    x0, x1 = min(thetas) - 0.5, max(thetas) + 0.5

    # Figure 1: Gap vs theta (Strategy 4 line + Strategies 2 & 3 horizontal bands)
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    if s3_stats is not None:
        ax1.axhspan(
            s3_stats['gmin'], s3_stats['gmax'], xmin=0, xmax=1,
            facecolor=s3_color, alpha=0.22, zorder=1,
        )
        ax1.axhline(s3_stats['mean'], color=s3_color, linewidth=2, linestyle='-', zorder=2)
    if s2_stats is not None:
        ax1.axhspan(
            s2_stats['gmin'], s2_stats['gmax'], xmin=0, xmax=1,
            facecolor=s2_color, alpha=0.22, zorder=1,
        )
        ax1.axhline(s2_stats['mean'], color=s2_color, linewidth=2, linestyle='-', zorder=2)
    ax1.errorbar(
        thetas, gap_means, yerr=gap_cis,
        fmt='o-', color='#1f77b4', linewidth=2, markersize=8,
        capsize=5, capthick=2, elinewidth=2, zorder=3,
    )
    ax1.set_xlabel(r'$\theta$', fontsize=12)
    ax1.set_ylabel('Gap', fontsize=12)
    ax1.set_xticks(thetas)
    ax1.grid(True, alpha=0.3, zorder=0)
    ax1.set_xlim(x0, x1)
    ax1.set_ylim(bottom=0)
    legend_handles = [
        Line2D(
            [0], [0], color='#1f77b4', marker='o', linestyle='-',
            linewidth=2, markersize=8, label='Event-driven',
        ),
        mpatches.Patch(
            facecolor=s2_color, edgecolor=s2_color, alpha=0.35,
            label='Path Ratio Conservation',
        ),
        mpatches.Patch(
            facecolor=s3_color, edgecolor=s3_color, alpha=0.35,
            label='Global Optimal Proportions',
        ),
    ]
    ax1.legend(handles=legend_handles, loc='upper left', fontsize=9)
    plt.tight_layout()
    gap_path = os.path.join(output_dir, 'gap_vs_theta_with_ci.png')
    plt.savefig(gap_path, dpi=150)
    plt.close()
    print(f"✓ Gap vs θ 已保存: {gap_path}")

    # Figure 2: Regret vs theta
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.errorbar(
        thetas, regret_means, yerr=regret_cis,
        fmt='s-', color='#2ca02c', linewidth=2, markersize=8,
        capsize=5, capthick=2, elinewidth=2
    )
    ax2.set_xlabel('θ (threshold)', fontsize=12)
    ax2.set_ylabel('Regret', fontsize=12)
    ax2.set_title(f'Regret vs θ (Strategy 4, Long Congested, 20 seeds)\n95% CI error bars', fontsize=14)
    ax2.set_xticks(thetas)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(min(thetas) - 0.5, max(thetas) + 0.5)
    ax2.set_ylim(bottom=0)
    plt.tight_layout()
    regret_path = os.path.join(output_dir, 'regret_vs_theta_with_ci.png')
    plt.savefig(regret_path, dpi=150)
    plt.close()
    print(f"✓ Regret vs θ 已保存: {regret_path}")

    # Print summary
    print("\n汇总 (mean ± 95% CI half-width):")
    for i, t in enumerate(thetas):
        print(f"  θ={t}: gap={gap_means[i]:.4f} ± {gap_cis[i]:.4f}, regret={regret_means[i]:.1f} ± {regret_cis[i]:.1f}")


if __name__ == '__main__':
    main()
