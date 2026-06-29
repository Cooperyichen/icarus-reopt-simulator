#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Step 6 optimization separately to verify infeasibility.
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer

def test_step6_optimization():
    """Test Step 6 optimization with detailed output."""
    
    print("=" * 80)
    print("Step 6 Optimization Test")
    print("=" * 80)
    print()
    
    # Load sequence to get Step 6 arrival rates
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    if not os.path.exists(sequence_file):
        # Try alternative sequence files
        for alt_file in ['arrival_rate_sequence_random.csv', 
                        'arrival_rate_sequence_increasing.csv',
                        'arrival_rate_sequence_hybrid.csv']:
            alt_path = os.path.join(src_dir, 'results', alt_file)
            if os.path.exists(alt_path):
                sequence_file = alt_path
                break
    
    if not os.path.exists(sequence_file):
        print(f"✗ Sequence file not found in {os.path.join(src_dir, 'results')}")
        print("  Tried: arrival_rate_sequence_10_steps.csv, random, increasing, hybrid")
        return
    
    print(f"✓ Loading sequence from: {os.path.basename(sequence_file)}")
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    step6_rates = sequence_df.iloc[5].values.tolist()  # Step 6 (index 5, 0-based)
    
    print(f"Step 6 Arrival Rates: {step6_rates}")
    print(f"Total Demand: {sum(step6_rates):.2f} packets/s")
    print()
    
    # Compare with Step 5 and Step 7
    step5_rates = sequence_df.iloc[4].values.tolist()
    step7_rates = sequence_df.iloc[6].values.tolist()
    
    print("Comparison with adjacent steps:")
    print(f"  Step 5: {step5_rates} (Total: {sum(step5_rates):.2f} packets/s)")
    print(f"  Step 6: {step6_rates} (Total: {sum(step6_rates):.2f} packets/s) <- TESTING")
    print(f"  Step 7: {step7_rates} (Total: {sum(step7_rates):.2f} packets/s)")
    print()
    
    # Load configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Display network configuration
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    max_hops = config['optimization']['max_hops']
    split_config = config['optimization']['split_commodities']
    
    print("Network Configuration:")
    print(f"  Interlink capacity: {interlink_capacity:,} bits/s")
    print(f"  Packet size: {packet_size} bytes")
    print(f"  Max hops: {max_hops}")
    print(f"  Split commodities: {split_config}")
    print(f"  Objective: {config['optimization']['objective_func']}")
    print()
    
    # Calculate theoretical max capacity
    max_capacity_per_link_packets_s = interlink_capacity / (packet_size * 8)
    print(f"Theoretical max capacity per link: {max_capacity_per_link_packets_s:.2f} packets/s")
    print()
    
    # Create network topology
    print("Creating network topology...")
    regen_obp = ToroidalTopo(scenario_config=config, width=config['system']['width'], 
                            height=config['system']['height'])
    
    # Create demand matrix
    num_commodities = config['optimization']['num_commodities']
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities)
    
    # Update arrival rates for Step 6
    print(f"\nUpdating demand matrix with Step 6 arrival rates...")
    for idx, rate in enumerate(step6_rates):
        if idx < len(demand_matrix):
            old_rate = demand_matrix.at[idx, 'Arrival Rate']
            demand_matrix.at[idx, 'Arrival Rate'] = rate
            print(f"  Commodity {idx}: {old_rate:.2f} -> {rate:.2f} packets/s")
    
    print()
    
    # Create optimizer
    print("Initializing optimizer...")
    optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
    
    # Run optimization
    print("\n" + "=" * 80)
    print("Running Optimization")
    print("=" * 80)
    print()
    
    objective_type = config['optimization']['objective_func']
    mode = config['simulation']['failure_strategy']
    
    result = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    print("\n" + "=" * 80)
    print("Optimization Result")
    print("=" * 80)
    print()
    
    if result is None:
        print("✗ Optimization returned None - Problem is infeasible")
        return
    
    if len(result) == 0:
        print("✗ Optimization returned empty result - Problem is infeasible")
        return
    
    # Analyze result
    total_rate_in_result = result['Arrival Rate'].sum()
    expected_total = sum(step6_rates)
    
    print(f"Result Statistics:")
    print(f"  Number of paths in result: {len(result)}")
    print(f"  Total flow in result: {total_rate_in_result:.2f} packets/s")
    print(f"  Expected total: {expected_total:.2f} packets/s")
    print(f"  Difference: {expected_total - total_rate_in_result:.2f} packets/s")
    print()
    
    # Check if all commodities are satisfied
    commodity_flows = {}
    for idx, row in result.iterrows():
        comm_id = row['id_flow']
        if comm_id not in commodity_flows:
            commodity_flows[comm_id] = 0
        commodity_flows[comm_id] += row['Arrival Rate']
    
    print("Commodity Flow Satisfaction:")
    for idx, expected_rate in enumerate(step6_rates):
        actual_rate = commodity_flows.get(idx, 0)
        satisfied = abs(actual_rate - expected_rate) < 0.01
        status = "✓" if satisfied else "✗"
        print(f"  Commodity {idx}: {status} {actual_rate:.2f} / {expected_rate:.2f} packets/s")
        if not satisfied:
            print(f"    Missing: {expected_rate - actual_rate:.2f} packets/s")
    
    print()
    
    if abs(total_rate_in_result - expected_total) < 0.01:
        print("✓ Optimization SUCCEEDED - All demand satisfied")
    else:
        print("✗ Optimization PARTIALLY FAILED - Some demand not satisfied")
        print(f"  Missing: {expected_total - total_rate_in_result:.2f} packets/s")

if __name__ == '__main__':
    test_step6_optimization()

