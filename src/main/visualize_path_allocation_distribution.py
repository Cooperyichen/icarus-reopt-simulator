#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualize path allocation distribution for first and last steps

Create bar charts showing the distribution of path allocation ratios
for each commodity in step 1 and step 10.
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)


def create_path_allocation_bar_chart(sequence_name, step_id, output_dir):
    """
    Create a bar chart showing path allocation distribution for a specific step.
    
    Args:
        sequence_name: Name of the sequence
        step_id: Step ID (1 or 10)
        output_dir: Output directory for saving the figure
    """
    result_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    analysis_dir = os.path.join(result_base_dir, sequence_name, 'strategy1', 'path_allocation_analysis')
    
    # Load detailed path ratios data
    detailed_file = os.path.join(analysis_dir, 'detailed_path_ratios.csv')
    if not os.path.exists(detailed_file):
        print(f"✗ File not found: {detailed_file}")
        return
    
    df = pd.read_csv(detailed_file)
    
    # Filter for the specific step
    step_df = df[df['step_id'] == step_id].copy()
    
    if len(step_df) == 0:
        print(f"✗ No data found for step {step_id}")
        return
    
    # Define percentage bins (0-5%, 5-10%, 10-15%, etc.)
    bins = np.arange(0, 1.05, 0.05)  # 0%, 5%, 10%, ..., 100%
    bin_labels = [f'{int(bins[i]*100)}-{int(bins[i+1]*100)}%' for i in range(len(bins)-1)]
    
    # Get unique commodities
    commodities = sorted(step_df['commodity_id'].unique())
    num_commodities = len(commodities)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Colors for different commodities
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # Width of bars
    bar_width = 0.8 / num_commodities
    
    # Calculate positions for grouped bars
    x_positions = np.arange(len(bin_labels))
    
    # For each commodity, count paths in each bin
    for idx, commodity_id in enumerate(commodities):
        commodity_data = step_df[step_df['commodity_id'] == commodity_id]['ratio'].values
        
        # Count paths in each bin
        counts, _ = np.histogram(commodity_data, bins=bins)
        
        # Calculate bar positions (grouped bars)
        bar_positions = x_positions + idx * bar_width - (num_commodities - 1) * bar_width / 2
        
        # Create bars
        bars = ax.bar(bar_positions, counts, bar_width, 
                     label=f'Commodity {commodity_id}',
                     color=colors[idx % len(colors)],
                     alpha=0.8,
                     edgecolor='black',
                     linewidth=0.5)
    
    # Customize the plot
    ax.set_xlabel('Path Allocation Ratio Range', fontsize=14, fontweight='bold')
    ax.set_ylabel('Number of Paths', fontsize=14, fontweight='bold')
    ax.set_title(f'Path Allocation Distribution - {sequence_name.replace("_", " ").title()} - Step {step_id}',
                fontsize=16, fontweight='bold', pad=20)
    
    # Set x-axis labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels(bin_labels, rotation=45, ha='right', fontsize=10)
    
    # Add grid
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')
    ax.set_axisbelow(True)
    
    # Add legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f'path_allocation_distribution_step{step_id}.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved: {output_file}")
    
    # Print summary statistics
    print(f"\nStep {step_id} Summary:")
    for commodity_id in commodities:
        commodity_data = step_df[step_df['commodity_id'] == commodity_id]['ratio'].values
        print(f"  Commodity {commodity_id}: {len(commodity_data)} paths, "
              f"ratio range: [{commodity_data.min():.4f}, {commodity_data.max():.4f}], "
              f"mean: {commodity_data.mean():.4f}")


def main():
    """Main function"""
    print("=" * 80)
    print("Visualizing Path Allocation Distribution")
    print("=" * 80)
    print()
    
    # Output directory
    output_base_dir = os.path.join(src_dir, 'results', '可视化结果展示', '全优化流量分布')
    os.makedirs(output_base_dir, exist_ok=True)
    
    # Sequences to process
    sequences = ['increasing_sequence', 'random_perturbation', 'hybrid_sequence']
    steps = [1, 10]  # First and last steps
    
    for sequence_name in sequences:
        print(f"\n{'='*80}")
        print(f"Processing: {sequence_name}")
        print(f"{'='*80}")
        
        sequence_output_dir = os.path.join(output_base_dir, sequence_name)
        os.makedirs(sequence_output_dir, exist_ok=True)
        
        for step_id in steps:
            try:
                create_path_allocation_bar_chart(sequence_name, step_id, sequence_output_dir)
            except Exception as e:
                print(f"✗ Error processing {sequence_name} step {step_id}: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("✓ Visualization complete!")
    print(f"{'='*80}")
    print(f"\nOutput directory: {output_base_dir}")


if __name__ == '__main__':
    main()

