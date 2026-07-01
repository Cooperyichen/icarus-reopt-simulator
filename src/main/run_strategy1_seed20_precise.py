#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用与 run_all_20seeds_precise 一致的精确求解器选项（含 require_optimal_strict）
重新运行 Strategy 1 在 seed 20 的 long congested 序列，覆盖 strategy1_stats.csv。

  python -m main.run_strategy1_seed20_precise

之后可重算 gap/regret 与 regret_vs_time 图：
  python -m main.compute_gap_regret_interevent_20seeds
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
from main.run_all_20seeds_precise import STRICT_OPTIMAL_OPTIONS

SEED = 20
SEQUENCE_DIR_NAME = 'long congested sequence'


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    long_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    sequence_file = os.path.join(long_base, str(SEED), 'arrival_rate_sequence_50_steps.csv')

    if not os.path.exists(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return

    config = load_yaml_file(config_file)
    sequence = pd.read_csv(sequence_file, index_col=0).values
    sequence_name = f"{SEQUENCE_DIR_NAME}/{SEED}"

    print("=" * 80)
    print(f"Strategy 1 精确重算 seed={SEED} (STRICT_OPTIMAL_OPTIONS)")
    print(f"Solver options: {STRICT_OPTIMAL_OPTIONS}")
    print("=" * 80)

    strategy_stats, infeasible_steps = execute_strategy_reoptimization(
        sequence, config, result_dir_base,
        solver_options=STRICT_OPTIMAL_OPTIONS,
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
    print("可选: python -m main.compute_gap_regret_interevent_20seeds")
    print("=" * 80)


if __name__ == '__main__':
    main()
