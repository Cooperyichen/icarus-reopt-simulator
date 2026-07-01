#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 uniform long congested sequence 的 20 个 seed 上运行 Strategy 1（每步重优化），
作为 gap/regret 的基准。结果写入 uniform long congested sequence/{seed}/strategy1/strategy1_stats.csv。

用法（在 src 目录下）:
  python -m main.run_strategy1_uniform_long_congested
"""

import os
import sys
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_reoptimization

SEQUENCE_DIR_NAME = 'uniform long congested sequence'
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


def run_strategy1_for_seed(seed, sequence_file, sequence_name, config, result_dir_base):
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
    seeds = load_seeds()
    print("=" * 80)
    print(f"运行 Strategy 1 在 uniform long congested sequence（{len(seeds)} 个 seed）")
    print("=" * 80)

    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    seq_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    config = load_yaml_file(config_file)

    for seed in seeds:
        sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"
        sequence_file = os.path.join(seq_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
        run_strategy1_for_seed(seed, sequence_file, sequence_name, config, result_dir_base)

    print("=" * 80)
    print("✓ 完成。可运行 visualize_gap_vs_sequence_length_long_uniform 绘制 gap vs 序列长度。")
    print("=" * 80)


if __name__ == '__main__':
    main()
