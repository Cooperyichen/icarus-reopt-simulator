#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to calculate maximum link utilization from simulation results.
Uses port traffic statistics and interlink capacity from CSV files and YAML configuration.
"""

import sys
import os
import pandas as pd
import numpy as np
import re

# Add the project directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_path)

from utils.libs import *
from topo.utils import load_yaml_file
from main import run_simulation_scenario
from port.port import Port
from modem.switch import SimplePacketSwitch, FairPacketSwitch

def parse_path(path_str):
    """
    Parse a path string to extract interlinks (only between OBP modules, not uplinks/downlinks).
    Example: "OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(1, 0) -> ..."
    Returns list of interlink tuples: [(src_module, dst_module), ...]
    Only includes links between different OBP modules (not uplink/downlink connections).
    """
    # Extract OBP modules from path (excluding uplink/downlink nodes)
    # Pattern matches: OBPModule(x, y) but not OBPModule(x, y)_uplink_0 or _downlink_0
    pattern = r'OBPModule\((\d+),\s*(\d+)\)(?!_[ud])'
    matches = re.findall(pattern, path_str)
    
    interlinks = []
    for i in range(len(matches) - 1):
        src = tuple(map(int, matches[i]))
        dst = tuple(map(int, matches[i + 1]))
        # Only add if src and dst are different (actual interlink, not same module)
        if src != dst:
            interlinks.append((src, dst))
    
    return interlinks

def calculate_link_utilization(scenario_name="80_lambda_our_model_2c", run_id=1):
    """
    Calculate maximum link utilization from simulation results.
    """
    # Load YAML configuration
    yaml_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'{scenario_name}.yaml')
    config = load_yaml_file(yaml_path)
    
    # Get interlink capacity (in bits/s)
    interlink_capacity = config['system']['interlink_capacity']  # 10,000,000 bits/s = 10 Mbit/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    simulation_time = config['simulation']['simulation_time']  # ms
    generation_finish_time = config['simulation']['generation_finish_time']  # ms
    
    # Get results directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(script_dir, '..')
    results_base_dir = os.path.join(src_dir, "results")
    result_dir = os.path.join(results_base_dir, scenario_name, f"run_{run_id}")
    
    # Load MCFP results to get path allocations
    mcfp_csv = os.path.join(result_dir, 'mcfp_results_flows_2_commodities.csv')
    if not os.path.exists(mcfp_csv):
        print(f"Error: MCFP results file not found: {mcfp_csv}")
        return None
    
    df_mcfp = pd.read_csv(mcfp_csv)
    
    # Check if results already exist - if so, use them instead of re-running
    # This ensures we use the same results that were already generated
    switches = None  # Initialize switches variable
    if os.path.exists(mcfp_csv):
        print(f"Using existing simulation results for {scenario_name}, run {run_id}...")
        # Load existing results without re-running simulation
        # Note: We only need MCFP results for link utilization calculation
        # Port statistics section will be skipped if switches is None
        pass
    else:
        # Run simulation to get port statistics (only if results don't exist)
        print(f"Running simulation for {scenario_name}, run {run_id}...")
        np.random.seed(run_id - 1)
        all_flows, switches, blocked_flows = run_simulation_scenario(config, result_dir, run_id - 1)
    
    print("\n" + "="*80)
    print("LINK UTILIZATION ANALYSIS")
    print("="*80)
    
    # Dictionary to store traffic on each interlink
    # Key: (src_module, dst_module) tuple, Value: total bits transmitted
    interlink_traffic = {}
    
    # Method 1: Calculate from MCFP results (optimization allocation)
    print("\n1. CALCULATING TRAFFIC FROM OPTIMIZATION RESULTS:")
    print(f"   Interlink Capacity: {interlink_capacity:,} bits/s ({interlink_capacity/1e6:.2f} Mbit/s)")
    print(f"   Packet Size: {packet_size} bytes")
    print(f"   Simulation Time: {simulation_time} ms")
    print(f"   Generation Time: {generation_finish_time} ms")
    
    # Calculate effective simulation time for traffic generation
    effective_time = generation_finish_time / 1000.0  # Convert ms to seconds
    
    for idx, row in df_mcfp.iterrows():
        arrival_rate = row['Arrival Rate']  # packets/s
        path = row['Path']
        
        # Parse path to get interlinks
        interlinks = parse_path(path)
        
        # Calculate bits transmitted on each interlink
        # bits = packets/s * packet_size (bytes) * 8 (bits/byte) * time (s)
        bits_transmitted = arrival_rate * packet_size * 8 * effective_time
        
        for interlink in interlinks:
            # DO NOT normalize interlink direction - each direction has independent capacity
            # Interlinks are bidirectional, but each direction has its own capacity limit
            # So we should track traffic for each direction separately
            key = interlink  # Keep original direction
            
            if key not in interlink_traffic:
                interlink_traffic[key] = 0
            interlink_traffic[key] += bits_transmitted
    
    # Method 2: Calculate from actual port statistics (simulation results)
    print("\n2. CALCULATING TRAFFIC FROM PORT STATISTICS:")
    port_traffic = {}
    
    if switches is None:
        print("   (Skipped - using optimization results only)")
    else:
        for (x, y), switch in switches.items():
            if isinstance(switch, FairPacketSwitch):
                ports = switch.egress_ports
            elif isinstance(switch, SimplePacketSwitch):
                ports = switch.ports
            else:
                continue
            
            for port in ports:
                if isinstance(port, Port):
                    # Get packets transmitted through this port
                    packets_transmitted = port.packets_received - port.packets_dropped
                    bits_transmitted = packets_transmitted * packet_size * 8
                    
                    # Try to identify which interlink this port belongs to
                    # This is approximate since we need to map ports to interlinks
                    port_traffic[port.element_id] = {
                        'packets': packets_transmitted,
                        'bits': bits_transmitted,
                        'switch': (x, y)
                    }
    
    # Calculate utilization for each interlink
    print("\n3. INTERLINK UTILIZATION (from optimization results):")
    utilizations = []
    
    for interlink, bits in interlink_traffic.items():
        # Calculate average bit rate
        bit_rate = bits / effective_time  # bits/s
        
        # Calculate utilization percentage
        utilization = (bit_rate / interlink_capacity) * 100
        
        utilizations.append({
            'interlink': interlink,
            'bits_transmitted': bits,
            'bit_rate': bit_rate,
            'utilization': utilization
        })
        
        print(f"   Interlink {interlink[0]} <-> {interlink[1]}:")
        print(f"      Bits Transmitted: {bits:,.0f} bits")
        print(f"      Average Bit Rate: {bit_rate:,.2f} bits/s ({bit_rate/1e6:.4f} Mbit/s)")
        print(f"      Utilization: {utilization:.4f}%")
    
    # Find maximum utilization
    if utilizations:
        max_util = max(utilizations, key=lambda x: x['utilization'])
        
        print("\n" + "="*80)
        print("MAXIMUM LINK UTILIZATION:")
        print("="*80)
        print(f"Maximum Utilization: {max_util['utilization']:.4f}%")
        print(f"Interlink: {max_util['interlink'][0]} <-> {max_util['interlink'][1]}")
        print(f"Bit Rate: {max_util['bit_rate']:,.2f} bits/s ({max_util['bit_rate']/1e6:.4f} Mbit/s)")
        print(f"Capacity: {interlink_capacity:,} bits/s ({interlink_capacity/1e6:.2f} Mbit/s)")
        
        # Save results to CSV
        df_util = pd.DataFrame(utilizations)
        csv_path = os.path.join(result_dir, 'link_utilization.csv')
        df_util.to_csv(csv_path, index=False)
        print(f"\nResults saved to: {csv_path}")
        
        return max_util
    else:
        print("\nNo interlink traffic found!")
        return None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate maximum link utilization')
    parser.add_argument('--scenario', type=str, default='80_lambda_our_model_2c',
                        help='Scenario name to analyze')
    parser.add_argument('--run', type=int, default=1,
                        help='Run number to analyze')
    
    args = parser.parse_args()
    
    result = calculate_link_utilization(args.scenario, args.run)

