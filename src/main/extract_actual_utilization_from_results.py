#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract actual maximum link utilization from existing simulation results.

This script loads switches from saved simulation results and calculates
actual link utilization from port statistics.
"""

import sys
import os
import pandas as pd
import numpy as np
import pickle

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import (
    calculate_actual_max_link_utilization_from_simulation
)
from modem.switch import SimplePacketSwitch, FairPacketSwitch


def extract_actual_utilization_for_strategy(result_dir_base, strategy_name, sequence_name, num_steps=10, num_commodities=4):
    """
    Extract actual maximum link utilization from saved simulation results.
    
    Args:
        result_dir_base: Base directory for results
        strategy_name: 'strategy1', 'strategy2', or 'strategy3'
        sequence_name: Name of the sequence (e.g., 'random_perturbation')
        num_steps: Number of steps
        num_commodities: Number of commodities
        
    Returns:
        list: List of dictionaries with step_id and max_link_utilization_actual
    """
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Check if sequence_name is provided (subdirectory structure)
    if sequence_name:
        strategy_dir = os.path.join(result_dir_base, sequence_name, strategy_name)
    else:
        strategy_dir = os.path.join(result_dir_base, strategy_name)
    
    actual_utils = []
    
    for step_id in range(1, num_steps + 1):
        step_dir = os.path.join(strategy_dir, f'step_{step_id}')
        
        # Try to load switches from pickle file (if saved)
        switches_file = os.path.join(step_dir, 'switches.pkl')
        
        if os.path.exists(switches_file):
            try:
                with open(switches_file, 'rb') as f:
                    switches = pickle.load(f)
                
                # Calculate actual utilization
                max_util_actual = calculate_actual_max_link_utilization_from_simulation(switches, config)
                
                actual_utils.append({
                    'step_id': step_id,
                    'max_link_utilization_actual': max_util_actual
                })
                
                print(f"Step {step_id}: {max_util_actual:.4f}%")
            except Exception as e:
                print(f"Error loading switches for Step {step_id}: {e}")
                actual_utils.append({
                    'step_id': step_id,
                    'max_link_utilization_actual': None
                })
        else:
            print(f"Warning: switches.pkl not found for {strategy_name} Step {step_id}")
            actual_utils.append({
                'step_id': step_id,
                'max_link_utilization_actual': None
            })
    
    return actual_utils


def re_run_simulation_for_actual_utilization(result_dir_base, strategy_name, sequence_name, config, num_steps=10, num_commodities=4):
    """
    Re-run simulation briefly to get switches object, then calculate actual utilization.
    
    This is necessary if switches were not saved to pickle files.
    """
    import main.main as main_module
    
    # Check if sequence_name is provided
    if sequence_name:
        strategy_dir = os.path.join(result_dir_base, sequence_name, strategy_name)
    else:
        strategy_dir = os.path.join(result_dir_base, strategy_name)
    
    actual_utils = []
    
    for step_id in range(1, num_steps + 1):
        step_dir = os.path.join(strategy_dir, f'step_{step_id}')
        
        # Load step config (may need to reconstruct from arrival rates)
        # For now, use base config
        step_config = config.copy()
        
        # Load arrival rates from stats file if available
        stats_file = os.path.join(strategy_dir, f'{strategy_name}_stats.csv')
        if os.path.exists(stats_file):
            stats_df = pd.read_csv(stats_file)
            if step_id <= len(stats_df):
                arrival_rates_str = stats_df.iloc[step_id - 1]['arrival_rates']
                arrival_rates = eval(arrival_rates_str) if isinstance(arrival_rates_str, str) else arrival_rates_str
                step_config['fixed_demand'] = config['fixed_demand'].copy()
                step_config['fixed_demand']['arrival_rate'] = arrival_rates
        
        # Load precomputed demand matrix
        mcfp_file = os.path.join(step_dir, f'mcfp_results_flows_{num_commodities}_commodities.csv')
        if not os.path.exists(mcfp_file):
            print(f"Warning: MCFP file not found for Step {step_id}")
            actual_utils.append({
                'step_id': step_id,
                'max_link_utilization_actual': None
            })
            continue
        
        precomputed_demand_matrix = pd.read_csv(mcfp_file)
        
        # Re-run simulation to get switches
        np.random.seed(42)  # Same seed for reproducibility
        try:
            all_flows, switches, blocked_flows = main_module.run_simulation_scenario(
                step_config, step_dir, 0, precomputed_demand_matrix=precomputed_demand_matrix
            )
            
            # Calculate actual utilization
            max_util_actual = calculate_actual_max_link_utilization_from_simulation(switches, step_config)
            
            actual_utils.append({
                'step_id': step_id,
                'max_link_utilization_actual': max_util_actual
            })
            
            print(f"Step {step_id}: {max_util_actual:.4f}%")
        except Exception as e:
            print(f"Error running simulation for Step {step_id}: {e}")
            actual_utils.append({
                'step_id': step_id,
                'max_link_utilization_actual': None
            })
    
    return actual_utils


def main():
    """Main function to extract actual utilization for all strategies."""
    
    print("=" * 80)
    print("Extracting Actual Maximum Link Utilization from Simulation Results")
    print("=" * 80)
    print()
    
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    
    sequences = [
        ('random_perturbation', 'Random Perturbation'),
        ('increasing_sequence', 'Increasing Sequence'),
        ('hybrid_sequence', 'Hybrid Sequence'),
        (None, 'Default Sequence')  # Root directory
    ]
    
    for sequence_name, seq_display in sequences:
        print(f"\n{'=' * 80}")
        print(f"Sequence: {seq_display}")
        print(f"{'=' * 80}\n")
        
        for strategy_name in ['strategy1', 'strategy2', 'strategy3']:
            print(f"Processing {strategy_name}...")
            
            # Try to extract from pickle first
            actual_utils = extract_actual_utilization_for_strategy(
                result_dir_base, strategy_name, sequence_name, num_steps=10, num_commodities=4
            )
            
            # If pickle failed, re-run simulation
            if any(util.get('max_link_utilization_actual') is None for util in actual_utils):
                print(f"  Re-running simulation for {strategy_name}...")
                actual_utils = re_run_simulation_for_actual_utilization(
                    result_dir_base, strategy_name, sequence_name, config, num_steps=10, num_commodities=4
                )
            
            # Update stats CSV file
            if sequence_name:
                stats_file = os.path.join(result_dir_base, sequence_name, strategy_name, f'{strategy_name}_stats.csv')
            else:
                stats_file = os.path.join(result_dir_base, f'{strategy_name}_stats.csv')
            
            if os.path.exists(stats_file):
                stats_df = pd.read_csv(stats_file)
                
                # Add actual utilization column
                actual_util_dict = {util['step_id']: util['max_link_utilization_actual'] 
                                   for util in actual_utils if util['max_link_utilization_actual'] is not None}
                
                stats_df['max_link_utilization_actual'] = stats_df['step_id'].map(actual_util_dict)
                
                # Save updated stats
                stats_df.to_csv(stats_file, index=False)
                print(f"  ✓ Updated {stats_file}")
                
                # Print summary
                if stats_df['max_link_utilization_actual'].notna().any():
                    avg_actual = stats_df['max_link_utilization_actual'].mean()
                    print(f"  Average actual utilization: {avg_actual:.4f}%")
            else:
                print(f"  ⚠️  Stats file not found: {stats_file}")
        
        print()


if __name__ == '__main__':
    main()

