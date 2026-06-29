#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为hybrid_sequence生成策略4多个阈值版本的对比可视化
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10


def load_strategy4_data_with_threshold(threshold, results_base_dir):
    """加载指定阈值的策略4数据"""
    stats_file = os.path.join(
        results_base_dir, 'hybrid_sequence', 
        f'strategy4_threshold_{threshold}', 'strategy4_stats.csv'
    )
    
    if not os.path.exists(stats_file):
        return None
    
    df = pd.read_csv(stats_file)
    df['threshold'] = threshold
    return df


def plot_metric_comparison_multiple_thresholds(metric_name, thresholds, all_data, output_file):
    """绘制多个阈值版本的指标对比图"""
    # 准备数据
    plot_data = []
    for threshold in thresholds:
        threshold_data = all_data[all_data['threshold'] == threshold].copy()
        if len(threshold_data) > 0:
            threshold_data['strategy_label'] = f'Strategy 4 (θ={threshold})'
            plot_data.append(threshold_data)
    
    if not plot_data:
        print(f"  ⚠️  没有数据可绘制: {metric_name}")
        return
    
    combined_data = pd.concat(plot_data, ignore_index=True)
    
    # 创建图表
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 颜色映射
    colors = ['#d62728', '#ff7f0e', '#2ca02c', '#9467bd']  # Red, Orange, Green, Purple
    color_map = {threshold: colors[i % len(colors)] for i, threshold in enumerate(thresholds)}
    
    # 绘制每个阈值的数据
    for threshold in thresholds:
        threshold_data = combined_data[combined_data['threshold'] == threshold]
        if len(threshold_data) > 0:
            label = f'Strategy 4 (θ={threshold})'
            color = color_map[threshold]
            
            ax.plot(threshold_data['step_id'], threshold_data[metric_name],
                   marker='D', linestyle=':', linewidth=2, markersize=8,
                   label=label, color=color, alpha=0.8)
            
            # 标记触发重优化的时间步
            reoptimized_steps = threshold_data[threshold_data['reoptimized'] == True]['step_id']
            if len(reoptimized_steps) > 0:
                reoptimized_values = threshold_data[threshold_data['reoptimized'] == True][metric_name]
                ax.scatter(reoptimized_steps, reoptimized_values,
                          s=250, marker='*', color=color, edgecolors='black',
                          linewidth=2, zorder=5)
    
    # 设置标签和标题
    metric_labels = {
        'max_link_utilization': 'Max Link Utilization (%)',
        'max_link_utilization_theoretical': 'Theoretical Max Link Utilization (%)',
        'max_link_utilization_actual': 'Actual Max Link Utilization (%)',
        'pli': 'Packet Loss Index (%)',
        'avg_delay': 'Average Delay (ms)'
    }
    
    metric_title = {
        'max_link_utilization': 'Max Link Utilization',
        'max_link_utilization_theoretical': 'Theoretical Max Link Utilization',
        'max_link_utilization_actual': 'Actual Max Link Utilization',
        'pli': 'Packet Loss Index',
        'avg_delay': 'Average Delay'
    }
    
    # 如果列名不存在，尝试使用max_link_utilization
    if metric_name not in combined_data.columns:
        if metric_name == 'max_link_utilization_theoretical' and 'max_link_utilization' in combined_data.columns:
            metric_name = 'max_link_utilization'
    
    ax.set_xlabel('Time Step', fontweight='bold')
    ax.set_ylabel(metric_labels.get(metric_name, metric_name), fontweight='bold')
    ax.set_title(f'{metric_title.get(metric_name, metric_name)} - Strategy 4 Multiple Thresholds\n'
                 f'Hybrid Sequence', fontweight='bold', pad=20)
    
    # 添加网格和图例
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    # 创建图例
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        # 添加重优化标记的说明
        from matplotlib.lines import Line2D
        star_handle = Line2D([0], [0], marker='*', color='black', linestyle='None',
                            markersize=12, markeredgecolor='black', markeredgewidth=2,
                            label='Re-optimized step', markerfacecolor='none')
        handles.append(star_handle)
        labels.append('Re-optimized step')
        
        ax.legend(handles, labels, loc='best', framealpha=0.9, title='Thresholds')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ {metric_title.get(metric_name, metric_name)}对比图已保存: {os.path.basename(output_file)}")


def generate_visualizations(thresholds):
    """生成所有可视化图表"""
    print("=" * 80)
    print("生成策略4多阈值对比可视化")
    print("=" * 80)
    print()
    
    results_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', 'hybrid_sequence')
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载所有阈值的数据
    all_data_list = []
    for threshold in thresholds:
        data = load_strategy4_data_with_threshold(threshold, results_base_dir)
        if data is not None:
            all_data_list.append(data)
    
    if not all_data_list:
        print("✗ 没有找到任何策略4数据")
        return
    
    all_data = pd.concat(all_data_list, ignore_index=True)
    
    # 检查可用的列
    available_columns = all_data.columns.tolist()
    print(f"可用列: {available_columns}")
    
    # 生成各个指标的对比图
    metrics = []
    if 'max_link_utilization' in available_columns:
        metrics.append('max_link_utilization')
    if 'max_link_utilization_actual' in available_columns:
        metrics.append('max_link_utilization_actual')
    if 'pli' in available_columns:
        metrics.append('pli')
    if 'avg_delay' in available_columns:
        metrics.append('avg_delay')
    
    if not metrics:
        print("✗ 没有找到可用的指标列")
        return
    
    for metric in metrics:
        output_file = os.path.join(output_dir, f'strategy4_multiple_thresholds_{metric}.png')
        plot_metric_comparison_multiple_thresholds(metric, thresholds, all_data, output_file)
    
    # 生成触发重优化步骤的汇总图
    plot_reoptimization_summary(thresholds, all_data, output_dir)
    
    print("\n" + "=" * 80)
    print("✓ 所有可视化图表已生成！")
    print("=" * 80)
    print(f"输出目录: {output_dir}")


def plot_reoptimization_summary(thresholds, all_data, output_dir):
    """绘制重优化步骤汇总图"""
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 为每个阈值创建数据
    threshold_positions = {threshold: i for i, threshold in enumerate(thresholds)}
    colors = ['#d62728', '#ff7f0e', '#2ca02c', '#9467bd']
    
    for threshold in thresholds:
        threshold_data = all_data[all_data['threshold'] == threshold]
        reoptimized_steps = threshold_data[threshold_data['reoptimized'] == True]['step_id'].tolist()
        
        y_pos = threshold_positions[threshold]
        color = colors[thresholds.index(threshold) % len(colors)]
        
        # 绘制时间线
        if reoptimized_steps:
            ax.scatter(reoptimized_steps, [y_pos] * len(reoptimized_steps),
                      s=400, marker='*', color=color, edgecolors='black',
                      linewidth=2, zorder=5, label=f'θ={threshold}')
        
        # 绘制所有步骤（非重优化的用小点）
        all_steps = threshold_data['step_id'].tolist()
        non_reoptimized = [s for s in all_steps if s not in reoptimized_steps]
        if non_reoptimized:
            ax.scatter(non_reoptimized, [y_pos] * len(non_reoptimized),
                      s=50, marker='o', color=color, alpha=0.3, zorder=1)
    
    ax.set_xlabel('Time Step', fontweight='bold')
    ax.set_ylabel('Threshold', fontweight='bold')
    ax.set_yticks(range(len(thresholds)))
    ax.set_yticklabels([f'θ={t}' for t in thresholds])
    ax.set_title('Re-optimization Trigger Summary - Strategy 4\n'
                 'Hybrid Sequence (* = Re-optimized step)', fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='x', linestyle='--')
    ax.set_axisbelow(True)
    
    # 添加图例
    ax.legend(loc='upper right', framealpha=0.9, title='Thresholds')
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'strategy4_multiple_thresholds_reoptimization_summary.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ 重优化步骤汇总图已保存: strategy4_multiple_thresholds_reoptimization_summary.png")


def main():
    """主函数"""
    thresholds = [6, 8, 10, 12]
    generate_visualizations(thresholds)


if __name__ == '__main__':
    main()

