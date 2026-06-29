#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新hybrid_sequence的可视化，包含多个阈值的策略4
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
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
    }
}

# 策略4多阈值元数据
STRATEGY4_THRESHOLDS = [6, 8, 10, 12]
STRATEGY4_COLORS = ['#d62728', '#ff7f0e', '#2ca02c', '#9467bd']  # Red, Orange, Green, Purple


def load_strategy_data(sequence_name, strategy_name, results_base_dir):
    """加载策略数据"""
    subdir_file = os.path.join(results_base_dir, sequence_name, strategy_name, f'{strategy_name}_stats.csv')
    root_file = os.path.join(results_base_dir, f'{strategy_name}_stats.csv')
    
    stats_file = None
    if os.path.exists(subdir_file):
        stats_file = subdir_file
    elif sequence_name == 'hybrid_sequence' and strategy_name in ['strategy1', 'strategy2']:
        if os.path.exists(root_file):
            stats_file = root_file
    
    if stats_file is None or not os.path.exists(stats_file):
        return None
    
    try:
        df = pd.read_csv(stats_file)
        df['sequence_name'] = sequence_name
        df['strategy'] = strategy_name
        if 'max_link_utilization' in df.columns:
            df = df.rename(columns={'max_link_utilization': 'max_link_utilization_theoretical'})
        if 'max_link_utilization_actual' not in df.columns:
            df['max_link_utilization_actual'] = np.nan
        return df
    except Exception as e:
        print(f"  ⚠️  加载{strategy_name}数据时出错: {e}")
        return None


def load_strategy4_multiple_thresholds(results_base_dir):
    """加载多个阈值的策略4数据"""
    all_data = []
    for threshold in STRATEGY4_THRESHOLDS:
        stats_file = os.path.join(
            results_base_dir, 'hybrid_sequence',
            f'strategy4_threshold_{threshold}', 'strategy4_stats.csv'
        )
        if os.path.exists(stats_file):
            try:
                df = pd.read_csv(stats_file)
                df['sequence_name'] = 'hybrid_sequence'
                df['strategy'] = f'strategy4_threshold_{threshold}'
                df['threshold'] = threshold
                if 'max_link_utilization' in df.columns:
                    df = df.rename(columns={'max_link_utilization': 'max_link_utilization_theoretical'})
                if 'max_link_utilization_actual' not in df.columns:
                    df['max_link_utilization_actual'] = np.nan
                all_data.append(df)
            except Exception as e:
                print(f"  ⚠️  加载策略4（阈值={threshold}）数据时出错: {e}")
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return None


def plot_metric_comparison_with_multiple_thresholds(metric_name, all_strategy_data, strategy4_data, output_file):
    """绘制包含多个阈值策略4的指标对比图"""
    sequence_name = 'hybrid_sequence'
    sequence_data = all_strategy_data[all_strategy_data['sequence_name'] == sequence_name].copy()
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # 绘制其他策略
    available_strategies = sequence_data['strategy'].unique().tolist()
    for strategy in available_strategies:
        if strategy.startswith('strategy4'):
            continue
        
        strategy_data = sequence_data[sequence_data['strategy'] == strategy]
        if metric_name not in strategy_data.columns:
            continue
        
        valid_data = strategy_data[['step_id', metric_name]].dropna(subset=[metric_name])
        if len(valid_data) == 0:
            continue
        
        if strategy in STRATEGY_METADATA:
            meta = STRATEGY_METADATA[strategy]
            label = meta['name']
            color = meta['color']
            marker = meta['marker']
            linestyle = meta['linestyle']
        else:
            label = strategy
            color = None
            marker = 'o'
            linestyle = '-'
        
        ax.plot(valid_data['step_id'], valid_data[metric_name],
               marker=marker, linestyle=linestyle, label=label,
               color=color, linewidth=2, markersize=6)
    
    # 绘制多个阈值的策略4
    if strategy4_data is not None:
        for i, threshold in enumerate(STRATEGY4_THRESHOLDS):
            threshold_data = strategy4_data[strategy4_data['threshold'] == threshold]
            if len(threshold_data) == 0:
                continue
            
            if metric_name not in threshold_data.columns:
                continue
            
            valid_data = threshold_data[['step_id', metric_name]].dropna(subset=[metric_name])
            if len(valid_data) == 0:
                continue
            
            color = STRATEGY4_COLORS[i % len(STRATEGY4_COLORS)]
            label = f'Strategy 4 (θ={threshold})'
            
            ax.plot(valid_data['step_id'], valid_data[metric_name],
                   marker='D', linestyle=':', linewidth=2, markersize=7,
                   label=label, color=color, alpha=0.8)
            
            # 标记触发重优化的时间步
            reoptimized_steps = threshold_data[threshold_data['reoptimized'] == True]['step_id']
            if len(reoptimized_steps) > 0:
                reoptimized_values = threshold_data[
                    (threshold_data['reoptimized'] == True) & 
                    (threshold_data[metric_name].notna())
                ]
                if len(reoptimized_values) > 0:
                    ax.scatter(reoptimized_values['step_id'], reoptimized_values[metric_name],
                              s=250, marker='*', color=color, edgecolors='black',
                              linewidth=2, zorder=5)
    
    # 设置标签和标题
    metric_labels = {
        'max_link_utilization_theoretical': 'Theoretical Max Link Utilization (%)',
        'max_link_utilization_actual': 'Actual Max Link Utilization (%)',
        'pli': 'Packet Loss Indicator (PLI) (%)',
        'avg_delay': 'Average Delay (s)'
    }
    
    metric_titles = {
        'max_link_utilization_theoretical': 'Theoretical Max Link Utilization Comparison',
        'max_link_utilization_actual': 'Actual Max Link Utilization Comparison',
        'pli': 'PLI Comparison',
        'avg_delay': 'Average Delay Comparison'
    }
    
    ax.set_xlabel('Time Step', fontsize=12, fontweight='bold')
    ax.set_ylabel(metric_labels.get(metric_name, metric_name), fontsize=12, fontweight='bold')
    ax.set_title(metric_titles.get(metric_name, f'{metric_name} Comparison'), 
                fontsize=14, fontweight='bold')
    
    # 添加图例
    handles, labels = ax.get_legend_handles_labels()
    # 添加重优化标记说明
    star_handle = Line2D([0], [0], marker='*', color='black', linestyle='None',
                        markersize=12, markeredgecolor='black', markeredgewidth=2,
                        label='Re-optimized step', markerfacecolor='none')
    handles.append(star_handle)
    labels.append('Re-optimized step')
    
    ax.legend(handles, labels, loc='best', framealpha=0.9, fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ {metric_titles.get(metric_name, metric_name)}已保存: {os.path.basename(output_file)}")


def main():
    """主函数"""
    print("=" * 80)
    print("更新hybrid_sequence可视化（包含多个阈值的策略4）")
    print("=" * 80)
    print()
    
    results_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', 'hybrid_sequence')
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载所有策略数据
    strategies = ['strategy1', 'strategy2', 'strategy3']
    all_strategy_data_list = []
    
    for strategy_name in strategies:
        strategy_data = load_strategy_data('hybrid_sequence', strategy_name, results_base_dir)
        if strategy_data is not None:
            all_strategy_data_list.append(strategy_data)
    
    all_strategy_data = pd.concat(all_strategy_data_list, ignore_index=True) if all_strategy_data_list else pd.DataFrame()
    
    # 加载多个阈值的策略4数据
    strategy4_data = load_strategy4_multiple_thresholds(results_base_dir)
    
    if strategy4_data is None:
        print("✗ 没有找到策略4多阈值数据")
        return
    
    # 生成各个指标的对比图
    metrics = [
        'max_link_utilization_theoretical',
        'max_link_utilization_actual',
        'pli',
        'avg_delay'
    ]
    
    for metric in metrics:
        output_file = os.path.join(output_dir, f'{metric}_comparison.png')
        plot_metric_comparison_with_multiple_thresholds(
            metric, all_strategy_data, strategy4_data, output_file
        )
    
    print("\n" + "=" * 80)
    print("✓ 所有可视化图表已更新！")
    print("=" * 80)
    print(f"输出目录: {output_dir}")


if __name__ == '__main__':
    main()

