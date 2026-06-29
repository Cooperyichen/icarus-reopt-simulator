#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate arrival rate sequence for dual variable validation experiment.

Based on random perturbation sequence step 1 initial values:
- Commodity 0, 1, 3: Keep constant at step 1 values
- Commodity 2: Increase by 50 each step (300 → 350 → 400 → ... → 750)
"""

import sys
import os
import pandas as pd
import numpy as np

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)


def generate_dual_validation_sequence():
    """
    Generate arrival rate sequence for dual variable validation.
    
    Returns:
        pandas.DataFrame: Arrival rate sequence with 10 steps
    """
    # Step 1 initial values from random perturbation sequence
    initial_rates = [540.0, 780.0, 300.0, 780.0]
    
    num_steps = 10
    num_commodities = 4
    
    # Generate sequence
    sequence_data = []
    
    for step_id in range(1, num_steps + 1):
        arrival_rates = initial_rates.copy()
        
        # Commodity 2 increases by 50 each step
        # Step 1: 300, Step 2: 350, ..., Step 10: 750
        arrival_rates[2] = initial_rates[2] + (step_id - 1) * 50
        
        sequence_data.append({
            'Time_Step': step_id,
            'Commodity_0': arrival_rates[0],
            'Commodity_1': arrival_rates[1],
            'Commodity_2': arrival_rates[2],
            'Commodity_3': arrival_rates[3]
        })
    
    df = pd.DataFrame(sequence_data)
    df.set_index('Time_Step', inplace=True)
    
    return df


def main():
    """Main function"""
    print("=" * 80)
    print("Generating Dual Variable Validation Sequence")
    print("=" * 80)
    print()
    
    # Generate sequence
    sequence_df = generate_dual_validation_sequence()
    
    # Print sequence info
    print("Sequence Information:")
    print(f"  Number of steps: {len(sequence_df)}")
    print(f"  Number of commodities: {len(sequence_df.columns)}")
    print()
    print("Step 1 (initial):")
    print(f"  {sequence_df.iloc[0].to_dict()}")
    print()
    print("Step 10 (final):")
    print(f"  {sequence_df.iloc[-1].to_dict()}")
    print()
    print("Commodity 2 progression:")
    for step_id in [1, 5, 10]:
        print(f"  Step {step_id}: {sequence_df.iloc[step_id-1]['Commodity_2']:.1f}")
    print()
    
    # Save to CSV
    output_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_dual_validation.csv')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    sequence_df.to_csv(output_file)
    
    print(f"✓ Sequence saved to: {output_file}")
    print()
    print("=" * 80)
    print("✓ Sequence generation complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()

