#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify dual variable sign convention for demand constraints.

This script tests:
1. Whether CVXPY returns positive or negative dual variables for equality constraints
2. Whether the constraint order matches the demand matrix order
3. Whether dual variables should be negated
"""

import sys
import os
import pandas as pd
import numpy as np
import cvxpy as cp

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer


def test_simple_cvxpy_equality_constraint():
    """Test CVXPY dual variable sign for a simple minimization problem."""
    print("=" * 80)
    print("Test 1: Simple CVXPY Equality Constraint Dual Variable Sign")
    print("=" * 80)
    print()
    
    # Simple test: minimize max(x, y) subject to x + y = d
    # When d increases, max(x,y) should increase (objective worsens)
    # So dual variable should be positive
    
    x = cp.Variable()
    y = cp.Variable()
    d = 10  # demand parameter
    
    # Constraint: x + y == d
    constraint = (x + y == d)
    
    # Objective: minimize max(x, y)
    objective = cp.Minimize(cp.maximum(x, y))
    
    problem = cp.Problem(objective, [constraint])
    problem.solve()
    
    print(f"Problem: minimize max(x,y) subject to x+y={d}")
    print(f"  Solution: x={x.value:.6f}, y={y.value:.6f}")
    print(f"  Objective: {problem.value:.6f}")
    print(f"  Dual variable: {constraint.dual_value:.6e}")
    print(f"  Interpretation: Increase d by 1, objective changes by {constraint.dual_value:.6e}")
    print(f"  Expected: positive (increasing d should increase max(x,y))")
    print()
    
    # Test with increased demand
    d2 = 11
    constraint2 = (x + y == d2)
    problem2 = cp.Problem(objective, [constraint2])
    problem2.solve()
    
    obj_diff = problem2.value - problem.value
    print(f"  Actual objective change when d increases by 1: {obj_diff:.6e}")
    print(f"  Match with dual variable: {abs(obj_diff - constraint.dual_value) < 1e-5}")
    print()
    
    return constraint.dual_value > 0


def test_optimizer_dual_variable_extraction():
    """Test dual variable extraction from the actual optimizer."""
    print("=" * 80)
    print("Test 2: Optimizer Dual Variable Extraction")
    print("=" * 80)
    print()
    
    # Load config
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Create topology
    regen_obp = ToroidalTopo(scenario_config=config, width=config['system']['width'],
                            height=config['system']['height'])
    
    # Create demand matrix
    num_commodities = config['optimization']['num_commodities']
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    
    print("Original demand matrix:")
    print(demand_matrix[['Source', 'Destination', 'Arrival Rate']])
    print()
    
    # Create optimizer and run
    optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
    objective_type = config['optimization']['objective_func']
    mode = config['simulation']['failure_strategy']
    
    print(f"Running optimization with objective: {objective_type}")
    result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    # Extract dual variables
    dual_vars = {}
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
        print(f"\n✓ Dual variables extracted: {len(dual_vars)} commodities")
        print()
        print("Dual Variable Values:")
        for idx in sorted(dual_vars.keys()):
            dual_val = dual_vars[idx]
            if dual_val is not None:
                print(f"  Commodity {idx}: {dual_val:.6e}")
                print(f"    Demand: {demand_matrix.loc[idx, 'Arrival Rate']:.2f} packets/s")
                print(f"    Expected sign: positive (increasing demand should increase max link utilization)")
            else:
                print(f"  Commodity {idx}: None")
        print()
        
        # Check if all values are the same
        non_none_vals = [v for v in dual_vars.values() if v is not None]
        if len(non_none_vals) > 1:
            unique_vals = set([abs(v) for v in non_none_vals])
            if len(unique_vals) == 1:
                print("⚠️  WARNING: All dual variables have the same absolute value!")
                print(f"   This is suspicious - different commodities should have different dual values.")
            else:
                print(f"✓ Dual variables vary across commodities (good)")
        
        # Check signs
        all_positive = all(v > 0 for v in non_none_vals if v is not None)
        all_negative = all(v < 0 for v in non_none_vals if v is not None)
        
        if all_positive:
            print("✓ All dual variables are positive (correct for minimization)")
        elif all_negative:
            print("⚠️  WARNING: All dual variables are negative!")
            print("   For minimize max_link_utilization, dual variables should be positive.")
            print("   This suggests the sign convention may be inverted.")
        else:
            print("⚠️  Mixed signs in dual variables (unexpected for equality constraints)")
    
    else:
        print("✗ Dual variables not found in result")
    
    return dual_vars


def test_demand_increase_impact():
    """Test actual impact of increasing demand on objective."""
    print("=" * 80)
    print("Test 3: Actual Impact of Demand Increase on Objective")
    print("=" * 80)
    print()
    
    # Load config
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Create topology
    regen_obp = ToroidalTopo(scenario_config=config, width=config['system']['width'],
                            height=config['system']['height'])
    
    # Create demand matrix
    num_commodities = config['optimization']['num_commodities']
    demand_matrix_base = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    
    # Create optimizer
    optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
    objective_type = config['optimization']['objective_func']
    mode = config['simulation']['failure_strategy']
    
    # Run baseline optimization
    print("Running baseline optimization...")
    result_base = optimizer.solve_mcfp_path_formulation(demand_matrix_base, objective_type, mode)
    
    # Get baseline objective (max link utilization)
    from main.multi_step_comparison_experiment import calculate_max_link_utilization
    base_util = calculate_max_link_utilization(result_base, config)
    print(f"  Baseline max link utilization: {base_util:.6f}%")
    print()
    
    # Test increasing demand for each commodity by 1 packet/s
    print("Testing impact of increasing each commodity's demand by 1 packet/s:")
    for commodity_id in range(num_commodities):
        demand_matrix_test = demand_matrix_base.copy()
        original_demand = demand_matrix_test.loc[commodity_id, 'Arrival Rate']
        demand_matrix_test.loc[commodity_id, 'Arrival Rate'] = original_demand + 1.0
        
        result_test = optimizer.solve_mcfp_path_formulation(demand_matrix_test, objective_type, mode)
        test_util = calculate_max_link_utilization(result_test, config)
        
        util_change = test_util - base_util
        print(f"  Commodity {commodity_id}: demand {original_demand:.2f} -> {original_demand+1:.2f}")
        print(f"    Max link util change: {util_change:.6e}%")
        print(f"    Expected from dual: (check dual variable value)")
        print()
    
    return True


def main():
    """Main function to run all tests."""
    print("=" * 80)
    print("Dual Variable Sign and Extraction Verification")
    print("=" * 80)
    print()
    
    # Test 1: Simple CVXPY example
    test1_passed = test_simple_cvxpy_equality_constraint()
    
    print()
    print("=" * 80)
    print()
    
    # Test 2: Actual optimizer
    dual_vars = test_optimizer_dual_variable_extraction()
    
    print()
    print("=" * 80)
    print()
    
    # Test 3: Verify by perturbing demand
    test_demand_increase_impact()
    
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    print(f"Test 1 (Simple CVXPY): Dual variable positive = {test1_passed}")
    if dual_vars:
        non_none = [v for v in dual_vars.values() if v is not None]
        if non_none:
            all_neg = all(v < 0 for v in non_none)
            print(f"Test 2 (Optimizer): All dual variables negative = {all_neg}")
            if all_neg:
                print("  → RECOMMENDATION: Negate dual variables in optimizer extraction code")
    print()


if __name__ == '__main__':
    main()

