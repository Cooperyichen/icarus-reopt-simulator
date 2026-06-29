#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run three multi-step comparison experiments with different arrival rate sequences:
1. Random perturbation sequence
2. Increasing sequence  
3. Hybrid sequence

Each experiment compares Strategy 1 (re-optimization) vs Strategy 2 (path ratio preservation).
"""

import sys
import os
import shutil
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from main.multi_step_comparison_experiment import main as run_experiment
from topo.utils import load_yaml_file

def run_single_experiment(sequence_file, experiment_name):
    """Run a single experiment with the given sequence file."""
    print("\n" + "=" * 80)
    print(f"Starting Experiment: {experiment_name}")
    print("=" * 80)
    print()
    
    # Temporarily copy the sequence file to the standard location
    standard_sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    shutil.copy(sequence_file, standard_sequence_file)
    print(f"✓ Copied {sequence_file} to {standard_sequence_file}")
    print()
    
    # Run the experiment
    try:
        results = run_experiment()
        print(f"\n✓ Experiment '{experiment_name}' completed successfully!")
        return results
    except Exception as e:
        print(f"\n✗ Experiment '{experiment_name}' failed with error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run all three experiments."""
    
    results_dir = os.path.join(src_dir, 'results')
    
    experiments = [
        {
            'name': 'Random Perturbation',
            'sequence_file': os.path.join(results_dir, 'arrival_rate_sequence_random.csv'),
            'description': 'Normal distribution perturbation (std_dev=50) for all commodities'
        },
        {
            'name': 'Increasing Sequence',
            'sequence_file': os.path.join(results_dir, 'arrival_rate_sequence_increasing.csv'),
            'description': 'Exponential increment (scale=50) for all commodities'
        },
        {
            'name': 'Hybrid Sequence',
            'sequence_file': os.path.join(results_dir, 'arrival_rate_sequence_hybrid.csv'),
            'description': 'Normal perturbation (0-1) + Exponential increment (2-3)'
        }
    ]
    
    print("=" * 80)
    print("Running Three Multi-Step Comparison Experiments")
    print("Objective: minimize_max_link_utilization")
    print("=" * 80)
    print()
    
    # Verify configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    print(f"Configuration:")
    print(f"  Objective function: {config['optimization']['objective_func']}")
    print(f"  Split commodities: {config['optimization']['split_commodities']}")
    print()
    
    all_results = {}
    
    for i, exp in enumerate(experiments, 1):
        print(f"\n{'='*80}")
        print(f"Experiment {i}/3: {exp['name']}")
        print(f"Description: {exp['description']}")
        print(f"{'='*80}")
        
        if not os.path.exists(exp['sequence_file']):
            print(f"✗ Error: Sequence file not found: {exp['sequence_file']}")
            continue
        
        results = run_single_experiment(exp['sequence_file'], exp['name'])
        
        if results:
            all_results[exp['name']] = results
            
            # Backup results for this experiment
            backup_dir = os.path.join(results_dir, 'multi_step_comparison', exp['name'].lower().replace(' ', '_'))
            if os.path.exists(os.path.join(results_dir, 'multi_step_comparison')):
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                os.makedirs(backup_dir, exist_ok=True)
                shutil.copytree(
                    os.path.join(results_dir, 'multi_step_comparison', 'strategy1'),
                    os.path.join(backup_dir, 'strategy1')
                )
                shutil.copytree(
                    os.path.join(results_dir, 'multi_step_comparison', 'strategy2'),
                    os.path.join(backup_dir, 'strategy2')
                )
                shutil.copy(
                    os.path.join(results_dir, 'multi_step_comparison', 'comparison_summary.csv'),
                    os.path.join(backup_dir, 'comparison_summary.csv')
                )
                print(f"\n✓ Results backed up to: {backup_dir}")
        
        print()
        print(f"{'='*80}")
        print(f"Experiment {i}/3 completed")
        print(f"{'='*80}")
        print()
    
    print("\n" + "=" * 80)
    print("All Experiments Summary")
    print("=" * 80)
    print()
    
    for name, results in all_results.items():
        if results:
            s1_stats = results['strategy1_stats']
            s2_stats = results['strategy2_stats']
            
            s1_avg_util = sum(s['max_link_utilization'] for s in s1_stats) / len(s1_stats)
            s2_avg_util = sum(s['max_link_utilization'] for s in s2_stats) / len(s2_stats)
            
            print(f"{name}:")
            print(f"  Strategy 1 Avg Util: {s1_avg_util:.4f}%")
            print(f"  Strategy 2 Avg Util: {s2_avg_util:.4f}%")
            print(f"  Difference (S1-S2): {s1_avg_util - s2_avg_util:.4f}%")
            print()
    
    print("=" * 80)
    print("All experiments completed!")
    print("=" * 80)
    
    return all_results


if __name__ == '__main__':
    results = main()

