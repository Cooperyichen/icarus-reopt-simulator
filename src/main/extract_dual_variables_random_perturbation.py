#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract dual variables for demand constraints from random_perturbation sequence.

This script re-runs the optimization for each step to extract dual variables,
or reads from saved MCFP results if available.
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
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer


def extract_dual_variables_from_step(step_dir, config, arrival_rates):
    """
    Extract dual variables by re-running optimization for a specific step.
    
    Args:
        step_dir: Directory path for the step (for reference)
        config: Configuration dictionary
        arrival_rates: List of arrival rates for the step
        
    Returns:
        dict: Dual variables {commodity_id: dual_value}
    """
    # Update config with arrival rates
    step_config = config.copy()
    step_config['fixed_demand'] = config['fixed_demand'].copy()
    step_config['fixed_demand']['arrival_rate'] = arrival_rates
    
    # Create topology
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=step_config, width=width, height=height)
    
    # Generate demand matrix
    num_commodities = len(arrival_rates)
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    
    # Run optimization
    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']
    
    result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    # Extract dual variables
    dual_vars = {}
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
    else:
        print(f"  ⚠️  Dual variables not found in result")
    
    return dual_vars


def extract_dual_variables_for_strategy(sequence_name, strategy_name, config_file, result_base_dir):
    """
    Extract dual variables for all steps of a strategy.
    
    Args:
        sequence_name: Name of the sequence (e.g., 'random_perturbation')
        strategy_name: Name of the strategy (e.g., 'strategy1')
        config_file: Path to YAML config file
        result_base_dir: Base directory for results
        
    Returns:
        pd.DataFrame: DataFrame with columns [step_id, commodity_id, dual_value, arrival_rate]
    """
    print(f"\n{'='*80}")
    print(f"Extracting Dual Variables: {sequence_name} / {strategy_name}")
    print(f"{'='*80}")
    
    # Load config
    config = load_yaml_file(config_file)
    
    # Load sequence
    sequence_file = os.path.join(src_dir, 'results', f'arrival_rate_sequence_{sequence_name.replace("_", "") if sequence_name != "random_perturbation" else "random"}.csv')
    if not os.path.exists(sequence_file):
        sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_random.csv')
    
    if not os.path.exists(sequence_file):
        print(f"✗ Sequence file not found: {sequence_file}")
        return None
    
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    num_steps, num_commodities = sequence.shape
    
    print(f"✓ Loaded sequence: {num_steps} steps, {num_commodities} commodities")
    
    # Load stats to get arrival rates for each step
    stats_file = os.path.join(result_base_dir, sequence_name, strategy_name, f'{strategy_name}_stats.csv')
    if not os.path.exists(stats_file):
        print(f"✗ Stats file not found: {stats_file}")
        return None
    
    stats_df = pd.read_csv(stats_file)
    print(f"✓ Loaded stats file: {len(stats_df)} steps")
    
    # Extract dual variables for each step
    all_dual_data = []
    
    for idx, row in stats_df.iterrows():
        step_id = int(row['step_id'])
        arrival_rates_str = row['arrival_rates']
        
        # Parse arrival rates (convert from string if needed)
        if isinstance(arrival_rates_str, str):
            # Remove brackets and split
            arrival_rates = [float(x.strip()) for x in arrival_rates_str.strip('[]').split(',')]
        else:
            arrival_rates = sequence[step_id - 1].tolist()
        
        print(f"\n  Step {step_id}/{num_steps}:")
        print(f"    Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
        
        # Extract dual variables
        step_dir = os.path.join(result_base_dir, sequence_name, strategy_name, f'step_{step_id}')
        dual_vars = extract_dual_variables_from_step(step_dir, config, arrival_rates)
        
        # Store dual variables for each commodity
        for commodity_id in range(num_commodities):
            dual_value = dual_vars.get(commodity_id, None)
            all_dual_data.append({
                'step_id': step_id,
                'commodity_id': commodity_id,
                'dual_value': dual_value,
                'arrival_rate': arrival_rates[commodity_id]
            })
        
        # Print dual variables for this step
        print(f"    Dual variables:")
        for commodity_id in range(num_commodities):
            dual_val = dual_vars.get(commodity_id, None)
            if dual_val is not None:
                print(f"      Commodity {commodity_id}: {dual_val:.6e}")
            else:
                print(f"      Commodity {commodity_id}: None")
    
    # Create DataFrame
    dual_df = pd.DataFrame(all_dual_data)
    
    return dual_df


def main():
    """Main function to extract dual variables for random_perturbation sequence."""
    
    print("=" * 80)
    print("Extract Dual Variables for Random Perturbation Sequence")
    print("=" * 80)
    
    # Configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    sequence_name = 'random_perturbation'
    
    # Strategies that use optimization (have dual variables)
    strategies = ['strategy1', 'strategy4']  # Strategy 3 also optimizes, but globally
    
    all_results = {}
    
    for strategy_name in strategies:
        print(f"\n{'='*80}")
        print(f"Processing Strategy: {strategy_name}")
        print(f"{'='*80}")
        
        dual_df = extract_dual_variables_for_strategy(
            sequence_name, strategy_name, config_file, result_base_dir
        )
        
        if dual_df is not None:
            all_results[strategy_name] = dual_df
            
            # Save to CSV
            output_file = os.path.join(result_base_dir, sequence_name, strategy_name, 
                                     f'dual_variables_{strategy_name}.csv')
            dual_df.to_csv(output_file, index=False)
            print(f"\n✓ Dual variables saved to: {output_file}")
            
            # Print summary
            print(f"\n  Summary:")
            print(f"    Total records: {len(dual_df)}")
            print(f"    Steps: {dual_df['step_id'].nunique()}")
            print(f"    Commodities: {dual_df['commodity_id'].nunique()}")
            
            # Count non-None dual values
            non_none_count = dual_df['dual_value'].notna().sum()
            print(f"    Non-None dual values: {non_none_count}/{len(dual_df)}")
    
    # Create combined output for easy comparison
    if len(all_results) > 1:
        print(f"\n{'='*80}")
        print("Creating Combined Output")
        print(f"{'='*80}")
        
        # Pivot tables for easier comparison
        for strategy_name, dual_df in all_results.items():
            pivot_df = dual_df.pivot(index='step_id', columns='commodity_id', values='dual_value')
            pivot_file = os.path.join(result_base_dir, sequence_name, strategy_name,
                                     f'dual_variables_pivot_{strategy_name}.csv')
            pivot_df.to_csv(pivot_file)
            print(f"  ✓ Pivot table saved: {pivot_file}")
    
    print(f"\n{'='*80}")
    print("✓ Dual Variable Extraction Complete")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()

