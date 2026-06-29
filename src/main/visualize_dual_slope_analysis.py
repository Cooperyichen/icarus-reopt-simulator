#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualize dual variable changes and slope differences.
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
matplotlib.rcParams['axes.unicode_minus'] = False

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)


def visualize_dual_slope_analysis():
    """Create visualizations for dual variable and slope analysis."""
    
    result_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation', 
                             'strategy_dual_validation')
    comparison_file = os.path.join(result_dir, 'dual_prediction_comparison.csv')
    summary_file = os.path.join(result_dir, 'dual_validation_summary.csv')
    slope_file = os.path.join(result_dir, 'slope_analysis.csv')
    
    df = pd.read_csv(comparison_file)
    summary = pd.read_csv(summary_file)
    slope_data = pd.read_csv(slope_file)
    
    lambda_2 = summary['lambda_2'].iloc[0]
    slope_diff = slope_data['slope_difference'].iloc[0]
    slope_theo = slope_data['slope_theoretical_demand'].iloc[0]
    slope_pred = slope_data['slope_predicted_demand'].iloc[0]
    
    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    
    # 1. Dual variable (constant in our experiment)
    ax1 = plt.subplot(2, 3, 1)
    ax1.axhline(y=lambda_2, color='blue', linestyle='-', linewidth=2, label=f'λ₂ = {lambda_2:.6f}')
    ax1.set_xlabel('Time Step', fontsize=12)
    ax1.set_ylabel('Dual Variable λ₂ (%/(packets/s))', fontsize=12)
    ax1.set_title('Dual Variable for Commodity 2\n(Constant in Experiment)', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)
    ax1.set_xlim(0.5, 10.5)
    ax1.set_xticks(range(1, 11))
    
    # 2. Utilization slopes comparison
    ax2 = plt.subplot(2, 3, 2)
    categories = ['Theoretical', 'Predicted\n(Linear)', 'Difference']
    values = [slope_theo, slope_pred, slope_diff]
    colors = ['#2E86AB', '#A23B72', '#F18F01']
    bars = ax2.bar(categories, values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('Slope (%/(packets/s))', fontsize=12)
    ax2.set_title('Slope Comparison\n(Utilization vs Demand Change)', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.6f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # 3. Slope difference visualization
    ax3 = plt.subplot(2, 3, 3)
    demand_change = df['demand_change'].values
    theoretical_util = df['theoretical_util'].values
    predicted_util = df['predicted_util'].values
    
    # Linear fits
    z_theo = np.polyfit(demand_change, theoretical_util, 1)
    z_pred = np.polyfit(demand_change, predicted_util, 1)
    p_theo = np.poly1d(z_theo)
    p_pred = np.poly1d(z_pred)
    
    x_fit = np.linspace(0, 450, 100)
    ax3.plot(demand_change, theoretical_util, 'o', color='#2E86AB', markersize=8, 
             label='Theoretical', zorder=3)
    ax3.plot(demand_change, predicted_util, 's', color='#A23B72', markersize=8, 
             label='Predicted (Linear)', zorder=3)
    ax3.plot(x_fit, p_theo(x_fit), '--', color='#2E86AB', linewidth=2, alpha=0.7,
             label=f'Theoretical fit (slope={slope_theo:.6f})', zorder=2)
    ax3.plot(x_fit, p_pred(x_fit), '--', color='#A23B72', linewidth=2, alpha=0.7,
             label=f'Predicted fit (slope={slope_pred:.6f})', zorder=2)
    
    # Highlight the difference
    ax3.fill_between(x_fit, p_pred(x_fit), p_theo(x_fit), 
                     alpha=0.2, color='#F18F01', label=f'Slope difference area')
    
    ax3.set_xlabel('Commodity 2 Demand Change (packets/s)', fontsize=12)
    ax3.set_ylabel('Max Link Utilization (%)', fontsize=12)
    ax3.set_title('Slope Difference Visualization', fontsize=13, fontweight='bold')
    ax3.legend(fontsize=9, loc='upper left')
    ax3.grid(True, alpha=0.3)
    
    # 4. Error accumulation over time
    ax4 = plt.subplot(2, 3, 4)
    step_id = df['step_id'].values
    absolute_error = df['absolute_error'].values
    
    # Calculate expected error from slope difference
    expected_error = slope_diff * demand_change
    
    ax4.plot(step_id, absolute_error, 'o-', color='#C73E1D', linewidth=2, 
             markersize=8, label='Actual Error', zorder=3)
    ax4.plot(step_id, expected_error, '--', color='#F18F01', linewidth=2, 
             label=f'Expected Error (slope_diff × Δd)', zorder=2)
    
    ax4.set_xlabel('Time Step', fontsize=12)
    ax4.set_ylabel('Absolute Error (%)', fontsize=12)
    ax4.set_title('Error Accumulation\n(Matches Slope Difference)', fontsize=13, fontweight='bold')
    ax4.legend(fontsize=11)
    ax4.grid(True, alpha=0.3)
    ax4.set_xticks(range(1, 11))
    
    # 5. Slope difference interpretation
    ax5 = plt.subplot(2, 3, 5)
    ax5.axis('off')
    
    text_content = f"""
Slope Difference Analysis

Value: {slope_diff:.6f} %/(packets/s)

Interpretation:

1. Non-linear Effects
   Additional utilization increase per unit
   demand change not captured by linear
   approximation (dual variable).

2. Mathematical Meaning
   Represents second-order and higher-order
   terms in Taylor expansion:
   
   util(d) = util(d₀) + λ₂×(d-d₀) 
           + (1/2)×d²util/dd²×(d-d₀)² + ...
   
   Slope difference ≈ higher-order terms

3. Physical Meaning
   - Sub-optimal routing (fixed path ratios)
   - Capacity constraint binding effects
   - Network congestion non-linearity

4. Second-Order Coefficient
   d²util/dd² ≈ {2*absolute_error[-1]/(demand_change[-1]**2):.6e} %/(packets/s)²
    """
    
    ax5.text(0.05, 0.95, text_content, transform=ax5.transAxes,
            fontsize=11, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    # 6. Relative contribution
    ax6 = plt.subplot(2, 3, 6)
    
    # Calculate contribution percentages
    total_slope = slope_theo
    pred_contribution = (slope_pred / total_slope) * 100
    diff_contribution = (slope_diff / total_slope) * 100
    
    sizes = [pred_contribution, diff_contribution]
    labels = [f'Linear (λ₂)\n{pred_contribution:.1f}%', 
              f'Non-linear\n{diff_contribution:.1f}%']
    colors_pie = ['#A23B72', '#F18F01']
    explode = (0, 0.1)
    
    wedges, texts, autotexts = ax6.pie(sizes, explode=explode, labels=labels, 
                                        colors=colors_pie, autopct='%1.1f%%',
                                        shadow=True, startangle=90, textprops={'fontsize': 11})
    
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(12)
    
    ax6.set_title('Contribution to Total Slope\n(Linear vs Non-linear)', 
                  fontsize=13, fontweight='bold')
    
    plt.tight_layout()
    
    # Save figure
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', '对偶变量验证')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'dual_variable_slope_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Visualization saved to: {output_file}")
    
    plt.close()


if __name__ == '__main__':
    visualize_dual_slope_analysis()

