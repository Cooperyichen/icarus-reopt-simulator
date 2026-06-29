#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run Strategy 4 on uniform long congested sequence for theta in {4,6,8,10,12}."""

import os
import sys
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_adaptive_reoptimization

SEQUENCE_DIR_NAME = 'uniform long congested sequence'
THRESHOLDS = [4, 6, 8, 10, 12]
SEEDS_FILE = os.path.join(
    src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME, 'feasible_uniform_long_congested_seeds_20.csv'
)


def load_seeds():
    if os.path.isfile(SEEDS_FILE):
        return pd.read_csv(SEEDS_FILE)['seed'].astype(int).tolist()
    fallback = os.path.join(
        src_dir, 'results', '可视化结果展示', 'long congested sequence', 'feasible_long_congested_seeds_20.csv'
    )
    return pd.read_csv(fallback)['seed'].astype(int).tolist()


def run_for_seed_theta(seed, threshold, config, result_dir_base):
    sequence_name = f'{SEQUENCE_DIR_NAME}/{seed}'
    sequence_file = os.path.join(
        result_dir_base, SEQUENCE_DIR_NAME, str(seed), 'arrival_rate_sequence_50_steps.csv'
    )
    if not os.path.isfile(sequence_file):
        print(f'✗ 缺少序列文件，跳过 seed={seed}: {sequence_file}')
        return None

    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values

    if threshold == 8:
        run_result_base = os.path.join(result_dir_base, sequence_name)
        strategy_dir = os.path.join(result_dir_base, sequence_name, 'strategy4')
    else:
        run_result_base = os.path.join(result_dir_base, sequence_name, f'strategy4_threshold_{threshold}')
        strategy_dir = os.path.join(run_result_base, 'strategy4')

    # If the expected output already exists, skip to avoid re-computation.
    out_stats = os.path.join(strategy_dir, 'strategy4_stats.csv')
    if os.path.isfile(out_stats):
        print(f'✓ skip (already exists): seed={seed}, θ={threshold}: {out_stats}')
        return out_stats

    strategy_stats = execute_strategy_adaptive_reoptimization(
        sequence, config, run_result_base, threshold=threshold
    )
    os.makedirs(strategy_dir, exist_ok=True)

    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    df.to_csv(out_stats, index=False)
    reopt_count = int(df['reoptimized'].astype(str).str.lower().isin(['true', '1']).sum()) if 'reoptimized' in df.columns else 0
    print(f'✓ seed={seed}, θ={threshold}: {out_stats} (reopt={reopt_count}/{len(df)})')
    return out_stats


def main(seeds_override=None, thetas_override=None):
    seeds = seeds_override if seeds_override is not None else load_seeds()
    thresholds = thetas_override if thetas_override is not None else THRESHOLDS
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')

    print('=' * 80)
    print('Run Strategy4 on uniform long congested sequence')
    print('=' * 80)
    print(f'Seeds: {len(seeds)}, Thresholds: {thresholds}')

    total = len(seeds) * len(thresholds)
    idx = 0
    for threshold in thresholds:
        print('\n' + '-' * 80)
        print(f'θ={threshold}')
        print('-' * 80)
        for seed in seeds:
            idx += 1
            print(f'[{idx}/{total}] seed={seed}, θ={threshold}')
            run_for_seed_theta(seed, threshold, config, result_dir_base)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run Strategy4 on uniform long congested sequence')
    parser.add_argument('--seeds', type=str, default=None,
                        help='Comma-separated seed list (default: all 20 from CSV)')
    parser.add_argument('--thetas', type=str, default=None,
                        help='Comma-separated theta list (default: 4,6,8,10,12)')
    args = parser.parse_args()
    seeds_override = [int(s) for s in args.seeds.split(',')] if args.seeds else None
    thetas_override = [int(t) for t in args.thetas.split(',')] if args.thetas else None
    main(seeds_override=seeds_override, thetas_override=thetas_override)
