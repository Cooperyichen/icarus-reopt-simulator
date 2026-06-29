#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate an increasing arrival rate sequence using exponential distribution.

This script generates a sequence where:
- Step 1 uses the initial arrival rates
- Each subsequent step: arrival_rate[t] = arrival_rate[t-1] + exponential_sample
- Each commodity's increment is independently sampled from an exponential distribution
"""

import pandas as pd
import numpy as np
import os
import sys

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file


def generate_increasing_arrival_rate_sequence(initial_rates, num_steps, exp_scale, seed=None):
    """
    Generates an increasing arrival rate sequence using exponential increments.
    
    Each step: arrival_rate[t] = arrival_rate[t-1] + exp_sample
    where exp_sample is independently sampled from Exponential(scale) for each commodity.
    
    Args:
        initial_rates (list): List of initial arrival rates for each commodity.
        num_steps (int): The total number of time steps in the sequence.
        exp_scale (float): Scale parameter for exponential distribution (mean = scale).
                          Higher scale = larger average increments.
        seed (int, optional): Seed for reproducibility. Defaults to None.
        
    Returns:
        pandas.DataFrame: A DataFrame where each row is a time step and columns are commodities.
    """
    if seed is not None:
        np.random.seed(seed)
    
    num_commodities = len(initial_rates)
    arrival_rate_sequence = []
    
    current_rates = np.array(initial_rates, dtype=float)
    arrival_rate_sequence.append(current_rates.copy())
    
    for _ in range(1, num_steps):
        # Generate independent exponential increments for each commodity
        increments = np.random.exponential(scale=exp_scale, size=num_commodities)
        
        # Apply increments (always increasing)
        current_rates = current_rates + increments
        
        arrival_rate_sequence.append(current_rates.copy())
        
    df_sequence = pd.DataFrame(arrival_rate_sequence, 
                               columns=[f'Commodity_{i}' for i in range(num_commodities)])
    df_sequence.index.name = 'Time_Step'
    df_sequence.index = df_sequence.index + 1  # Start index from 1
    
    return df_sequence


def main():
    print("=" * 80)
    print("Generating Increasing Arrival Rate Sequence")
    print("Using Exponential Distribution for Increments")
    print("=" * 80)
    print()
    
    # Load original sequence to get initial rates
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    
    if os.path.exists(sequence_file):
        df_original = pd.read_csv(sequence_file, index_col=0)
        initial_rates = df_original.iloc[0].values
        print(f"Loaded initial rates from existing sequence:")
    else:
        # Fallback: use scaled rates from config
        config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
        config = load_yaml_file(config_file)
        original_rates = config['fixed_demand']['arrival_rate']
        scale_factor = 0.6
        initial_rates = np.array(original_rates) * scale_factor
        print(f"Using initial rates from config (scaled by {scale_factor}):")
    
    print(f"  Initial rates: {initial_rates}")
    print()
    
    # Parameters for sequence generation
    exp_scale = 50.0  # Exponential scale parameter (mean = 50 packets/s per step)
    num_steps = 10
    seed = 42  # For reproducibility
    
    print(f"Generation parameters:")
    print(f"  Number of steps: {num_steps}")
    print(f"  Exponential scale (mean increment): {exp_scale} packets/s")
    print(f"  Distribution: Exponential(scale={exp_scale})")
    print(f"  Note: Mean increment per step = {exp_scale} packets/s")
    print(f"  Random seed: {seed}")
    print()
    
    # Generate the sequence
    df_sequence = generate_increasing_arrival_rate_sequence(
        initial_rates, num_steps, exp_scale, seed
    )
    
    print("=" * 80)
    print("Generated Arrival Rate Sequence")
    print("=" * 80)
    print()
    print(df_sequence.to_string(float_format="%.6f"))
    print()
    
    # Save to CSV (overwrite existing file)
    output_csv_path = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
    df_sequence.to_csv(output_csv_path)
    print(f"Sequence saved to: {output_csv_path}")
    
    print("\n" + "=" * 80)
    print("Sequence Statistics")
    print("=" * 80)
    print()
    
    num_commodities = len(initial_rates)
    for i in range(num_commodities):
        col_name = f'Commodity_{i}'
        rates = df_sequence[col_name].values
        
        # Calculate increments
        increments = np.diff(rates)
        
        print(f"Commodity {i}:")
        print(f"  Initial (Step 1): {rates[0]:.2f} packets/s")
        print(f"  Final (Step 10): {rates[-1]:.2f} packets/s")
        print(f"  Total increase: {rates[-1] - rates[0]:.2f} packets/s")
        print(f"  Average increment: {increments.mean():.2f} packets/s (expected: ~{exp_scale})")
        print(f"  Increment std: {increments.std():.2f} packets/s (expected: ~{exp_scale})")
        print(f"  Min increment: {increments.min():.2f} packets/s")
        print(f"  Max increment: {increments.max():.2f} packets/s")
        print()
    
    print("\n" + "=" * 80)
    print("Step-to-Step Increments (arrival_rate[t] - arrival_rate[t-1])")
    print("Should follow Exponential(scale={}) distribution".format(exp_scale))
    print("=" * 80)
    print()
    
    # Calculate increments for each commodity
    for i in range(num_commodities):
        col_name = f'Commodity_{i}'
        increments = df_sequence[col_name].diff().dropna()
        
        print(f"Commodity {i} increments:")
        for step_idx, inc in enumerate(increments, start=2):
            print(f"  Step {step_idx-1} -> Step {step_idx}: {inc:+.2f} packets/s")
        print()
    
    print("=" * 80)
    print(f"New sequence saved to: {output_csv_path}")
    print("Sequence is monotonically increasing (each step adds exponential increment)")
    print("Ready for multi-step comparison experiment")
    print("=" * 80)
    print()


if __name__ == '__main__':
    main()

