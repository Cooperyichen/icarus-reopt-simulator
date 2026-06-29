#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced dual variable analysis with capacity constraint dual variables.

This script:
1. Extracts all dual variables (demand + capacity constraints)
2. Finds the edge with maximum utilization
3. Builds enhanced linear extrapolation formula including capacity constraint duals
4. Compares predictions with theoretical values
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
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from main.multi_step_comparison_experiment import (
    parse_path,
    calculate_max_link_utilization
)


def find_max_utilization_edge(mcfp_df, config):
    """
    Find the edge with maximum utilization from mcfp results.
    
    Args:
        mcfp_df: DataFrame from mcfp_results CSV
        config: Configuration dictionary
        
    Returns:
        tuple: ((u, v), max_utilization) - edge with max utilization and its utilization value
    """
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    generation_finish_time = config['simulation']['generation_finish_time']  # ms
    effective_time = generation_finish_time / 1000.0  # Convert ms to seconds
    
    interlink_traffic = {}
    
    # Calculate traffic on each interlink
    for idx, row in mcfp_df.iterrows():
        arrival_rate = row['Arrival Rate']  # packets/s
        path = row['Path']
        
        if pd.isna(path):
            continue
        
        # Parse path to get interlinks
        interlinks = parse_path(path)
        
        # Calculate bits transmitted on each interlink
        bits_transmitted = arrival_rate * packet_size * 8 * effective_time
        
        for interlink in interlinks:
            if interlink not in interlink_traffic:
                interlink_traffic[interlink] = 0
            interlink_traffic[interlink] += bits_transmitted
    
    # Calculate utilization for each interlink
    max_utilization = 0.0
    max_edge = None
    
    for interlink, bits in interlink_traffic.items():
        bit_rate = bits / effective_time  # bits/s
        utilization = (bit_rate / interlink_capacity) * 100
        if utilization > max_utilization:
            max_utilization = utilization
            max_edge = interlink
    
    return max_edge, max_utilization


def check_max_edge_stability(sequence_df, config, result_dir_base):
    """
    Check if the maximum utilization edge changes across all steps.
    
    Args:
        sequence_df: DataFrame with arrival rate sequence
        config: Configuration dictionary
        result_dir_base: Base directory for results
        
    Returns:
        dict: Analysis results including edge stability information
    """
    print("=" * 80)
    print("Checking Maximum Utilization Edge Stability")
    print("=" * 80)
    print()
    
    num_steps = len(sequence_df)
    max_edges_by_step = []
    
    # Load results for each step
    result_dir = os.path.join(result_dir_base, 'strategy_dual_validation')
    
    for step_id in range(1, num_steps + 1):
        step_dir = os.path.join(result_dir, f'step_{step_id}')
        mcfp_file = os.path.join(step_dir, 'mcfp_results_flows_4_commodities.csv')
        
        if not os.path.exists(mcfp_file):
            print(f"⚠️  Step {step_id}: mcfp file not found")
            continue
        
        mcfp_df = pd.read_csv(mcfp_file)
        max_edge, max_util = find_max_utilization_edge(mcfp_df, config)
        
        if max_edge is not None:
            max_edges_by_step.append({
                'step_id': step_id,
                'max_edge': max_edge,
                'max_utilization': max_util
            })
            print(f"Step {step_id}: Max edge = {max_edge}, Utilization = {max_util:.4f}%")
    
    # Check if edge is stable
    if len(max_edges_by_step) > 0:
        first_edge = max_edges_by_step[0]['max_edge']
        all_same = all(step['max_edge'] == first_edge for step in max_edges_by_step)
        
        print()
        if all_same:
            print(f"✓ Maximum utilization edge is stable: {first_edge}")
        else:
            print("⚠️  Maximum utilization edge changes across steps:")
            for step in max_edges_by_step:
                print(f"  Step {step['step_id']}: {step['max_edge']}")
        
        return {
            'stable': all_same,
            'max_edge': first_edge if all_same else None,
            'edges_by_step': max_edges_by_step
        }
    else:
        print("✗ No valid steps found")
        return None


def extract_all_dual_variables(config, arrival_rates):
    """
    Extract all dual variables (demand + capacity) from optimization.
    
    Args:
        config: Configuration dictionary
        arrival_rates: List of arrival rates for each commodity
        
    Returns:
        dict: {
            'demand_duals': {commodity_id: dual_value},
            'capacity_duals': {(u, v): dual_value},
            'max_edge': (u, v),
            'max_edge_capacity_dual': float,
            'max_link_util': float,
            'mcfp_df': DataFrame
        }
    """
    step_config = config.copy()
    step_config['fixed_demand'] = config['fixed_demand'].copy()
    step_config['fixed_demand']['arrival_rate'] = arrival_rates
    
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=step_config, width=width, height=height)
    
    num_commodities = len(arrival_rates)
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    
    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']
    
    result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    # Extract demand dual variables
    demand_duals = {}
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        demand_duals = result_df.attrs['dual_variables']
    
    # Extract capacity dual variables
    capacity_duals = {}
    if hasattr(result_df, 'attrs') and 'capacity_dual_variables' in result_df.attrs:
        capacity_duals = result_df.attrs['capacity_dual_variables']
    
    # Find max utilization edge
    # Convert result_df to format expected by find_max_utilization_edge
    # We need to create a DataFrame with 'Arrival Rate' and 'Path' columns
    mcfp_df = result_df.copy()
    if 'Path' not in mcfp_df.columns:
        # If Path column doesn't exist, we need to reconstruct it
        # For now, we'll use the result_df as is if it has the right structure
        pass
    
    max_edge, max_util = find_max_utilization_edge(mcfp_df, step_config)
    
    # Try to get capacity dual for max edge
    # Note: Edge format might be different (tuple vs string)
    max_edge_capacity_dual = None
    if max_edge:
        # Try different formats
        if max_edge in capacity_duals:
            max_edge_capacity_dual = capacity_duals[max_edge]
        else:
            # Try converting edge to string format
            edge_str = f"('OBPModule{max_edge[0]}', 'OBPModule{max_edge[1]}')"
            for edge_key, dual_val in capacity_duals.items():
                if isinstance(edge_key, tuple) and edge_key == max_edge:
                    max_edge_capacity_dual = dual_val
                    break
                elif isinstance(edge_key, str) and str(max_edge) in edge_key:
                    max_edge_capacity_dual = dual_val
                    break
    
    return {
        'demand_duals': demand_duals,
        'capacity_duals': capacity_duals,
        'max_edge': max_edge,
        'max_edge_capacity_dual': max_edge_capacity_dual,
        'max_link_util': max_util,
        'mcfp_df': mcfp_df
    }


def calculate_edge_flow_change(mcfp_df_step1, edge, demand_changes, config):
    """
    Calculate the change in flow through edge e when demands change.
    
    Args:
        mcfp_df_step1: DataFrame from Step 1 mcfp results
        edge: Edge tuple (u, v)
        demand_changes: dict {commodity_id: (new_demand - old_demand)} in packets/s
        config: Configuration dictionary
        
    Returns:
        float: Δflow_e_bits (bits/s) - total flow change through edge e
    """
    packet_size = config['simulation']['avg_packet_size']  # bytes
    
    # Extract path ratios from Step 1
    # Group by commodity and path
    path_flows = {}  # {(commodity_id, path): flow_in_packets_per_sec}
    commodity_demands_step1 = {}  # {commodity_id: total_demand}
    
    for idx, row in mcfp_df_step1.iterrows():
        commodity_id = row['id_flow']
        path = row['Path']
        flow = row['Arrival Rate']  # packets/s
        
        if pd.isna(path):
            continue
        
        key = (commodity_id, path)
        if key not in path_flows:
            path_flows[key] = 0.0
        path_flows[key] += flow
        
        if commodity_id not in commodity_demands_step1:
            commodity_demands_step1[commodity_id] = 0.0
        commodity_demands_step1[commodity_id] += flow
    
    # Calculate path ratios
    path_ratios = {}  # {(commodity_id, path): ratio}
    for (commodity_id, path), flow in path_flows.items():
        if commodity_id in commodity_demands_step1 and commodity_demands_step1[commodity_id] > 0:
            ratio = flow / commodity_demands_step1[commodity_id]
            path_ratios[(commodity_id, path)] = ratio
    
    # Calculate flow change through edge e
    total_flow_change_bits = 0.0
    
    for (commodity_id, path), ratio in path_ratios.items():
        # Check if this path uses edge e
        interlinks = parse_path(path)
        if edge in interlinks:
            # Calculate flow change on this path
            if commodity_id in demand_changes:
                demand_change = demand_changes[commodity_id]  # packets/s
                flow_change_packets = ratio * demand_change  # packets/s
                flow_change_bits = flow_change_packets * packet_size * 8  # bits/s
                total_flow_change_bits += flow_change_bits
    
    return total_flow_change_bits


def run_enhanced_prediction():
    """
    Run enhanced prediction with capacity constraint dual variables.
    
    Returns:
        dict: Results including predictions and errors
    """
    print("=" * 80)
    print("Enhanced Dual Variable Prediction Analysis")
    print("=" * 80)
    print()
    
    # Configuration
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    # Load sequence
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_dual_validation.csv')
    if not os.path.exists(sequence_file):
        print(f"✗ Sequence file not found: {sequence_file}")
        return None
    
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    num_steps, num_commodities = sequence.shape
    
    # Output directory
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison', 'dual_validation')
    enhanced_dir = os.path.join(result_dir_base, 'enhanced_dual_analysis')
    os.makedirs(enhanced_dir, exist_ok=True)
    
    # Step 1: Extract all dual variables
    print("Step 1: Extracting all dual variables...")
    step1_rates = sequence[0].tolist()
    step1_duals = extract_all_dual_variables(config, step1_rates)
    
    lambda_2 = step1_duals['demand_duals'].get(2, None)
    step1_max_edge = step1_duals['max_edge']
    step1_capacity_duals = step1_duals['capacity_duals']
    step1_util = step1_duals['max_link_util']
    step1_mcfp_df = step1_duals['mcfp_df']
    
    print(f"  λ₂ (commodity 2 demand dual): {lambda_2:.6e} %/(packets/s)")
    print(f"  Step 1 max edge: {step1_max_edge}")
    step1_mu_e = step1_capacity_duals.get(step1_max_edge, None)
    print(f"  Step 1 μ_e (max edge capacity dual): {step1_mu_e:.6e} %/(bits/s)" if step1_mu_e is not None else "  Step 1 μ_e: None")
    print(f"  Step 1 max link utilization: {step1_util:.4f}%")
    print()
    
    # Check edge stability
    print("Checking edge stability...")
    edge_stability = check_max_edge_stability(sequence_df, config, result_dir_base)
    print()
    
    # Determine which edge to use for prediction
    # If edge is stable, use Step 1 edge; otherwise, use the edge from Step 2 onwards
    if edge_stability and edge_stability['stable']:
        max_edge = edge_stability['max_edge']
        mu_e = step1_capacity_duals.get(max_edge, None)
        print(f"Using stable max edge: {max_edge}")
    else:
        # Edge changes - use the edge from Step 2 onwards (most common)
        if edge_stability and len(edge_stability['edges_by_step']) > 1:
            # Use the edge from Step 2 (which is used in most steps)
            max_edge_step2 = edge_stability['edges_by_step'][1]['max_edge']
            print(f"⚠️  Edge changes: Step 1 edge = {step1_max_edge}, Step 2+ edge = {max_edge_step2}")
            
            # Try to get dual variable for Step 2 edge from Step 1
            # Check all capacity duals to find the one for Step 2 edge
            mu_e_step2_edge = None
            for edge_key, dual_val in step1_capacity_duals.items():
                if isinstance(edge_key, tuple) and edge_key == max_edge_step2:
                    mu_e_step2_edge = dual_val
                    break
                elif isinstance(edge_key, str):
                    # Try to parse and match
                    if str(max_edge_step2) in edge_key or edge_key.replace("'OBPModule", "").replace("'", "") == str(max_edge_step2).replace("(", "").replace(")", ""):
                        mu_e_step2_edge = dual_val
                        break
            
            # If Step 2 edge has a dual variable in Step 1, use it
            # Otherwise, we need to extract it from Step 2 optimization
            if mu_e_step2_edge is not None and mu_e_step2_edge > 1e-10:
                max_edge = max_edge_step2
                mu_e = mu_e_step2_edge
                print(f"   Using Step 2 edge ({max_edge}) with μ_e from Step 1: {mu_e:.6e} %/(bits/s)")
            else:
                # Extract dual variable from Step 2 optimization
                print(f"   Extracting dual variable for Step 2 edge from Step 2 optimization...")
                step2_rates = sequence[1].tolist()
                step2_duals = extract_all_dual_variables(config, step2_rates)
                step2_capacity_duals = step2_duals['capacity_duals']
                step2_max_edge = step2_duals['max_edge']
                
                # Get dual for Step 2's max edge
                mu_e = None
                if step2_max_edge == max_edge_step2:
                    mu_e = step2_duals.get('max_edge_capacity_dual', None)
                else:
                    # Try to find it in capacity_duals
                    for edge_key, dual_val in step2_capacity_duals.items():
                        if isinstance(edge_key, tuple) and edge_key == max_edge_step2:
                            mu_e = dual_val
                            break
                
                max_edge = max_edge_step2
                if mu_e is not None and mu_e > 1e-10:
                    print(f"   Step 2 edge μ_e: {mu_e:.6e} %/(bits/s)")
                else:
                    print(f"   ⚠️  Step 2 edge μ_e is None or too small, checking all capacity duals...")
                    # Print all non-zero capacity duals for debugging
                    non_zero_duals = {k: v for k, v in step2_capacity_duals.items() if v is not None and v > 1e-10}
                    if non_zero_duals:
                        print(f"   Non-zero capacity duals in Step 2: {len(non_zero_duals)}")
                        # Use the largest one as approximation
                        if non_zero_duals:
                            largest_edge, largest_dual = max(non_zero_duals.items(), key=lambda x: x[1])
                            print(f"   Largest capacity dual: edge {largest_edge}, μ = {largest_dual:.6e}")
                            # But we should use the actual max edge
                            max_edge = max_edge_step2
                            mu_e = None  # Keep as None for now
                    else:
                        print(f"   No non-zero capacity duals found in Step 2")
                    # Fall back to Step 1 edge
                    max_edge = step1_max_edge
                    mu_e = step1_mu_e
        else:
            max_edge = step1_max_edge
            mu_e = step1_mu_e
    print()
    
    # Run predictions for each step
    print("Running predictions for each step...")
    predictions = []
    
    for step_id in range(1, num_steps + 1):
        arrival_rates = sequence[step_id - 1].tolist()
        demand_change_2 = arrival_rates[2] - step1_rates[2]
        demand_changes = {2: demand_change_2}  # Only commodity 2 changes
        
        # Calculate Δflow_e_bits
        delta_flow_e_bits = calculate_edge_flow_change(
            step1_mcfp_df, max_edge, demand_changes, config
        )
        
        # Original prediction (only λ₂)
        original_pred = step1_util + lambda_2 * demand_change_2
        
        # Enhanced prediction (λ₂ + μ_e × Δflow_e_bits)
        if mu_e is not None:
            enhanced_pred = step1_util + lambda_2 * demand_change_2 + mu_e * delta_flow_e_bits
        else:
            enhanced_pred = original_pred
        
        # Get theoretical value
        result_dir = os.path.join(result_dir_base, 'strategy_dual_validation')
        step_dir = os.path.join(result_dir, f'step_{step_id}')
        mcfp_file = os.path.join(step_dir, 'mcfp_results_flows_4_commodities.csv')
        
        theoretical_util = None
        if os.path.exists(mcfp_file):
            mcfp_df = pd.read_csv(mcfp_file)
            theoretical_util = calculate_max_link_utilization(mcfp_df, config)
        
        predictions.append({
            'step_id': step_id,
            'commodity_2_demand': arrival_rates[2],
            'demand_change': demand_change_2,
            'delta_flow_e_bits': delta_flow_e_bits,
            'theoretical_util': theoretical_util,
            'original_pred': original_pred,
            'enhanced_pred': enhanced_pred,
            'original_error': theoretical_util - original_pred if theoretical_util is not None else None,
            'enhanced_error': theoretical_util - enhanced_pred if theoretical_util is not None else None
        })
        
        print(f"Step {step_id}: Theoretical={theoretical_util:.4f}%, "
              f"Original={original_pred:.4f}%, Enhanced={enhanced_pred:.4f}%")
    
    # Save results
    predictions_df = pd.DataFrame(predictions)
    output_file = os.path.join(enhanced_dir, 'enhanced_prediction_comparison.csv')
    predictions_df.to_csv(output_file, index=False)
    print(f"\n✓ Results saved to: {output_file}")
    
    # Generate detailed report
    print("\n" + "=" * 80)
    print("Generating Detailed Analysis Report...")
    print("=" * 80)
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("Enhanced Dual Variable Analysis Report")
    report_lines.append("=" * 80)
    report_lines.append("")
    
    # Capacity constraint information
    report_lines.append("1. Capacity Constraint Form:")
    report_lines.append("   flow_e_bits <= capacity_e")
    report_lines.append("   where flow_e_bits = Σ(flow_on_path[(i, path_idx)] for all paths using edge e) × packet_size × 8")
    report_lines.append("")
    report_lines.append("2. Dual Variable Units:")
    report_lines.append(f"   λ₂ (demand constraint): %/(packets/s)")
    report_lines.append(f"   μ_e (capacity constraint): %/(bits/s)")
    report_lines.append("   μ_e represents: if capacity increases by 1 bits/s, max utilization decreases by μ_e %")
    report_lines.append("")
    
    # Step 1 dual variables
    report_lines.append("3. Step 1 Dual Variables:")
    report_lines.append(f"   λ₂ = {lambda_2:.6e} %/(packets/s)")
    report_lines.append(f"   Max edge: {max_edge}")
    report_lines.append(f"   μ_e = {mu_e:.6e} %/(bits/s)" if mu_e is not None else "   μ_e = None")
    report_lines.append(f"   Step 1 max link utilization: {step1_util:.4f}%")
    report_lines.append("")
    
    # Edge stability
    report_lines.append("4. Maximum Utilization Edge Stability:")
    if edge_stability and edge_stability['stable']:
        report_lines.append(f"   ✓ Edge is stable: {edge_stability['max_edge']}")
    else:
        report_lines.append("   ⚠️  Edge changes across steps")
        if edge_stability:
            for step in edge_stability['edges_by_step']:
                report_lines.append(f"      Step {step['step_id']}: {step['max_edge']}")
    report_lines.append("")
    
    # Linear extrapolation formula
    report_lines.append("5. Linear Extrapolation Formula:")
    report_lines.append("   util(d) = util(d₀) + λ₂ × (d₂ - d₂₀) + μ_e × Δflow_e_bits")
    report_lines.append("")
    report_lines.append("   where:")
    report_lines.append("   - util(d₀): Step 1 max link utilization")
    report_lines.append("   - λ₂: Commodity 2 demand constraint dual variable")
    report_lines.append("   - d₂ - d₂₀: Commodity 2 demand change (packets/s)")
    report_lines.append("   - μ_e: Max edge capacity constraint dual variable")
    report_lines.append("   - Δflow_e_bits: Total flow change through max edge (bits/s)")
    report_lines.append("")
    report_lines.append("   Δflow_e_bits calculation:")
    report_lines.append("   Δflow_e_bits = Σ(ratio_i_path × (d_i - d_i₀) for all paths using edge e) × packet_size × 8")
    report_lines.append("   where ratio_i_path = flow_on_path[(i, path_idx)]₀ / d_i₀ (from Step 1)")
    report_lines.append("")
    
    # Error analysis
    report_lines.append("6. Prediction Error Analysis:")
    if len(predictions_df) > 0:
        original_errors = predictions_df['original_error'].dropna()
        enhanced_errors = predictions_df['enhanced_error'].dropna()
        
        if len(original_errors) > 0:
            report_lines.append(f"   Original prediction (λ₂ only):")
            report_lines.append(f"      Mean absolute error: {original_errors.abs().mean():.4f}%")
            report_lines.append(f"      Max absolute error: {original_errors.abs().max():.4f}%")
            report_lines.append(f"      RMSE: {np.sqrt((original_errors**2).mean()):.4f}%")
        
        if len(enhanced_errors) > 0:
            report_lines.append(f"   Enhanced prediction (λ₂ + μ_e × Δflow_e_bits):")
            report_lines.append(f"      Mean absolute error: {enhanced_errors.abs().mean():.4f}%")
            report_lines.append(f"      Max absolute error: {enhanced_errors.abs().max():.4f}%")
            report_lines.append(f"      RMSE: {np.sqrt((enhanced_errors**2).mean()):.4f}%")
            
            if len(original_errors) > 0:
                improvement = (original_errors.abs().mean() - enhanced_errors.abs().mean()) / original_errors.abs().mean() * 100
                report_lines.append(f"      Improvement: {improvement:.2f}% reduction in mean absolute error")
    report_lines.append("")
    
    # Unit verification
    report_lines.append("7. Unit Verification:")
    report_lines.append("   λ₂ × (d₂ - d₂₀): [%/(packets/s)] × [packets/s] = % ✓")
    report_lines.append("   μ_e × Δflow_e_bits: [%/(bits/s)] × [bits/s] = % ✓")
    report_lines.append("")
    
    # Save report
    report_file = os.path.join(enhanced_dir, 'enhanced_dual_analysis_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    print(f"✓ Report saved to: {report_file}")
    
    return {
        'step1_duals': step1_duals,
        'edge_stability': edge_stability,
        'predictions': predictions_df
    }


if __name__ == '__main__':
    run_enhanced_prediction()

