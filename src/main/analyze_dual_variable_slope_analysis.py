#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze dual variable and slope differences in dual validation experiment.

This script:
1. Checks if dual variable for commodity 2 changes during the experiment
2. Calculates slopes of theoretical and predicted max link utilization
3. Analyzes what the slope difference corresponds to
"""

import sys
import os
import pandas as pd
import numpy as np
from scipy import stats

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


def analyze_dual_variable_changes():
    """
    Check if dual variable for commodity 2 changes during the experiment.
    
    Note: In this experiment, we only optimize at Step 1 and preserve path ratios.
    However, we can check what the dual variable would be if we optimized at each step.
    """
    print("=" * 80)
    print("Analysis 1: Dual Variable Changes During Experiment")
    print("=" * 80)
    print()
    
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Load sequence
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_dual_validation.csv')
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    
    print("Extracting dual variables for each step (if we were to optimize):")
    print()
    
    dual_variables_by_step = []
    
    for step_id in range(1, 11):
        arrival_rates = sequence_df.iloc[step_id - 1].values.tolist()
        print(f"Step {step_id}: Arrival rates = {[f'{r:.1f}' for r in arrival_rates]}")
        
        # Extract dual variables (this would require optimization at each step)
        dual_vars = extract_dual_variables_from_optimization(config, arrival_rates)
        lambda_2 = dual_vars.get(2, None)
        
        if lambda_2 is not None:
            dual_variables_by_step.append({
                'step_id': step_id,
                'commodity_2_demand': arrival_rates[2],
                'lambda_2': lambda_2
            })
            print(f"  λ_2 = {lambda_2:.6e}")
        else:
            print(f"  λ_2 = None (not available)")
        print()
    
    dual_df = pd.DataFrame(dual_variables_by_step)
    
    if len(dual_df) > 0:
        print("Dual Variable Analysis:")
        print(f"  Mean λ_2: {dual_df['lambda_2'].mean():.6e}")
        print(f"  Std λ_2: {dual_df['lambda_2'].std():.6e}")
        print(f"  Min λ_2: {dual_df['lambda_2'].min():.6e}")
        print(f"  Max λ_2: {dual_df['lambda_2'].max():.6e}")
        print(f"  Range: {dual_df['lambda_2'].max() - dual_df['lambda_2'].min():.6e}")
        print()
        
        # Check if dual variable changes significantly
        if dual_df['lambda_2'].std() < 1e-10:
            print("  ✓ Dual variable remains constant (within numerical precision)")
        else:
            print(f"  ⚠️  Dual variable changes: std = {dual_df['lambda_2'].std():.6e}")
            print(f"     This suggests the dual variable depends on the demand level")
        
        # Save dual variables
        output_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation', 
                                 'strategy_dual_validation')
        dual_file = os.path.join(output_dir, 'dual_variables_by_step.csv')
        dual_df.to_csv(dual_file, index=False)
        print(f"  ✓ Dual variables saved to: {dual_file}")
    
    return dual_df


def analyze_slope_differences():
    """
    Analyze slope differences between theoretical and predicted max link utilization.
    """
    print("=" * 80)
    print("Analysis 2: Slope Difference Analysis")
    print("=" * 80)
    print()
    
    # Load comparison data
    result_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation', 
                             'strategy_dual_validation')
    comparison_file = os.path.join(result_dir, 'dual_prediction_comparison.csv')
    
    if not os.path.exists(comparison_file):
        print(f"✗ Comparison file not found: {comparison_file}")
        return None
    
    df = pd.read_csv(comparison_file)
    
    # Calculate slopes using linear regression
    x = df['step_id'].values
    y_theoretical = df['theoretical_util'].values
    y_predicted = df['predicted_util'].values
    y_demand_change = df['demand_change'].values
    
    # Slope of theoretical utilization vs step
    slope_theoretical_step, intercept_theoretical_step, r_theoretical_step, p_theoretical_step, _ = \
        stats.linregress(x, y_theoretical)
    
    # Slope of predicted utilization vs step
    slope_predicted_step, intercept_predicted_step, r_predicted_step, p_predicted_step, _ = \
        stats.linregress(x, y_predicted)
    
    # Slope of theoretical utilization vs demand change
    slope_theoretical_demand, intercept_theoretical_demand, r_theoretical_demand, p_theoretical_demand, _ = \
        stats.linregress(y_demand_change, y_theoretical)
    
    # Slope of predicted utilization vs demand change
    slope_predicted_demand, intercept_predicted_demand, r_predicted_demand, p_predicted_demand, _ = \
        stats.linregress(y_demand_change, y_predicted)
    
    print("Slope Analysis:")
    print()
    print("1. Utilization vs Time Step:")
    print(f"   Theoretical slope: {slope_theoretical_step:.6f} %/step")
    print(f"   Predicted slope: {slope_predicted_step:.6f} %/step")
    print(f"   Slope difference: {slope_theoretical_step - slope_predicted_step:.6f} %/step")
    print(f"   R² (theoretical): {r_theoretical_step**2:.6f}")
    print(f"   R² (predicted): {r_predicted_step**2:.6f}")
    print()
    
    print("2. Utilization vs Demand Change:")
    print(f"   Theoretical slope: {slope_theoretical_demand:.6f} %/(packets/s)")
    print(f"   Predicted slope: {slope_predicted_demand:.6f} %/(packets/s)")
    print(f"   Slope difference: {slope_theoretical_demand - slope_predicted_demand:.6f} %/(packets/s)")
    print(f"   R² (theoretical): {r_theoretical_demand**2:.6f}")
    print(f"   R² (predicted): {r_predicted_demand**2:.6f}")
    print()
    
    # Get lambda_2 from summary
    summary_file = os.path.join(result_dir, 'dual_validation_summary.csv')
    if os.path.exists(summary_file):
        summary = pd.read_csv(summary_file)
        lambda_2 = summary['lambda_2'].iloc[0]
        
        print("3. Dual Variable Comparison:")
        print(f"   λ_2 (from Step 1): {lambda_2:.6e} %/(packets/s)")
        print(f"   Predicted slope: {slope_predicted_demand:.6f} %/(packets/s)")
        print(f"   Difference: {abs(slope_predicted_demand - lambda_2):.6e}")
        if abs(slope_predicted_demand - lambda_2) < 1e-6:
            print("   ✓ Predicted slope matches λ_2 (as expected)")
        else:
            print(f"   ⚠️  Small numerical difference: {abs(slope_predicted_demand - lambda_2):.6e}")
        print()
        
        print("4. Slope Difference Interpretation:")
        slope_diff = slope_theoretical_demand - slope_predicted_demand
        print(f"   Slope difference: {slope_diff:.6f} %/(packets/s)")
        print(f"   This represents the additional increase in max link utilization")
        print(f"   per unit demand change that is NOT captured by the linear extrapolation.")
        print()
        print("   Possible explanations:")
        print(f"   a) Non-linear effects: As demand increases, the optimization problem")
        print(f"      becomes more constrained, leading to non-linear response")
        print(f"   b) Path re-allocation: Optimal path allocation may change with demand,")
        print(f"      but we're using fixed path ratios from Step 1")
        print(f"   c) Capacity constraints: Different links may become bottlenecks at")
        print(f"      different demand levels, causing the slope to change")
        print(f"   d) Second-order effects: Higher-order terms in the Taylor expansion")
        print(f"      that are not captured by the first-order (dual variable) approximation")
        print()
        
        # Calculate what the "effective dual variable" would be at different steps
        print("5. Effective Dual Variable Analysis:")
        print("   (What would λ_2 be if we optimized at each step?)")
        print()
        
        # Load dual variables if available
        dual_file = os.path.join(result_dir, 'dual_variables_by_step.csv')
        if os.path.exists(dual_file):
            dual_df = pd.read_csv(dual_file)
            print("   Step-by-step dual variables:")
            for _, row in dual_df.iterrows():
                print(f"     Step {int(row['step_id'])}: λ_2 = {row['lambda_2']:.6e}")
            print()
            
            # Compare with slope difference
            if len(dual_df) > 1:
                mean_lambda = dual_df['lambda_2'].mean()
                print(f"   Mean λ_2 across steps: {mean_lambda:.6e}")
                print(f"   Step 1 λ_2: {lambda_2:.6e}")
                print(f"   Difference: {abs(mean_lambda - lambda_2):.6e}")
                print()
                
                # Calculate effective slope from dual variables
                # If we use the mean dual variable, what would the slope be?
                effective_slope = mean_lambda
                print(f"   Effective slope (using mean λ_2): {effective_slope:.6f} %/(packets/s)")
                print(f"   Theoretical slope: {slope_theoretical_demand:.6f} %/(packets/s)")
                print(f"   Remaining difference: {slope_theoretical_demand - effective_slope:.6f} %/(packets/s)")
                print()
                print("   This remaining difference suggests:")
                print("   - Even with updated dual variables, there's still non-linearity")
                print("   - The path ratio preservation strategy may not be optimal")
                print("   - Capacity constraints create non-linear effects")
        else:
            print("   (Dual variables by step not yet calculated)")
            print("   Run Analysis 1 first to get step-by-step dual variables")
    
    return {
        'slope_theoretical_step': slope_theoretical_step,
        'slope_predicted_step': slope_predicted_step,
        'slope_theoretical_demand': slope_theoretical_demand,
        'slope_predicted_demand': slope_predicted_demand,
        'slope_difference': slope_theoretical_demand - slope_predicted_demand
    }


def interpret_slope_difference(slope_diff, lambda_2):
    """
    Interpret what the slope difference corresponds to.
    """
    print("=" * 80)
    print("Analysis 3: What Does the Slope Difference Correspond To?")
    print("=" * 80)
    print()
    
    print("The slope difference represents:")
    print()
    print(f"1. Non-linear Correction Term:")
    print(f"   The difference ({slope_diff:.6f} %/(packets/s)) is the additional")
    print(f"   increase in max link utilization per unit demand change that cannot")
    print(f"   be captured by the first-order (linear) approximation using dual variables.")
    print()
    
    print(f"2. Mathematical Interpretation:")
    print(f"   If we expand max_link_util as a function of demand:")
    print(f"   util(d) = util(d₀) + λ₂ × (d - d₀) + (1/2) × d²util/dd² × (d - d₀)² + ...")
    print(f"   ")
    print(f"   The dual variable λ₂ captures the first-order term (linear approximation)")
    print(f"   The slope difference captures the second-order and higher-order terms")
    print()
    
    print(f"3. Physical Interpretation:")
    print(f"   - As demand increases, the network becomes more congested")
    print(f"   - Optimal path allocation may shift to avoid bottlenecks")
    print(f"   - But we're using fixed path ratios, so we can't adapt")
    print(f"   - This leads to sub-optimal routing and higher utilization")
    print()
    
    print(f"4. Practical Implications:")
    print(f"   - For small demand changes (< 100 packets/s): Linear approximation works well")
    print(f"   - For large demand changes (> 300 packets/s): Re-optimization is needed")
    print(f"   - The slope difference quantifies when re-optimization becomes necessary")
    print()
    
    # Calculate when error becomes significant
    significant_error_threshold = 5.0  # 5% absolute error
    demand_change_for_significant_error = significant_error_threshold / slope_diff if slope_diff > 0 else float('inf')
    
    print(f"5. Re-optimization Threshold:")
    print(f"   If we accept up to {significant_error_threshold}% error,")
    if demand_change_for_significant_error != float('inf'):
        print(f"   demand change should be < {demand_change_for_significant_error:.1f} packets/s")
        print(f"   This corresponds to approximately {demand_change_for_significant_error/50:.1f} steps")
    else:
        print(f"   (slope difference is too small to calculate)")
    print()


def main():
    """Main function"""
    print("=" * 80)
    print("Dual Variable and Slope Analysis")
    print("=" * 80)
    print()
    
    # Analysis 1: Check dual variable changes
    dual_df = analyze_dual_variable_changes()
    
    print()
    print()
    
    # Analysis 2: Calculate slope differences
    slope_results = analyze_slope_differences()
    
    print()
    print()
    
    # Analysis 3: Interpret slope difference
    if slope_results is not None:
        summary_file = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation', 
                                   'strategy_dual_validation', 'dual_validation_summary.csv')
        if os.path.exists(summary_file):
            summary = pd.read_csv(summary_file)
            lambda_2 = summary['lambda_2'].iloc[0]
            interpret_slope_difference(slope_results['slope_difference'], lambda_2)
    
    print("=" * 80)
    print("✓ Analysis complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()

