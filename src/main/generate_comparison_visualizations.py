#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成多步骤策略对比可视化图表和数据统一存储

功能：
1. 整合所有策略和序列的数据到统一CSV文件
2. 为每个序列生成4个指标的对比图（理论利用率、实际利用率、PLI、延迟）
3. 为每个序列生成arrival rate时间序列图
4. 支持新策略和序列的轻松扩展
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import ast

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

# 策略元数据映射
STRATEGY_METADATA = {
    'strategy1': {
        'name': 'Strategy 1 (Re-optimization)',
        'color': '#1f77b4',  # Blue
        'marker': 'o',
        'linestyle': '-'
    },
    'strategy2': {
        'name': 'Strategy 2 (Path Ratio Preservation)',
        'color': '#ff7f0e',  # Orange
        'marker': 's',
        'linestyle': '--'
    },
    'strategy3': {
        'name': 'Strategy 3 (Global Optimal Ratio)',
        'color': '#2ca02c',  # Green
        'marker': '^',
        'linestyle': '-.'
    },
    'strategy4': {
        'name': 'Strategy 4 (Adaptive Re-optimization)',
        'color': '#d62728',  # Red
        'marker': 'D',
        'linestyle': ':'
    }
}

# 序列文件路径映射
SEQUENCE_FILE_MAP = {
    'random_perturbation': 'arrival_rate_sequence_random.csv',
    'increasing_sequence': 'arrival_rate_sequence_increasing.csv',
    'hybrid_sequence': 'arrival_rate_sequence_hybrid.csv'
}


def load_strategy_data(sequence_name, strategy_name, results_base_dir):
    """
    加载特定序列和策略的统计数据CSV。
    
    Args:
        sequence_name: 序列名称（random_perturbation, increasing_sequence, hybrid_sequence）
        strategy_name: 策略名称（strategy1, strategy2, strategy3, strategy4）
        results_base_dir: 结果根目录路径
        
    Returns:
        DataFrame: 策略统计数据，如果文件不存在则返回None
    """
    # 首先尝试从子目录加载
    subdir_file = os.path.join(results_base_dir, sequence_name, strategy_name, f'{strategy_name}_stats.csv')
    
    # 如果子目录文件不存在，尝试根目录（用于hybrid序列的策略1和2）
    root_file = os.path.join(results_base_dir, f'{strategy_name}_stats.csv')
    
    stats_file = None
    if os.path.exists(subdir_file):
        stats_file = subdir_file
    elif sequence_name == 'hybrid_sequence' and strategy_name in ['strategy1', 'strategy2']:
        # 对于hybrid序列的策略1和2，使用根目录文件
        if os.path.exists(root_file):
            stats_file = root_file
    
    if stats_file is None or not os.path.exists(stats_file):
        return None
    
    try:
        df = pd.read_csv(stats_file)
        
        # 标准化列名（处理可能的命名差异）
        # 确保包含必要的列
        required_columns = ['step_id', 'arrival_rates', 'max_link_utilization', 'pli', 'avg_delay']
        
        # 添加sequence_name和strategy列
        df['sequence_name'] = sequence_name
        df['strategy'] = strategy_name
        
        # 重命名列以统一格式
        if 'max_link_utilization' in df.columns:
            df = df.rename(columns={'max_link_utilization': 'max_link_utilization_theoretical'})
        
        # 确保有actual列（可能为NaN）
        if 'max_link_utilization_actual' not in df.columns:
            df['max_link_utilization_actual'] = np.nan
        
        return df
    except Exception as e:
        print(f"  ⚠️  加载{strategy_name}数据时出错: {e}")
        return None


def load_sequence_data(sequence_name):
    """
    加载arrival rate序列CSV。
    
    Args:
        sequence_name: 序列名称
        
    Returns:
        DataFrame: 序列数据，列：Time_Step, Commodity_0-3
    """
    if sequence_name not in SEQUENCE_FILE_MAP:
        raise ValueError(f"未知序列名称: {sequence_name}")
    
    sequence_file = os.path.join(src_dir, 'results', SEQUENCE_FILE_MAP[sequence_name])
    
    if not os.path.exists(sequence_file):
        print(f"  ⚠️  序列文件不存在: {sequence_file}")
        return None
    
    df = pd.read_csv(sequence_file, index_col=0)
    return df


def consolidate_all_strategy_data(sequences, strategies, results_base_dir, output_file):
    """
    将所有策略数据整合为统一CSV。
    
    Args:
        sequences: 序列名称列表
        strategies: 策略名称列表
        results_base_dir: 结果根目录
        output_file: 输出CSV文件路径
        
    Returns:
        DataFrame: 整合后的数据
    """
    all_data = []
    
    for sequence_name in sequences:
        for strategy_name in strategies:
            print(f"  加载 {sequence_name}/{strategy_name}...", end=' ')
            df = load_strategy_data(sequence_name, strategy_name, results_base_dir)
            
            if df is not None and len(df) > 0:
                all_data.append(df)
                print(f"✓ ({len(df)} 行)")
            else:
                print("✗ (无数据)")
    
    if not all_data:
        print("  ⚠️  未找到任何数据！")
        return None
    
    # 合并所有数据
    unified_df = pd.concat(all_data, ignore_index=True)
    
    # 确保列顺序一致
    column_order = [
        'sequence_name', 'strategy', 'step_id', 'arrival_rates',
        'max_link_utilization_theoretical', 'max_link_utilization_actual',
        'pli', 'avg_delay', 'trigger_metric', 'reoptimized',
        'optimizer_feasible', 'optimizer_status'
    ]
    
    # 只保留存在的列
    existing_columns = [col for col in column_order if col in unified_df.columns]
    other_columns = [col for col in unified_df.columns if col not in existing_columns]
    unified_df = unified_df[existing_columns + other_columns]
    
    # 保存到CSV
    unified_df.to_csv(output_file, index=False)
    print(f"\n✓ 统一数据已保存到: {output_file}")
    print(f"  总行数: {len(unified_df)}")
    print(f"  序列数: {unified_df['sequence_name'].nunique()}")
    print(f"  策略数: {unified_df['strategy'].nunique()}")
    
    return unified_df


def plot_arrival_rate_sequence(sequence_df, output_file):
    """
    绘制所有commodity的arrival rate时间序列。
    
    Args:
        sequence_df: 序列DataFrame（列：Time_Step, Commodity_0-3）
        output_file: 输出文件路径
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    steps = sequence_df.index.values  # Time_Step (1-10)
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#9467bd']
    
    for i, col in enumerate(['Commodity_0', 'Commodity_1', 'Commodity_2', 'Commodity_3']):
        if col in sequence_df.columns:
            ax.plot(steps, sequence_df[col], 'o-', label=col, 
                   color=colors[i], linewidth=2, markersize=6)
    
    ax.set_xlabel('Time Step', fontsize=12)
    ax.set_ylabel('Arrival Rate (packets/s)', fontsize=12)
    ax.set_title('Arrival Rate Time Series', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Arrival rate序列图已保存: {os.path.basename(output_file)}")


def plot_metric_comparison(sequence_name, metric_name, all_strategy_data, output_file, strategy_metadata):
    """
    通用的指标对比绘图函数。
    
    Args:
        sequence_name: 序列名称
        metric_name: 指标名称（max_link_utilization_theoretical, max_link_utilization_actual, pli, avg_delay）
        all_strategy_data: 所有策略数据的DataFrame（统一格式）
        output_file: 输出文件路径
        strategy_metadata: 策略元数据字典
    """
    # 筛选当前序列的数据
    sequence_data = all_strategy_data[all_strategy_data['sequence_name'] == sequence_name].copy()
    
    if len(sequence_data) == 0:
        print(f"  ⚠️  {sequence_name} 无数据，跳过 {metric_name} 图表")
        return
    
    # 检测哪些策略有数据
    available_strategies = sequence_data['strategy'].unique().tolist()
    
    if not available_strategies:
        print(f"  ⚠️  {sequence_name} 无可用策略，跳过 {metric_name} 图表")
        return
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # 为每个策略绘制数据
    for strategy in available_strategies:
        strategy_data = sequence_data[sequence_data['strategy'] == strategy]
        
        if metric_name not in strategy_data.columns:
            continue
        
        # 过滤NaN值
        valid_data = strategy_data[['step_id', metric_name]].dropna(subset=[metric_name])
        
        if len(valid_data) == 0:
            continue
        
        steps = valid_data['step_id'].values
        values = valid_data[metric_name].values
        
        # 获取策略元数据
        if strategy in strategy_metadata:
            meta = strategy_metadata[strategy]
            label = meta['name']
            color = meta['color']
            marker = meta['marker']
            linestyle = meta['linestyle']
        else:
            label = strategy
            color = None
            marker = 'o'
            linestyle = '-'
        
        ax.plot(steps, values, marker=marker, linestyle=linestyle, label=label,
               color=color, linewidth=2, markersize=6)
    
    # 设置标签和标题
    if metric_name == 'max_link_utilization_theoretical':
        ylabel = 'Theoretical Max Link Utilization (%)'
        title = 'Theoretical Max Link Utilization Comparison'
    elif metric_name == 'max_link_utilization_actual':
        ylabel = 'Actual Max Link Utilization (%)'
        title = 'Actual Max Link Utilization Comparison'
    elif metric_name == 'pli':
        ylabel = 'Packet Loss Indicator (PLI) (%)'
        title = 'PLI Comparison'
    elif metric_name == 'avg_delay':
        ylabel = 'Average Delay (s)'
        title = 'Average Delay Comparison'
    else:
        ylabel = metric_name
        title = f'{metric_name} Comparison'
    
    ax.set_xlabel('Time Step', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ {title}已保存: {os.path.basename(output_file)}")


def generate_visualizations_for_sequence(sequence_name, all_strategy_data, sequence_df, output_dir, strategy_metadata):
    """
    为单个序列生成所有图表。
    
    Args:
        sequence_name: 序列名称
        all_strategy_data: 所有策略数据的DataFrame
        sequence_df: 序列DataFrame
        output_dir: 输出目录
        strategy_metadata: 策略元数据字典
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n生成 {sequence_name} 的可视化图表...")
    
    # 1. Arrival rate序列图
    if sequence_df is not None:
        arrival_plot = os.path.join(output_dir, 'arrival_rate_sequence.png')
        plot_arrival_rate_sequence(sequence_df, arrival_plot)
    
    # 2-5. 指标对比图
    metrics = [
        'max_link_utilization_theoretical',
        'max_link_utilization_actual',
        'pli',
        'avg_delay'
    ]
    
    for metric in metrics:
        plot_file = os.path.join(output_dir, f'{metric}_comparison.png')
        plot_metric_comparison(sequence_name, metric, all_strategy_data, plot_file, strategy_metadata)


def generate_all_visualizations(sequences, strategies, results_base_dir, output_base_dir, strategy_metadata):
    """
    主协调函数：生成所有可视化。
    
    Args:
        sequences: 序列名称列表
        strategies: 策略名称列表
        results_base_dir: 结果根目录
        output_base_dir: 输出根目录
        strategy_metadata: 策略元数据字典
    """
    print("=" * 80)
    print("生成多步骤策略对比可视化")
    print("=" * 80)
    print()
    
    # 创建输出目录
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 1. 整合所有策略数据
    print("步骤1: 整合所有策略数据...")
    unified_file = os.path.join(output_base_dir, 'unified_strategy_data.csv')
    all_strategy_data = consolidate_all_strategy_data(sequences, strategies, results_base_dir, unified_file)
    
    if all_strategy_data is None:
        print("\n✗ 无法整合数据，退出")
        return
    
    # 2. 为每个序列生成图表
    print("\n步骤2: 生成可视化图表...")
    
    for sequence_name in sequences:
        # 加载序列数据
        sequence_df = load_sequence_data(sequence_name)
        
        # 生成图表
        sequence_output_dir = os.path.join(output_base_dir, sequence_name)
        generate_visualizations_for_sequence(
            sequence_name, all_strategy_data, sequence_df, 
            sequence_output_dir, strategy_metadata
        )
    
    print("\n" + "=" * 80)
    print("✓ 所有可视化已完成！")
    print("=" * 80)
    print(f"\n输出目录: {output_base_dir}")
    print(f"统一数据文件: {unified_file}")


def main():
    """主函数"""
    # 配置
    sequences = ['random_perturbation', 'increasing_sequence', 'hybrid_sequence']
    strategies = ['strategy1', 'strategy2', 'strategy3', 'strategy4']
    results_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    output_base_dir = os.path.join(src_dir, 'results', '可视化结果展示')
    
    # 生成所有可视化
    generate_all_visualizations(
        sequences, strategies, results_base_dir, 
        output_base_dir, STRATEGY_METADATA
    )


if __name__ == '__main__':
    main()

