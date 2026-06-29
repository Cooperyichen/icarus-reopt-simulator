#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project ICARUS-MDA-POLY MTL Load Balancing Simulation

Created on Thu July 10 12:36:05 2023

This script is the main module for sim_net_hts, which simulates network scenarios for load balancing.
It orchestrates the entire simulation process, from loading scenario configurations to running simulations
and generating plots for analysis. The script uses a toroidal topology for network simulations and includes 
multi-commodity flow optimization to handle various network demands efficiently.

Key functionalities:
- Load and process scenario configurations from YAML files.
- Run multiple simulation scenarios with different configurations.
- Visualize network topologies and generate demand matrices.
- Optimize network flows using multi-commodity flow optimization.
- Simulate network behavior and collect data on flow performance.
- Generate and save various plots for performance analysis.

Usage:
- Ensure that the necessary configuration files are available in the specified directory.
- Execute the script to run simulations and generate results and plots.

Dependencies:
- Python 3.10.9 or higher
- Required Python packages:  In utils/libs.py


"""


# # @author: zineb.garroussi@polymtl.ca


import sys
import os

#sys.path.append('/home/monpc/project_hts_python/project/sim_net_hts/src')

# Add the project directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_path)



from utils.libs import *
from topo.toroidal_topo import ToroidalTopo
from topo.utils import print_results
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from topo.utils import get_scenario_filenames
from topo.utils import load_yaml_file
from topo.utils import ensure_directory_exists
from topo.utils import save_to_csv
from simulator.simulator import Simulator

from plots.simulation_charts import * 
from plots.simulation_charts_per_priority import * 


from plots.plots_first_paper import *
from plots.plots_first_paper_bis import *
from plots.plots_second_paper import *

###############################################################################


# Function to delete 'received_packets.csv'
def delete_csv_file():
    """
    Deletes the 'received_packets.csv' file if it exists in the results directory.
    """
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    csv_file = os.path.join(results_dir, 'received_packets.csv')
    if os.path.exists(csv_file):
        os.remove(csv_file)
        print(f"Deleted existing file: {csv_file}")
        
        


# =============================================================================
# ###############  QUEUE SIMULATION 
# 
# =============================================================================

def run_simulation_scenario(scenario_config,result_dir,current_run, precomputed_demand_matrix=None) :# , port_buffers):
    
    
    
    """
    Run simulation based on the provided scenario configuration.

    :param scenario_config: Configuration for the scenario to be run.
    :type scenario_config: dict
    :param result_dir: Directory to save the simulation results.
    :type result_dir: str
    :param current_run: Identifier for the current run of the simulation.
    :type current_run: int
    :param precomputed_demand_matrix: Optional precomputed demand matrix (DataFrame) to skip optimization.
                                       If provided, optimizer will not be called.
    :type precomputed_demand_matrix: pandas.DataFrame or None
    :return: Tuple containing all flows, switches, and blocked flows.
    :rtype: tuple
    """    
    
    
    
    scenario_name = scenario_config.get("scenario_name", "Unnamed Scenario")
    print(f"Running simulation for {scenario_name} ...")
    
    # For reproducibility
    #random.seed(scenario_config['random_seed']['seed_value'])    # I comment this line because  I use random seed in main class 
    ############################################################################################################################
    width = scenario_config['system']['width']

    height = scenario_config['system']['height']

    simulation_time = scenario_config['simulation']['simulation_time']


    
    # Instantiate a RegenerativeOBP object with a 4x4 grid
    regen_obp = ToroidalTopo(scenario_config = scenario_config, width=width, height=height)
    

    # Visualize the created toroidal grid
    regen_obp.visualize_obp()
    #regen_obp.visualize_grid()    
    
    #regen_obp.print_node_counts()
    
    # for row in regen_obp.obp_topology:
    #     for module in row:
    #         print(module, "neighbors:", module.neighbors)
    #     print()
        
        
    # Extract OBP topology and neighbors
    obp_data_list = []
    for row in regen_obp.obp_topology:
        for module in row:
            data = {
                'OBP Module': str(module),
                'Neighbors': ', '.join(str(neighbor) for neighbor in module.neighbors)
            }
            obp_data_list.append(data)

    # Compute total interlink edges
    interlink_edges = sum(1 for _, _, data in regen_obp.graph.edges(data=True) if data['link_type'] == 'interlink')
    # Add the interlink edges data to obp_data_list
    obp_data_list.append({
        'OBP Module': 'Total Interlink Edges',
        'Neighbors': interlink_edges
    })

    # Get node connections
    node_connections = regen_obp.get_node_connections()
    obp_data_list.extend(node_connections)  # Append node connection data to obp_data_list



    # Convert the list of dictionaries to a pandas DataFrame
    df_obp = pd.DataFrame(obp_data_list)

    
    save_to_csv(df_obp, filename=os.path.join(result_dir, 'obp_topology.csv'))


       
        
   ##################################################################################################    

    interlink_edges = sum(1 for _, _, data in regen_obp.graph.edges(data=True) if data['link_type'] == 'interlink')
    print(f"Total interlink edges: {interlink_edges}")    
            
    ##################################################################################################    
    
    total_uplinks = regen_obp.get_total_uplinks()
    total_downlinks = regen_obp.get_total_downlinks()

    # print(f"Total number of uplinks: {total_uplinks}")
    # print(f"Total number of downlinks: {total_downlinks}")        
        
    
    ################################################################################################## 
     # Compute total number of OBP nodes
    obp_node_count = sum(1 for _, data in regen_obp.graph.nodes(data=True) if data.get('type_node') == 'obp_module')
    # print(f"Total OBP nodes: {obp_node_count}")


     ####################################################################################################  
     ####################################################################################################  
    num_commodities = scenario_config['optimization']['num_commodities']

    #demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities) #  number of flows
    
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities) #  number of flows

    


    # print("Demand matrix:")
    
    # print(demand_matrix)   
    
    
    ####################################################################################
    

    
    
############################################################################################


    # Create a dictionary to store results
    topology_data = {
        'Width': width,
        'Height': height,
        'Total OBP Nodes': obp_node_count,  # This line captures the result

        'Total Interlink Edges': interlink_edges,
        'Total Uplinks': total_uplinks,
        'Total Downlinks': total_downlinks,
    }

    # Convert the dictionary to a pandas DataFrame
    df_topology = pd.DataFrame([topology_data])


###############################################################################################



    # Call solve_mcfp method to solve the multi-commodity flow problem
    objective_type = scenario_config['optimization']['objective_func']  # Read from YAML config 



    
    save_to_csv(demand_matrix, filename=os.path.join(result_dir, 'demand_matrix.csv'))

    
    save_to_csv(df_topology, filename=os.path.join(result_dir, 'topology.csv'))




            
    if scenario_config['optimization']['optimization_model'] == 'multicommodity' : 
        # Check if precomputed demand matrix is provided (for path ratio preservation)
        if precomputed_demand_matrix is not None:
            print("Using precomputed demand matrix (path ratio preservation enabled)...")
            updated_demand_matrix_multicommodity = precomputed_demand_matrix
        else:
            # Run optimizer as usual
            mode = scenario_config['simulation']['failure_strategy']  # mode of failure strategy cold or warm
            optimizer = MultiCommodityOptimizer(scenario_config, regen_obp.graph, regen_obp.interlinks)
            updated_demand_matrix_multicommodity = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)

        save_to_csv(updated_demand_matrix_multicommodity, filename=os.path.join(result_dir, f"mcfp_results_flows_{num_commodities}_commodities.csv"))
        


      

    #########################################################################################################    
    
    
   
    if scenario_config['optimization']['optimization_model'] == 'multicommodity' : 
        # Call the run_simulation method on results of shortest path algorithm
        simulator_instance_mc = Simulator(regen_obp, scenario_config, result_dir, current_run, current_algo='multicommodity', demand_matrix=demand_matrix, updated_demand_matrix= updated_demand_matrix_multicommodity)
     

    total_flows_mc = demand_matrix['Arrival Rate'].sum()  # Assuming 'Flow' column has the flows for each entry


    
    
    if scenario_config['optimization']['optimization_model'] == 'multicommodity':
        
        # Check if multi-step simulation is enabled
        num_steps = scenario_config['simulation'].get('num_steps', 1)
        
        if num_steps > 1:
            # Run multi-step simulation
            all_flows, switches, blocked_flows, multi_step_stats = simulator_instance_mc.run_multi_step_simulation(
                updated_demand_matrix_multicommodity, demand_matrix, simulation_time, current_run
            )
            
            # Save multi-step statistics
            import json
            multi_step_stats_file = os.path.join(result_dir, 'multi_step_stats.json')
            with open(multi_step_stats_file, 'w') as f:
                # Convert to JSON-serializable format
                stats_json = {
                    'all_steps_stats': multi_step_stats['all_steps_stats'],
                    'overall_stats': multi_step_stats['overall_stats']
                }
                json.dump(stats_json, f, indent=2)
        else:
            # Run single-step simulation (default behavior)
            all_flows, switches, blocked_flows = simulator_instance_mc.run_simulation_with_rb(
                updated_demand_matrix_multicommodity, demand_matrix, simulation_time, current_run
            )
            multi_step_stats = None 


        
        #print_results("Optimization Model: Multicommodity", all_flows, len(all_flows)) #, failed_nodes_count)
        
        
                
        # Print information about blocked flows and save to file
        blocked_flows_dir = os.path.join(result_dir, 'blocked_flows')
        ensure_directory_exists(blocked_flows_dir)
        blocked_flows_file = os.path.join(blocked_flows_dir, 'blocked_flows.txt')
        with open(blocked_flows_file, 'a') as f:
            if blocked_flows:
                f.write(f"********************  Blocked flows for run {current_run}:  **************************\n")
                print("********************  Blocked flows:  **************************")
                for blocked_flow in blocked_flows:
                    flow_info = f"Flow ID {blocked_flow['id_flow']} from {blocked_flow['Source']} to {blocked_flow['Destination']} is blocked."
                    print(flow_info)
                    f.write(flow_info + '\n')
            else:
                f.write(f"No flows are blocked for run {current_run}.\n")
        
        
        

        return all_flows, switches, blocked_flows
        
    
        


##############################################################################################################
def main():
    
    """
    Main function to run all scenarios.
    
    This function deletes existing CSV files, loads scenario configurations,
    runs simulations for each scenario, and performs analysis and plotting of the results.
    """



    
    delete_csv_file()
    
    # results_base_dir = "results"
    # folder_path = "data"


    # Update the path to the results directory
    results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
    sns.set_theme(style="whitegrid")
    

    script_dir = os.path.dirname(os.path.abspath(__file__))  # Directory of main.py
    src_dir = os.path.join(script_dir, '..')  # src directory
    results_base_dir = os.path.join(src_dir, "results")
    folder_path = os.path.join(src_dir, "data")

    # Specify the path to the scenarios.yaml file
    scenarios_file_path = os.path.join(folder_path, 'scenarios.yaml')

    # Check if the file exists
    if not os.path.exists(scenarios_file_path):
        raise FileNotFoundError(f"No such file: {scenarios_file_path}")

    # Call the function to load and process all scenarios
    specific_files = get_scenario_filenames(folder_path)



    scenarios = []
            
    for filename in specific_files:
        full_path = os.path.join(folder_path, filename)
        if os.path.exists(full_path):
            scenario_config = load_yaml_file(full_path)
            num_runs = 5 # scenario_config['simulation']['num_runs']  # Now inside the loop
            scenarios.append((filename, scenario_config))
        else:
            print(f"File '{filename}' does not exist in '{folder_path}'.")
            
            
            

    #print(num_runs)   
     # Initialize a dictionary to store results for all scenarios
    all_results = {}
    all_results_priorities = {}
    

    
    # Iterate over each scenario
    for filename, scenario in scenarios:
        
        # Retrieve the time unit from the scenario configuration
        time_unit = scenario.get('system', {}).get('time_unit', 'ms')  # Default to milliseconds if not specified
        
        base_filename = os.path.splitext(filename)[0]
        scenario_results = {}
        # Retrieve the time unit from the scenario configuration
        time_unit = scenario.get('system', {}).get('time_unit', 'ms')  # Default to milliseconds if not specified
        
        # Run each scenario num_runs times
        for run in range(num_runs):

            
            # Set a unique seed for each run
            np.random.seed(run) #random.seed(run)  # or use any other method to generate a unique seed

            current_result_dir = os.path.join(results_base_dir, base_filename, f"run_{run+1}")
            ensure_directory_exists(current_result_dir)
            
            #######################################################################################
            

            
            ###############################################################
            
            print()

            print(f"Running simulation {run + 1} for scenario: {scenario.get('scenario_name', 'Unknown')} ...")
            
            # Run the simulation with the current scenario configuration


            #all_flows = run_simulation_scenario(scenario, current_result_dir,run) #, port_buffers)
            
            all_flows, switches, blocked_flows = run_simulation_scenario(scenario, current_result_dir, run)  # Include switches
            
            
            scenario_results[f"run_{run}"] = {
                "all_flows_results": all_flows,
                "switches": switches,  # Store switches information
                "blocked_flows": blocked_flows  # Store blocked flows information

            }
            
            # Print blocked flows
            if blocked_flows:
                print("********************  Blocked flows:  **************************")
                for blocked_flow in blocked_flows:
                    print(f"Flow ID {blocked_flow['id_flow']} from {blocked_flow['Source']} to {blocked_flow['Destination']} is blocked.")

            
        # Store results for the current scenario
        all_results[base_filename] = scenario_results


        ########## plot for each scenario 
        # plot_average_delay__capacity(all_results, time_unit=time_unit, results_dir=current_result_dir)
        
        # plot_network_PLI__capacity(all_results, time_unit=time_unit, results_dir=current_result_dir)

        # plot_average_delay__capacity_priority(all_results,time_unit=time_unit, plot_priority_our_model=True,plot_priority_capacity=False, plot_overall_our_model=False, plot_overall_capacity=True, results_dir=current_result_dir)
       
        # plot_average_PLI__capacity_priority(all_results,time_unit=time_unit, plot_priority_our_model=True,plot_priority_capacity=False, plot_overall_our_model=False, plot_overall_capacity=True, results_dir=current_result_dir)
            
        # print_summary_statistics(all_results, results_dir=current_result_dir)

        # print_summary_statistics_per_priority(all_results, results_dir=current_result_dir)
        
              

    # After all runs for a scenario, perform  aggregate analysis or plotting as required

    

    # # =============================================================================
    # #     ###  PLOTS OVER DIFFERENT SIMULATION 
    # # =============================================================================
    
    # Plotting the total number of packets sent across different simulation states.
    # After all runs for a scenario, perform aggregate analysis or plotting as required

    plot_total_packets_sent__(all_results)
    
    
    # # Plotting the total number of packets successfully received in the network for each simulation state.
    plot_total_packets_received__(all_results)
    

    # # Plotting the total number of packets that were dropped during transmission in each simulation state.
    plot_total_packets_dropped__(all_results)
    
    
    # # Plotting the average end-to-end delay experienced by packets in each simulation state.
    plot_average_delay__(all_results, time_unit=time_unit)
    
    
    # # Plotting the Network Packet Loss Indicator (PLI) for different simulation states.
    plot_network_PLI__(all_results)
    
    
    # # Plotting the Traffic Distribution Index (LDI) for each simulation state.
    # plot_LDI__(all_results)
    
    
    #  ###############################################################################################

    

    
    # plot_total_packets_sent_priority(all_results)
    
    # plot_total_packets_received_priority(all_results)
    
    # plot_total_packets_dropped_priority(all_results)
    
    # plot_average_delay_priority(all_results, time_unit=time_unit)
    
    # plot_network_PLI_priority(all_results)
    
    # plot_LDI_priority(all_results)
    
   #  ###################################################################################################


    # plots in case capacities we compare with 1*1 architecture 
    
    plot_average_delay__capacity(all_results, time_unit=time_unit, results_dir=results_dir)
    
    plot_network_PLI__capacity(all_results, time_unit=time_unit, results_dir=results_dir)
    
    ####################################################################################################
    
    
    # plots in case interlinks 
    
    # plot_average_delay__capacity_interlinks(all_results, time_unit=time_unit, results_dir=results_dir)

    
    # plot_network_PLI__capacity_interlinks(all_results,  time_unit=time_unit, results_dir=results_dir)

    
    
    
    ############################################################################################################

    
    plot_average_delay__capacity_priority(all_results,time_unit=time_unit, plot_priority_our_model=True,plot_priority_capacity=False, plot_overall_our_model=False, plot_overall_capacity=True, results_dir=results_dir)
    
    plot_average_PLI__capacity_priority(all_results,time_unit=time_unit, plot_priority_our_model=True,plot_priority_capacity=False, plot_overall_our_model=False, plot_overall_capacity=True, results_dir=results_dir)

    print()
   
   ####################################################################################################

    print("Simulation finished")
    print()
    
    print("***********  Statisctis *************************************")

    print()
    print_summary_statistics(all_results, results_dir=results_dir, time_unit=time_unit)
    
    print("***********  Statisctis per priority *************************************")

    
    print_summary_statistics_per_priority(all_results, results_dir=results_dir)

    print()
    
    
    # print(all_results)



######################################################################################################################
if __name__ == "__main__":
    main()
    #cProfile.run("main()")










