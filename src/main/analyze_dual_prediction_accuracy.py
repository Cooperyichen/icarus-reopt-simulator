#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze dual variable prediction accuracy.

Compare theoretical max link utilization with predicted values
based on dual variable linear extrapolation.
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


def extract_dual_variables_from_optimization(config, arrival_rates):
    """Extract dual variables by running optimization."""
    step_config = config.copy()
    step_config['fixed_demand'] = config['fixed_demand'].copy()
    step_config['fixed_demand']['arrival_rate'] = arrival_rates
    
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=step_config, width=width, height=height)
    
    num_commodities = len(arrival_rates)
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    
    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']
    
    result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    dual_vars = {}
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
    
    return dual_vars


def analyze_dual_prediction_accuracy():
    """
    Analyze dual variable prediction accuracy.
    
    Returns:
        pandas.DataFrame: Comparison data with theoretical and predicted values
    """
    print("=" * 80)
    print("Dual Variable Prediction Accuracy Analysis")
    print("=" * 80)
    print()
    
    # Configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Load experiment results
    result_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation', 
                             'strategy_dual_validation')
    stats_file = os.path.join(result_dir, 'experiment_stats.csv')
    
    if not os.path.exists(stats_file):
        print(f"✗ Experiment stats file not found: {stats_file}")
        print("Please run run_dual_validation_experiment.py first")
        return None
    
    stats_df = pd.read_csv(stats_file)
    
    # Load sequence to get arrival rates
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_dual_validation.csv')
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    
    # Step 1 arrival rates
    step1_arrival_rates = sequence_df.iloc[0].values.tolist()
    step1_demand_2 = step1_arrival_rates[2]  # 300.0
    
    # Extract dual variable for commodity 2 from Step 1
    print("Extracting dual variable from Step 1...")
    dual_variables = extract_dual_variables_from_optimization(config, step1_arrival_rates)
    lambda_2 = dual_variables.get(2, None)
    
    if lambda_2 is None:
        print("✗ Dual variable for commodity 2 not found")
        return None
    
    print(f"✓ Dual variable for commodity 2 (λ_2): {lambda_2:.6e}")
    print()
    
    # Step 1 theoretical utilization
    step1_util = stats_df[stats_df['step_id'] == 1]['max_link_utilization'].iloc[0]
    print(f"Step 1 theoretical max link utilization: {step1_util:.4f}%")
    print()
    
    # Calculate predictions for all steps
    comparison_data = []
    
    for idx, row in stats_df.iterrows():
        step_id = int(row['step_id'])
        theoretical_util = row['max_link_utilization']
        
        # Get current arrival rates
        arrival_rates_str = row['arrival_rates']
        if isinstance(arrival_rates_str, str):
            arrival_rates = [float(x.strip()) for x in arrival_rates_str.strip('[]').split(',')]
        else:
            arrival_rates = sequence_df.iloc[step_id - 1].values.tolist()
        
        current_demand_2 = arrival_rates[2]
        demand_change_2 = current_demand_2 - step1_demand_2
        
        # Linear extrapolation: predicted_util = step1_util + λ_2 × (d_2_current - d_2_step1)
        predicted_util = step1_util + lambda_2 * demand_change_2
        
        # Calculate errors
        absolute_error = abs(theoretical_util - predicted_util)
        relative_error = (absolute_error / theoretical_util * 100) if theoretical_util > 0 else 0
        
        comparison_data.append({
            'step_id': step_id,
            'commodity_2_demand': current_demand_2,
            'demand_change': demand_change_2,
            'theoretical_util': theoretical_util,
            'predicted_util': predicted_util,
            'absolute_error': absolute_error,
            'relative_error': relative_error
        })
        
        print(f"Step {step_id}:")
        print(f"  Commodity 2 demand: {current_demand_2:.1f} (change: {demand_change_2:+.1f})")
        print(f"  Theoretical util: {theoretical_util:.4f}%")
        print(f"  Predicted util: {predicted_util:.4f}%")
        print(f"  Absolute error: {absolute_error:.4f}%")
        print(f"  Relative error: {relative_error:.4f}%")
        print()
    
    # Create comparison DataFrame
    comparison_df = pd.DataFrame(comparison_data)
    
    # Save comparison data
    output_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation', 
                             'strategy_dual_validation')
    comparison_file = os.path.join(output_dir, 'dual_prediction_comparison.csv')
    comparison_df.to_csv(comparison_file, index=False)
    print(f"✓ Comparison data saved to: {comparison_file}")
    
    # Calculate summary statistics
    print("=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    print()
    print(f"Mean absolute error: {comparison_df['absolute_error'].mean():.4f}%")
    print(f"Max absolute error: {comparison_df['absolute_error'].max():.4f}%")
    print(f"Min absolute error: {comparison_df['absolute_error'].min():.4f}%")
    print(f"Std absolute error: {comparison_df['absolute_error'].std():.4f}%")
    print()
    print(f"Mean relative error: {comparison_df['relative_error'].mean():.4f}%")
    print(f"Max relative error: {comparison_df['relative_error'].max():.4f}%")
    print()
    
    # Save summary
    summary_data = {
        'lambda_2': lambda_2,
        'step1_util': step1_util,
        'step1_demand_2': step1_demand_2,
        'mean_absolute_error': comparison_df['absolute_error'].mean(),
        'max_absolute_error': comparison_df['absolute_error'].max(),
        'mean_relative_error': comparison_df['relative_error'].mean(),
        'max_relative_error': comparison_df['relative_error'].max()
    }
    summary_df = pd.DataFrame([summary_data])
    summary_file = os.path.join(output_dir, 'dual_validation_summary.csv')
    summary_df.to_csv(summary_file, index=False)
    print(f"✓ Summary saved to: {summary_file}")
    
    return comparison_df


def main():
    """Main function"""
    comparison_df = analyze_dual_prediction_accuracy()
    if comparison_df is not None:
        print()
        print("=" * 80)
        print("✓ Analysis complete!")
        print("=" * 80)


if __name__ == '__main__':
    main()

