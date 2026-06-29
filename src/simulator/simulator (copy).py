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
            # Fixed interarrival time
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

        
        finish_time = 500 # float(self.scenario_config['simulation']['generation_finish_time']) # or  float("inf") for infinite generation 
        # Convert 'inf' string from YAML to float representation
        if self.scenario_config['simulation']['generation_finish_time'] == 'inf':
            finish = float('inf')
        else:
            finish = float(self.scenario_config['simulation']['generation_finish_time'])

        
        # Ensuring generation_finish_time is less than or equal to simulation_time
        if not (finish <= simulation_time or finish == float('inf')):
            raise ValueError("generation_finish_time cannot be greater than simulation_time. Please, reset in YAML :)")


         
        #initial_delay  =  float("inf")
        buffer_size = 1000 #convert_none((self.scenario_config['simulation']['buffer_size'])) # Buffer size     #  20000  # None # 20000 # None #100000 #None # 
        port_rate = self.scenario_config['system']['interlink_capacity']  # interlink_capacity 
        obp_rate = 1000000 #  self.scenario_config['simulation']['obp_capacity']
        limit_bytes = False #self.scenario_config['simulation']['limit_bytes']
        
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

                # Create a wire to connect the current switch to the neighbor switch
                wire = Wire(
                    env=self.env,
                    delay_dist=delay_dist,
                    src_coords=(x, y),
                    dst_coords=(nx, ny),
                    wire_id=f"Wire_{x}_{y}_to_{nx}_{ny}",
                    debug=False
                )

                wires[(x, y, nx, ny)] = wire  # Store the wire in the dictionary with its coordinates as the key





    
                
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
                            #switch.out =  switch.ports[port_number]
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
               
    
        # Run the simulation
        self.env.run(until=simulation_time)
    
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
