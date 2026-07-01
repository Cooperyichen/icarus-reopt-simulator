#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用精确求解器运行指定 seeds 的 Strategy 1、Strategy 2（保持比例）、Strategy 4（θ=6, 8, 10），
并生成 regret_vs_time_seed{N}.png。

对于 Strategy 4 的按比例缩放步（不重新优化），即使 link utilization 超过 100% 也记录到结果中。
"""

import sys
import os
import argparse
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import (
    execute_strategy_reoptimization,
    execute_strategy_path_ratio_preservation,
    execute_strategy_adaptive_reoptimization,
)

SEQUENCE_DIR_NAME = 'long congested sequence'
THRESHOLDS = [6, 8, 10]

PRECISE_SOLVER_OPTIONS = {
    'eps_abs': 1e-8,
    'eps_rel': 1e-8,
    'max_iters': 500000,
}


def run_s4_for_threshold(seed, threshold, sequence_file, sequence_name, config, result_dir_base):
    """为指定 θ 运行 S4。按比例缩放步的 utilization 即使 >100% 也会记录。"""
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values

    if threshold == 8:
        run_base = os.path.join(result_dir_base, sequence_name)
        strategy_subdir = 'strategy4'
    else:
        run_base = os.path.join(result_dir_base, sequence_name, f'strategy4_threshold_{threshold}')
        strategy_subdir = 'strategy4'

    strategy_stats = execute_strategy_adaptive_reoptimization(
        sequence, config, run_base,
        threshold=threshold,
        solver_options=PRECISE_SOLVER_OPTIONS
    )

    strategy_dir = os.path.join(run_base, strategy_subdir)
    os.makedirs(strategy_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    stats_file = os.path.join(strategy_dir, 'strategy4_stats.csv')
    df.to_csv(stats_file, index=False)
    return stats_file


def run_for_seed(seed, config_file, result_dir_base, visualize=True):
    """为单个 seed 运行 S1, S2, S4 并可选生成可视化。"""
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    sequence_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
    sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"

    if not os.path.exists(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return False

    config = load_yaml_file(config_file)

    print("=" * 80)
    print(f"使用精确求解器运行 seed {seed}: S1, S2, S4 (θ=6,8,10)")
    print("=" * 80)
    print(f"Solver options: {PRECISE_SOLVER_OPTIONS}")
    print()

    # Strategy 1
    print("\n--- Strategy 1 ---")
    strategy_stats, infeasible = execute_strategy_reoptimization(
        pd.read_csv(sequence_file, index_col=0).values, config,
        os.path.join(result_dir_base, sequence_name),
        solver_options=PRECISE_SOLVER_OPTIONS
    )
    s1_dir = os.path.join(result_dir_base, sequence_name, 'strategy1')
    os.makedirs(s1_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    df.to_csv(os.path.join(s1_dir, 'strategy1_stats.csv'), index=False)
    print(f"✓ Strategy 1 已保存 (infeasible: {infeasible})")

    # Strategy 2 (保持比例)
    print("\n--- Strategy 2 (保持比例) ---")
    strategy_stats = execute_strategy_path_ratio_preservation(
        pd.read_csv(sequence_file, index_col=0).values, config, os.path.join(result_dir_base, sequence_name),
        solver_options=PRECISE_SOLVER_OPTIONS
    )
    s2_dir = os.path.join(result_dir_base, sequence_name, 'strategy2')
    os.makedirs(s2_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    df.to_csv(os.path.join(s2_dir, 'strategy2_stats.csv'), index=False)
    print("✓ Strategy 2 已保存")

    # Strategy 4 (θ=6, 8, 10)
    for threshold in THRESHOLDS:
        print(f"\n--- Strategy 4 (θ={threshold}) ---")
        stats_file = run_s4_for_threshold(
            seed, threshold, sequence_file, sequence_name, config, result_dir_base
        )
        print(f"✓ 已保存: {stats_file}")

    if visualize:
        print("\n" + "=" * 80)
        print(f"正在生成 regret_vs_time_seed{seed}.png ...")
        print("=" * 80)
        import subprocess
        subprocess.run(
            [sys.executable, '-m', 'main.visualize_regret_vs_time_long_congested', '--seed', str(seed)],
            cwd=src_dir, check=True
        )

    return True


def main():
    parser = argparse.ArgumentParser(description='Run S1, S2, S4 with precise solver for specified seeds')
    parser.add_argument('--seeds', type=str, default='42,123,1234',
                        help='Comma-separated seeds (default: 42,123,1234)')
    parser.add_argument('--no-viz', action='store_true', help='Skip visualization')
    args = parser.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(',')]
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')

    for seed in seeds:
        run_for_seed(seed, config_file, result_dir_base, visualize=not args.no_viz)


if __name__ == '__main__':
    main()
