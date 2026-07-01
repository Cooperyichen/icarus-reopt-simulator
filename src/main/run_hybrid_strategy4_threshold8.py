#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行策略4（阈值=8）在hybrid_sequence上并生成可视化
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


def run_strategy4_for_hybrid(threshold=8):
    """运行策略4（阈值=8）在hybrid_sequence上"""
    print("=" * 80)
    print(f"运行策略4（阈值={threshold}）在 hybrid_sequence")
    print("=" * 80)
    print()
    
    # 配置
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_hybrid.csv')
    
    # 检查序列文件
    if not os.path.exists(sequence_file):
        print(f"✗ 错误: 序列文件不存在: {sequence_file}")
        return None
    
    # 加载配置和序列
    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    
    print(f"✓ 加载序列: {len(sequence)} 步, {sequence.shape[1]} 个commodities")
    print(f"  Step 1 arrival rates: {sequence[0].tolist()}")
    print(f"  Step {len(sequence)} arrival rates: {sequence[-1].tolist()}")
    print()
    
    # 运行策略4
    try:
        print("开始运行策略4...")
        strategy_stats = execute_strategy_adaptive_reoptimization(
            sequence, config, os.path.join(result_dir_base, 'hybrid_sequence'),
            threshold=threshold
        )
        
        # 保存统计信息到CSV
        strategy_dir = os.path.join(result_dir_base, 'hybrid_sequence', 'strategy4')
        os.makedirs(strategy_dir, exist_ok=True)
        
        df = pd.DataFrame(strategy_stats)
        stats_file = os.path.join(strategy_dir, 'strategy4_stats.csv')
        
        # 将arrival_rates列表转换为字符串以便CSV存储
        if 'arrival_rates' in df.columns:
            df['arrival_rates'] = df['arrival_rates'].apply(lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x)
        
        df.to_csv(stats_file, index=False)
        print(f"✓ 统计信息已保存到: {stats_file}")
        print()
        
        # 打印摘要
        print("=" * 80)
        print("执行摘要")
        print("=" * 80)
        print(f"  总步数: {len(strategy_stats)}")
        reoptimized_count = sum(1 for s in strategy_stats if s.get('reoptimized', False))
        print(f"  重新优化次数: {reoptimized_count}/{len(strategy_stats)}")
        print()
        
        return strategy_stats
            
    except Exception as e:
        print(f"✗ 运行策略4时出错: {e}")
        traceback.print_exc()
        return None


def generate_visualizations():
    """生成可视化图表（仅针对hybrid_sequence）"""
    print("=" * 80)
    print("生成可视化图表（仅hybrid_sequence）")
    print("=" * 80)
    print()
    
    try:
        from generate_comparison_visualizations import (
            load_strategy_data,
            load_sequence_data,
            generate_visualizations_for_sequence,
            STRATEGY_METADATA,
            SEQUENCE_FILE_MAP
        )
        
        sequence_name = 'hybrid_sequence'
        results_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
        output_base_dir = os.path.join(src_dir, 'results', '可视化结果展示')
        
        # 加载所有策略数据
        strategies = ['strategy1', 'strategy2', 'strategy3', 'strategy4']
        all_strategy_data_list = []
        
        for strategy_name in strategies:
            strategy_data = load_strategy_data(sequence_name, strategy_name, results_base_dir)
            if strategy_data is not None:
                all_strategy_data_list.append(strategy_data)
        
        if not all_strategy_data_list:
            print("✗ 没有找到任何策略数据")
            return
        
        all_strategy_data = pd.concat(all_strategy_data_list, ignore_index=True)
        
        # 加载序列数据
        sequence_df = load_sequence_data(sequence_name)
        
        # 生成可视化
        sequence_output_dir = os.path.join(output_base_dir, sequence_name)
        generate_visualizations_for_sequence(
            sequence_name, all_strategy_data, sequence_df,
            sequence_output_dir, STRATEGY_METADATA
        )
        
        print(f"✓ 可视化图表已生成到: {sequence_output_dir}")
        
    except Exception as e:
        print(f"✗ 生成可视化时出错: {e}")
        traceback.print_exc()


def main():
    """主函数"""
    threshold = 8
    
    # Step 1: 运行策略4
    strategy_stats = run_strategy4_for_hybrid(threshold=threshold)
    
    if strategy_stats is None:
        print("✗ 策略4运行失败，无法生成可视化")
        return
    
    # Step 2: 生成可视化
    print()
    generate_visualizations()
    
    print("=" * 80)
    print("✓ 所有任务完成！")
    print("=" * 80)
    print(f"结果保存在: src/results/可视化结果展示/hybrid_sequence/")


if __name__ == '__main__':
    main()

