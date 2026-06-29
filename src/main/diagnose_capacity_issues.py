#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic script to check why there's no packet loss despite capacity violations.
"""

import sys
import os
import yaml
import pandas as pd

# Add the project directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_path)

from utils.libs import *
from topo.utils import load_yaml_file

def diagnose_capacity_issues(scenario_name="80_lambda_our_model_2c", run_id=1):
    """
    Diagnose why there's no packet loss despite capacity violations.
    """
    print("="*80)
    print("CAPACITY VIOLATION DIAGNOSIS")
    print("="*80)
    
    # Load YAML configuration
    yaml_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'{scenario_name}.yaml')
    config = load_yaml_file(yaml_path)
    
    # Get configuration values
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    buffer_size_yaml = config['simulation']['buffer_size']  # bytes
    limit_bytes_yaml = config['simulation']['limit_bytes']
    
    print(f"\n1. YAML CONFIGURATION:")
    print(f"   Interlink Capacity: {interlink_capacity:,} bits/s ({interlink_capacity/1e6:.2f} Mbit/s)")
    print(f"   Packet Size: {packet_size} bytes")
    print(f"   Buffer Size (YAML): {buffer_size_yaml} bytes")
    print(f"   Limit Bytes (YAML): {limit_bytes_yaml}")
    
    # Check simulator.py hardcoded values
    print(f"\n2. SIMULATOR HARDCODED VALUES (from simulator.py):")
    print(f"   ⚠️  buffer_size is HARDCODED to 1000 (not reading from YAML!)")
    print(f"   ⚠️  limit_bytes is HARDCODED to False (not reading from YAML!)")
    print(f"   ⚠️  obp_rate is HARDCODED to 1000000 (not reading from YAML!)")
    
    # Check optimization results
    result_dir = os.path.join(os.path.dirname(__file__), '..', 'results', scenario_name, f'run_{run_id}')
    mcfp_csv = os.path.join(result_dir, 'mcfp_results_flows_2_commodities.csv')
    
    if not os.path.exists(mcfp_csv):
        print(f"\n⚠️  MCFP results file not found: {mcfp_csv}")
        return
    
    df = pd.read_csv(mcfp_csv)
    
    print(f"\n3. OPTIMIZATION RESULTS ANALYSIS:")
    print(f"   Total paths: {len(df)}")
    
    # Parse paths and calculate interlink flows
    import re
    from collections import defaultdict
    
    def parse_path(path_str):
        pattern = r'OBPModule\((\d+),\s*(\d+)\)(?!_[ud])'
        matches = re.findall(pattern, path_str)
        interlinks = []
        for i in range(len(matches) - 1):
            src = tuple(map(int, matches[i]))
            dst = tuple(map(int, matches[i + 1]))
            if src != dst:
                interlinks.append((src, dst) if src < dst else (dst, src))
        return interlinks
    
    interlink_flows = defaultdict(float)
    for idx, row in df.iterrows():
        arrival_rate = row['Arrival Rate']  # packets/s
        path = row['Path']
        interlinks = parse_path(path)
        for interlink in interlinks:
            interlink_flows[interlink] += arrival_rate
    
    # Check violations
    max_allowed_packets_per_s = interlink_capacity / (packet_size * 8)
    violations = []
    
    print(f"\n   Max allowed packets/s per interlink: {max_allowed_packets_per_s:.2f}")
    print(f"\n   Top 10 interlinks by flow:")
    
    for interlink, flow_packets_per_s in sorted(interlink_flows.items(), key=lambda x: x[1], reverse=True)[:10]:
        flow_bits_per_s = flow_packets_per_s * packet_size * 8
        utilization = (flow_bits_per_s / interlink_capacity) * 100
        print(f"     {interlink}: {flow_packets_per_s:.2f} packets/s = {flow_bits_per_s:,.0f} bits/s ({utilization:.2f}%)")
        if utilization > 100:
            violations.append((interlink, utilization, flow_packets_per_s))
    
    if violations:
        print(f"\n   ⚠️  Found {len(violations)} interlinks exceeding capacity!")
        for interlink, util, flow in violations:
            print(f"      {interlink}: {util:.2f}% (flow: {flow:.2f} packets/s)")
    
    # Check why no packet loss
    print(f"\n4. WHY NO PACKET LOSS?")
    print(f"\n   a) Buffer Size Issue:")
    print(f"      - YAML config: {buffer_size_yaml} bytes")
    print(f"      - Simulator uses: 1000 bytes (HARDCODED)")
    print(f"      - Actual buffer can hold: {1000 / packet_size:.1f} packets")
    print(f"      - This is MUCH larger than YAML config!")
    
    print(f"\n   b) Limit Bytes Issue:")
    print(f"      - YAML config: {limit_bytes_yaml}")
    print(f"      - Simulator uses: False (HARDCODED)")
    print(f"      - This means buffer is packet-based, not byte-based!")
    
    print(f"\n   c) Port Rate:")
    print(f"      - Port rate should be: {interlink_capacity:,} bits/s")
    print(f"      - This should limit transmission rate")
    print(f"      - But if buffer is large enough, packets can queue without dropping")
    
    print(f"\n   d) Optimization Constraint Violation:")
    print(f"      - Optimization found solution with capacity violations")
    print(f"      - This suggests constraint may not be properly enforced")
    print(f"      - Or solver allowed OPTIMAL_INACCURATE status")
    
    print(f"\n5. RECOMMENDATIONS:")
    print(f"   1. Fix simulator.py to read buffer_size from YAML config")
    print(f"   2. Fix simulator.py to read limit_bytes from YAML config")
    print(f"   3. Check why optimization allows capacity violations")
    print(f"   4. Verify port rate is correctly applied in simulation")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnose capacity issues')
    parser.add_argument('--scenario', type=str, default='80_lambda_our_model_2c',
                        help='Scenario name')
    parser.add_argument('--run', type=int, default=1,
                        help='Run number')
    
    args = parser.parse_args()
    
    diagnose_capacity_issues(args.scenario, args.run)

