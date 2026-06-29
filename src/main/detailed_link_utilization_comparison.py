#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细对比Strategy 1和Strategy 2的link utilization计算
"""

import sys
import os
import pandas as pd
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file


def parse_path(path_str):
    """Parse path string to extract interlinks."""
    pattern = r'OBPModule\((\d+),\s*(\d+)\)(?!_[ud])'
    matches = re.findall(pattern, path_str)
    
    interlinks = []
    for i in range(len(matches) - 1):
        src = tuple(map(int, matches[i]))
        dst = tuple(map(int, matches[i + 1]))
        if src != dst:
            interlinks.append((src, dst))
    
    return interlinks


def calculate_interlink_traffic(mcfp_df):
    """Calculate traffic on each interlink from MCFP results."""
    interlink_traffic = {}
    
    for _, row in mcfp_df.iterrows():
        arrival_rate = row['Arrival Rate']  # packets/s
        path = row['Path']
        if pd.isna(path):
            continue
            
        interlinks = parse_path(path)
        
        for interlink in interlinks:
            if interlink not in interlink_traffic:
                interlink_traffic[interlink] = 0
            interlink_traffic[interlink] += arrival_rate
    
    return interlink_traffic


def main():
    """Main function to compare link utilization calculation."""
    
    result_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    
    step = 2  # 选择一个步骤进行详细分析
    
    strategy1_file = os.path.join(result_dir, 'strategy1', f'step_{step}', 
                                  'mcfp_results_flows_4_commodities.csv')
    strategy2_file = os.path.join(result_dir, 'strategy2', f'step_{step}', 
                                  'mcfp_results_flows_4_commodities.csv')
    
    print("=" * 80)
    print(f"Detailed Link Utilization Comparison - Step {step}")
    print("=" * 80)
    print()
    
    df1 = pd.read_csv(strategy1_file)
    df2 = pd.read_csv(strategy2_file)
    
    print(f"Strategy 1: {len(df1)} paths, total arrival rate: {df1['Arrival Rate'].sum():.2f} packets/s")
    print(f"Strategy 2: {len(df2)} paths, total arrival rate: {df2['Arrival Rate'].sum():.2f} packets/s")
    print()
    
    # 计算每个interlink的流量
    interlink_traffic1 = calculate_interlink_traffic(df1)
    interlink_traffic2 = calculate_interlink_traffic(df2)
    
    # 计算bit rate和utilization
    max_rate1 = max(interlink_traffic1.values()) if interlink_traffic1 else 0
    max_rate2 = max(interlink_traffic2.values()) if interlink_traffic2 else 0
    
    max_bit_rate1 = max_rate1 * packet_size * 8  # bits/s
    max_bit_rate2 = max_rate2 * packet_size * 8  # bits/s
    
    util1 = (max_bit_rate1 / interlink_capacity) * 100
    util2 = (max_bit_rate2 / interlink_capacity) * 100
    
    print(f"Maximum Link Utilization:")
    print(f"  Strategy 1: {util1:.4f}%")
    print(f"  Strategy 2: {util2:.4f}%")
    print(f"  Difference (S1 - S2): {util1 - util2:.4f}%")
    print()
    
    # 找出最大utilization的interlink
    max_interlink1 = max(interlink_traffic1.items(), key=lambda x: x[1])
    max_interlink2 = max(interlink_traffic2.items(), key=lambda x: x[1])
    
    print(f"Maximum loaded interlink:")
    print(f"  Strategy 1: {max_interlink1[0]} with {max_interlink1[1]:.2f} packets/s")
    print(f"  Strategy 2: {max_interlink2[0]} with {max_interlink2[1]:.2f} packets/s")
    print()
    
    # 找出差异最大的interlink
    all_interlinks = set(interlink_traffic1.keys()) | set(interlink_traffic2.keys())
    diff_data = []
    for il in all_interlinks:
        rate1 = interlink_traffic1.get(il, 0)
        rate2 = interlink_traffic2.get(il, 0)
        diff = rate1 - rate2
        bit_rate1 = rate1 * packet_size * 8
        bit_rate2 = rate2 * packet_size * 8
        util1_il = (bit_rate1 / interlink_capacity) * 100
        util2_il = (bit_rate2 / interlink_capacity) * 100
        diff_data.append({
            'interlink': il,
            'rate1': rate1,
            'rate2': rate2,
            'diff': diff,
            'util1': util1_il,
            'util2': util2_il,
            'util_diff': util1_il - util2_il
        })
    
    diff_data.sort(key=lambda x: abs(x['diff']), reverse=True)
    
    print("Top 10 interlinks with largest difference:")
    print(f"{'Interlink':<25} {'S1 Rate':<12} {'S2 Rate':<12} {'Diff':<12} {'S1 Util%':<12} {'S2 Util%':<12} {'Util Diff%':<12}")
    print("-" * 95)
    for item in diff_data[:10]:
        il_str = f"{item['interlink'][0]}->{item['interlink'][1]}"
        print(f"{il_str:<25} {item['rate1']:>11.2f} {item['rate2']:>11.2f} {item['diff']:>+11.2f} "
              f"{item['util1']:>11.4f} {item['util2']:>11.4f} {item['util_diff']:>+11.4f}")
    print()


if __name__ == '__main__':
    main()

