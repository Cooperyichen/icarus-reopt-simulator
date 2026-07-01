#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify dual variable extraction functionality.
"""

import sys
import os
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer

def test_dual_variables():
    """Test dual variable extraction."""
    
    print("=" * 80)
    print("Dual Variable Extraction Test")
    print("=" * 80)
    print()
    
    # Load configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Load sequence to get Step 6 arrival rates (or use default rates)
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    if os.path.exists(sequence_file):
        sequence_df = pd.read_csv(sequence_file, index_col=0)
        step6_rates = sequence_df.iloc[5].values.tolist()
        print(f"Using Step 6 arrival rates from sequence: {step6_rates}")
    else:
        # Use default rates from config
        step6_rates = config['fixed_demand']['arrival_rate']
        print(f"Using default arrival rates from config: {step6_rates}")
    
    print()
    
    # Create network topology
    regen_obp = ToroidalTopo(scenario_config=config, width=config['system']['width'], 
                            height=config['system']['height'])
    
    # Create demand matrix
    num_commodities = config['optimization']['num_commodities']
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities)
    
    # Update arrival rates
    for idx, rate in enumerate(step6_rates):
        if idx < len(demand_matrix):
            demand_matrix.at[idx, 'Arrival Rate'] = rate
    
    # Create optimizer
    optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
    
    # Run optimization
    objective_type = config['optimization']['objective_func']
    mode = config['simulation']['failure_strategy']
    
    print("Running optimization...")
    result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    print("\n" + "=" * 80)
    print("Accessing Dual Variables from Result")
    print("=" * 80)
    print()
    
    # Access dual variables from DataFrame attributes
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
        print(f"✓ Dual variables extracted successfully")
        print(f"  Number of commodities: {len(dual_vars)}")
        print()
        print("Dual Variable Values:")
        for idx, dual_val in sorted(dual_vars.items()):
            if dual_val is not None:
                print(f"  Commodity {idx}: {dual_val:.6e}")
                print(f"    Interpretation: If demand for commodity {idx} increases by 1 packet/s,")
                print(f"                   the maximum link utilization will change by {dual_val:.6e}%")
            else:
                print(f"  Commodity {idx}: None (not available)")
        print()
    else:
        print("✗ Dual variables not found in result")
        print(f"  Available attributes: {list(result_df.attrs.keys()) if hasattr(result_df, 'attrs') else 'No attrs'}")
        print()
    
    # Verify dual variables are accessible
    print("=" * 80)
    print("Verification")
    print("=" * 80)
    print()
    
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
        print("✓ Dual variables are accessible via result_df.attrs['dual_variables']")
        print(f"✓ Return type: {type(result_df)}")
        print(f"✓ Dual variables type: {type(dual_vars)} (should be dict)")
        print()
        print("Example usage:")
        print("  result_df = optimizer.solve_mcfp_path_formulation(...)")
        print("  dual_vars = result_df.attrs['dual_variables']")
        print("  print(dual_vars[0])  # Dual variable for commodity 0")
    else:
        print("✗ Dual variables not accessible")

if __name__ == '__main__':
    test_dual_variables()

