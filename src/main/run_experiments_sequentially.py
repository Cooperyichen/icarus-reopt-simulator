#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sequentially run three experiments with different arrival rate sequences.
"""

import sys
import os
import shutil

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from main.multi_step_comparison_experiment import main as run_experiment

results_dir = os.path.join(src_dir, 'results')
standard_file = os.path.join(results_dir, 'arrival_rate_sequence_10_steps.csv')

experiments = [
    {
        'name': 'Random Perturbation',
        'file': os.path.join(results_dir, 'arrival_rate_sequence_random.csv')
    },
    {
        'name': 'Increasing Sequence',
        'file': os.path.join(results_dir, 'arrival_rate_sequence_increasing.csv')
    },
    {
        'name': 'Hybrid Sequence',
        'file': os.path.join(results_dir, 'arrival_rate_sequence_hybrid.csv')
    }
]

print("=" * 80)
print("Running Three Experiments Sequentially")
print("Objective: minimize_max_link_utilization")
print("=" * 80)
print()

for i, exp in enumerate(experiments, 1):
    print(f"\n{'='*80}")
    print(f"Experiment {i}/3: {exp['name']}")
    print(f"{'='*80}\n")
    
    if not os.path.exists(exp['file']):
        print(f"✗ Sequence file not found: {exp['file']}")
        continue
    
    # Copy sequence file
    shutil.copy(exp['file'], standard_file)
    print(f"✓ Using sequence: {exp['file']}\n")
    
    # Run experiment
    try:
        results = run_experiment()
        print(f"\n✓ Experiment {i}/3 completed!\n")
    except Exception as e:
        print(f"\n✗ Experiment {i}/3 failed: {e}\n")

print("=" * 80)
print("All experiments completed!")
print("=" * 80)

