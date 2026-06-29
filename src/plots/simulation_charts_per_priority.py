#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides functions for plotting various statistics
such as total packets sent, received, dropped, average delay, 
network PLI, and LDI from simulation results. The statistics are
plotted per priority class.



"""

# @author: zineb.garroussi@polymtl.ca


import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from collections import defaultdict
from scipy import stats
from modem.switch import FairPacketSwitch, SimplePacketSwitch  # Add this line to import the required switch classes
from port.port import Port  # Import the Port class

from topo.utils import mean_confidence_interval


### plots




def plot_total_packets_sent_priority(all_results):
    
    """
    Plot the total packets sent per priority class with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """

    
    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")


    custom_colors = [
        "#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", 
        "#c55a11", "#ffd700", "#5f27cd", "#10ac84"
    ]

    # Initialize a dictionary to store data for each priority in each scenario
    data = {}

    # Iterate over each scenario and priority to collect data
    for scenario, runs in all_results.items():
        data[scenario] = {}
        for run in runs.values():
            for flow in run['all_flows_results']:
                priority = flow.priority
                if priority not in data[scenario]:
                    data[scenario][priority] = []
                data[scenario][priority].append(flow.pkt_gen.packets_sent)

    # Calculate means and confidence intervals
    for scenario in data:
        for priority in data[scenario]:
            packets_sent = data[scenario][priority]
            mean, ci_lower, ci_upper = mean_confidence_interval(packets_sent)
            data[scenario][priority] = (mean, ci_lower, ci_upper)

    # Find the number of scenarios and priorities
    num_scenarios = len(all_results)
    num_priorities = max(len(priorities) for priorities in data.values())

    plt.figure(figsize=(12, 8))
    bar_width = 0.15
    group_width = num_priorities * bar_width + (bar_width * 0.5)
    x_base_positions = np.arange(0, num_scenarios * group_width, group_width)

    # Plot bars
    for scenario_index, (scenario, priorities) in enumerate(data.items()):
        for priority_index, (priority, (mean, ci_lower, ci_upper)) in enumerate(priorities.items()):
            x_position = x_base_positions[scenario_index] + (bar_width * priority_index)
            bar_color = custom_colors[priority - 1]  # Assuming priority starts from 1
            bar = plt.bar(x_position, mean, color=bar_color, width=bar_width, label=f"Class of service {priority}" if scenario_index == 0 else "")
            plt.errorbar(x_position, mean, yerr=[[mean - ci_lower], [ci_upper - mean]], fmt='none', ecolor='black', capsize=10)
            
            # Annotate the upper and lower bounds of the confidence interval
            #plt.text(x_position, ci_upper + 0.1, f'{ci_upper:.2f}', ha='center', va='bottom', fontsize=10, color='black')
            #plt.text(x_position, ci_lower - 0.1, f'{ci_lower:.2f}', ha='center', va='top', fontsize=10, color='black')

    # # Set x-axis labels for scenarios
    # plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    # plt.yticks(fontsize=20)
    # plt.ylabel('Packets Sent', fontsize=22)
    # plt.title('Average Total Packets Sent per Priority', fontsize=22)
    # plt.legend(fontsize=20)
    
    
    
        # Create a sorted legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    sorted_labels = sorted(by_label.keys(), key=lambda x: int(x.split()[-1]))  # Sort by priority number
    sorted_handles = [by_label[label] for label in sorted_labels]
    
    # Set x-axis labels for scenarios
    plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    plt.yticks(fontsize=20)
    plt.ylabel('Packets Sent', fontsize=22)
    plt.title('Average Total Packets Sent per Priority', fontsize=22)
    plt.legend(sorted_handles, sorted_labels, fontsize=20)

    # Save and show the plot
    plt.savefig(os.path.join(results_dir, 'average_packets_sent_per_priority.pdf'), bbox_inches='tight')
    plt.show()

####################################################################################################################





def plot_total_packets_received_priority(all_results):

    """
    Plot the total packets received per priority class with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """
    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    custom_colors = [
        "#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", 
        "#c55a11", "#ffd700", "#5f27cd", "#10ac84"
    ]

    # Initialize a dictionary to store data for each priority in each scenario
    data = {}

    # Iterate over each scenario and priority to collect data
    for scenario, runs in all_results.items():
        data[scenario] = {}
        for run in runs.values():
            for flow in run['all_flows_results']:
                priority = flow.priority
                if priority not in data[scenario]:
                    data[scenario][priority] = []
                data[scenario][priority].append(flow.pkt_sink.packets_received.get(flow.fid, 0))

    # Calculate means and confidence intervals
    for scenario in data:
        for priority in data[scenario]:
            packets_received = data[scenario][priority]
            mean, ci_lower, ci_upper = mean_confidence_interval(packets_received)
            data[scenario][priority] = (mean, ci_lower, ci_upper)

    # Find the number of scenarios and priorities
    num_scenarios = len(all_results)
    num_priorities = max(len(priorities) for priorities in data.values())

    plt.figure(figsize=(12, 8))
    bar_width = 0.15
    group_width = num_priorities * bar_width + (bar_width * 0.5)
    x_base_positions = np.arange(0, num_scenarios * group_width, group_width)

    # Plot bars
    for scenario_index, (scenario, priorities) in enumerate(data.items()):
        for priority_index, (priority, (mean, ci_lower, ci_upper)) in enumerate(priorities.items()):
            x_position = x_base_positions[scenario_index] + (bar_width * priority_index)
            bar_color = custom_colors[priority - 1]  # Assuming priority starts from 1
            bar = plt.bar(x_position, mean, color=bar_color, width=bar_width, label=f"Class of service {priority}" if scenario_index == 0 else "")
            plt.errorbar(x_position, mean, yerr=[[mean - ci_lower], [ci_upper - mean]], fmt='none', ecolor='black', capsize=10)
            
            # Annotate the upper and lower bounds of the confidence interval
            #plt.text(x_position, ci_upper + 0.1, f'{ci_upper:.2f}', ha='center', va='bottom', fontsize=10, color='black')
            #plt.text(x_position, ci_lower - 0.1, f'{ci_lower:.2f}', ha='center', va='top', fontsize=10, color='black')

    # # Set x-axis labels for scenarios
    # plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    # plt.yticks(fontsize=20)
    # plt.ylabel('Packets Received', fontsize=22)
    # plt.title('Average Total Packets Received per Priority', fontsize=22)
    # plt.legend(fontsize=20)


    # Create a sorted legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    sorted_labels = sorted(by_label.keys(), key=lambda x: int(x.split()[-1]))  # Sort by priority number
    sorted_handles = [by_label[label] for label in sorted_labels]

    # Set x-axis labels for scenarios
    plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    plt.yticks(fontsize=20)
    plt.ylabel('Packets Received', fontsize=22)
    plt.title('Average Total Packets Received per Priority', fontsize=22)
    plt.legend(sorted_handles, sorted_labels, fontsize=20)
    
    # Save and show the plot
    plt.savefig(os.path.join(results_dir, 'average_packets_received_per_priority.pdf'), bbox_inches='tight')
    plt.show()


#############################################################################################################



def plot_total_packets_dropped_priority(all_results):

    """
    Plot the total packets dropped per priority class with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """
    
    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")


    custom_colors = [
        "#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", 
        "#c55a11", "#ffd700", "#5f27cd", "#10ac84"
    ]

    # Initialize a dictionary to store data for each priority in each scenario
    data = {}

    # Iterate over each scenario and priority to collect data
    for scenario, runs in all_results.items():
        data[scenario] = {}
        for run in runs.values():
            for flow in run['all_flows_results']:
                priority = flow.priority
                if priority not in data[scenario]:
                    data[scenario][priority] = []
                # Collect dropped packets for the current flow and priority
                dropped_packets = 0
                for (x, y), switch in run['switches'].items():
                    if isinstance(switch, FairPacketSwitch):
                        ports = switch.egress_ports
                    elif isinstance(switch, SimplePacketSwitch):
                        ports = switch.ports
                    else:
                        print(f"Unknown switch type for switch ({x}, {y})")
                        continue

                    for port in ports:
                        if isinstance(port, Port):
                            dropped_packets += port.dropped_by_flow.get(flow.fid, 0)

                data[scenario][priority].append(dropped_packets)

    # Calculate means and confidence intervals
    for scenario in data:
        for priority in data[scenario]:
            packets_dropped = data[scenario][priority]
            mean, ci_lower, ci_upper = mean_confidence_interval(packets_dropped)
            data[scenario][priority] = (mean, ci_lower, ci_upper)

    # Find the number of scenarios and priorities
    num_scenarios = len(all_results)
    num_priorities = max(len(priorities) for priorities in data.values())

    plt.figure(figsize=(12, 8))
    bar_width = 0.15
    group_width = num_priorities * bar_width + (bar_width * 0.5)
    x_base_positions = np.arange(0, num_scenarios * group_width, group_width)

    # Plot bars
    for scenario_index, (scenario, priorities) in enumerate(data.items()):
        for priority_index, (priority, (mean, ci_lower, ci_upper)) in enumerate(priorities.items()):
            x_position = x_base_positions[scenario_index] + (bar_width * priority_index)
            bar_color = custom_colors[priority - 1]  # Assuming priority starts from 1
            bar = plt.bar(x_position, mean, color=bar_color, width=bar_width, label=f"Class of service {priority}" if scenario_index == 0 else "")
            plt.errorbar(x_position, mean, yerr=[[mean - ci_lower], [ci_upper - mean]], fmt='none', ecolor='black', capsize=10)
            
            # Annotate the upper and lower bounds of the confidence interval
            #plt.text(x_position, ci_upper + 0.1, f'{ci_upper:.2f}', ha='center', va='bottom', fontsize=10, color='black')
            #plt.text(x_position, ci_lower - 0.1, f'{ci_lower:.2f}', ha='center', va='top', fontsize=10, color='black')

    # # Set x-axis labels for scenarios
    # plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    # plt.yticks(fontsize=20)
    # plt.ylabel('Packets Dropped', fontsize=22)
    # plt.title('Average Total Packets Dropped per Priority', fontsize=22)
    # plt.legend(fontsize=20)

    # Create a sorted legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    sorted_labels = sorted(by_label.keys(), key=lambda x: int(x.split()[-1]))  # Sort by priority number
    sorted_handles = [by_label[label] for label in sorted_labels]

    # Set x-axis labels for scenarios
    plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    plt.yticks(fontsize=20)
    plt.ylabel('Packets Dropped', fontsize=22)
    plt.title('Average Total Packets Dropped per Priority', fontsize=22)
    plt.legend(sorted_handles, sorted_labels, fontsize=20)
    # Save and show the plot
    plt.savefig(os.path.join(results_dir, 'average_packets_dropped_per_priority.pdf'), bbox_inches='tight')
    plt.show()


######################################################################################################################

def plot_average_delay_priority(all_results, time_unit='s'):
    
    """
    Plot the average delay per priority class with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    :param time_unit: Time unit for the delay (default is seconds).
    :type time_unit: str, optional
    """


    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")


    custom_colors = [
        "#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", 
        "#c55a11", "#ffd700", "#5f27cd", "#10ac84"
    ]

    # Initialize a dictionary to store data for each priority in each scenario
    data = {}

    # Iterate over each scenario and priority to collect data
    for scenario, runs in all_results.items():
        data[scenario] = {}
        for run in runs.values():
            for flow in run['all_flows_results']:
                priority = flow.priority
                if priority not in data[scenario]:
                    data[scenario][priority] = []
                if flow.pkt_sink.waits.get(flow.fid, []):
                    average_wait = sum(flow.pkt_sink.waits[flow.fid]) / len(flow.pkt_sink.waits[flow.fid])
                    data[scenario][priority].append(average_wait)

    # Calculate means and confidence intervals
    for scenario in data:
        for priority in data[scenario]:
            delays = data[scenario][priority]
            mean, ci_lower, ci_upper = mean_confidence_interval(delays)
            data[scenario][priority] = (mean, ci_lower, ci_upper)

    # Find the number of scenarios and priorities
    num_scenarios = len(all_results)
    num_priorities = max(len(priorities) for priorities in data.values())

    plt.figure(figsize=(12, 8))
    bar_width = 0.15
    group_width = num_priorities * bar_width + (bar_width * 0.5)
    x_base_positions = np.arange(0, num_scenarios * group_width, group_width)

    # Plot bars
    for scenario_index, (scenario, priorities) in enumerate(data.items()):
        for priority_index, (priority, (mean, ci_lower, ci_upper)) in enumerate(priorities.items()):
            x_position = x_base_positions[scenario_index] + (bar_width * priority_index)
            bar_color = custom_colors[priority - 1]  # Assuming priority starts from 1
            bar = plt.bar(x_position, mean, color=bar_color, width=bar_width, label=f"Class of service {priority}" if scenario_index == 0 else "")
            plt.errorbar(x_position, mean, yerr=[[mean - ci_lower], [ci_upper - mean]], fmt='none', ecolor='black', capsize=10)
            
            # Annotate the upper and lower bounds of the confidence interval
            #plt.text(x_position, ci_upper + 0.1, f'{ci_upper:.3f}', ha='center', va='bottom', fontsize=10, color='black')
            #plt.text(x_position, ci_lower - 0.1, f'{ci_lower:.3f}', ha='center', va='top', fontsize=10, color='black')


    # Create a sorted legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    sorted_labels = sorted(by_label.keys(), key=lambda x: int(x.split()[-1]))  # Sort by priority number
    sorted_handles = [by_label[label] for label in sorted_labels]

    # Set x-axis labels for scenarios
    plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    plt.yticks(fontsize=20)
    if time_unit == 'ms':
        plt.ylabel('Average Delay [ms]', fontsize=22)
    else:
        plt.ylabel('Average Delay [s]', fontsize=22)
    plt.title('Average Delay per Priority', fontsize=22)
    plt.legend(sorted_handles, sorted_labels, fontsize=20)

    # Save and show the plot
    plt.savefig(os.path.join(results_dir, 'average_delay_per_priority.pdf'), bbox_inches='tight')
    plt.show()
    
###########################################################################################################################


def plot_network_PLI_priority(all_results):
    
    """
    Plot the Packet Loss Indicator (PLI) per priority class with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """


    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

 
    
    custom_colors = [
        "#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", 
        "#c55a11", "#ffd700", "#5f27cd", "#10ac84"
    ]


    # Initialize a dictionary to store data for each priority in each scenario
    data = {}

    # Iterate over each scenario and priority to collect data
    for scenario, runs in all_results.items():
        data[scenario] = {}
        for run in runs.values():
            for flow in run['all_flows_results']:
                priority = flow.priority
                if priority not in data[scenario]:
                    data[scenario][priority] = []
                total_packets_sent = flow.pkt_gen.packets_sent
                total_packets_dropped = total_packets_sent - flow.pkt_sink.packets_received.get(flow.fid, 0)
                if total_packets_sent > 0:
                    PLI = (total_packets_dropped / total_packets_sent) * 100
                else:
                    PLI = 0
                data[scenario][priority].append(PLI)

    # Calculate means and confidence intervals
    for scenario in data:
        for priority in data[scenario]:
            plis = data[scenario][priority]
            mean, ci_lower, ci_upper = mean_confidence_interval(plis)
            data[scenario][priority] = (mean, ci_lower, ci_upper)

    # Find the number of scenarios and priorities
    num_scenarios = len(all_results)
    num_priorities = max(len(priorities) for priorities in data.values())

    plt.figure(figsize=(12, 8))
    bar_width = 0.15
    group_width = num_priorities * bar_width + (bar_width * 0.5)
    x_base_positions = np.arange(0, num_scenarios * group_width, group_width)

    # Plot bars
    for scenario_index, (scenario, priorities) in enumerate(data.items()):
        for priority_index, (priority, (mean, ci_lower, ci_upper)) in enumerate(priorities.items()):
            x_position = x_base_positions[scenario_index] + (bar_width * priority_index)
            bar_color = custom_colors[priority - 1]  # Assuming priority starts from 1
            bar = plt.bar(x_position, mean, color=bar_color, width=bar_width, label=f"Class of service {priority}" if scenario_index == 0 else "")
            plt.errorbar(x_position, mean, yerr=[[mean - ci_lower], [ci_upper - mean]], fmt='none', ecolor='black', capsize=10)
            
            # Annotate the upper and lower bounds of the confidence interval
            #plt.text(x_position, ci_upper + 0.1, f'{ci_upper:.2f}', ha='center', va='bottom', fontsize=10, color='black')
            #plt.text(x_position, ci_lower - 0.1, f'{ci_lower:.2f}', ha='center', va='top', fontsize=10, color='black')

    # # Set x-axis labels for scenarios
    # plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    # plt.yticks(fontsize=20)
    # plt.ylabel('Packet Loss Indicator (%)', fontsize=22)
    # plt.title('Packet Loss Indicator per Priority', fontsize=22)
    # plt.legend(fontsize=20)

    # Create a sorted legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    sorted_labels = sorted(by_label.keys(), key=lambda x: int(x.split()[-1]))  # Sort by priority number
    sorted_handles = [by_label[label] for label in sorted_labels]

    # Set x-axis labels for scenarios
    plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    plt.yticks(fontsize=20)
    plt.ylabel('Packet Loss Indicator (%)', fontsize=22)
    plt.title('Packet Loss Indicator per Priority', fontsize=22)
    plt.legend(sorted_handles, sorted_labels, fontsize=20)
    # Save and show the plot
    plt.savefig(os.path.join(results_dir, 'average_network_PLI_per_priority.pdf'), bbox_inches='tight')
    plt.show()

################################################################################################################################

def plot_LDI_priority(all_results):
    
    """

    Plot the Load Distribution Index (LDI) per priority class with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    
    
    """
    
    
    
    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    custom_colors = [
        "#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", 
        "#c55a11", "#ffd700", "#5f27cd", "#10ac84"
    ]
    
    # Initialize a dictionary to store data for each priority in each scenario
    data = {}

    # Iterate over each scenario and priority to collect data
    for scenario, runs in all_results.items():
        data[scenario] = {}
        for run in runs.values():
            for flow in run['all_flows_results']:
                priority = flow.priority
                if priority not in data[scenario]:
                    data[scenario][priority] = []
                total_packets_per_link = []
                for (x, y), switch in run['switches'].items():
                    if isinstance(switch, FairPacketSwitch):
                        ports = switch.egress_ports
                    elif isinstance(switch, SimplePacketSwitch):
                        ports = switch.ports
                    else:
                        print(f"Unknown switch type for switch ({x}, {y})")
                        continue

                    for port in ports:
                        if isinstance(port, Port):
                            total_packets = port.packets_received - port.packets_dropped
                            total_packets_per_link.append(total_packets)

                if total_packets_per_link:
                    n = len(total_packets_per_link)
                    sum_xi = sum(total_packets_per_link)
                    sum_xi_squared = sum(x ** 2 for x in total_packets_per_link)
                    if sum_xi_squared != 0:
                        LDI = (1 / n) * (sum_xi ** 2 / sum_xi_squared)
                        data[scenario][priority].append(LDI)

    # Calculate means and confidence intervals
    for scenario in data:
        for priority in data[scenario]:
            ldis = data[scenario][priority]
            if ldis:
                mean, ci_lower, ci_upper = mean_confidence_interval(ldis)
                data[scenario][priority] = (mean, ci_lower, ci_upper)
            else:
                data[scenario][priority] = (0, 0, 0)  # If no data is available, set mean and CIs to 0

    # Find the number of scenarios and priorities
    num_scenarios = len(all_results)
    num_priorities = max(len(priorities) for priorities in data.values())

    plt.figure(figsize=(12, 8))
    bar_width = 0.15
    group_width = num_priorities * bar_width + (bar_width * 0.5)
    x_base_positions = np.arange(0, num_scenarios * group_width, group_width)

    # Plot bars
    for scenario_index, (scenario, priorities) in enumerate(data.items()):
        for priority_index, (priority, (mean, ci_lower, ci_upper)) in enumerate(priorities.items()):
            x_position = x_base_positions[scenario_index] + (bar_width * priority_index)
            bar_color = custom_colors[priority - 1]  # Assuming priority starts from 1
            bar = plt.bar(x_position, mean, color=bar_color, width=bar_width, label=f"Class of service {priority}" if scenario_index == 0 else "")
            plt.errorbar(x_position, mean, yerr=[[mean - ci_lower], [ci_upper - mean]], fmt='none', ecolor='black', capsize=10)
            
            # Annotate the upper and lower bounds of the confidence interval
            #plt.text(x_position, ci_upper + 0.1, f'{ci_upper:.2f}', ha='center', va='bottom', fontsize=10, color='black')
            #plt.text(x_position, ci_lower - 0.1, f'{ci_lower:.2f}', ha='center', va='top', fontsize=10, color='black')

    # # Set x-axis labels for scenarios
    # plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    # plt.yticks(fontsize=20)
    # plt.ylabel('Load Distribution Index (LDI)', fontsize=22)
    # plt.title('Load Distribution Index per Priority', fontsize=22)
    # plt.legend(fontsize=20)

    # Create a sorted legend
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    sorted_labels = sorted(by_label.keys(), key=lambda x: int(x.split()[-1]))  # Sort by priority number
    sorted_handles = [by_label[label] for label in sorted_labels]

    # Set x-axis labels for scenarios
    plt.xticks(x_base_positions + group_width / 2 - bar_width, list(all_results.keys()), fontsize=20, rotation=45)
    plt.yticks(fontsize=20)
    plt.ylabel('Load Distribution Index (LDI)', fontsize=22)
    plt.title('Load Distribution Index per Priority', fontsize=22)
    plt.legend(sorted_handles, sorted_labels, fontsize=20)

    # Save and show the plot
    plt.savefig(os.path.join(results_dir, 'average_LDI_per_priority.pdf'), bbox_inches='tight')
    plt.show()

##############################################################################################################################

def print_summary_statistics_per_priority(all_results, results_dir=None):
    """
    Print summary statistics of the simulation results per priority and save them to a file.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """
    if results_dir is None:
        results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists

    # Define the file path for the summary statistics
    summary_file_path = os.path.join(results_dir, 'summary_statistics_per_priority.txt')

    with open(summary_file_path, 'w') as summary_file:
        for scenario, runs in all_results.items():
            total_sent = defaultdict(float)
            total_received = defaultdict(float)
            total_dropped = defaultdict(float)
            delays = defaultdict(list)
            plls = defaultdict(list)
            ldis = defaultdict(list)
            num_runs = len(runs)

            for run in runs.values():
                for flow in run['all_flows_results']:
                    priority = flow.priority
                    total_sent[priority] += flow.pkt_gen.packets_sent
                    total_received[priority] += flow.pkt_sink.packets_received.get(flow.fid, 0)
                    if flow.pkt_sink.waits.get(flow.fid, []):
                        average_wait = sum(flow.pkt_sink.waits[flow.fid]) / len(flow.pkt_sink.waits[flow.fid])
                        delays[priority].append(average_wait)

                total_packets_sent = sum(flow.pkt_gen.packets_sent for flow in run['all_flows_results'])
                total_packets_received = sum(flow.pkt_sink.packets_received.get(flow.fid, 0) for flow in run['all_flows_results'])
                total_packets_dropped = total_packets_sent - total_packets_received

                if total_packets_sent > 0:
                    pli = (total_packets_dropped / total_packets_sent) * 100
                else:
                    pli = 0
                plls[priority].append(pli)

                total_packets_per_link = []
                for (x, y), switch in run['switches'].items():
                    if isinstance(switch, FairPacketSwitch):
                        ports = switch.egress_ports
                    elif isinstance(switch, SimplePacketSwitch):
                        ports = switch.ports
                    else:
                        print(f"Unknown switch type for switch ({x}, {y})")
                        continue

                    for port in ports:
                        if isinstance(port, Port):
                            total_packets = port.packets_received - port.packets_dropped
                            total_packets_per_link.append(total_packets)

                if total_packets_per_link:
                    n = len(total_packets_per_link)
                    sum_xi = sum(total_packets_per_link)
                    sum_xi_squared = sum(x ** 2 for x in total_packets_per_link)
                    if sum_xi_squared != 0:
                        ldi = (1 / n) * (sum_xi ** 2 / sum_xi_squared)
                    else:
                        ldi = 0
                    ldis[priority].append(ldi)

            for priority in total_sent:
                avg_sent = total_sent[priority] / num_runs
                avg_received = total_received[priority] / num_runs
                avg_dropped = avg_sent - avg_received
                avg_delay = np.mean(delays[priority]) if delays[priority] else 0
                avg_pli = np.mean(plls[priority]) if plls[priority] else 0
                avg_ldi = np.mean(ldis[priority]) if ldis[priority] else 0

                delay_ci = mean_confidence_interval(delays[priority])
                pli_ci = mean_confidence_interval(plls[priority])
                ldi_ci = mean_confidence_interval(ldis[priority])

                summary_file.write(f"Scenario {scenario} - Priority {priority}:\n")
                summary_file.write(f"  Average Packets Sent: {avg_sent}\n")
                summary_file.write(f"  Average Packets Received: {avg_received}\n")
                summary_file.write(f"  Average Packets Dropped: {avg_dropped}\n")
                summary_file.write(f"  Average Delay: {avg_delay}\n")
               # summary_file.write(f"  Delay CI (Min, Mean, Max): {delay_ci[1] - delay_ci[0]}, {delay_ci[1]}, {delay_ci[2] - delay_ci[1]}\n")
                summary_file.write(f"  Average PLI: {avg_pli}\n")
               # summary_file.write(f"  PLI CI (Min, Mean, Max): {pli_ci[1] - pli_ci[0]}, {pli_ci[1]}, {pli_ci[2] - pli_ci[1]}\n")
              #  summary_file.write(f"  Average LDI: {avg_ldi}\n")
              #  summary_file.write(f"  LDI CI (Min, Mean, Max): {ldi_ci[1] - ldi_ci[0]}, {ldi_ci[1]}, {ldi_ci[2] - ldi_ci[1]}\n")
                summary_file.write("\n")

    print(f"Summary statistics per priority saved to {summary_file_path}")
    print()
