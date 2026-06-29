#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细分析Step 2中Strategy 1和Strategy 2的流量分配差异，
解释为什么Strategy 2（固定比例）比Strategy 1（重新优化）达到更低的maximum link utilization。
"""

import sys
import os
import pandas as pd
import numpy as np
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file

def parse_path(path_str):
    """Parse path to extract interlinks."""
    pattern = r'OBPModule\((\d+),\s*(\d+)\)(?!_[ud])'
    matches = re.findall(pattern, path_str)
    
    interlinks = []
    for i in range(len(matches) - 1):
        src = tuple(map(int, matches[i]))
        dst = tuple(map(int, matches[i + 1]))
        if src != dst:
            interlinks.append((src, dst))
    
    return interlinks

def main():
    print("=" * 80)
    print("Step 2 Detailed Analysis: Strategy 1 vs Strategy 2")
    print("Why does Strategy 2 (fixed ratios) perform better?")
    print("=" * 80)
    print()
    
    # Load configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    step_id = 2
    
    # Load MCFP results
    s1_step1 = pd.read_csv(f'src/results/multi_step_comparison/strategy1/step_1/mcfp_results_flows_4_commodities.csv')
    s1_step2 = pd.read_csv(f'src/results/multi_step_comparison/strategy1/step_2/mcfp_results_flows_4_commodities.csv')
    s2_step1 = pd.read_csv(f'src/results/multi_step_comparison/strategy2/step_1/mcfp_results_flows_4_commodities.csv')
    s2_step2 = pd.read_csv(f'src/results/multi_step_comparison/strategy2/step_2/mcfp_results_flows_4_commodities.csv')
    
    # Calculate maximum link utilization
    from main.multi_step_comparison_experiment import calculate_max_link_utilization
    
    s1_step2_util = calculate_max_link_utilization(s1_step2, config)
    s2_step2_util = calculate_max_link_utilization(s2_step2, config)
    
    print(f"Maximum Link Utilization:")
    print(f"  Strategy 1: {s1_step2_util:.4f}%")
    print(f"  Strategy 2: {s2_step2_util:.4f}%")
    print(f"  Difference: {s1_step2_util - s2_step2_util:.4f}% (Strategy 2 is better)")
    print()
    
    # Calculate interlink traffic for both strategies
    interlink_capacity = config['system']['interlink_capacity']
    packet_size = config['simulation']['avg_packet_size']
    
    def get_interlink_traffic(df):
        interlink_traffic = {}
        for idx, row in df.iterrows():
            arrival_rate = row['Arrival Rate']  # packets/s
            path = row['Path']
            interlinks = parse_path(path)
            bits_rate = arrival_rate * packet_size * 8  # bits/s
            
            for interlink in interlinks:
                if interlink not in interlink_traffic:
                    interlink_traffic[interlink] = 0
                interlink_traffic[interlink] += bits_rate
        return interlink_traffic
    
    s1_interlink_traffic = get_interlink_traffic(s1_step2)
    s2_interlink_traffic = get_interlink_traffic(s2_step2)
    
    # Calculate utilization for each interlink
    s1_utils = {link: (traffic / interlink_capacity) * 100 
                for link, traffic in s1_interlink_traffic.items()}
    s2_utils = {link: (traffic / interlink_capacity) * 100 
                for link, traffic in s2_interlink_traffic.items()}
    
    # Find maximum utilization interlinks
    s1_max_link = max(s1_utils.items(), key=lambda x: x[1])
    s2_max_link = max(s2_utils.items(), key=lambda x: x[1])
    
    print(f"Maximum Utilization Interlink:")
    print(f"  Strategy 1: {s1_max_link[0]} -> Utilization: {s1_max_link[1]:.4f}%")
    print(f"  Strategy 2: {s2_max_link[0]} -> Utilization: {s2_max_link[1]:.4f}%")
    print()
    
    # Compare traffic on Strategy 1's max interlink
    target_link = s1_max_link[0]
    s1_traffic_on_max = s1_interlink_traffic[target_link]
    s2_traffic_on_max = s2_interlink_traffic.get(target_link, 0)
    
    print(f"Traffic on Strategy 1's maximum interlink {target_link}:")
    print(f"  Strategy 1: {s1_traffic_on_max:,.2f} bits/s ({s1_max_link[1]:.4f}% utilization)")
    print(f"  Strategy 2: {s2_traffic_on_max:,.2f} bits/s ({s2_utils.get(target_link, 0):.4f}% utilization)")
    print(f"  Difference: {s1_traffic_on_max - s2_traffic_on_max:,.2f} bits/s")
    print()
    
    # Find top interlinks by utilization difference
    all_links = set(s1_utils.keys()) | set(s2_utils.keys())
    link_diffs = []
    for link in all_links:
        s1_util = s1_utils.get(link, 0)
        s2_util = s2_utils.get(link, 0)
        diff = s1_util - s2_util  # Positive means S1 is higher
        link_diffs.append({
            'interlink': link,
            's1_util': s1_util,
            's2_util': s2_util,
            'diff': diff
        })
    
    link_diffs_sorted = sorted(link_diffs, key=lambda x: x['diff'], reverse=True)
    
    print("=" * 80)
    print("Top 10 Interlinks with Largest Utilization Differences")
    print("(Positive diff means Strategy 1 has higher utilization)")
    print("=" * 80)
    print()
    print(f"{'Interlink':<30} {'Strategy 1':>12} {'Strategy 2':>12} {'Difference':>12}")
    print("-" * 70)
    for item in link_diffs_sorted[:10]:
        link_str = f"{item['interlink'][0]} -> {item['interlink'][1]}"
        print(f"{link_str:<30} {item['s1_util']:>11.4f}% {item['s2_util']:>11.4f}% {item['diff']:>11.4f}%")
    print()
    
    # Extract path ratios for comparison
    def extract_ratios(df):
        ratios = {}
        for commodity_id in df['id_flow'].unique():
            comm_df = df[df['id_flow'] == commodity_id]
            total = comm_df['Arrival Rate'].sum()
            if total > 0:
                path_ratios = {}
                for _, row in comm_df.iterrows():
                    path_ratios[row['Path']] = row['Arrival Rate'] / total
                ratios[int(commodity_id)] = path_ratios
        return ratios
    
    s1_step1_ratios = extract_ratios(s1_step1)
    s1_step2_ratios = extract_ratios(s1_step2)
    s2_step1_ratios = extract_ratios(s2_step1)
    s2_step2_ratios = extract_ratios(s2_step2)
    
    print("=" * 80)
    print("Path Ratio Analysis")
    print("=" * 80)
    print()
    
    for commodity_id in sorted(s1_step1_ratios.keys()):
        print(f"Commodity {commodity_id}:")
        
        # Check if Strategy 1 changed ratios from Step 1 to Step 2
        s1_comm_paths = set(s1_step1_ratios[commodity_id].keys())
        if commodity_id in s1_step2_ratios:
            s1_step2_paths = set(s1_step2_ratios[commodity_id].keys())
            s1_paths_same = s1_comm_paths == s1_step2_paths
            
            if s1_paths_same:
                # Calculate max ratio change
                max_ratio_change = 0.0
                for path in s1_comm_paths:
                    if path in s1_step2_ratios[commodity_id]:
                        change = abs(s1_step1_ratios[commodity_id][path] - s1_step2_ratios[commodity_id][path])
                        max_ratio_change = max(max_ratio_change, change)
                print(f"  Strategy 1: Paths same, max ratio change: {max_ratio_change:.6f}")
            else:
                print(f"  Strategy 1: Paths changed (Step 1: {len(s1_comm_paths)}, Step 2: {len(s1_step2_paths)})")
        
        # Strategy 2 should have identical ratios
        s2_comm_paths = set(s2_step1_ratios[commodity_id].keys())
        if commodity_id in s2_step2_ratios:
            s2_step2_paths = set(s2_step2_ratios[commodity_id].keys())
            s2_paths_same = s2_comm_paths == s2_step2_paths
            if s2_paths_same:
                max_ratio_diff = 0.0
                for path in s2_comm_paths:
                    if path in s2_step2_ratios[commodity_id]:
                        diff = abs(s2_step1_ratios[commodity_id][path] - s2_step2_ratios[commodity_id][path])
                        max_ratio_diff = max(max_ratio_diff, diff)
                print(f"  Strategy 2: Paths same, max ratio diff: {max_ratio_diff:.2e} (preserved)")
        print()
    
    print("=" * 80)
    print("Conclusion: Why Strategy 2 Performs Better")
    print("=" * 80)
    print()
    print("1. OBJECTIVE MISMATCH:")
    print("   - The optimizer uses 'minimize_max_flow' objective")
    print("   - This minimizes the maximum flow on any single PATH")
    print("   - It does NOT directly minimize the maximum utilization on any single LINK")
    print()
    print("2. PATH vs LINK:")
    print("   - A path may use multiple interlinks")
    print("   - Minimizing max path flow does not guarantee minimizing max link utilization")
    print("   - Multiple paths can share the same interlink")
    print()
    print("3. RE-OPTIMIZATION EFFECT:")
    print("   - Strategy 1 re-optimizes at Step 2 with new arrival rates")
    print("   - The optimizer may redistribute flows to minimize max path flow")
    print("   - This redistribution can inadvertently create bottlenecks on specific interlinks")
    print()
    print("4. PATH RATIO PRESERVATION:")
    print("   - Strategy 2 maintains the path ratios from Step 1")
    print("   - Step 1 optimization found a globally balanced distribution")
    print("   - This balance is maintained even when arrival rates change")
    print()
    print("5. RESULT:")
    print("   - Strategy 1's re-optimization creates a local optimum for path flows")
    print("   - But this local optimum can have higher link utilization")
    print("   - Strategy 2's preserved ratios maintain global link balance")
    print(f"   - Result: Strategy 2 has {s1_step2_util - s2_step2_util:.4f}% lower max link utilization")
    print()


if __name__ == '__main__':
    main()

