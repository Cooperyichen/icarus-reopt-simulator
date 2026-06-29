#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualize dual variable prediction comparison.

Generate charts comparing theoretical and predicted max link utilization.
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)


def visualize_dual_prediction_comparison():
    """Generate visualization charts for dual variable prediction comparison."""
    print("=" * 80)
    print("Visualizing Dual Variable Prediction Comparison")
    print("=" * 80)
    print()
    
    # Load comparison data
    result_dir = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation', 
                             'strategy_dual_validation')
    comparison_file = os.path.join(result_dir, 'dual_prediction_comparison.csv')
    
    if not os.path.exists(comparison_file):
        print(f"✗ Comparison file not found: {comparison_file}")
        print("Please run analyze_dual_prediction_accuracy.py first")
        return
    
    df = pd.read_csv(comparison_file)
    
    # Output directory
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', '对偶变量验证')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Theoretical vs Predicted (Line plot)
    ax = axes[0, 0]
    ax.plot(df['step_id'], df['theoretical_util'], marker='o', linewidth=2, 
           label='Theoretical', color='#1f77b4', markersize=8)
    ax.plot(df['step_id'], df['predicted_util'], marker='s', linewidth=2, 
           label='Predicted (Linear Extrapolation)', color='#ff7f0e', markersize=8, linestyle='--')
    ax.set_xlabel('Time Step', fontsize=12, fontweight='bold')
    ax.set_ylabel('Max Link Utilization (%)', fontsize=12, fontweight='bold')
    ax.set_title('Theoretical vs Predicted Max Link Utilization', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(df['step_id'])
    
    # 2. Absolute Error (Bar chart)
    ax = axes[0, 1]
    bars = ax.bar(df['step_id'], df['absolute_error'], color='#d62728', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Time Step', fontsize=12, fontweight='bold')
    ax.set_ylabel('Absolute Error (%)', fontsize=12, fontweight='bold')
    ax.set_title('Prediction Absolute Error', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(df['step_id'])
    
    # Add value labels on bars
    for i, (step, error) in enumerate(zip(df['step_id'], df['absolute_error'])):
        if error > 0.5:  # Only label if error is significant
            ax.text(step, error, f'{error:.2f}%', ha='center', va='bottom', fontsize=9)
    
    # 3. Relative Error (Bar chart)
    ax = axes[1, 0]
    bars = ax.bar(df['step_id'], df['relative_error'], color='#2ca02c', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Time Step', fontsize=12, fontweight='bold')
    ax.set_ylabel('Relative Error (%)', fontsize=12, fontweight='bold')
    ax.set_title('Prediction Relative Error', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(df['step_id'])
    
    # Add value labels on bars
    for i, (step, error) in enumerate(zip(df['step_id'], df['relative_error'])):
        if error > 1.0:  # Only label if error is significant
            ax.text(step, error, f'{error:.1f}%', ha='center', va='bottom', fontsize=9)
    
    # 4. Error vs Demand Change (Scatter plot)
    ax = axes[1, 1]
    scatter = ax.scatter(df['demand_change'], df['absolute_error'], 
                        s=100, alpha=0.6, c=df['step_id'], cmap='viridis', 
                        edgecolors='black', linewidth=1)
    ax.set_xlabel('Commodity 2 Demand Change (packets/s)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Absolute Error (%)', fontsize=12, fontweight='bold')
    ax.set_title('Prediction Error vs Demand Change', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Time Step', fontsize=10)
    
    # Add trend line
    z = np.polyfit(df['demand_change'], df['absolute_error'], 1)
    p = np.poly1d(z)
    ax.plot(df['demand_change'], p(df['demand_change']), "r--", alpha=0.8, linewidth=2, label='Trend')
    ax.legend(fontsize=10)
    
    plt.tight_layout()
    
    # Save figure
    output_file = os.path.join(output_dir, 'dual_prediction_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Comparison chart saved: {output_file}")
    
    # Create separate detailed comparison chart
    fig, ax = plt.subplots(figsize=(12, 8))
    
    x = np.arange(len(df))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, df['theoretical_util'], width, label='Theoretical', 
                   color='#1f77b4', alpha=0.8, edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + width/2, df['predicted_util'], width, label='Predicted', 
                   color='#ff7f0e', alpha=0.8, edgecolor='black', linewidth=0.5)
    
    ax.set_xlabel('Time Step', fontsize=14, fontweight='bold')
    ax.set_ylabel('Max Link Utilization (%)', fontsize=14, fontweight='bold')
    ax.set_title('Theoretical vs Predicted Max Link Utilization (Detailed Comparison)', 
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(df['step_id'])
    ax.legend(fontsize=12, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for i, (theo, pred) in enumerate(zip(df['theoretical_util'], df['predicted_util'])):
        ax.text(i - width/2, theo, f'{theo:.2f}%', ha='center', va='bottom', fontsize=9, rotation=90)
        ax.text(i + width/2, pred, f'{pred:.2f}%', ha='center', va='bottom', fontsize=9, rotation=90)
    
    plt.tight_layout()
    
    output_file2 = os.path.join(output_dir, 'dual_prediction_detailed_comparison.png')
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Detailed comparison chart saved: {output_file2}")
    
    # Create error trend chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Absolute error trend
    ax1.plot(df['step_id'], df['absolute_error'], marker='o', linewidth=2, 
            markersize=8, color='#d62728')
    ax1.fill_between(df['step_id'], df['absolute_error'], alpha=0.3, color='#d62728')
    ax1.set_xlabel('Time Step', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Absolute Error (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Absolute Error Trend', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(df['step_id'])
    
    # Relative error trend
    ax2.plot(df['step_id'], df['relative_error'], marker='s', linewidth=2, 
            markersize=8, color='#2ca02c')
    ax2.fill_between(df['step_id'], df['relative_error'], alpha=0.3, color='#2ca02c')
    ax2.set_xlabel('Time Step', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Relative Error (%)', fontsize=12, fontweight='bold')
    ax2.set_title('Relative Error Trend', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(df['step_id'])
    
    plt.tight_layout()
    
    output_file3 = os.path.join(output_dir, 'prediction_error_trend.png')
    plt.savefig(output_file3, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Error trend chart saved: {output_file3}")
    
    # Print summary
    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Mean absolute error: {df['absolute_error'].mean():.4f}%")
    print(f"Max absolute error: {df['absolute_error'].max():.4f}% (Step {df.loc[df['absolute_error'].idxmax(), 'step_id']})")
    print(f"Mean relative error: {df['relative_error'].mean():.4f}%")
    print(f"Max relative error: {df['relative_error'].max():.4f}% (Step {df.loc[df['relative_error'].idxmax(), 'step_id']})")
    print()
    print("=" * 80)
    print("✓ Visualization complete!")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")


def main():
    """Main function"""
    visualize_dual_prediction_comparison()


if __name__ == '__main__':
    main()

