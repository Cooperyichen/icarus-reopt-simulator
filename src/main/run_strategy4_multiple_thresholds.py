#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行策略4的多个阈值版本（6, 8, 10, 12）在hybrid_sequence上
"""

import sys
import os
import pandas as pd
import numpy as np
import traceback

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_adaptive_reoptimization


def run_strategy4_with_threshold(threshold, sequence_file, config, result_dir_base):
    """运行策略4（指定阈值）在hybrid_sequence上"""
    print(f"\n{'='*80}")
    print(f"运行策略4（阈值={threshold}）在 hybrid_sequence")
    print(f"{'='*80}")
    
    # 加载序列
    if not os.path.exists(sequence_file):
        print(f"✗ 错误: 序列文件不存在: {sequence_file}")
        return None
    
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    
    # 运行策略4
    try:
        strategy_stats = execute_strategy_adaptive_reoptimization(
            sequence, config, result_dir_base,
            threshold=threshold
        )
        
        # 保存统计信息到CSV（使用不同的文件名以区分阈值）
        strategy_dir = os.path.join(result_dir_base, 'hybrid_sequence', f'strategy4_threshold_{threshold}')
        os.makedirs(strategy_dir, exist_ok=True)
        
        df = pd.DataFrame(strategy_stats)
        stats_file = os.path.join(strategy_dir, 'strategy4_stats.csv')
        
        # 将arrival_rates列表转换为字符串以便CSV存储
        if 'arrival_rates' in df.columns:
            df['arrival_rates'] = df['arrival_rates'].apply(lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x)
        
        df.to_csv(stats_file, index=False)
        print(f"✓ 统计信息已保存到: {stats_file}")
        
        # 打印摘要
        reoptimized_count = sum(1 for s in strategy_stats if s.get('reoptimized', False))
        reoptimized_steps = [s['step_id'] for s in strategy_stats if s.get('reoptimized', False)]
        print(f"  重新优化次数: {reoptimized_count}/{len(strategy_stats)}")
        print(f"  重新优化步骤: {reoptimized_steps}")
        
        return strategy_stats
            
    except Exception as e:
        print(f"✗ 运行策略4（阈值={threshold}）时出错: {e}")
        traceback.print_exc()
        return None


def main():
    """主函数：运行多个阈值的策略4"""
    print("=" * 80)
    print("运行策略4的多个阈值版本（6, 8, 10, 12）在hybrid_sequence")
    print("=" * 80)
    print()
    
    # 配置
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_hybrid.csv')
    
    # 加载配置
    config = load_yaml_file(config_file)
    
    # 阈值列表
    thresholds = [6, 8, 10, 12]
    
    # 运行每个阈值
    results = {}
    for threshold in thresholds:
        strategy_stats = run_strategy4_with_threshold(
            threshold, sequence_file, config, result_dir_base
        )
        if strategy_stats is not None:
            results[threshold] = strategy_stats
        print()
    
    # 打印总结
    print("=" * 80)
    print("执行总结")
    print("=" * 80)
    for threshold in thresholds:
        if threshold in results:
            reoptimized_count = sum(1 for s in results[threshold] if s.get('reoptimized', False))
            print(f"  阈值 {threshold}: {reoptimized_count}/10 次重新优化")
        else:
            print(f"  阈值 {threshold}: ✗ 失败")
    
    print("\n" + "=" * 80)
    print("✓ 所有策略4实验完成！")
    print("=" * 80)


if __name__ == '__main__':
    main()

