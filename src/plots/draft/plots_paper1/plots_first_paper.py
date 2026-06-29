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




# This function needs to return both the lower and upper confidence interval bounds
def mean_confidence_interval(data, confidence=0.99):
    """Calculate the mean and confidence interval."""
    n = len(data)
    mean = np.mean(data)
    stderr = stats.sem(data)
    h = stderr * stats.t.ppf((1 + confidence) / 2., n - 1)
    return mean, mean - h, mean + h  # Return the mean, lower bound, and upper bound


################################################################################################


def plot_average_delay__capacity(all_results, time_unit='s'):
    results_dir = 'results'
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    data_by_capacity = {}

    # Extract data, categorize by capacity, and sort by demand
    for setup in all_results:
        parts = setup.split('_')
        demand = int(parts[0])  # Convert to integer for sorting purposes
        capacity = parts[-1].replace('.yaml', '')
        delays = [run['results_mc']['average_delay'] for run in all_results[setup].values()]
        mean, ci_lower, ci_upper = mean_confidence_interval(delays)

        if capacity not in data_by_capacity:
            data_by_capacity[capacity] = []
        data_by_capacity[capacity].append((demand, mean, ci_lower, ci_upper))

    # Sorting data by demand for each capacity
    for capacity in data_by_capacity:
        data_by_capacity[capacity].sort()

    plt.figure(figsize=(10, 6))

    # Plotting each capacity with evenly spaced x-axis elements
    max_length = max(len(data) for data in data_by_capacity.values())
    
    evenly_spaced_interval = np.linspace(0, max_length - 1, max_length)
    
    for capacity, data in data_by_capacity.items():
        demands = [item[0] for item in data]
        means = [item[1] for item in data]
        ci_lowers = [item[2] for item in data]
        ci_uppers = [item[3] for item in data]
        yerr = [(mean - ci_lower, ci_upper - mean) for mean, ci_lower, ci_upper in zip(means, ci_lowers, ci_uppers)]

        if capacity == "model":
            
            plt.plot(evenly_spaced_interval[:len(data)], means, '-o', label='Proposed model', linewidth=3)
            
            #plt.errorbar(evenly_spaced_interval[:len(data)], means, yerr=np.transpose(yerr), fmt='o', color='blue', capsize=5)
            
            plt.fill_between(evenly_spaced_interval[:len(data)], ci_lowers, ci_uppers, color='gray', alpha=0.3, linestyle='dashed')




            #plt.errorbar(evenly_spaced_interval[:len(data)], means, yerr=np.array(yerr).T, fmt='-o', label=f'Capacity {capacity}', linewidth=2)


           # plt.fill_between(evenly_spaced_interval[:len(data)], ci_lowers, ci_uppers, alpha=0.3)
        else:
            plt.plot(evenly_spaced_interval[:len(data)], means, '-o', label=f'Single modem bank, {capacity}', linewidth=3)
            
            plt.fill_between(evenly_spaced_interval[:len(data)], ci_lowers, ci_uppers, color='gray', alpha=0.3, linestyle='dashed')

            
           # plt.errorbar(evenly_spaced_interval[:len(data)], means, yerr=np.array(yerr).T, fmt='-o', label=f'Capacity {capacity}', linewidth=2)


          #  plt.fill_between(evenly_spaced_interval[:len(data)], ci_lowers, ci_uppers, alpha=0.3)

    plt.yticks(fontsize=16)
    plt.xticks(evenly_spaced_interval, [f'{d}' for d in demands], fontsize=16)  # Adjusted as per request

    #plt.xlabel('Traffic demand', fontsize=20)
    # Dynamic label based on time unit
    time_label = 'ms' if time_unit == 'ms' else 's'
    plt.xlabel(f'Traffic demand (λ) per commodity  [Packets /{time_label}]', fontsize=20)
    
    # Apply plain number formatting to the y-axis.
    plt.gca().yaxis.set_major_formatter(ScalarFormatter(useOffset=False))



    if time_unit == 'ms':
        plt.ylabel('Average end-to-end delay [ms]', fontsize=20)
    else:
        plt.ylabel('Average end-to-end delay [s]', fontsize=20)
    #plt.title('Average Delay by OBP Capacity', fontsize=16)
    #plt.legend(title='Processing Capacities', fontsize=12)
    #plt.legend(fontsize=20)
    
    # Set y-axis to start from zero
    #plt.gca().set_ylim(bottom=0)
    
    # Place the legend outside the plot on the right side
    plt.legend(loc='upper left', fontsize=20)

    # Save the plot
    pdf_filename = os.path.join(results_dir, 'average_delay_by_capacity.pdf')
    #eps_filename = os.path.join(results_dir, 'average_delay_by_capacity_line_chart.eps')
    plt.savefig(pdf_filename, bbox_inches='tight')
    #plt.savefig(eps_filename, format='eps', bbox_inches='tight')
    
    for capacity, data in data_by_capacity.items():
        print(f"Capacity: {capacity} -> Data: {data}")

    plt.show()
    
    
###################################################################################################


def plot_network_PLI__capacity(all_results, time_unit='s'):
    results_dir = 'results'
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    data_by_capacity = {}

    # Extract data, categorize by capacity, and sort by demand
    for setup in all_results:
        parts = setup.split('_')
        demand = int(parts[0])  # Convert to integer for sorting purposes
        capacity = parts[-1].replace('.yaml', '')
        plis = [run['results_mc']['network_PLI'] for run in all_results[setup].values()]
        mean_pli, ci_lower, ci_upper = mean_confidence_interval(plis)

        if capacity not in data_by_capacity:
            data_by_capacity[capacity] = []
        data_by_capacity[capacity].append((demand, mean_pli, ci_lower, ci_upper))

    # Sorting data by demand for each capacity
    for capacity in data_by_capacity:
        data_by_capacity[capacity].sort()

    plt.figure(figsize=(10, 6))

    # Plotting each capacity with evenly spaced x-axis elements
    max_length = max(len(data) for data in data_by_capacity.values())
    evenly_spaced_interval = np.linspace(0, max_length - 1, max_length)
    for capacity, data in data_by_capacity.items():
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

    pdf_filename = os.path.join(results_dir, 'network_PLI_by_capacity.pdf')
    plt.savefig(pdf_filename, bbox_inches='tight')
    plt.show()
    
#################################################################################################################



    
    
#######################################################################################################################    
