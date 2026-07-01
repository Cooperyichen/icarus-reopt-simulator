#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化路径区间变化分析结果

生成图表展示路径在不同时间步的区间变化情况
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
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 10


def get_ratio_interval(ratio):
    """根据路径分配比例返回其所在的百分比区间标签"""
    bins = np.arange(0, 1.05, 0.05)
    bin_labels = [f'{int(bins[i]*100)}-{int(bins[i+1]*100)}%' for i in range(len(bins)-1)]
    bin_idx = np.digitize(ratio, bins) - 1
    bin_idx = max(0, min(bin_idx, len(bin_labels) - 1))
    return bin_labels[bin_idx]


def get_interval_index(interval_str, bin_labels):
    """获取区间在bin_labels中的索引"""
    try:
        return bin_labels.index(interval_str)
    except:
        return -1


def visualize_path_interval_changes(sequence_name, output_dir):
    """
    可视化路径区间变化
    
    Args:
        sequence_name: 序列名称
        output_dir: 输出目录
    """
    print(f"正在生成可视化: {sequence_name}")
    
    result_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    analysis_dir = os.path.join(result_base_dir, sequence_name, 'strategy1', 'path_allocation_analysis')
    
    # 加载详细路径比例数据
    detailed_file = os.path.join(analysis_dir, 'detailed_path_ratios.csv')
    if not os.path.exists(detailed_file):
        print(f"✗ 文件不存在: {detailed_file}")
        return
    
    df = pd.read_csv(detailed_file)
    
    # 获取所有步骤
    all_steps = sorted(df['step_id'].unique())
    if len(all_steps) < 2:
        print(f"✗ 数据不足，需要至少2个时间步")
        return
    
    step1 = all_steps[0]
    step_last = all_steps[-1]
    
    # 获取两个时间步的数据
    df_step1 = df[df['step_id'] == step1].copy()
    df_step_last = df[df['step_id'] == step_last].copy()
    
    # 为每个路径添加区间标签
    bins = np.arange(0, 1.05, 0.05)
    bin_labels = [f'{int(bins[i]*100)}-{int(bins[i+1]*100)}%' for i in range(len(bins)-1)]
    
    df_step1['interval'] = df_step1['ratio'].apply(get_ratio_interval)
    df_step_last['interval'] = df_step_last['ratio'].apply(get_ratio_interval)
    
    # 创建路径标识符
    df_step1['path_key'] = df_step1['commodity_id'].astype(str) + '|' + df_step1['path'].astype(str)
    df_step_last['path_key'] = df_step_last['commodity_id'].astype(str) + '|' + df_step_last['path'].astype(str)
    
    # 合并两个时间步的数据
    merged = pd.merge(
        df_step1[['path_key', 'commodity_id', 'path', 'ratio', 'interval']],
        df_step_last[['path_key', 'commodity_id', 'path', 'ratio', 'interval']],
        on='path_key',
        suffixes=('_step1', '_step_last'),
        how='outer'
    )
    
    # 找出区间发生变化的路径
    merged_both = merged[merged['interval_step1'].notna() & merged['interval_step_last'].notna()].copy()
    
    # 为所有路径计算ratio_diff
    merged_both['ratio_diff'] = merged_both['ratio_step_last'] - merged_both['ratio_step1']
    merged_both['abs_ratio_diff'] = abs(merged_both['ratio_diff'])
    
    changed_paths = merged_both[merged_both['interval_step1'] != merged_both['interval_step_last']].copy()
    
    if len(changed_paths) > 0:
        changed_paths['interval_idx_step1'] = changed_paths['interval_step1'].apply(
            lambda x: get_interval_index(x, bin_labels))
        changed_paths['interval_idx_step_last'] = changed_paths['interval_step_last'].apply(
            lambda x: get_interval_index(x, bin_labels))
        changed_paths['interval_shift'] = changed_paths['interval_idx_step_last'] - changed_paths['interval_idx_step1']
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # ========== 图1: 总体统计摘要 ==========
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'Path Interval Change Analysis - {sequence_name.replace("_", " ").title()}\n'
                 f'Step {step1} vs Step {step_last}', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 1.1 区间变化路径数量统计
    ax = axes[0, 0]
    total_paths = len(merged_both)
    changed_count = len(changed_paths) if len(changed_paths) > 0 else 0
    unchanged_count = total_paths - changed_count
    
    categories = ['Unchanged', 'Changed']
    counts = [unchanged_count, changed_count]
    colors = ['#2ca02c', '#d62728']
    
    bars = ax.bar(categories, counts, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    ax.set_ylabel('Number of Paths', fontweight='bold')
    ax.set_title('Paths with Interval Changes', fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}\n({height/total_paths*100:.2f}%)',
                ha='center', va='bottom', fontweight='bold')
    
    # 1.2 按Commodity统计区间变化
    ax = axes[0, 1]
    if len(changed_paths) > 0:
        commodity_changes = changed_paths.groupby('commodity_id_step1').size()
        commodity_totals = merged_both.groupby('commodity_id_step1').size()
        commodity_change_rates = (commodity_changes / commodity_totals * 100).fillna(0)
        
        commodities = sorted(commodity_change_rates.index)
        change_rates = [commodity_change_rates[c] for c in commodities]
        
        bars = ax.bar([f'Commodity {c}' for c in commodities], change_rates, 
                     color='#ff7f0e', alpha=0.8, edgecolor='black', linewidth=1.5)
        ax.set_ylabel('Change Rate (%)', fontweight='bold')
        ax.set_title('Interval Change Rate by Commodity', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2f}%',
                    ha='center', va='bottom', fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'No paths changed intervals', 
                ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_title('Interval Change Rate by Commodity', fontweight='bold')
    
    # 1.3 区间移动方向统计
    ax = axes[1, 0]
    if len(changed_paths) > 0:
        shift_counts = changed_paths['interval_shift'].value_counts().sort_index()
        
        directions = []
        counts_list = []
        colors_list = []
        for shift in shift_counts.index:
            if shift < 0:
                directions.append(f'Left ({shift:+d})')
                colors_list.append('#d62728')
            elif shift > 0:
                directions.append(f'Right ({shift:+d})')
                colors_list.append('#2ca02c')
            else:
                directions.append('No change')
                colors_list.append('#7f7f7f')
            counts_list.append(shift_counts[shift])
        
        bars = ax.bar(directions, counts_list, color=colors_list, alpha=0.8, 
                     edgecolor='black', linewidth=1.5)
        ax.set_ylabel('Number of Paths', fontweight='bold')
        ax.set_title('Interval Shift Direction', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold')
    else:
        ax.text(0.5, 0.5, 'No paths changed intervals', 
                ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_title('Interval Shift Direction', fontweight='bold')
    
    # 1.4 路径比例变化分布
    ax = axes[1, 1]
    if len(changed_paths) > 0:
        ax.scatter(changed_paths['ratio_step1'], changed_paths['ratio_step_last'],
                  c=changed_paths['commodity_id_step1'], cmap='tab10', 
                  s=100, alpha=0.7, edgecolors='black', linewidth=1)
        
        # 添加对角线（y=x）
        max_ratio = max(changed_paths['ratio_step1'].max(), changed_paths['ratio_step_last'].max())
        min_ratio = min(changed_paths['ratio_step1'].min(), changed_paths['ratio_step_last'].min())
        ax.plot([min_ratio, max_ratio], [min_ratio, max_ratio], 
               'r--', linewidth=2, alpha=0.5, label='No change line')
        
        ax.set_xlabel(f'Path Ratio - Step {step1}', fontweight='bold')
        ax.set_ylabel(f'Path Ratio - Step {step_last}', fontweight='bold')
        ax.set_title('Path Ratio Changes (Changed Paths Only)', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
    else:
        ax.text(0.5, 0.5, 'No paths changed intervals', 
                ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_title('Path Ratio Changes', fontweight='bold')
    
    plt.tight_layout()
    output_file1 = os.path.join(output_dir, 'path_interval_change_summary.png')
    plt.savefig(output_file1, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved: {output_file1}")
    
    # ========== 图2: 详细的路径变化散点图 ==========
    if len(changed_paths) > 0:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Detailed Path Ratio Changes - {sequence_name.replace("_", " ").title()}\n'
                     f'Step {step1} vs Step {step_last}', 
                     fontsize=16, fontweight='bold', y=0.995)
        
        # 2.1 所有路径的散点图（按commodity分组）
        ax = axes[0, 0]
        for commodity_id in sorted(merged_both['commodity_id_step1'].unique()):
            commodity_data = merged_both[merged_both['commodity_id_step1'] == commodity_id]
            ax.scatter(commodity_data['ratio_step1'], commodity_data['ratio_step_last'],
                      label=f'Commodity {int(commodity_id)}', s=50, alpha=0.6, edgecolors='black', linewidth=0.5)
        
        # 添加对角线
        max_ratio = max(merged_both['ratio_step1'].max(), merged_both['ratio_step_last'].max())
        min_ratio = min(merged_both['ratio_step1'].min(), merged_both['ratio_step_last'].min())
        ax.plot([min_ratio, max_ratio], [min_ratio, max_ratio], 
               'r--', linewidth=2, alpha=0.5, label='No change line')
        
        ax.set_xlabel(f'Path Ratio - Step {step1}', fontweight='bold')
        ax.set_ylabel(f'Path Ratio - Step {step_last}', fontweight='bold')
        ax.set_title('All Paths Ratio Comparison', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # 2.2 发生变化的路径（突出显示）
        ax = axes[0, 1]
        # 先画所有路径（灰色）
        ax.scatter(merged_both['ratio_step1'], merged_both['ratio_step_last'],
                  c='lightgray', s=30, alpha=0.3, edgecolors='none', label='Unchanged paths')
        
        # 再画变化的路径（彩色）
        scatter = ax.scatter(changed_paths['ratio_step1'], changed_paths['ratio_step_last'],
                            c=changed_paths['abs_ratio_diff'], cmap='YlOrRd', 
                            s=150, alpha=0.8, edgecolors='black', linewidth=1.5, 
                            label='Changed paths')
        
        # 添加对角线
        ax.plot([min_ratio, max_ratio], [min_ratio, max_ratio], 
               'r--', linewidth=2, alpha=0.5)
        
        ax.set_xlabel(f'Path Ratio - Step {step1}', fontweight='bold')
        ax.set_ylabel(f'Path Ratio - Step {step_last}', fontweight='bold')
        ax.set_title('Changed Paths (Highlighted)', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # 添加colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Absolute Ratio Change', fontweight='bold')
        
        # 2.3 按commodity分组的箱线图
        ax = axes[1, 0]
        data_for_box = []
        labels = []
        for commodity_id in sorted(merged_both['commodity_id_step1'].unique()):
            commodity_data = merged_both[merged_both['commodity_id_step1'] == commodity_id]
            data_for_box.append(commodity_data['ratio_diff'].values)
            labels.append(f'C{int(commodity_id)}')
        
        bp = ax.boxplot(data_for_box, tick_labels=labels, patch_artist=True)
        for patch in bp['boxes']:
            patch.set_facecolor('#1f77b4')
            patch.set_alpha(0.7)
        
        ax.axhline(y=0, color='r', linestyle='--', linewidth=2, alpha=0.5)
        ax.set_ylabel('Ratio Change (Step Last - Step 1)', fontweight='bold')
        ax.set_xlabel('Commodity', fontweight='bold')
        ax.set_title('Path Ratio Change Distribution by Commodity', fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # 2.4 区间变化热力图
        ax = axes[1, 1]
        if len(changed_paths) > 0:
            # 创建区间变化矩阵
            interval_matrix = pd.crosstab(
                changed_paths['interval_step1'], 
                changed_paths['interval_step_last']
            )
            
            if len(interval_matrix) > 0 and len(interval_matrix.columns) > 0:
                sns.heatmap(interval_matrix, annot=True, fmt='d', cmap='YlOrRd', 
                           ax=ax, cbar_kws={'label': 'Number of Paths'}, 
                           linewidths=0.5, linecolor='gray')
                ax.set_xlabel(f'Interval - Step {step_last}', fontweight='bold')
                ax.set_ylabel(f'Interval - Step {step1}', fontweight='bold')
                ax.set_title('Interval Transition Matrix', fontweight='bold')
            else:
                ax.text(0.5, 0.5, 'Insufficient data for heatmap', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
                ax.set_title('Interval Transition Matrix', fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No paths changed intervals', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)
            ax.set_title('Interval Transition Matrix', fontweight='bold')
        
        plt.tight_layout()
        output_file2 = os.path.join(output_dir, 'path_interval_change_detailed.png')
        plt.savefig(output_file2, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"✓ Saved: {output_file2}")
    
    # ========== 图3: 区间分布对比 ==========
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'Interval Distribution Comparison - {sequence_name.replace("_", " ").title()}\n'
                 f'Step {step1} vs Step {step_last}', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 3.1 Step 1 区间分布
    ax = axes[0, 0]
    step1_counts = df_step1.groupby(['commodity_id', 'interval']).size().reset_index(name='count')
    step1_pivot = step1_counts.pivot(index='interval', columns='commodity_id', values='count').fillna(0)
    
    x_pos = np.arange(len(bin_labels))
    width = 0.2
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for idx, commodity_id in enumerate(sorted(df_step1['commodity_id'].unique())):
        counts = [step1_pivot.loc[interval, commodity_id] if interval in step1_pivot.index else 0 
                 for interval in bin_labels]
        ax.bar(x_pos + idx * width, counts, width, label=f'Commodity {int(commodity_id)}', 
              color=colors[idx % len(colors)], alpha=0.8, edgecolor='black', linewidth=0.5)
    
    ax.set_xlabel('Interval', fontweight='bold')
    ax.set_ylabel('Number of Paths', fontweight='bold')
    ax.set_title(f'Interval Distribution - Step {step1}', fontweight='bold')
    ax.set_xticks(x_pos[::2])  # 每两个显示一个
    ax.set_xticklabels(bin_labels[::2], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3.2 Step Last 区间分布
    ax = axes[0, 1]
    step_last_counts = df_step_last.groupby(['commodity_id', 'interval']).size().reset_index(name='count')
    step_last_pivot = step_last_counts.pivot(index='interval', columns='commodity_id', values='count').fillna(0)
    
    for idx, commodity_id in enumerate(sorted(df_step_last['commodity_id'].unique())):
        counts = [step_last_pivot.loc[interval, commodity_id] if interval in step_last_pivot.index else 0 
                 for interval in bin_labels]
        ax.bar(x_pos + idx * width, counts, width, label=f'Commodity {int(commodity_id)}', 
              color=colors[idx % len(colors)], alpha=0.8, edgecolor='black', linewidth=0.5)
    
    ax.set_xlabel('Interval', fontweight='bold')
    ax.set_ylabel('Number of Paths', fontweight='bold')
    ax.set_title(f'Interval Distribution - Step {step_last}', fontweight='bold')
    ax.set_xticks(x_pos[::2])
    ax.set_xticklabels(bin_labels[::2], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # 3.3 区间分布差异
    ax = axes[1, 0]
    diff_data = []
    for interval in bin_labels:
        step1_total = step1_pivot.loc[interval].sum() if interval in step1_pivot.index else 0
        step_last_total = step_last_pivot.loc[interval].sum() if interval in step_last_pivot.index else 0
        diff = step_last_total - step1_total
        diff_data.append(diff)
    
    colors_diff = ['#d62728' if d < 0 else '#2ca02c' if d > 0 else '#7f7f7f' for d in diff_data]
    bars = ax.bar(x_pos, diff_data, color=colors_diff, alpha=0.8, edgecolor='black', linewidth=0.5)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.set_xlabel('Interval', fontweight='bold')
    ax.set_ylabel('Difference (Step Last - Step 1)', fontweight='bold')
    ax.set_title('Interval Distribution Difference', fontweight='bold')
    ax.set_xticks(x_pos[::2])
    ax.set_xticklabels(bin_labels[::2], rotation=45, ha='right')
    ax.grid(True, alpha=0.3, axis='y')
    
    # 添加数值标签（只显示非零值）
    for i, (bar, val) in enumerate(zip(bars, diff_data)):
        if val != 0:
            ax.text(bar.get_x() + bar.get_width()/2., val,
                   f'{int(val):+d}', ha='center', 
                   va='bottom' if val > 0 else 'top', fontsize=8, fontweight='bold')
    
    # 3.4 变化路径的区间分布
    ax = axes[1, 1]
    if len(changed_paths) > 0:
        changed_step1_counts = changed_paths['interval_step1'].value_counts().sort_index()
        changed_step_last_counts = changed_paths['interval_step_last'].value_counts().sort_index()
        
        x_pos_changed = np.arange(len(bin_labels))
        step1_vals = [changed_step1_counts.get(interval, 0) for interval in bin_labels]
        step_last_vals = [changed_step_last_counts.get(interval, 0) for interval in bin_labels]
        
        width_changed = 0.35
        ax.bar(x_pos_changed - width_changed/2, step1_vals, width_changed, 
              label=f'Step {step1}', color='#1f77b4', alpha=0.8, edgecolor='black', linewidth=0.5)
        ax.bar(x_pos_changed + width_changed/2, step_last_vals, width_changed, 
              label=f'Step {step_last}', color='#ff7f0e', alpha=0.8, edgecolor='black', linewidth=0.5)
        
        ax.set_xlabel('Interval', fontweight='bold')
        ax.set_ylabel('Number of Changed Paths', fontweight='bold')
        ax.set_title('Interval Distribution of Changed Paths', fontweight='bold')
        ax.set_xticks(x_pos_changed[::2])
        ax.set_xticklabels(bin_labels[::2], rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
    else:
        ax.text(0.5, 0.5, 'No paths changed intervals', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_title('Interval Distribution of Changed Paths', fontweight='bold')
    
    plt.tight_layout()
    output_file3 = os.path.join(output_dir, 'path_interval_distribution_comparison.png')
    plt.savefig(output_file3, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved: {output_file3}")
    
    print(f"✓ 可视化完成: {sequence_name}")


def main():
    """主函数"""
    sequences = ['increasing_sequence', 'random_perturbation']
    
    for sequence_name in sequences:
        try:
            output_base_dir = os.path.join(src_dir, 'results', '可视化结果展示', '全优化流量分布')
            output_dir = os.path.join(output_base_dir, sequence_name)
            
            visualize_path_interval_changes(sequence_name, output_dir)
            print()
        except Exception as e:
            print(f"✗ 处理 {sequence_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
            print()


if __name__ == '__main__':
    main()

