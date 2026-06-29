#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行策略4（阈值=8）在 long congested sequence 的各个 seed 上。

为每个 seed (0, 1, 7, 42, 123, 1234) 加载 arrival_rate_sequence_50_steps.csv，
执行 Strategy 4，结果保存到 long congested sequence/{seed}/strategy4/strategy4_stats.csv。
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
THRESHOLD = 8
SEQUENCE_DIR_NAME = 'long congested sequence'


def run_strategy4_for_seed(seed, sequence_file, sequence_name, config, result_dir_base, threshold=8):
    """
    为给定 seed 的序列运行策略4。

    Args:
        seed: 种子标识（用于日志）
        sequence_file: 包含到达率序列的CSV文件路径
        sequence_name: 序列名称（用于结果路径，如 "long congested sequence/0"）
        config: 配置字典
        result_dir_base: 结果基础目录（multi_step_comparison）
        threshold: 阈值参数（默认8）

    Returns:
        list: 策略统计信息列表，失败返回 None
    """
    print(f"\n{'='*80}")
    print(f"运行策略4（阈值={threshold}）在 {sequence_name} (seed={seed})")
    print(f"{'='*80}")

    if not os.path.exists(sequence_file):
        print(f"✗ 错误: 序列文件不存在: {sequence_file}")
        return None

    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values

    try:
        result_dir = os.path.join(result_dir_base, sequence_name)
        strategy_stats = execute_strategy_adaptive_reoptimization(
            sequence, config, result_dir, threshold=threshold
        )

        strategy_dir = os.path.join(result_dir_base, sequence_name, 'strategy4')
        os.makedirs(strategy_dir, exist_ok=True)

        df = pd.DataFrame(strategy_stats)
        stats_file = os.path.join(strategy_dir, 'strategy4_stats.csv')
        if 'arrival_rates' in df.columns:
            df['arrival_rates'] = df['arrival_rates'].apply(
                lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
            )
        df.to_csv(stats_file, index=False)
        print(f"✓ 统计信息已保存到: {stats_file}")

        reoptimized_count = sum(1 for s in strategy_stats if s.get('reoptimized', False))
        reoptimized_steps = [s['step_id'] for s in strategy_stats if s.get('reoptimized', False)]
        print(f"  重新优化次数: {reoptimized_count}/{len(strategy_stats)}")
        print(f"  重新优化步骤: {reoptimized_steps}")

        return strategy_stats
    except Exception as e:
        print(f"✗ 运行策略4时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("=" * 80)
    print(f"运行策略4（阈值={THRESHOLD}）在 long congested sequence（{len(SEEDS)} 个 seed）")
    print("=" * 80)
    print()

    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)

    config = load_yaml_file(config_file)
    results_summary = {}

    for seed in SEEDS:
        sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"
        sequence_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')

        strategy_stats = run_strategy4_for_seed(
            seed, sequence_file, sequence_name, config, result_dir_base, threshold=THRESHOLD
        )

        if strategy_stats is not None:
            results_summary[seed] = {
                'completed': True,
                'num_steps': len(strategy_stats),
                'reoptimized_count': sum(1 for s in strategy_stats if s.get('reoptimized', False)),
            }
        else:
            results_summary[seed] = {'completed': False}
        print()

    print("=" * 80)
    print("执行摘要")
    print("=" * 80)
    for seed in SEEDS:
        status = results_summary.get(seed, {})
        if status.get('completed', False):
            print(f"  seed {seed}: ✓ 完成 ({status.get('num_steps', 0)} 步, "
                  f"{status.get('reoptimized_count', 0)} 次重优化)")
        else:
            print(f"  seed {seed}: ✗ 失败")
    print("=" * 80)
    print("✓ 策略4（long congested sequence）执行完成！")
    print(f"结果已保存到: {result_dir_base}")
    print("\n下一步: 运行 pytest tests/test_strategy4_long_congested.py -v 进行验收，"
          "通过后运行 python -m main.visualize_long_congested_inter_event_cdf 生成 Figure 1。")


if __name__ == '__main__':
    main()
