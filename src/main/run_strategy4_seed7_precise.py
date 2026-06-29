#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用与 S1 相同的精确求解器重新运行 Strategy 4 在 seed 7 的 long congested 序列，
覆盖 θ=6, 8, 10 的 strategy4_stats.csv，保证与 S1 公平比较。
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_adaptive_reoptimization

SEED = 7
SEQUENCE_DIR_NAME = 'long congested sequence'
THRESHOLDS = [6, 8, 10]

PRECISE_SOLVER_OPTIONS = {
    'eps_abs': 1e-8,
    'eps_rel': 1e-8,
    'max_iters': 500000,
}


def run_s4_for_threshold(seed, threshold, sequence_file, sequence_name, config, result_dir_base):
    """为指定 θ 运行 S4，结果写入 strategy4/ 或 strategy4_threshold_{θ}/strategy4/。"""
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
    reopt_count = sum(1 for s in strategy_stats if s.get('reoptimized', False))
    return stats_file, reopt_count


def main():
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    sequence_file = os.path.join(long_congested_base, str(SEED), 'arrival_rate_sequence_50_steps.csv')
    sequence_name = f"{SEQUENCE_DIR_NAME}/{SEED}"

    if not os.path.exists(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return

    config = load_yaml_file(config_file)

    print("=" * 80)
    print(f"使用精确求解器重新运行 Strategy 4 (seed={SEED})，θ=6, 8, 10")
    print("=" * 80)
    print(f"Solver options: {PRECISE_SOLVER_OPTIONS}")
    print()

    for threshold in THRESHOLDS:
        print(f"\n--- θ={threshold} ---")
        stats_file, reopt_count = run_s4_for_threshold(
            SEED, threshold, sequence_file, sequence_name, config, result_dir_base
        )
        print(f"✓ 已保存: {stats_file} (重优化 {reopt_count} 次)")

    print("\n" + "=" * 80)
    print("请运行: python -m main.visualize_regret_vs_time_long_congested --seed 7")
    print("以重新生成 regret_vs_time_seed7.png")
    print("=" * 80)


if __name__ == '__main__':
    main()
