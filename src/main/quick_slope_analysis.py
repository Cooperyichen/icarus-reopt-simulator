#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick slope analysis using existing data.
"""

import sys
import os
import pandas as pd
import numpy as np
from scipy import stats

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)


def quick_slope_analysis():
    """Quick analysis of slopes and dual variable."""
    print("=" * 80)
    print("Dual Variable and Slope Analysis")
    print("=" * 80)
    print()
    
    # Load data
    result_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation', 
                             'strategy_dual_validation')
    comparison_file = os.path.join(result_dir, 'dual_prediction_comparison.csv')
    summary_file = os.path.join(result_dir, 'dual_validation_summary.csv')
    
    df = pd.read_csv(comparison_file)
    summary = pd.read_csv(summary_file)
    
    lambda_2 = summary['lambda_2'].iloc[0]
    
    print("1. Dual Variable for Commodity 2:")
    print(f"   λ_2 (from Step 1): {lambda_2:.6e} %/(packets/s)")
    print(f"   Note: In this experiment, we only optimize at Step 1,")
    print(f"         so λ_2 remains constant throughout.")
    print(f"   If we were to optimize at each step, λ_2 might change")
    print(f"   due to different demand levels affecting the optimization problem.")
    print()
    
    # Calculate slopes
    x = df['step_id'].values
    y_theoretical = df['theoretical_util'].values
    y_predicted = df['predicted_util'].values
    demand_change = df['demand_change'].values
    
    # Slope vs step
    slope_theo_step, intercept_theo_step, r_theo_step, _, _ = stats.linregress(x, y_theoretical)
    slope_pred_step, intercept_pred_step, r_pred_step, _, _ = stats.linregress(x, y_predicted)
    
    # Slope vs demand change
    slope_theo_demand, intercept_theo_demand, r_theo_demand, _, _ = stats.linregress(demand_change, y_theoretical)
    slope_pred_demand, intercept_pred_demand, r_pred_demand, _, _ = stats.linregress(demand_change, y_predicted)
    
    print("2. Slope Analysis:")
    print()
    print("   A. Utilization vs Time Step:")
    print(f"      Theoretical slope: {slope_theo_step:.6f} %/step")
    print(f"      Predicted slope: {slope_pred_step:.6f} %/step")
    print(f"      Slope difference: {slope_theo_step - slope_pred_step:.6f} %/step")
    print(f"      R² (theoretical): {r_theo_step**2:.6f}")
    print(f"      R² (predicted): {r_pred_step**2:.6f}")
    print()
    
    print("   B. Utilization vs Demand Change (more meaningful):")
    print(f"      Theoretical slope: {slope_theo_demand:.6f} %/(packets/s)")
    print(f"      Predicted slope: {slope_pred_demand:.6f} %/(packets/s)")
    print(f"      Slope difference: {slope_theo_demand - slope_pred_demand:.6f} %/(packets/s)")
    print(f"      R² (theoretical): {r_theo_demand**2:.6f}")
    print(f"      R² (predicted): {r_pred_demand**2:.6f}")
    print()
    
    print("   C. Verification:")
    print(f"      λ_2 (dual variable): {lambda_2:.6e} %/(packets/s)")
    print(f"      Predicted slope: {slope_pred_demand:.6f} %/(packets/s)")
    print(f"      Difference: {abs(slope_pred_demand - lambda_2):.6e}")
    if abs(slope_pred_demand - lambda_2) < 1e-6:
        print(f"      ✓ Predicted slope matches λ_2 (as expected from linear extrapolation)")
    print()
    
    print("3. What Does the Slope Difference Correspond To?")
    print("=" * 80)
    print()
    
    slope_diff = slope_theo_demand - slope_pred_demand
    
    print(f"   Slope difference: {slope_diff:.6f} %/(packets/s)")
    print()
    print("   This difference represents:")
    print()
    print("   a) Non-linear Effects:")
    print(f"      The additional increase in max link utilization per unit")
    print(f"      demand change that cannot be captured by the first-order")
    print(f"      (linear) approximation using dual variables.")
    print()
    print("   b) Mathematical Interpretation:")
    print(f"      If we expand max_link_util as a function of demand d:")
    print(f"      util(d) = util(d₀) + λ₂ × (d - d₀) + (1/2) × d²util/dd² × (d - d₀)² + ...")
    print(f"      ")
    print(f"      - λ₂ captures the first-order term (linear approximation)")
    print(f"      - The slope difference captures second-order and higher-order terms")
    print()
    print("   c) Physical Interpretation:")
    print(f"      - As commodity 2 demand increases, the network becomes more congested")
    print(f"      - Optimal path allocation should shift to balance load")
    print(f"      - But we're using FIXED path ratios from Step 1")
    print(f"      - This sub-optimal routing leads to higher utilization than predicted")
    print(f"      - The slope difference quantifies this sub-optimality")
    print()
    print("   d) Capacity Constraint Effects:")
    print(f"      - At low demand: Many paths available, utilization scales linearly")
    print(f"      - At high demand: Fewer paths available, bottlenecks form")
    print(f"      - The slope difference reflects when capacity constraints become binding")
    print()
    print("   e) Practical Implication:")
    print(f"      - For small changes (< 100 packets/s): Linear approximation works")
    print(f"      - For large changes (> 300 packets/s): Re-optimization needed")
    print(f"      - Slope difference = {slope_diff:.6f} means each additional")
    print(f"        packet/s increases utilization by {slope_diff:.6f}% more than")
    print(f"        predicted by the dual variable alone")
    print()
    
    # Calculate effective "second-order coefficient"
    # If error = (1/2) * second_order * (demand_change)^2
    # Then second_order = 2 * error / (demand_change)^2
    # For step 10: demand_change = 450, error = 13.32%
    step10_error = df[df['step_id'] == 10]['absolute_error'].iloc[0]
    step10_demand_change = df[df['step_id'] == 10]['demand_change'].iloc[0]
    
    if step10_demand_change > 0:
        # Approximate second-order coefficient
        second_order_coeff = 2 * step10_error / (step10_demand_change ** 2)
        print("   f) Second-Order Coefficient Estimate:")
        print(f"      Approximate d²util/dd² ≈ {second_order_coeff:.6e} %/(packets/s)²")
        print(f"      This quantifies the curvature (non-linearity) of the utilization function")
        print()
    
    # Save analysis
    analysis_data = {
        'lambda_2': lambda_2,
        'slope_theoretical_demand': slope_theo_demand,
        'slope_predicted_demand': slope_pred_demand,
        'slope_difference': slope_diff,
        'slope_theoretical_step': slope_theo_step,
        'slope_predicted_step': slope_pred_step,
        'r2_theoretical': r_theo_demand**2,
        'r2_predicted': r_pred_demand**2
    }
    
    analysis_df = pd.DataFrame([analysis_data])
    analysis_file = os.path.join(result_dir, 'slope_analysis.csv')
    analysis_df.to_csv(analysis_file, index=False)
    print(f"✓ Slope analysis saved to: {analysis_file}")
    
    print()
    print("=" * 80)
    print("✓ Analysis complete!")
    print("=" * 80)


if __name__ == '__main__':
    quick_slope_analysis()

