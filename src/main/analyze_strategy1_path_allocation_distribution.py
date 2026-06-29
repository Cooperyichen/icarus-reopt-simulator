#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析策略1的路径分配比例统计分布

功能：
1. 从策略1的MCFP结果文件中提取路径分配比例
2. 分析不同商品、不同步骤的路径分配比例分布
3. 生成统计报告和可视化
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file


def extract_path_ratios_from_csv(csv_file_path):
    """
    从MCFP结果CSV文件中提取路径分配比例
    
    Args:
        csv_file_path: CSV文件路径
        
    Returns:
        dict: {commodity_id: {path: ratio}}
    """
    df = pd.read_csv(csv_file_path)
    ratios_by_commodity = {}
    
    for commodity_id in df['id_flow'].unique():
        commodity_df = df[df['id_flow'] == commodity_id]
        total_flow = commodity_df['Arrival Rate'].sum()
        
        if total_flow > 0:
            path_ratios = {}
            for _, row in commodity_df.iterrows():
                path = row['Path']
                flow = row['Arrival Rate']
                path_ratios[path] = flow / total_flow
            ratios_by_commodity[int(commodity_id)] = path_ratios
        else:
            ratios_by_commodity[int(commodity_id)] = {}
    
    return ratios_by_commodity


def analyze_strategy1_path_distribution(sequence_name):
    """
    分析策略1在指定序列中的路径分配比例分布
    
    Args:
        sequence_name: 序列名称
    """
    print("=" * 80)
    print(f"分析策略1路径分配比例分布: {sequence_name}")
    print("=" * 80)
    print()
    
    result_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    strategy_name = 'strategy1'
    
    # 收集所有路径分配比例数据
    all_ratios = []  # 存储所有路径比例值
    ratios_by_commodity = defaultdict(list)  # 按商品分组
    ratios_by_step = defaultdict(list)  # 按步骤分组
    path_counts = []  # 每个商品的路径数量
    step_commodity_ratios = []  # 用于详细分析
    
    num_steps = 10
    num_commodities = 4
    
    # 遍历所有步骤
    for step_id in range(1, num_steps + 1):
        mcfp_file = os.path.join(result_base_dir, sequence_name, strategy_name, 
                                 f'step_{step_id}', f'mcfp_results_flows_{num_commodities}_commodities.csv')
        
        if not os.path.exists(mcfp_file):
            print(f"⚠️  步骤 {step_id} 文件不存在: {mcfp_file}")
            continue
        
        # 提取路径比例
        path_ratios = extract_path_ratios_from_csv(mcfp_file)
        
        # 收集数据
        for commodity_id, ratios in path_ratios.items():
            path_counts.append({
                'step_id': step_id,
                'commodity_id': commodity_id,
                'num_paths': len(ratios)
            })
            
            for path, ratio in ratios.items():
                all_ratios.append(ratio)
                ratios_by_commodity[commodity_id].append(ratio)
                ratios_by_step[step_id].append(ratio)
                
                step_commodity_ratios.append({
                    'step_id': step_id,
                    'commodity_id': commodity_id,
                    'path': path,
                    'ratio': ratio
                })
    
    # 转换为DataFrame
    all_ratios_df = pd.DataFrame({'ratio': all_ratios})
    step_commodity_df = pd.DataFrame(step_commodity_ratios)
    path_counts_df = pd.DataFrame(path_counts)
    
    # 打印统计信息
    print("1. 总体统计:")
    print(f"   总路径数: {len(all_ratios)}")
    print(f"   路径比例范围: [{all_ratios_df['ratio'].min():.6f}, {all_ratios_df['ratio'].max():.6f}]")
    print(f"   平均路径比例: {all_ratios_df['ratio'].mean():.6f}")
    print(f"   中位数路径比例: {all_ratios_df['ratio'].median():.6f}")
    print(f"   标准差: {all_ratios_df['ratio'].std():.6f}")
    print()
    
    # 分位数统计
    print("2. 分位数统计:")
    quantiles = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    for q in quantiles:
        value = all_ratios_df['ratio'].quantile(q)
        print(f"   {q*100:.0f}%分位数: {value:.6f}")
    print()
    
    # 按商品统计
    print("3. 按商品统计:")
    for commodity_id in sorted(ratios_by_commodity.keys()):
        ratios = ratios_by_commodity[commodity_id]
        ratios_array = np.array(ratios)
        print(f"   商品 {commodity_id}:")
        print(f"     路径数: {len(ratios)}")
        print(f"     比例范围: [{ratios_array.min():.6f}, {ratios_array.max():.6f}]")
        print(f"     平均比例: {ratios_array.mean():.6f}")
        print(f"     中位数: {np.median(ratios_array):.6f}")
        print(f"     标准差: {ratios_array.std():.6f}")
    print()
    
    # 按步骤统计
    print("4. 按步骤统计:")
    for step_id in sorted(ratios_by_step.keys()):
        ratios = ratios_by_step[step_id]
        ratios_array = np.array(ratios)
        print(f"   步骤 {step_id}:")
        print(f"     路径数: {len(ratios)}")
        print(f"     平均比例: {ratios_array.mean():.6f}")
        print(f"     标准差: {ratios_array.std():.6f}")
    print()
    
    # 路径数量统计
    print("5. 每个商品的路径数量统计:")
    if len(path_counts_df) > 0:
        for commodity_id in sorted(path_counts_df['commodity_id'].unique()):
            commodity_paths = path_counts_df[path_counts_df['commodity_id'] == commodity_id]
            print(f"   商品 {commodity_id}:")
            print(f"     平均路径数: {commodity_paths['num_paths'].mean():.1f}")
            print(f"     路径数范围: [{commodity_paths['num_paths'].min()}, {commodity_paths['num_paths'].max()}]")
            print(f"     路径数是否变化: {'是' if commodity_paths['num_paths'].nunique() > 1 else '否'}")
    print()
    
    # 保存详细数据
    output_dir = os.path.join(result_base_dir, sequence_name, strategy_name, 'path_allocation_analysis')
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存所有路径比例数据
    all_ratios_file = os.path.join(output_dir, 'all_path_ratios.csv')
    all_ratios_df.to_csv(all_ratios_file, index=False)
    print(f"✓ 所有路径比例数据已保存: {all_ratios_file}")
    
    # 保存详细数据
    detailed_file = os.path.join(output_dir, 'detailed_path_ratios.csv')
    step_commodity_df.to_csv(detailed_file, index=False)
    print(f"✓ 详细路径比例数据已保存: {detailed_file}")
    
    # 保存路径数量统计
    path_counts_file = os.path.join(output_dir, 'path_counts.csv')
    path_counts_df.to_csv(path_counts_file, index=False)
    print(f"✓ 路径数量统计已保存: {path_counts_file}")
    
    # 生成统计摘要
    summary_data = {
        'total_paths': len(all_ratios),
        'min_ratio': all_ratios_df['ratio'].min(),
        'max_ratio': all_ratios_df['ratio'].max(),
        'mean_ratio': all_ratios_df['ratio'].mean(),
        'median_ratio': all_ratios_df['ratio'].median(),
        'std_ratio': all_ratios_df['ratio'].std(),
        'q10': all_ratios_df['ratio'].quantile(0.1),
        'q25': all_ratios_df['ratio'].quantile(0.25),
        'q75': all_ratios_df['ratio'].quantile(0.75),
        'q90': all_ratios_df['ratio'].quantile(0.90),
        'q95': all_ratios_df['ratio'].quantile(0.95),
        'q99': all_ratios_df['ratio'].quantile(0.99),
    }
    
    summary_df = pd.DataFrame([summary_data])
    summary_file = os.path.join(output_dir, 'summary_statistics.csv')
    summary_df.to_csv(summary_file, index=False)
    print(f"✓ 统计摘要已保存: {summary_file}")
    
    # 生成可视化
    print("\n生成可视化图表...")
    generate_visualizations(all_ratios_df, step_commodity_df, path_counts_df, output_dir, sequence_name)
    
    print("\n" + "=" * 80)
    print("✓ 分析完成")
    print("=" * 80)


def generate_visualizations(all_ratios_df, step_commodity_df, path_counts_df, output_dir, sequence_name):
    """生成可视化图表"""
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 1. 路径比例分布直方图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1.1 总体分布
    ax = axes[0, 0]
    ax.hist(all_ratios_df['ratio'], bins=50, edgecolor='black', alpha=0.7)
    ax.set_xlabel('路径分配比例', fontsize=12)
    ax.set_ylabel('频数', fontsize=12)
    ax.set_title('路径分配比例总体分布', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # 1.2 对数尺度分布
    ax = axes[0, 1]
    positive_ratios = all_ratios_df[all_ratios_df['ratio'] > 0]['ratio']
    ax.hist(positive_ratios, bins=50, edgecolor='black', alpha=0.7)
    ax.set_xlabel('路径分配比例', fontsize=12)
    ax.set_ylabel('频数', fontsize=12)
    ax.set_title('路径分配比例分布（对数尺度）', fontsize=14, fontweight='bold')
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3)
    
    # 1.3 按商品分组
    ax = axes[1, 0]
    for commodity_id in sorted(step_commodity_df['commodity_id'].unique()):
        commodity_ratios = step_commodity_df[step_commodity_df['commodity_id'] == commodity_id]['ratio']
        ax.hist(commodity_ratios, bins=30, alpha=0.5, label=f'商品 {commodity_id}', edgecolor='black')
    ax.set_xlabel('路径分配比例', fontsize=12)
    ax.set_ylabel('频数', fontsize=12)
    ax.set_title('按商品分组的路径分配比例分布', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 1.4 箱线图
    ax = axes[1, 1]
    data_for_box = [step_commodity_df[step_commodity_df['commodity_id'] == cid]['ratio'].values 
                     for cid in sorted(step_commodity_df['commodity_id'].unique())]
    ax.boxplot(data_for_box, labels=[f'商品 {i}' for i in sorted(step_commodity_df['commodity_id'].unique())])
    ax.set_ylabel('路径分配比例', fontsize=12)
    ax.set_title('按商品分组的路径分配比例箱线图', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    dist_file = os.path.join(output_dir, 'path_ratio_distribution.png')
    plt.savefig(dist_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 分布图已保存: {os.path.basename(dist_file)}")
    
    # 2. 按步骤的变化趋势
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # 2.1 平均路径比例随时间变化
    ax = axes[0]
    step_means = step_commodity_df.groupby('step_id')['ratio'].mean()
    step_stds = step_commodity_df.groupby('step_id')['ratio'].std()
    ax.plot(step_means.index, step_means.values, marker='o', linewidth=2, label='平均值')
    ax.fill_between(step_means.index, 
                    step_means.values - step_stds.values,
                    step_means.values + step_stds.values,
                    alpha=0.3, label='±1标准差')
    ax.set_xlabel('步骤', fontsize=12)
    ax.set_ylabel('平均路径分配比例', fontsize=12)
    ax.set_title('平均路径分配比例随时间变化', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2.2 路径数量随时间变化
    ax = axes[1]
    for commodity_id in sorted(path_counts_df['commodity_id'].unique()):
        commodity_paths = path_counts_df[path_counts_df['commodity_id'] == commodity_id]
        ax.plot(commodity_paths['step_id'], commodity_paths['num_paths'], 
               marker='o', label=f'商品 {commodity_id}', linewidth=2)
    ax.set_xlabel('步骤', fontsize=12)
    ax.set_ylabel('路径数量', fontsize=12)
    ax.set_title('每个商品的路径数量随时间变化', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    trend_file = os.path.join(output_dir, 'path_ratio_trends.png')
    plt.savefig(trend_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 趋势图已保存: {os.path.basename(trend_file)}")
    
    # 3. 热力图：每个商品在不同步骤的平均路径比例
    fig, ax = plt.subplots(figsize=(12, 6))
    pivot_data = step_commodity_df.groupby(['step_id', 'commodity_id'])['ratio'].mean().unstack(fill_value=0)
    sns.heatmap(pivot_data, annot=True, fmt='.4f', cmap='YlOrRd', ax=ax, cbar_kws={'label': '平均路径比例'})
    ax.set_xlabel('商品ID', fontsize=12)
    ax.set_ylabel('步骤', fontsize=12)
    ax.set_title('每个商品在不同步骤的平均路径分配比例', fontsize=14, fontweight='bold')
    plt.tight_layout()
    heatmap_file = os.path.join(output_dir, 'path_ratio_heatmap.png')
    plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ 热力图已保存: {os.path.basename(heatmap_file)}")


def main():
    """主函数"""
    sequences = ['increasing_sequence', 'hybrid_sequence', 'random_perturbation']
    
    for sequence_name in sequences:
        try:
            analyze_strategy1_path_distribution(sequence_name)
            print("\n\n")
        except Exception as e:
            print(f"✗ 分析 {sequence_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
            print("\n\n")


if __name__ == '__main__':
    main()

