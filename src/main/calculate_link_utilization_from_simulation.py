#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to calculate link utilization from simulation results (port statistics).
This calculates utilization based on actual packets sent through ports during simulation,
rather than from optimization results.
"""

import sys
import os
import pandas as pd
import numpy as np

# Add the project directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_path)

from utils.libs import *
from topo.utils import load_yaml_file
from main import run_simulation_scenario
from port.port import Port
from modem.switch import SimplePacketSwitch, FairPacketSwitch


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
    # Get source coordinates from the switch
    src_coords = switch_coords
    
    # Get destination coordinates from port.out
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


def calculate_link_utilization_from_simulation(scenario_name="80_lambda_our_model_2c", run_id=1):
    """
    Calculate link utilization from simulation port statistics.
    """
    # Load YAML configuration
    yaml_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'{scenario_name}.yaml')
    config = load_yaml_file(yaml_path)
    
    # Get configuration parameters
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    simulation_time = config['simulation']['simulation_time']  # ms
    generation_finish_time = config['simulation']['generation_finish_time']  # ms
    time_unit = config['system'].get('time_unit', 'ms')
    
    # Convert time to seconds
    if time_unit == 'ms':
        effective_time = generation_finish_time / 1000.0  # Convert ms to seconds
    else:
        effective_time = generation_finish_time  # Already in seconds
    
    # Get results directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(script_dir, '..')
    results_base_dir = os.path.join(src_dir, "results")
    result_dir = os.path.join(results_base_dir, scenario_name, f"run_{run_id}")
    
    print("\n" + "="*80)
    print("LINK UTILIZATION FROM SIMULATION (PORT STATISTICS)")
    print("="*80)
    print(f"\nScenario: {scenario_name}, Run: {run_id}")
    print(f"Interlink Capacity: {interlink_capacity:,} bits/s ({interlink_capacity/1e6:.2f} Mbit/s)")
    print(f"Packet Size: {packet_size} bytes")
    print(f"Simulation Time: {simulation_time} {time_unit}")
    print(f"Generation Finish Time: {generation_finish_time} {time_unit}")
    print(f"Effective Time (for bit rate calculation): {effective_time:.3f} seconds")
    
    # Run simulation to get switches (or load existing results)
    print(f"\nLoading simulation results...")
    np.random.seed(run_id - 1)
    all_flows, switches, blocked_flows = run_simulation_scenario(config, result_dir, run_id - 1)
    
    # Dictionary to store traffic on each interlink
    # Key: (src_coords, dst_coords) tuple, Value: port statistics
    interlink_traffic = {}
    
    print("\n" + "="*80)
    print("COLLECTING PORT STATISTICS")
    print("="*80)
    
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
            packets_dropped = port.packets_dropped
            
            # Calculate bit rate
            bit_rate = (packets_sent / effective_time) * packet_size * 8  # bits/s
            
            # Store statistics
            if interlink not in interlink_traffic:
                interlink_traffic[interlink] = {
                    'packets_sent': 0,
                    'packets_dropped': 0,
                    'bit_rate': 0.0,
                    'ports': []
                }
            
            interlink_traffic[interlink]['packets_sent'] += packets_sent
            interlink_traffic[interlink]['packets_dropped'] += packets_dropped
            interlink_traffic[interlink]['bit_rate'] += bit_rate
            interlink_traffic[interlink]['ports'].append({
                'switch': (x, y),
                'port_id': port.element_id,
                'packets_sent': packets_sent,
                'packets_dropped': packets_dropped
            })
    
    # Calculate utilization for each interlink
    print("\n" + "="*80)
    print("INTERLINK UTILIZATION (from simulation port statistics)")
    print("="*80)
    
    utilizations = []
    
    for interlink, stats in sorted(interlink_traffic.items(), key=lambda x: x[1]['bit_rate'], reverse=True):
        bit_rate = stats['bit_rate']
        utilization = (bit_rate / interlink_capacity) * 100
        
        utilizations.append({
            'interlink': interlink,
            'packets_sent': stats['packets_sent'],
            'packets_dropped': stats['packets_dropped'],
            'bit_rate': bit_rate,
            'utilization': utilization
        })
        
        print(f"\nInterlink {interlink[0]} → {interlink[1]}:")
        print(f"   Packets Sent: {stats['packets_sent']:,}")
        print(f"   Packets Dropped: {stats['packets_dropped']:,}")
        print(f"   Bit Rate: {bit_rate:,.2f} bits/s ({bit_rate/1e6:.4f} Mbit/s)")
        print(f"   Utilization: {utilization:.4f}%")
        print(f"   Ports: {len(stats['ports'])} port(s)")
    
    # Find maximum utilization
    if utilizations:
        max_util = max(utilizations, key=lambda x: x['utilization'])
        
        print("\n" + "="*80)
        print("MAXIMUM LINK UTILIZATION (from simulation)")
        print("="*80)
        print(f"Maximum Utilization: {max_util['utilization']:.4f}%")
        print(f"Interlink: {max_util['interlink'][0]} → {max_util['interlink'][1]}")
        print(f"Bit Rate: {max_util['bit_rate']:,.2f} bits/s ({max_util['bit_rate']/1e6:.4f} Mbit/s)")
        print(f"Capacity: {interlink_capacity:,} bits/s ({interlink_capacity/1e6:.2f} Mbit/s)")
        print(f"Packets Sent: {max_util['packets_sent']:,}")
        print(f"Packets Dropped: {max_util['packets_dropped']:,}")
        
        # Save results to CSV
        df_util = pd.DataFrame(utilizations)
        csv_path = os.path.join(result_dir, 'link_utilization_from_simulation.csv')
        df_util.to_csv(csv_path, index=False)
        print(f"\nResults saved to: {csv_path}")
        
        return max_util
    else:
        print("\nNo interlink traffic found!")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate link utilization from simulation port statistics')
    parser.add_argument('--scenario', type=str, default='80_lambda_our_model_2c',
                        help='Scenario name to analyze')
    parser.add_argument('--run', type=int, default=1,
                        help='Run number to analyze')
    
    args = parser.parse_args()
    
    result = calculate_link_utilization_from_simulation(args.scenario, args.run)

