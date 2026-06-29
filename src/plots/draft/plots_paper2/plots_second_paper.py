#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plots for first paper

@author: zineb.garroussi@polymtl.ca
"""
import numpy as np
import matplotlib.pyplot as plt
import os
from collections import defaultdict


from utils.libs import *  # Importing all libraries centralized in the libs.py module

import seaborn as sns
from scipy.stats import sem, t
from itertools import cycle  # Add this line




# This function needs to return both the lower and upper confidence interval bounds
def mean_confidence_interval(data, confidence=0.99):
    """Calculate the mean and confidence interval."""
    n = len(data)
    mean = np.mean(data)
    stderr = stats.sem(data)
    h = stderr * stats.t.ppf((1 + confidence) / 2., n - 1)
    return mean, mean - h, mean + h  # Return the mean, lower bound, and upper bound


################################################################################################

# def plot_average_delay__capacity_priority(
#     all_results, 
#     time_unit='s', 
#     plot_priority_our_model=True, 
#     plot_priority_capacity=True, 
#     plot_overall_our_model=True, 
#     plot_overall_capacity=True
# ):
#     results_dir = 'results'
#     os.makedirs(results_dir, exist_ok=True)
#     sns.set_theme(style="whitegrid")

#     custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]

#     # Initialize a dictionary to store data for each priority and overall results
#     data = {'our_model': {}, 'capacity': {}, 'overall': {'our_model': [], 'capacity': {}}}
#     all_demands = set()

#     # Iterate over each scenario and priority to collect data
#     for scenario, runs in all_results.items():
#         demand = int(scenario.split('_')[0])
#         all_demands.add(demand)
#         if 'our_model' in scenario:
#             model_key = 'our_model'
#         else:
#             model_key = 'capacity'
#             capacity = int(scenario.split('_')[-1].replace('c', ''))

#         overall_delays = [run['results_mc']['average_delay'] for run in runs.values()]
#         overall_mean, overall_ci_lower, overall_ci_upper = mean_confidence_interval(overall_delays)
        
#         if model_key == 'our_model':
#             data['overall'][model_key].append((demand, overall_mean, overall_ci_lower, overall_ci_upper))
#         else:
#             if capacity not in data['overall'][model_key]:
#                 data['overall'][model_key][capacity] = []
#             data['overall'][model_key][capacity].append((demand, overall_mean, overall_ci_lower, overall_ci_upper))

#         for priority in runs['run_0']['results_mc_per_priority']:
#             delays = [run['results_mc_per_priority'][priority]['average_delay'] for run in runs.values()]
#             mean, ci_lower, ci_upper = mean_confidence_interval(delays)
            
#             if model_key == 'our_model':
#                 if priority not in data[model_key]:
#                     data[model_key][priority] = []
#                 data[model_key][priority].append((demand, mean, ci_lower, ci_upper))
#             else:
#                 if capacity not in data[model_key]:
#                     data[model_key][capacity] = {}
#                 if priority not in data[model_key][capacity]:
#                     data[model_key][capacity][priority] = []
#                 data[model_key][capacity][priority].append((demand, mean, ci_lower, ci_upper))

#     # Create a mapping of demands to equally spaced x-values
#     sorted_demands = sorted(all_demands)
#     demand_to_x = {demand: i for i, demand in enumerate(sorted_demands)}

#     plt.figure(figsize=(14, 10))

#     # Plot for 'our model' by priority if enabled
#     if plot_priority_our_model:
#         for priority in data['our_model']:
#             x_positions = []
#             y_means = []
#             y_lowers = []
#             y_uppers = []
#             for demand, mean, ci_lower, ci_upper in sorted(data['our_model'][priority]):
#                 x_positions.append(demand_to_x[demand])
#                 y_means.append(mean)
#                 y_lowers.append(ci_lower)
#                 y_uppers.append(ci_upper)
            
#             plt.plot(x_positions, y_means, marker='o', linestyle='-', color=custom_colors[priority - 1], label=f"Class of service {priority} (our model)")
#             plt.fill_between(x_positions, y_lowers, y_uppers, color=custom_colors[priority - 1], alpha=0.3)

#     # Plot for each capacity by priority if enabled
#     if plot_priority_capacity:
#         for capacity in data['capacity']:
#             for priority in data['capacity'][capacity]:
#                 x_positions = []
#                 y_means = []
#                 y_lowers = []
#                 y_uppers = []
#                 for demand, mean, ci_lower, ci_upper in sorted(data['capacity'][capacity][priority]):
#                     x_positions.append(demand_to_x[demand])
#                     y_means.append(mean)
#                     y_lowers.append(ci_lower)
#                     y_uppers.append(ci_upper)
                
#                 plt.plot(x_positions, y_means, marker='x', linestyle='--', color=custom_colors[priority - 1], label=f"Class of service {priority} (capacity {capacity})")
#                 plt.fill_between(x_positions, y_lowers, y_uppers, color=custom_colors[priority - 1], alpha=0.3)

#     # Plot overall delay for 'our model' if enabled
#     if plot_overall_our_model:
#         for demand, mean, ci_lower, ci_upper in sorted(data['overall']['our_model']):
#             x = demand_to_x[demand]
#             plt.plot(x, mean, marker='s', linestyle='-', color='black', label='Overall (our model)' if demand == sorted_demands[0] else "", markersize=8)
#             plt.fill_between([x], [ci_lower], [ci_upper], color='black', alpha=0.3)

#     # Plot overall delay for each capacity if enabled
#     if plot_overall_capacity:
#         for capacity in data['overall']['capacity']:
#             #x = []
#             for demand, mean, ci_lower, ci_upper in sorted(data['overall']['capacity'][capacity]):
#                 #x.append(demand_to_x[demand])
#                 x = demand_to_x[demand]

#                 plt.plot(x, mean, marker='d', linestyle='--', color='grey', label=f'Single modem bank (capacity {capacity})' if demand == sorted_demands[0] else "", markersize=8, linewidth=2)
#                 plt.fill_between([x], [ci_lower], [ci_upper], color='grey', alpha=0.3)

#     # Apply plain number formatting to the y-axis.
#     plt.gca().yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    
#     time_label = 'ms' if time_unit == 'ms' else 's'
#     plt.xlabel(f'Traffic demand (λ) per commodity  [Packets /{time_label}]', fontsize=20)
    
#     if time_unit == 'ms':
#         plt.ylabel('Average end-to-end delay [ms]', fontsize=20)
#     else:
#         plt.ylabel('Average end-to-end delay [s]', fontsize=20)
    
#     plt.legend(loc='upper left', fontsize=20)
    
#     # Set x-ticks to the mapped demands
#     plt.xticks(range(len(sorted_demands)), sorted_demands, fontsize=20)
#     plt.yticks(fontsize=20)

#     # Save and show the plot
#     plt.savefig(os.path.join(results_dir, 'average_delay_per_priority_combined.pdf'), bbox_inches='tight')
#     plt.show()

##################################################################################################################

def plot_average_delay__capacity_priority(
    all_results, 
    time_unit='s', 
    plot_priority_our_model=True, 
    plot_priority_capacity=True, 
    plot_overall_our_model=True, 
    plot_overall_capacity=True
):
    results_dir = 'results'
    os.makedirs(results_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")

    custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]

    # Initialize a dictionary to store data for each priority and overall results
    data = {'our_model': {}, 'capacity': {}, 'overall': {'our_model': [], 'capacity': {}}}
    all_demands = set()

    # Iterate over each scenario and priority to collect data
    for scenario, runs in all_results.items():
        demand = int(scenario.split('_')[0])
        all_demands.add(demand)
        if 'our_model' in scenario:
            model_key = 'our_model'
        else:
            model_key = 'capacity'
            capacity = int(scenario.split('_')[-1].replace('c', ''))

        overall_delays = [run['results_mc']['average_delay'] for run in runs.values()]
        overall_mean, overall_ci_lower, overall_ci_upper = mean_confidence_interval(overall_delays)
        
        if model_key == 'our_model':
            data['overall'][model_key].append((demand, overall_mean, overall_ci_lower, overall_ci_upper))
        else:
            if capacity not in data['overall'][model_key]:
                data['overall'][model_key][capacity] = []
            data['overall'][model_key][capacity].append((demand, overall_mean, overall_ci_lower, overall_ci_upper))

        for priority in runs['run_0']['results_mc_per_priority']:
            delays = [run['results_mc_per_priority'][priority]['average_delay'] for run in runs.values()]
            mean, ci_lower, ci_upper = mean_confidence_interval(delays)
            
            if model_key == 'our_model':
                if priority not in data[model_key]:
                    data[model_key][priority] = []
                data[model_key][priority].append((demand, mean, ci_lower, ci_upper))
            else:
                if capacity not in data[model_key]:
                    data[model_key][capacity] = {}
                if priority not in data[model_key][capacity]:
                    data[model_key][capacity][priority] = []
                data[model_key][capacity][priority].append((demand, mean, ci_lower, ci_upper))

    # Create a mapping of demands to equally spaced x-values
    sorted_demands = sorted(all_demands)
    demand_to_x = {demand: i for i, demand in enumerate(sorted_demands)}

    plt.figure(figsize=(14, 10))

    # Plot for 'our model' by priority if enabled
    if plot_priority_our_model:
        for priority in data['our_model']:
            x_positions = []
            y_means = []
            y_lowers = []
            y_uppers = []
            for demand, mean, ci_lower, ci_upper in sorted(data['our_model'][priority]):
                x_positions.append(demand_to_x[demand])
                y_means.append(mean)
                y_lowers.append(ci_lower)
                y_uppers.append(ci_upper)
            
            plt.plot(x_positions, y_means, marker='o', linestyle='-', color=custom_colors[priority - 1], label=f"Class of service {priority} (our model)")
            plt.fill_between(x_positions, y_lowers, y_uppers, color=custom_colors[priority - 1], alpha=0.3)

    # Plot for each capacity by priority if enabled
    if plot_priority_capacity:
        for capacity in data['capacity']:
            for priority in data['capacity'][capacity]:
                x_positions = []
                y_means = []
                y_lowers = []
                y_uppers = []
                for demand, mean, ci_lower, ci_upper in sorted(data['capacity'][capacity][priority]):
                    x_positions.append(demand_to_x[demand])
                    y_means.append(mean)
                    y_lowers.append(ci_lower)
                    y_uppers.append(ci_upper)
                
                plt.plot(x_positions, y_means, marker='x', linestyle='--', color=custom_colors[priority - 1], label=f"Class of service {priority} (capacity {capacity})")
                plt.fill_between(x_positions, y_lowers, y_uppers, color=custom_colors[priority - 1], alpha=0.3)

    # Plot overall delay for 'our model' if enabled
    if plot_overall_our_model:
        x_positions = []
        y_means = []
        y_lowers = []
        y_uppers = []
        for demand, mean, ci_lower, ci_upper in sorted(data['overall']['our_model']):
            x = demand_to_x[demand]
            x_positions.append(x)
            y_means.append(mean)
            y_lowers.append(ci_lower)
            y_uppers.append(ci_upper)
        plt.plot(x_positions, y_means, marker='s', linestyle='-', color='black', label='Overall (our model)', markersize=8)
        plt.fill_between(x_positions, y_lowers, y_uppers, color='black', alpha=0.3)

    # Plot overall delay for each capacity if enabled
    if plot_overall_capacity:
        for capacity in data['overall']['capacity']:
            x_positions = []
            y_means = []
            y_lowers = []
            y_uppers = []
            for demand, mean, ci_lower, ci_upper in sorted(data['overall']['capacity'][capacity]):
                x = demand_to_x[demand]
                x_positions.append(x)
                y_means.append(mean)
                y_lowers.append(ci_lower)
                y_uppers.append(ci_upper)
            plt.plot(x_positions, y_means, marker='d', linestyle='--', color='grey', label=f'Single modem bank (capacity {capacity})', markersize=8, linewidth=2)
            plt.fill_between(x_positions, y_lowers, y_uppers, color='grey', alpha=0.3)

    # Apply plain number formatting to the y-axis.
    plt.gca().yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    
    time_label = 'ms' if time_unit == 'ms' else 's'
    plt.xlabel(f'Traffic demand (λ) per commodity  [Packets /{time_label}]', fontsize=20)
    
    if time_unit == 'ms':
        plt.ylabel('Average end-to-end delay [ms]', fontsize=20)
    else:
        plt.ylabel('Average end-to-end delay [s]', fontsize=20)
    
    plt.legend(loc='upper left', fontsize=20)
    
    # Set x-ticks to the mapped demands
    plt.xticks(range(len(sorted_demands)), sorted_demands, fontsize=20)
    plt.yticks(fontsize=20)

    # Save and show the plot
    plt.savefig(os.path.join(results_dir, 'average_delay_per_priority_combined.pdf'), bbox_inches='tight')
    plt.show()
    
    
###################################################################################################################    
    


def plot_average_PLI__capacity_priority(
    all_results, 
    time_unit='s', 
    plot_priority_our_model=True, 
    plot_priority_capacity=True, 
    plot_overall_our_model=True, 
    plot_overall_capacity=True
):
    results_dir = 'results'
    os.makedirs(results_dir, exist_ok=True)
    sns.set_theme(style="whitegrid")

    custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]

    # Initialize a dictionary to store data for each priority and overall results
    data = {'our_model': {}, 'capacity': {}, 'overall': {'our_model': [], 'capacity': {}}}
    all_demands = set()

    # Iterate over each scenario and priority to collect data
    for scenario, runs in all_results.items():
        demand = int(scenario.split('_')[0])
        all_demands.add(demand)
        if 'our_model' in scenario:
            model_key = 'our_model'
        else:
            model_key = 'capacity'
            capacity = int(scenario.split('_')[-1].replace('c', ''))

        overall_PLIs = [run['results_mc']['network_PLI'] for run in runs.values()]
        overall_mean, overall_ci_lower, overall_ci_upper = mean_confidence_interval(overall_PLIs)
        
        if model_key == 'our_model':
            data['overall'][model_key].append((demand, overall_mean, overall_ci_lower, overall_ci_upper))
        else:
            if capacity not in data['overall'][model_key]:
                data['overall'][model_key][capacity] = []
            data['overall'][model_key][capacity].append((demand, overall_mean, overall_ci_lower, overall_ci_upper))

        for priority in runs['run_0']['results_mc_per_priority']:
            PLIs = [run['results_mc_per_priority'][priority]['network_PLI'] for run in runs.values()]
            mean, ci_lower, ci_upper = mean_confidence_interval(PLIs)
            
            if model_key == 'our_model':
                if priority not in data[model_key]:
                    data[model_key][priority] = []
                data[model_key][priority].append((demand, mean, ci_lower, ci_upper))
            else:
                if capacity not in data[model_key]:
                    data[model_key][capacity] = {}
                if priority not in data[model_key][capacity]:
                    data[model_key][capacity][priority] = []
                data[model_key][capacity][priority].append((demand, mean, ci_lower, ci_upper))

    # Create a mapping of demands to equally spaced x-values
    sorted_demands = sorted(all_demands)
    demand_to_x = {demand: i for i, demand in enumerate(sorted_demands)}

    plt.figure(figsize=(14, 10))

    # Plot for 'our model' by priority if enabled
    if plot_priority_our_model:
        for priority in data['our_model']:
            x_positions = []
            y_means = []
            y_lowers = []
            y_uppers = []
            for demand, mean, ci_lower, ci_upper in sorted(data['our_model'][priority]):
                x_positions.append(demand_to_x[demand])
                y_means.append(mean)
                y_lowers.append(ci_lower)
                y_uppers.append(ci_upper)
            
            plt.plot(x_positions, y_means, marker='o', linestyle='-', color=custom_colors[priority - 1], label=f"Class of service {priority} (our model)")
            plt.fill_between(x_positions, y_lowers, y_uppers, color=custom_colors[priority - 1], alpha=0.3)

    # Plot for each capacity by priority if enabled
    if plot_priority_capacity:
        for capacity in data['capacity']:
            for priority in data['capacity'][capacity]:
                x_positions = []
                y_means = []
                y_lowers = []
                y_uppers = []
                for demand, mean, ci_lower, ci_upper in sorted(data['capacity'][capacity][priority]):
                    x_positions.append(demand_to_x[demand])
                    y_means.append(mean)
                    y_lowers.append(ci_lower)
                    y_uppers.append(ci_upper)
                
                plt.plot(x_positions, y_means, marker='x', linestyle='--', color=custom_colors[priority - 1], label=f"Class of service {priority} (capacity {capacity})")
                plt.fill_between(x_positions, y_lowers, y_uppers, color=custom_colors[priority - 1], alpha=0.3)

    # Plot overall PLI for 'our model' if enabled
    if plot_overall_our_model:
        x_positions = []
        y_means = []
        y_lowers = []
        y_uppers = []
        for demand, mean, ci_lower, ci_upper in sorted(data['overall']['our_model']):
            x = demand_to_x[demand]
            x_positions.append(x)
            y_means.append(mean)
            y_lowers.append(ci_lower)
            y_uppers.append(ci_upper)
        plt.plot(x_positions, y_means, marker='s', linestyle='-', color='black', label='Overall (our model)', markersize=8)
        plt.fill_between(x_positions, y_lowers, y_uppers, color='black', alpha=0.3)

    # Plot overall PLI for each capacity if enabled
    if plot_overall_capacity:
        for capacity in data['overall']['capacity']:
            x_positions = []
            y_means = []
            y_lowers = []
            y_uppers = []
            for demand, mean, ci_lower, ci_upper in sorted(data['overall']['capacity'][capacity]):
                x = demand_to_x[demand]
                x_positions.append(x)
                y_means.append(mean)
                y_lowers.append(ci_lower)
                y_uppers.append(ci_upper)
            plt.plot(x_positions, y_means, marker='d', linestyle='--', color='grey', label=f'Single modem bank (capacity {capacity})', markersize=8, linewidth=2)
            plt.fill_between(x_positions, y_lowers, y_uppers, color='grey', alpha=0.3)

    # Apply plain number formatting to the y-axis.
    plt.gca().yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
    
    time_label = 'ms' if time_unit == 'ms' else 's'
    plt.xlabel(f'Traffic demand (λ) per commodity  [Packets /{time_label}]', fontsize=20)
    
    if time_unit == 'ms':
        plt.ylabel('Average Packet Loss Indicator [ms]', fontsize=20)
    else:
        plt.ylabel('Average Packet Loss Indicator [s]', fontsize=20)
    
    plt.legend(loc='upper left', fontsize=20)
    
    # Set x-ticks to the mapped demands
    plt.xticks(range(len(sorted_demands)), sorted_demands, fontsize=20)
    plt.yticks(fontsize=20)

    # Save and show the plot
    plt.savefig(os.path.join(results_dir, 'average_PLI_per_priority_combined.pdf'), bbox_inches='tight')
    plt.show()
