#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculate theoretical maximum link utilization for Strategy 1 and Strategy 2
from the multi-step comparison experiment results.

This script reads the saved mcfp_results files and calculates theoretical
maximum link utilization for each step of both strategies.
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
from main.multi_step_comparison_experiment import (
    parse_path,
    calculate_max_link_utilization
)


def calculate_theoretical_utilization_for_all_steps(
    result_dir_base,
    config,
    strategy_name,
    num_steps=10,
    num_commodities=4
):
    """
    Calculate theoretical maximum link utilization for all steps of a strategy.
    
    Args:
        result_dir_base: Base directory for results (e.g., 'src/results/multi_step_comparison')
        config: Configuration dictionary
        strategy_name: 'strategy1' or 'strategy2'
        num_steps: Number of time steps
        num_commodities: Number of commodities
        
    Returns:
        list: List of dictionaries with step_id and max_link_utilization
    """
    utilizations = []
    
    for step_id in range(1, num_steps + 1):
        mcfp_file = os.path.join(
            result_dir_base, strategy_name, f'step_{step_id}',
            f'mcfp_results_flows_{num_commodities}_commodities.csv'
        )
        
        if not os.path.exists(mcfp_file):
            print(f"Warning: File not found: {mcfp_file}")
            utilizations.append({
                'step_id': step_id,
                'max_link_utilization': None
            })
            continue
            
        mcfp_df = pd.read_csv(mcfp_file)
        max_link_util = calculate_max_link_utilization(mcfp_df, config)
        utilizations.append({
            'step_id': step_id,
            'max_link_utilization': max_link_util
        })
    
    return utilizations


def main():
    """Main function to calculate and compare theoretical link utilization."""
    
    print("=" * 80)
    print("Theoretical Maximum Link Utilization Calculation")
    print("Strategy 1 (Re-optimization) vs Strategy 2 (Path Ratio Preservation)")
    print("=" * 80)
    print()
    
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(script_dir, '..')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    
    # Load configuration
    config = load_yaml_file(config_file)
    num_steps = 10
    num_commodities = 4
    
    print(f"Result directory: {result_dir_base}")
    print(f"Configuration: {config['scenario_name']}")
    print(f"Number of steps: {num_steps}")
    print(f"Number of commodities: {num_commodities}")
    print()
    
    # Calculate for Strategy 1
    print("Calculating Strategy 1 (Re-optimization)...")
    strategy1_utils = calculate_theoretical_utilization_for_all_steps(
        result_dir_base, config, 'strategy1', num_steps, num_commodities
    )
    
    # Calculate for Strategy 2
    print("Calculating Strategy 2 (Path Ratio Preservation)...")
    strategy2_utils = calculate_theoretical_utilization_for_all_steps(
        result_dir_base, config, 'strategy2', num_steps, num_commodities
    )
    
    # Create comparison DataFrame
    comparison_data = []
    for i in range(num_steps):
        step_id = i + 1
        util1 = strategy1_utils[i]['max_link_utilization']
        util2 = strategy2_utils[i]['max_link_utilization']
        
        diff = None
        strategy1_lower = None
        if util1 is not None and util2 is not None:
            diff = util1 - util2
            strategy1_lower = (util1 <= util2)
        
        comparison_data.append({
            'step_id': step_id,
            'strategy1_max_util': util1,
            'strategy2_max_util': util2,
            'difference': diff,
            'strategy1_lower_or_equal': strategy1_lower
        })
    
    df_comparison = pd.DataFrame(comparison_data)
    
    # Display results
    print("\n" + "=" * 80)
    print("Theoretical Maximum Link Utilization Comparison")
    print("=" * 80)
    print()
    print(df_comparison.to_string(index=False))
    print()
    
    # Summary statistics
    print("=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    print()
    
    valid_steps = df_comparison[
        (df_comparison['strategy1_max_util'].notna()) & 
        (df_comparison['strategy2_max_util'].notna())
    ]
    
    if len(valid_steps) > 0:
        avg_util1 = valid_steps['strategy1_max_util'].mean()
        avg_util2 = valid_steps['strategy2_max_util'].mean()
        avg_diff = valid_steps['difference'].mean()
        
        print(f"Average Max Link Utilization:")
        print(f"  Strategy 1 (Re-optimization): {avg_util1:.4f}%")
        print(f"  Strategy 2 (Path Ratio Preservation): {avg_util2:.4f}%")
        print(f"  Average Difference (Strategy1 - Strategy2): {avg_diff:.4f}%")
        print()
        
        # Check if Strategy 1 is always lower or equal
        strategy1_lower_count = valid_steps['strategy1_lower_or_equal'].sum()
        total_valid_steps = len(valid_steps)
        
        print(f"Steps where Strategy 1 ≤ Strategy 2: {strategy1_lower_count}/{total_valid_steps}")
        print(f"Steps where Strategy 1 > Strategy 2: {total_valid_steps - strategy1_lower_count}/{total_valid_steps}")
        print()
        
        if strategy1_lower_count == total_valid_steps:
            print("✓ RESULT: Strategy 1 is always lower than or equal to Strategy 2")
        else:
            steps_where_strategy1_higher = valid_steps[
                ~valid_steps['strategy1_lower_or_equal']
            ]['step_id'].tolist()
            print(f"✗ RESULT: Strategy 1 is higher than Strategy 2 in steps: {steps_where_strategy1_higher}")
            print()
            print("Details for steps where Strategy 1 > Strategy 2:")
            for step_id in steps_where_strategy1_higher:
                row = valid_steps[valid_steps['step_id'] == step_id].iloc[0]
                print(f"  Step {step_id}:")
                print(f"    Strategy 1: {row['strategy1_max_util']:.4f}%")
                print(f"    Strategy 2: {row['strategy2_max_util']:.4f}%")
                print(f"    Difference: {row['difference']:.4f}%")
    else:
        print("No valid data found!")
    
    print()
    
    # Save results to CSV
    output_file = os.path.join(result_dir_base, 'theoretical_link_utilization_comparison.csv')
    df_comparison.to_csv(output_file, index=False)
    print(f"Results saved to: {output_file}")
    print()
    
    return df_comparison


if __name__ == '__main__':
    df = main()

