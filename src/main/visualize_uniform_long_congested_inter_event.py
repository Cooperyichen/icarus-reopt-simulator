#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot inter-event histogram across theta for uniform long congested sequence."""

import os
import sys
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from main.visualize_long_congested_inter_event_cdf import (
    collect_delta_ts_from_stats,
    plot_inter_event_histogram_multi_theta_with_envelope,
)

SEQUENCE_DIR_NAME = 'uniform long congested sequence'
THRESHOLDS = [4, 6, 8, 10, 12]


def load_seeds():
    path = os.path.join(
        src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME, 'feasible_uniform_long_congested_seeds_20.csv'
    )
    if os.path.isfile(path):
        return pd.read_csv(path)['seed'].astype(int).tolist()
    fallback = os.path.join(
        src_dir, 'results', '可视化结果展示', 'long congested sequence', 'feasible_long_congested_seeds_20.csv'
    )
    return pd.read_csv(fallback)['seed'].astype(int).tolist()


def load_stats_for_threshold(results_base_dir, seeds, threshold):
    seq_root = os.path.join(results_base_dir, SEQUENCE_DIR_NAME)
    out = {}
    for seed in seeds:
        if threshold == 8:
            path = os.path.join(seq_root, str(seed), 'strategy4', 'strategy4_stats.csv')
        else:
            path = os.path.join(seq_root, str(seed), f'strategy4_threshold_{threshold}', 'strategy4', 'strategy4_stats.csv')
        if os.path.isfile(path):
            out[seed] = pd.read_csv(path)
    return out


def build_gamma_suitability(uniform_fit_csv, baseline_fit_csv, out_csv):
    uni = pd.read_csv(uniform_fit_csv)
    base = pd.read_csv(baseline_fit_csv)

    uni_g = uni[uni['dist'] == 'gamma'][['theta', 'rmse']].rename(columns={'rmse': 'uniform_gamma_rmse'})
    uni_w = uni[uni['dist'] == 'weibull'][['theta', 'rmse']].rename(columns={'rmse': 'uniform_weibull_rmse'})
    base_g = base[base['dist'] == 'gamma'][['theta', 'rmse']].rename(columns={'rmse': 'baseline_gamma_rmse'})

    merged = uni_g.merge(uni_w, on='theta', how='inner').merge(base_g, on='theta', how='left')
    merged['gamma_beats_weibull'] = merged['uniform_gamma_rmse'] <= merged['uniform_weibull_rmse']
    merged['rmse_ratio_vs_baseline_gamma'] = merged['uniform_gamma_rmse'] / merged['baseline_gamma_rmse'].replace(0, np.nan)
    merged['not_much_larger_than_baseline'] = merged['rmse_ratio_vs_baseline_gamma'] <= 1.5
    merged['gamma_suitable'] = merged['gamma_beats_weibull'] & merged['not_much_larger_than_baseline']
    merged.to_csv(out_csv, index=False)

    print(f'✓ suitability summary saved: {out_csv}')
    print(merged[['theta', 'uniform_gamma_rmse', 'uniform_weibull_rmse', 'baseline_gamma_rmse', 'gamma_suitable']].to_string(index=False))


def main():
    seeds = load_seeds()
    results_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)

    delta_ts_by_theta = {}
    for theta in THRESHOLDS:
        stats = load_stats_for_threshold(results_base, seeds, theta)
        if stats:
            delta_ts_by_theta[theta] = collect_delta_ts_from_stats(stats)
            print(f'θ={theta}: loaded {len(delta_ts_by_theta[theta])} inter-event samples from {len(stats)} seeds')
        else:
            print(f'θ={theta}: no stats found')

    if len(delta_ts_by_theta) < 2:
        raise RuntimeError('可用阈值数据不足，无法绘制多阈值 histogram。')

    fig_path = os.path.join(output_dir, 'inter_event_histogram_multi_theta.png')
    fit_csv = os.path.join(output_dir, 'inter_event_envelope_fit_evaluation.csv')
    plot_inter_event_histogram_multi_theta_with_envelope(delta_ts_by_theta, fig_path, fit_csv)

    baseline_fit_csv = os.path.join(
        src_dir, 'results', '可视化结果展示', 'long congested sequence', 'inter_event_envelope_fit_evaluation.csv'
    )
    if os.path.isfile(baseline_fit_csv):
        summary_csv = os.path.join(output_dir, 'gamma_fit_suitability_summary.csv')
        build_gamma_suitability(fit_csv, baseline_fit_csv, summary_csv)
    else:
        print(f'提示: baseline 拟合文件缺失，跳过 suitability 对比: {baseline_fit_csv}')


if __name__ == '__main__':
    main()
