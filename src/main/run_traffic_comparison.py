#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to run simulations with different traffic values (500, 1000, 2500) 
and generate comparison plots for PLI and average delay.
"""

import sys
import os
import copy
import yaml
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import ScalarFormatter

# Add the project directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_path)

from utils.libs import *
from topo.utils import load_yaml_file, mean_confidence_interval
from main import run_simulation_scenario
from plots.plots_first_paper import plot_average_delay__capacity, plot_network_PLI__capacity


def modify_yaml_for_traffic(base_yaml_path, traffic_value, output_yaml_path):
    """
    Modify the YAML file to set traffic value.
    
    Args:
        base_yaml_path: Path to the base YAML file
        traffic_value: Traffic value to set (500, 1000, or 2500)
        output_yaml_path: Path to save the modified YAML file
    """
    with open(base_yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Modify arrival_rate in fixed_demand
    if 'fixed_demand' in config and 'arrival_rate' in config['fixed_demand']:
        config['fixed_demand']['arrival_rate'] = [traffic_value, traffic_value]
    
    # Also modify minimum_flow_value and maximum_flow_value in random_demand (for consistency)
    if 'random_demand' in config:
        config['random_demand']['minimum_flow_value'] = traffic_value
        config['random_demand']['maximum_flow_value'] = traffic_value
    
    # Update scenario name to include traffic value
    config['scenario_name'] = f"{traffic_value}_lambda_our_model_2c"
    
    # Save modified YAML
    with open(output_yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return config


def run_single_traffic_scenario(traffic_value, base_yaml_path, results_base_dir):
    """
    Run simulation for a single traffic value.
    
    Args:
        traffic_value: Traffic value to test (500, 1000, or 2500)
        base_yaml_path: Path to the base YAML file
        results_base_dir: Base directory for results
    
    Returns:
        Dictionary containing simulation results
    """
    print("\n" + "="*80)
    print(f"Running simulation for traffic value: {traffic_value} packets/s")
    print("="*80)
    
    # Create temporary YAML file for this traffic value
    temp_yaml_path = os.path.join(
        os.path.dirname(base_yaml_path),
        f"temp_{traffic_value}_lambda_our_model_2c.yaml"
    )
    
    # Modify YAML
    config = modify_yaml_for_traffic(base_yaml_path, traffic_value, temp_yaml_path)
    
    scenario_name = config['scenario_name']
    num_runs = config['simulation']['num_runs']
    
    # Run simulation
    all_results = {}
    
    for run_id in range(1, num_runs + 1):
        print(f"\n  Run {run_id}/{num_runs}...")
        result_dir = os.path.join(results_base_dir, scenario_name, f"run_{run_id}")
        os.makedirs(result_dir, exist_ok=True)  # Ensure directory exists
        
        np.random.seed(run_id - 1)
        all_flows, switches, blocked_flows = run_simulation_scenario(config, result_dir, run_id - 1)
        
        all_results[run_id] = {
            'all_flows_results': all_flows,
            'switches': switches,
            'blocked_flows': blocked_flows
        }
    
    # Clean up temporary YAML file
    if os.path.exists(temp_yaml_path):
        os.remove(temp_yaml_path)
    
    return {scenario_name: all_results}


def plot_comparison(all_results_dict, results_dir, time_unit='ms'):
    """
    Generate comparison plots for PLI and average delay.
    
    Args:
        all_results_dict: Dictionary containing results for all traffic values
        results_dir: Directory to save plots
        time_unit: Time unit ('ms' or 's')
    """
    os.makedirs(results_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")
    
    # Extract data
    traffic_values = []
    delays_mean = []
    delays_ci_lower = []
    delays_ci_upper = []
    plis_mean = []
    plis_ci_lower = []
    plis_ci_upper = []
    
    for scenario_name, runs in sorted(all_results_dict.items()):
        # Extract traffic value from scenario name
        traffic_value = int(scenario_name.split('_')[0])
        traffic_values.append(traffic_value)
        
        # Calculate delays
        run_delays = []
        for run in runs.values():
            flow_delays = []
            for flow in run['all_flows_results']:
                if flow.pkt_sink.waits.get(flow.fid, []):
                    average_wait = sum(flow.pkt_sink.waits[flow.fid]) / len(flow.pkt_sink.waits[flow.fid])
                    flow_delays.append(average_wait)
            if flow_delays:
                run_delays.append(sum(flow_delays) / len(flow_delays))
        
        if run_delays:
            mean, ci_lower, ci_upper = mean_confidence_interval(run_delays)
            delays_mean.append(mean)
            delays_ci_lower.append(ci_lower)
            delays_ci_upper.append(ci_upper)
        else:
            delays_mean.append(0)
            delays_ci_lower.append(0)
            delays_ci_upper.append(0)
        
        # Calculate PLIs
        run_plis = []
        for run in runs.values():
            flow_plis = []
            for flow in run['all_flows_results']:
                total_packets_sent = flow.pkt_gen.packets_sent
                total_packets_received = flow.pkt_sink.packets_received.get(flow.fid, 0)
                if total_packets_sent > 0:
                    pli = ((total_packets_sent - total_packets_received) / total_packets_sent) * 100
                else:
                    pli = 0
                flow_plis.append(pli)
            if flow_plis:
                run_plis.append(sum(flow_plis) / len(flow_plis))
        
        if run_plis:
            mean, ci_lower, ci_upper = mean_confidence_interval(run_plis)
            plis_mean.append(mean)
            plis_ci_lower.append(ci_lower)
            plis_ci_upper.append(ci_upper)
        else:
            plis_mean.append(0)
            plis_ci_lower.append(0)
            plis_ci_upper.append(0)
    
    # Sort by traffic value
    sorted_indices = np.argsort(traffic_values)
    traffic_values = [traffic_values[i] for i in sorted_indices]
    delays_mean = [delays_mean[i] for i in sorted_indices]
    delays_ci_lower = [delays_ci_lower[i] for i in sorted_indices]
    delays_ci_upper = [delays_ci_upper[i] for i in sorted_indices]
    plis_mean = [plis_mean[i] for i in sorted_indices]
    plis_ci_lower = [plis_ci_lower[i] for i in sorted_indices]
    plis_ci_upper = [plis_ci_upper[i] for i in sorted_indices]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Note: arrival_rate is always in packets/s, regardless of time_unit
    # time_unit only affects simulation_time and other time-related parameters
    time_label_delay = 'ms' if time_unit == 'ms' else 's'  # For delay y-axis
    traffic_label = 's'  # arrival_rate is always in packets/s
    
    # Plot 1: Average Delay
    ax1.plot(traffic_values, delays_mean, '-o', linewidth=3, markersize=10, color='#3498db', label='Average Delay')
    ax1.fill_between(traffic_values, delays_ci_lower, delays_ci_upper, color='#3498db', alpha=0.2)
    ax1.set_xlabel(f'Traffic Demand (λ) per Commodity [Packets/{traffic_label}]', fontsize=16)
    if time_unit == 'ms':
        ax1.set_ylabel(f'Average End-to-End Delay [{time_label_delay}]', fontsize=16)
    else:
        ax1.set_ylabel(f'Average End-to-End Delay [{time_label_delay}]', fontsize=16)
    ax1.set_title('Average Delay vs Traffic Demand', fontsize=18, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=14)
    ax1.tick_params(labelsize=14)
    ax1.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    
    # Plot 2: PLI
    ax2.plot(traffic_values, plis_mean, '-s', linewidth=3, markersize=10, color='#e74c3c', label='Packet Loss Indicator')
    ax2.fill_between(traffic_values, plis_ci_lower, plis_ci_upper, color='#e74c3c', alpha=0.2)
    ax2.set_xlabel(f'Traffic Demand (λ) per Commodity [Packets/{traffic_label}]', fontsize=16)
    ax2.set_ylabel('Packet Loss Indicator (PLI) [%]', fontsize=16)
    ax2.set_title('PLI vs Traffic Demand', fontsize=18, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=14)
    ax2.tick_params(labelsize=14)
    ax2.yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    
    plt.tight_layout()
    
    # Save plot
    plot_path = os.path.join(results_dir, 'traffic_comparison_pli_delay.pdf')
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    print(f"\n对比图已保存到: {plot_path}")
    
    # Also save as PNG
    plot_path_png = os.path.join(results_dir, 'traffic_comparison_pli_delay.png')
    plt.savefig(plot_path_png, bbox_inches='tight', dpi=300)
    print(f"对比图已保存到: {plot_path_png}")
    
    plt.show()
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"{'Traffic':<12} {'Avg Delay (mean)':<20} {'Delay CI':<25} {'PLI (mean)':<15} {'PLI CI':<25}")
    print("-"*80)
    for i, tv in enumerate(traffic_values):
        delay_str = f"[{delays_ci_lower[i]:.4f}, {delays_ci_upper[i]:.4f}]"
        pli_str = f"[{plis_ci_lower[i]:.4f}, {plis_ci_upper[i]:.4f}]"
        print(f"{tv:<12} {delays_mean[i]:<20.6f} {delay_str:<25} {plis_mean[i]:<15.4f} {pli_str:<25}")


def main():
    """Main function to run traffic comparison."""
    # Configuration
    base_yaml_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', '80_lambda_our_model_2c.yaml'
    )
    results_base_dir = os.path.join(
        os.path.dirname(__file__), '..', 'results'
    )
    comparison_results_dir = os.path.join(results_base_dir, 'traffic_comparison')
    
    traffic_values = [500, 1000, 2500]
    
    print("="*80)
    print("TRAFFIC COMPARISON SIMULATION")
    print("="*80)
    print(f"Base YAML: {base_yaml_path}")
    print(f"Traffic values to test: {traffic_values}")
    print(f"Results directory: {comparison_results_dir}")
    print("="*80)
    
    # Load base config to get time_unit
    base_config = load_yaml_file(base_yaml_path)
    time_unit = base_config['system'].get('time_unit', 'ms')
    
    # Run simulations for each traffic value
    all_results_dict = {}
    
    for traffic_value in traffic_values:
        results = run_single_traffic_scenario(
            traffic_value, base_yaml_path, results_base_dir
        )
        all_results_dict.update(results)
    
    # Generate comparison plots
    print("\n" + "="*80)
    print("GENERATING COMPARISON PLOTS")
    print("="*80)
    plot_comparison(all_results_dict, comparison_results_dir, time_unit=time_unit)
    
    print("\n" + "="*80)
    print("TRAFFIC COMPARISON COMPLETED")
    print("="*80)


if __name__ == "__main__":
    main()

