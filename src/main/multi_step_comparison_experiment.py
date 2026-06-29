#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-step comparison experiment: Re-optimization vs Path Ratio Preservation.

This script compares two strategies for multi-step simulation:
1. Strategy 1 (Re-optimization): Re-optimize at each time step
2. Strategy 2 (Path Ratio Preservation): Optimize only at step 1, preserve path ratios for subsequent steps

Outputs:
- Maximum link utilization comparison per step
- PLI comparison plots
- Delay comparison plots
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from pathlib import Path

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file, save_to_csv
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from simulator.simulator import Simulator
import main.main as main_module
from modem.switch import SimplePacketSwitch, FairPacketSwitch
from port.port import Port

# Import path ratio functions from test script
from main.test_path_ratio_preservation import (
    extract_path_ratios_from_csv,
    apply_path_ratios_to_demand
)
from main.global_optimal_ratio import (
    extract_paths_info_from_step1,
    optimize_global_path_ratios,
    solve_global_optimal_ratio_with_capacity_lp,
)

# Set plotting style
sns.set_theme(style="whitegrid")


def parse_path(path_str):
    """
    Parse path string to extract interlinks (only between OBP modules).
    Returns list of interlink tuples: [(src_module, dst_module), ...]
    Handles NaN/float path values by returning empty list.
    """
    import re
    if path_str is None or (isinstance(path_str, float) and np.isnan(path_str)):
        return []
    path_str = str(path_str)
    pattern = r'OBPModule\((\d+),\s*(\d+)\)(?!_[ud])'
    matches = re.findall(pattern, path_str)
    
    interlinks = []
    for i in range(len(matches) - 1):
        src = tuple(map(int, matches[i]))
        dst = tuple(map(int, matches[i + 1]))
        if src != dst:
            interlinks.append((src, dst))
    
    return interlinks


def calculate_max_link_utilization(mcfp_df, config):
    """
    Calculate maximum link utilization from mcfp_results DataFrame.
    
    Args:
        mcfp_df: DataFrame from mcfp_results CSV
        config: Configuration dictionary
        
    Returns:
        float: Maximum link utilization percentage
    """
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    generation_finish_time = config['simulation']['generation_finish_time']  # ms
    effective_time = generation_finish_time / 1000.0  # Convert ms to seconds
    
    interlink_traffic = {}
    
    for idx, row in mcfp_df.iterrows():
        arrival_rate = row['Arrival Rate']  # packets/s
        path = row['Path']
        
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
    for interlink, bits in interlink_traffic.items():
        bit_rate = bits / effective_time  # bits/s
        utilization = (bit_rate / interlink_capacity) * 100
        max_utilization = max(max_utilization, utilization)
    
    return max_utilization


def calculate_step_statistics(all_flows):
    """
    Calculate PLI and average delay from flows.
    
    Args:
        all_flows: List of Flow objects
        
    Returns:
        dict: {'pli': float, 'avg_delay': float}
    """
    total_sent = sum(flow.pkt_gen.packets_sent for flow in all_flows)
    total_received = sum(
        flow.pkt_sink.packets_received.get(flow.fid, 0)
        for flow in all_flows
        if hasattr(flow.pkt_sink, 'packets_received')
    )
    
    total_dropped = total_sent - total_received
    pli = (total_dropped / total_sent * 100) if total_sent > 0 else 0.0
    
    # Calculate average delay
    delays = []
    for flow in all_flows:
        if hasattr(flow.pkt_sink, 'waits') and flow.fid in flow.pkt_sink.waits:
            waits = flow.pkt_sink.waits[flow.fid]
            if waits:
                delays.extend(waits)
    
    avg_delay = np.mean(delays) if delays else 0.0
    
    return {'pli': pli, 'avg_delay': avg_delay}


def get_port_interlink_mapping(port, switch_coords):
    """
    Get the interlink edge that this port corresponds to.
    
    Args:
        port: Port object
        switch_coords: Coordinates of the switch that owns this port (src_coords)
    
    Returns:
        tuple: ((src_x, src_y), (dst_x, dst_y)) if port connects to another switch,
               None otherwise
    """
    src_coords = switch_coords
    
    if port.out is None:
        return None
    
    # Check if port.out is a switch
    if hasattr(port.out, 'x') and hasattr(port.out, 'y'):
        dst_coords = (port.out.x, port.out.y)
        return (src_coords, dst_coords)
    
    # If port.out is a scheduler (WFQ/Priority), check its out
    if hasattr(port.out, 'out') and port.out.out is not None:
        if hasattr(port.out.out, 'x') and hasattr(port.out.out, 'y'):
            dst_coords = (port.out.out.x, port.out.out.y)
            return (src_coords, dst_coords)
    
    return None


def calculate_actual_max_link_utilization_from_simulation(switches, config):
    """
    Calculate maximum link utilization from actual simulation port statistics.
    
    Args:
        switches: Dictionary of switches {(x, y): switch_object}
        config: Configuration dictionary
        
    Returns:
        float: Maximum link utilization percentage from actual simulation
    """
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    generation_finish_time = config['simulation']['generation_finish_time']  # ms
    effective_time = generation_finish_time / 1000.0  # Convert ms to seconds
    
    # Dictionary to store traffic on each interlink
    interlink_traffic = {}
    
    # Iterate through all switches
    for (x, y), switch in switches.items():
        # Get ports based on switch type
        if isinstance(switch, FairPacketSwitch):
            ports = switch.egress_ports
        elif isinstance(switch, SimplePacketSwitch):
            ports = switch.ports
        else:
            continue
        
        # Iterate through ports
        for port in ports:
            if not isinstance(port, Port):
                continue
            
            # Get interlink mapping for this port
            interlink = get_port_interlink_mapping(port, (x, y))
            
            if interlink is None:
                # Port doesn't connect to another switch (might be uplink/downlink)
                continue
            
            # Get port statistics
            packets_sent = port.packets_received - port.packets_dropped  # Successfully sent packets
            
            # Calculate bit rate
            bit_rate = (packets_sent / effective_time) * packet_size * 8  # bits/s
            
            # Store statistics
            if interlink not in interlink_traffic:
                interlink_traffic[interlink] = 0.0
            
            interlink_traffic[interlink] += bit_rate
    
    # Calculate utilization for each interlink
    max_utilization = 0.0
    for interlink, bit_rate in interlink_traffic.items():
        utilization = (bit_rate / interlink_capacity) * 100.0
        max_utilization = max(max_utilization, utilization)
    
    return max_utilization


def calculate_trigger_metric(dual_vars, current_demand, last_demand):
    """
    Calculate trigger metric for adaptive re-optimization strategy.
    
    Trigger metric = Σ(λ_i × |d_i_current - d_i_last|) for all commodities i
    
    Args:
        dual_vars: Dictionary {commodity_id: dual_value} from last optimization
        current_demand: List of current demand values [d0, d1, d2, d3]
        last_demand: List of demand values from last optimization [d0, d1, d2, d3]
        
    Returns:
        float: Trigger metric value
    """
    metric = 0.0
    
    for i, (current, last) in enumerate(zip(current_demand, last_demand)):
        # Skip if dual variable is None or missing
        if i not in dual_vars or dual_vars[i] is None:
            continue
        
        dual_value = dual_vars[i]
        demand_change = abs(current - last)
        metric += dual_value * demand_change
    
    return metric


def execute_strategy_reoptimization(sequence, config, result_dir_base, solver_options=None):
    """
    Execute Strategy 1: Re-optimize at each time step.
    
    Args:
        sequence: Arrival rate sequence (numpy array, shape: (num_steps, num_commodities))
        config: Configuration dictionary
        result_dir_base: Base directory for results
        solver_options: dict, optional. Extra kwargs for solver (e.g. abstol=1e-9 for ECOS).
        
    Returns:
        list: List of step statistics dictionaries
    """
    print("\n" + "=" * 80)
    print("Strategy 1: Re-optimization (Optimize at each step)")
    print("=" * 80)
    
    num_steps, num_commodities = sequence.shape
    strategy_stats = []
    infeasible_steps = []
    
    # Create topology once
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)
    
    previous_ratios = None
    previous_mcfp_df = None
    
    for step_id in range(1, num_steps + 1):
        print(f"\n--- Step {step_id}/{num_steps} ---")
        arrival_rates = sequence[step_id - 1].tolist()
        print(f"Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
        
        result_dir = os.path.join(result_dir_base, 'strategy1', f'step_{step_id}')
        os.makedirs(result_dir, exist_ok=True)
        
        # Update config with current arrival rates
        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        step_config['fixed_demand']['arrival_rate'] = arrival_rates
        step_config['simulation'] = config['simulation'].copy()
        step_config['simulation']['num_steps'] = 1  # Single step per iteration
        
        # Update regen_obp scenario_config to use updated arrival rates
        # (regen_obp.generate_demand_matrix reads from scenario_config)
        regen_obp.scenario_config = step_config
        
        # Generate demand matrix for current step
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
        
        optimizer_feasible = False
        optimizer_status = 'not_called'
        updated_demand_matrix = None
        
        # Try to optimize (always for step 1, try for step 2+)
        if step_id == 1:
            # Step 1: Always optimize
            print("Running optimizer for Step 1...")
            try:
                optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
                objective_type = step_config['optimization']['objective_func']
                mode = step_config['simulation']['failure_strategy']
                updated_demand_matrix = optimizer.solve_mcfp_path_formulation(
                    demand_matrix, objective_type, mode,
                    verbose=False, solver_options=solver_options
                )
                
                # Debug: Print optimizer result info
                if updated_demand_matrix is not None:
                    total_rate = updated_demand_matrix['Arrival Rate'].sum()
                    num_rows = len(updated_demand_matrix)
                    print(f"  Optimizer returned: {num_rows} rows, total arrival rate: {total_rate:.2f}")
                
                # Check if optimization was successful
                # A successful optimization should have non-zero flows and multiple paths per commodity
                # (When split_commodities='on', each commodity should have multiple paths, not just 1 row per commodity)
                if updated_demand_matrix is not None and len(updated_demand_matrix) > 0:
                    # Check if any flows are non-zero (optimization actually found paths)
                    # Also check if we have more rows than commodities (indicating split paths)
                    total_rate = updated_demand_matrix['Arrival Rate'].sum()
                    if total_rate > 0 and len(updated_demand_matrix) > num_commodities:
                        optimizer_feasible = True
                        optimizer_status = 'feasible'
                        print(f"✓ Optimization successful for Step {step_id}")
                    else:
                        optimizer_status = 'infeasible'
                        optimizer_feasible = False
                        print(f"✗ Optimization failed for Step {step_id} (total rate: {total_rate:.2f}, rows: {len(updated_demand_matrix)})")
                else:
                    optimizer_status = 'infeasible'
                    optimizer_feasible = False
                    print(f"✗ Optimization failed for Step {step_id} (no result returned)")
            except Exception as e:
                optimizer_status = 'error'
                print(f"✗ Optimization error for Step {step_id}: {e}")
        else:
            # Step 2+: Try to optimize
            print(f"Attempting to re-optimize for Step {step_id}...")
            try:
                optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
                objective_type = step_config['optimization']['objective_func']
                mode = step_config['simulation']['failure_strategy']
                updated_demand_matrix = optimizer.solve_mcfp_path_formulation(
                    demand_matrix, objective_type, mode,
                    verbose=False, solver_options=solver_options
                )
                
                if updated_demand_matrix is not None and len(updated_demand_matrix) > 0:
                    # Check if problem was actually solved (not all zeros)
                    if updated_demand_matrix['Arrival Rate'].sum() > 0:
                        optimizer_feasible = True
                        optimizer_status = 'feasible'
                        print(f"✓ Re-optimization successful for Step {step_id}")
                    else:
                        optimizer_status = 'infeasible'
                        print(f"✗ Re-optimization infeasible for Step {step_id} (all flows are zero)")
                else:
                    optimizer_status = 'infeasible'
                    print(f"✗ Re-optimization failed for Step {step_id}")
            except Exception as e:
                optimizer_status = 'error'
                print(f"✗ Re-optimization error for Step {step_id}: {e}")
        
        # If optimization failed and we have previous ratios, use them
        if not optimizer_feasible and previous_ratios is not None and previous_mcfp_df is not None:
            print(f"⚠️  Using previous step's path ratios for Step {step_id} (optimization infeasible)")
            updated_demand_matrix = apply_path_ratios_to_demand(
                previous_ratios, arrival_rates, previous_mcfp_df
            )
            optimizer_status = 'infeasible_using_previous'
            infeasible_steps.append(step_id)
        elif not optimizer_feasible:
            # If step 1 fails, we can't continue
            print(f"✗ Fatal error: Optimization failed for Step {step_id} and no previous ratios available")
            raise RuntimeError(f"Optimization failed for Step {step_id}")
        
        # Run simulation
        np.random.seed(42)  # Fixed seed for reproducibility
        all_flows, switches, blocked_flows = main_module.run_simulation_scenario(
            step_config, result_dir, 0, precomputed_demand_matrix=updated_demand_matrix
        )
        
        # Save mcfp_results
        mcfp_file = os.path.join(result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
        save_to_csv(updated_demand_matrix, filename=mcfp_file)
        
        # Calculate statistics
        mcfp_df = pd.read_csv(mcfp_file)
        max_link_util_theoretical = calculate_max_link_utilization(mcfp_df, step_config)
        max_link_util_actual = calculate_actual_max_link_utilization_from_simulation(switches, step_config)
        flow_stats = calculate_step_statistics(all_flows)
        
        step_stat = {
            'step_id': step_id,
            'arrival_rates': arrival_rates,
            'max_link_utilization': max_link_util_theoretical,  # Theoretical (from MCFP)
            'max_link_utilization_actual': max_link_util_actual,  # Actual (from simulation)
            'pli': flow_stats['pli'],
            'avg_delay': flow_stats['avg_delay'],
            'optimizer_feasible': optimizer_feasible,
            'optimizer_status': optimizer_status
        }
        strategy_stats.append(step_stat)
        
        # Save ratios for next step
        previous_ratios = extract_path_ratios_from_csv(mcfp_file)
        previous_mcfp_df = mcfp_df
        
        print(f"Step {step_id} Statistics:")
        print(f"  Max Link Utilization: {max_link_util_theoretical:.4f}%")
        print(f"  PLI: {flow_stats['pli']:.4f}%")
        print(f"  Average Delay: {flow_stats['avg_delay']:.6f}s")
        print(f"  Optimizer Status: {optimizer_status}")
    
    print(f"\n✓ Strategy 1 completed. Infeasible steps: {infeasible_steps}")
    return strategy_stats, infeasible_steps


def execute_strategy_path_ratio_preservation(sequence, config, result_dir_base, solver_options=None):
    """
    Execute Strategy 2: Optimize only at step 1, preserve path ratios for subsequent steps.
    
    Args:
        sequence: Arrival rate sequence (numpy array, shape: (num_steps, num_commodities))
        config: Configuration dictionary
        result_dir_base: Base directory for results
        solver_options: dict, optional. Extra kwargs for solver at step 1.
        
    Returns:
        list: List of step statistics dictionaries
    """
    print("\n" + "=" * 80)
    print("Strategy 2: Path Ratio Preservation (Optimize only at Step 1)")
    print("=" * 80)
    
    num_steps, num_commodities = sequence.shape
    strategy_stats = []
    
    # Create topology once
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)
    
    baseline_ratios = None
    baseline_mcfp_df = None
    
    for step_id in range(1, num_steps + 1):
        print(f"\n--- Step {step_id}/{num_steps} ---")
        arrival_rates = sequence[step_id - 1].tolist()
        print(f"Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
        
        result_dir = os.path.join(result_dir_base, 'strategy2', f'step_{step_id}')
        os.makedirs(result_dir, exist_ok=True)
        
        # Update config with current arrival rates
        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        step_config['fixed_demand']['arrival_rate'] = arrival_rates
        step_config['simulation'] = config['simulation'].copy()
        step_config['simulation']['num_steps'] = 1  # Single step per iteration
        
        # Update regen_obp scenario_config to use updated arrival rates
        # (regen_obp.generate_demand_matrix reads from scenario_config)
        regen_obp.scenario_config = step_config
        
        # Generate demand matrix for current step
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
        
        updated_demand_matrix = None
        
        if step_id == 1:
            # Step 1: Optimize
            print("Running optimizer for Step 1...")
            optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
            objective_type = step_config['optimization']['objective_func']
            mode = step_config['simulation']['failure_strategy']
            updated_demand_matrix = optimizer.solve_mcfp_path_formulation(
                demand_matrix, objective_type, mode,
                verbose=False, solver_options=solver_options
            )
            
            # Save baseline ratios
            mcfp_file = os.path.join(result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
            save_to_csv(updated_demand_matrix, filename=mcfp_file)
            baseline_ratios = extract_path_ratios_from_csv(mcfp_file)
            baseline_mcfp_df = pd.read_csv(mcfp_file)
            print("✓ Baseline path ratios extracted from Step 1")
        else:
            # Step 2+: Use preserved ratios
            print(f"Using preserved path ratios from Step 1...")
            updated_demand_matrix = apply_path_ratios_to_demand(
                baseline_ratios, arrival_rates, baseline_mcfp_df
            )
        
        # Run simulation
        np.random.seed(42)  # Fixed seed for reproducibility
        all_flows, switches, blocked_flows = main_module.run_simulation_scenario(
            step_config, result_dir, 0, precomputed_demand_matrix=updated_demand_matrix
        )
        
        # Save mcfp_results
        mcfp_file = os.path.join(result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
        save_to_csv(updated_demand_matrix, filename=mcfp_file)
        
        # Calculate statistics
        mcfp_df = pd.read_csv(mcfp_file)
        max_link_util_theoretical = calculate_max_link_utilization(mcfp_df, step_config)
        max_link_util_actual = calculate_actual_max_link_utilization_from_simulation(switches, step_config)
        flow_stats = calculate_step_statistics(all_flows)
        
        step_stat = {
            'step_id': step_id,
            'arrival_rates': arrival_rates,
            'max_link_utilization': max_link_util_theoretical,  # Theoretical (from MCFP)
            'max_link_utilization_actual': max_link_util_actual,  # Actual (from simulation)
            'pli': flow_stats['pli'],
            'avg_delay': flow_stats['avg_delay'],
            'optimizer_feasible': (step_id == 1),
            'optimizer_status': 'feasible' if step_id == 1 else 'not_called'
        }
        strategy_stats.append(step_stat)
        
        print(f"Step {step_id} Statistics:")
        print(f"  Max Link Utilization: {max_link_util_theoretical:.4f}%")
        print(f"  PLI: {flow_stats['pli']:.4f}%")
        print(f"  Average Delay: {flow_stats['avg_delay']:.6f}s")
        print(f"  Optimizer Status: {step_stat['optimizer_status']}")
    
    print("\n✓ Strategy 2 completed.")
    return strategy_stats


def execute_strategy_adaptive_reoptimization(sequence, config, result_dir_base, threshold=8, solver_options=None):
    """
    Execute Strategy 4: Adaptive Re-optimization based on Dual Variables.
    
    This strategy triggers re-optimization only when the trigger metric exceeds a threshold.
    Trigger metric = Σ(λ_i × |d_i_current - d_i_last|) for all commodities i
    
    Args:
        sequence: Arrival rate sequence (numpy array, shape: (num_steps, num_commodities))
        config: Configuration dictionary
        result_dir_base: Base directory for results
        threshold: Threshold for trigger metric (default: 50)
        solver_options: dict, optional. Extra kwargs for solver when reoptimizing.
        
    Returns:
        list: List of step statistics dictionaries
    """
    print("\n" + "=" * 80)
    print(f"Strategy 4: Adaptive Re-optimization (Threshold: {threshold})")
    print("=" * 80)
    
    num_steps, num_commodities = sequence.shape
    strategy_stats = []
    
    # Create topology once
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)
    
    # Storage for last optimization state
    last_dual_variables = None
    last_demand = None
    last_path_ratios = None
    last_mcfp_df = None
    
    for step_id in range(1, num_steps + 1):
        print(f"\n--- Step {step_id}/{num_steps} ---")
        arrival_rates = sequence[step_id - 1].tolist()
        print(f"Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
        
        result_dir = os.path.join(result_dir_base, 'strategy4', f'step_{step_id}')
        os.makedirs(result_dir, exist_ok=True)
        
        # Update config with current arrival rates
        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        step_config['fixed_demand']['arrival_rate'] = arrival_rates
        step_config['simulation'] = config['simulation'].copy()
        step_config['simulation']['num_steps'] = 1  # Single step per iteration
        
        # Update regen_obp scenario_config
        regen_obp.scenario_config = step_config
        
        # Generate demand matrix for current step
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
        
        # Calculate trigger metric (for Step 2+)
        trigger_metric = None
        reoptimized = False
        optimizer_feasible = None
        optimizer_status = 'not_called'
        current_dual_variables = None
        
        if step_id == 1:
            # Step 1: Always optimize
            print("Step 1: Unconditionally running optimizer...")
            reoptimized = True
        else:
            # Step 2+: Calculate trigger metric
            if last_dual_variables is not None and last_demand is not None:
                trigger_metric = calculate_trigger_metric(last_dual_variables, arrival_rates, last_demand)
                print(f"Trigger metric: {trigger_metric:.4f} (threshold: {threshold})")
                
                if trigger_metric > threshold:
                    print(f"Trigger metric ({trigger_metric:.4f}) > threshold ({threshold}). Re-optimizing...")
                    reoptimized = True
                else:
                    print(f"Trigger metric ({trigger_metric:.4f}) <= threshold ({threshold}). Using preserved path ratios.")
            else:
                # No previous optimization state, must optimize
                print("No previous optimization state. Running optimizer...")
                reoptimized = True
                trigger_metric = 0.0
        
        updated_demand_matrix = None
        
        if reoptimized:
            # Run optimizer
            optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
            objective_type = step_config['optimization']['objective_func']
            mode = step_config['simulation']['failure_strategy']
            
            updated_demand_matrix = optimizer.solve_mcfp_path_formulation(
                demand_matrix, objective_type, mode,
                verbose=False, solver_options=solver_options
            )
            
            # Extract dual variables
            if hasattr(updated_demand_matrix, 'attrs') and 'dual_variables' in updated_demand_matrix.attrs:
                current_dual_variables = updated_demand_matrix.attrs['dual_variables']
            
            # Check if optimization was feasible
            # Save mcfp_results to check flows
            mcfp_file = os.path.join(result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
            save_to_csv(updated_demand_matrix, filename=mcfp_file)
            mcfp_df = pd.read_csv(mcfp_file)
            
            # Check if any flows are non-zero (simple feasibility check)
            total_flow = mcfp_df['Arrival Rate'].sum()
            if total_flow > 1e-6:  # Some flow allocated
                optimizer_feasible = True
                optimizer_status = 'feasible'
                
                # Update last optimization state
                last_dual_variables = current_dual_variables.copy() if current_dual_variables else None
                last_demand = arrival_rates.copy()
                last_path_ratios = extract_path_ratios_from_csv(mcfp_file)
                last_mcfp_df = mcfp_df
                
                print("✓ Optimization successful")
            else:
                # Optimization infeasible, fall back to path ratios
                optimizer_feasible = False
                optimizer_status = 'infeasible_fallback'
                print("⚠ Optimization infeasible. Falling back to last path ratios...")
                
                if last_path_ratios is not None and last_mcfp_df is not None:
                    updated_demand_matrix = apply_path_ratios_to_demand(
                        last_path_ratios, arrival_rates, last_mcfp_df
                    )
                    # Re-save with fallback ratios
                    save_to_csv(updated_demand_matrix, filename=mcfp_file)
                    mcfp_df = pd.read_csv(mcfp_file)
                    print("✓ Applied fallback path ratios")
                else:
                    # No fallback available (should not happen if Step 1 succeeded)
                    raise RuntimeError(f"Step {step_id} optimization infeasible and no fallback ratios available")
        else:
            # Use preserved path ratios
            if last_path_ratios is not None and last_mcfp_df is not None:
                updated_demand_matrix = apply_path_ratios_to_demand(
                    last_path_ratios, arrival_rates, last_mcfp_df
                )
            else:
                raise RuntimeError(f"Step {step_id}: No path ratios available (Step 1 should have set them)")
        
        # Run simulation
        np.random.seed(42)  # Fixed seed for reproducibility
        all_flows, switches, blocked_flows = main_module.run_simulation_scenario(
            step_config, result_dir, 0, precomputed_demand_matrix=updated_demand_matrix
        )
        
        # Save mcfp_results (if not already saved)
        mcfp_file = os.path.join(result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
        if not os.path.exists(mcfp_file):
            save_to_csv(updated_demand_matrix, filename=mcfp_file)
        
        # Calculate statistics
        mcfp_df = pd.read_csv(mcfp_file)
        max_link_util_theoretical = calculate_max_link_utilization(mcfp_df, step_config)
        max_link_util_actual = calculate_actual_max_link_utilization_from_simulation(switches, step_config)
        flow_stats = calculate_step_statistics(all_flows)
        
        # Calculate trigger metric for this step (if not already calculated)
        if trigger_metric is None and step_id > 1:
            if last_dual_variables is not None and last_demand is not None:
                trigger_metric = calculate_trigger_metric(last_dual_variables, arrival_rates, last_demand)
        
        step_stat = {
            'step_id': step_id,
            'arrival_rates': arrival_rates,
            'max_link_utilization': max_link_util_theoretical,
            'max_link_utilization_actual': max_link_util_actual,
            'pli': flow_stats['pli'],
            'avg_delay': flow_stats['avg_delay'],
            'trigger_metric': trigger_metric,
            'reoptimized': reoptimized,
            'optimizer_feasible': optimizer_feasible,
            'optimizer_status': optimizer_status
        }
        strategy_stats.append(step_stat)
        
        print(f"Step {step_id} Statistics:")
        print(f"  Trigger Metric: {trigger_metric if trigger_metric is not None else 'N/A'}")
        print(f"  Re-optimized: {reoptimized}")
        print(f"  Max Link Utilization: {max_link_util_theoretical:.4f}%")
        print(f"  PLI: {flow_stats['pli']:.4f}%")
        print(f"  Average Delay: {flow_stats['avg_delay']:.6f}s")
        print(f"  Optimizer Status: {optimizer_status}")
    
    # Generate summary report
    reoptimized_steps = [stat['step_id'] for stat in strategy_stats if stat['reoptimized']]
    preserved_steps = [stat['step_id'] for stat in strategy_stats if not stat['reoptimized']]
    
    print("\n" + "=" * 80)
    print("Strategy 4: Summary Report")
    print("=" * 80)
    print(f"Total Steps: {num_steps}")
    print(f"Re-optimized Steps: {len(reoptimized_steps)} ({len(reoptimized_steps)/num_steps*100:.1f}%)")
    print(f"  Steps: {reoptimized_steps}")
    print(f"Path Ratio Preserved Steps: {len(preserved_steps)} ({len(preserved_steps)/num_steps*100:.1f}%)")
    print(f"  Steps: {preserved_steps}")
    print(f"Threshold Used: {threshold}")
    print("=" * 80)
    
    print("\n✓ Strategy 4 completed.")
    return strategy_stats


def execute_strategy_global_optimal_ratio(sequence, config, result_dir_base,
                                          solver_options=None, global_ratio_minimize_options=None):
    """
    Execute Strategy 3: Global Optimal Ratio (optimize once for all steps).
    
    Given the entire 10-step arrival rate sequence, find a single fixed path flow
    ratio that minimizes the average maximum link utilization across all 10 steps.
    
    Args:
        sequence: Arrival rate sequence (numpy array, shape: (num_steps, num_commodities))
        config: Configuration dictionary
        result_dir_base: Base directory for results
        solver_options: optional dict passed to Step-1 MCFP (same as Strategy 1/4 precise runs)
        global_ratio_minimize_options: optional dict merged into scipy.minimize options for SLSQP
        
    Returns:
        list: List of step statistics dictionaries
    """
    print("\n" + "=" * 80)
    print("Strategy 3: Global Optimal Ratio (Optimize once for all steps)")
    print("=" * 80)
    
    num_steps, num_commodities = sequence.shape
    strategy_stats = []
    
    # Create topology once
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)
    
    # Step 1: First run optimization to get Step 1 results (for path extraction)
    print("\n--- Step 1: Initial optimization for path extraction ---")
    step1_arrival_rates = sequence[0].tolist()
    
    step1_config = config.copy()
    step1_config['fixed_demand'] = config['fixed_demand'].copy()
    step1_config['fixed_demand']['arrival_rate'] = step1_arrival_rates
    step1_config['simulation'] = config['simulation'].copy()
    step1_config['simulation']['num_steps'] = 1
    
    regen_obp.scenario_config = step1_config
    step1_demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    
    # Run Step 1 optimization
    optimizer = MultiCommodityOptimizer(step1_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step1_config['optimization']['objective_func']
    mode = step1_config['simulation']['failure_strategy']
    step1_mcfp_result = optimizer.solve_mcfp_path_formulation(
        step1_demand_matrix, objective_type, mode,
        verbose=False, solver_options=solver_options
    )
    
    # Save Step 1 results
    step1_result_dir = os.path.join(result_dir_base, 'strategy3', 'step_1')
    os.makedirs(step1_result_dir, exist_ok=True)
    step1_mcfp_file = os.path.join(step1_result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
    save_to_csv(step1_mcfp_result, filename=step1_mcfp_file)
    
    # Extract paths info from Step 1
    print("Extracting path information from Step 1...")
    paths_info = extract_paths_info_from_step1(step1_mcfp_file)
    print(f"✓ Extracted paths for {len(paths_info)} commodities")
    
    # Step 2: Optimize global path ratios for entire sequence
    print("\n--- Global Optimization: Finding optimal path ratios for all steps ---")
    sequence_df = pd.DataFrame(sequence, columns=[f'Commodity_{i}' for i in range(num_commodities)])
    
    # Get Step 1 ratios as initial guess
    initial_ratios = extract_path_ratios_from_csv(step1_mcfp_file)
    
    print("Running global optimization (this may take several minutes)...")
    optimization_result = optimize_global_path_ratios(
        sequence_df, paths_info, config,
        initial_ratios=initial_ratios,
        method='SLSQP',
        minimize_options=global_ratio_minimize_options
    )
    
    optimal_ratios = optimization_result['optimal_ratios']
    optimal_avg_util = optimization_result['optimal_value']
    opt_status = optimization_result['optimization_result']
    global_ratio_ok = optimization_result.get('optimizer_success', getattr(opt_status, 'success', False))
    
    print(f"✓ Global optimization completed!")
    print(f"  Status: {opt_status.status}")
    print(f"  Optimal average utilization: {optimal_avg_util:.4f}%")
    print(f"  Number of iterations: {opt_status.nit}")
    print(f"  SLSQP success: {global_ratio_ok}")
    
    # Step 3: Apply optimal ratios to each step and run simulation
    step1_mcfp_df = pd.read_csv(step1_mcfp_file)
    
    for step_id in range(1, num_steps + 1):
        print(f"\n--- Step {step_id}/{num_steps} ---")
        arrival_rates = sequence[step_id - 1].tolist()
        print(f"Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
        
        result_dir = os.path.join(result_dir_base, 'strategy3', f'step_{step_id}')
        os.makedirs(result_dir, exist_ok=True)
        
        # Update config with current arrival rates
        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        step_config['fixed_demand']['arrival_rate'] = arrival_rates
        step_config['simulation'] = config['simulation'].copy()
        step_config['simulation']['num_steps'] = 1
        
        # Apply optimal ratios to current step's arrival rates
        print(f"Applying global optimal path ratios...")
        updated_demand_matrix = apply_path_ratios_to_demand(
            optimal_ratios, arrival_rates, step1_mcfp_df
        )
        
        # Run simulation
        np.random.seed(42)  # Fixed seed for reproducibility
        all_flows, switches, blocked_flows = main_module.run_simulation_scenario(
            step_config, result_dir, 0, precomputed_demand_matrix=updated_demand_matrix
        )
        
        # Save mcfp_results
        mcfp_file = os.path.join(result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
        save_to_csv(updated_demand_matrix, filename=mcfp_file)
        
        # Calculate statistics
        mcfp_df = pd.read_csv(mcfp_file)
        max_link_util_theoretical = calculate_max_link_utilization(mcfp_df, step_config)
        max_link_util_actual = calculate_actual_max_link_utilization_from_simulation(switches, step_config)
        flow_stats = calculate_step_statistics(all_flows)
        
        step_stat = {
            'step_id': step_id,
            'arrival_rates': arrival_rates,
            'max_link_utilization': max_link_util_theoretical,  # Theoretical (from MCFP)
            'max_link_utilization_actual': max_link_util_actual,  # Actual (from simulation)
            'pli': flow_stats['pli'],
            'avg_delay': flow_stats['avg_delay'],
            'optimizer_feasible': (step_id == 1),  # Only Step 1 ran optimizer for path extraction
            'optimizer_status': 'global_optimized' if step_id == 1 else 'applied_global_ratio',
            'global_ratio_optimizer_success': global_ratio_ok,
        }
        strategy_stats.append(step_stat)
        
        print(f"Step {step_id} Statistics:")
        print(f"  Max Link Utilization: {max_link_util_theoretical:.4f}%")
        print(f"  PLI: {flow_stats['pli']:.2f}%")
        print(f"  Avg Delay: {flow_stats['avg_delay']:.6f}s")
    
    print(f"\n✓ Strategy 3 completed!")
    print(f"  Global optimal average utilization: {optimal_avg_util:.4f}%")
    
    return strategy_stats


def execute_strategy_global_optimal_ratio_cap100_theoretical_only(
    sequence,
    config,
    result_dir_base,
    solver_options=None,
    cvxpy_solve_kwargs=None,
    max_utilization_percent=100.0,
):
    """
    Strategy 3 variant: global fixed path ratios via LP with per-interlink
    utilization <= max_utilization_percent every step; no Simpy simulation.

    Writes under result_dir_base/strategy3_cap100_theoretical/.
    """
    print("\n" + "=" * 80)
    print("Strategy 3 (cap-constrained LP, theoretical only)")
    print("=" * 80)

    num_steps, num_commodities = sequence.shape
    strategy_stats = []
    out_root = os.path.join(result_dir_base, 'strategy3_cap100_theoretical')
    os.makedirs(out_root, exist_ok=True)

    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)

    print("\n--- Step 1: MCFP for path extraction ---")
    step1_arrival_rates = sequence[0].tolist()
    step1_config = config.copy()
    step1_config['fixed_demand'] = config['fixed_demand'].copy()
    step1_config['fixed_demand']['arrival_rate'] = step1_arrival_rates
    step1_config['simulation'] = config['simulation'].copy()
    step1_config['simulation']['num_steps'] = 1

    regen_obp.scenario_config = step1_config
    step1_demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)

    optimizer = MultiCommodityOptimizer(step1_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step1_config['optimization']['objective_func']
    mode = step1_config['simulation']['failure_strategy']
    step1_mcfp_result = optimizer.solve_mcfp_path_formulation(
        step1_demand_matrix, objective_type, mode,
        verbose=False, solver_options=solver_options
    )

    step1_result_dir = os.path.join(out_root, 'step_1')
    os.makedirs(step1_result_dir, exist_ok=True)
    step1_mcfp_file = os.path.join(step1_result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
    save_to_csv(step1_mcfp_result, filename=step1_mcfp_file)

    paths_info = extract_paths_info_from_step1(step1_mcfp_file)
    print(f"✓ Paths for {len(paths_info)} commodities")

    sequence_df = pd.DataFrame(sequence, columns=[f'Commodity_{i}' for i in range(num_commodities)])

    solve_kw = {'verbose': False}
    if cvxpy_solve_kwargs:
        solve_kw.update(cvxpy_solve_kwargs)

    print("\n--- LP: min average max utilization, util <= {:.1f}% ---".format(max_utilization_percent))
    lp_result = solve_global_optimal_ratio_with_capacity_lp(
        sequence_df, paths_info, config,
        cvxpy_solve_kwargs=solve_kw,
        max_utilization_percent=max_utilization_percent,
    )

    lp_status = lp_result['cvxpy_status']
    feasible = lp_result['feasible']

    if not feasible or lp_result['optimal_ratios'] is None:
        print("\n" + "!" * 80)
        print(f"INFEASIBLE or failed LP: status={lp_status}")
        print("!" * 80 + "\n")
        meta_path = os.path.join(out_root, 'run_infeasible.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({
                'feasible': False,
                'cvxpy_status': lp_status,
                'capacity_constrained': True,
                'mode': 'theoretical_only',
            }, f, indent=2)
        return []

    optimal_ratios = lp_result['optimal_ratios']
    opt_avg = lp_result['optimal_value']
    print(f"✓ LP optimal  status={lp_status}  objective (avg u)={opt_avg:.6f}%")

    step1_mcfp_df = pd.read_csv(step1_mcfp_file)
    max_observed = 0.0
    tol = 0.05  # percentage points slack for numerical error

    for step_id in range(1, num_steps + 1):
        arrival_rates = sequence[step_id - 1].tolist()
        result_dir = os.path.join(out_root, f'step_{step_id}')
        os.makedirs(result_dir, exist_ok=True)

        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        step_config['fixed_demand']['arrival_rate'] = arrival_rates
        step_config['simulation'] = config['simulation'].copy()
        step_config['simulation']['num_steps'] = 1

        updated_demand_matrix = apply_path_ratios_to_demand(
            optimal_ratios, arrival_rates, step1_mcfp_df
        )
        mcfp_file = os.path.join(result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv")
        save_to_csv(updated_demand_matrix, filename=mcfp_file)

        mcfp_df = pd.read_csv(mcfp_file)
        max_link_util_theoretical = calculate_max_link_utilization(mcfp_df, step_config)
        max_observed = max(max_observed, max_link_util_theoretical)

        if max_link_util_theoretical > max_utilization_percent + tol:
            print(
                f"  WARNING step {step_id}: theoretical util {max_link_util_theoretical:.4f}% "
                f"> {max_utilization_percent + tol:.2f}% (numerical slack check)"
            )

        step_stat = {
            'step_id': step_id,
            'arrival_rates': arrival_rates,
            'max_link_utilization': max_link_util_theoretical,
            'max_link_utilization_actual': float('nan'),
            'pli': float('nan'),
            'avg_delay': float('nan'),
            'optimizer_feasible': (step_id == 1),
            'optimizer_status': 'lp_cap100' if step_id > 1 else 'mcfp_step1',
            'global_ratio_optimizer_success': True,
            'mode': 'theoretical_only',
            'capacity_constrained': True,
            'lp_status': lp_status,
            'lp_objective_avg_u': opt_avg,
        }
        strategy_stats.append(step_stat)

    print(f"\n✓ Theoretical-only run done. Peak max_link_utilization over steps: {max_observed:.4f}%")
    meta_ok = os.path.join(out_root, 'run_summary.json')
    with open(meta_ok, 'w', encoding='utf-8') as f:
        json.dump({
            'feasible': True,
            'cvxpy_status': lp_status,
            'lp_objective_avg_u': opt_avg,
            'peak_max_link_utilization': max_observed,
            'capacity_constrained': True,
            'mode': 'theoretical_only',
        }, f, indent=2)

    return strategy_stats


def plot_comparison_results(strategy1_stats, strategy2_stats, output_dir):
    """
    Generate comparison plots for the two strategies.
    
    Args:
        strategy1_stats: List of step statistics from Strategy 1
        strategy2_stats: List of step statistics from Strategy 2
        output_dir: Directory to save plots
    """
    steps = [s['step_id'] for s in strategy1_stats]
    
    # Extract data
    max_util_1 = [s['max_link_utilization'] for s in strategy1_stats]
    max_util_2 = [s['max_link_utilization'] for s in strategy2_stats]
    pli_1 = [s['pli'] for s in strategy1_stats]
    pli_2 = [s['pli'] for s in strategy2_stats]
    delay_1 = [s['avg_delay'] for s in strategy1_stats]
    delay_2 = [s['avg_delay'] for s in strategy2_stats]
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 1, figsize=(12, 12))
    
    # Plot 1: Maximum Link Utilization
    axes[0].plot(steps, max_util_1, 'o-', label='Strategy 1: Re-optimization', linewidth=2, markersize=8)
    axes[0].plot(steps, max_util_2, 's--', label='Strategy 2: Path Ratio Preservation', linewidth=2, markersize=8)
    axes[0].set_xlabel('Time Step', fontsize=12)
    axes[0].set_ylabel('Maximum Link Utilization (%)', fontsize=12)
    axes[0].set_title('Maximum Link Utilization Comparison', fontsize=14, fontweight='bold')
    axes[0].legend(fontsize=11)
    axes[0].grid(True, alpha=0.3)
    
    # Plot 2: PLI
    axes[1].plot(steps, pli_1, 'o-', label='Strategy 1: Re-optimization', linewidth=2, markersize=8)
    axes[1].plot(steps, pli_2, 's--', label='Strategy 2: Path Ratio Preservation', linewidth=2, markersize=8)
    axes[1].set_xlabel('Time Step', fontsize=12)
    axes[1].set_ylabel('Packet Loss Indicator (PLI) (%)', fontsize=12)
    axes[1].set_title('PLI Comparison', fontsize=14, fontweight='bold')
    axes[1].legend(fontsize=11)
    axes[1].grid(True, alpha=0.3)
    
    # Plot 3: Delay
    axes[2].plot(steps, delay_1, 'o-', label='Strategy 1: Re-optimization', linewidth=2, markersize=8)
    axes[2].plot(steps, delay_2, 's--', label='Strategy 2: Path Ratio Preservation', linewidth=2, markersize=8)
    axes[2].set_xlabel('Time Step', fontsize=12)
    axes[2].set_ylabel('Average Delay (s)', fontsize=12)
    axes[2].set_title('Average Delay Comparison', fontsize=14, fontweight='bold')
    axes[2].legend(fontsize=11)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save combined plot
    output_file = os.path.join(output_dir, 'comparison_all_metrics.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Comparison plots saved to: {output_file}")
    
    # Also save individual plots
    for i, metric in enumerate(['max_link_utilization', 'pli', 'delay']):
        fig, ax = plt.subplots(figsize=(10, 6))
        if metric == 'max_link_utilization':
            ax.plot(steps, max_util_1, 'o-', label='Strategy 1: Re-optimization', linewidth=2, markersize=8)
            ax.plot(steps, max_util_2, 's--', label='Strategy 2: Path Ratio Preservation', linewidth=2, markersize=8)
            ax.set_ylabel('Maximum Link Utilization (%)', fontsize=12)
            title = 'Maximum Link Utilization Comparison'
        elif metric == 'pli':
            ax.plot(steps, pli_1, 'o-', label='Strategy 1: Re-optimization', linewidth=2, markersize=8)
            ax.plot(steps, pli_2, 's--', label='Strategy 2: Path Ratio Preservation', linewidth=2, markersize=8)
            ax.set_ylabel('Packet Loss Indicator (PLI) (%)', fontsize=12)
            title = 'PLI Comparison'
        else:  # delay
            ax.plot(steps, delay_1, 'o-', label='Strategy 1: Re-optimization', linewidth=2, markersize=8)
            ax.plot(steps, delay_2, 's--', label='Strategy 2: Path Ratio Preservation', linewidth=2, markersize=8)
            ax.set_ylabel('Average Delay (s)', fontsize=12)
            title = 'Average Delay Comparison'
        
        ax.set_xlabel('Time Step', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        
        output_file = os.path.join(output_dir, f'{metric}_comparison.png')
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
    
    plt.close(fig)


def main():
    """Main function to run multi-step comparison experiment."""
    
    print("=" * 80)
    print("Multi-Step Comparison Experiment")
    print("Re-optimization vs Path Ratio Preservation")
    print("=" * 80)
    print()
    
    # Configuration
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    output_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    os.makedirs(output_dir, exist_ok=True)
    
    # Load arrival rate sequence
    print("Loading arrival rate sequence...")
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values  # Convert to numpy array
    num_steps, num_commodities = sequence.shape
    
    print(f"✓ Loaded {num_steps} time steps with {num_commodities} commodities")
    print(f"  Sequence range: Step 1 to Step {num_steps}")
    print(f"  Step 1 arrival rates: {sequence[0].tolist()}")
    print(f"  Step {num_steps} arrival rates: {sequence[-1].tolist()}")
    print(f"  (Sequence already scaled - Step 1 was multiplied by 0.6 before generation)")
    print()
    
    # Load configuration
    print("Loading configuration...")
    config = load_yaml_file(config_file)
    print(f"✓ Configuration loaded: {config['scenario_name']}")
    print()
    
    # Execute Strategy 1
    strategy1_stats, infeasible_steps = execute_strategy_reoptimization(
        sequence, config, output_dir
    )
    
    # Execute Strategy 2
    strategy2_stats = execute_strategy_path_ratio_preservation(
        sequence, config, output_dir
    )
    
    # Save statistics to CSV
    df1 = pd.DataFrame(strategy1_stats)
    df2 = pd.DataFrame(strategy2_stats)
    
    df1_file = os.path.join(output_dir, 'strategy1_stats.csv')
    df2_file = os.path.join(output_dir, 'strategy2_stats.csv')
    
    # Convert arrival_rates list to string for CSV
    df1['arrival_rates'] = df1['arrival_rates'].apply(lambda x: str(x))
    df2['arrival_rates'] = df2['arrival_rates'].apply(lambda x: str(x))
    
    df1.to_csv(df1_file, index=False)
    df2.to_csv(df2_file, index=False)
    
    print(f"\n✓ Statistics saved to:")
    print(f"  {df1_file}")
    print(f"  {df2_file}")
    
    # Generate comparison summary
    summary_data = []
    for i in range(len(strategy1_stats)):
        s1 = strategy1_stats[i]
        s2 = strategy2_stats[i]
        summary_data.append({
            'step_id': s1['step_id'],
            'strategy1_max_util': s1['max_link_utilization'],
            'strategy2_max_util': s2['max_link_utilization'],
            'util_diff': s1['max_link_utilization'] - s2['max_link_utilization'],
            'strategy1_pli': s1['pli'],
            'strategy2_pli': s2['pli'],
            'pli_diff': s1['pli'] - s2['pli'],
            'strategy1_delay': s1['avg_delay'],
            'strategy2_delay': s2['avg_delay'],
            'delay_diff': s1['avg_delay'] - s2['avg_delay'],
            'strategy1_optimizer_status': s1['optimizer_status']
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_file = os.path.join(output_dir, 'comparison_summary.csv')
    summary_df.to_csv(summary_file, index=False)
    print(f"  {summary_file}")
    
    # Generate plots
    print("\nGenerating comparison plots...")
    plot_comparison_results(strategy1_stats, strategy2_stats, output_dir)
    
    # Print summary
    print("\n" + "=" * 80)
    print("Experiment Summary")
    print("=" * 80)
    print(f"Strategy 1 (Re-optimization):")
    print(f"  Infeasible steps: {infeasible_steps if infeasible_steps else 'None'}")
    print(f"  Average Max Link Utilization: {np.mean([s['max_link_utilization'] for s in strategy1_stats]):.4f}%")
    print(f"  Average PLI: {np.mean([s['pli'] for s in strategy1_stats]):.4f}%")
    print(f"  Average Delay: {np.mean([s['avg_delay'] for s in strategy1_stats]):.6f}s")
    print()
    print(f"Strategy 2 (Path Ratio Preservation):")
    print(f"  Average Max Link Utilization: {np.mean([s['max_link_utilization'] for s in strategy2_stats]):.4f}%")
    print(f"  Average PLI: {np.mean([s['pli'] for s in strategy2_stats]):.4f}%")
    print(f"  Average Delay: {np.mean([s['avg_delay'] for s in strategy2_stats]):.6f}s")
    print()
    
    return {
        'strategy1_stats': strategy1_stats,
        'strategy2_stats': strategy2_stats,
        'infeasible_steps': infeasible_steps,
        'summary_df': summary_df
    }


if __name__ == '__main__':
    results = main()

