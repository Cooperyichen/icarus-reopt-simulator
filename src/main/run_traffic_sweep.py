#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to run simulations with different traffic rates (400-1000 packets/s in steps of 100)
and plot the results in a single figure.

Based on 70_lambda_our_model.yaml configuration.
"""

import sys
import os
import copy
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Add the project directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_path)

from utils.libs import *
from topo.utils import load_yaml_file, ensure_directory_exists
from main import run_simulation_scenario
from topo.utils import mean_confidence_interval

def run_traffic_sweep():
    """
    Run simulations with different traffic rates and collect results.
    """
    # Base configuration file
    base_yaml_path = os.path.join(os.path.dirname(__file__), '..', 'data', '70_lambda_our_model.yaml')
    
    # Load base configuration
    base_config = load_yaml_file(base_yaml_path)
    
    # Traffic rates to test: 400, 500, 600, 700, 800, 900, 1000
    traffic_rates = [400, 500, 600, 700, 800, 900, 1000]
    
    # Results storage
    all_results = {}
    num_runs = 2  # Number of runs per traffic rate
    
    # Setup results directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(script_dir, '..')
    results_base_dir = os.path.join(src_dir, "results")
    
    # Iterate over each traffic rate
    for traffic_rate in traffic_rates:
        print(f"\n{'='*60}")
        print(f"Running simulations for traffic rate: {traffic_rate} packets/s")
        print(f"{'='*60}\n")
        
        # Create a copy of the base configuration
        config = copy.deepcopy(base_config)
        
        # Update traffic rate
        config['fixed_demand']['arrival_rate'] = [traffic_rate, traffic_rate]
        config['random_demand']['minimum_flow_value'] = traffic_rate
        config['random_demand']['maximum_flow_value'] = traffic_rate
        
        # Update scenario name
        config['scenario_name'] = f"{traffic_rate}_lambda_our_model"
        
        # Store results for this traffic rate
        scenario_name = config['scenario_name']
        scenario_results = {}
        
        # Run multiple times for statistical confidence
        for run in range(num_runs):
            # Set a unique seed for each run
            np.random.seed(run)
            
            # Create result directory
            base_filename = scenario_name
            current_result_dir = os.path.join(results_base_dir, base_filename, f"run_{run+1}")
            ensure_directory_exists(current_result_dir)
            
            print(f"Running simulation {run + 1}/{num_runs} for traffic rate: {traffic_rate} packets/s")
            
            # Run the simulation
            all_flows, switches, blocked_flows = run_simulation_scenario(config, current_result_dir, run)
            
            scenario_results[f"run_{run}"] = {
                "all_flows_results": all_flows,
                "switches": switches,
                "blocked_flows": blocked_flows
            }
        
        # Store results
        all_results[scenario_name] = scenario_results
    
    # Plot results
    plot_traffic_sweep_results(all_results, traffic_rates, results_base_dir)
    
    return all_results

def plot_traffic_sweep_results(all_results, traffic_rates, results_dir):
    """
    Plot PLI and Delay vs Traffic Rate in a single figure.
    """
    sns.set_theme(style="whitegrid")
    
    # Extract data
    pli_means = []
    pli_ci_lower = []
    pli_ci_upper = []
    delay_means = []
    delay_ci_lower = []
    delay_ci_upper = []
    
    for traffic_rate in traffic_rates:
        scenario_name = f"{traffic_rate}_lambda_our_model"
        
        if scenario_name not in all_results:
            continue
        
        runs = all_results[scenario_name]
        
        # Calculate PLI
        plis = []
        for run in runs.values():
            total_sent = sum(flow.pkt_gen.packets_sent for flow in run['all_flows_results'])
            total_received = sum(flow.pkt_sink.packets_received.get(flow.fid, 0) 
                               for flow in run['all_flows_results'])
            total_dropped = total_sent - total_received
            
            if total_sent > 0:
                pli = (total_dropped / total_sent) * 100
            else:
                pli = 0
            plis.append(pli)
        
        # Calculate Delay
        delays = []
        for run in runs.values():
            run_delays = []
            for flow in run['all_flows_results']:
                if flow.pkt_sink.waits.get(flow.fid, []):
                    avg_delay = sum(flow.pkt_sink.waits[flow.fid]) / len(flow.pkt_sink.waits[flow.fid])
                    run_delays.append(avg_delay)
            if run_delays:
                delays.append(np.mean(run_delays))
        
        # Calculate statistics
        if plis:
            pli_mean, pli_ci_l, pli_ci_u = mean_confidence_interval(plis)
            pli_means.append(pli_mean)
            pli_ci_lower.append(pli_mean - pli_ci_l)
            pli_ci_upper.append(pli_ci_u - pli_mean)
        else:
            pli_means.append(0)
            pli_ci_lower.append(0)
            pli_ci_upper.append(0)
        
        if delays:
            delay_mean, delay_ci_l, delay_ci_u = mean_confidence_interval(delays)
            delay_means.append(delay_mean)
            delay_ci_lower.append(delay_mean - delay_ci_l)
            delay_ci_upper.append(delay_ci_u - delay_mean)
        else:
            delay_means.append(0)
            delay_ci_lower.append(0)
            delay_ci_upper.append(0)
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot PLI
    ax1.errorbar(traffic_rates, pli_means, 
                yerr=[pli_ci_lower, pli_ci_upper],
                fmt='o-', linewidth=2, markersize=8, capsize=5,
                color='#e74c3c', label='PLI')
    ax1.set_xlabel('Traffic Rate (packets/s)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Packet Loss Indicator (PLI) (%)', fontsize=12, fontweight='bold')
    ax1.set_title('PLI vs Traffic Rate', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)
    
    # Plot Delay
    ax2.errorbar(traffic_rates, delay_means,
                yerr=[delay_ci_lower, delay_ci_upper],
                fmt='s-', linewidth=2, markersize=8, capsize=5,
                color='#3498db', label='Average Delay')
    ax2.set_xlabel('Traffic Rate (packets/s)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Average End-to-End Delay (ms)', fontsize=12, fontweight='bold')
    ax2.set_title('Average Delay vs Traffic Rate', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)
    
    plt.tight_layout()
    
    # Save figure
    plot_path = os.path.join(results_dir, 'traffic_sweep_results.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {plot_path}")
    
    # Also save data to CSV
    import pandas as pd
    data = {
        'Traffic_Rate': traffic_rates,
        'PLI_Mean': pli_means,
        'PLI_CI_Lower': [m - l for m, l in zip(pli_means, pli_ci_lower)],
        'PLI_CI_Upper': [m + u for m, u in zip(pli_means, pli_ci_upper)],
        'Delay_Mean': delay_means,
        'Delay_CI_Lower': [m - l for m, l in zip(delay_means, delay_ci_lower)],
        'Delay_CI_Upper': [m + u for m, u in zip(delay_means, delay_ci_upper)]
    }
    df = pd.DataFrame(data)
    csv_path = os.path.join(results_dir, 'traffic_sweep_results.csv')
    df.to_csv(csv_path, index=False)
    print(f"Data saved to: {csv_path}")
    
    plt.show()

if __name__ == "__main__":
    print("Starting traffic sweep simulation...")
    results = run_traffic_sweep()
    print("\nTraffic sweep simulation completed!")

