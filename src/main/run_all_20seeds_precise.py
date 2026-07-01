#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 20 个可行 long congested 序列使用精确求解器运行：
- Strategy 1 (基准)
- Strategy 2 (Path ratio scaling)
- Strategy 4 (θ=4, 6, 8, 10, 12)

结果保存到 multi_step_comparison/long congested sequence/{seed}/ 下。
"""

import sys
import os
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
THRESHOLDS = [4, 6, 8, 10, 12]

# ECOS-first（见 muti_commodity_optimizer._solve_kwargs_for_cvxpy_solver）：使用 abstol/reltol/feastol，
# 避免仅写 eps_abs 时先跑 SCS、ECOS 未吃到容差的问题。
PRECISE_SOLVER_OPTIONS = {
    'abstol': 1e-9,
    'reltol': 1e-9,
    'feastol': 1e-9,
    'abstol_inacc': 1e-9,
    'reltol_inacc': 1e-9,
    'feastol_inacc': 1e-9,
    'max_iters': 500000,
}

# 严格最优：OPTIMAL_INACCURATE 时自动用 ECOS 重试
STRICT_OPTIMAL_OPTIONS = {
    **PRECISE_SOLVER_OPTIONS,
    'require_optimal_strict': True,
}


def load_feasible_seeds():
    """从 feasible_long_congested_seeds_20.csv 加载种子列表。"""
    path = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME,
                        'feasible_long_congested_seeds_20.csv')
    if os.path.isfile(path):
        df = pd.read_csv(path)
        return df['seed'].astype(int).tolist()
    return [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 19, 20, 21, 23, 42, 123, 1234]


def run_s4_for_threshold(seed, threshold, sequence_file, sequence_name, config, result_dir_base, solver_options=None):
    """为指定 θ 运行 S4。"""
    opts = solver_options or PRECISE_SOLVER_OPTIONS
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
        solver_options=opts
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


def run_for_seed(seed, config_file, result_dir_base, solver_options=None):
    """为单个 seed 运行 S1, S2, S4 (θ=4,6,8,10,12)。"""
    opts = solver_options or PRECISE_SOLVER_OPTIONS
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    sequence_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
    sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"

    if not os.path.exists(sequence_file):
        print(f"✗ seed {seed}: 序列文件不存在")
        return False

    config = load_yaml_file(config_file)
    sequence = pd.read_csv(sequence_file, index_col=0).values

    print("\n" + "=" * 80)
    print(f"Seed {seed}: S1, S2, S4 (θ={THRESHOLDS})")
    print("=" * 80)

    # Strategy 1
    print("--- Strategy 1 ---")
    strategy_stats, infeasible = execute_strategy_reoptimization(
        sequence, config, os.path.join(result_dir_base, sequence_name),
        solver_options=opts
    )
    s1_dir = os.path.join(result_dir_base, sequence_name, 'strategy1')
    os.makedirs(s1_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    df.to_csv(os.path.join(s1_dir, 'strategy1_stats.csv'), index=False)
    print(f"✓ S1 已保存 (infeasible: {infeasible})")
    if infeasible:
        print(f"  ⚠ 存在不可行步，该 seed 可能不符合条件")

    # Strategy 2
    print("--- Strategy 2 (Path ratio scaling) ---")
    strategy_stats = execute_strategy_path_ratio_preservation(
        sequence, config, os.path.join(result_dir_base, sequence_name),
        solver_options=opts
    )
    s2_dir = os.path.join(result_dir_base, sequence_name, 'strategy2')
    os.makedirs(s2_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    df.to_csv(os.path.join(s2_dir, 'strategy2_stats.csv'), index=False)
    print("✓ S2 已保存")

    # Strategy 4 (θ=4, 6, 8, 10, 12)
    for threshold in THRESHOLDS:
        print(f"--- Strategy 4 (θ={threshold}) ---")
        try:
            run_s4_for_threshold(seed, threshold, sequence_file, sequence_name, config, result_dir_base, solver_options=opts)
            print(f"✓ S4 θ={threshold} 已保存")
        except Exception as e:
            print(f"✗ S4 θ={threshold} 失败: {e}")

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run S1, S2, S4 with precise solver for 20 feasible seeds')
    parser.add_argument('--seeds', type=str, default=None, help='Comma-separated seeds (default: 20 feasible)')
    parser.add_argument('--skip', type=str, default=None, help='Comma-separated seeds to skip')
    parser.add_argument('--strict-optimal', action='store_true', help='Require OPTIMAL (retry with ECOS if OPTIMAL_INACCURATE)')
    args = parser.parse_args()

    if args.seeds:
        seeds = [int(s.strip()) for s in args.seeds.split(',')]
    else:
        seeds = load_feasible_seeds()

    if args.skip:
        skip = {int(s.strip()) for s in args.skip.split(',')}
        seeds = [s for s in seeds if s not in skip]

    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    solver_opts = STRICT_OPTIMAL_OPTIONS if args.strict_optimal else PRECISE_SOLVER_OPTIONS

    print("=" * 80)
    print(f"精确求解：{len(seeds)} 个种子，S1 + S2 + S4 (θ={THRESHOLDS})" +
          (" [strict optimal]" if args.strict_optimal else ""))
    print("=" * 80)

    for i, seed in enumerate(seeds):
        print(f"\n[{i+1}/{len(seeds)}]")
        run_for_seed(seed, config_file, result_dir_base, solver_options=solver_opts)

    print("\n" + "=" * 80)
    print("运行完成。请执行 compute_gap_regret_interevent_20seeds 计算汇总并生成图表。")
    print("=" * 80)


if __name__ == '__main__':
    main()
