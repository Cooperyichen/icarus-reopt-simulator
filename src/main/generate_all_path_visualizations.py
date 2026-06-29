#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为所有序列生成完整的路径分配可视化内容

参照 increasing_sequence 的内容结构，为其他序列生成相同的可视化文件
"""

import sys
import os

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

# Import visualization scripts
import importlib.util

def load_module_from_file(filepath, module_name):
    """动态加载模块"""
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load modules
visualize_path_allocation = load_module_from_file(
    os.path.join(script_dir, 'visualize_path_allocation_distribution.py'),
    'visualize_path_allocation_distribution'
)
visualize_path_interval = load_module_from_file(
    os.path.join(script_dir, 'visualize_path_interval_changes.py'),
    'visualize_path_interval_changes'
)


def generate_all_visualizations():
    """为所有序列生成完整的可视化内容"""
    print("=" * 80)
    print("Generating All Path Allocation Visualizations")
    print("=" * 80)
    print()
    
    sequences = ['increasing_sequence', 'random_perturbation', 'hybrid_sequence']
    output_base_dir = os.path.join(src_dir, 'results', '可视化结果展示', '全优化流量分布')
    
    for sequence_name in sequences:
        print(f"\n{'='*80}")
        print(f"Processing: {sequence_name}")
        print(f"{'='*80}")
        
        # Step 1: 检查并生成 detailed_path_ratios.csv（如果需要）
        result_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
        analysis_dir = os.path.join(result_base_dir, sequence_name, 'strategy1', 'path_allocation_analysis')
        detailed_file = os.path.join(analysis_dir, 'detailed_path_ratios.csv')
        
        if not os.path.exists(detailed_file):
            print(f"\n⚠️  detailed_path_ratios.csv not found for {sequence_name}")
            print(f"   This sequence may not have strategy1 data.")
            print(f"   Skipping {sequence_name}...")
            continue
        else:
            print(f"✓ Found detailed_path_ratios.csv")
        
        output_dir = os.path.join(output_base_dir, sequence_name)
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 2: 生成路径分配分布图（step1 和 step10）
        print(f"\n--- Generating path allocation distribution charts ---")
        try:
            for step_id in [1, 10]:
                try:
                    visualize_path_allocation.create_path_allocation_bar_chart(sequence_name, step_id, output_dir)
                except Exception as e:
                    print(f"   ✗ Error generating step {step_id}: {e}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Step 3: 生成路径区间变化分析图
        print(f"\n--- Generating path interval change analysis charts ---")
        try:
            visualize_path_interval.visualize_path_interval_changes(sequence_name, output_dir)
        except Exception as e:
            print(f"   ✗ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n✓ Completed: {sequence_name}")
    
    print(f"\n{'='*80}")
    print("✓ All visualizations complete!")
    print(f"{'='*80}")
    print(f"\nOutput directory: {output_base_dir}")


if __name__ == '__main__':
    generate_all_visualizations()

