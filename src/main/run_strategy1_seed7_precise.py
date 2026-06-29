#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用精确求解器（ECOS abstol=1e-9, reltol=1e-9）重新运行 Strategy 1 在 seed 7 的 long congested 序列，
覆盖 strategy1_stats.csv，用于验证使用高精度求解后是否仍存在 regret 下降。
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_reoptimization

SEED = 7
SEQUENCE_DIR_NAME = 'long congested sequence'

# 精确求解选项：仅使用 SCS/通用参数，避免 Clarabel 等收到不支持的 abstol
# SCS: eps_abs, eps_rel, max_iters；提高迭代与收紧容差
PRECISE_SOLVER_OPTIONS = {
    'eps_abs': 1e-8,
    'eps_rel': 1e-8,
    'max_iters': 500000,
}


def main():
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    sequence_file = os.path.join(long_congested_base, str(SEED), 'arrival_rate_sequence_50_steps.csv')

    if not os.path.exists(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    sequence_name = f"{SEQUENCE_DIR_NAME}/{SEED}"

    print("=" * 80)
    print(f"使用精确求解器重新运行 Strategy 1 (seed={SEED})")
    print("=" * 80)
    print(f"Solver options: {PRECISE_SOLVER_OPTIONS}")
    print()

    strategy_stats, infeasible_steps = execute_strategy_reoptimization(
        sequence, config, result_dir_base,
        solver_options=PRECISE_SOLVER_OPTIONS
    )

    strategy_dir = os.path.join(result_dir_base, sequence_name, 'strategy1')
    os.makedirs(strategy_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    stats_file = os.path.join(strategy_dir, 'strategy1_stats.csv')
    df.to_csv(stats_file, index=False)
    print(f"\n✓ 已保存: {stats_file} (infeasible steps: {infeasible_steps})")
    print("\n请运行: python -m main.visualize_regret_vs_time_long_congested --seed 7")
    print("以重新生成 regret_vs_time_seed7.png")
    print("=" * 80)


if __name__ == '__main__':
    main()
