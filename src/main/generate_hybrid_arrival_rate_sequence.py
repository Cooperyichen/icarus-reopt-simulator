#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate a hybrid arrival rate sequence with mixed perturbation methods.

This script generates a sequence where:
- Commodities 0-1: Normal distribution perturbation (std_dev=50)
- Commodities 2-3: Exponential distribution increment (scale=50)
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


def generate_hybrid_arrival_rate_sequence(initial_rates, num_steps, normal_std_dev, exp_scale, normal_commodities=[0, 1], exp_commodities=[2, 3], seed=None):
    """
    Generates a hybrid arrival rate sequence with mixed perturbation methods.
    
    For commodities in normal_commodities:
        arrival_rate[t] = arrival_rate[t-1] + N(0, std_dev²)
    
    For commodities in exp_commodities:
        arrival_rate[t] = arrival_rate[t-1] + Exponential(scale)
    
    Args:
        initial_rates (list): List of initial arrival rates for each commodity.
        num_steps (int): The total number of time steps in the sequence.
        normal_std_dev (float): Standard deviation for normal distribution perturbation.
        exp_scale (float): Scale parameter for exponential distribution (mean = scale).
        normal_commodities (list): List of commodity indices to use normal perturbation. Default: [0, 1]
        exp_commodities (list): List of commodity indices to use exponential increment. Default: [2, 3]
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
        increments = np.zeros(num_commodities)
        
        # Apply normal distribution perturbation to specified commodities
        for comm_idx in normal_commodities:
            if comm_idx < num_commodities:
                increments[comm_idx] = np.random.normal(0, normal_std_dev)
        
        # Apply exponential increment to specified commodities
        for comm_idx in exp_commodities:
            if comm_idx < num_commodities:
                increments[comm_idx] = np.random.exponential(scale=exp_scale)
        
        # Apply increments
        current_rates = current_rates + increments
        
        # Ensure rates are non-negative (especially for normal perturbation)
        current_rates = np.maximum(current_rates, 1.0)
        
        arrival_rate_sequence.append(current_rates.copy())
        
    df_sequence = pd.DataFrame(arrival_rate_sequence, 
                               columns=[f'Commodity_{i}' for i in range(num_commodities)])
    df_sequence.index.name = 'Time_Step'
    df_sequence.index = df_sequence.index + 1  # Start index from 1
    
    return df_sequence


def main():
    print("=" * 80)
    print("Generating Hybrid Arrival Rate Sequence")
    print("Commodities 0-1: Normal Distribution (std_dev=50)")
    print("Commodities 2-3: Exponential Increment (scale=50)")
    print("=" * 80)
    print()
    
    # Load original sequence to get initial rates
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    
    if os.path.exists(sequence_file):
        df_original = pd.read_csv(sequence_file, index_col=0)
        # Use Step 1 from increasing sequence (which has the scaled initial rates)
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
    normal_std_dev = 50.0  # Normal distribution standard deviation
    exp_scale = 50.0  # Exponential scale parameter (mean = 50 packets/s per step)
    normal_commodities = [0, 1]  # Commodities 0-1 use normal perturbation
    exp_commodities = [2, 3]  # Commodities 2-3 use exponential increment
    num_steps = 10
    seed = 42  # For reproducibility
    
    print(f"Generation parameters:")
    print(f"  Number of steps: {num_steps}")
    print(f"  Normal perturbation (Commodities {normal_commodities}):")
    print(f"    Distribution: N(0, {normal_std_dev}²)")
    print(f"    Standard deviation: {normal_std_dev} packets/s")
    print(f"  Exponential increment (Commodities {exp_commodities}):")
    print(f"    Distribution: Exponential(scale={exp_scale})")
    print(f"    Mean increment: {exp_scale} packets/s")
    print(f"  Random seed: {seed}")
    print()
    
    # Generate the sequence
    df_sequence = generate_hybrid_arrival_rate_sequence(
        initial_rates, num_steps, normal_std_dev, exp_scale,
        normal_commodities, exp_commodities, seed
    )
    
    print("=" * 80)
    print("Generated Hybrid Arrival Rate Sequence")
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
        
        if i in normal_commodities:
            method = "Normal Perturbation"
            expected_mean = 0.0
            expected_std = normal_std_dev
        else:
            method = "Exponential Increment"
            expected_mean = exp_scale
            expected_std = exp_scale
        
        print(f"Commodity {i} ({method}):")
        print(f"  Initial (Step 1): {rates[0]:.2f} packets/s")
        print(f"  Final (Step 10): {rates[-1]:.2f} packets/s")
        print(f"  Total change: {rates[-1] - rates[0]:+.2f} packets/s")
        print(f"  Average increment: {increments.mean():.2f} packets/s (expected: ~{expected_mean})")
        print(f"  Increment std: {increments.std():.2f} packets/s (expected: ~{expected_std})")
        print(f"  Min increment: {increments.min():.2f} packets/s")
        print(f"  Max increment: {increments.max():.2f} packets/s")
        print()
    
    print("\n" + "=" * 80)
    print("Step-to-Step Changes (arrival_rate[t] - arrival_rate[t-1])")
    print("=" * 80)
    print()
    
    # Show increments for each commodity
    for i in range(num_commodities):
        col_name = f'Commodity_{i}'
        increments = df_sequence[col_name].diff().dropna()
        
        if i in normal_commodities:
            method = "Normal Perturbation"
        else:
            method = "Exponential Increment"
        
        print(f"Commodity {i} ({method}):")
        for step_idx, inc in enumerate(increments, start=2):
            print(f"  Step {step_idx-1} -> Step {step_idx}: {inc:+.2f} packets/s")
        print()
    
    print("=" * 80)
    print(f"New hybrid sequence saved to: {output_csv_path}")
    print("Ready for multi-step comparison experiment")
    print("=" * 80)
    print()


if __name__ == '__main__':
    main()

