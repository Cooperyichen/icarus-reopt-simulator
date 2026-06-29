#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行 hybrid_sequence 的 strategy1 实验并生成可视化
"""

import sys
import os
import pandas as pd

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_reoptimization
import importlib.util


def load_module_from_file(filepath, module_name):
    """动态加载模块"""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    """主函数"""
    print("=" * 80)
    print("Running Strategy 1 for Hybrid Sequence")
    print("=" * 80)
    print()
    
    # 配置
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    
    # 查找 hybrid_sequence 文件
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_hybrid.csv')
    
    if not os.path.exists(sequence_file):
        print("✗ Error: Could not find hybrid_sequence file")
        print(f"  Expected: {sequence_file}")
        return
    
    print(f"✓ Using sequence file: {sequence_file}")
    
    # 加载序列
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    num_steps, num_commodities = sequence.shape
    
    print(f"✓ Loaded sequence: {num_steps} steps, {num_commodities} commodities")
    print(f"  Step 1 arrival rates: {sequence[0].tolist()}")
    print(f"  Step {num_steps} arrival rates: {sequence[-1].tolist()}")
    print()
    
    # 加载配置
    config = load_yaml_file(config_file)
    print(f"✓ Configuration loaded: {config['scenario_name']}")
    print()
    
    # Step 1: 运行 strategy1 实验
    print("=" * 80)
    print("Step 1: Running Strategy 1 Experiment")
    print("=" * 80)
    print()
    
    try:
        strategy_stats, infeasible_steps = execute_strategy_reoptimization(
            sequence, config, result_dir_base
        )
        
        # 保存统计信息
        strategy_dir = os.path.join(result_dir_base, 'hybrid_sequence', 'strategy1')
        os.makedirs(strategy_dir, exist_ok=True)
        
        df = pd.DataFrame(strategy_stats)
        stats_file = os.path.join(strategy_dir, 'strategy1_stats.csv')
        df['arrival_rates'] = df['arrival_rates'].apply(lambda x: str(x) if isinstance(x, (list, pd.Series)) else x)
        df.to_csv(stats_file, index=False)
        
        print(f"✓ Strategy 1 experiment completed!")
        print(f"✓ Statistics saved to: {stats_file}")
        if infeasible_steps:
            print(f"⚠️  Infeasible steps: {infeasible_steps}")
        print()
    except Exception as e:
        print(f"✗ Error running Strategy 1: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: 生成路径分配分析数据
    print("=" * 80)
    print("Step 2: Generating Path Allocation Analysis Data")
    print("=" * 80)
    print()
    
    try:
        analyze_module = load_module_from_file(
            os.path.join(script_dir, 'analyze_strategy1_path_allocation_distribution.py'),
            'analyze_strategy1_path_allocation_distribution'
        )
        analyze_module.analyze_strategy1_path_distribution('hybrid_sequence')
        print("✓ Path allocation analysis data generated")
        print()
    except Exception as e:
        print(f"✗ Error generating analysis data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: 生成可视化
    print("=" * 80)
    print("Step 3: Generating Visualizations")
    print("=" * 80)
    print()
    
    try:
        # 加载可视化模块
        visualize_path_allocation = load_module_from_file(
            os.path.join(script_dir, 'visualize_path_allocation_distribution.py'),
            'visualize_path_allocation_distribution'
        )
        visualize_path_interval = load_module_from_file(
            os.path.join(script_dir, 'visualize_path_interval_changes.py'),
            'visualize_path_interval_changes'
        )
        
        output_base_dir = os.path.join(src_dir, 'results', '可视化结果展示', '全优化流量分布')
        output_dir = os.path.join(output_base_dir, 'hybrid_sequence')
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成路径分配分布图
        print("--- Generating path allocation distribution charts ---")
        for step_id in [1, 10]:
            try:
                visualize_path_allocation.create_path_allocation_bar_chart(
                    'hybrid_sequence', step_id, output_dir
                )
            except Exception as e:
                print(f"   ✗ Error generating step {step_id}: {e}")
        
        # 生成区间变化分析图
        print("\n--- Generating path interval change analysis charts ---")
        visualize_path_interval.visualize_path_interval_changes('hybrid_sequence', output_dir)
        
        print("\n✓ All visualizations generated!")
        print(f"  Output directory: {output_dir}")
        
    except Exception as e:
        print(f"✗ Error generating visualizations: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 80)
    print("✓ All steps completed successfully!")
    print("=" * 80)


if __name__ == '__main__':
    main()

