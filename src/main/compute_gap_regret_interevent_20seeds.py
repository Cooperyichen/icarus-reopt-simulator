#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 20 个可行序列计算：
- Path ratio scaling、Strategy 3、Strategy 3 cap100 理论 LP、Strategy 4 (θ=4,6,8,10,12) 的 gap、regret
- Strategy 4 各 θ 的 inter-event time

定义：gap = (1/T)*sum_t (Jevent-Jfull)/max(|Jfull|,ε), regret = sum_t (Jevent-Jfull)
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
THRESHOLDS = [4, 6, 8, 10, 12]
UTIL_COL = 'max_link_utilization'
EPS = 1.0


def load_feasible_seeds():
    path = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME,
                        'feasible_long_congested_seeds_20.csv')
    if os.path.isfile(path):
        return pd.read_csv(path)['seed'].astype(int).tolist()
    return [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 19, 20, 21, 23, 42, 123, 1234]


def _is_reoptimized(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ('true', '1', 'yes')


def get_s4_path(results_base_dir, seed, theta):
    if theta == 8:
        return os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy4', 'strategy4_stats.csv')
    return os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(seed),
                        f'strategy4_threshold_{theta}', 'strategy4', 'strategy4_stats.csv')


def compute_gap_regret(s1_df, other_df, util_col=UTIL_COL, eps=EPS):
    s1 = s1_df[['step_id', util_col]].rename(columns={util_col: 's1_util'})
    other = other_df[['step_id', util_col]].rename(columns={util_col: 'other_util'})
    m = s1.merge(other, on='step_id', how='inner')
    if len(m) == 0:
        return np.nan, np.nan
    jfull = m['s1_util'].values.astype(float)
    jother = m['other_util'].values.astype(float)
    denom = np.maximum(np.abs(jfull), eps)
    gap = float(np.mean((jother - jfull) / denom))
    regret = float(np.sum(jother - jfull))
    return gap, regret


def compute_inter_event_times(reoptimized_steps):
    if len(reoptimized_steps) < 2:
        return []
    return [reoptimized_steps[i + 1] - reoptimized_steps[i] for i in range(len(reoptimized_steps) - 1)]


def main():
    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)

    seeds = load_feasible_seeds()
    gap_regret_rows = []
    inter_event_rows = []

    for seed in seeds:
        s1_path = os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy1', 'strategy1_stats.csv')
        if not os.path.isfile(s1_path):
            continue
        s1_df = pd.read_csv(s1_path)
        num_steps = len(s1_df)

        # Path ratio scaling (S2)
        s2_path = os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy2', 'strategy2_stats.csv')
        if os.path.isfile(s2_path):
            s2_df = pd.read_csv(s2_path)
            gap, regret = compute_gap_regret(s1_df, s2_df)
            gap_regret_rows.append({
                'seed': seed, 'strategy': 'path_ratio_scaling', 'theta': np.nan,
                'gap': gap, 'regret': regret, 'num_steps': num_steps
            })

        s3_path = os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy3', 'strategy3_stats.csv')
        if os.path.isfile(s3_path):
            s3_df = pd.read_csv(s3_path)
            gap, regret = compute_gap_regret(s1_df, s3_df)
            gap_regret_rows.append({
                'seed': seed, 'strategy': 'strategy3', 'theta': np.nan,
                'gap': gap, 'regret': regret, 'num_steps': num_steps
            })

        s3c_path = os.path.join(
            results_base_dir, SEQUENCE_DIR_NAME, str(seed),
            'strategy3_cap100_theoretical', 'strategy3_stats.csv'
        )
        if os.path.isfile(s3c_path):
            s3c_df = pd.read_csv(s3c_path)
            gap, regret = compute_gap_regret(s1_df, s3c_df)
            gap_regret_rows.append({
                'seed': seed, 'strategy': 'strategy3_cap100_theoretical', 'theta': np.nan,
                'gap': gap, 'regret': regret, 'num_steps': num_steps
            })

        # Strategy 4 (θ=4,6,8,10,12)
        for theta in THRESHOLDS:
            s4_path = get_s4_path(results_base_dir, seed, theta)
            if not os.path.isfile(s4_path):
                continue
            s4_df = pd.read_csv(s4_path)
            gap, regret = compute_gap_regret(s1_df, s4_df)
            gap_regret_rows.append({
                'seed': seed, 'strategy': 'strategy4', 'theta': theta,
                'gap': gap, 'regret': regret, 'num_steps': num_steps
            })

            # Inter-event time
            reopt = s4_df['reoptimized'].apply(_is_reoptimized)
            reopt_steps = sorted(s4_df.loc[reopt, 'step_id'].astype(int).tolist())
            dt_list = compute_inter_event_times(reopt_steps)
            inter_event_rows.append({
                'seed': seed, 'theta': theta,
                'reopt_count': len(reopt_steps),
                'num_inter_events': len(dt_list),
                'mean_dt': np.mean(dt_list) if dt_list else np.nan,
                'min_dt': min(dt_list) if dt_list else np.nan,
                'max_dt': max(dt_list) if dt_list else np.nan,
                'inter_event_times': str(dt_list) if dt_list else '',
            })

    # Save gap_regret
    df_gr = pd.DataFrame(gap_regret_rows)
    gr_path = os.path.join(output_dir, 'gap_regret_summary_20seeds.csv')
    df_gr.to_csv(gr_path, index=False)
    print(f"✓ 已保存: {gr_path}")

    # Save inter_event
    df_ie = pd.DataFrame(inter_event_rows)
    ie_path = os.path.join(output_dir, 'inter_event_summary_20seeds.csv')
    df_ie.to_csv(ie_path, index=False)
    print(f"✓ 已保存: {ie_path}")

    # Per-step regret (for detailed analysis): seed, step_id, strategy, theta, j_full, j_event, instantaneous_regret
    per_step_rows = []
    for seed in seeds:
        s1_path = os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy1', 'strategy1_stats.csv')
        if not os.path.isfile(s1_path):
            continue
        s1_df = pd.read_csv(s1_path)[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_full'})

        for strategy, theta_val, path in [
            ('path_ratio_scaling', np.nan, os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy2', 'strategy2_stats.csv')),
            ('strategy3', np.nan, os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(seed), 'strategy3', 'strategy3_stats.csv')),
            ('strategy3_cap100_theoretical', np.nan, os.path.join(
                results_base_dir, SEQUENCE_DIR_NAME, str(seed),
                'strategy3_cap100_theoretical', 'strategy3_stats.csv')),
        ]:
            if not os.path.isfile(path):
                continue
            other = pd.read_csv(path)[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
            m = s1_df.merge(other, on='step_id', how='inner')
            for _, r in m.iterrows():
                per_step_rows.append({
                    'seed': seed, 'step_id': int(r['step_id']),
                    'strategy': strategy, 'theta': theta_val,
                    'j_full': r['j_full'], 'j_event': r['j_event'],
                    'instantaneous_regret': r['j_event'] - r['j_full']
                })

        for theta in THRESHOLDS:
            path = get_s4_path(results_base_dir, seed, theta)
            if not os.path.isfile(path):
                continue
            other = pd.read_csv(path)[['step_id', UTIL_COL]].rename(columns={UTIL_COL: 'j_event'})
            m = s1_df.merge(other, on='step_id', how='inner')
            for _, r in m.iterrows():
                per_step_rows.append({
                    'seed': seed, 'step_id': int(r['step_id']),
                    'strategy': 'strategy4', 'theta': theta,
                    'j_full': r['j_full'], 'j_event': r['j_event'],
                    'instantaneous_regret': r['j_event'] - r['j_full']
                })

    if per_step_rows:
        df_ps = pd.DataFrame(per_step_rows)
        ps_path = os.path.join(output_dir, 'per_step_regret_20seeds.csv')
        df_ps.to_csv(ps_path, index=False)
        print(f"✓ 已保存: {ps_path}")

    print("\n汇总预览:")
    if len(df_gr) > 0:
        print(df_gr.groupby(['strategy', 'theta']).agg({'gap': 'mean', 'regret': 'sum'}).to_string())

    # 批量生成 cumulative regret 图表
    import subprocess
    for seed in seeds:
        try:
            subprocess.run(
                [sys.executable, '-m', 'main.visualize_regret_vs_time_long_congested', '--seed', str(seed)],
                cwd=src_dir, check=True, capture_output=True
            )
            print(f"✓ regret_vs_time_seed{seed}.png")
        except subprocess.CalledProcessError:
            print(f"✗ seed {seed} 图表生成失败")


if __name__ == '__main__':
    main()
