#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to analyze packet loss causes in simulation results.
Distinguishes between:
1. Buffer overflow drops (packets dropped at ports due to queue limits)
2. Time limit drops (packets still in transit when simulation ends)
"""

import sys
import os
import yaml

# Add the project directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_path)

from utils.libs import *
from topo.utils import load_yaml_file
from main.main import run_simulation_scenario
from port.port import Port
from modem.switch import SimplePacketSwitch, FairPacketSwitch

def analyze_packet_loss(scenario_name="80_lambda_our_model_2c", run_id=1):
    """
    Analyze packet loss for a specific scenario and run.
    
    Args:
        scenario_name: Name of the scenario
        run_id: Run number to analyze
    """
    # Load scenario configuration
    yaml_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'{scenario_name}.yaml')
    if not os.path.exists(yaml_path):
        # Try without .yaml extension
        yaml_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'{scenario_name}.yaml')
    
    config = load_yaml_file(yaml_path)
    
    # Verify configuration values
    buffer_size = config.get('simulation', {}).get('buffer_size', 'Unknown')
    obp_capacity = config.get('simulation', {}).get('obp_capacity', 'Unknown')
    arrival_rate = config.get('fixed_demand', {}).get('arrival_rate', 'Unknown')
    
    print(f"\n{'='*80}")
    print("CONFIGURATION VERIFICATION:")
    print(f"{'='*80}")
    print(f"  Buffer Size: {buffer_size} bytes")
    print(f"  OBP Capacity: {obp_capacity} packets/s")
    print(f"  Arrival Rate: {arrival_rate} packets/s")
    print(f"{'='*80}\n")
    
    # Get results directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(script_dir, '..')
    results_base_dir = os.path.join(src_dir, "results")
    result_dir = os.path.join(results_base_dir, scenario_name, f"run_{run_id}")
    
    # Run simulation to get fresh results
    print(f"Running simulation for {scenario_name}, run {run_id}...")
    np.random.seed(run_id - 1)  # Use run_id - 1 to match main.py behavior
    all_flows, switches, blocked_flows = run_simulation_scenario(config, result_dir, run_id - 1)
    
    print("\n" + "="*80)
    print("PACKET LOSS ANALYSIS")
    print("="*80)
    
    # 1. Calculate total packets sent and received
    total_sent = sum(flow.pkt_gen.packets_sent for flow in all_flows)
    total_received = sum(flow.pkt_sink.packets_received.get(flow.fid, 0) for flow in all_flows)
    total_lost = total_sent - total_received
    
    print(f"\n1. OVERALL STATISTICS:")
    print(f"   Total Packets Sent: {total_sent}")
    print(f"   Total Packets Received: {total_received}")
    print(f"   Total Packets Lost: {total_lost}")
    print(f"   PLI: {(total_lost / total_sent * 100) if total_sent > 0 else 0:.6f}%")
    
    # 2. Count buffer overflow drops from ports
    buffer_overflow_drops = 0
    port_drops_by_switch = {}
    port_drops_by_flow = {}
    
    print(f"\n2. BUFFER OVERFLOW DROPS (from Port queues):")
    for (x, y), switch in switches.items():
        if isinstance(switch, FairPacketSwitch):
            ports = switch.egress_ports
        elif isinstance(switch, SimplePacketSwitch):
            ports = switch.ports
        else:
            continue
        
        switch_drops = 0
        for port in ports:
            if isinstance(port, Port):
                port_drops = port.packets_dropped
                switch_drops += port_drops
                buffer_overflow_drops += port_drops
                
                # Count drops by flow
                for flow_id, drops in port.dropped_by_flow.items():
                    if flow_id not in port_drops_by_flow:
                        port_drops_by_flow[flow_id] = 0
                    port_drops_by_flow[flow_id] += drops
                
                if port_drops > 0:
                    print(f"   Switch ({x}, {y}), Port {port.element_id}: {port_drops} drops")
        
        if switch_drops > 0:
            port_drops_by_switch[(x, y)] = switch_drops
    
    print(f"\n   Total Buffer Overflow Drops: {buffer_overflow_drops}")
    
    # 3. Calculate time limit drops (packets still in transit)
    time_limit_drops = total_lost - buffer_overflow_drops
    
    print(f"\n3. TIME LIMIT DROPS (packets still in transit at simulation end):")
    print(f"   Time Limit Drops: {max(0, time_limit_drops)}")
    
    # 4. Check packets in queues at simulation end
    packets_in_queues = 0
    packets_in_ports = {}
    
    print(f"\n4. PACKETS STILL IN QUEUES AT SIMULATION END:")
    for (x, y), switch in switches.items():
        if isinstance(switch, FairPacketSwitch):
            ports = switch.egress_ports
        elif isinstance(switch, SimplePacketSwitch):
            ports = switch.ports
        else:
            continue
        
        for port in ports:
            if isinstance(port, Port):
                queue_length = len(port.store.items)
                if queue_length > 0:
                    packets_in_queues += queue_length
                    packets_in_ports[port.element_id] = queue_length
                    print(f"   Switch ({x}, {y}), Port {port.element_id}: {queue_length} packets in queue")
    
    print(f"\n   Total Packets in Queues: {packets_in_queues}")
    
    # 5. Check packets in transit (in wires/interlinks)
    # This is harder to track directly, but we can estimate
    estimated_in_transit = time_limit_drops - packets_in_queues
    
    print(f"\n5. ESTIMATED PACKETS IN TRANSIT (in wires/interlinks):")
    print(f"   Estimated: {max(0, estimated_in_transit)}")
    
    # 6. Summary by flow
    print(f"\n6. LOSS BREAKDOWN BY FLOW:")
    for flow in all_flows:
        flow_sent = flow.pkt_gen.packets_sent
        flow_received = flow.pkt_sink.packets_received.get(flow.fid, 0)
        flow_lost = flow_sent - flow_received
        flow_buffer_drops = port_drops_by_flow.get(flow.fid, 0)
        flow_time_drops = flow_lost - flow_buffer_drops
        
        print(f"\n   Flow {flow.fid} (Priority {flow.priority}):")
        print(f"      Sent: {flow_sent}, Received: {flow_received}, Lost: {flow_lost}")
        print(f"      Buffer Overflow: {flow_buffer_drops}")
        print(f"      Time Limit: {max(0, flow_time_drops)}")
    
    # 7. Final summary
    print(f"\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print(f"Total Lost: {total_lost}")
    print(f"  - Buffer Overflow: {buffer_overflow_drops} ({buffer_overflow_drops/total_lost*100 if total_lost > 0 else 0:.2f}%)")
    print(f"  - Time Limit: {max(0, time_limit_drops)} ({max(0, time_limit_drops)/total_lost*100 if total_lost > 0 else 0:.2f}%)")
    print(f"  - Still in Queues: {packets_in_queues}")
    print(f"  - Estimated in Transit: {max(0, estimated_in_transit)}")
    
    return {
        'total_sent': total_sent,
        'total_received': total_received,
        'total_lost': total_lost,
        'buffer_overflow_drops': buffer_overflow_drops,
        'time_limit_drops': max(0, time_limit_drops),
        'packets_in_queues': packets_in_queues,
        'estimated_in_transit': max(0, estimated_in_transit)
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze packet loss causes')
    parser.add_argument('--scenario', type=str, default='80_lambda_our_model_2c',
                        help='Scenario name to analyze')
    parser.add_argument('--run', type=int, default=1,
                        help='Run number to analyze')
    
    args = parser.parse_args()
    
    results = analyze_packet_loss(args.scenario, args.run)

