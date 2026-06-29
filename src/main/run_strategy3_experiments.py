#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Strategy 3 (Global Optimal Ratio) experiments on Experiment 4 sequences.

This script runs Strategy 3 on the three arrival rate sequences from Experiment 4:
1. Random perturbation sequence
2. Increasing sequence
3. Hybrid sequence

It then compares Strategy 3 with Strategy 1 and Strategy 2 results.
"""

import sys
import os
import pandas as pd
import numpy as np
import shutil

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_global_optimal_ratio


def run_strategy3_for_sequence(sequence_file, sequence_name, config_file, output_base_dir):
    """
    Run Strategy 3 for a given arrival rate sequence.
    
    Args:
        sequence_file: Path to CSV file containing arrival rate sequence
        sequence_name: Name of the sequence (for output directory)
        config_file: Path to YAML configuration file
        output_base_dir: Base directory for outputs
        
    Returns:
        list: Strategy 3 statistics
    """
    print("=" * 80)
    print(f"Running Strategy 3: {sequence_name}")
    print("=" * 80)
    print()
    
    # Load sequence
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    
    # Load config
    config = load_yaml_file(config_file)
    
    # Output directory
    output_dir = os.path.join(output_base_dir, sequence_name, 'strategy3')
    os.makedirs(output_dir, exist_ok=True)
    
    # Run Strategy 3
    strategy3_stats = execute_strategy_global_optimal_ratio(
        sequence, config, output_dir
    )
    
    # Save statistics
    df3 = pd.DataFrame(strategy3_stats)
    df3_file = os.path.join(output_dir, 'strategy3_stats.csv')
    df3['arrival_rates'] = df3['arrival_rates'].apply(lambda x: str(x))
    df3.to_csv(df3_file, index=False)
    
    print(f"\n✓ Strategy 3 statistics saved to: {df3_file}")
    
    return strategy3_stats


def compare_strategies(sequence_name, output_base_dir):
    """
    Compare Strategy 1, 2, and 3 results for a given sequence.
    
    Args:
        sequence_name: Name of the sequence
        output_base_dir: Base directory for outputs
        
    Returns:
        dict: Comparison summary
    """
    base_dir = os.path.join(output_base_dir, sequence_name)
    
    # Load statistics
    s1_file = os.path.join(base_dir, 'strategy1', 'strategy1_stats.csv')
    s2_file = os.path.join(base_dir, 'strategy2', 'strategy2_stats.csv')
    s3_file = os.path.join(base_dir, 'strategy3', 'strategy3_stats.csv')
    
    if not all(os.path.exists(f) for f in [s1_file, s2_file, s3_file]):
        print(f"⚠️  Some strategy files not found for {sequence_name}, skipping comparison")
        return None
    
    s1_df = pd.read_csv(s1_file)
    s2_df = pd.read_csv(s2_file)
    s3_df = pd.read_csv(s3_file)
    
    # Calculate averages
    summary = {
        'sequence': sequence_name,
        'strategy1_avg_util': s1_df['max_link_utilization'].mean(),
        'strategy2_avg_util': s2_df['max_link_utilization'].mean(),
        'strategy3_avg_util': s3_df['max_link_utilization'].mean(),
        'strategy1_avg_pli': s1_df['pli'].mean(),
        'strategy2_avg_pli': s2_df['pli'].mean(),
        'strategy3_avg_pli': s3_df['pli'].mean(),
        'strategy1_avg_delay': s1_df['avg_delay'].mean(),
        'strategy2_avg_delay': s2_df['avg_delay'].mean(),
        'strategy3_avg_delay': s3_df['avg_delay'].mean(),
    }
    
    # Calculate differences
    summary['util_s1_vs_s2'] = summary['strategy1_avg_util'] - summary['strategy2_avg_util']
    summary['util_s1_vs_s3'] = summary['strategy1_avg_util'] - summary['strategy3_avg_util']
    summary['util_s2_vs_s3'] = summary['strategy2_avg_util'] - summary['strategy3_avg_util']
    
    return summary


def main():
    """Main function to run Strategy 3 experiments."""
    
    print("=" * 80)
    print("Strategy 3 (Global Optimal Ratio) Experiments")
    print("Running on Experiment 4 sequences")
    print("=" * 80)
    print()
    
    # Configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    output_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    
    # Sequence files
    sequences = {
        'random_perturbation': os.path.join(src_dir, 'results', 'arrival_rate_sequence_random.csv'),
        'increasing_sequence': os.path.join(src_dir, 'results', 'arrival_rate_sequence_increasing.csv'),
        'hybrid_sequence': os.path.join(src_dir, 'results', 'arrival_rate_sequence_hybrid.csv'),
    }
    
    all_summaries = []
    
    # Run Strategy 3 for each sequence
    for seq_name, seq_file in sequences.items():
        if not os.path.exists(seq_file):
            print(f"⚠️  Sequence file not found: {seq_file}, skipping")
            continue
        
        # Run Strategy 3
        strategy3_stats = run_strategy3_for_sequence(
            seq_file, seq_name, config_file, output_base_dir
        )
        
        # Compare with Strategy 1 and 2 (if they exist)
        summary = compare_strategies(seq_name, output_base_dir)
        if summary:
            all_summaries.append(summary)
        
        print()
    
    # Print comparison summary
    if all_summaries:
        print("=" * 80)
        print("Comparison Summary: Strategy 1 vs Strategy 2 vs Strategy 3")
        print("=" * 80)
        print()
        
        for summary in all_summaries:
            seq_name = summary['sequence']
            print(f"Sequence: {seq_name}")
            print(f"  Strategy 1 Avg Util: {summary['strategy1_avg_util']:.4f}%")
            print(f"  Strategy 2 Avg Util: {summary['strategy2_avg_util']:.4f}%")
            print(f"  Strategy 3 Avg Util: {summary['strategy3_avg_util']:.4f}%")
            print(f"  Difference (S1-S2): {summary['util_s1_vs_s2']:.4f}%")
            print(f"  Difference (S1-S3): {summary['util_s1_vs_s3']:.4f}%")
            print(f"  Difference (S2-S3): {summary['util_s2_vs_s3']:.4f}%")
            print()
        
        # Save summary
        summary_df = pd.DataFrame(all_summaries)
        summary_file = os.path.join(output_base_dir, 'strategy3_comparison_summary.csv')
        summary_df.to_csv(summary_file, index=False)
        print(f"✓ Comparison summary saved to: {summary_file}")
    
    print("=" * 80)
    print("Strategy 3 experiments completed!")
    print("=" * 80)


if __name__ == '__main__':
    main()

