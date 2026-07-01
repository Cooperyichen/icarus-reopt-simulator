#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze infeasibility issue at Step 6 and extract dual variables for all steps.
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.regenerate_obp import RegenerateOBP
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from main.multi_step_comparison_experiment import apply_path_ratios_to_demand

def analyze_infeasibility(step_id, arrival_rates, config_file):
    """Analyze why optimization is infeasible at a specific step."""
    
    print("=" * 80)
    print(f"Infeasibility Analysis for Step {step_id}")
    print("=" * 80)
    print()
    
    # Load config
    config = load_yaml_file(config_file)
    
    # Create regen_obp
    regen_obp = RegenerateOBP(config_file)
    
    # Create demand matrix
    demand_matrix = regen_obp.generate_demand_matrix()
    
    # Update arrival rates
    for idx, rate in enumerate(arrival_rates):
        if idx < len(demand_matrix):
            demand_matrix.at[idx, 'Arrival Rate'] = rate
    
    print(f"Arrival rates for Step {step_id}: {arrival_rates}")
    print(f"Total demand: {sum(arrival_rates):.2f} packets/s")
    print()
    
    # Create optimizer
    optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
    
    # Check basic constraints
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    
    print("Network Configuration:")
    print(f"  Interlink capacity: {interlink_capacity:,} bits/s")
    print(f"  Packet size: {packet_size} bytes")
    print(f"  Max capacity per link: {interlink_capacity / (packet_size * 8) * 1000:.2f} packets/ms")
    print()
    
    # Try to solve
    objective_type = config['optimization']['objective_func']
    mode = config['simulation']['failure_strategy']
    
    print("Attempting optimization...")
    result = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    if result is None or len(result) == 0:
        print("✗ Optimization returned no result")
        return None
    
    total_rate = result['Arrival Rate'].sum()
    print(f"✓ Optimization returned result with total rate: {total_rate:.2f}")
    print(f"  Number of paths: {len(result)}")
    
    return result

def extract_dual_variables_for_all_steps():
    """Extract dual variables for all steps of Strategy 1."""
    
    print("=" * 80)
    print("Extracting Dual Variables for All Steps")
    print("=" * 80)
    print()
    
    # This requires modifying the optimizer to return dual variables
    # For now, we'll create a modified version that extracts duals
    
    print("Note: Dual variable extraction requires modification of optimizer.")
    print("We'll need to modify solve_mcfp_path_formulation to return dual values.")
    print()
    
    # Load sequence
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    if not os.path.exists(sequence_file):
        print(f"✗ Sequence file not found: {sequence_file}")
        return
    
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    
    dual_variables = {}
    
    for step_id in range(1, 11):
        arrival_rates = sequence[step_id - 1].tolist()
        
        # Re-run optimization to get duals (this will be slow)
        result = analyze_infeasibility(step_id, arrival_rates, config_file)
        
        if step_id == 6:
            print("\n" + "=" * 80)
            print("Detailed Analysis for Step 6 (Infeasible Step)")
            print("=" * 80)
            print()
            print("Checking constraints manually...")
            print()
    
    return dual_variables

if __name__ == '__main__':
    # Load sequence to get Step 6 arrival rates
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    if os.path.exists(sequence_file):
        sequence_df = pd.read_csv(sequence_file, index_col=0)
        step6_rates = sequence_df.iloc[5].values.tolist()  # Step 6 (index 5)
        
        config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
        
        print("Analyzing Step 6 infeasibility...")
        result = analyze_infeasibility(6, step6_rates, config_file)
    else:
        print(f"✗ Sequence file not found: {sequence_file}")

