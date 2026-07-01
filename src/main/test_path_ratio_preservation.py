#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test path ratio preservation by:
1. Running initial simulation with original arrival rates
2. Extracting path flow ratios from mcfp_results
3. Applying random perturbations to arrival rates
4. Applying extracted path ratios to new arrival rates
5. Running second simulation with perturbed arrival rates
6. Comparing path ratios between two scenarios
"""

import sys
import os
import pandas as pd
import numpy as np
import yaml
from pathlib import Path

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
import main.main as main_module


def extract_path_ratios_from_csv(csv_file_path):
    """
    Extract path flow ratios from mcfp_results CSV file.
    
    Args:
        csv_file_path: Path to mcfp_results CSV file
        
    Returns:
        dict: {commodity_id: {path: ratio}}
    """
    df = pd.read_csv(csv_file_path)
    
    ratios_by_commodity = {}
    
    for commodity_id in df['id_flow'].unique():
        commodity_df = df[df['id_flow'] == commodity_id]
        total_flow = commodity_df['Arrival Rate'].sum()
        
        path_ratios = {}
        for _, row in commodity_df.iterrows():
            path = row['Path']
            flow = row['Arrival Rate']
            if total_flow > 0:
                path_ratios[path] = flow / total_flow
            else:
                path_ratios[path] = 0.0
        
        ratios_by_commodity[int(commodity_id)] = path_ratios
    
    return ratios_by_commodity


def apply_path_ratios_to_demand(baseline_ratios, new_demands, original_mcfp_df):
    """
    Apply path ratios to new commodity demands.
    
    Args:
        baseline_ratios: dict {commodity_id: {path: ratio}}
        new_demands: list of new arrival rates for each commodity
        original_mcfp_df: DataFrame from original mcfp_results (for path info)
        
    Returns:
        DataFrame: New demand matrix with applied ratios
    """
    new_flow_data = []
    
    for commodity_id in sorted(baseline_ratios.keys()):
        if commodity_id >= len(new_demands):
            continue
            
        new_demand = new_demands[commodity_id]
        path_ratios = baseline_ratios[commodity_id]
        
        # Get original commodity info from mcfp_df
        commodity_df = original_mcfp_df[original_mcfp_df['id_flow'] == commodity_id]
        if len(commodity_df) == 0:
            continue
            
        source = commodity_df.iloc[0]['Source']
        destination = commodity_df.iloc[0]['Destination']
        priority = commodity_df.iloc[0]['Priority']
        
        # Apply ratios to each path
        for path, ratio in path_ratios.items():
            new_flow = new_demand * ratio
            new_flow_data.append({
                'id_flow': commodity_id,
                'Source': source,
                'Destination': destination,
                'Arrival Rate': new_flow,
                'Path': path,
                'Priority': priority
            })
    
    new_df = pd.DataFrame(new_flow_data)
    return new_df


def generate_perturbed_arrival_rates(original_rates, perturbation_range=0.2, seed=42):
    """
    Generate perturbed arrival rates by adding random noise.
    
    Args:
        original_rates: list of original arrival rates
        perturbation_range: relative perturbation range (e.g., 0.2 = ±20%)
        seed: random seed for reproducibility
        
    Returns:
        list: Perturbed arrival rates
    """
    np.random.seed(seed)
    perturbed_rates = []
    
    for rate in original_rates:
        # Generate random perturbation in [-perturbation_range, +perturbation_range]
        perturbation = np.random.uniform(-perturbation_range, perturbation_range)
        new_rate = rate * (1 + perturbation)
        # Ensure positive
        new_rate = max(new_rate, 1.0)
        perturbed_rates.append(new_rate)
    
    return perturbed_rates


def compare_path_ratios(ratios1, ratios2, tolerance=1e-6):
    """
    Compare two path ratio dictionaries.
    
    Args:
        ratios1: First path ratio dict {commodity_id: {path: ratio}}
        ratios2: Second path ratio dict {commodity_id: {path: ratio}}
        tolerance: Tolerance for floating point comparison
        
    Returns:
        dict: Comparison results
    """
    comparison_results = {
        'commodities_match': [],
        'all_match': True,
        'differences': {}
    }
    
    # Check if same commodities
    commodities1 = set(ratios1.keys())
    commodities2 = set(ratios2.keys())
    
    if commodities1 != commodities2:
        comparison_results['all_match'] = False
        comparison_results['error'] = f"Commodity mismatch: {commodities1} vs {commodities2}"
        return comparison_results
    
    # Compare ratios for each commodity
    for commodity_id in commodities1:
        ratios1_commodity = ratios1[commodity_id]
        ratios2_commodity = ratios2[commodity_id]
        
        # Check if same paths
        paths1 = set(ratios1_commodity.keys())
        paths2 = set(ratios2_commodity.keys())
        
        if paths1 != paths2:
            comparison_results['all_match'] = False
            comparison_results['differences'][commodity_id] = {
                'error': f"Path mismatch: {paths1} vs {paths2}"
            }
            continue
        
        # Compare ratios
        commodity_match = True
        path_differences = {}
        
        for path in paths1:
            ratio1 = ratios1_commodity[path]
            ratio2 = ratios2_commodity[path]
            diff = abs(ratio1 - ratio2)
            
            if diff > tolerance:
                commodity_match = False
                path_differences[path] = {
                    'ratio1': ratio1,
                    'ratio2': ratio2,
                    'difference': diff
                }
        
        comparison_results['commodities_match'].append({
            'commodity_id': commodity_id,
            'match': commodity_match,
            'path_differences': path_differences
        })
        
        if not commodity_match:
            comparison_results['all_match'] = False
            comparison_results['differences'][commodity_id] = path_differences
    
    return comparison_results


def main():
    """Main function to test path ratio preservation."""
    
    print("=" * 80)
    print("Path Ratio Preservation Test")
    print("=" * 80)
    print()
    
    # Configuration
    scenario_name = "80_lambda_our_model_2c"
    yaml_file = os.path.join(src_dir, 'data', f'{scenario_name}.yaml')
    results_base_dir = os.path.join(src_dir, 'results')
    run_id = 1
    
    # Load configuration
    print("Loading configuration...")
    config = load_yaml_file(yaml_file)
    original_rates_raw = config['fixed_demand']['arrival_rate']
    num_commodities = config['optimization']['num_commodities']
    
    # Reduce arrival rates to ensure feasibility (scale down by factor)
    # Current rates might be too high for 4 commodities
    scale_factor = 0.6  # Reduce by 40% to ensure feasible optimization
    original_rates = [rate * scale_factor for rate in original_rates_raw]
    config['fixed_demand']['arrival_rate'] = original_rates
    
    print(f"Scenario: {scenario_name}")
    print(f"Number of commodities: {num_commodities}")
    print(f"Original arrival rates (raw): {original_rates_raw}")
    print(f"Original arrival rates (scaled): {original_rates}")
    print(f"Scale factor: {scale_factor}")
    print()
    
    # Step 1: Run initial simulation
    print("=" * 80)
    print("Step 1: Running initial simulation...")
    print("=" * 80)
    
    result_dir_1 = os.path.join(results_base_dir, scenario_name, f"run_{run_id}")
    os.makedirs(result_dir_1, exist_ok=True)
    
    # Set random seed for reproducibility
    np.random.seed(run_id - 1)
    
    all_flows_1, switches_1, blocked_flows_1 = main_module.run_simulation_scenario(
        config, result_dir_1, run_id - 1
    )
    
    # Read mcfp_results from first simulation
    mcfp_file_1 = os.path.join(result_dir_1, f"mcfp_results_flows_{num_commodities}_commodities.csv")
    
    if not os.path.exists(mcfp_file_1):
        print(f"ERROR: MCFP results file not found: {mcfp_file_1}")
        return
    
    print(f"✓ Initial simulation completed. Results saved to: {mcfp_file_1}")
    print()
    
    # Step 2: Extract path ratios from first simulation
    print("=" * 80)
    print("Step 2: Extracting path flow ratios...")
    print("=" * 80)
    
    mcfp_df_1 = pd.read_csv(mcfp_file_1)
    baseline_ratios = extract_path_ratios_from_csv(mcfp_file_1)
    
    print(f"Extracted path ratios for {len(baseline_ratios)} commodities:")
    for commodity_id, path_ratios in sorted(baseline_ratios.items()):
        total_ratio = sum(path_ratios.values())
        print(f"  Commodity {commodity_id}: {len(path_ratios)} paths, ratio sum = {total_ratio:.6f}")
        for path, ratio in sorted(path_ratios.items(), key=lambda x: x[1], reverse=True)[:3]:  # Show top 3
            print(f"    Path: {path[:60]}... Ratio: {ratio:.6f}")
    print()
    
    # Step 3: Generate perturbed arrival rates
    print("=" * 80)
    print("Step 3: Generating perturbed arrival rates...")
    print("=" * 80)
    
    perturbed_rates = generate_perturbed_arrival_rates(original_rates, perturbation_range=0.2, seed=42)
    
    print(f"Original rates: {[f'{r:.2f}' for r in original_rates]}")
    print(f"Perturbed rates: {[f'{r:.2f}' for r in perturbed_rates]}")
    print()
    
    # Step 4: Create new configuration with perturbed rates
    print("=" * 80)
    print("Step 4: Creating new configuration with perturbed rates...")
    print("=" * 80)
    
    config_2 = config.copy()
    config_2['fixed_demand'] = config['fixed_demand'].copy()
    config_2['fixed_demand']['arrival_rate'] = perturbed_rates
    config_2['scenario_name'] = f"{scenario_name}_perturbed"
    
    # Apply path ratios to create new demand matrix
    new_demand_matrix = apply_path_ratios_to_demand(
        baseline_ratios, perturbed_rates, mcfp_df_1
    )
    
    print(f"✓ Created new demand matrix with {len(new_demand_matrix)} paths")
    print()
    
    # Step 5: Run second simulation with perturbed rates (using preserved path ratios)
    print("=" * 80)
    print("Step 5: Running second simulation with perturbed rates...")
    print("=" * 80)
    print("⚠️  IMPORTANT: Using preserved path ratios from Scenario 1!")
    print("   The optimizer will NOT be called in Scenario 2.")
    print(f"   New demand matrix has {len(new_demand_matrix)} paths with preserved ratios.")
    print()
    
    result_dir_2 = os.path.join(results_base_dir, config_2['scenario_name'], f"run_{run_id}")
    os.makedirs(result_dir_2, exist_ok=True)
    
    np.random.seed(run_id - 1)  # Same seed for reproducibility
    
    # Run simulation with precomputed demand matrix (path ratio preservation)
    # This will skip the optimizer and use the new_demand_matrix directly
    all_flows_2, switches_2, blocked_flows_2 = main_module.run_simulation_scenario(
        config_2, result_dir_2, run_id - 1, precomputed_demand_matrix=new_demand_matrix
    )
    
    # Read mcfp_results from second simulation
    mcfp_file_2 = os.path.join(result_dir_2, f"mcfp_results_flows_{num_commodities}_commodities.csv")
    
    if not os.path.exists(mcfp_file_2):
        print(f"ERROR: MCFP results file not found: {mcfp_file_2}")
        return
    
    print(f"✓ Second simulation completed. Results saved to: {mcfp_file_2}")
    print()
    
    # Step 6: Extract path ratios from second simulation
    print("=" * 80)
    print("Step 6: Extracting path flow ratios from second simulation...")
    print("=" * 80)
    
    ratios_2 = extract_path_ratios_from_csv(mcfp_file_2)
    
    print(f"Extracted path ratios for {len(ratios_2)} commodities:")
    for commodity_id, path_ratios in sorted(ratios_2.items()):
        total_ratio = sum(path_ratios.values())
        print(f"  Commodity {commodity_id}: {len(path_ratios)} paths, ratio sum = {total_ratio:.6f}")
    print()
    
    # Step 7: Compare path ratios
    print("=" * 80)
    print("Step 7: Comparing path ratios between two scenarios...")
    print("=" * 80)
    
    comparison = compare_path_ratios(baseline_ratios, ratios_2, tolerance=1e-6)
    
    if comparison['all_match']:
        print("✓ SUCCESS: Path ratios are identical between two scenarios!")
    else:
        print("✗ FAILURE: Path ratios differ between two scenarios.")
        print("\nDifferences:")
        for commodity_id, differences in comparison['differences'].items():
            print(f"\n  Commodity {commodity_id}:")
            if 'error' in differences:
                print(f"    Error: {differences['error']}")
            else:
                for path, diff_info in differences.items():
                    print(f"    Path: {path[:60]}...")
                    print(f"      Ratio 1: {diff_info['ratio1']:.6f}")
                    print(f"      Ratio 2: {diff_info['ratio2']:.6f}")
                    print(f"      Difference: {diff_info['difference']:.6f}")
    
    print()
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Scenario 1: {scenario_name}")
    print(f"  Arrival rates: {[f'{r:.2f}' for r in original_rates]}")
    print(f"  Result file: {mcfp_file_1}")
    print()
    print(f"Scenario 2: {config_2['scenario_name']}")
    print(f"  Arrival rates: {[f'{r:.2f}' for r in perturbed_rates]}")
    print(f"  Result file: {mcfp_file_2}")
    print()
    print(f"Path ratio comparison: {'MATCH' if comparison['all_match'] else 'DIFFER'}")
    print("=" * 80)
    
    return {
        'baseline_ratios': baseline_ratios,
        'ratios_2': ratios_2,
        'comparison': comparison,
        'original_rates': original_rates,
        'perturbed_rates': perturbed_rates,
        'mcfp_file_1': mcfp_file_1,
        'mcfp_file_2': mcfp_file_2
    }


if __name__ == '__main__':
    main()

