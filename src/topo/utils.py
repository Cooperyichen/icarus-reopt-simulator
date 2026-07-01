#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This utility script provides various helper functions and classes for network simulation and analysis.
The primary and most important function in this script is `generate_fib`, which generates the Forwarding
Information Base (FIB) for the graph nodes.

"""

# @author: zineb.garroussi@polymtl.ca


import numpy as np
import matplotlib.pyplot as plt
import os
from collections import defaultdict

from utils.libs import *  # Importing all libraries centralized in the libs.py module


from random import sample
import networkx as nx

from flow.flow import Flow





def get_scenario_filenames(scenarios_directory):
    # Define the full path to the scenarios.yaml file
    scenarios_file_path = os.path.join(scenarios_directory, 'scenarios.yaml')
    
    # Check if the scenarios.yaml file exists in the specified directory
    if not os.path.isfile(scenarios_file_path):
        raise FileNotFoundError(f"No such file: {scenarios_file_path}")
    
    # Load the scenarios.yaml file to get the list of scenario filenames
    with open(scenarios_file_path, 'r') as file:
        scenarios_config = yaml.safe_load(file)

    # Extract the list of scenario filenames from the loaded configuration
    scenario_filenames = scenarios_config['scenarios']
    
    # Return the list of scenario filenames
    return scenario_filenames

##############################################################################################################
def load_yaml_file(filename):
    """Load the contents of a YAML file into a dictionary."""
    with open(filename, 'r') as file:
        return yaml.safe_load(file)

##############################################################################################################


def ensure_directory_exists(dir_path):
    """
    Ensures that a given directory path exists.
    If it doesn't exist, it's created.
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)    
        

##############################################################################################################


def save_to_csv(df, filename):
    """
    Saves a DataFrame to a CSV file.
    
    Args:
        df (pd.DataFrame): The DataFrame to save.
        filename (str): The filename for the CSV file.
    """
    # Use filename directly since it's the full path
    df.to_csv(filename, index=False)
    print(f"Data saved to: {filename}")
    


################################################################################################



# This function needs to return both the lower and upper confidence interval bounds
def mean_confidence_interval(data, confidence=0.95):
    """Calculate the mean and confidence interval."""
    n = len(data)
    mean = np.mean(data)
    stderr = stats.sem(data)
    h = stderr * stats.t.ppf((1 + confidence) / 2., n - 1)
    return mean, mean - h, mean + h  # Return the mean, lower bound, and upper bound

####################################################################################################################

def generate_fib(G, all_flows):
    """
    Generate Forwarding Information Base (FIB) for the graph nodes.

    This function generates the FIB for each node in the graph `G` based on the provided flows.
    The FIB maps flows to their corresponding next hops and ports.

    Args:
        G (networkx.DiGraph): The graph representing the network topology.
        all_flows (list): List of all flows in the network.

    Returns:
        networkx.DiGraph: The updated graph with FIB information added to each node.
    """
    # # Exclude uplink and downlink nodes from the initial list of nodes
    # nodes_to_process = [n for n in G.nodes() if G.nodes[n]["type_node"] not in ["uplink_node", "downlink_node"]]

    # for n in nodes_to_process:
    #     node = G.nodes[n]

    #     node["port_to_nexthop"] = dict()
    #     node["nexthop_to_port"] = dict()

    #     for port, nh in enumerate(nx.neighbors(G, n)):
    #         # Skip uplink and downlink neighbors
    #         if G.nodes[nh]["type_node"] in ["uplink_node", "downlink_node"]:
    #             continue
    #         node["nexthop_to_port"][nh] = port
    #         node["port_to_nexthop"][port] = nh

    #     node["flow_to_port"] = dict()
    #     node["flow_to_nexthop"] = dict()
        
        
        
    # Exclude uplink and downlink nodes from the initial list of nodes
    nodes_to_process = [n for n in G.nodes() if G.nodes[n]["type_node"] == "obp_module"]

    for n in nodes_to_process:
        node = G.nodes[n]

        node["port_to_nexthop"] = dict()
        node["nexthop_to_port"] = dict()

        # Only consider neighbors that are also OBP modules
        obp_neighbors = [nh for nh in nx.neighbors(G, n) if G.nodes[nh]["type_node"] == "obp_module"]
        for port, nh in enumerate(obp_neighbors):
            node["nexthop_to_port"][nh] = port
            node["port_to_nexthop"][port] = nh

        node["flow_to_port"] = dict()
        node["flow_to_nexthop"] = dict()        
        
        
        
        

    for flow in all_flows:
        path = list(zip(flow.path, flow.path[1:]))
        for seg in path:
            a, z = seg
            # Skip uplink and downlink nodes
            if G.nodes[a]["type_node"] in ["uplink_node", "downlink_node"]:
                continue
            if G.nodes[z]["type_node"] in ["uplink_node", "downlink_node"]:
                continue
            if flow.fid not in G.nodes[a]["flow_to_port"]:
                G.nodes[a]["flow_to_port"][flow.fid] = []
            if flow.fid not in G.nodes[a]["flow_to_nexthop"]:
                G.nodes[a]["flow_to_nexthop"][flow.fid] = []
            G.nodes[a]["flow_to_port"][flow.fid].append(G.nodes[a]["nexthop_to_port"][z])
            G.nodes[a]["flow_to_nexthop"][flow.fid].append(z)

    # Print the generated FIB information
    for n in nodes_to_process:
        node = G.nodes[n]
        # print(f"Node {n}:")
        # print(f"  Port to Next Hop: {node['port_to_nexthop']}")
        # print(f"  Next Hop to Port: {node['nexthop_to_port']}")
        # print(f"  Flow to Port: {node['flow_to_port']}")
        # print(f"  Flow to Next Hop: {node['flow_to_nexthop']}")

    return G

###################################################################################################################


def convert_none(value):
    # Convertit la valeur en minuscules pour la comparaison
    value_lower = str(value).lower()
    
    # Vérifie si la valeur convertie est 'none' ou 'infinite'
    if value_lower == 'none' or value_lower == 'infinite':
        return None
    # Ajoute ici d'autres conditions si nécessaire
    
    return value


#####################################################################################################


def print_results(optimization_model, all_flows, total_flows):
    """
    Print simulation results including total packets sent, received, dropped,
    network Packet Loss Indicator (PLI), average delay, and Load Distribution Index (LDI).
    
    :param optimization_model: The optimization model used in the simulation.
    :type optimization_model: str
    :param all_flows: List of all flows in the simulation.
    :type all_flows: list[Flow]
    :param total_flows: Total number of flows in the simulation.
    :type total_flows: int
    """

    total_packets_dropped = sum(flow.pkt_gen.packets_sent - flow.pkt_sink.packets_received.get(flow.fid, 0) for flow in all_flows)
    total_packets_sent = sum(flow.pkt_gen.packets_sent for flow in all_flows)
    total_packets_received = sum(flow.pkt_sink.packets_received.get(flow.fid, 0) for flow in all_flows)
    
    network_PLI = total_packets_dropped / total_packets_sent if total_packets_sent > 0 else 0
    average_delay = sum(
        sum(flow.pkt_sink.waits.get(flow.fid, [])) / len(flow.pkt_sink.waits.get(flow.fid, [])) if flow.pkt_sink.waits.get(flow.fid, []) else 0
        for flow in all_flows
    ) / total_flows if total_flows > 0 else 0
    LDI = network_PLI  # Assuming LDI is the same as network_PLI

    print(f"Optimization Model: {optimization_model}")
    print(f"Total Packets Sent: {total_packets_sent}")
    print(f"Total Packets Received: {total_packets_received}")
    print(f"Total Packets Dropped: {total_packets_dropped}")
    print(f"Network PLI: {network_PLI}")
    print(f"Average Delay: {average_delay}")
    print(f"LDI: {LDI}")
    print(f"Total Flows: {total_flows}")



################################################################################################
