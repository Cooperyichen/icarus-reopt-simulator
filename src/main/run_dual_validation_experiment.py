#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run dual variable validation experiment.

This experiment:
1. Uses the dual validation sequence (commodity 2 increases, others constant)
2. Optimizes only at Step 1 (reuses random_perturbation/strategy1/step_1 result)
3. Applies Step 1 path ratios to subsequent steps
4. Calculates theoretical max link utilization for each step
5. Extracts dual variables from Step 1
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
from main.multi_step_comparison_experiment import (
    extract_path_ratios_from_csv,
    apply_path_ratios_to_demand,
    calculate_max_link_utilization,
    calculate_step_statistics,
    save_to_csv
)
import main.main as main_module


def extract_dual_variables_from_optimization(config, arrival_rates):
    """
    Extract dual variables by running optimization.
    
    Args:
        config: Configuration dictionary
        arrival_rates: List of arrival rates
        
    Returns:
        dict: Dual variables {commodity_id: dual_value}
    """
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


def run_dual_validation_experiment():
    """
    Run the dual variable validation experiment.
    
    Returns:
        tuple: (experiment_stats, dual_variables, step1_util)
    """
    print("=" * 80)
    print("Dual Variable Validation Experiment")
    print("=" * 80)
    print()
    
    # Configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Load sequence
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_dual_validation.csv')
    if not os.path.exists(sequence_file):
        print(f"✗ Sequence file not found: {sequence_file}")
        print("Please run generate_dual_validation_sequence.py first")
        return None
    
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    num_steps, num_commodities = sequence.shape
    
    # Output directory
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation')
    strategy_dir = os.path.join(result_dir_base, 'strategy_dual_validation')
    os.makedirs(strategy_dir, exist_ok=True)
    
    # Create topology
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)
    
    # Step 1: Check if we can reuse existing result
    step1_arrival_rates = sequence[0].tolist()
    step1_result_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 
                                    'random_perturbation', 'strategy1', 'step_1')
    step1_mcfp_file = os.path.join(step1_result_dir, 'mcfp_results_flows_4_commodities.csv')
    
    baseline_ratios = None
    baseline_mcfp_df = None
    step1_util = None
    dual_variables = None
    
    if os.path.exists(step1_mcfp_file):
        print("Step 1: Reusing existing optimization result from random_perturbation/strategy1/step_1")
        baseline_mcfp_df = pd.read_csv(step1_mcfp_file)
        baseline_ratios = extract_path_ratios_from_csv(step1_mcfp_file)
        
        # Calculate Step 1 utilization
        step1_config = config.copy()
        step1_config['fixed_demand'] = config['fixed_demand'].copy()
        step1_config['fixed_demand']['arrival_rate'] = step1_arrival_rates
        step1_util = calculate_max_link_utilization(baseline_mcfp_df, step1_config)
        
        # Extract dual variables (need to re-run optimization to get dual variables)
        print("  Extracting dual variables...")
        dual_variables = extract_dual_variables_from_optimization(config, step1_arrival_rates)
        print(f"  ✓ Dual variables extracted: {dual_variables}")
        
        # Copy Step 1 result to our experiment directory
        experiment_step1_dir = os.path.join(strategy_dir, 'step_1')
        os.makedirs(experiment_step1_dir, exist_ok=True)
        import shutil
        shutil.copy(step1_mcfp_file, os.path.join(experiment_step1_dir, 'mcfp_results_flows_4_commodities.csv'))
    else:
        print("Step 1: Running optimization (existing result not found)")
        # Run optimization for Step 1
        step1_config = config.copy()
        step1_config['fixed_demand'] = config['fixed_demand'].copy()
        step1_config['fixed_demand']['arrival_rate'] = step1_arrival_rates
        step1_config['simulation'] = config['simulation'].copy()
        step1_config['simulation']['num_steps'] = 1
        
        regen_obp.scenario_config = step1_config
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
        
        optimizer = MultiCommodityOptimizer(step1_config, regen_obp.graph, regen_obp.interlinks)
        objective_type = step1_config['optimization']['objective_func']
        mode = step1_config['simulation']['failure_strategy']
        
        updated_demand_matrix = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
        
        # Extract dual variables
        if hasattr(updated_demand_matrix, 'attrs') and 'dual_variables' in updated_demand_matrix.attrs:
            dual_variables = updated_demand_matrix.attrs['dual_variables']
        
        # Save Step 1 result
        experiment_step1_dir = os.path.join(strategy_dir, 'step_1')
        os.makedirs(experiment_step1_dir, exist_ok=True)
        step1_mcfp_file = os.path.join(experiment_step1_dir, 'mcfp_results_flows_4_commodities.csv')
        save_to_csv(updated_demand_matrix, filename=step1_mcfp_file)
        
        baseline_mcfp_df = pd.read_csv(step1_mcfp_file)
        baseline_ratios = extract_path_ratios_from_csv(step1_mcfp_file)
        step1_util = calculate_max_link_utilization(baseline_mcfp_df, step1_config)
    
    print(f"  Step 1 max link utilization: {step1_util:.4f}%")
    print(f"  Dual variable for commodity 2: {dual_variables.get(2, None)}")
    print()
    
    # Steps 2-10: Apply preserved path ratios
    experiment_stats = []
    
    for step_id in range(2, num_steps + 1):
        print(f"Step {step_id}/{num_steps}:")
        arrival_rates = sequence[step_id - 1].tolist()
        print(f"  Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
        
        result_dir = os.path.join(strategy_dir, f'step_{step_id}')
        os.makedirs(result_dir, exist_ok=True)
        
        # Update config
        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        step_config['fixed_demand']['arrival_rate'] = arrival_rates
        step_config['simulation'] = config['simulation'].copy()
        step_config['simulation']['num_steps'] = 1
        
        # Apply preserved path ratios
        updated_demand_matrix = apply_path_ratios_to_demand(
            baseline_ratios, arrival_rates, baseline_mcfp_df
        )
        
        # Save MCFP results
        mcfp_file = os.path.join(result_dir, 'mcfp_results_flows_4_commodities.csv')
        save_to_csv(updated_demand_matrix, filename=mcfp_file)
        
        # Calculate theoretical max link utilization
        mcfp_df = pd.read_csv(mcfp_file)
        max_link_util_theoretical = calculate_max_link_utilization(mcfp_df, step_config)
        
        # Run simulation
        np.random.seed(42)
        all_flows, switches, blocked_flows = main_module.run_simulation_scenario(
            step_config, result_dir, 0, precomputed_demand_matrix=updated_demand_matrix
        )
        
        # Calculate statistics
        flow_stats = calculate_step_statistics(all_flows)
        max_link_util_actual = calculate_max_link_utilization(mcfp_df, step_config)
        
        step_stat = {
            'step_id': step_id,
            'arrival_rates': arrival_rates,
            'max_link_utilization': max_link_util_theoretical,
            'max_link_utilization_actual': max_link_util_actual,
            'pli': flow_stats['pli'],
            'avg_delay': flow_stats['avg_delay']
        }
        experiment_stats.append(step_stat)
        
        print(f"  Max link utilization: {max_link_util_theoretical:.4f}%")
    
    # Add Step 1 to stats
    step1_stat = {
        'step_id': 1,
        'arrival_rates': step1_arrival_rates,
        'max_link_utilization': step1_util,
        'max_link_utilization_actual': step1_util,
        'pli': None,  # Will be calculated if needed
        'avg_delay': None
    }
    experiment_stats.insert(0, step1_stat)
    
    # Save statistics
    stats_df = pd.DataFrame(experiment_stats)
    stats_file = os.path.join(strategy_dir, 'experiment_stats.csv')
    stats_df['arrival_rates'] = stats_df['arrival_rates'].apply(lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x)
    stats_df.to_csv(stats_file, index=False)
    
    print()
    print("=" * 80)
    print("✓ Experiment completed!")
    print("=" * 80)
    print(f"Results saved to: {strategy_dir}")
    
    return experiment_stats, dual_variables, step1_util


def main():
    """Main function"""
    result = run_dual_validation_experiment()
    if result is None:
        return
    
    experiment_stats, dual_variables, step1_util = result
    
    print()
    print("Summary:")
    print(f"  Step 1 max link utilization: {step1_util:.4f}%")
    print(f"  Dual variable for commodity 2: {dual_variables.get(2, None)}")
    print(f"  Total steps: {len(experiment_stats)}")


if __name__ == '__main__':
    main()

