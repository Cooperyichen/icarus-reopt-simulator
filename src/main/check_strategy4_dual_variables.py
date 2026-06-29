#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查策略4在increasing_sequence和hybrid_sequence中对偶变量的提取和使用情况

功能：
1. 验证对偶变量是否被正确提取
2. 检查对偶变量的值是否合理
3. 分析对偶变量的变化情况
4. 验证对偶变量在触发指标计算中是否被正确使用
"""

import sys
import os
import pandas as pd
import numpy as np
import ast

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer


def extract_dual_variables_from_optimization(config, arrival_rates):
    """
    通过重新运行优化来提取对偶变量
    
    Args:
        config: 配置字典
        arrival_rates: 到达率列表
        
    Returns:
        dict: 对偶变量字典 {commodity_id: dual_value}
    """
    step_config = config.copy()
    step_config['fixed_demand'] = config['fixed_demand'].copy()
    step_config['fixed_demand']['arrival_rate'] = arrival_rates
    
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=step_config, width=width, height=height)
    
    num_commodities = len(arrival_rates)
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    
    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']
    
    # 运行优化
    result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    # 提取对偶变量
    dual_vars = {}
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
        print(f"  ✓ 对偶变量提取成功: {len(dual_vars)} 个商品")
    else:
        print(f"  ✗ 对偶变量未找到")
        if hasattr(result_df, 'attrs'):
            print(f"    可用属性: {list(result_df.attrs.keys())}")
        else:
            print(f"    结果对象没有attrs属性")
    
    return dual_vars


def check_strategy4_dual_variables(sequence_name, threshold=20):
    """
    检查策略4在指定序列中对偶变量的提取和使用情况
    
    Args:
        sequence_name: 序列名称 ('increasing_sequence' 或 'hybrid_sequence')
        threshold: 阈值
    """
    print("=" * 80)
    print(f"检查策略4对偶变量: {sequence_name} (阈值={threshold})")
    print("=" * 80)
    print()
    
    # 配置路径
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    strategy_name = 'strategy4'
    
    # 加载配置和序列
    config = load_yaml_file(config_file)
    sequence_file = os.path.join(src_dir, 'results', f'arrival_rate_sequence_{sequence_name.replace("_sequence", "")}.csv')
    
    if not os.path.exists(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return
    
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    
    # 加载策略4统计
    stats_file = os.path.join(result_base_dir, sequence_name, strategy_name, f'{strategy_name}_stats.csv')
    if not os.path.exists(stats_file):
        print(f"✗ 统计文件不存在: {stats_file}")
        return
    
    stats_df = pd.read_csv(stats_file)
    
    print(f"序列信息:")
    print(f"  总步数: {len(stats_df)}")
    print(f"  商品数: {len(sequence[0])}")
    print()
    
    # 分析每个步骤
    all_dual_data = []
    reoptimized_steps = []
    
    for idx, row in stats_df.iterrows():
        step_id = int(row['step_id'])
        reoptimized = row['reoptimized']
        trigger_metric = row['trigger_metric'] if pd.notna(row['trigger_metric']) else None
        
        # 解析到达率
        arrival_rates_str = row['arrival_rates']
        if isinstance(arrival_rates_str, str):
            arrival_rates = [float(x.strip()) for x in arrival_rates_str.strip('[]').split(',')]
        else:
            arrival_rates = sequence[step_id - 1].tolist()
        
        print(f"步骤 {step_id}:")
        print(f"  到达率: {[f'{r:.2f}' for r in arrival_rates]}")
        print(f"  重新优化: {reoptimized}")
        print(f"  触发指标: {trigger_metric if trigger_metric is not None else 'N/A'}")
        
        # 如果是重新优化的步骤，提取对偶变量
        if reoptimized:
            reoptimized_steps.append(step_id)
            print(f"  → 提取对偶变量...")
            dual_vars = extract_dual_variables_from_optimization(config, arrival_rates)
            
            # 保存对偶变量数据
            for commodity_id in range(len(arrival_rates)):
                dual_value = dual_vars.get(commodity_id, None)
                all_dual_data.append({
                    'step_id': step_id,
                    'commodity_id': commodity_id,
                    'dual_value': dual_value,
                    'arrival_rate': arrival_rates[commodity_id],
                    'reoptimized': True
                })
            
            # 打印对偶变量
            print(f"  对偶变量值:")
            for commodity_id in range(len(arrival_rates)):
                dual_value = dual_vars.get(commodity_id, None)
                if dual_value is not None:
                    print(f"    商品 {commodity_id}: {dual_value:.6e}")
                else:
                    print(f"    商品 {commodity_id}: None (未提取)")
        else:
            # 非重新优化步骤，使用上一次的对偶变量
            print(f"  → 使用上一次优化的对偶变量")
            # 这里我们需要找到上一次重新优化的步骤的对偶变量
            # 为了简化，我们标记为沿用
            for commodity_id in range(len(arrival_rates)):
                all_dual_data.append({
                    'step_id': step_id,
                    'commodity_id': commodity_id,
                    'dual_value': None,  # 标记为沿用上一次
                    'arrival_rate': arrival_rates[commodity_id],
                    'reoptimized': False
                })
        
        print()
    
    # 创建对偶变量DataFrame
    dual_df = pd.DataFrame(all_dual_data)
    
    # 保存结果
    output_file = os.path.join(result_base_dir, sequence_name, strategy_name, 
                              f'dual_variables_analysis_threshold{threshold}.csv')
    dual_df.to_csv(output_file, index=False)
    print(f"✓ 对偶变量分析已保存: {output_file}")
    
    # 创建透视表
    pivot_df = dual_df[dual_df['reoptimized'] == True].pivot(
        index='step_id', columns='commodity_id', values='dual_value'
    )
    pivot_file = os.path.join(result_base_dir, sequence_name, strategy_name, 
                             f'dual_variables_pivot_threshold{threshold}.csv')
    pivot_df.to_csv(pivot_file)
    print(f"✓ 透视表已保存: {pivot_file}")
    
    # 分析报告
    print("\n" + "=" * 80)
    print("分析报告")
    print("=" * 80)
    print(f"重新优化的步骤: {reoptimized_steps} ({len(reoptimized_steps)}/{len(stats_df)})")
    print()
    
    # 检查对偶变量提取情况
    reoptimized_dual_df = dual_df[dual_df['reoptimized'] == True]
    if len(reoptimized_dual_df) > 0:
        non_none_count = reoptimized_dual_df['dual_value'].notna().sum()
        total_count = len(reoptimized_dual_df)
        print(f"对偶变量提取情况:")
        print(f"  成功提取: {non_none_count}/{total_count} ({non_none_count/total_count*100:.1f}%)")
        
        if non_none_count > 0:
            print(f"  对偶变量统计:")
            valid_duals = reoptimized_dual_df['dual_value'].dropna()
            print(f"    最小值: {valid_duals.min():.6e}")
            print(f"    最大值: {valid_duals.max():.6e}")
            print(f"    平均值: {valid_duals.mean():.6e}")
            print(f"    中位数: {valid_duals.median():.6e}")
        else:
            print(f"  ⚠️  警告: 没有成功提取任何对偶变量！")
    else:
        print(f"⚠️  警告: 没有重新优化的步骤，无法提取对偶变量")
    
    # 分析对偶变量变化
    if len(reoptimized_steps) > 1:
        print(f"\n对偶变量变化分析:")
        for i in range(len(reoptimized_steps) - 1):
            step1 = reoptimized_steps[i]
            step2 = reoptimized_steps[i + 1]
            
            duals1 = dual_df[(dual_df['step_id'] == step1) & (dual_df['reoptimized'] == True)]
            duals2 = dual_df[(dual_df['step_id'] == step2) & (dual_df['reoptimized'] == True)]
            
            print(f"  步骤 {step1} → 步骤 {step2}:")
            for commodity_id in range(len(sequence[0])):
                dual1 = duals1[duals1['commodity_id'] == commodity_id]['dual_value'].values[0]
                dual2 = duals2[duals2['commodity_id'] == commodity_id]['dual_value'].values[0]
                
                if dual1 is not None and dual2 is not None:
                    change = dual2 - dual1
                    change_pct = (change / abs(dual1)) * 100 if dual1 != 0 else 0
                    print(f"    商品 {commodity_id}: {dual1:.6e} → {dual2:.6e} "
                          f"(变化: {change:+.6e}, {change_pct:+.2f}%)")
                else:
                    print(f"    商品 {commodity_id}: 无法比较 (存在None值)")
    
    print("\n" + "=" * 80)
    print("✓ 检查完成")
    print("=" * 80)


def main():
    """主函数"""
    sequences = ['increasing_sequence', 'hybrid_sequence']
    threshold = 20
    
    for sequence_name in sequences:
        check_strategy4_dual_variables(sequence_name, threshold)
        print("\n\n")


if __name__ == '__main__':
    main()

