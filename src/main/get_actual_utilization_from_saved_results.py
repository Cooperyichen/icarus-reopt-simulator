#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract actual maximum link utilization from saved multi-step simulation results.

This script re-runs simulations briefly to get switches object, then calculates
actual link utilization from port statistics.
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
import main.main as main_module
from main.multi_step_comparison_experiment import (
    calculate_actual_max_link_utilization_from_simulation
)


def get_actual_util_for_step(step_dir, step_config, precomputed_demand_matrix, num_commodities=4):
    """
    Re-run simulation for one step to get switches, then calculate actual utilization.
    
    Args:
        step_dir: Directory for this step
        step_config: Configuration for this step
        precomputed_demand_matrix: Precomputed demand matrix (DataFrame)
        num_commodities: Number of commodities
        
    Returns:
        float: Actual maximum link utilization percentage
    """
    # Re-run simulation with same seed for reproducibility
    np.random.seed(42)
    
    try:
        all_flows, switches, blocked_flows = main_module.run_simulation_scenario(
            step_config, step_dir, 0, precomputed_demand_matrix=precomputed_demand_matrix
        )
        
        # Calculate actual utilization
        max_util_actual = calculate_actual_max_link_utilization_from_simulation(switches, step_config)
        
        return max_util_actual
    except Exception as e:
        print(f"  Error: {e}")
        return None


def extract_actual_util_for_strategy(result_dir_base, strategy_name, sequence_name=None, config=None, num_steps=10, num_commodities=4):
    """
    Extract actual maximum link utilization for all steps of a strategy.
    
    Args:
        result_dir_base: Base directory for results
        strategy_name: 'strategy1', 'strategy2', or 'strategy3'
        sequence_name: Name of sequence (None for root directory)
        config: Configuration dictionary
        num_steps: Number of steps
        num_commodities: Number of commodities
        
    Returns:
        list: List of actual utilization values for each step
    """
    if config is None:
        config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
        config = load_yaml_file(config_file)
    
    # Determine strategy directory
    if sequence_name:
        strategy_dir = os.path.join(result_dir_base, sequence_name, strategy_name)
    else:
        strategy_dir = os.path.join(result_dir_base, strategy_name)
    
    actual_utils = []
    
    # Load arrival rates from stats file if available
    stats_file = os.path.join(strategy_dir, f'{strategy_name}_stats.csv')
    arrival_rates_list = None
    
    if os.path.exists(stats_file):
        stats_df = pd.read_csv(stats_file)
        arrival_rates_list = []
        for _, row in stats_df.iterrows():
            rates_str = row['arrival_rates']
            rates = eval(rates_str) if isinstance(rates_str, str) else rates_str
            arrival_rates_list.append(rates)
    
    for step_id in range(1, num_steps + 1):
        step_dir = os.path.join(strategy_dir, f'step_{step_id}')
        mcfp_file = os.path.join(step_dir, f'mcfp_results_flows_{num_commodities}_commodities.csv')
        
        if not os.path.exists(mcfp_file):
            print(f"  Step {step_id}: MCFP file not found, skipping")
            actual_utils.append(None)
            continue
        
        # Load precomputed demand matrix
        precomputed_demand_matrix = pd.read_csv(mcfp_file)
        
        # Prepare step config
        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        
        if arrival_rates_list and step_id <= len(arrival_rates_list):
            step_config['fixed_demand']['arrival_rate'] = arrival_rates_list[step_id - 1]
        
        step_config['simulation'] = config['simulation'].copy()
        step_config['simulation']['num_steps'] = 1
        
        # Get actual utilization
        print(f"  Step {step_id}...", end=' ', flush=True)
        max_util_actual = get_actual_util_for_step(
            step_dir, step_config, precomputed_demand_matrix, num_commodities
        )
        
        if max_util_actual is not None:
            print(f"{max_util_actual:.4f}%")
            actual_utils.append(max_util_actual)
        else:
            print("Failed")
            actual_utils.append(None)
    
    return actual_utils


def main():
    """Main function to extract actual utilization for all strategies."""
    
    print("=" * 80)
    print("Extracting Actual Maximum Link Utilization from Simulation Results")
    print("=" * 80)
    print()
    print("Note: This will re-run simulations to extract port statistics.")
    print("      This may take several minutes...")
    print()
    
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    
    # Focus on default sequence (root directory) first
    print(f"\n{'=' * 80}")
    print("Default Sequence (Root Directory)")
    print(f"{'=' * 80}\n")
    
    for strategy_name in ['strategy1', 'strategy2']:
        print(f"Processing {strategy_name}...")
        
        # Extract actual utilization
        actual_utils = extract_actual_util_for_strategy(
            result_dir_base, strategy_name, sequence_name=None, 
            config=config, num_steps=10, num_commodities=4
        )
        
        # Update stats CSV file
        stats_file = os.path.join(result_dir_base, f'{strategy_name}_stats.csv')
        
        if os.path.exists(stats_file):
            stats_df = pd.read_csv(stats_file)
            
            # Add actual utilization column
            stats_df['max_link_utilization_actual'] = actual_utils
            
            # Save updated stats
            stats_df.to_csv(stats_file, index=False)
            print(f"  ✓ Updated {stats_file}")
            
            # Print summary
            if stats_df['max_link_utilization_actual'].notna().any():
                avg_actual = stats_df['max_link_utilization_actual'].mean()
                avg_theoretical = stats_df['max_link_utilization'].mean()
                print(f"  Average theoretical utilization: {avg_theoretical:.4f}%")
                print(f"  Average actual utilization: {avg_actual:.4f}%")
                print(f"  Difference: {avg_actual - avg_theoretical:.4f}%")
        else:
            print(f"  ⚠️  Stats file not found: {stats_file}")
        
        print()
    
    # For Strategy 3, check if stats files exist in subdirectories
    sequences = ['random_perturbation', 'increasing_sequence', 'hybrid_sequence']
    
    for sequence_name in sequences:
        strategy3_dir = os.path.join(result_dir_base, sequence_name, 'strategy3')
        stats_file = os.path.join(strategy3_dir, 'strategy3_stats.csv')
        
        if os.path.exists(stats_file):
            print(f"\n{'=' * 80}")
            print(f"Strategy 3: {sequence_name}")
            print(f"{'=' * 80}\n")
            
            print(f"Processing strategy3 for {sequence_name}...")
            
            # Extract actual utilization
            actual_utils = extract_actual_util_for_strategy(
                result_dir_base, 'strategy3', sequence_name=sequence_name,
                config=config, num_steps=10, num_commodities=4
            )
            
            # Update stats CSV file
            if os.path.exists(stats_file):
                stats_df = pd.read_csv(stats_file)
                stats_df['max_link_utilization_actual'] = actual_utils
                stats_df.to_csv(stats_file, index=False)
                print(f"  ✓ Updated {stats_file}")
                
                # Print summary
                if stats_df['max_link_utilization_actual'].notna().any():
                    avg_actual = stats_df['max_link_utilization_actual'].mean()
                    avg_theoretical = stats_df['max_link_utilization'].mean()
                    print(f"  Average theoretical utilization: {avg_theoretical:.4f}%")
                    print(f"  Average actual utilization: {avg_actual:.4f}%")
                    print(f"  Difference: {avg_actual - avg_theoretical:.4f}%")
            
            print()
    
    print("=" * 80)
    print("Extraction completed!")
    print("=" * 80)


if __name__ == '__main__':
    main()

