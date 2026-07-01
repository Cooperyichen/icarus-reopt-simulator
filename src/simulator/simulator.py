#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

    
    This module defines the Simulator class which orchestrates the simulation of a regenerative On-Board Processor (OBP) network.
    
    The core functionality includes initializing the simulation environment, managing node failures, rerouting traffic, 
    and running the simulation with different scheduling algorithms (FIFO, WFQ, Priority).
    
    Key functions include:
        - run_simulation_with_rb(self, updated_demand_matrix, demand_matrix, simulation_time)


    A class to simulate a regenerative OBP network.

    Parameters
    ----------
    regen_obp : RegenerativeOBP
        A reference to the regenerative On-Board Processor.
    scenario_config : dict
        Configuration dictionary for the simulation scenario.
    result_dir : str
        Directory to store simulation results.
    current_run : int
        Identifier for the current simulation run.
    current_algo : str
        The current algorithm used for the simulation.
    demand_matrix : pd.DataFrame
        The initial demand matrix.
    updated_demand_matrix : pd.DataFrame
        The demand matrix after routing

    Attributes
    ----------
    env : simpy.Environment
        The simulation environment.
    regen_obp : RegenerativeOBP
        Reference to the RegenerativeOBP object.
    current_algo : str
        The current algorithm used for the simulation.
    scenario_config : dict
        Configuration dictionary for the simulation scenario.
    result_dir : str
        Directory to store simulation results.
    current_run : int
        Identifier for the current simulation run.
    port_queues : dict
        Queues for ports.
    obp_ports : dict
        Ports for OBP modules.
    interlink_queues : dict
        Queues for interlinks.
    interlink_object : dict
        Objects representing interlinks.
    demand_matrix : pd.DataFrame
        The initial demand matrix.
    updated_demand_matrix : pd.DataFrame
        The demand matrix after updates.
    switches : dict
        Dictionary of switches in the topology.

    Methods
    -------

    get_arrival_distribution(lambda_arrival_rate)
        Determine the arrival distribution function based on the scenario configuration.
    get_packet_size_distribution()
        Determine the packet size distribution function based on the scenario configuration.
    run_simulation_with_rb(updated_demand_matrix, demand_matrix, simulation_time, current_run)
        Run the simulation with the specified demand matrices and simulation time.
    assign_unique_flow_ids(updated_demand_matrix)
        Assign unique flow IDs to the demand matrix.

"""

# @author:  zineb.garroussi@polymtl.ca



from utils.libs import *  # Importing all libraries centralized in the libs.py module
from topo.toroidal_topo import ToroidalTopo
from topo.utils import convert_none
from packet.packet import Packet # Import the Packet class
from topo.utils import save_to_csv
from topo.utils import generate_fib
from flow.flow import Flow
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from packet.dist_generator import PacketGenerator
from packet.sink import PacketSink
from modem.switch import SimplePacketSwitch
from modem.switch import FairPacketSwitch
from port.wire import Wire
from port.monitor import PortMonitor
from port.port import Port



################################################################################


class Simulator:
    
    
    

    def __init__(self, regen_obp, scenario_config,result_dir, current_run, current_algo, demand_matrix, updated_demand_matrix): 
        """
    Initialize the Simulator object.
    
    Parameters:
    - regen_obp: A reference to the regenerative On-Board Processor.
    
    Attributes:
    - regen_obp: Reference to the RegenerativeOBP object.
    - failed_nodes_count: Counter to keep track of the number of nodes that failed.
    - failed_nodes_list: A list to store nodes that have failed.
    - max_failed_nodes: The maximum number of nodes that are allowed to fail, fetched from the config.
    """
    
        #self.env = simpy.Environment()  # Create the SimPy environment here
        #self.env = simpy.rt.RealtimeEnvironment(factor=1,strict=False)
        self.env = simpy.rt.RealtimeEnvironment(initial_time=0, factor=0.0000001,strict=False)
        
        self.regen_obp = regen_obp
        self.current_algo = current_algo
        self.failed_nodes_count = 0  # Initialize the counter for failed nodes
        self.failed_nodes_list = []  # list of nodes that have failed
        self.scenario_config = scenario_config
        
        # Track restored packet IDs for debugging
        self.restored_packet_ids = []  # List of packet IDs that were restored
        
        # self.max_failed_nodes =  self.scenario_config['simulation']['max_failed_nodes'] #  maximum nodes you want to fail
        
        # self.failure_probability = self.scenario_config['simulation']['probability_failure']

        
        # max_failures = self.scenario_config['simulation']['max_failed_nodes']

        
        self.result_dir = result_dir
        self.current_run = current_run
        self.failure_log = []  # To store times when failures occur
        # self.obp_ports = {}  # Dictionary to hold the OBPport objects
        self.port_queues = {}  # Initialize here if needed
        self.obp_ports = {}  # Initialize the attribute here
        
        self.interlink_queues = {}
        self.interlink_object = {}
        
        self.demand_matrix = demand_matrix 
        self.updated_demand_matrix = updated_demand_matrix
        
        self.switches = {}


##################################################################################################################


#     def trigger_failures(self):
#         """
#         Randomly trigger failures based on the probability and the number of failures allowed.
        
#         This method iterates over all the switches in the simulator and triggers failures 
#         based on predefined periods specified in the scenario configuration. The failures 
#         are scheduled to occur at specific times within the simulation period as defined 
#         by the user.
        
#         Attributes:
#             num_failures (int): Counter for the number of failures triggered.
#         """
#         num_failures = 0  # Initialize the number of failures to 0
#         simulation_time = self.scenario_config['simulation']['simulation_time']
#         failure_specs = self.scenario_config['simulation'].get('failures', [])
    
#         for failure_spec in failure_specs:
#             if num_failures >= self.max_failed_nodes:
#                 break
    
#             failure_period = failure_spec['period']
            
#             if failure_period == 'beginning':
#                 failure_time = random.uniform(0, simulation_time / 3)
#             elif failure_period == 'middle':
#                 failure_time = random.uniform(simulation_time / 3, 2 * simulation_time / 3)
#             elif failure_period == 'end':
#                 failure_time = random.uniform(2 * simulation_time / 3, simulation_time)
#             else:
#                 continue  # Skip if the period is not recognized
            
#             # Randomly select a switch to fail
#             (x, y), switch = random.choice(list(self.switches.items()))
#             self.env.process(self.schedule_failure(switch, failure_time))  # Schedule the failure in the simulation environment
#             print(f"Failure scheduled for switch at ({x}, {y}) at time {failure_time} during {failure_period} period")  # Print the time of failure
#             num_failures += 1  # Increment the failure counter
    
#         # If the number of specified failures is less than the max, fill up with random failures
#         while num_failures < self.max_failed_nodes:
#             for (x, y), switch in self.switches.items():  # Iterate over each switch in the topology
#                 if random.random() < self.failure_probability:  # Check if a failure should be triggered based on the failure probability
#                     # Determine the time of failure randomly if no specific periods are left
#                     failure_time = random.uniform(0, simulation_time)
                    
#                     self.env.process(self.schedule_failure(switch, failure_time))  # Schedule the failure in the simulation environment
#                     print(f"Failure scheduled for switch at ({x}, {y}) at time {failure_time}")  # Print the time of failure
#                     num_failures += 1  # Increment the failure counter
#                     if num_failures >= self.max_failed_nodes:  # If the maximum number of failures is reached, exit the loop
#                         break

# ####################################################################################################################


#     def schedule_failure(self, switch, failure_time):
#         yield self.env.timeout(failure_time)
#         switch.fail()
#         self.failure_log.append(failure_time)  # Log the failure time
#         failure_strategy = self.scenario_config['simulation']['failure_strategy']
        
#         if failure_strategy == "fail-routing" :
#             # Call re-routing logic after failure
#             self.reroute_after_failure(switch)


# ######################################################################################################################


#     def reroute_after_failure(self, failed_switch):
#         """
#         Re-route the traffic considering the failed switch and backup nodes.
#         """
#         print(f"Re-routing traffic after failure of switch {failed_switch.element_id}")
    
    
#         # Step 1: Mark the Failed Node in the Graph
#         # Update the graph to mark the failed node
#         for node in self.regen_obp.graph.nodes:
#             if node == (failed_switch.x, failed_switch.y):
#                 self.regen_obp.graph.nodes[node]['failed'] = True
#                 print(f"Node {node} marked as failed.")
                
        
#         # Step 2: Identify Affected Paths in the Updated Demand Matrix
#         # Identify affected paths in the updated demand matrix
#         affected_paths = []
#         for idx, row in self.updated_demand_matrix.iterrows():
#             path = row['Path'].split(' -> ')
#             for segment in path:
#                 if segment == f"OBPModule({failed_switch.x}, {failed_switch.y})":
#                     affected_paths.append(path)
#                     break
        
#         print("Affected paths:")
#         for path in affected_paths:
#             print(" -> ".join(path))
            
            
#         # Step 3: Update the Demand Matrix
        
#         self.demand_matrix = self.update_demand_matrix_with_backup(failed_switch)

        
#         print("New demand matrix:")
#         print(self.demand_matrix)
        
        
#         # Step 4: Re-run the Optimization with the New Demand Matrix
#         self.updated_demand_matrix = self.rerun_optimization_with_updated_demand(self.demand_matrix)
        
#         print("New Updated demand matrix:")
#         print(self.updated_demand_matrix)
        
        
#         # Step 5: Update the Simulation with the New updated Demand Matrix and  new demand matrix
        
#         # Integrate the Updated Demand Matrix into the Simulation

#         # Stop the current simulation
        
#         # Update the simulation environment with the new paths from the updated demand matrix
        
#         # Resume the simulation.
        
#         # Step 5: Integrate the Updated Demand Matrix into the Simulation
        
#         self.update_simulation()

        

       
# ################################################################################################################
    
#     def update_demand_matrix_with_backup(self, failed_switch):
#         # Extract the coordinates of the failed switch
#         failed_coords = (failed_switch.x, failed_switch.y)
#         print(f"Failed coordinates: {failed_coords}")
        
#         # Loop through uplink and downlink nodes of the failed node used in the demand matrix and print them
#         uplink_nodes = []
#         downlink_nodes = []
        
#         for idx, row in self.demand_matrix.iterrows():
#             source = row['Source']
#             destination = row['Destination']
            
#             if f"OBPModule({failed_switch.x}, {failed_switch.y})" in source:
#                 uplink_nodes.append(source)
#             if f"OBPModule({failed_switch.x}, {failed_switch.y})" in destination:
#                 downlink_nodes.append(destination)
        
#         print("Uplink nodes of the failed node used in the demand matrix:")
#         for uplink in uplink_nodes:
#             print(uplink)
        
#         print("Downlink nodes of the failed node used in the demand matrix:")
#         for downlink in downlink_nodes:
#             print(downlink)
    
#         # Step to check for a backup node and create corresponding uplink and downlink nodes
#         backup_node = None
#         for node, data in self.regen_obp.graph.nodes(data=True):
#             if data.get('backup', False) and not data.get('failed', False):
#                 backup_node = node
#                 self.regen_obp.graph.nodes[node]['backup'] = False  # Mark backup as used
#                 print(f"Backup node found: {backup_node}")
#                 break
        

#         if backup_node:
#             print(f"Backup node found: {backup_node}")
            
#             # Extract x and y from backup_node string
#             parts = backup_node.strip("OBPModule()").split(", ")
#             backup_x, backup_y = int(parts[0]), int(parts[1])
#             print(f"Backup node coordinates: x={backup_x}, y={backup_y}")
#             self.regen_obp.graph.nodes[node]['backup'] = False  # Mark backup as used

                
#             new_uplink_nodes = []
#             new_downlink_nodes = []
            
#             # Create new uplink and downlink nodes for the backup node
#             for uplink in uplink_nodes:
#                 uplink_suffix = '_'.join(uplink.split('_')[-2:]) # uplink.split('_')[-1] 
                
#                 new_uplink = f"OBPModule({backup_x}, {backup_y})_{uplink_suffix}"
#                 new_uplink_nodes.append(new_uplink)
#                 # Add the new uplink node to the graph and connect it with the backup OBP module
#                 self.regen_obp.graph.add_node(new_uplink, type_node="uplink_node", x=backup_x, y=backup_y)
#                 self.regen_obp.graph.add_edge(new_uplink, backup_node, link_type="uplink")
                
                            
#             for downlink in downlink_nodes:
#                 downlink_suffix =  '_'.join(downlink.split('_')[-2:]) # downlink.split('_')[-1]  # Extract the downlink suffix (e.g., '_downlink_1')
#                 new_downlink = f"OBPModule({backup_x}, {backup_y})_{downlink_suffix}"
#                 new_downlink_nodes.append(new_downlink)
#                 # Add the new downlink node to the graph and connect it with the backup OBP module
#                 self.regen_obp.graph.add_node(new_downlink, type_node="downlink_node", x=backup_x, y=backup_y)
#                 self.regen_obp.graph.add_edge(backup_node, new_downlink, link_type="downlink")
                
                            
#             print("New uplink nodes created for the backup node:")
#             for uplink in new_uplink_nodes:
#                 print(uplink)
            
#             print("New downlink nodes created for the backup node:")
#             for downlink in new_downlink_nodes:
#                 print(downlink)     
                
#             # Update the demand matrix to replace failed nodes with backup nodes
#             for idx, row in self.demand_matrix.iterrows():
#                 if row['Source'] in uplink_nodes:
#                     new_source = new_uplink_nodes[uplink_nodes.index(row['Source'])]
#                     self.demand_matrix.loc[idx, 'Source'] = new_source
#                 if row['Destination'] in downlink_nodes:
#                     new_destination = new_downlink_nodes[downlink_nodes.index(row['Destination'])]
#                     self.demand_matrix.loc[idx, 'Destination'] = new_destination
                        
                    

#         print("New demand matrix:")
#         print(self.demand_matrix)
        
#         return self.demand_matrix
                

# ####################################################################################################################

    
#     def rerun_optimization_with_updated_demand(self, demand_matrix):
#         # Re-run the optimization with the updated demand matrix
#         objective_type = self.scenario_config['optimization']['objective_func']
#         mode = self.scenario_config['simulation']['failure_strategy']
    
#         optimizer = MultiCommodityOptimizer(self.scenario_config, self.regen_obp.graph, self.regen_obp.interlinks)
#         updated_demand_matrix = optimizer.solve_mcfp_path_formulation(
#             demand_matrix, objective_type, mode=mode
#         )
        
#         return updated_demand_matrix



# ########################################################################################################################


#     def update_simulation(self):
#         """
#         Update the simulation environment with the new paths from the updated demand matrix.
#         """
#         # Stop the current simulation
#         self.env = simpy.rt.RealtimeEnvironment(initial_time=self.env.now, factor=0.0000000000000001, strict=False)
        
#         # Reconfigure the simulation environment
#         self.configure_simulation_with_updated_demand(self.updated_demand_matrix)
        
#         # Resume the simulation
#         simulation_time = self.scenario_config['simulation']['simulation_time']
#         self.env.run(until=simulation_time)
#         print("Simulation resumed with updated demand matrix.")
        
        
########################################################################################################################
       
        

        
###################################################################################################################

    def get_arrival_distribution(self, lambda_arrival_rate):
        """
        Determine the arrival distribution function based on the scenario configuration.

        Parameters:
        - lambda_arrival_rate: The rate of arrival for the exponential distribution.

        Returns:
        - A function that generates interarrival times according to the specified distribution.
        """
        interarrival_type = self.scenario_config['simulation']['interarrival_time_generation']
        
        if interarrival_type == "exponential":
            # Exponential distribution
            return functools.partial(np.random.exponential, 1.00 / lambda_arrival_rate)
        
        elif interarrival_type == "fixed":
            # Fixed interarrival time - use the configured fixed value
            return lambda: self.scenario_config['simulation']['interarrival_time_value_if_generation_fixed']
        
        elif interarrival_type == "weibull":
            # Weibull distribution
            shape_weibull = self.scenario_config['simulation']['weibull_packet_generation']['shape_weibull']
            wscale = lambda_arrival_rate / math.gamma(1.0 + 1.0 / shape_weibull)
            return functools.partial(random.weibullvariate, wscale, shape_weibull)
        
        elif interarrival_type == "uniform":
            # Uniform distribution
            lower_bound = self.scenario_config['simulation']['uniform_packet_generation']['lower_bound']
            upper_bound = self.scenario_config['simulation']['uniform_packet_generation']['upper_bound']
            return functools.partial(random.uniform, lower_bound, upper_bound)
        
        else:
            raise ValueError("Invalid packet interarrival generation type")
            
###############################################################################################################################            
            
    def get_packet_size_distribution(self):
        """
        Determine the packet size distribution function based on the scenario configuration.

        Returns:
        - A function that generates packet sizes according to the specified distribution.
        """
        avg_packet_size = self.scenario_config['simulation']['avg_packet_size']
        packet_dist_type = self.scenario_config['simulation']['packet_distribution_generation']
        
        if packet_dist_type == "fixed":
            # Fixed packet size
            return lambda: avg_packet_size
        
        elif packet_dist_type == "exponential":
            # Exponential packet size distribution
            return functools.partial(random.expovariate, 1.00 / avg_packet_size)
        
        else:
            raise ValueError("Invalid packet size generation type")
            
            
##########################################################################################################################################
        
    def run_simulation_with_rb(self, updated_demand_matrix, demand_matrix, simulation_time,current_run): #,port_buffers): 
        
        """
        Run the simulation with the specified demand matrices and simulation time.
    
        This function orchestrates the simulation, including setting up packet generators,
        packet sinks, switches, and wires. It also triggers failures and handles re-routing 
        logic when necessary.
    
        Parameters
        ----------
        updated_demand_matrix : pd.DataFrame
            The updated demand matrix after applying optimization.
        demand_matrix : pd.DataFrame
            The initial demand matrix.
        simulation_time : float
            The total time for the simulation.
        current_run : int
            The identifier for the current simulation run.
    
        Returns
        -------
        all_flows : list
            List of all flow objects used in the simulation.
        switches : dict
            Dictionary of switch objects used in the simulation.
        blocked_flows : list
            List of blocked flows, if any.
        """        
        
        scenario_folder = self.scenario_config['scenario_name']
        
        #print()
        


        
        # Fetching algorithm from configuration
        fetchingAlgorithm = self.scenario_config['simulation']['fetchingAlgorithm']
        
        #infinite_capacity = self.scenario_config['obp_port']['infinite_capacity']  # for obp
        #infinite_capacity_interlink = self.scenario_config['interlink']['infinite_capacity'] # for interlink
        
        

        
        
        #limit_bytes =  self.scenario_config['simulation']['limit_bytes'] 

                
        print("Simulation begin (Simpy)")
        
        #print('demand_matrix')
        #print(demand_matrix)
        
        #print("updated_demand_matrix")
        #print(updated_demand_matrix)
        failure_probability =  self.scenario_config['simulation']['probability_failure']

        
        # Convert 'inf' string from YAML to float representation
        if self.scenario_config['simulation']['generation_finish_time'] == 'inf':
            finish = float('inf')
        else:
            finish = float(self.scenario_config['simulation']['generation_finish_time'])
        
        # Convert finish_time from ms to seconds (simpy uses seconds)
        # Check time_unit to determine if conversion is needed
        time_unit = self.scenario_config.get('system', {}).get('time_unit', 'ms')
        if time_unit == 'ms':
            finish_time = finish / 1000.0  # Convert ms to seconds
        else:
            finish_time = finish  # Already in seconds

        
        # Ensuring generation_finish_time is less than or equal to simulation_time
        if not (finish <= simulation_time or finish == float('inf')):
            raise ValueError("generation_finish_time cannot be greater than simulation_time. Please, reset in YAML :)")


         
        #initial_delay  =  float("inf")
        buffer_size = convert_none(self.scenario_config['simulation']['buffer_size'])  # Buffer size from config
        port_rate = self.scenario_config['system']['interlink_capacity']  # interlink_capacity 
        obp_rate = self.scenario_config['simulation']['obp_capacity']  # OBP capacity from config
        limit_bytes = self.scenario_config['simulation']['limit_bytes']  # Limit bytes flag from config
        
        # Assign unique flow IDs
        #self.assign_unique_flow_ids(updated_demand_matrix)
        
        # Assign unique flow IDs and get the mapping
        flow_id_mapping = self.assign_unique_flow_ids(updated_demand_matrix)



    
        # Separate feasible and blocked flows
        feasible_demand_matrix = updated_demand_matrix[updated_demand_matrix['Path'].notnull()]
        blocked_demand_matrix = updated_demand_matrix[updated_demand_matrix['Path'].isnull()]

    
        # Create flow ID mapping and all flows using only feasible flows
        flow_id_mapping = self.assign_unique_flow_ids(feasible_demand_matrix)
        all_flows = []
    
    


        blocked_flows = blocked_demand_matrix.to_dict('records') if not blocked_demand_matrix.empty else []


        
        all_flows = []
        nports = 4

        
        for idx, row in feasible_demand_matrix.iterrows(): # updated_demand_matrix.iterrows():
            path = row['Path'].split(' -> ')
            
            # Determine the arrival distribution for each flow
            lambda_arrival_rate = row['Arrival Rate']  # Adjust based on your actual data
            arrival_dist = self.get_arrival_distribution(lambda_arrival_rate)
            
            # Determine the packet size distribution for each flow
            size_dist = self.get_packet_size_distribution()
            
            flow = Flow(
                fid= int(row['unique_flow_id']), #row['id_flow'],
                src=row['Source'],
                dst=row['Destination'],
                size=row['Arrival Rate'],  # Assuming size is equivalent to arrival rate for simplicity
                start_time=0,  # Set the start time to 0 or another appropriate value
                arrival_dist= arrival_dist, #lambda: random.uniform(0.01, 0.02),  # Replace with actual arrival distribution function
                size_dist= size_dist, #lambda: 1,  # Replace with actual size distribution function
                path = path[1:-1],
                flow_value = row['Arrival Rate'],
                priority=row['Priority']
            )
            
            
            
                
            all_flows.append(flow)
            
            
            
        
        n_flows = len(all_flows)
        



        for flow in all_flows:
            


            pg = PacketGenerator(
                env=self.env,
                id=f"Flow_{flow.fid}",

                adist=flow.arrival_dist,
                sdist=flow.size_dist,
                finish=finish_time,
               # initial_delay = initial_delay,
                flow_id=flow.fid,
                original_flow_id=flow_id_mapping[flow.fid],  # Pass the original flow ID


                rec_flow=False,
                size=None,  # Maximum size of packets to send
                debug=False
            )
            
            

            
            # Create PacketSink for each flow
            ps = PacketSink(
                env=self.env,
                rec_arrivals=True,
                absolute_arrivals=True,
                rec_waits=True,
                rec_flow_ids=True,
                debug=False
            )        
            
            flow.pkt_gen = pg
            flow.pkt_sink = ps
            

        # Convert all_flows list to a dictionary for generate_fib
        #all_flows_dict = {flow.fid: flow for flow in all_flows}
        
        
        # Generate the FIB for the graph using the flows
        self.regen_obp.graph = generate_fib(self.regen_obp.graph, all_flows)
        
        #print("OKKKKK")






        #self.switches = {}
        if fetchingAlgorithm == 'fifo':
            # Create SimplePacketSwitch for each node in the topology

            for module in self.regen_obp.get_all_obp_modules():
                x, y = module.x, module.y  # Assuming modules have x and y attributes
                
                # Check if switch already exists (for multi-step simulation state restoration)
                if (x, y) in self.switches:
                    switch = self.switches[(x, y)]  # Reuse existing switch
                    # Update FIB (because flows may have changed)
                    node_name = f"OBPModule({x}, {y})"
                    if node_name in self.regen_obp.graph.nodes:
                        switch.demux.fib = self.regen_obp.graph.nodes[node_name]['flow_to_port']
                        #print(switch.demux.fib)
                    else:
                        print(f"Warning: Node {node_name} not found in the graph")
                else:
                    # Create new switch only if it doesn't exist
                    switch = SimplePacketSwitch(
                        env=self.env,
                        nports=nports,  # Adjust the number of ports as needed
                        port_rate=port_rate,  # Adjust the port rate as needed
                        obp_rate=obp_rate,
                        buffer_size=buffer_size,  # Adjust the buffer size as needed
                        element_id=f"Switch_{x}_{y}",
                        x=x,
                        y=y,
                        limit_bytes = limit_bytes,
                        debug=False
                    )

                    # Set demux.fib based on the FIB generated for the graph
                    node_name = f"OBPModule({x}, {y})"
                    if node_name in self.regen_obp.graph.nodes:
                        switch.demux.fib = self.regen_obp.graph.nodes[node_name]['flow_to_port']
                        #print(switch.demux.fib)
                    else:
                        print(f"Warning: Node {node_name} not found in the graph")

                    self.switches[(x, y)] = switch  # Store the switch in the dictionary with its coordinates

        elif fetchingAlgorithm == 'wfq':
            server_type = 'WFQ'
        elif fetchingAlgorithm == 'priority':
            server_type = 'PRIORITY'
        else:
            raise ValueError("Fetching algorithm not known. Please enter an adequate word in the configuration file.")

        if fetchingAlgorithm in ['wfq', 'priority']:
            # Parameters for FairPacketSwitch
            weights = {flow.fid: flow.priority for flow in all_flows}  # Set weights based on flow priority
            #print(weights)

            # Create FairPacketSwitch for each node in the topology
            for module in self.regen_obp.get_all_obp_modules():
                x, y = module.x, module.y  # Assuming modules have x and y attributes
                
                # Check if switch already exists (for multi-step simulation state restoration)
                if (x, y) in self.switches:
                    switch = self.switches[(x, y)]  # Reuse existing switch
                    # Update FIB (because flows may have changed)
                    # Note: weights may need updating, but FairPacketSwitch may not support dynamic updates
                    # If weights change, may need to recreate switch (currently assuming weights don't change)
                    node_name = f"OBPModule({x}, {y})"
                    if node_name in self.regen_obp.graph.nodes:
                        switch.demux.fib = self.regen_obp.graph.nodes[node_name]['flow_to_port']
                        #print(switch.demux.fib)
                    else:
                        print(f"Warning: Node {node_name} not found in the graph")
                else:
                    # Create new switch only if it doesn't exist
                    switch = FairPacketSwitch(
                        env=self.env,
                        nports=nports,  # Adjust the number of ports as needed
                        port_rate=port_rate,  # Adjust the port rate as needed
                        obp_rate = obp_rate,
                        buffer_size= buffer_size,  # Adjust the buffer size as needed
                        weights= weights,  # Provide the weights
                        server=server_type,  # Provide the server type
                        element_id=f"Switch_{x}_{y}",
                        x=x,
                        y=y,
                        limit_bytes = limit_bytes,
                        debug=False
                    )

                    # Set demux.fib based on the FIB generated for the graph
                    node_name = f"OBPModule({x}, {y})"
                    if node_name in self.regen_obp.graph.nodes:
                        switch.demux.fib = self.regen_obp.graph.nodes[node_name]['flow_to_port']
                        #print(switch.demux.fib)
                    else:
                        print(f"Warning: Node {node_name} not found in the graph")

                    self.switches[(x, y)] = switch  # Store the switch in the dictionary with its coordinates

        # Create wires to connect the switches based on the topology
        wires = {}
        delay_dist = lambda: 0  # Replace with actual delay distribution function 
        for module in self.regen_obp.get_all_obp_modules():
            x, y = module.x, module.y
            current_switch = self.switches[(x, y)]
            for neighbor in module.neighbors:
                nx, ny = neighbor.x, neighbor.y
                neighbor_switch = self.switches[(nx, ny)]

                # Check if wire already exists (for multi-step simulation state restoration)
                wire = None
                wire_key = (x, y, nx, ny)
                
                # Try to find existing wire by checking port.out connections
                if isinstance(current_switch, FairPacketSwitch):
                    ports = current_switch.egress_ports
                elif isinstance(current_switch, SimplePacketSwitch):
                    ports = current_switch.ports
                else:
                    ports = []
                
                for port in ports:
                    if isinstance(port.out, Wire):
                        if (port.out.src_coords == (x, y) and 
                            port.out.dst_coords == (nx, ny)):
                            wire = port.out  # Reuse existing wire
                            break
                
                if not wire:
                    # Create new wire only if it doesn't exist
                    wire = Wire(
                        env=self.env,
                        delay_dist=delay_dist,
                        src_coords=(x, y),
                        dst_coords=(nx, ny),
                        wire_id=f"Wire_{x}_{y}_to_{nx}_{ny}",
                        debug=False
                    )

                wires[wire_key] = wire  # Store the wire in the dictionary with its coordinates as the key





    
                
        #print("OKKKKK")


        #  snippet for setting up the ports
        for n in self.regen_obp.graph.nodes():
            node = self.regen_obp.graph.nodes[n]
            if "port_to_nexthop" in node:
                for port_number, next_hop in node["port_to_nexthop"].items():
                    if (node['x'], node['y']) in self.switches:
                        switch = self.switches[(node['x'], node['y'])]
                        next_hop_coords = eval(next_hop.replace('OBPModule', ''))
                        if next_hop_coords in self.switches:
                            # Find or use the corresponding wire
                            wire_key = (node['x'], node['y'], next_hop_coords[0], next_hop_coords[1])
                            if wire_key in wires:
                                wire = wires[wire_key]
                                switch.ports[port_number].out = wire
                                # Set wire.out to the next switch
                                wire.out = self.switches[next_hop_coords]
                            else:
                                # If wire doesn't exist, connect to switch (backward compatibility)
                                switch.ports[port_number].out = self.switches[next_hop_coords]
                            #print(f"Port {port_number} of switch ({node['x']}, {node['y']}) set to {next_hop_coords}")
   

           
    



        #print("OKKKKK")
        
        
        
        # # Loop over all flows and set up wiring
        # for flow in all_flows:
        #     # Set the output of the packet generator to the source switch
        #     src_coords = eval(flow.path[0].replace('OBPModule', ''))
        #     if src_coords in switches:
        #         print(src_coords)
        #         flow.pkt_gen.out = switches[src_coords]
        #         switches[src_coords].demux
                
        #         #switches[src_coords].ports[3] = flow.pkt_sink 
                
            
        #     # Set the output of the last switch in the path to the packet sink
        #     dst_coords = eval(flow.path[-1].replace('OBPModule', ''))
        #     if dst_coords in switches:
        #         print(dst_coords)
        #         last_hop_switch = switches[dst_coords]
        #         switches[dst_coords].demux.ends[flow.fid] = flow.pkt_sink
                


        #self.trigger_failures()  # Trigger failures after setting up switches and before running the simulation

        # # Loop over all flows and set up wiring
        # for flow in all_flows:
            
        #     # # If there's only one switch, connect the generator output directly to the sink
        #     # if len(self.switches) == 1:
        #     #     single_switch = list(self.switches.values())[0]
        #     #     flow.pkt_gen.out = single_switch
        #     #     single_switch.demux.ends[flow.fid] = flow.pkt_sink

            
        #     # Set the output of the packet generator to the source switch
        #     src_coords = eval(flow.path[0].replace('OBPModule', ''))
        #     if src_coords in self.switches:
        #         #print(src_coords)
        #         flow.pkt_gen.out = self.switches[src_coords]
        
        #     # Set the output of the last switch in the path to the packet sink
        #     dst_coords = eval(flow.path[-1].replace('OBPModule', ''))
        #     if dst_coords in self.switches:
        #         #print(dst_coords)
        #         last_hop_switch = self.switches[dst_coords]
        #         self.switches[dst_coords].demux.ends[flow.fid] = flow.pkt_sink
        
        
        
        
        #     # # If there's only one switch, connect the generator output directly to the sink
        #     # if len(self.switches) == 1:
        #     #     single_switch = list(self.switches.values())[0]
        #     #     flow.pkt_gen.out = single_switch.ports[0]
        #     #     single_switch.ports[0].out = flow.pkt_sink

                
                
        #         #single_switch.ports[0].out = flow.pkt_sink
                
        #         # single_switch = list(self.switches.values())[0]
        #         # flow.pkt_gen.out = single_switch.ports[1]
        #         # single_switch.ports[1].out = flow.pkt_sink
                
        #         # single_switch = list(self.switches.values())[0]
        #         # flow.pkt_gen.out = single_switch.ports[2]
        #         # single_switch.ports[2].out = flow.pkt_sink

        #         # single_switch = list(self.switches.values())[0]
        #         # flow.pkt_gen.out = single_switch.ports[3]
        #         # single_switch.ports[3].out = flow.pkt_sink




        # Assuming self.switches contains only one switch
        if len(self.switches) == 1:
            single_switch = list(self.switches.values())[0]
            for flow in all_flows:
                # # Directly connect the packet generator to the single switch
                flow.pkt_gen.out = single_switch
                
                #single_switch.demux.fib = {0: 0, 1: 0, 2:0, 3:0, 4:0,5:0, 6:0,7:0,8:0,9:0}
                
                
                #single_switch.ports[0].out =  flow.pkt_sink 
                
                #single_switch.out =  flow.pkt_sink 

                single_switch.demux.ends[flow.fid] = flow.pkt_sink
                

                

        else:
            # Existing wiring logic for multiple switches
            for flow in all_flows:
                # Set the output of the packet generator to the source switch
                src_coords = eval(flow.path[0].replace('OBPModule', ''))
                if src_coords in self.switches:
                    flow.pkt_gen.out = self.switches[src_coords]
        
                # Set the output of the last switch in the path to the packet sink
                dst_coords = eval(flow.path[-1].replace('OBPModule', ''))
                if dst_coords in self.switches:
                    last_hop_switch = self.switches[dst_coords]
                    self.switches[dst_coords].demux.ends[flow.fid] = flow.pkt_sink


        # print("OKKKKK")




               
        # Process the simulation results.
        # Indicating the type of simulation we're running.

        if  self.scenario_config['simulation']['interarrival_time_generation'] == "exponential" and  self.scenario_config['simulation']['packet_distribution_generation'] == "exponential" :
            
            print('A M/M/1 queueing simulation')
            
        elif  self.scenario_config['simulation']['interarrival_time_generation'] == "weibull" and self.scenario_config['simulation']['packet_distribution_generation'] == "exponential" :
            
            print('A Weibull/M/1 queueing simulation')
            
        elif  self.scenario_config['simulation']['interarrival_time_generation'] == "uniform" and self.scenario_config['simulation']['packet_distribution_generation'] == "exponential" :
            
            print('A Uniform/M/1 queueing simulation')  
            
        elif  self.scenario_config['simulation']['interarrival_time_generation'] == "exponential" and self.scenario_config['simulation']['packet_distribution_generation'] != "exponential" :
            
            print('A M/G/1 queueing simulation')  
            
        elif  self.scenario_config['simulation']['interarrival_time_generation'] != "exponential" and self.scenario_config['simulation']['packet_distribution_generation'] != "exponential" :
            
            print('A G/G/1 queueing simulation')  
               
    
        # Convert simulation_time from ms to seconds (simpy uses seconds)
        # Check time_unit to determine if conversion is needed
        time_unit = self.scenario_config.get('system', {}).get('time_unit', 'ms')
        if time_unit == 'ms':
            simulation_time_seconds = simulation_time / 1000.0  # Convert ms to seconds
        else:
            simulation_time_seconds = simulation_time  # Already in seconds
        
        # Run the simulation
        self.env.run(until=simulation_time_seconds)
    
        print("Simulation end (Simpy) for this scenario")




        
        # # Print the number of packets generated and received for each flow
        # for flow in all_flows:
        #     print(f"Flow ID {flow.fid} - Number of packets generated: {flow.pkt_gen.packets_sent}")
        #     print(f"Flow ID {flow.fid} - Number of packets received: {flow.pkt_sink.packets_received[flow.fid]}")
            
            



        #     print()






      #  print("----------------------------------------------------------------------------------")




        # # Initialize a counter for total dropped packets
        # total_dropped_packets = 0
        
        # # Aggregate dropped packets by flow
        # flow_dropped_packets = {flow.fid: 0 for flow in all_flows}
        
        # for (x, y), switch in self.switches.items():
        #     # Determine the correct attribute to use based on switch type
        #     if isinstance(switch, FairPacketSwitch):
        #         ports = switch.egress_ports
        #     elif isinstance(switch, SimplePacketSwitch):
        #         ports = switch.ports
        #     else:
        #         print(f"Unknown switch type for switch ({x}, {y})")
        #         continue
            
        #     for port in ports:
        #         if isinstance(port, Port):  # Ensure port is an instance of Port
        #             for flow_id, dropped_count in port.dropped_by_flow.items():
        #                 flow_dropped_packets[flow_id] += dropped_count
        #                 total_dropped_packets += dropped_count  # Accumulate the total dropped packets
        #                 # print(f"Switch ({x}, {y}) - Port {port.element_id} - Flow {flow_id} dropped {dropped_count} packets")
        
        # # Display results using the original flow IDs
        # for flow in all_flows:
        #     original_flow_id = flow_id_mapping[flow.fid]
        #     print(f"Original Flow ID {original_flow_id} (Unique Flow ID {flow.fid}) - Number of packets generated: {flow.pkt_gen.packets_sent}")
        #     print(f"Original Flow ID {original_flow_id} (Unique Flow ID {flow.fid}) - Number of packets received: {flow.pkt_sink.packets_received.get(flow.fid, 0)}")
        #     print(f"Original Flow ID {original_flow_id} (Unique Flow ID {flow.fid}) - Number of packets dropped: {flow_dropped_packets.get(flow.fid, 0)}")
        #     print()
        
        # # Display the total number of packets dropped
        # print(f"Total number of packets dropped across all flows: {total_dropped_packets}")

        # print()

        # # Display blocked flows statistics
        # if not blocked_demand_matrix.empty:
        #     print("Blocked flows by the optimizer:")
        #     for idx, row in blocked_demand_matrix.iterrows():
        #         print(f"Flow ID {row['id_flow']} from {row['Source']} to {row['Destination']} is blocked.")
        # else:
        #     print("No flows are blocked by the Optimizer.")
             
        # print()
            
        #self.plot_failures(simulation_time)

            
        return all_flows, self.switches, blocked_flows


####################################################################################################


    def assign_unique_flow_ids(self, updated_demand_matrix):
        
        """
        Assign unique flow IDs to the demand matrix and create a mapping of unique IDs to original IDs.
    
        Parameters
        ----------
        updated_demand_matrix : pd.DataFrame
            The demand matrix with updated flow information.
    
        Returns
        -------
        flow_id_mapping : dict
            A dictionary mapping unique flow IDs to original flow IDs.
        """       
            
        
        unique_id_counter = 0
        flow_id_mapping = {}
        for idx in updated_demand_matrix.index:
            original_flow_id = updated_demand_matrix.at[idx, 'id_flow']
            updated_demand_matrix.at[idx, 'unique_flow_id'] = unique_id_counter
            flow_id_mapping[unique_id_counter] = original_flow_id
            unique_id_counter += 1
        return flow_id_mapping
    

####################################################################################################

    
    # def plot_failures(self, simulation_time):
    #     """
    #     Plot the simulation horizon and mark the failure times with crosses.
        
    #     Parameters:
    #     - simulation_time: The total time for the simulation.
    #     """
    #     plt.figure(figsize=(10, 6))
    #     plt.plot([0, simulation_time], [1, 1], label='Simulation Horizon', color='blue')
    #     for failure_time in self.failure_log:
    #         plt.plot(failure_time, 1, 'rx')  # 'rx' means red cross
    #     plt.xlabel('Time')
    #     plt.ylabel('Simulation Horizon')
    #     plt.title('Simulation Horizon with Failure Times')
    #     plt.legend()
    #     plt.grid(True)
    #     plt.show()


####################################################################################################





    # def configure_simulation_with_updated_demand(self, updated_demand_matrix):
    #     """
    #     Reconfigure the simulation environment with the updated demand matrix.
    #     """
    #     # Clear the current switches and flows
    #     self.switches.clear()

    #     # Generate the FIB for the graph using the updated demand matrix
    #     all_flows = []
    #     flow_id_mapping = self.assign_unique_flow_ids(updated_demand_matrix)
    #     for idx, row in updated_demand_matrix.iterrows():
    #         path = row['Path'].split(' -> ')

    #         # Determine the arrival distribution for each flow
    #         lambda_arrival_rate = row['Arrival Rate']
    #         arrival_dist = self.get_arrival_distribution(lambda_arrival_rate)

    #         # Determine the packet size distribution for each flow
    #         size_dist = self.get_packet_size_distribution()

    #         flow = Flow(
    #             fid=int(row['unique_flow_id']),
    #             src=row['Source'],
    #             dst=row['Destination'],
    #             size=row['Arrival Rate'],
    #             start_time=0,
    #             arrival_dist=arrival_dist,
    #             size_dist=size_dist,
    #             path=path[1:-1],
    #             flow_value=row['Arrival Rate'],
    #             priority=row['Priority']
    #         )

    #         all_flows.append(flow)

    #     self.regen_obp.graph = generate_fib(self.regen_obp.graph, all_flows)

    #     # Re-create switches based on the updated demand matrix
    #     fetchingAlgorithm =  self.scenario_config['simulation']['fetchingAlgorithm']
    #     nports = 4
    #     port_rate = self.scenario_config['system']['interlink_capacity']
    #     obp_rate = self.scenario_config['simulation']['obp_capacity']
    #     buffer_size = convert_none((self.scenario_config['simulation']['buffer_size']))

    #     if fetchingAlgorithm == 'fifo':
    #         for module in self.regen_obp.get_all_obp_modules():
    #             x, y = module.x, module.y
    #             switch = SimplePacketSwitch(
    #                 env=self.env,
    #                 nports=nports,
    #                 port_rate=port_rate,
    #                 obp_rate=obp_rate,
    #                 buffer_size=buffer_size,
    #                 element_id=f"Switch_{x}_{y}",
    #                 x=x,
    #                 y=y,
    #                 debug=False
    #             )
    #             node_name = f"OBPModule({x}, {y})"
    #             if node_name in self.regen_obp.graph.nodes:
    #                 switch.demux.fib = self.regen_obp.graph.nodes[node_name]['flow_to_port']
    #             else:
    #                 print(f"Warning: Node {node_name} not found in the graph")

    #             self.switches[(x, y)] = switch

    #     elif fetchingAlgorithm in ['wfq', 'priority']:
    #         server_type = 'WFQ' if fetchingAlgorithm == 'wfq' else 'PRIORITY'
    #         weights = {flow.fid: flow.priority for flow in all_flows}

    #         for module in self.regen_obp.get_all_obp_modules():
    #             x, y = module.x, module.y
    #             switch = FairPacketSwitch(
    #                 env=self.env,
    #                 nports=nports,
    #                 port_rate=port_rate,
    #                 obp_rate=obp_rate,
    #                 buffer_size=buffer_size,
    #                 weights=weights,
    #                 server=server_type,
    #                 element_id=f"Switch_{x}_{y}",
    #                 x=x,
    #                 y=y,
    #                 debug=False
    #             )
    #             node_name = f"OBPModule({x}, {y})"
    #             if node_name in self.regen_obp.graph.nodes:
    #                 switch.demux.fib = self.regen_obp.graph.nodes[node_name]['flow_to_port']
    #             else:
    #                 print(f"Warning: Node {node_name} not found in the graph")

    #             self.switches[(x, y)] = switch

    #     # Create wires to connect the switches based on the topology
    #     wires = {}
    #     delay_dist = lambda: 0
    #     for module in self.regen_obp.get_all_obp_modules():
    #         x, y = module.x, module.y
    #         current_switch = self.switches[(x, y)]
    #         for neighbor in module.neighbors:
    #             nx, ny = neighbor.x, neighbor.y
    #             neighbor_switch = self.switches[(nx, ny)]

    #             wire = Wire(
    #                 env=self.env,
    #                 delay_dist=delay_dist,
    #                 src_coords=(x, y),
    #                 dst_coords=(nx, ny),
    #                 wire_id=f"Wire_{x}_{y}_to_{nx}_{ny}",
    #                 debug=False
    #             )

    #             wires[(x, y, nx, ny)] = wire

    #     for n in self.regen_obp.graph.nodes():
    #         node = self.regen_obp.graph.nodes[n]
    #         if "port_to_nexthop" in node:
    #             for port_number, next_hop in node["port_to_nexthop"].items():
    #                 if (node['x'], node['y']) in self.switches:
    #                     switch = self.switches[(node['x'], node['y'])]
    #                     next_hop_coords = eval(next_hop.replace('OBPModule', ''))
    #                     if next_hop_coords in self.switches:
    #                         switch.ports[port_number].out = self.switches[next_hop_coords]

    #     for flow in all_flows:
    #         src_coords = eval(flow.path[0].replace('OBPModule', ''))
    #         if src_coords in self.switches:
    #             flow.pkt_gen.out = self.switches[src_coords]

    #         dst_coords = eval(flow.path[-1].replace('OBPModule', ''))
    #         if dst_coords in self.switches:
    #             self.switches[dst_coords].demux.ends[flow.fid] = flow.pkt_sink

    #         if len(self.switches) == 1:
    #             single_switch = list(self.switches.values())[0]
    #             flow.pkt_gen.out = single_switch.ports[0]
    #             single_switch.ports[0].out = flow.pkt_sink

    #     print("Simulation reconfigured with updated demand matrix.")

####################################################################################################
# Multi-step Simulation: State Saving and Restoration Methods
####################################################################################################

    def iter_switch_ports(self, switch):
        """Return the output ports used by supported switch implementations."""
        if isinstance(switch, FairPacketSwitch):
            return switch.egress_ports
        if isinstance(switch, SimplePacketSwitch):
            return switch.ports
        return []

    def find_switch_port(self, switch, port_id):
        """Find a switch port by saved element ID, with index lookup for legacy state."""
        ports = self.iter_switch_ports(switch)
        for port in ports:
            if getattr(port, 'element_id', None) == port_id:
                return port

        if isinstance(port_id, int) and 0 <= port_id < len(ports):
            return ports[port_id]

        return None

    def save_packets_in_queues(self):
        """
        Save all packets currently in Port queues.
        
        Returns:
            dict: Dictionary mapping (switch_coords, port_id) to list of packet objects
        """
        import copy
        packets_in_queues = {}
        
        for (x, y), switch in self.switches.items():
            for port in self.iter_switch_ports(switch):
                if isinstance(port, Port):
                    # Get all packets in the queue
                    queue_packets = list(port.store.items)
                    if queue_packets:
                        key = ((x, y), port.element_id)
                        # Deep copy packets to avoid reference issues
                        packets_in_queues[key] = [copy.deepcopy(packet) for packet in queue_packets]
                        # Record metadata for each packet
                        for packet in packets_in_queues[key]:
                            packet._saved_queue_time = self.env.now
                            packet._saved_queue_location = key
        
        return packets_in_queues
    
    def save_packets_in_wires(self):
        """
        Save all packets currently in Wire stores (in transit).
        
        Returns:
            dict: Dictionary mapping wire_key to list of packet info dictionaries
        """
        import copy
        packets_in_wires = {}
        
        # Method: Find wires by traversing switches and their ports
        for (x, y), switch in self.switches.items():
            for port in self.iter_switch_ports(switch):
                if isinstance(port, Port) and hasattr(port, 'out'):
                    # Check if port.out is a Wire
                    if isinstance(port.out, Wire):
                        wire = port.out
                        wire_packets = list(wire.store.items)
                        if wire_packets:
                            wire_key = (wire.src_coords, wire.dst_coords)
                            packets_in_wires[wire_key] = []
                            
                            for packet in wire_packets:
                                # Calculate remaining delay time
                                queued_time = self.env.now - packet.current_time
                                delay = wire.delay_dist()
                                remaining_delay = max(0, delay - queued_time)
                                
                                # Deep copy packet
                                packet_copy = copy.deepcopy(packet)
                                
                                packets_in_wires[wire_key].append({
                                    'packet': packet_copy,
                                    'remaining_delay': remaining_delay,
                                    'wire_id': wire.wire_id,
                                    'src_coords': wire.src_coords,
                                    'dst_coords': wire.dst_coords
                                })
        
        return packets_in_wires
    
    def save_port_statistics(self):
        """
        Save port statistics (packets_received, packets_dropped) for each port.
        
        Returns:
            dict: Dictionary mapping (switch_coords, port_id) to statistics dict
        """
        port_statistics = {}
        
        for (x, y), switch in self.switches.items():
            for port in self.iter_switch_ports(switch):
                if isinstance(port, Port):
                    key = ((x, y), port.element_id)
                    port_statistics[key] = {
                        'packets_received': port.packets_received,
                        'packets_dropped': port.packets_dropped,
                        'dropped_by_flow': dict(port.dropped_by_flow) if hasattr(port, 'dropped_by_flow') else {}
                    }
        
        return port_statistics
    
    def save_simulation_state(self, step_id, all_flows):
        """
        Save the complete simulation state at the end of a time step.
        Also marks packets as Time Limit Drops and counts them.
        
        Args:
            step_id: The current step ID
            all_flows: List of all Flow objects
            
        Returns:
            dict: Complete simulation state including:
                - step_id: Current step ID
                - step_end_time: Simulation time at step end
                - packets_in_queues: Packets in Port queues
                - packets_in_wires: Packets in Wire stores
                - port_statistics: Port statistics
                - flow_statistics: Flow statistics (sent/received per flow)
                - time_limit_drops_count: Number of Time Limit Drops (for consistency)
        """
        # Collect packets in queues and wires
        packets_in_queues = self.save_packets_in_queues()
        packets_in_wires = self.save_packets_in_wires()
        port_statistics = self.save_port_statistics()
        
        # Mark packets as Time Limit Drops and count them
        queue_count = sum(len(packets) for packets in packets_in_queues.values())
        wire_count = sum(len(packet_info_list) for packet_info_list in packets_in_wires.values())
        time_limit_drops_count = queue_count + wire_count
        
        # Mark these packets as Time Limit Drops
        for packets in packets_in_queues.values():
            for packet in packets:
                packet._time_limit_drop_step = step_id
                if packet.status != "dropped":  # Only mark if not already dropped
                    packet.status = "time_limit_drop"
        
        for packet_info_list in packets_in_wires.values():
            for packet_info in packet_info_list:
                packet = packet_info['packet']
                packet._time_limit_drop_step = step_id
                if packet.status != "dropped":  # Only mark if not already dropped
                    packet.status = "time_limit_drop"
        
        # Collect flow statistics
        flow_statistics = {}
        for flow in all_flows:
            flow_statistics[flow.fid] = {
                'packets_sent': flow.pkt_gen.packets_sent if hasattr(flow.pkt_gen, 'packets_sent') else 0,
                'packets_received': flow.pkt_sink.packets_received.get(flow.fid, 0) if hasattr(flow.pkt_sink, 'packets_received') else 0
            }
        
        state = {
            'step_id': step_id,
            'step_end_time': self.env.now,
            'packets_in_queues': packets_in_queues,
            'packets_in_wires': packets_in_wires,
            'port_statistics': port_statistics,
            'flow_statistics': flow_statistics,
            'time_limit_drops_count': time_limit_drops_count
        }
        
        return state
    
    def restore_packets_in_queues(self, saved_queues, time_offset=0):
        """
        Restore packets from queues to the next time step.
        
        Args:
            saved_queues: Dictionary mapping (switch_coords, port_id) to list of packets
            time_offset: Time offset to add to packet timestamps (in seconds)
            
        Returns:
            list: List of restored packet IDs
        """
        restored_packet_ids = []
        
        for (switch_coords, port_id), packets in saved_queues.items():
            x, y = switch_coords
            switch = self.switches.get((x, y))
            if not switch:
                continue
            
            target_port = self.find_switch_port(switch, port_id)
            if target_port is None:
                continue
            
            if target_port:
                # Restore packets to the queue
                for packet in packets:
                    # Adjust timestamps (relative to new time step)
                    packet.timestamp += time_offset
                    # Update packet's current time
                    if hasattr(packet, '_saved_queue_time'):
                        packet.current_time = packet._saved_queue_time + time_offset
                    else:
                        packet.current_time = self.env.now
                    
                    # Ensure packet status is not "dropped" (it was in transit)
                    if packet.status == "dropped":
                        packet.status = "in_transit"
                    
                    # Mark as recovered from time limit if it was a time limit drop
                    if hasattr(packet, '_time_limit_drop_step') and packet._time_limit_drop_step is not None:
                        packet._recovered_from_time_limit = True
                    
                    # Put packet back into queue
                    target_port.store.put(packet)
                    restored_packet_ids.append(packet.id)
        
        return restored_packet_ids
    
    def restore_packets_in_wires(self, saved_wires, time_offset=0):
        """
        Restore packets from wires to the next time step.
        
        Args:
            saved_wires: Dictionary mapping wire_key to list of packet info dictionaries
            time_offset: Time offset to add to packet timestamps (in seconds)
            
        Returns:
            list: List of restored packet IDs
        """
        restored_packet_ids = []
        
        for wire_key, wire_packets_info in saved_wires.items():
            src_coords, dst_coords = wire_key
            
            # Find the corresponding wire by traversing switches and ports
            wire = None
            for (x, y), switch in self.switches.items():
                for port in self.iter_switch_ports(switch):
                    if isinstance(port, Port) and isinstance(port.out, Wire):
                        if (port.out.src_coords == src_coords and 
                            port.out.dst_coords == dst_coords):
                            wire = port.out
                            break
                
                if wire:
                    break
            
            if wire:
                for packet_info in wire_packets_info:
                    packet = packet_info['packet']
                    remaining_delay = packet_info.get('remaining_delay', 0)
                    
                    # Adjust timestamps
                    packet.timestamp += time_offset
                    # Reset current_time to new environment time
                    # This ensures Wire's delay calculation works correctly
                    packet.current_time = self.env.now
                    
                    # Reset status if it was dropped
                    if packet.status == "dropped":
                        packet.status = "in_transit"
                    
                    # Mark as recovered from time limit if it was a time limit drop
                    if hasattr(packet, '_time_limit_drop_step') and packet._time_limit_drop_step is not None:
                        packet._recovered_from_time_limit = True
                    
                    # Put packet back into wire
                    # Note: The remaining_delay will be handled by Wire's run() method
                    # which recalculates delay based on packet.current_time
                    wire.store.put(packet)
                    restored_packet_ids.append(packet.id)
            else:
                # Wire not found - this might happen if topology changed between steps
                # For now, we just skip these packets
                pass
        
        return restored_packet_ids
    
    def restore_simulation_state(self, previous_state, time_offset=0):
        """
        Restore the complete simulation state from a previous time step.
        
        Args:
            previous_state: State dictionary saved from previous step
            time_offset: Time offset to add to all timestamps (in seconds)
            
        Returns:
            dict: Restoration results including:
                - recovered_queue_packets: List of packet IDs recovered from queues
                - recovered_wire_packets: List of packet IDs recovered from wires
                - total_recovered: Total number of packets recovered
        """
        recovered_queue_packets = []
        recovered_wire_packets = []
        
        # Restore packets from queues
        if 'packets_in_queues' in previous_state:
            recovered_queue_packets = self.restore_packets_in_queues(
                previous_state['packets_in_queues'],
                time_offset
            )
        
        # Restore packets from wires
        if 'packets_in_wires' in previous_state:
            recovered_wire_packets = self.restore_packets_in_wires(
                previous_state['packets_in_wires'],
                time_offset
            )
        
        # Restore port statistics (optional - depends on whether we want cumulative stats)
        # For now, we don't restore port statistics as they should be reset for each step
        # or accumulated separately
        
        result = {
            'recovered_queue_packets': recovered_queue_packets,
            'recovered_wire_packets': recovered_wire_packets,
            'total_recovered': len(recovered_queue_packets) + len(recovered_wire_packets)
        }
        
        return result
    
    def count_time_limit_drops(self, step_id, all_flows):
        """
        Count Time Limit Drops for a specific step.
        Time Limit Drops = packets still in queues or wires at step end.
        
        Args:
            step_id: The step ID
            all_flows: List of all Flow objects
            
        Returns:
            int: Number of Time Limit Drops
        """
        # Count packets in queues
        packets_in_queues = self.save_packets_in_queues()
        queue_count = sum(len(packets) for packets in packets_in_queues.values())
        
        # Count packets in wires
        packets_in_wires = self.save_packets_in_wires()
        wire_count = sum(len(packet_info_list) for packet_info_list in packets_in_wires.values())
        
        total_time_limit_drops = queue_count + wire_count
        
        # Mark these packets as Time Limit Drops
        for packets in packets_in_queues.values():
            for packet in packets:
                packet._time_limit_drop_step = step_id
                if packet.status != "dropped":  # Only mark if not already dropped
                    packet.status = "time_limit_drop"
        
        for packet_info_list in packets_in_wires.values():
            for packet_info in packet_info_list:
                packet = packet_info['packet']
                packet._time_limit_drop_step = step_id
                if packet.status != "dropped":  # Only mark if not already dropped
                    packet.status = "time_limit_drop"
        
        return total_time_limit_drops
    
    def calculate_step_pli(self, step_id, all_flows, saved_state=None):
        """
        Calculate PLI for a single time step.
        Step PLI = (Buffer Overflow Drops + Time Limit Drops) / Step Sent
        
        Args:
            step_id: The step ID
            all_flows: List of all Flow objects
            saved_state: Optional saved state dict (if provided, uses its time_limit_drops_count)
            
        Returns:
            dict: Step statistics including:
                - step_id: Step ID
                - step_sent: Packets sent in this step
                - step_received: Packets received in this step
                - step_buffer_drops: Buffer overflow drops in this step
                - step_time_limit_drops: Time limit drops in this step
                - step_pli: PLI for this step (includes Time Limit Drops)
        """
        # Calculate step sent and received
        # Note: For now, we use total sent/received as step sent/received
        # In a full implementation, we would track per-step counters
        step_sent = sum(flow.pkt_gen.packets_sent for flow in all_flows 
                       if hasattr(flow.pkt_gen, 'packets_sent'))
        step_received = sum(flow.pkt_sink.packets_received.get(flow.fid, 0) 
                           for flow in all_flows 
                           if hasattr(flow.pkt_sink, 'packets_received'))
        
        # Calculate buffer overflow drops from ports
        step_buffer_drops = 0
        for (x, y), switch in self.switches.items():
            for port in self.iter_switch_ports(switch):
                if isinstance(port, Port):
                    step_buffer_drops += port.packets_dropped
        
        # Use Time Limit Drops count from saved_state if available (for consistency)
        # Otherwise, count packets still in queues or wires
        if saved_state is not None and 'time_limit_drops_count' in saved_state:
            # Use the count from saved_state (packets were already marked during save)
            step_time_limit_drops = saved_state['time_limit_drops_count']
        else:
            # Fallback: count packets still in queues or wires (for marking)
            # Note: This should only happen for the last step or if saved_state is not provided
            packets_in_transit = self.count_time_limit_drops(step_id, all_flows)
            step_time_limit_drops = packets_in_transit
        
        # Calculate step PLI (includes Time Limit Drops)
        step_total_lost = step_buffer_drops + step_time_limit_drops
        step_pli = (step_total_lost / step_sent * 100) if step_sent > 0 else 0
        
        return {
            'step_id': step_id,
            'step_sent': step_sent,
            'step_received': step_received,
            'step_buffer_drops': step_buffer_drops,
            'step_time_limit_drops': step_time_limit_drops,
            'step_pli': step_pli
        }
    
    def calculate_overall_pli(self, all_steps_stats, final_flows, final_switches):
        """
        Calculate overall PLI across all time steps.
        Overall PLI = Final truly lost packets / Total sent across all steps
        Only counts packets that were never recovered (not Time Limit Drops that were later recovered).
        
        Args:
            all_steps_stats: List of step statistics from all steps
            final_flows: Final flows at the end of all steps
            final_switches: Final switches at the end of all steps
            
        Returns:
            dict: Overall statistics including:
                - total_sent_all_steps: Total packets sent across all steps
                - total_received_final: Final packets received
                - total_final_lost: Final truly lost packets
                - total_buffer_drops: Total buffer overflow drops
                - total_time_limit_drops: Total Time Limit Drops across all steps
                - recovered_time_limit_count: Number of Time Limit Drops that were recovered
                - final_unrecovered_time_limit: Number of Time Limit Drops that were never recovered
                - overall_pli: Overall PLI (only counts final truly lost packets)
        """
        # Calculate total sent across all steps
        total_sent_all_steps = sum(stats['step_sent'] for stats in all_steps_stats)
        
        # Calculate final received
        total_received_final = sum(
            flow.pkt_sink.packets_received.get(flow.fid, 0)
            for flow in final_flows
            if hasattr(flow.pkt_sink, 'packets_received')
        )
        
        # Calculate final truly lost
        total_final_lost = total_sent_all_steps - total_received_final
        
        # Calculate total buffer drops across all steps
        total_buffer_drops = sum(stats['step_buffer_drops'] for stats in all_steps_stats)
        
        # Calculate total Time Limit Drops across all steps
        total_time_limit_drops = sum(stats['step_time_limit_drops'] for stats in all_steps_stats)
        
        # Count recovered Time Limit Drops
        # This is done by checking packets that were marked as recovered
        recovered_time_limit_count = 0
        for flow in final_flows:
            if hasattr(flow.pkt_sink, 'recovered_time_limit_packets'):
                recovered_time_limit_count += len(flow.pkt_sink.recovered_time_limit_packets)
        
        # Calculate final unrecovered Time Limit Drops
        final_unrecovered_time_limit = total_time_limit_drops - recovered_time_limit_count
        
        # Overall PLI = (Buffer Drops + Unrecovered Time Limit Drops) / Total Sent
        overall_pli = ((total_buffer_drops + final_unrecovered_time_limit) / total_sent_all_steps * 100) if total_sent_all_steps > 0 else 0
        
        return {
            'total_sent_all_steps': total_sent_all_steps,
            'total_received_final': total_received_final,
            'total_final_lost': total_final_lost,
            'total_buffer_drops': total_buffer_drops,
            'total_time_limit_drops': total_time_limit_drops,
            'recovered_time_limit_count': recovered_time_limit_count,
            'final_unrecovered_time_limit': final_unrecovered_time_limit,
            'overall_pli': overall_pli,
            'breakdown': {
                'buffer_overflow_loss': total_buffer_drops,
                'unrecovered_time_limit_loss': final_unrecovered_time_limit,
                'total_loss': total_buffer_drops + final_unrecovered_time_limit
            }
        }
    
    def run_multi_step_simulation(self, updated_demand_matrix, demand_matrix, simulation_time, current_run):
        """
        Run multi-step simulation with state saving and restoration between steps.
        
        Args:
            updated_demand_matrix: The updated demand matrix after optimization
            demand_matrix: The initial demand matrix
            simulation_time: Total simulation time (will be divided into steps)
            current_run: Current run ID
            
        Returns:
            tuple: (all_flows, switches, blocked_flows, multi_step_stats)
                - all_flows: Final flows after all steps
                - switches: Final switches after all steps
                - blocked_flows: Blocked flows
                - multi_step_stats: Statistics for all steps including overall PLI
        """
        # Read multi-step configuration
        num_steps = self.scenario_config['simulation'].get('num_steps', 1)
        step_duration = self.scenario_config['simulation'].get('step_duration', simulation_time)
        reoptimize_per_step = self.scenario_config['simulation'].get('reoptimize_per_step', False)
        preserve_path_ratios = self.scenario_config['simulation'].get('preserve_path_ratios', True)
        
        # Convert step_duration from ms to seconds if needed
        time_unit = self.scenario_config.get('system', {}).get('time_unit', 'ms')
        if time_unit == 'ms':
            step_duration_seconds = step_duration / 1000.0
        else:
            step_duration_seconds = step_duration
        
        # If num_steps is 1, run single-step simulation (default behavior)
        if num_steps == 1:
            all_flows, switches, blocked_flows = self.run_simulation_with_rb(
                updated_demand_matrix, demand_matrix, simulation_time, current_run
            )
            # Calculate single-step PLI
            step_stats = self.calculate_step_pli(step_id=1, all_flows=all_flows)
            overall_stats = self.calculate_overall_pli(
                all_steps_stats=[step_stats],
                final_flows=all_flows,
                final_switches=switches
            )
            multi_step_stats = {
                'all_steps_stats': [step_stats],
                'overall_stats': overall_stats
            }
            return all_flows, switches, blocked_flows, multi_step_stats
        
        # Multi-step simulation
        all_steps_stats = []
        all_steps_states = []
        current_demand_matrix = updated_demand_matrix.copy()
        previous_state = None
        
        for step_id in range(1, num_steps + 1):
            print(f"\n{'='*80}")
            print(f"Running Step {step_id}/{num_steps}")
            print(f"{'='*80}")
            
            # Re-optimize if needed
            if reoptimize_per_step and step_id > 1:
                print(f"Re-optimizing for step {step_id}...")
                from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
                objective_type = self.scenario_config['optimization']['objective_func']
                mode = self.scenario_config['simulation']['failure_strategy']
                optimizer = MultiCommodityOptimizer(self.scenario_config, self.regen_obp.graph, self.regen_obp.interlinks)
                current_demand_matrix = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
            elif step_id > 1 and preserve_path_ratios:
                # Reuse paths but maintain flow ratios
                # For now, we just reuse the same demand matrix
                # In a full implementation, we would adjust flow values while maintaining ratios
                print(f"Reusing paths for step {step_id} (maintaining flow ratios)...")
                # TODO: Implement path ratio preservation logic if needed
            
            # Create new SimPy environment for this step
            # Note: We need to create a new environment to reset time
            self.env = simpy.rt.RealtimeEnvironment(initial_time=0, factor=0.0000001, strict=False)
            
            # For steps after the first, we need to restore state before running simulation
            # But we need switches and wires to exist first
            # Solution: Run a minimal simulation (0.001s) to create infrastructure, then restore, then run full simulation
            if previous_state is not None and step_id > 1:
                # First, create switches and wires by running a minimal simulation
                # We'll use a very short time (0.001s) just to create the infrastructure
                minimal_time = 0.001  # 1ms in seconds
                print(f"Preparing infrastructure for step {step_id}...")
                # Temporarily adjust generation_finish_time to match minimal_time
                original_finish_time = self.scenario_config['simulation'].get('generation_finish_time')
                self.scenario_config['simulation']['generation_finish_time'] = minimal_time
                try:
                    temp_flows, temp_switches, temp_blocked = self.run_simulation_with_rb(
                        current_demand_matrix, demand_matrix, minimal_time, current_run
                    )
                finally:
                    # Restore original finish_time
                    if original_finish_time is not None:
                        self.scenario_config['simulation']['generation_finish_time'] = original_finish_time
                
                # Now restore state
                time_offset = step_duration_seconds * (step_id - 1)
                print(f"Restoring state from step {step_id - 1}...")
                # Debug: Print what we're trying to restore
                saved_queue_count = sum(len(packets) for packets in previous_state.get('packets_in_queues', {}).values())
                saved_wire_count = sum(len(packet_info_list) for packet_info_list in previous_state.get('packets_in_wires', {}).values())
                print(f"  Attempting to restore: {saved_queue_count} from queues, {saved_wire_count} from wires")
                restore_result = self.restore_simulation_state(previous_state, time_offset=time_offset)
                print(f"Restored {restore_result['total_recovered']} packets ({len(restore_result['recovered_queue_packets'])} from queues, {len(restore_result['recovered_wire_packets'])} from wires)")
                
                # Track restored packet IDs for debugging
                self.restored_packet_ids = restore_result['recovered_queue_packets'] + restore_result['recovered_wire_packets']
                print(f"  Tracked restored packet IDs: {self.restored_packet_ids[:10]}..." if len(self.restored_packet_ids) > 10 else f"  Tracked restored packet IDs: {self.restored_packet_ids}")
                
                # Now run the full simulation for this step
                # Note: We need to reset flows and re-create them for the full simulation
                # Actually, we should re-run the full simulation, but the infrastructure is already created
                # For now, we'll run the full simulation which will re-create flows but reuse switches/wires
                # For Step 2+, use longer duration to allow recovered packets to reach sink
                # Step 2 should have enough time for recovered packets to be processed
                step2_duration = step_duration * 20  # Give Step 2 20x more time for recovery (400ms for step_duration=20ms)
                if time_unit == 'ms':
                    step2_duration_seconds = step2_duration / 1000.0
                else:
                    step2_duration_seconds = step2_duration
                
                # Ensure generation_finish_time is not greater than step_duration (considering time_unit)
                time_unit = self.scenario_config.get('system', {}).get('time_unit', 'ms')
                generation_finish_time = self.scenario_config['simulation'].get('generation_finish_time', float('inf'))
                # For Step 2+, stop generating new packets early to focus on recovery
                if step_id > 1:
                    # Stop generation early in Step 2 to allow recovered packets to be processed
                    # Use a very small value to minimize new packet generation
                    self.scenario_config['simulation']['generation_finish_time'] = 0.001  # 1ms in ms unit (very short)
                elif generation_finish_time > step_duration:
                    self.scenario_config['simulation']['generation_finish_time'] = step_duration
                # Debug: Check demux.ends before running Step 2
                if step_id == 2:
                    print(f"\n[DEBUG] Before Step 2 simulation - Checking demux.ends connections:")
                    for (x, y), switch in self.switches.items():
                        if hasattr(switch, 'demux') and hasattr(switch.demux, 'ends'):
                            if len(switch.demux.ends) > 0:
                                print(f"  Switch ({x}, {y}) demux.ends: {list(switch.demux.ends.keys())}")
                            else:
                                print(f"  Switch ({x}, {y}) demux.ends: EMPTY (no connections!)")
                
                all_flows, switches, blocked_flows = self.run_simulation_with_rb(
                    current_demand_matrix, demand_matrix, step2_duration, current_run
                )
                
                # Debug: Check demux.ends after running Step 2
                if step_id == 2:
                    print(f"\n[DEBUG] After Step 2 simulation - Checking demux.ends connections:")
                    for (x, y), switch in self.switches.items():
                        if hasattr(switch, 'demux') and hasattr(switch.demux, 'ends'):
                            if len(switch.demux.ends) > 0:
                                print(f"  Switch ({x}, {y}) demux.ends: {list(switch.demux.ends.keys())}")
                            else:
                                print(f"  Switch ({x}, {y}) demux.ends: EMPTY (no connections!)")
            else:
                # First step: just run simulation normally
                # Ensure generation_finish_time is not greater than step_duration
                time_unit = self.scenario_config.get('system', {}).get('time_unit', 'ms')
                generation_finish_time = self.scenario_config['simulation'].get('generation_finish_time', float('inf'))
                if generation_finish_time > step_duration:
                    self.scenario_config['simulation']['generation_finish_time'] = step_duration
                all_flows, switches, blocked_flows = self.run_simulation_with_rb(
                    current_demand_matrix, demand_matrix, step_duration, current_run
                )
            
            # Save state BEFORE calculating PLI to ensure packets are still in queues/wires
            # This ensures that Time Limit Drops count matches the saved packets
            previous_state = None
            if step_id < num_steps:
                previous_state = self.save_simulation_state(step_id=step_id, all_flows=all_flows)
                all_steps_states.append(previous_state)
                # Debug: Print saved packet counts
                queue_count = sum(len(packets) for packets in previous_state.get('packets_in_queues', {}).values())
                wire_count = sum(len(packet_info_list) for packet_info_list in previous_state.get('packets_in_wires', {}).values())
                print(f"State saved for step {step_id} (Queues: {queue_count} packets, Wires: {wire_count} packets)")
            
            # Calculate step PLI (after saving state to ensure consistency)
            # Pass saved_state to use the actual Time Limit Drops count
            step_stats = self.calculate_step_pli(step_id=step_id, all_flows=all_flows, saved_state=previous_state)
            all_steps_stats.append(step_stats)
            
            print(f"\nStep {step_id} Statistics:")
            print(f"  Sent: {step_stats['step_sent']}")
            print(f"  Received: {step_stats['step_received']}")
            print(f"  Buffer Drops: {step_stats['step_buffer_drops']}")
            print(f"  Time Limit Drops: {step_stats['step_time_limit_drops']}")
            print(f"  Step PLI: {step_stats['step_pli']:.2f}%")
            
            # Debug: Check location of restored packets at end of Step 2
            if step_id == 2 and hasattr(self, 'restored_packet_ids') and len(self.restored_packet_ids) > 0:
                print(f"\n{'='*80}")
                print("Recovered Packets Location Check (Step 2 End)")
                print(f"{'='*80}")
                
                # Get restored packet IDs
                restored_packet_ids = self.restored_packet_ids
                
                # Check packets in queues
                current_queues = self.save_packets_in_queues()
                current_queue_ids = []
                queue_locations = {}  # Map packet_id -> (switch_coords, port_id)
                for (switch_coords, port_id), packets in current_queues.items():
                    for p in packets:
                        current_queue_ids.append(p.id)
                        if p.id in restored_packet_ids:
                            queue_locations[p.id] = (switch_coords, port_id, p.flow_id)
                
                # Check packets in wires
                current_wires = self.save_packets_in_wires()
                current_wire_ids = []
                for packet_info_list in current_wires.values():
                    current_wire_ids.extend([p['packet'].id for p in packet_info_list])
                
                # Check packets in sink (recovered_time_limit_packets)
                sink_recovered_ids = []
                for flow in all_flows:
                    if hasattr(flow.pkt_sink, 'recovered_time_limit_packets'):
                        sink_recovered_ids.extend(flow.pkt_sink.recovered_time_limit_packets)
                
                # Analyze results
                still_in_queues = [pid for pid in restored_packet_ids if pid in current_queue_ids]
                still_in_wires = [pid for pid in restored_packet_ids if pid in current_wire_ids]
                in_sink = [pid for pid in restored_packet_ids if pid in sink_recovered_ids]
                missing = [pid for pid in restored_packet_ids 
                          if pid not in current_queue_ids and pid not in current_wire_ids and pid not in sink_recovered_ids]
                
                print(f"  Total Restored Packet IDs: {len(restored_packet_ids)}")
                print(f"  Still in Queues: {len(still_in_queues)}")
                if len(still_in_queues) > 0:
                    print(f"    Queue Packet IDs: {still_in_queues[:10]}..." if len(still_in_queues) > 10 else f"    Queue Packet IDs: {still_in_queues}")
                    # Print queue locations
                    print(f"    Queue Locations:")
                    for pid in still_in_queues[:5]:  # Show first 5
                        if pid in queue_locations:
                            switch_coords, port_id, flow_id = queue_locations[pid]
                            print(f"      Packet {pid} (flow {flow_id}): Switch {switch_coords}, Port {port_id}")
                            # Check if this port is connected
                            if switch_coords in self.switches:
                                switch = self.switches[switch_coords]
                                port = self.find_switch_port(switch, port_id)
                                if port is not None and hasattr(port, 'out'):
                                    if port.out is None:
                                        print(f"        WARNING: Port {port_id} has no output connection!")
                                    elif isinstance(port.out, Wire):
                                        print(f"        Port {port_id} -> Wire -> {port.out.dst_coords}")
                                    else:
                                        print(f"        Port {port_id} -> {type(port.out).__name__}")
                print(f"  Still in Wires: {len(still_in_wires)}")
                if len(still_in_wires) > 0:
                    print(f"    Wire Packet IDs: {still_in_wires[:10]}..." if len(still_in_wires) > 10 else f"    Wire Packet IDs: {still_in_wires}")
                print(f"  In Sink (Recovered): {len(in_sink)}")
                if len(in_sink) > 0:
                    print(f"    Sink Packet IDs: {in_sink[:10]}..." if len(in_sink) > 10 else f"    Sink Packet IDs: {in_sink}")
                print(f"  Missing (Not Found): {len(missing)}")
                if len(missing) > 0:
                    print(f"    Missing Packet IDs: {missing[:10]}..." if len(missing) > 10 else f"    Missing Packet IDs: {missing}")
                
                # Summary
                total_accounted = len(still_in_queues) + len(still_in_wires) + len(in_sink)
                print(f"\n  Summary:")
                print(f"    Accounted for: {total_accounted}/{len(restored_packet_ids)}")
                print(f"    Unaccounted: {len(restored_packet_ids) - total_accounted}")
        
        # Calculate overall PLI
        print(f"\n{'='*80}")
        print("Calculating Overall Statistics")
        print(f"{'='*80}")
        overall_stats = self.calculate_overall_pli(
            all_steps_stats=all_steps_stats,
            final_flows=all_flows,
            final_switches=switches
        )
        
        print(f"\nOverall Statistics:")
        print(f"  Total Sent (All Steps): {overall_stats['total_sent_all_steps']}")
        print(f"  Total Received (Final): {overall_stats['total_received_final']}")
        print(f"  Total Final Lost: {overall_stats['total_final_lost']}")
        print(f"  Total Buffer Drops: {overall_stats['total_buffer_drops']}")
        print(f"  Total Time Limit Drops: {overall_stats['total_time_limit_drops']}")
        print(f"  Recovered Time Limit Drops: {overall_stats['recovered_time_limit_count']}")
        print(f"  Final Unrecovered Time Limit: {overall_stats['final_unrecovered_time_limit']}")
        print(f"  Overall PLI: {overall_stats['overall_pli']:.2f}%")
        
        multi_step_stats = {
            'all_steps_stats': all_steps_stats,
            'overall_stats': overall_stats,
            'all_steps_states': all_steps_states
        }
        
        return all_flows, switches, blocked_flows, multi_step_stats
