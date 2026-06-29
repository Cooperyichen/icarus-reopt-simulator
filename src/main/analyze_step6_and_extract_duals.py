#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Step 6 infeasibility and extract dual variables for all steps.
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

def modify_optimizer_for_duals(optimizer):
    """Enable dual variable storage in optimizer."""
    optimizer._store_dual_variables = True

def extract_dual_variables(optimizer, demand_constraints):
    """Extract dual variables from solved problem."""
    # Access dual values through constraints
    dual_vars = {}
    for i, constraint in enumerate(demand_constraints):
        try:
            dual_value = constraint.dual_value
            if dual_value is not None:
                dual_vars[i] = float(dual_value)
        except:
            pass
    return dual_vars

def analyze_step6_and_extract_duals():
    """Analyze Step 6 and extract duals for all steps."""
    
    # Load sequence
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    if not os.path.exists(sequence_file):
        # Try alternative path
        sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_random.csv')
        if not os.path.exists(sequence_file):
            print(f"✗ Sequence file not found")
            return
    
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    print("=" * 80)
    print("Step 6 Infeasibility Analysis and Dual Variable Extraction")
    print("=" * 80)
    print()
    
    # Analyze Step 6 specifically
    step6_rates = sequence_df.iloc[5].values.tolist()
    print(f"Step 6 Arrival Rates: {step6_rates}")
    print(f"Total Demand: {sum(step6_rates):.2f} packets/s")
    print()
    
    # Check Step 5 and Step 7 for comparison
    step5_rates = sequence_df.iloc[4].values.tolist()
    step7_rates = sequence_df.iloc[6].values.tolist()
    
    print("Comparison:")
    print(f"  Step 5: {step5_rates} (Total: {sum(step5_rates):.2f})")
    print(f"  Step 6: {step6_rates} (Total: {sum(step6_rates):.2f}) - INFEASIBLE")
    print(f"  Step 7: {step7_rates} (Total: {sum(step7_rates):.2f})")
    print()
    
    # Note: To extract dual variables, we need to modify the optimizer
    # For now, we'll explain what we need to do
    
    print("=" * 80)
    print("Note on Dual Variable Extraction")
    print("=" * 80)
    print()
    print("Dual variables correspond to demand constraints:")
    print("  For each commodity i: sum(flows on all paths) = demand_i")
    print("  Dual variable λ_i represents the marginal cost of increasing demand_i")
    print()
    print("To extract dual variables, we need to:")
    print("  1. Access constraint.dual_value after problem.solve()")
    print("  2. Store demand_constraints list in optimizer")
    print("  3. Extract dual values for each demand constraint")
    print()
    
    # Create a modified optimizer run for Step 6
    regen_obp = RegenerateOBP(config_file)
    demand_matrix = regen_obp.generate_demand_matrix()
    
    for idx, rate in enumerate(step6_rates):
        if idx < len(demand_matrix):
            demand_matrix.at[idx, 'Arrival Rate'] = rate
    
    optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
    objective_type = config['optimization']['objective_func']
    mode = config['simulation']['failure_strategy']
    
    print("Attempting Step 6 optimization with detailed output...")
    print()
    
    # The optimizer will print detailed information about infeasibility
    result = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    if result is None or len(result) == 0:
        print("✗ Optimization returned no result - truly infeasible")
    else:
        total_rate = result['Arrival Rate'].sum()
        if total_rate < sum(step6_rates) * 0.99:  # Allow small numerical error
            print(f"⚠️  Optimization returned partial result (total: {total_rate:.2f}, expected: {sum(step6_rates):.2f})")
            print("   Some commodities may have been marked as infeasible")
        else:
            print(f"✓ Optimization succeeded (total: {total_rate:.2f})")
    
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    print("The optimizer uses a loop that removes commodities marked as 'Infeasible'")
    print("when the problem is infeasible. The specific constraint that causes")
    print("infeasibility may be a capacity constraint on a specific interlink,")
    print("or a combination of demand and capacity constraints that cannot be satisfied.")
    print()
    print("To fully diagnose, we would need to:")
    print("  1. Check each capacity constraint individually")
    print("  2. Analyze the path structure for Step 6")
    print("  3. Compare with Step 5 and Step 7 to identify what changed")
    print()

if __name__ == '__main__':
    analyze_step6_and_extract_duals()

