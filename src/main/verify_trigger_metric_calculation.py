#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证策略4中触发指标的计算是否正确

检查：
1. 对偶变量是否被正确使用
2. 触发指标的计算公式是否正确
3. 触发指标的值是否合理
"""

import sys
import os
import pandas as pd
import numpy as np

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from main.multi_step_comparison_experiment import calculate_trigger_metric


def extract_dual_variables_from_optimization(config, arrival_rates):
    """提取对偶变量"""
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
    
    result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    dual_vars = {}
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
    
    return dual_vars


def verify_trigger_metric_calculation(sequence_name, threshold=20):
    """验证触发指标的计算"""
    print("=" * 80)
    print(f"验证触发指标计算: {sequence_name} (阈值={threshold})")
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
    
    # 存储对偶变量
    last_dual_variables = None
    last_demand = None
    
    print("验证触发指标计算:\n")
    
    for idx, row in stats_df.iterrows():
        step_id = int(row['step_id'])
        reoptimized = row['reoptimized']
        trigger_metric_recorded = row['trigger_metric'] if pd.notna(row['trigger_metric']) else None
        
        # 解析到达率
        arrival_rates_str = row['arrival_rates']
        if isinstance(arrival_rates_str, str):
            arrival_rates = [float(x.strip()) for x in arrival_rates_str.strip('[]').split(',')]
        else:
            arrival_rates = sequence[step_id - 1].tolist()
        
        print(f"步骤 {step_id}:")
        print(f"  到达率: {[f'{r:.2f}' for r in arrival_rates]}")
        
        if step_id == 1:
            # 步骤1：提取对偶变量
            print(f"  → 步骤1：提取对偶变量")
            last_dual_variables = extract_dual_variables_from_optimization(config, arrival_rates)
            last_demand = arrival_rates.copy()
            
            print(f"  对偶变量: {last_dual_variables}")
            print(f"  触发指标: N/A (步骤1)")
        else:
            # 步骤2+：计算触发指标
            if last_dual_variables is not None and last_demand is not None:
                # 使用策略4的函数计算触发指标
                trigger_metric_calculated = calculate_trigger_metric(
                    last_dual_variables, arrival_rates, last_demand
                )
                
                print(f"  上一次对偶变量: {last_dual_variables}")
                print(f"  上一次到达率: {[f'{r:.2f}' for r in last_demand]}")
                print(f"  当前到达率: {[f'{r:.2f}' for r in arrival_rates]}")
                print(f"  计算的触发指标: {trigger_metric_calculated:.6f}")
                if trigger_metric_recorded is not None:
                    print(f"  记录的触发指标: {trigger_metric_recorded:.6f}")
                else:
                    print(f"  记录的触发指标: N/A")
                
                # 验证
                if trigger_metric_recorded is not None:
                    diff = abs(trigger_metric_calculated - trigger_metric_recorded)
                    if diff < 1e-6:
                        print(f"  ✓ 触发指标计算正确 (差异: {diff:.2e})")
                    else:
                        print(f"  ✗ 触发指标不匹配 (差异: {diff:.6f})")
                
                # 详细计算过程
                print(f"  详细计算:")
                for i in range(len(arrival_rates)):
                    if i in last_dual_variables and last_dual_variables[i] is not None:
                        demand_change = abs(arrival_rates[i] - last_demand[i])
                        contribution = last_dual_variables[i] * demand_change
                        print(f"    商品 {i}: λ={last_dual_variables[i]:.6e}, "
                              f"Δd={demand_change:.2f}, "
                              f"贡献={contribution:.6f}")
                
                # 如果重新优化，更新对偶变量
                if reoptimized:
                    print(f"  → 重新优化，更新对偶变量")
                    last_dual_variables = extract_dual_variables_from_optimization(config, arrival_rates)
                    last_demand = arrival_rates.copy()
                    print(f"  新对偶变量: {last_dual_variables}")
            else:
                print(f"  ⚠️  警告: 没有上一次的对偶变量或需求")
        
        print()
    
    print("=" * 80)
    print("✓ 验证完成")
    print("=" * 80)


def main():
    """主函数"""
    sequences = ['increasing_sequence', 'hybrid_sequence']
    threshold = 20
    
    for sequence_name in sequences:
        verify_trigger_metric_calculation(sequence_name, threshold)
        print("\n\n")


if __name__ == '__main__':
    main()

