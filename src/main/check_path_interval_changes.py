#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查路径流量分配在不同时间步是否跨越不同的百分比区间

分析step1和step10（或最后一步）的路径分配比例，找出哪些路径
在不同时间步处于不同的百分比区间。
"""

import sys
import os
import pandas as pd
import numpy as np

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)


def get_ratio_interval(ratio):
    """
    根据路径分配比例返回其所在的百分比区间标签
    
    Args:
        ratio: 路径分配比例 (0-1)
        
    Returns:
        str: 区间标签，如 "0-5%", "5-10%", etc.
    """
    bins = np.arange(0, 1.05, 0.05)  # 0%, 5%, 10%, ..., 100%
    bin_labels = [f'{int(bins[i]*100)}-{int(bins[i+1]*100)}%' for i in range(len(bins)-1)]
    
    # 找到ratio所在的区间
    bin_idx = np.digitize(ratio, bins) - 1
    bin_idx = max(0, min(bin_idx, len(bin_labels) - 1))  # 确保在有效范围内
    
    return bin_labels[bin_idx]


def check_path_interval_changes(sequence_name):
    """
    检查指定序列中路径在不同时间步的区间变化
    
    Args:
        sequence_name: 序列名称
    """
    print("=" * 80)
    print(f"检查路径区间变化: {sequence_name}")
    print("=" * 80)
    print()
    
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
        print(f"✗ 数据不足，需要至少2个时间步，但只有 {len(all_steps)} 个")
        return
    
    step1 = all_steps[0]
    step_last = all_steps[-1]
    
    print(f"比较时间步: Step {step1} vs Step {step_last}")
    print()
    
    # 获取两个时间步的数据
    df_step1 = df[df['step_id'] == step1].copy()
    df_step_last = df[df['step_id'] == step_last].copy()
    
    # 为每个路径添加区间标签
    df_step1['interval'] = df_step1['ratio'].apply(get_ratio_interval)
    df_step_last['interval'] = df_step_last['ratio'].apply(get_ratio_interval)
    
    # 创建路径标识符（commodity_id + path）
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
    # 只考虑在两个时间步都存在的路径
    merged_both = merged[merged['interval_step1'].notna() & merged['interval_step_last'].notna()].copy()
    changed_paths = merged_both[merged_both['interval_step1'] != merged_both['interval_step_last']].copy()
    
    print("=" * 80)
    print("统计摘要")
    print("=" * 80)
    print()
    print(f"Step {step1} 总路径数: {len(df_step1)}")
    print(f"Step {step_last} 总路径数: {len(df_step_last)}")
    print(f"两个时间步都存在的路径数: {len(merged_both)}")
    print(f"区间发生变化的路径数: {len(changed_paths)}")
    print(f"区间变化比例: {len(changed_paths) / len(merged_both) * 100:.2f}%")
    print()
    
    # 按commodity统计
    print("=" * 80)
    print("按Commodity统计区间变化")
    print("=" * 80)
    print()
    
    for commodity_id in sorted(merged_both['commodity_id_step1'].unique()):
        commodity_paths = merged_both[merged_both['commodity_id_step1'] == commodity_id]
        commodity_changed = changed_paths[changed_paths['commodity_id_step1'] == commodity_id]
        
        print(f"Commodity {commodity_id}:")
        print(f"  总路径数: {len(commodity_paths)}")
        print(f"  区间变化的路径数: {len(commodity_changed)}")
        if len(commodity_paths) > 0:
            print(f"  变化比例: {len(commodity_changed) / len(commodity_paths) * 100:.2f}%")
        print()
    
    # 显示区间变化的详细信息
    if len(changed_paths) > 0:
        print("=" * 80)
        print("区间变化的路径详情（前20条）")
        print("=" * 80)
        print()
        
        # 按变化幅度排序（ratio的绝对差值）
        changed_paths['ratio_diff'] = abs(changed_paths['ratio_step_last'] - changed_paths['ratio_step1'])
        changed_paths_sorted = changed_paths.sort_values('ratio_diff', ascending=False)
        
        print(f"{'Commodity':<10} {'Step1区间':<12} {'Step1比例':<12} {'StepLast区间':<12} {'StepLast比例':<12} {'变化量':<10}")
        print("-" * 80)
        
        for idx, row in changed_paths_sorted.head(20).iterrows():
            print(f"{int(row['commodity_id_step1']):<10} "
                  f"{row['interval_step1']:<12} "
                  f"{row['ratio_step1']:<12.6f} "
                  f"{row['interval_step_last']:<12} "
                  f"{row['ratio_step_last']:<12.6f} "
                  f"{row['ratio_diff']:<10.6f}")
        
        if len(changed_paths) > 20:
            print(f"\n... 还有 {len(changed_paths) - 20} 条路径发生区间变化")
        
        print()
        
        # 统计区间变化的模式
        print("=" * 80)
        print("区间变化模式统计")
        print("=" * 80)
        print()
        
        # 计算区间索引
        bins = np.arange(0, 1.05, 0.05)
        bin_labels = [f'{int(bins[i]*100)}-{int(bins[i+1]*100)}%' for i in range(len(bins)-1)]
        
        def get_interval_index(interval_str):
            try:
                return bin_labels.index(interval_str)
            except:
                return -1
        
        changed_paths['interval_idx_step1'] = changed_paths['interval_step1'].apply(get_interval_index)
        changed_paths['interval_idx_step_last'] = changed_paths['interval_step_last'].apply(get_interval_index)
        changed_paths['interval_shift'] = changed_paths['interval_idx_step_last'] - changed_paths['interval_idx_step1']
        
        print("区间移动统计:")
        shift_counts = changed_paths['interval_shift'].value_counts().sort_index()
        for shift, count in shift_counts.items():
            direction = "向右" if shift > 0 else "向左" if shift < 0 else "无变化"
            print(f"  移动 {shift:+d} 个区间 ({direction}): {count} 条路径")
        print()
        
        # 显示最大的区间跳跃
        print("最大的区间跳跃（前10条）:")
        print(f"{'Commodity':<10} {'Step1区间':<15} {'StepLast区间':<15} {'跳跃':<10}")
        print("-" * 60)
        for idx, row in changed_paths_sorted.head(10).iterrows():
            # 重新计算shift，因为可能在某些情况下列没有正确创建
            idx1 = get_interval_index(row['interval_step1'])
            idx2 = get_interval_index(row['interval_step_last'])
            shift = idx2 - idx1 if idx1 >= 0 and idx2 >= 0 else 0
            print(f"{int(row['commodity_id_step1']):<10} "
                  f"{row['interval_step1']:<15} "
                  f"{row['interval_step_last']:<15} "
                  f"{shift:+d} 个区间")
        print()
    else:
        print("=" * 80)
        print("✓ 没有路径发生区间变化")
        print("=" * 80)
        print()
        print("所有路径在两个时间步都保持在相同的百分比区间内。")
        print()
    
    # 检查是否有路径在某个时间步存在但在另一个时间步不存在
    only_step1 = merged[merged['interval_step1'].notna() & merged['interval_step_last'].isna()]
    only_step_last = merged[merged['interval_step1'].isna() & merged['interval_step_last'].notna()]
    
    if len(only_step1) > 0 or len(only_step_last) > 0:
        print("=" * 80)
        print("路径存在性变化")
        print("=" * 80)
        print()
        print(f"仅在 Step {step1} 存在的路径数: {len(only_step1)}")
        print(f"仅在 Step {step_last} 存在的路径数: {len(only_step_last)}")
        print()
        
        if len(only_step1) > 0:
            print(f"仅在 Step {step1} 存在的路径（前10条）:")
            for idx, row in only_step1.head(10).iterrows():
                print(f"  Commodity {int(row['commodity_id_step1'])}: "
                      f"区间 {row['interval_step1']}, "
                      f"比例 {row['ratio_step1']:.6f}")
            print()
        
        if len(only_step_last) > 0:
            print(f"仅在 Step {step_last} 存在的路径（前10条）:")
            for idx, row in only_step_last.head(10).iterrows():
                print(f"  Commodity {int(row['commodity_id_step_last'])}: "
                      f"区间 {row['interval_step_last']}, "
                      f"比例 {row['ratio_step_last']:.6f}")
            print()
    
    print("=" * 80)
    print("分析完成")
    print("=" * 80)
    print()


def main():
    """主函数"""
    sequences = ['increasing_sequence', 'random_perturbation', 'hybrid_sequence']
    
    for sequence_name in sequences:
        try:
            check_path_interval_changes(sequence_name)
            print()
        except Exception as e:
            print(f"✗ 处理 {sequence_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
            print()


if __name__ == '__main__':
    main()

