#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test helper functions for ICARUS simulation tests.
"""

import sys
import os

# Add the project src directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

from topo.toroidal_topo import ToroidalTopo
from simulator.simulator import Simulator


def create_test_config(time_unit='ms', simulation_time=100, generation_finish_time=100):
    """
    Create a minimal test configuration dictionary.
    
    Args:
        time_unit: Time unit ('ms' or 's')
        simulation_time: Simulation time in the specified unit
        generation_finish_time: Generation finish time in the specified unit
    
    Returns:
        dict: Test configuration
    """
    return {
        'scenario_name': 'test_scenario',
        'system': {
            'time_unit': time_unit,
            'width': 4,
            'height': 4,
            'downlink_number': 15,
            'uplink_number': 15,
            'interlink_capacity': 10000000,
            'demand_matrix_generation': 'fixed'
        },
        'optimization': {
            'num_commodities': 2,
            'optimization_model': 'multicommodity',
            'max_hops': 7,
            'objective_func': 'minimize_max_flow',
            'split_commodities': 'on'
        },
        'fixed_demand': {
            'arrival_rate': [2400, 2400],
            'priority': [1, 1],
            'source': ['OBPModule(0, 0)_uplink_0', 'OBPModule(0, 1)_uplink_0'],
            'destination': ['OBPModule(3, 1)_downlink_0', 'OBPModule(3, 2)_downlink_0']
        },
        'simulation': {
            'num_runs': 1,
            'simulation_time': simulation_time,
            'generation_finish_time': generation_finish_time,
            'buffer_size': 15000,
            'obp_capacity': 1000,
            'fetchingAlgorithm': 'fifo',
            'brancher_type': 'random',
            'limit_bytes': True,
            'interarrival_time_generation': 'exponential',
            'packet_distribution_generation': 'fixed',
            'avg_packet_size': 1500.0,
            'max_failed_nodes': 0,
            'probability_failure': 0,
            'failures': [],
            'path_mode': 'warm',
            'failure_strategy': 'fail-routing',
            'backup_is_considered': 'off',
            're_routing_is_considered': 'off',
            'backup': []
        },
        'obp_port': {
            'infinite_capacity': False
        },
        'interlink': {
            'infinite_capacity': False
        }
    }


def create_test_simulator(config, result_dir='/tmp/test_results'):
    """
    Create a test Simulator instance.
    
    Args:
        config: Configuration dictionary
        result_dir: Result directory path
    
    Returns:
        Simulator: Test simulator instance
    """
    regen_obp = ToroidalTopo(scenario_config=config, 
                           width=config['system']['width'],
                           height=config['system']['height'])
    
    simulator = Simulator(
        regen_obp=regen_obp,
        scenario_config=config,
        result_dir=result_dir,
        current_run=1,
        current_algo='fifo',
        demand_matrix=None,
        updated_demand_matrix=None
    )
    
    return simulator

