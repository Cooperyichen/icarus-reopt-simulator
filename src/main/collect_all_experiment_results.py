#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run each experiment separately and collect all results.
"""

import sys
import os
import shutil
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from main.multi_step_comparison_experiment import main as run_experiment

results_dir = os.path.join(src_dir, 'results')
standard_file = os.path.join(results_dir, 'arrival_rate_sequence_10_steps.csv')

experiments = [
    ('Random Perturbation', os.path.join(results_dir, 'arrival_rate_sequence_random.csv')),
    ('Increasing Sequence', os.path.join(results_dir, 'arrival_rate_sequence_increasing.csv')),
    ('Hybrid Sequence', os.path.join(results_dir, 'arrival_rate_sequence_hybrid.csv'))
]

all_results = {}

for exp_name, seq_file in experiments:
    print(f"\n{'='*80}")
    print(f"Running: {exp_name}")
    print(f"{'='*80}\n")
    
    if not os.path.exists(seq_file):
        print(f"✗ File not found: {seq_file}")
        continue
    
    # Copy sequence file
    shutil.copy(seq_file, standard_file)
    
    # Run experiment
    try:
        results = run_experiment()
        
        # Read results
        summary_file = os.path.join(results_dir, 'multi_step_comparison', 'comparison_summary.csv')
        if os.path.exists(summary_file):
            df = pd.read_csv(summary_file)
            all_results[exp_name] = {
                'comparison_df': df,
                's1_avg_util': df['strategy1_max_util'].mean(),
                's2_avg_util': df['strategy2_max_util'].mean(),
                's1_avg_pli': df['strategy1_pli'].mean(),
                's2_avg_pli': df['strategy2_pli'].mean(),
                's1_avg_delay': df['strategy1_delay'].mean(),
                's2_avg_delay': df['strategy2_delay'].mean()
            }
            print(f"\n✓ {exp_name} completed")
            print(f"  Strategy 1: Util={all_results[exp_name]['s1_avg_util']:.4f}%")
            print(f"  Strategy 2: Util={all_results[exp_name]['s2_avg_util']:.4f}%")
    except Exception as e:
        print(f"\n✗ {exp_name} failed: {e}")

print(f"\n{'='*80}")
print("All Experiments Summary")
print(f"{'='*80}\n")

for exp_name, data in all_results.items():
    print(f"{exp_name}:")
    print(f"  Strategy 1: Util={data['s1_avg_util']:.4f}%, PLI={data['s1_avg_pli']:.4f}%")
    print(f"  Strategy 2: Util={data['s2_avg_util']:.4f}%, PLI={data['s2_avg_pli']:.4f}%")
    print(f"  Difference: {data['s1_avg_util'] - data['s2_avg_util']:.4f}%")
    print()

