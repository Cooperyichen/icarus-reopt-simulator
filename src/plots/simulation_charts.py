#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module provides functions for plotting various statistics
such as total packets sent, received, dropped, average delay, 
network PLI, and LDI from simulation results.




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

def plot_total_packets_sent__(all_results):
    """
    Plot the total packets sent with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """
    
    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    total_flows_list = []
    mean_packets_sent = []
    ci_lengths = []

    # Calculate means and confidence intervals for each setup
    for setup, runs in all_results.items():
        packets_sent = []
        for run_key, run_data in runs.items():
            all_flows = run_data['all_flows_results']
            packets_sent.append(sum(flow.pkt_gen.packets_sent for flow in all_flows))
        
        mean, ci_lower, ci_upper = mean_confidence_interval(packets_sent)
        total_flows_list.append(setup)
        mean_packets_sent.append(mean)
        ci_lengths.append((ci_upper - mean, mean - ci_lower))

    # Custom earth tone colors
    custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]

    # Create the bar plot with matplotlib to control the bar width
    plt.figure(figsize=(14, 8))
    bar_width = 0.6  # Set your desired bar width here
    x_positions = np.arange(len(total_flows_list))

    bars = plt.bar(x_positions, mean_packets_sent, color=custom_colors, width=bar_width)

    # Adding the error bars
    for i, bar in enumerate(bars):
        ci_lower, ci_upper = ci_lengths[i]
        plt.errorbar(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                      yerr=[[ci_lower], [ci_upper]], fmt='none', ecolor='black', capsize=14)

    # Rotate x-axis labels to prevent overlap
    plt.xticks(x_positions, total_flows_list, rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)  # Increase font size for y-axis labels
    plt.ylabel('Packets Sent', fontsize=14)
    plt.title('Total Packets Sent', fontsize=16)

    pdf_filename = os.path.join(results_dir, 'average_packets_sent.pdf')

    plt.tight_layout()  # Adjust layout to make room for rotated labels
    plt.savefig(pdf_filename, bbox_inches='tight')
    plt.show()
  
######################################################################################################################
# Adapted function to plot total packets received with confidence intervals
def plot_total_packets_received__(all_results):
    """
    Plot the total packets received with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """
    
    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    total_flows_list = []
    mean_packets_received = []
    ci_lengths = []

    # Calculate means and confidence intervals for each setup
    for setup in all_results:
        packets_received = [
            sum(flow.pkt_sink.packets_received.get(flow.fid, 0) for flow in run['all_flows_results'])
            for run in all_results[setup].values()
        ]
        mean, ci_lower, ci_upper = mean_confidence_interval(packets_received)
        total_flows_list.append(setup)
        mean_packets_received.append(mean)
        ci_lengths.append((ci_upper - mean, mean - ci_lower))

    # Custom earth tone colors
    custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]

    # Create the bar plot with matplotlib to control the bar width
    plt.figure(figsize=(14, 8))
    bar_width = 0.6  # Set your desired bar width here
    x_positions = np.arange(len(total_flows_list))

    bars = plt.bar(x_positions, mean_packets_received, color=custom_colors, width=bar_width)

    # Adding the error bars and annotating the confidence interval bounds on the plot
    for i, bar in enumerate(bars):
        ci_lower, ci_upper = ci_lengths[i]
        plt.errorbar(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     yerr=[[ci_lower], [ci_upper]], fmt='none', ecolor='black', capsize=14)
        # Uncomment the lines below to annotate the confidence interval bounds on the plot
        # plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + ci_upper, f'{bar.get_height() + ci_upper:.2f}',
        #          ha='center', va='bottom', color='black', fontsize=15)
        # plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - ci_lower, f'{bar.get_height() - ci_lower:.2f}',
        #          ha='center', va='top', color='black', fontsize=15)

    # Set the x-axis labels to the names of the setups
    plt.xticks(x_positions, total_flows_list, rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)  # Increase font size for y-axis labels
    plt.ylabel('Packets Received', fontsize=14)
    plt.title('Total Packets Received', fontsize=16)

    pdf_filename = os.path.join(results_dir, 'average_packets_received.pdf')

    plt.tight_layout()  # Adjust layout to make room for rotated labels
    plt.savefig(pdf_filename, bbox_inches='tight')
    plt.show()
    
##################################################################################################################
 
def plot_total_packets_dropped__(all_results):
    """
    Plot the total packets dropped with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """
    
    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    total_flows_list = []
    mean_packets_dropped = []
    ci_lengths = []

    # Calculate means and confidence intervals for each setup
    for setup in all_results:
        packets_dropped = [
            sum(flow.pkt_gen.packets_sent for flow in run['all_flows_results']) -
            sum(flow.pkt_sink.packets_received.get(flow.fid, 0) for flow in run['all_flows_results'])
            for run in all_results[setup].values()
        ]
        mean, ci_lower, ci_upper = mean_confidence_interval(packets_dropped)
        total_flows_list.append(setup)
        mean_packets_dropped.append(mean)
        ci_lengths.append((ci_upper - mean, mean - ci_lower))

    # Custom earth tone colors
    custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]

    # Create the bar plot with matplotlib to control the bar width
    plt.figure(figsize=(14, 8))
    bar_width = 0.6  # Set your desired bar width here
    x_positions = np.arange(len(total_flows_list))

    bars = plt.bar(x_positions, mean_packets_dropped, color=custom_colors, width=bar_width)

    # Adding the error bars and annotating the confidence interval bounds on the plot
    for i, bar in enumerate(bars):
        ci_lower, ci_upper = ci_lengths[i]
        plt.errorbar(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     yerr=[[ci_lower], [ci_upper]], fmt='none', ecolor='black', capsize=14)
        # Uncomment the lines below to annotate the confidence interval bounds on the plot
        # plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + ci_upper, f'{bar.get_height() + ci_upper:.2f}',
        #          ha='center', va='bottom', color='black', fontsize=15)
        # plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() - ci_lower, f'{bar.get_height() - ci_lower:.2f}',
        #          ha='center', va='top', color='black', fontsize=15)

    # Set the x-axis labels to the names of the setups
    plt.xticks(x_positions, total_flows_list, rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)  # Increase font size for y-axis labels
    plt.ylabel('Total Packets Dropped', fontsize=14)
    plt.title('Total Packets Dropped', fontsize=16)

    pdf_filename = os.path.join(results_dir, 'average_packets_dropped.pdf')

    plt.tight_layout()  # Adjust layout to make room for rotated labels
    plt.savefig(pdf_filename, bbox_inches='tight')
    plt.show()



##############################################################################################################

def plot_average_delay__(all_results, time_unit='s'):
    """
    Plot the average delay with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    :param time_unit: Time unit for the delay (default is seconds).
    :type time_unit: str, optional
    """

    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    total_flows_list = []
    mean_delay = []
    ci_lengths = []

    # Calculate means and confidence intervals for each setup
    for setup in all_results:
        delays = []
        for run in all_results[setup].values():
            run_delays = []
            for flow in run['all_flows_results']:
                if flow.pkt_sink.waits.get(flow.fid, []):
                    average_wait = sum(flow.pkt_sink.waits[flow.fid]) / len(flow.pkt_sink.waits[flow.fid])
                    run_delays.append(average_wait)
            if run_delays:
                delays.append(sum(run_delays) / len(run_delays))

        mean, ci_lower, ci_upper = mean_confidence_interval(delays)
        total_flows_list.append(setup)
        mean_delay.append(mean)
        ci_lengths.append((ci_upper - mean, mean - ci_lower))

    # Custom earth tone colors
    custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]

    # Convert delay values based on time_unit BEFORE plotting
    # Note: delays from SimPy are in seconds
    if time_unit == 'ms':
        mean_delay = [d * 1000 for d in mean_delay]  # Convert to milliseconds
        ci_lengths = [(upper * 1000, lower * 1000) for upper, lower in ci_lengths]  # Convert CI to milliseconds
    
    # Create the bar plot with matplotlib to control the bar width
    plt.figure(figsize=(10, 6))
    bar_width = 0.4  # Set your desired bar width here
    x_positions = np.arange(len(total_flows_list))

    bars = plt.bar(x_positions, mean_delay, color=custom_colors, width=bar_width)

    # Adding the error bars and annotating the confidence interval bounds on the plot
    for i, bar in enumerate(bars):
        ci_upper, ci_lower = ci_lengths[i]
        plt.errorbar(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                      yerr=[[ci_lower], [ci_upper]], fmt='none', ecolor='black', capsize=14)

    # Set the x-axis labels to the names of the setups
    plt.xticks(x_positions, total_flows_list, rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)  # Increase font size for y-axis labels

    if time_unit == 'ms':
        plt.ylabel('Average Delay [ms]', fontsize=14)
    else:  # Default to seconds
        plt.ylabel('Average Delay [s]', fontsize=14)

    plt.title('Average End-to-End Delay', fontsize=16)

    pdf_filename = os.path.join(results_dir, 'average_delay.pdf')

    plt.tight_layout()  # Adjust layout to make room for rotated labels
    plt.savefig(pdf_filename, bbox_inches='tight')
    plt.show()

    
##############################################################################################################



def plot_network_PLI__(all_results):
    """
    Plot the Packet Loss Indicator (PLI) with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """
    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")

    total_flows_list = []
    mean_PLI = []
    ci_lengths = []

    for setup in all_results:
        PLIs = []
        for run in all_results[setup].values():
            total_packets_sent = sum(flow.pkt_gen.packets_sent for flow in run['all_flows_results'])
            total_packets_dropped = sum(flow.pkt_gen.packets_sent - flow.pkt_sink.packets_received.get(flow.fid, 0) for flow in run['all_flows_results'])
            
            if total_packets_sent > 0:
                PLI = (total_packets_dropped / total_packets_sent) * 100
            else:
                PLI = 0
            PLIs.append(PLI)
        
        mean, ci_lower, ci_upper = mean_confidence_interval(PLIs)
        total_flows_list.append(setup)
        mean_PLI.append(mean)
        ci_lengths.append((ci_upper - mean, mean - ci_lower))

    # Custom earth tone colors
    custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]
    plt.figure(figsize=(10, 6))
    bar_width = 0.4
    x_positions = np.arange(len(total_flows_list))

    bars = plt.bar(x_positions, mean_PLI, color=custom_colors, width=bar_width)
    for i, bar in enumerate(bars):
        ci_lower, ci_upper = ci_lengths[i]
        plt.errorbar(bar.get_x() + bar.get_width() / 2, bar.get_height(), yerr=[[ci_lower], [ci_upper]], fmt='none', ecolor='black', capsize=14)

    plt.xticks(x_positions, total_flows_list, rotation=45, ha='right', fontsize=12)
    plt.yticks(fontsize=12)
    plt.ylabel('Packet Loss Indicator (%)', fontsize=14)
    plt.title('Average Network Packet Loss Indicator (PLI)', fontsize=16)

    pdf_filename = os.path.join(results_dir, 'average_network_PLI.pdf')
    plt.tight_layout()
    plt.savefig(pdf_filename, bbox_inches='tight')
    plt.show()


##############################################################################################################
def plot_LDI__(all_results):
    
    """
    Plot the Load Distribution Index (LDI) with confidence intervals.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    """


    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")


    total_flows_list = []
    mean_LDI = []
    ci_lengths = []

    for setup in all_results:
        LDIs = []
        for run in all_results[setup].values():
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
                        # Total packets sent is the number of packets received minus the packets dropped
                        total_packets = port.packets_received - port.packets_dropped
                        total_packets_per_link.append(total_packets)

            if total_packets_per_link:
                n = len(total_packets_per_link)
                sum_xi = sum(total_packets_per_link)
                sum_xi_squared = sum(x ** 2 for x in total_packets_per_link)
                if sum_xi_squared != 0:
                    LDI = (1 / n) * (sum_xi ** 2 / sum_xi_squared)
                    LDIs.append(LDI)

        if LDIs:
            mean, ci_lower, ci_upper = mean_confidence_interval(LDIs)
            total_flows_list.append(setup)
            mean_LDI.append(mean)
            ci_lengths.append((ci_upper - mean, mean - ci_lower))

    # Custom earth tone colors
    custom_colors = ["#959595", "#8a95a2", "#dfc1bb", "#3498db", "#e74c3c", "#c55a11", "#ffd700", "#5f27cd", "#10ac84"]

    plt.figure(figsize=(10, 6))
    bar_width = 0.4
    x_positions = np.arange(len(total_flows_list))

    bars = plt.bar(x_positions, mean_LDI, color=custom_colors, width=bar_width)

    for i, bar in enumerate(bars):
        ci_lower, ci_upper = ci_lengths[i]
        plt.errorbar(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                     yerr=[[ci_lower], [ci_upper]], fmt='none', ecolor='black', capsize=14)

    plt.xticks(x_positions, total_flows_list, fontsize=22)
    plt.yticks(fontsize=15)  # Increase font size for y-axis labels
    plt.ylabel('Load Distribution Index (LDI)', fontsize=22)

    pdf_filename = os.path.join(results_dir, 'average_LDI.pdf')
    plt.savefig(pdf_filename, bbox_inches='tight')
    plt.show()


##########################################################################################


def print_summary_statistics(all_results, results_dir=None, time_unit='s'):
    """
    Print summary statistics of the simulation results and save them to a file.
    
    :param all_results: Dictionary containing the simulation results.
    :type all_results: dict
    :param time_unit: Time unit for delay ('s' for seconds, 'ms' for milliseconds).
    :type time_unit: str
    """
    # Update the path to the results directory
    if results_dir is None:
        results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists

    # Define the file path for the summary statistics
    summary_file_path = os.path.join(results_dir, 'summary_statistics.txt')

    with open(summary_file_path, 'w') as summary_file:
        for scenario, runs in all_results.items():
            total_sent = []
            total_received = []
            total_dropped = []
            delays = []
            plls = []
            ldis = []

            for run_id, run in runs.items():
                run_sent = sum(flow.pkt_gen.packets_sent for flow in run['all_flows_results'])
                run_received = sum(flow.pkt_sink.packets_received.get(flow.fid, 0) for flow in run['all_flows_results'])
                run_dropped = run_sent - run_received
                run_delays = [sum(flow.pkt_sink.waits[flow.fid]) / len(flow.pkt_sink.waits[flow.fid])
                              for flow in run['all_flows_results'] if flow.pkt_sink.waits.get(flow.fid, [])]

                total_packets_sent = run_sent
                total_packets_received = run_received
                total_packets_dropped = total_packets_sent - total_packets_received

                pli = (total_packets_dropped / total_packets_sent) * 100 if total_packets_sent > 0 else 0

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
                    ldi = (1 / n) * (sum_xi ** 2 / sum_xi_squared) if sum_xi_squared != 0 else 0
                else:
                    ldi = 0

                delays.extend(run_delays)
                plls.append(pli)
                ldis.append(ldi)

                total_sent.append(run_sent)
                total_received.append(run_received)
                total_dropped.append(run_dropped)

            avg_sent = np.mean(total_sent) if total_sent else 0
            avg_received = np.mean(total_received) if total_received else 0
            avg_dropped = np.mean(total_dropped) if total_dropped else 0
            avg_delay = np.mean(delays) if delays else 0
            avg_pli = np.mean(plls) if plls else 0
            avg_ldi = np.mean(ldis) if ldis else 0

            # Confidence intervals
            delay_ci = mean_confidence_interval(delays)
            pli_ci = mean_confidence_interval(plls)
            ldi_ci = mean_confidence_interval(ldis)

            # Convert delay based on time_unit
            # Note: delays from SimPy are in seconds
            if time_unit == 'ms':
                delay_value = avg_delay * 1000  # Convert seconds to milliseconds
                delay_unit = 'ms'
            else:
                delay_value = avg_delay  # Keep in seconds
                delay_unit = 's'
            
            summary_file.write(f"Scenario {scenario}:\n")
            summary_file.write(f"  Average Packets Sent: {avg_sent}\n")
            summary_file.write(f"  Average Packets Received: {avg_received}\n")
            summary_file.write(f"  Average Packets Dropped: {avg_dropped}\n")
            summary_file.write(f"  Average Delay: {delay_value:.6f} {delay_unit}\n")
           # summary_file.write(f"  Delay CI (Min, Mean, Max): {delay_ci[1] - delay_ci[0]}, {delay_ci[1]}, {delay_ci[2] - delay_ci[1]}\n")
            summary_file.write(f"  Average PLI: {avg_pli}\n")
          #  summary_file.write(f"  PLI CI (Min, Mean, Max): {pli_ci[1] - pli_ci[0]}, {pli_ci[1]}, {pli_ci[2] - pli_ci[1]}\n")
            summary_file.write(f"  Average LDI: {avg_ldi}\n")
         #   summary_file.write(f"  LDI CI (Min, Mean, Max): {ldi_ci[1] - ldi_ci[0]}, {ldi_ci[1]}, {ldi_ci[2] - ldi_ci[1]}\n")
            summary_file.write("\n")

        #     # Debugging prints
        #     print(f"Scenario {scenario}:")
        #     print(f"  Average Packets Sent: {avg_sent}")
        #     print(f"  Average Packets Received: {avg_received}")
        #     print(f"  Average Packets Dropped: {avg_dropped}")
        #     print(f"  Average Delay: {avg_delay}")
        #   #  print(f"  Delay CI (Min, Mean, Max): {delay_ci[1] - delay_ci[0]}, {delay_ci[1]}, {delay_ci[2] - delay_ci[1]}")
        #     print(f"  Average PLI: {avg_pli}")
        #  #   print(f"  PLI CI (Min, Mean, Max): {pli_ci[1] - pli_ci[0]}, {pli_ci[1]}, {pli_ci[2] - pli_ci[1]}")
        #     print(f"  Average LDI: {avg_ldi}")
        # #    print(f"  LDI CI (Min, Mean, Max): {ldi_ci[1] - ldi_ci[0]}, {ldi_ci[1]}, {ldi_ci[2] - ldi_ci[1]}")

    print(f"Summary statistics saved to {summary_file_path}")
    print()