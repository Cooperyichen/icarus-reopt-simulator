#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 80_lambda_our_model_2c.yaml 生成 50 步随机扰动序列，并检查每步优化问题的可行性。

参考 random_perturbation 的扰动方式：
  arrival_rate[t+1] = arrival_rate[t] + N(0, σ²)
  其中 σ = 50 (标准差), 方差 = σ² = 2500
"""

import numpy as np
import pandas as pd
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from main.generate_arrival_rate_sequence import generate_arrival_rate_sequence


def check_optimization_feasibility_for_sequence(sequence, config, std_dev):
    """
    对序列中每一步运行优化器，检查是否可解。
    
    Returns:
        list: 每步的可行性结果 [(step_id, feasible, status, arrival_rates), ...]
    """
    num_steps, num_commodities = sequence.shape
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)
    
    results = []
    infeasible_steps = []
    
    for step_id in range(1, num_steps + 1):
        arrival_rates = sequence[step_id - 1].tolist()
        
        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        step_config['fixed_demand']['arrival_rate'] = arrival_rates
        regen_obp.scenario_config = step_config
        
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
        
        feasible = False
        status = 'unknown'
        
        try:
            optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
            objective_type = step_config['optimization']['objective_func']
            mode = step_config['simulation']['failure_strategy']
            updated_demand_matrix = optimizer.solve_mcfp_path_formulation(
                demand_matrix, objective_type, mode
            )
            
            if updated_demand_matrix is not None and len(updated_demand_matrix) > 0:
                total_rate = updated_demand_matrix['Arrival Rate'].sum()
                if total_rate > 0 and len(updated_demand_matrix) > num_commodities:
                    feasible = True
                    status = 'feasible'
                else:
                    status = 'infeasible'
                    infeasible_steps.append(step_id)
            else:
                status = 'infeasible'
                infeasible_steps.append(step_id)
                
        except Exception as e:
            status = f'error: {str(e)[:50]}'
            infeasible_steps.append(step_id)
        
        results.append({
            'step_id': step_id,
            'arrival_rates': arrival_rates,
            'feasible': feasible,
            'status': status
        })
        
        symbol = "✓" if feasible else "✗"
        print(f"  Step {step_id:2d}/{num_steps}: {symbol} {status}  rates={[f'{r:.1f}' for r in arrival_rates]}")
    
    return results, infeasible_steps


def main(seed=42):
    print("=" * 80)
    print(f"50 步随机扰动序列 - 优化可行性检查 (seed={seed})")
    print("=" * 80)
    print()
    
    # 加载配置
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    initial_rates = config['fixed_demand']['arrival_rate']
    num_commodities = config['optimization']['num_commodities']
    
    # 随机扰动参数 (与 random_perturbation 一致)
    std_dev = 50  # 标准差
    variance = std_dev ** 2  # 方差 = 2500
    num_steps = 50
    
    print("配置信息:")
    print(f"  初始 arrival_rate: {initial_rates} packets/s")
    print(f"  Commodity 数量: {num_commodities}")
    print(f"  扰动方式: arrival_rate[t+1] = arrival_rate[t] + N(0, σ²)")
    print(f"  高斯分布标准差 σ: {std_dev} packets/s")
    print(f"  高斯分布方差 σ²: {variance} packets²/s²")
    print(f"  序列长度: {num_steps} 步")
    print(f"  随机种子: {seed}")
    print()
    
    # 生成 50 步序列
    print("生成 50 步随机扰动序列...")
    sequence = generate_arrival_rate_sequence(
        initial_rates=initial_rates,
        num_steps=num_steps,
        std_dev=std_dev,
        seed=seed
    )
    
    # 保存序列到 long congested sequence/{seed} 文件夹（与 random_perturbation, increasing_sequence, hybrid_sequence 并列）
    output_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 'long congested sequence', str(seed))
    os.makedirs(output_dir, exist_ok=True)
    
    columns = [f'Commodity_{i}' for i in range(num_commodities)]
    df_sequence = pd.DataFrame(sequence, columns=columns)
    df_sequence.index.name = 'Time_Step'
    df_sequence.index = df_sequence.index + 1
    sequence_file = os.path.join(output_dir, 'arrival_rate_sequence_50_steps.csv')
    df_sequence.to_csv(sequence_file, index=True)
    print(f"序列已保存: {sequence_file}")
    print()
    
    # 检查每步优化可行性
    print("=" * 80)
    print("逐步运行优化器检查可行性...")
    print("=" * 80)
    
    results, infeasible_steps = check_optimization_feasibility_for_sequence(
        sequence, config, std_dev
    )
    
    # 保存结果
    df_results = pd.DataFrame(results)
    df_results['arrival_rates'] = df_results['arrival_rates'].apply(
        lambda x: str([f'{r:.2f}' for r in x])
    )
    results_file = os.path.join(output_dir, 'feasibility_check_results.csv')
    df_results.to_csv(results_file, index=False)
    print(f"\n结果已保存: {results_file}")
    
    # 汇总报告
    print()
    print("=" * 80)
    print("汇总报告")
    print("=" * 80)
    print()
    print(f"随机扰动高斯分布参数:")
    print(f"  标准差 σ = {std_dev} packets/s")
    print(f"  方差 σ² = {variance} packets²/s²")
    print()
    print(f"可行性统计:")
    feasible_count = sum(1 for r in results if r['feasible'])
    print(f"  可行步数: {feasible_count}/{num_steps}")
    print(f"  不可行步数: {len(infeasible_steps)}/{num_steps}")
    
    if infeasible_steps:
        print(f"\n不可行的步骤: {infeasible_steps}")
        for step_id in infeasible_steps:
            r = results[step_id - 1]
            print(f"  Step {step_id}: rates={r['arrival_rates']}, status={r['status']}")
    else:
        print(f"\n✓ 所有 {num_steps} 步优化问题均可解，未发生不可行情况。")
    
    print()
    print("=" * 80)
    
    return results, infeasible_steps


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='生成随机扰动序列并检查可行性')
    parser.add_argument('--seed', type=int, default=42, help='随机种子 (默认: 42)')
    parser.add_argument('--seeds', type=str, default=None,
                        help='多个种子，逗号分隔，如 "0,1,7,123" (指定时忽略 --seed)')
    args = parser.parse_args()
    
    if args.seeds:
        seeds = [int(s.strip()) for s in args.seeds.split(',')]
        all_results = {}
        for s in seeds:
            print(f"\n{'#'*80}\n# 处理种子 {s}\n{'#'*80}\n")
            results, infeasible_steps = main(seed=s)
            all_results[s] = {'infeasible_steps': infeasible_steps, 'feasible_count': sum(1 for r in results if r['feasible'])}
        print("\n" + "=" * 80)
        print("多种子汇总")
        print("=" * 80)
        for s, info in all_results.items():
            status = "✓ 全部可行" if not info['infeasible_steps'] else f"✗ 不可行步: {info['infeasible_steps']}"
            print(f"  seed={s}: {info['feasible_count']}/50 可行  {status}")
    else:
        results, infeasible_steps = main(seed=args.seed)
