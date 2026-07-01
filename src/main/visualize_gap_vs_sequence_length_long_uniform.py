#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 long congested sequence 与 uniform long congested sequence，按前缀步数 T∈{10,20,30,40,50}
计算 Strategy 4 相对 Strategy 1 的 gap（与全序列定义一致，仅对 step_id≤T 的步取平均）。

gap = (1/T) * sum_{t=1..T} (Jevent(t)-Jfull(t)) / max(|Jfull(t)|, ε)
其中 J 为 max_link_utilization（%）。

输出：
- gap_vs_sequence_length_long_uniform.png（仅 long congested 单图；CSV 仍含 uniform 汇总）
- gap_vs_sequence_length_detail.csv（每 seed × theta × T × sequence_type）
- gap_vs_sequence_length_summary.csv（跨 seed 的 mean ± 95% CI）
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

RESULTS_BASE = os.path.join(src_dir, 'results', 'multi_step_comparison')
OUTPUT_DIR = os.path.join(src_dir, 'results', '可视化结果展示', 'gap_sequence_length_comparison')

LONG_NAME = 'long congested sequence'
UNIFORM_NAME = 'uniform long congested sequence'

SEEDS_LONG = os.path.join(
    src_dir, 'results', '可视化结果展示', LONG_NAME, 'feasible_long_congested_seeds_20.csv'
)
SEEDS_UNIFORM = os.path.join(
    src_dir, 'results', '可视化结果展示', UNIFORM_NAME, 'feasible_uniform_long_congested_seeds_20.csv'
)

THRESHOLDS = [4, 6, 8, 10, 12]
PREFIX_STEPS = [10, 20, 30, 40, 50]
UTIL_COL = 'max_link_utilization'
EPS = 1.0
CONFIDENCE = 0.95

COLOR_MAP = {4: '#9467bd', 6: '#1f77b4', 8: '#2ca02c', 10: '#ff7f0e', 12: '#d62728'}


def load_seeds():
    if not os.path.isfile(SEEDS_LONG):
        raise FileNotFoundError(f'缺少种子列表: {SEEDS_LONG}')
    seeds = pd.read_csv(SEEDS_LONG)['seed'].astype(int).tolist()
    return seeds


def s4_path(sequence_dir_name, seed, theta):
    base = os.path.join(RESULTS_BASE, sequence_dir_name, str(seed))
    if theta == 8:
        return os.path.join(base, 'strategy4', 'strategy4_stats.csv')
    return os.path.join(base, f'strategy4_threshold_{theta}', 'strategy4', 'strategy4_stats.csv')


def s1_path(sequence_dir_name, seed):
    return os.path.join(
        RESULTS_BASE, sequence_dir_name, str(seed), 'strategy1', 'strategy1_stats.csv'
    )


def compute_gap_prefix(s1_df, s4_df, max_step, util_col=UTIL_COL, eps=EPS):
    """仅使用 step_id ∈ [1, max_step] 的步计算 gap。"""
    s1 = s1_df[['step_id', util_col]].rename(columns={util_col: 's1_util'})
    s4 = s4_df[['step_id', util_col]].rename(columns={util_col: 's4_util'})
    m = s1.merge(s4, on='step_id', how='inner')
    m = m[m['step_id'] <= max_step].sort_values('step_id')
    if len(m) == 0:
        return np.nan
    jfull = m['s1_util'].values.astype(float)
    jevent = m['s4_util'].values.astype(float)
    denom = np.maximum(np.abs(jfull), eps)
    gap_terms = (jevent - jfull) / denom
    return float(np.mean(gap_terms))


def collect_for_sequence(sequence_dir_name, seeds, label):
    rows = []
    for seed in seeds:
        p1 = s1_path(sequence_dir_name, seed)
        if not os.path.isfile(p1):
            print(f'  [{label}] seed={seed}: 缺少 strategy1_stats.csv，跳过')
            continue
        s1_df = pd.read_csv(p1)
        for theta in THRESHOLDS:
            ps4 = s4_path(sequence_dir_name, seed, theta)
            if not os.path.isfile(ps4):
                continue
            s4_df = pd.read_csv(ps4)
            for T in PREFIX_STEPS:
                if s1_df['step_id'].max() < T or s4_df['step_id'].max() < T:
                    continue
                g = compute_gap_prefix(s1_df, s4_df, T)
                rows.append({
                    'sequence_type': label,
                    'sequence_dir': sequence_dir_name,
                    'seed': seed,
                    'theta': theta,
                    'prefix_steps': T,
                    'gap': g,
                })
    return pd.DataFrame(rows)


def ci_half(values):
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    if n < 2:
        return 0.0, float(np.nanmean(v)) if n == 1 else np.nan
    mean_v = np.mean(v)
    std_v = np.std(v, ddof=1)
    t_val = scipy_stats.t.ppf((1 + CONFIDENCE) / 2, df=n - 1)
    return t_val * (std_v / np.sqrt(n)), mean_v


def plot_panels(df_detail):
    """单图：long congested 序列；多条 θ 折线，x=前缀步数 T。CSV 仍汇总两类序列。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    summary_rows = []
    for seq_label in df_detail['sequence_type'].unique():
        sub = df_detail[df_detail['sequence_type'] == seq_label]
        for theta in THRESHOLDS:
            for T in PREFIX_STEPS:
                g = sub[(sub['theta'] == theta) & (sub['prefix_steps'] == T)]['gap'].values
                half, mean_g = ci_half(g)
                summary_rows.append({
                    'sequence_type': seq_label,
                    'theta': theta,
                    'prefix_steps': T,
                    'gap_mean': mean_g,
                    'ci_half_width_95': half,
                    'n_seeds': int(np.sum(~np.isnan(g))),
                })
    df_sum = pd.DataFrame(summary_rows)

    fig, ax = plt.subplots(figsize=(7, 5))
    sub_sum = df_sum[df_sum['sequence_type'] == LONG_NAME]
    if not sub_sum.empty:
        for theta in THRESHOLDS:
            tsub = sub_sum[sub_sum['theta'] == theta].sort_values('prefix_steps')
            if tsub.empty:
                continue
            x = tsub['prefix_steps'].values
            y = tsub['gap_mean'].values
            err = tsub['ci_half_width_95'].values
            ax.errorbar(
                x, y, yerr=err, marker='o', capsize=3, linewidth=2, markersize=5,
                color=COLOR_MAP.get(theta, '#333'), label=f'θ={theta}',
            )
    ax.set_xlabel('Prefix length T (steps)')
    ax.set_ylabel('Gap')
    ax.set_xticks(PREFIX_STEPS)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=8, ncol=2)
    plt.tight_layout()
    out_png = os.path.join(OUTPUT_DIR, 'gap_vs_sequence_length_long_uniform.png')
    plt.savefig(out_png, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'✓ 图已保存: {out_png}')
    return df_sum


def main():
    seeds = load_seeds()
    print('=' * 70)
    print('Gap vs prefix length: long congested vs uniform long congested')
    print(f'Seeds: {len(seeds)}, θ: {THRESHOLDS}, T: {PREFIX_STEPS}')
    print('=' * 70)

    df_long = collect_for_sequence(LONG_NAME, seeds, LONG_NAME)
    df_uni = collect_for_sequence(UNIFORM_NAME, seeds, UNIFORM_NAME)

    if df_long.empty and df_uni.empty:
        print('✗ 未收集到任何数据。请确认各 seed 下存在 strategy1 与 strategy4 的 stats。')
        print('  uniform 序列需先运行: python -m main.run_strategy1_uniform_long_congested')
        return

    df_detail = pd.concat([df_long, df_uni], ignore_index=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    detail_path = os.path.join(OUTPUT_DIR, 'gap_vs_sequence_length_detail.csv')
    df_detail.to_csv(detail_path, index=False)
    print(f'✓ 明细: {detail_path} ({len(df_detail)} rows)')

    df_sum = plot_panels(df_detail)
    sum_path = os.path.join(OUTPUT_DIR, 'gap_vs_sequence_length_summary.csv')
    df_sum.to_csv(sum_path, index=False)
    print(f'✓ 汇总: {sum_path}')


if __name__ == '__main__':
    main()
