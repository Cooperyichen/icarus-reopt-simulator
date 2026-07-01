#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行 Strategy 1（每步重优化）在 long congested sequence 的 6 个 seed 上，作为 gap/regret 的基准。
结果保存到 long congested sequence/{seed}/strategy1/strategy1_stats.csv。
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

SEEDS = [0, 1, 7, 42, 123, 1234]
SEQUENCE_DIR_NAME = 'long congested sequence'


def run_strategy1_for_seed(seed, sequence_file, sequence_name, config, result_dir_base):
    """为指定 seed 运行 Strategy 1，保存 strategy1_stats.csv。"""
    print(f"\n{'='*80}")
    print(f"运行 Strategy 1 在 {sequence_name} (seed={seed})")
    print(f"{'='*80}")

    if not os.path.exists(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return None

    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values

    try:
        result_dir = os.path.join(result_dir_base, sequence_name)
        strategy_stats, infeasible_steps = execute_strategy_reoptimization(
            sequence, config, result_dir
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
        print(f"✓ 已保存: {stats_file} (infeasible steps: {infeasible_steps})")
        return strategy_stats
    except Exception as e:
        print(f"✗ 出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("=" * 80)
    print(f"运行 Strategy 1 在 long congested sequence（{len(SEEDS)} 个 seed）")
    print("=" * 80)
    print()

    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    config = load_yaml_file(config_file)

    for seed in SEEDS:
        sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"
        sequence_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
        run_strategy1_for_seed(seed, sequence_file, sequence_name, config, result_dir_base)
        print()

    print("=" * 80)
    print("✓ Strategy 1 运行完成。可运行 compute_gap_regret_long_congested 计算 gap 与 regret。")
    print("=" * 80)


if __name__ == '__main__':
    main()
