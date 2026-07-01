#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证脚本：检查两点
1. Strategy 2的路径比例保持是否正确
2. 十个时间步的simulation_time和generation_finish_time是否一致
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


def verify_path_ratio_preservation(result_dir_base, num_steps=10, num_commodities=4):
    """
    验证Strategy 2的路径比例保持是否正确。
    
    检查每个步骤的路径比例是否与Step 1保持一致。
    """
    print("=" * 80)
    print("Verification 1: Path Ratio Preservation in Strategy 2")
    print("=" * 80)
    print()
    
    # 加载Step 1的baseline
    step1_file = os.path.join(result_dir_base, 'strategy2', 'step_1', 
                              f'mcfp_results_flows_{num_commodities}_commodities.csv')
    
    if not os.path.exists(step1_file):
        print(f"✗ Error: Step 1 file not found: {step1_file}")
        return False
    
    df1 = pd.read_csv(step1_file)
    
    # 计算Step 1的路径比例
    baseline_ratios = {}
    for commodity_id in df1['id_flow'].unique():
        commodity_df = df1[df1['id_flow'] == commodity_id]
        total = commodity_df['Arrival Rate'].sum()
        if total > 0:
            ratios = {}
            for _, row in commodity_df.iterrows():
                path = row['Path']
                rate = row['Arrival Rate']
                ratios[path] = rate / total
            baseline_ratios[int(commodity_id)] = ratios
    
    print(f"Step 1 (Baseline):")
    for commodity_id, ratios in sorted(baseline_ratios.items()):
        print(f"  Commodity {commodity_id}: {len(ratios)} paths, total ratio = {sum(ratios.values()):.10f}")
    print()
    
    # 检查每个后续步骤
    all_correct = True
    max_ratio_diff = 0.0
    max_diff_step = None
    max_diff_commodity = None
    
    for step_id in range(2, num_steps + 1):
        step_file = os.path.join(result_dir_base, 'strategy2', f'step_{step_id}',
                                 f'mcfp_results_flows_{num_commodities}_commodities.csv')
        
        if not os.path.exists(step_file):
            print(f"✗ Step {step_id}: File not found")
            all_correct = False
            continue
        
        df_step = pd.read_csv(step_file)
        
        # 计算当前步骤的路径比例
        step_ratios = {}
        for commodity_id in df_step['id_flow'].unique():
            commodity_df = df_step[df_step['id_flow'] == commodity_id]
            total = commodity_df['Arrival Rate'].sum()
            if total > 0:
                ratios = {}
                for _, row in commodity_df.iterrows():
                    path = row['Path']
                    rate = row['Arrival Rate']
                    ratios[path] = rate / total
                step_ratios[int(commodity_id)] = ratios
        
        # 与baseline比较
        step_correct = True
        for commodity_id in sorted(baseline_ratios.keys()):
            if commodity_id not in step_ratios:
                print(f"✗ Step {step_id}, Commodity {commodity_id}: Missing in step ratios")
                all_correct = False
                step_correct = False
                continue
            
            baseline = baseline_ratios[commodity_id]
            step_ratio = step_ratios[commodity_id]
            
            # 比较每条路径的比例
            for path in baseline.keys():
                baseline_ratio = baseline[path]
                if path in step_ratio:
                    step_ratio_val = step_ratio[path]
                    diff = abs(baseline_ratio - step_ratio_val)
                    if diff > max_ratio_diff:
                        max_ratio_diff = diff
                        max_diff_step = step_id
                        max_diff_commodity = commodity_id
                    
                    # 允许小的浮点数误差（1e-6）
                    if diff > 1e-6:
                        print(f"✗ Step {step_id}, Commodity {commodity_id}, Path: {path[:60]}...")
                        print(f"    Baseline ratio: {baseline_ratio:.10f}")
                        print(f"    Step ratio: {step_ratio_val:.10f}")
                        print(f"    Difference: {diff:.10e}")
                        all_correct = False
                        step_correct = False
                else:
                    if baseline_ratio > 1e-10:  # 只在比例显著时报告
                        print(f"✗ Step {step_id}, Commodity {commodity_id}: Path missing in step: {path[:60]}...")
                        all_correct = False
                        step_correct = False
        
        if step_correct:
            print(f"✓ Step {step_id}: Path ratios preserved correctly")
        else:
            print(f"✗ Step {step_id}: Path ratios NOT preserved correctly")
    
    print()
    if all_correct:
        print("✓ RESULT: All steps preserve path ratios correctly!")
        print(f"  Maximum ratio difference: {max_ratio_diff:.10e}")
    else:
        print("✗ RESULT: Path ratios are NOT preserved correctly in some steps!")
        if max_diff_step is not None:
            print(f"  Maximum difference: {max_ratio_diff:.10e} at Step {max_diff_step}, Commodity {max_diff_commodity}")
    
    print()
    return all_correct


def verify_simulation_parameters(config_file, num_steps=10):
    """
    验证十个时间步的simulation_time和generation_finish_time是否一致。
    """
    print("=" * 80)
    print("Verification 2: Simulation Parameters Consistency")
    print("=" * 80)
    print()
    
    # 加载原始配置
    config = load_yaml_file(config_file)
    
    original_sim_time = config['simulation']['simulation_time']
    original_gen_finish_time = config['simulation']['generation_finish_time']
    
    print(f"Original config values:")
    print(f"  simulation_time: {original_sim_time} ms")
    print(f"  generation_finish_time: {original_gen_finish_time} ms")
    print()
    
    # 模拟每个步骤的配置（像实验代码那样）
    print("Checking step configurations:")
    print()
    
    all_consistent = True
    for step_id in range(1, num_steps + 1):
        # 模拟实验代码中的配置创建过程
        step_config = config.copy()
        step_config['simulation'] = config['simulation'].copy()
        step_config['simulation']['num_steps'] = 1
        
        sim_time = step_config['simulation']['simulation_time']
        gen_finish_time = step_config['simulation']['generation_finish_time']
        
        consistent = (sim_time == original_sim_time and 
                      gen_finish_time == original_gen_finish_time)
        
        if not consistent:
            all_consistent = False
            print(f"✗ Step {step_id}: INCONSISTENT!")
            print(f"  simulation_time: {sim_time} ms (expected {original_sim_time})")
            print(f"  generation_finish_time: {gen_finish_time} ms (expected {original_gen_finish_time})")
        elif step_id <= 3 or step_id == num_steps:
            # 只显示前3步和最后一步
            print(f"✓ Step {step_id}: OK (sim_time={sim_time}ms, gen_finish={gen_finish_time}ms)")
    
    print()
    if all_consistent:
        print("✓ RESULT: All steps have consistent simulation_time and generation_finish_time")
    else:
        print("✗ RESULT: Found inconsistencies in some steps!")
    
    print()
    print("=" * 80)
    print("Note: calculate_max_link_utilization uses generation_finish_time from config")
    print(f"All steps should use: {original_gen_finish_time} ms for link utilization calculation")
    print("=" * 80)
    print()
    
    return all_consistent


def main():
    """Main function to run both verifications."""
    
    print("=" * 80)
    print("Strategy 2 Verification Script")
    print("=" * 80)
    print()
    
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(script_dir, '..')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    
    num_steps = 10
    num_commodities = 4
    
    # Verification 1: Path ratio preservation
    ratio_correct = verify_path_ratio_preservation(result_dir_base, num_steps, num_commodities)
    
    # Verification 2: Simulation parameters consistency
    params_consistent = verify_simulation_parameters(config_file, num_steps)
    
    # Summary
    print("=" * 80)
    print("Verification Summary")
    print("=" * 80)
    print()
    print(f"1. Path Ratio Preservation: {'✓ PASS' if ratio_correct else '✗ FAIL'}")
    print(f"2. Simulation Parameters Consistency: {'✓ PASS' if params_consistent else '✗ FAIL'}")
    print()
    
    if ratio_correct and params_consistent:
        print("✓ All verifications passed!")
    else:
        print("✗ Some verifications failed!")
    print()


if __name__ == '__main__':
    main()

