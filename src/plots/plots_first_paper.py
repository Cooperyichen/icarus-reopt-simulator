#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""


This script generates plots for our first paper, specifically focusing on the average delay by capacity 
and network Packet Loss Indicator (PLI) by capacity. It uses the Matplotlib and Seaborn libraries for 
visualization and extracts data from simulation results stored in a structured format. The plots include 
confidence intervals to illustrate the variability in the results.

Functions:
    plot_average_delay__capacity: Plots the average delay versus capacity for different traffic demands.
    plot_network_PLI__capacity: Plots the network PLI versus capacity for different traffic demands.


"""

# @author: zineb.garroussi@polymtl.ca

import numpy as np
import matplotlib.pyplot as plt
import os
from collections import defaultdict


from utils.libs import *  # Importing all libraries centralized in the libs.py module

from topo.utils import mean_confidence_interval



################################################################################################

def plot_average_delay__capacity(all_results, time_unit='s', results_dir=None):
    
    """
    Plots the average end-to-end delay versus capacity for different traffic demands.

    Args:
        all_results (dict): A dictionary containing the simulation results.
        time_unit (str): The unit of time for the x-axis label ('s' for seconds, 'ms' for milliseconds).
        results_dir (str): The directory to save the plot.

    Returns:
        None
    """


    # Update the path to the results directory
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    data_by_capacity = {}

    # Extract data, categorize by capacity, and sort by demand
    for setup in all_results:
        parts = setup.split('_')
        demand = int(parts[0])  # Convert to integer for sorting purposes
        # Check if this is an 'our_model' scenario
        if 'our_model' in setup:
            capacity = "model"
        else:
            capacity = parts[-1].replace('.yaml', '')

        run_averages = []  # List to store the average delays for each run

        for run in all_results[setup].values():
            flow_delays = []

            for flow in run['all_flows_results']:
                if flow.pkt_sink.waits.get(flow.fid, []):
                    average_wait = sum(flow.pkt_sink.waits[flow.fid]) / len(flow.pkt_sink.waits[flow.fid])
                    flow_delays.append(average_wait)

            if flow_delays:
                run_average = sum(flow_delays) / len(flow_delays)
                run_averages.append(run_average)

        if run_averages:
            scenario_average = sum(run_averages) / len(run_averages)
            mean, ci_lower, ci_upper = mean_confidence_interval(run_averages)
            if capacity not in data_by_capacity:
                data_by_capacity[capacity] = []
            data_by_capacity[capacity].append((demand, scenario_average, ci_lower, ci_upper))

    # Check if data_by_capacity is empty
    if not data_by_capacity:
        print("No data available to plot.")
        return

    plt.figure(figsize=(10, 6))

    # Plotting each capacity with evenly spaced x-axis elements
    max_length = max(len(data) for data in data_by_capacity.values())
    if max_length == 0:
        print("No valid data points to plot.")
        return

    evenly_spaced_interval = np.linspace(0, max_length - 1, max_length)

    for capacity, data in data_by_capacity.items():
        if not data:
            continue  # Skip empty data sets

        demands = [item[0] for item in data]
        means = [item[1] for item in data]
        ci_lowers = [item[2] for item in data]
        ci_uppers = [item[3] for item in data]
        
        # Convert delay values based on time_unit
        # Note: delays from SimPy are in seconds
        if time_unit == 'ms':
            means = [m * 1000 for m in means]  # Convert to milliseconds
            ci_lowers = [c * 1000 for c in ci_lowers]  # Convert to milliseconds
            ci_uppers = [c * 1000 for c in ci_uppers]  # Convert to milliseconds
        
        yerr = [(mean - ci_lower, ci_upper - mean) for mean, ci_lower, ci_upper in zip(means, ci_lowers, ci_uppers)]

        if capacity == "model":
            plt.plot(evenly_spaced_interval[:len(data)], means, '-o', label='Proposed model', linewidth=3)
            plt.fill_between(evenly_spaced_interval[:len(data)], ci_lowers, ci_uppers, color='gray', alpha=0.1, linestyle='dashed')
        else:
            plt.plot(evenly_spaced_interval[:len(data)], means, '-o', label=f'Single modem bank, {capacity}', linewidth=3)
            plt.fill_between(evenly_spaced_interval[:len(data)], ci_lowers, ci_uppers, color='gray', alpha=0.1, linestyle='dashed')

    plt.yticks(fontsize=16)
    plt.xticks(evenly_spaced_interval, [f'{d}' for d in demands], fontsize=16)  # Adjusted as per request

    time_label = 'ms' if time_unit == 'ms' else 's'
    plt.xlabel(f'Traffic demand (λ) per commodity  [Packets /{time_label}]', fontsize=20)
    plt.gca().yaxis.set_major_formatter(ScalarFormatter(useOffset=False))

    if time_unit == 'ms':
        plt.ylabel('Average end-to-end delay [ms]', fontsize=20)
    else:
        plt.ylabel('Average end-to-end delay [s]', fontsize=20)

    plt.legend(loc='upper left', fontsize=20)

    plt.savefig(os.path.join(results_dir, 'average_delay_by_capacity.pdf'), bbox_inches='tight')
    plt.show()

    
###################################################################################################

def plot_network_PLI__capacity(all_results, time_unit='s', results_dir=None):
    
    """
    Plots the network Packet Loss Indicator (PLI) versus capacity for different traffic demands.

    Args:
        all_results (dict): A dictionary containing the simulation results.
        time_unit (str): The unit of time for the x-axis label ('s' for seconds, 'ms' for milliseconds).
        results_dir (str): The directory to save the plot.

    Returns:
        None
    """
    if results_dir is None:
        results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    data_by_capacity = {}

    # Extract data, categorize by capacity, and sort by demand
    for setup in all_results:
        parts = setup.split('_')
        demand = int(parts[0])  # Convert to integer for sorting purposes
        # Check if this is an 'our_model' scenario
        if 'our_model' in setup:
            capacity = "model"
        else:
            capacity = parts[-1].replace('.yaml', '')

        run_plis = []  # List to store the PLI for each run

        for run in all_results[setup].values():
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
                run_average = sum(flow_plis) / len(flow_plis)
                run_plis.append(run_average)

        if run_plis:
            scenario_average = sum(run_plis) / len(run_plis)
            mean_pli, ci_lower, ci_upper = mean_confidence_interval(run_plis)
            if capacity not in data_by_capacity:
                data_by_capacity[capacity] = []
            data_by_capacity[capacity].append((demand, scenario_average, ci_lower, ci_upper))

    # Check if data_by_capacity is empty
    if not data_by_capacity:
        print("No data available to plot.")
        return

    plt.figure(figsize=(10, 6))

    # Plotting each capacity with evenly spaced x-axis elements
    max_length = max(len(data) for data in data_by_capacity.values())
    if max_length == 0:
        print("No valid data points to plot.")
        return

    evenly_spaced_interval = np.linspace(0, max_length - 1, max_length)

    for capacity, data in data_by_capacity.items():
        if not data:
            continue  # Skip empty data sets

        demands = [item[0] for item in data]
        means = [item[1] for item in data]
        ci_lowers = [item[2] for item in data]
        ci_uppers = [item[3] for item in data]

        if capacity == "model":
            plt.plot(evenly_spaced_interval[:len(data)], means, '-o', label='Proposed model', linewidth=3)
            plt.fill_between(evenly_spaced_interval[:len(data)], ci_lowers, ci_uppers, color='gray', alpha=0.3, linestyle='dashed')
        else:
            plt.plot(evenly_spaced_interval[:len(data)], means, '-o', label=f'Single modem bank, {capacity}', linewidth=3)
            plt.fill_between(evenly_spaced_interval[:len(data)], ci_lowers, ci_uppers, color='gray', alpha=0.3, linestyle='dashed')

    plt.yticks(fontsize=16)
    plt.xticks(evenly_spaced_interval, [f'{d}' for d in demands], fontsize=16)

    time_label = 'ms' if time_unit == 'ms' else 's'
    plt.xlabel(f'Traffic demand (λ) per commodity [Packets /{time_label}]', fontsize=20)
    plt.ylabel('Network PLI [%]', fontsize=20)
    plt.legend(loc='upper left', fontsize=20)
    plt.gca().set_ylim(bottom=0)

    plt.savefig(os.path.join(results_dir, 'network_PLI_by_capacity.pdf'), bbox_inches='tight')
    plt.show()

    
    
#######################################################################################################################    
