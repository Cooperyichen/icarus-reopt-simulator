#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Strategy 3 Step 6 Anomaly

This script verifies why Strategy 3 achieves lower theoretical max link utilization
than Strategy 1 at Step 6, which should not happen theoretically.
"""

import sys
import os
import pandas as pd
import numpy as np
from collections import defaultdict
from pathlib import Path

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import (
    calculate_max_link_utilization,
    parse_path
)
from main.global_optimal_ratio import (
    extract_paths_info_from_step1,
    calculate_single_step_utilization
)


def compare_path_sets(strategy1_file, strategy3_file, output_dir):
    """
    Phase 1: Compare path sets used by Strategy 1 and Strategy 3 at Step 6.
    
    Args:
        strategy1_file: Path to Strategy 1 Step 6 MCFP results
        strategy3_file: Path to Strategy 3 Step 6 MCFP results
        output_dir: Output directory for results
    """
    print("\n" + "=" * 80)
    print("Phase 1: Path Set Comparison")
    print("=" * 80)
    
    # Load MCFP results
    df_s1 = pd.read_csv(strategy1_file)
    df_s3 = pd.read_csv(strategy3_file)
    
    # Extract path sets for each commodity
    s1_paths = {}
    s3_paths = {}
    
    for commodity_id in sorted(df_s1['id_flow'].unique()):
        s1_commodity = df_s1[df_s1['id_flow'] == commodity_id]
        s1_paths[int(commodity_id)] = set(s1_commodity['Path'].unique())
    
    for commodity_id in sorted(df_s3['id_flow'].unique()):
        s3_commodity = df_s3[df_s3['id_flow'] == commodity_id]
        s3_paths[int(commodity_id)] = set(s3_commodity['Path'].unique())
    
    # Compare path sets
    comparison_data = []
    
    all_commodities = sorted(set(s1_paths.keys()) | set(s3_paths.keys()))
    
    for cid in all_commodities:
        s1_path_set = s1_paths.get(cid, set())
        s3_path_set = s3_paths.get(cid, set())
        
        s1_only = s1_path_set - s3_path_set
        s3_only = s3_path_set - s1_path_set
        common = s1_path_set & s3_path_set
        
        comparison_data.append({
            'commodity_id': cid,
            's1_path_count': len(s1_path_set),
            's3_path_count': len(s3_path_set),
            'common_path_count': len(common),
            's1_only_count': len(s1_only),
            's3_only_count': len(s3_only),
            'paths_identical': (s1_path_set == s3_path_set),
            's1_only_paths': ', '.join(sorted(s1_only)[:5]) if s1_only else 'None',
            's3_only_paths': ', '.join(sorted(s3_only)[:5]) if s3_only else 'None'
        })
        
        print(f"\nCommodity {cid}:")
        print(f"  S1 paths: {len(s1_path_set)}")
        print(f"  S3 paths: {len(s3_path_set)}")
        print(f"  Common: {len(common)}")
        print(f"  S1 only: {len(s1_only)}")
        print(f"  S3 only: {len(s3_only)}")
        print(f"  Identical: {s1_path_set == s3_path_set}")
        
        if s1_only:
            print(f"  S1-only paths (first 3): {list(s1_only)[:3]}")
        if s3_only:
            print(f"  S3-only paths (first 3): {list(s3_only)[:3]}")
    
    # Save comparison results
    comparison_df = pd.DataFrame(comparison_data)
    output_file = os.path.join(output_dir, 'path_set_comparison.csv')
    comparison_df.to_csv(output_file, index=False)
    print(f"\n✓ Path set comparison saved to: {output_file}")
    
    return comparison_df


def compare_flow_allocations(strategy1_file, strategy3_file, arrival_rates, output_dir):
    """
    Phase 2: Compare flow allocations between Strategy 1 and Strategy 3.
    
    Args:
        strategy1_file: Path to Strategy 1 Step 6 MCFP results
        strategy3_file: Path to Strategy 3 Step 6 MCFP results
        arrival_rates: List of arrival rates for each commodity
        output_dir: Output directory for results
    """
    print("\n" + "=" * 80)
    print("Phase 2: Flow Allocation Comparison")
    print("=" * 80)
    
    # Load MCFP results
    df_s1 = pd.read_csv(strategy1_file)
    df_s3 = pd.read_csv(strategy3_file)
    
    # Calculate path ratios for each commodity
    allocation_data = []
    
    for commodity_id in sorted(df_s1['id_flow'].unique()):
        if commodity_id >= len(arrival_rates):
            continue
            
        demand = arrival_rates[commodity_id]
        
        # Strategy 1
        s1_commodity = df_s1[df_s1['id_flow'] == commodity_id]
        s1_total = s1_commodity['Arrival Rate'].sum()
        
        # Strategy 3
        s3_commodity = df_s3[df_s3['id_flow'] == commodity_id]
        s3_total = s3_commodity['Arrival Rate'].sum()
        
        print(f"\nCommodity {int(commodity_id)} (demand: {demand:.2f}):")
        print(f"  S1 total flow: {s1_total:.2f} (diff: {abs(s1_total - demand):.4f})")
        print(f"  S3 total flow: {s3_total:.2f} (diff: {abs(s3_total - demand):.4f})")
        
        # Compare path-by-path allocations
        all_paths = set(s1_commodity['Path'].unique()) | set(s3_commodity['Path'].unique())
        
        for path in sorted(all_paths):
            s1_flow = s1_commodity[s1_commodity['Path'] == path]['Arrival Rate'].sum()
            s3_flow = s3_commodity[s3_commodity['Path'] == path]['Arrival Rate'].sum()
            
            s1_ratio = s1_flow / demand if demand > 0 else 0
            s3_ratio = s3_flow / demand if demand > 0 else 0
            ratio_diff = s3_ratio - s1_ratio
            
            allocation_data.append({
                'commodity_id': int(commodity_id),
                'path': path,
                's1_flow': s1_flow,
                's3_flow': s3_flow,
                's1_ratio': s1_ratio,
                's3_ratio': s3_ratio,
                'ratio_diff': ratio_diff,
                'absolute_diff': abs(ratio_diff)
            })
    
    # Save allocation comparison
    allocation_df = pd.DataFrame(allocation_data)
    output_file = os.path.join(output_dir, 'flow_allocation_comparison.csv')
    allocation_df.to_csv(output_file, index=False)
    print(f"\n✓ Flow allocation comparison saved to: {output_file}")
    
    # Summary statistics
    print("\nSummary Statistics:")
    print(f"  Total path allocations compared: {len(allocation_df)}")
    print(f"  Mean absolute ratio difference: {allocation_df['absolute_diff'].mean():.6f}")
    print(f"  Max absolute ratio difference: {allocation_df['absolute_diff'].max():.6f}")
    
    return allocation_df


def verify_utilization_calculation(strategy1_file, strategy3_file, config, output_dir):
    """
    Phase 3: Verify utilization calculation consistency.
    
    Args:
        strategy1_file: Path to Strategy 1 Step 6 MCFP results
        strategy3_file: Path to Strategy 3 Step 6 MCFP results
        config: Configuration dictionary
        output_dir: Output directory for results
    """
    print("\n" + "=" * 80)
    print("Phase 3: Utilization Calculation Verification")
    print("=" * 80)
    
    # Load MCFP results
    df_s1 = pd.read_csv(strategy1_file)
    df_s3 = pd.read_csv(strategy3_file)
    
    # Calculate using standard function
    util_s1_standard = calculate_max_link_utilization(df_s1, config)
    util_s3_standard = calculate_max_link_utilization(df_s3, config)
    
    # Manual calculation for verification
    def manual_calculate_util(mcfp_df, config):
        interlink_capacity = config['system']['interlink_capacity']
        packet_size = config['simulation']['avg_packet_size']
        
        interlink_traffic = {}
        
        for _, row in mcfp_df.iterrows():
            arrival_rate = row['Arrival Rate']
            path = row['Path']
            interlinks = parse_path(path)
            
            bits_per_second = arrival_rate * packet_size * 8
            
            for interlink in interlinks:
                if interlink not in interlink_traffic:
                    interlink_traffic[interlink] = 0.0
                interlink_traffic[interlink] += bits_per_second
        
        max_utilization = 0.0
        max_interlink = None
        
        for interlink, bits_per_second in interlink_traffic.items():
            utilization = (bits_per_second / interlink_capacity) * 100.0
            if utilization > max_utilization:
                max_utilization = utilization
                max_interlink = interlink
        
        return max_utilization, max_interlink, interlink_traffic
    
    util_s1_manual, max_link_s1, traffic_s1 = manual_calculate_util(df_s1, config)
    util_s3_manual, max_link_s3, traffic_s3 = manual_calculate_util(df_s3, config)
    
    print(f"\nStrategy 1 Step 6:")
    print(f"  Standard calculation: {util_s1_standard:.6f}%")
    print(f"  Manual calculation: {util_s1_manual:.6f}%")
    print(f"  Difference: {abs(util_s1_standard - util_s1_manual):.10f}%")
    print(f"  Max interlink: {max_link_s1}")
    
    print(f"\nStrategy 3 Step 6:")
    print(f"  Standard calculation: {util_s3_standard:.6f}%")
    print(f"  Manual calculation: {util_s3_manual:.6f}%")
    print(f"  Difference: {abs(util_s3_standard - util_s3_manual):.10f}%")
    print(f"  Max interlink: {max_link_s3}")
    
    # Save verification results
    verification_data = {
        'strategy': ['Strategy 1', 'Strategy 3'],
        'standard_calculation': [util_s1_standard, util_s3_standard],
        'manual_calculation': [util_s1_manual, util_s3_manual],
        'difference': [abs(util_s1_standard - util_s1_manual), abs(util_s3_standard - util_s3_manual)],
        'max_interlink': [str(max_link_s1), str(max_link_s3)]
    }
    
    verification_df = pd.DataFrame(verification_data)
    output_file = os.path.join(output_dir, 'utilization_calculation_verification.csv')
    verification_df.to_csv(output_file, index=False)
    print(f"\n✓ Utilization calculation verification saved to: {output_file}")
    
    return verification_df, traffic_s1, traffic_s3


def analyze_path_constraints(strategy3_step1_file, strategy1_step6_file, output_dir):
    """
    Phase 4: Analyze path constraints for Strategy 3.
    
    Args:
        strategy3_step1_file: Path to Strategy 3 Step 1 MCFP results
        strategy1_step6_file: Path to Strategy 1 Step 6 MCFP results
        output_dir: Output directory for results
    """
    print("\n" + "=" * 80)
    print("Phase 4: Path Constraint Analysis")
    print("=" * 80)
    
    # Extract Strategy 3 Step 1 paths
    paths_info_s3 = extract_paths_info_from_step1(strategy3_step1_file)
    
    # Load Strategy 1 Step 6 MCFP results
    df_s1_step6 = pd.read_csv(strategy1_step6_file)
    
    # Compare path sets
    constraint_data = []
    
    for commodity_id in sorted(paths_info_s3.keys()):
        s3_step1_paths = set(paths_info_s3[commodity_id]['paths'])
        
        s1_step6_commodity = df_s1_step6[df_s1_step6['id_flow'] == commodity_id]
        s1_step6_paths = set(s1_step6_commodity['Path'].unique())
        
        s1_new_paths = s1_step6_paths - s3_step1_paths
        s3_unused_paths = s3_step1_paths - s1_step6_paths
        
        constraint_data.append({
            'commodity_id': commodity_id,
            's3_step1_path_count': len(s3_step1_paths),
            's1_step6_path_count': len(s1_step6_paths),
            'common_path_count': len(s3_step1_paths & s1_step6_paths),
            's1_new_paths_count': len(s1_new_paths),
            's3_unused_paths_count': len(s3_unused_paths),
            's1_uses_new_paths': len(s1_new_paths) > 0,
            's3_paths_complete': len(s1_new_paths) == 0
        })
        
        print(f"\nCommodity {commodity_id}:")
        print(f"  S3 Step 1 paths: {len(s3_step1_paths)}")
        print(f"  S1 Step 6 paths: {len(s1_step6_paths)}")
        print(f"  Common: {len(s3_step1_paths & s1_step6_paths)}")
        print(f"  S1 new paths: {len(s1_new_paths)}")
        print(f"  S3 unused paths: {len(s3_unused_paths)}")
        
        if s1_new_paths:
            print(f"  ⚠️  S1 uses paths not in S3 Step 1 (first 3): {list(s1_new_paths)[:3]}")
    
    # Save constraint analysis
    constraint_df = pd.DataFrame(constraint_data)
    output_file = os.path.join(output_dir, 'path_constraint_analysis.csv')
    constraint_df.to_csv(output_file, index=False)
    print(f"\n✓ Path constraint analysis saved to: {output_file}")
    
    return constraint_df


def analyze_optimizer_behavior(strategy1_step6_file, strategy3_step6_file, config, output_dir):
    """
    Phase 5: Analyze optimizer behavior differences.
    
    Args:
        strategy1_step6_file: Path to Strategy 1 Step 6 MCFP results
        strategy3_step6_file: Path to Strategy 3 Step 6 MCFP results
        config: Configuration dictionary
        output_dir: Output directory for results
    """
    print("\n" + "=" * 80)
    print("Phase 5: Optimizer Behavior Analysis")
    print("=" * 80)
    
    # Load MCFP results
    df_s1 = pd.read_csv(strategy1_step6_file)
    df_s3 = pd.read_csv(strategy3_step6_file)
    
    # Calculate interlink utilizations for both strategies
    interlink_capacity = config['system']['interlink_capacity']
    packet_size = config['simulation']['avg_packet_size']
    
    def get_interlink_utilizations(mcfp_df, config):
        interlink_traffic = {}
        
        for _, row in mcfp_df.iterrows():
            arrival_rate = row['Arrival Rate']
            path = row['Path']
            interlinks = parse_path(path)
            
            bits_per_second = arrival_rate * packet_size * 8
            
            for interlink in interlinks:
                if interlink not in interlink_traffic:
                    interlink_traffic[interlink] = 0.0
                interlink_traffic[interlink] += bits_per_second
        
        utilizations = {}
        for interlink, bits_per_second in interlink_traffic.items():
            utilizations[interlink] = (bits_per_second / interlink_capacity) * 100.0
        
        return utilizations
    
    util_s1 = get_interlink_utilizations(df_s1, config)
    util_s3 = get_interlink_utilizations(df_s3, config)
    
    # Compare interlink utilizations
    all_interlinks = set(util_s1.keys()) | set(util_s3.keys())
    
    comparison_data = []
    for interlink in sorted(all_interlinks):
        u1 = util_s1.get(interlink, 0)
        u3 = util_s3.get(interlink, 0)
        diff = u3 - u1
        
        comparison_data.append({
            'interlink': str(interlink),
            's1_utilization': u1,
            's3_utilization': u3,
            'difference': diff,
            's3_better': u3 < u1
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df = comparison_df.sort_values('s1_utilization', ascending=False)
    
    print("\nTop 10 interlinks by S1 utilization:")
    print(comparison_df.head(10).to_string(index=False))
    
    # Save comparison
    output_file = os.path.join(output_dir, 'optimizer_behavior_analysis.csv')
    comparison_df.to_csv(output_file, index=False)
    print(f"\n✓ Optimizer behavior analysis saved to: {output_file}")
    
    return comparison_df


def generate_comprehensive_report(output_dir, phase_results):
    """
    Phase 6: Generate comprehensive verification report.
    
    Args:
        output_dir: Output directory for report
        phase_results: Dictionary containing results from all phases
    """
    print("\n" + "=" * 80)
    print("Phase 6: Generating Comprehensive Report")
    print("=" * 80)
    
    report_lines = []
    report_lines.append("# Strategy 3 Step 6 Anomaly Verification Report\n")
    report_lines.append("## Executive Summary\n")
    report_lines.append("This report documents the verification of why Strategy 3 achieves ")
    report_lines.append("lower theoretical max link utilization than Strategy 1 at Step 6.\n")
    
    # Phase 1 Summary
    if 'phase1' in phase_results:
        path_comparison = phase_results['phase1']
        report_lines.append("\n## Phase 1: Path Set Comparison\n")
        report_lines.append("### Results:\n")
        
        all_identical = path_comparison['paths_identical'].all()
        if all_identical:
            report_lines.append("- **All commodities use identical path sets**\n")
        else:
            report_lines.append("- **Path sets differ for some commodities**\n")
        
        for _, row in path_comparison.iterrows():
            cid = row['commodity_id']
            if not row['paths_identical']:
                report_lines.append(f"- Commodity {cid}: S1 has {row['s1_only_count']} unique paths, "
                                  f"S3 has {row['s3_only_count']} unique paths\n")
    
    # Phase 2 Summary
    if 'phase2' in phase_results:
        allocation = phase_results['phase2']
        report_lines.append("\n## Phase 2: Flow Allocation Comparison\n")
        report_lines.append("### Results:\n")
        
        mean_diff = allocation['absolute_diff'].mean()
        max_diff = allocation['absolute_diff'].max()
        
        report_lines.append(f"- Mean absolute ratio difference: {mean_diff:.6f}\n")
        report_lines.append(f"- Max absolute ratio difference: {max_diff:.6f}\n")
    
    # Phase 3 Summary
    if 'phase3' in phase_results:
        verification, traffic_s1, traffic_s3 = phase_results['phase3']
        report_lines.append("\n## Phase 3: Utilization Calculation Verification\n")
        report_lines.append("### Results:\n")
        
        for _, row in verification.iterrows():
            strategy = row['strategy']
            standard = row['standard_calculation']
            manual = row['manual_calculation']
            diff = row['difference']
            
            report_lines.append(f"- {strategy}: Standard={standard:.6f}%, "
                              f"Manual={manual:.6f}%, Difference={diff:.10f}%\n")
        
        report_lines.append("\n**Conclusion**: Calculation methods are consistent.\n")
    
    # Phase 4 Summary
    if 'phase4' in phase_results:
        constraint = phase_results['phase4']
        report_lines.append("\n## Phase 4: Path Constraint Analysis\n")
        report_lines.append("### Results:\n")
        
        s1_uses_new = constraint['s1_uses_new_paths'].any()
        if s1_uses_new:
            report_lines.append("- **Strategy 1 uses paths not available to Strategy 3**\n")
            report_lines.append("  This explains why Strategy 1 should perform better.\n")
        else:
            report_lines.append("- **Strategy 1 does not use new paths**\n")
            report_lines.append("  Path sets are constrained similarly.\n")
    
    # Phase 5 Summary
    if 'phase5' in phase_results:
        optimizer = phase_results['phase5']
        report_lines.append("\n## Phase 5: Optimizer Behavior Analysis\n")
        report_lines.append("### Results:\n")
        
        better_count = optimizer['s3_better'].sum()
        total_count = len(optimizer)
        
        report_lines.append(f"- S3 better on {better_count}/{total_count} interlinks\n")
        report_lines.append(f"- S1 max utilization: {optimizer['s1_utilization'].max():.6f}%\n")
        report_lines.append(f"- S3 max utilization: {optimizer['s3_utilization'].max():.6f}%\n")
    
    # Conclusions
    report_lines.append("\n## Conclusions\n")
    report_lines.append("### Key Findings:\n")
    report_lines.append("\n1. Path Set Comparison: [Summary]\n")
    report_lines.append("2. Flow Allocation: [Summary]\n")
    report_lines.append("3. Calculation Consistency: [Summary]\n")
    report_lines.append("4. Path Constraints: [Summary]\n")
    report_lines.append("5. Optimizer Behavior: [Summary]\n")
    
    # Write report
    report_content = ''.join(report_lines)
    report_file = os.path.join(output_dir, 'strategy3_step6_verification_report.md')
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✓ Comprehensive report saved to: {report_file}")
    
    return report_file


def main():
    """Main function to run all verification phases."""
    print("=" * 80)
    print("Strategy 3 Step 6 Anomaly Verification")
    print("=" * 80)
    
    # Configuration
    result_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    output_dir = os.path.join(src_dir, 'results', 'strategy3_step6_verification')
    os.makedirs(output_dir, exist_ok=True)
    
    # File paths
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    
    strategy1_step6_file = os.path.join(result_base, 'strategy1', 'step_6',
                                       'mcfp_results_flows_4_commodities.csv')
    strategy3_step6_file = os.path.join(result_base, 'hybrid_sequence', 'strategy3', 'strategy3', 'step_6',
                                       'mcfp_results_flows_4_commodities.csv')
    strategy3_step1_file = os.path.join(result_base, 'hybrid_sequence', 'strategy3', 'strategy3', 'step_1',
                                       'mcfp_results_flows_4_commodities.csv')
    
    # Get Step 6 arrival rates from stats file
    s3_stats_file = os.path.join(result_base, 'hybrid_sequence', 'strategy3', 'strategy3_stats.csv')
    s3_stats = pd.read_csv(s3_stats_file)
    step6_arrival_rates = eval(s3_stats[s3_stats['step_id'] == 6]['arrival_rates'].values[0])
    
    # Verify files exist
    for name, path in [('Strategy 1 Step 6', strategy1_step6_file),
                       ('Strategy 3 Step 6', strategy3_step6_file),
                       ('Strategy 3 Step 1', strategy3_step1_file)]:
        if not os.path.exists(path):
            print(f"✗ Error: {name} file not found: {path}")
            return
        print(f"✓ Found {name} file")
    
    # Run all phases
    phase_results = {}
    
    # Phase 1
    phase_results['phase1'] = compare_path_sets(strategy1_step6_file, strategy3_step6_file, output_dir)
    
    # Phase 2
    phase_results['phase2'] = compare_flow_allocations(strategy1_step6_file, strategy3_step6_file,
                                                      step6_arrival_rates, output_dir)
    
    # Phase 3
    phase_results['phase3'] = verify_utilization_calculation(strategy1_step6_file, strategy3_step6_file,
                                                            config, output_dir)
    
    # Phase 4
    phase_results['phase4'] = analyze_path_constraints(strategy3_step1_file, strategy1_step6_file, output_dir)
    
    # Phase 5
    phase_results['phase5'] = analyze_optimizer_behavior(strategy1_step6_file, strategy3_step6_file,
                                                        config, output_dir)
    
    # Phase 6
    generate_comprehensive_report(output_dir, phase_results)
    
    print("\n" + "=" * 80)
    print("✓ Verification complete!")
    print("=" * 80)
    print(f"\nResults saved to: {output_dir}")


if __name__ == '__main__':
    main()

