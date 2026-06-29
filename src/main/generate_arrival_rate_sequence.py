#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate arrival rate sequence with independent Gaussian perturbations for each commodity.

Each commodity's arrival rate evolves independently:
  arrival_rate[t+1] = arrival_rate[t] + N(0, 50²)

Where N(0, 50²) is a normal distribution with mean 0 and standard deviation 50.
"""

import numpy as np
import pandas as pd
import sys
import os

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file


def generate_arrival_rate_sequence(initial_rates, num_steps=10, std_dev=50, seed=42):
    """
    Generate a sequence of arrival rates with independent Gaussian perturbations.

    Args:
        initial_rates: List of initial arrival rates for each commodity
        num_steps: Number of time steps (default: 10)
        std_dev: Standard deviation of the Gaussian perturbation (default: 50)
        seed: Random seed for reproducibility (default: 42)

    Returns:
        numpy.ndarray: Array of shape (num_steps, num_commodities) containing arrival rate sequence
    """
    np.random.seed(seed)

    num_commodities = len(initial_rates)
    arrival_rate_sequence = np.zeros((num_steps, num_commodities))

    # Initialize first step with initial rates
    arrival_rate_sequence[0] = np.array(initial_rates)

    # Generate subsequent steps
    for t in range(1, num_steps):
        # Generate independent perturbations for each commodity
        perturbations = np.random.normal(0, std_dev, num_commodities)

        # Apply perturbations to previous step
        arrival_rate_sequence[t] = arrival_rate_sequence[t - 1] + perturbations

        # Ensure non-negative arrival rates (clip to minimum of 1.0)
        arrival_rate_sequence[t] = np.maximum(arrival_rate_sequence[t], 1.0)

    return arrival_rate_sequence


def generate_arrival_rate_sequence_uniform(initial_rates, num_steps=50, variance=2500, seed=42):
    """
    Generate a sequence of arrival rates with independent zero-mean uniform perturbations.

    Variance matching rule:
      For U(-a, a), Var = a^2 / 3
      Given target variance v, choose a = sqrt(3v)

    Args:
        initial_rates: List of initial arrival rates for each commodity
        num_steps: Number of time steps (default: 50)
        variance: Target perturbation variance per step (default: 2500)
        seed: Random seed for reproducibility (default: 42)

    Returns:
        numpy.ndarray: Array of shape (num_steps, num_commodities) containing arrival rate sequence
    """
    np.random.seed(seed)

    num_commodities = len(initial_rates)
    arrival_rate_sequence = np.zeros((num_steps, num_commodities))
    arrival_rate_sequence[0] = np.array(initial_rates)

    a = np.sqrt(3.0 * float(variance))

    for t in range(1, num_steps):
        perturbations = np.random.uniform(-a, a, num_commodities)
        arrival_rate_sequence[t] = arrival_rate_sequence[t - 1] + perturbations
        arrival_rate_sequence[t] = np.maximum(arrival_rate_sequence[t], 1.0)

    return arrival_rate_sequence


def main():
    """Main function to generate arrival rate sequence."""

    # Load configuration
    scenario_name = "80_lambda_our_model_2c"
    yaml_file = os.path.join(src_dir, 'data', f'{scenario_name}.yaml')

    config = load_yaml_file(yaml_file)
    initial_rates = config['fixed_demand']['arrival_rate']
    num_commodities = config['optimization']['num_commodities']

    print("=" * 80)
    print("Arrival Rate Sequence Generation")
    print("=" * 80)
    print()
    print(f"Initial arrival rates: {initial_rates} packets/s")
    print(f"Number of commodities: {num_commodities}")
    print(f"Perturbation: N(0, 50²) - Standard deviation = 50 packets/s")
    print(f"Number of time steps: 10")
    print()

    # Generate arrival rate sequence
    arrival_rate_sequence = generate_arrival_rate_sequence(
        initial_rates=initial_rates,
        num_steps=10,
        std_dev=50,
        seed=42
    )

    # Create DataFrame for better visualization
    columns = [f'Commodity_{i}' for i in range(num_commodities)]
    df = pd.DataFrame(arrival_rate_sequence, columns=columns)
    df.index.name = 'Time_Step'
    df.index = df.index + 1  # Start from step 1

    # Display sequence
    print("=" * 80)
    print("Generated Arrival Rate Sequence")
    print("=" * 80)
    print()
    print(df.to_string())
    print()

    # Calculate statistics
    print("=" * 80)
    print("Sequence Statistics")
    print("=" * 80)
    print()

    for i in range(num_commodities):
        col = f'Commodity_{i}'
        rates = df[col].values
        print(f"Commodity {i}:")
        print(f"  Initial: {rates[0]:.2f} packets/s")
        print(f"  Final: {rates[-1]:.2f} packets/s")
        print(f"  Min: {rates.min():.2f} packets/s")
        print(f"  Max: {rates.max():.2f} packets/s")
        print(f"  Mean: {rates.mean():.2f} packets/s")
        print(f"  Std: {rates.std():.2f} packets/s")
        print(f"  Change: {((rates[-1] / rates[0] - 1) * 100):+.2f}%")
        print()

    # Calculate step-to-step changes
    print("=" * 80)
    print("Step-to-Step Changes (arrival_rate[t] - arrival_rate[t-1])")
    print("=" * 80)
    print()

    step_changes = np.diff(arrival_rate_sequence, axis=0)
    change_df = pd.DataFrame(step_changes, columns=columns)
    change_df.index.name = 'Transition'
    change_df.index = [f"Step_{i} -> Step_{i+1}" for i in range(1, len(change_df) + 1)]

    print(change_df.to_string())
    print()

    # Verify perturbation statistics
    print("=" * 80)
    print("Perturbation Verification (should be ~N(0, 50²))")
    print("=" * 80)
    print()

    for i in range(num_commodities):
        changes = step_changes[:, i]
        print(f"Commodity {i}:")
        print(f"  Mean of perturbations: {changes.mean():.2f} (expected: ~0)")
        print(f"  Std of perturbations: {changes.std():.2f} (expected: ~50)")
        print()

    # Save to CSV
    output_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=True)

    print("=" * 80)
    print(f"Sequence saved to: {output_file}")
    print("=" * 80)

    # Also save in YAML-friendly format (for step_demands)
    print()
    print("YAML format for step_demands configuration:")
    print("-" * 80)
    print("step_demands:")
    print("  - null  # Step 1 uses fixed_demand arrival_rate")
    for t in range(1, 10):
        rates = arrival_rate_sequence[t].tolist()
        rates_str = ', '.join([f'{r:.2f}' for r in rates])
        print(f"  - [{rates_str}]  # Step {t+1}")
    print("-" * 80)

    return arrival_rate_sequence, df


if __name__ == '__main__':
    sequence, df = main()
