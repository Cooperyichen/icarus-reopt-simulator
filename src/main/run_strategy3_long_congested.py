#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 long congested sequence 的 20 个可行 seed 上运行 Strategy 3（全局最优路径比例）。

Step-1 MCFP 使用与 run_all_20seeds_precise 中 Strategy 4 相同的 solver_options。

  python -m main.run_strategy3_long_congested
  python -m main.run_strategy3_long_congested --strict-optimal
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_global_optimal_ratio
from main.run_all_20seeds_precise import PRECISE_SOLVER_OPTIONS, STRICT_OPTIMAL_OPTIONS

SEQUENCE_DIR_NAME = 'long congested sequence'


def load_feasible_seeds():
    path = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME,
                        'feasible_long_congested_seeds_20.csv')
    if os.path.isfile(path):
        return pd.read_csv(path)['seed'].astype(int).tolist()
    return [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 19, 20, 21, 23, 42, 123, 1234]


def run_strategy3_for_seed(seed, config, result_dir_base, solver_options):
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    sequence_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
    sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"
    run_base = os.path.join(result_dir_base, sequence_name)

    if not os.path.exists(sequence_file):
        print(f"✗ seed {seed}: 序列文件不存在: {sequence_file}")
        return False

    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values

    print("\n" + "=" * 80)
    print(f"Strategy 3 (global optimal ratio) — seed {seed}")
    print("=" * 80)

    strategy_stats = execute_strategy_global_optimal_ratio(
        sequence, config, run_base,
        solver_options=solver_options,
        global_ratio_minimize_options=None,
    )

    strategy_dir = os.path.join(run_base, 'strategy3')
    os.makedirs(strategy_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    stats_file = os.path.join(strategy_dir, 'strategy3_stats.csv')
    df.to_csv(stats_file, index=False)
    print(f"✓ strategy3_stats.csv 已保存: {stats_file}")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Run Strategy 3 on long congested sequence (20 feasible seeds, precise Step-1 MCFP)'
    )
    parser.add_argument('--seeds', type=str, default=None,
                        help='Comma-separated seeds (default: 20 feasible from CSV)')
    parser.add_argument('--skip', type=str, default=None, help='Comma-separated seeds to skip')
    parser.add_argument('--strict-optimal', action='store_true',
                        help='Require OPTIMAL MCFP status (same as run_all_20seeds_precise --strict-optimal)')
    args = parser.parse_args()

    if args.seeds:
        seeds = [int(s.strip()) for s in args.seeds.split(',')]
    else:
        seeds = load_feasible_seeds()

    if args.skip:
        skip = {int(s.strip()) for s in args.skip.split(',')}
        seeds = [s for s in seeds if s not in skip]

    solver_opts = STRICT_OPTIMAL_OPTIONS if args.strict_optimal else PRECISE_SOLVER_OPTIONS

    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    config = load_yaml_file(config_file)

    print("=" * 80)
    print(f"Strategy 3 — long congested sequence, {len(seeds)} seed(s)" +
          (" [strict optimal MCFP]" if args.strict_optimal else ""))
    print("=" * 80)

    ok = 0
    for i, seed in enumerate(seeds):
        print(f"\n[{i + 1}/{len(seeds)}]")
        if run_strategy3_for_seed(seed, config, result_dir_base, solver_opts):
            ok += 1

    print("\n" + "=" * 80)
    print(f"完成: {ok}/{len(seeds)} 成功。下一步: python -m main.check_strategy3_util_over_100_long_congested")
    print("  然后: python -m main.compute_gap_regret_interevent_20seeds")
    print("=" * 80)


if __name__ == '__main__':
    main()
