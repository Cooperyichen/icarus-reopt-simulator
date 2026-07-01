#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run all four strategies (Strategy 1, 2, 3, 4) for random_perturbation and increasing_sequence.

This script runs all strategies for the specified sequences and saves results to
the appropriate directories for visualization.
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
from main.multi_step_comparison_experiment import (
    execute_strategy_reoptimization,
    execute_strategy_path_ratio_preservation,
    execute_strategy_global_optimal_ratio,
    execute_strategy_adaptive_reoptimization
)


def run_strategy_for_sequence(sequence_file, sequence_name, strategy_name, config, result_dir_base):
    """
    Run a specific strategy for a given sequence.
    
    Args:
        sequence_file: Path to CSV file containing arrival rate sequence
        sequence_name: Name of the sequence
        strategy_name: 'strategy1', 'strategy2', 'strategy3', or 'strategy4'
        config: Configuration dictionary
        result_dir_base: Base directory for results
        
    Returns:
        tuple: (strategy_stats, infeasible_steps) or None if error
    """
    print(f"\n{'='*80}")
    print(f"Running {strategy_name} for {sequence_name}")
    print(f"{'='*80}")
    
    # Load sequence
    if not os.path.exists(sequence_file):
        print(f"✗ Error: Sequence file not found: {sequence_file}")
        return None
    
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    
    # Create output directory structure
    if strategy_name in ['strategy1', 'strategy2']:
        # Strategy 1 and 2 save to sequence-specific subdirectories
        strategy_dir = os.path.join(result_dir_base, sequence_name, strategy_name)
    else:
        # Strategy 3 and 4 save to sequence-specific subdirectories
        strategy_dir = os.path.join(result_dir_base, sequence_name, strategy_name)
    
    # Run the appropriate strategy
    try:
        if strategy_name == 'strategy1':
            strategy_stats, infeasible_steps = execute_strategy_reoptimization(
                sequence, config, os.path.join(result_dir_base, sequence_name)
            )
        elif strategy_name == 'strategy2':
            strategy_stats = execute_strategy_path_ratio_preservation(
                sequence, config, os.path.join(result_dir_base, sequence_name)
            )
            infeasible_steps = []
        elif strategy_name == 'strategy3':
            strategy_stats = execute_strategy_global_optimal_ratio(
                sequence, config, os.path.join(result_dir_base, sequence_name)
            )
            infeasible_steps = []
        elif strategy_name == 'strategy4':
            strategy_stats = execute_strategy_adaptive_reoptimization(
                sequence, config, os.path.join(result_dir_base, sequence_name),
                threshold=8
            )
            infeasible_steps = []
        else:
            print(f"✗ Unknown strategy: {strategy_name}")
            return None
        
        # Save statistics to CSV
        strategy_dir = os.path.join(result_dir_base, sequence_name, strategy_name)
        os.makedirs(strategy_dir, exist_ok=True)
        
        df = pd.DataFrame(strategy_stats)
        stats_file = os.path.join(strategy_dir, f'{strategy_name}_stats.csv')
        
        # Convert arrival_rates list to string for CSV
        if 'arrival_rates' in df.columns:
            df['arrival_rates'] = df['arrival_rates'].apply(lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x)
        
        df.to_csv(stats_file, index=False)
        print(f"✓ Statistics saved to: {stats_file}")
        
        if strategy_name == 'strategy1':
            return strategy_stats, infeasible_steps
        else:
            return strategy_stats, []
            
    except Exception as e:
        print(f"✗ Error running {strategy_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function to run all strategies for specified sequences."""
    
    print("=" * 80)
    print("Running All Strategies for Random Perturbation and Increasing Sequence")
    print("=" * 80)
    print()
    
    # Configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    
    # Load config
    config = load_yaml_file(config_file)
    
    # Sequences to run
    sequences = {
        'random_perturbation': os.path.join(src_dir, 'results', 'arrival_rate_sequence_random.csv'),
        'increasing_sequence': os.path.join(src_dir, 'results', 'arrival_rate_sequence_increasing.csv'),
    }
    
    # Strategies to run
    strategies = ['strategy1', 'strategy2', 'strategy3', 'strategy4']
    
    # Track results
    results_summary = {}
    
    for sequence_name, sequence_file in sequences.items():
        print(f"\n{'='*80}")
        print(f"Processing Sequence: {sequence_name}")
        print(f"{'='*80}")
        
        results_summary[sequence_name] = {}
        
        for strategy_name in strategies:
            result = run_strategy_for_sequence(
                sequence_file, sequence_name, strategy_name, config, result_dir_base
            )
            
            if result is not None:
                strategy_stats, infeasible_steps = result
                results_summary[sequence_name][strategy_name] = {
                    'completed': True,
                    'num_steps': len(strategy_stats),
                    'infeasible_steps': infeasible_steps
                }
            else:
                results_summary[sequence_name][strategy_name] = {
                    'completed': False
                }
            
            print()  # Blank line between strategies
    
    # Print summary
    print("\n" + "=" * 80)
    print("Execution Summary")
    print("=" * 80)
    
    for sequence_name, seq_results in results_summary.items():
        print(f"\n{sequence_name}:")
        for strategy_name, status in seq_results.items():
            if status.get('completed', False):
                infeasible = status.get('infeasible_steps', [])
                infeasible_str = f" (infeasible steps: {infeasible})" if infeasible else ""
                print(f"  {strategy_name}: ✓ Completed{infeasible_str}")
            else:
                print(f"  {strategy_name}: ✗ Failed")
    
    print("\n" + "=" * 80)
    print("✓ All strategies executed!")
    print("=" * 80)
    print(f"\nResults saved to: {result_dir_base}")
    print("\nNext step: Run generate_comparison_visualizations.py to update visualizations.")


if __name__ == '__main__':
    main()

