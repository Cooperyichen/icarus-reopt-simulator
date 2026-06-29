#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用当前优化器配置（STRICT_OPTIMAL_OPTIONS）重新计算指定 seed 的 Strategy 4 θ=4，
并更新 strategy4_threshold_4/strategy4/ 下的结果。
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
from main.multi_step_comparison_experiment import execute_strategy_adaptive_reoptimization

SEQUENCE_DIR_NAME = 'long congested sequence'
THRESHOLD = 4
DEFAULT_SEEDS = [14, 15, 20]

# 与 run_all_20seeds_precise 一致的精确求解配置
PRECISE_SOLVER_OPTIONS = {
    'eps_abs': 1e-8,
    'eps_rel': 1e-8,
    'max_iters': 500000,
}

# 严格最优：OPTIMAL_INACCURATE 时自动用 ECOS 重试
STRICT_OPTIMAL_OPTIONS = {
    **PRECISE_SOLVER_OPTIONS,
    'require_optimal_strict': True,
}


def main():
    parser = argparse.ArgumentParser(description='Re-run S4 θ=4 with precise solver')
    parser.add_argument('--seeds', type=str, default=None, help='Comma-separated seeds (default: 14,15,20)')
    args = parser.parse_args()
    seeds = [int(s.strip()) for s in (args.seeds or ','.join(map(str, DEFAULT_SEEDS))).split(',')]

    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)

    config = load_yaml_file(config_file)

    print("=" * 80)
    print(f"重新计算 S4 θ={THRESHOLD}，seed {seeds}")
    print(f"Solver options: {STRICT_OPTIMAL_OPTIONS}")
    print("=" * 80)

    for seed in seeds:
        sequence_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
        if not os.path.exists(sequence_file):
            print(f"\n✗ seed {seed}: 序列文件不存在 {sequence_file}")
            continue

        sequence_df = pd.read_csv(sequence_file, index_col=0)
        sequence = sequence_df.values
        sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"

        run_base = os.path.join(result_dir_base, sequence_name, f'strategy4_threshold_{THRESHOLD}')

        print(f"\n--- Seed {seed} ---")
        try:
            strategy_stats = execute_strategy_adaptive_reoptimization(
                sequence, config, run_base,
                threshold=THRESHOLD,
                solver_options=STRICT_OPTIMAL_OPTIONS
            )

            strategy_dir = os.path.join(run_base, 'strategy4')
            os.makedirs(strategy_dir, exist_ok=True)
            df = pd.DataFrame(strategy_stats)
            if 'arrival_rates' in df.columns:
                df['arrival_rates'] = df['arrival_rates'].apply(
                    lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
                )
            stats_file = os.path.join(strategy_dir, 'strategy4_stats.csv')
            df.to_csv(stats_file, index=False)
            print(f"✓ S4 θ={THRESHOLD} 已保存: {stats_file}")
        except Exception as e:
            print(f"✗ seed {seed} 失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("完成。可运行 compute_gap_regret_interevent_20seeds 或 visualize_regret_vs_time_long_congested 更新图表。")
    print("=" * 80)


if __name__ == '__main__':
    main()
