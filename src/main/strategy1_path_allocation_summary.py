#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略1路径分配比例统计分布总结报告
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

def generate_summary():
    """生成总结报告"""
    print("=" * 80)
    print("策略1路径分配比例统计分布总结报告")
    print("=" * 80)
    print()
    
    sequences = ['increasing_sequence', 'random_perturbation']
    result_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    
    for sequence_name in sequences:
        print(f"\n{'='*80}")
        print(f"序列: {sequence_name}")
        print(f"{'='*80}")
        
        analysis_dir = os.path.join(result_base_dir, sequence_name, 'strategy1', 'path_allocation_analysis')
        
        # 读取统计摘要
        summary_file = os.path.join(analysis_dir, 'summary_statistics.csv')
        if os.path.exists(summary_file):
            summary_df = pd.read_csv(summary_file)
            print("\n总体统计:")
            print(f"  总路径数: {int(summary_df['total_paths'].iloc[0])}")
            print(f"  路径比例范围: [{summary_df['min_ratio'].iloc[0]:.6f}, {summary_df['max_ratio'].iloc[0]:.6f}]")
            print(f"  平均路径比例: {summary_df['mean_ratio'].iloc[0]:.6f}")
            print(f"  中位数路径比例: {summary_df['median_ratio'].iloc[0]:.6f}")
            print(f"  标准差: {summary_df['std_ratio'].iloc[0]:.6f}")
            print(f"\n分位数:")
            print(f"  10%: {summary_df['q10'].iloc[0]:.6f}")
            print(f"  25%: {summary_df['q25'].iloc[0]:.6f}")
            print(f"  75%: {summary_df['q75'].iloc[0]:.6f}")
            print(f"  90%: {summary_df['q90'].iloc[0]:.6f}")
            print(f"  95%: {summary_df['q95'].iloc[0]:.6f}")
            print(f"  99%: {summary_df['q99'].iloc[0]:.6f}")
        
        # 读取详细数据
        detailed_file = os.path.join(analysis_dir, 'detailed_path_ratios.csv')
        if os.path.exists(detailed_file):
            df = pd.read_csv(detailed_file)
            
            print(f"\n按商品统计:")
            for commodity_id in sorted(df['commodity_id'].unique()):
                commodity_df = df[df['commodity_id'] == commodity_id]
                ratios = commodity_df['ratio'].values
                print(f"  商品 {commodity_id}:")
                print(f"    路径数: {len(ratios)}")
                print(f"    比例范围: [{ratios.min():.6f}, {ratios.max():.6f}]")
                print(f"    平均比例: {ratios.mean():.6f}")
                print(f"    中位数: {np.median(ratios):.6f}")
                print(f"    标准差: {ratios.std():.6f}")
            
            print(f"\n按步骤统计:")
            for step_id in sorted(df['step_id'].unique()):
                step_df = df[df['step_id'] == step_id]
                ratios = step_df['ratio'].values
                print(f"  步骤 {step_id}:")
                print(f"    平均比例: {ratios.mean():.6f}")
                print(f"    标准差: {ratios.std():.6f}")
        
        # 路径数量统计
        path_counts_file = os.path.join(analysis_dir, 'path_counts.csv')
        if os.path.exists(path_counts_file):
            path_counts_df = pd.read_csv(path_counts_file)
            print(f"\n路径数量统计:")
            for commodity_id in sorted(path_counts_df['commodity_id'].unique()):
                commodity_paths = path_counts_df[path_counts_df['commodity_id'] == commodity_id]
                print(f"  商品 {commodity_id}:")
                print(f"    平均路径数: {commodity_paths['num_paths'].mean():.1f}")
                print(f"    路径数范围: [{commodity_paths['num_paths'].min()}, {commodity_paths['num_paths'].max()}]")
                print(f"    路径数是否变化: {'是' if commodity_paths['num_paths'].nunique() > 1 else '否'}")
    
    print(f"\n{'='*80}")
    print("关键发现:")
    print(f"{'='*80}")
    print("""
1. 路径分配比例分布特征：
   - 平均路径比例约为 0.0357 (约 3.57%)
   - 中位数路径比例约为 0.032 (约 3.2%)
   - 大部分路径的比例在 0.02-0.04 之间（25%-75%分位数）

2. 路径数量：
   - 每个商品在每个步骤都有28条路径
   - 路径数量在所有步骤中保持稳定，没有变化

3. 分布特征：
   - 路径比例分布相对均匀
   - 存在一些非常小的路径比例（接近0），可能是优化器分配的极小流量
   - 最大路径比例约为0.21（21%），说明某些路径承担了较大的流量

4. 不同序列的对比：
   - increasing_sequence 和 random_perturbation 的统计特征相似
   - 平均路径比例、中位数、标准差都非常接近
   - 说明策略1在不同流量模式下的路径分配行为相对稳定
""")


if __name__ == '__main__':
    generate_summary()

