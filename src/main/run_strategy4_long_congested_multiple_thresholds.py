#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行策略4 的多个阈值（θ=6, 10）在 long congested sequence 上，用于与现有 θ=8 对比。

θ=8 数据已由 run_strategy4_long_congested 生成在 strategy4/ 下；
本脚本为 θ=6 和 θ=10 生成数据，保存到 strategy4_threshold_6/ 与 strategy4_threshold_10/。
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

SEEDS = [0, 1, 7, 42, 123, 1234]
THRESHOLDS = [6, 10]  # θ=8 已有，只跑 6 和 10
SEQUENCE_DIR_NAME = 'long congested sequence'


def run_strategy4_for_seed_and_threshold(seed, sequence_file, sequence_name, config, result_dir_base, threshold):
    """为指定 seed 和阈值运行策略4，结果写入 strategy4_threshold_{threshold}/strategy4/。"""
    print(f"\n{'='*80}")
    print(f"运行策略4（θ={threshold}）在 {sequence_name} (seed={seed})")
    print(f"{'='*80}")

    if not os.path.exists(sequence_file):
        print(f"✗ 错误: 序列文件不存在: {sequence_file}")
        return None

    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values

    # 实验会把 step_X 写到 result_dir_base/strategy4/，因此传入的 base 要带 strategy4_threshold_{t}
    run_result_base = os.path.join(result_dir_base, sequence_name, f'strategy4_threshold_{threshold}')
    try:
        strategy_stats = execute_strategy_adaptive_reoptimization(
            sequence, config, run_result_base, threshold=threshold
        )
    except Exception as e:
        print(f"✗ 运行策略4（θ={threshold}）时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

    strategy_dir = os.path.join(run_result_base, 'strategy4')
    os.makedirs(strategy_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    stats_file = os.path.join(strategy_dir, 'strategy4_stats.csv')
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    df.to_csv(stats_file, index=False)
    print(f"✓ 已保存: {stats_file}")
    reopt_count = sum(1 for s in strategy_stats if s.get('reoptimized', False))
    print(f"  重优化次数: {reopt_count}/{len(strategy_stats)}")
    return strategy_stats


def main():
    print("=" * 80)
    print(f"运行策略4（θ=6, θ=10）在 long congested sequence（{len(SEEDS)} 个 seed）")
    print("=" * 80)
    print()

    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    config = load_yaml_file(config_file)

    for threshold in THRESHOLDS:
        for seed in SEEDS:
            sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"
            sequence_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
            run_strategy4_for_seed_and_threshold(
                seed, sequence_file, sequence_name, config, result_dir_base, threshold
            )
        print()

    print("=" * 80)
    print("✓ θ=6 与 θ=10 数据已生成。与 θ=8（strategy4/）一起可用于三阈值柱状图。")
    print("=" * 80)


if __name__ == '__main__':
    main()
