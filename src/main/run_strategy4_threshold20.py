#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行策略4（阈值=20）在三个sequence上

这个脚本运行策略4（自适应重新优化）在以下三个序列上：
1. random_perturbation (随机扰动)
2. increasing_sequence (递增序列)
3. hybrid_sequence (混合序列)

阈值设置为20（而非默认的50）。
"""

import sys
import os
import pandas as pd
import numpy as np

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_adaptive_reoptimization


def run_strategy4_for_sequence(sequence_file, sequence_name, config, result_dir_base, threshold=20):
    """
    为给定序列运行策略4。
    
    Args:
        sequence_file: 包含到达率序列的CSV文件路径
        sequence_name: 序列名称
        config: 配置字典
        result_dir_base: 结果基础目录
        threshold: 阈值参数（默认20）
        
    Returns:
        list: 策略统计信息列表
    """
    print(f"\n{'='*80}")
    print(f"运行策略4（阈值={threshold}）在 {sequence_name}")
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
            sequence, config, os.path.join(result_dir_base, sequence_name),
            threshold=threshold
        )
        
        # 保存统计信息到CSV
        strategy_dir = os.path.join(result_dir_base, sequence_name, 'strategy4')
        os.makedirs(strategy_dir, exist_ok=True)
        
        df = pd.DataFrame(strategy_stats)
        stats_file = os.path.join(strategy_dir, 'strategy4_stats.csv')
        
        # 将arrival_rates列表转换为字符串以便CSV存储
        if 'arrival_rates' in df.columns:
            df['arrival_rates'] = df['arrival_rates'].apply(lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x)
        
        df.to_csv(stats_file, index=False)
        print(f"✓ 统计信息已保存到: {stats_file}")
        
        return strategy_stats
            
    except Exception as e:
        print(f"✗ 运行策略4时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数：运行策略4（阈值=20）在三个序列上"""
    
    print("=" * 80)
    print("运行策略4（阈值=20）在三个序列上")
    print("=" * 80)
    print()
    
    # 配置
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    threshold = 20  # 设置阈值为20
    
    # 加载配置
    config = load_yaml_file(config_file)
    
    # 要运行的序列
    sequences = {
        'random_perturbation': os.path.join(src_dir, 'results', 'arrival_rate_sequence_random.csv'),
        'increasing_sequence': os.path.join(src_dir, 'results', 'arrival_rate_sequence_increasing.csv'),
        'hybrid_sequence': os.path.join(src_dir, 'results', 'arrival_rate_sequence_hybrid.csv'),
    }
    
    # 跟踪结果
    results_summary = {}
    
    for sequence_name, sequence_file in sequences.items():
        print(f"\n{'='*80}")
        print(f"处理序列: {sequence_name}")
        print(f"{'='*80}")
        
        strategy_stats = run_strategy4_for_sequence(
            sequence_file, sequence_name, config, result_dir_base, threshold
        )
        
        if strategy_stats is not None:
            results_summary[sequence_name] = {
                'completed': True,
                'num_steps': len(strategy_stats)
            }
        else:
            results_summary[sequence_name] = {
                'completed': False
            }
        
        print()  # 序列之间的空行
    
    # 打印摘要
    print("\n" + "=" * 80)
    print("执行摘要")
    print("=" * 80)
    
    for sequence_name, status in results_summary.items():
        if status.get('completed', False):
            print(f"  {sequence_name}: ✓ 完成 ({status.get('num_steps', 0)} 步)")
        else:
            print(f"  {sequence_name}: ✗ 失败")
    
    print("\n" + "=" * 80)
    print("✓ 策略4（阈值=20）执行完成！")
    print("=" * 80)
    print(f"\n结果已保存到: {result_dir_base}")
    print("\n下一步: 运行 generate_comparison_visualizations.py 更新可视化结果。")


if __name__ == '__main__':
    main()

