#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

This code defines a class called `ToroidalTopo` that represents a regenerative OBP system. 
The class encapsulates the functionality to create the OBP topology, generate the OBP graph, and perform various operations on the graph such as counting nodes and extracting uplink 
and downlink nodes. The class uses the NetworkX library for graph operations and the matplotlib library for graph visualization.

Attributes:
    width (int): Width of the OBP topology.
    height (int): Height of the OBP topology.
    scenario_config (dict): Configuration dictionary for the scenario.
    obp_topology (list): A list of lists representing the OBP topology.
    modules (list): A list of all OBP modules in the topology.
    graph (networkx.DiGraph): The OBP graph.
    interlinks (list): A list to store Interlink objects.

Methods:
    generate_demand_matrix(num_commodities): Generate a demand matrix for the OBP network based on the scenario configuration. This function generates a demand matrix consisting of source-destination pairs, their respective arrival rates, and priorities. It supports both random and fixed demand generation modes.
"""


# @author: zineb.garroussi@polymtl.ca


from utils.libs import *  # Importing all libraries centralized in the libs.py module
#from config_loader import config_values
from modem.obp_module import OBPModule
from port.interlink import Interlink



class ToroidalTopo:

    def __init__(self, scenario_config, width, height):
        """
        Initialize the RegenerativeOBP class.

        Args:
            width (int): Width of the OBP topology.
            height (int): Height of the OBP topology.
            min_throughput (float): Minimum allowed throughput value.
            max_throughput (float): Maximum allowed throughput value.
        """
        self.width = width
        self.height = height
        self.scenario_config = scenario_config
        # self.downlink_number = downlink_number
        # self.uplink_number = uplink_number
        # self.arrival_rate = arrival_rate
        #dim = [width,height]
        self.obp_topology = self.create_toroidal_topology()  # Creating the OBP topology
        self.modules = [module for row in self.obp_topology for module in row]  # Collecting all OBP modules
        #self.graph = self.create_obp_graph()  # Creating the OBP graph
        self.graph, _, _ = self.create_toroidal_grid()
        
        # Retrieve and process interlink details
        interlink_details = self.get_interlinks()
        # You can now print, store, or process these interlink details further
        #print('Interlink Details:', interlink_details)








    def create_toroidal_topology(self):
        """
        Create the toroidal topology for OBP modules and Interlinks between them.

        Returns:
            list: A list of lists representing the OBP topology.
        """
        obp_modules = [[OBPModule(x, y) for y in range(self.height)] for x in range(self.width)]
        self.interlinks = []  # Initialize a list to store Interlink objects

        bandwidth = self.scenario_config['system']['interlink_capacity']  # interlink_capacity  # Example bandwidth value

        for x in range(self.width):
            for y in range(self.height):
                current_module = obp_modules[x][y]

                # Define neighbors (right, bottom, left, top)
                neighbors = [
                    obp_modules[(x + 1) % self.width][y],    # Right neighbor
                    obp_modules[x][(y + 1) % self.height],   # Bottom neighbor
                    obp_modules[(x - 1) % self.width][y],    # Left neighbor
                    obp_modules[x][(y - 1) % self.height]    # Top neighbor
                ]

                # Create Interlinks for each neighbor
                for neighbor in neighbors:
                    if neighbor != current_module:
                        current_module.add_neighbor(neighbor)
                        interlink = Interlink(current_module, neighbor, bandwidth)
                        self.interlinks.append(interlink)

        return obp_modules



    
        
    def custom_layout(self, G):
        """
        Create a custom layout for positioning nodes in the graph visualization.
    
        Args:
            G (networkx.Graph): The graph to be visualized.
    
        Returns:
            dict: A dictionary mapping nodes to their positions.
        """
        position = nx.spring_layout(G, scale=1000)  # Initial layout for all nodes
    
        spacing_x = 1.0 / self.width
        spacing_y = 1.0 / self.height
    
        # Toroidal placement for OBP nodes
        for node, data in G.nodes(data=True):
            if data["type_node"] == "obp_module":
                x, y = data['x'], data['y']
                position[node] = (x * spacing_x+2.00, y * spacing_y+2.00)
        
        offset_factor = 0.1
    
        # Adjust the y-coordinate position for uplink and downlink nodes
        for node, data in G.nodes(data=True):
            if data["type_node"] == "uplink_node":
                index = int(node.split("_")[-1])  # Extract the node index
                position[node][1] += 1.5 + index * offset_factor  # Offset each node by a factor of its index
            elif data["type_node"] == "downlink_node":
                index = int(node.split("_")[-1])
                position[node][1] -= 1.5 + index * offset_factor
    
        # Use the initial positions as a starting point for kamada_kawai_layout
        position = nx.kamada_kawai_layout(G, pos=position, scale=1000)
    
        return position
        
        



    def get_all_obp_modules(self):
        """
        Get a list of all OBPModule instances within the RegenerativeOBP topology.

        Returns:
            list: A list of OBPModule instances.
        """
        return self.modules    
    

    



    def create_obp_graph(self):
        """
        Create the OBP graph with Interlink objects.

        Returns:
            networkx.DiGraph: The OBP graph.
        """
        G = nx.DiGraph()

        # Initialize OBP nodes and set up backup nodes, uplinks, and downlinks
        for y, row in enumerate(self.obp_topology):
            for x, module in enumerate(row):
                module_name = f"OBPModule({module.x}, {module.y})"

                # Determine if the module is a backup based on scenario configuration
                is_backup = (module.x, module.y) in [eval(item) for item in self.scenario_config['simulation']['backup']]

                # Add OBP module node to the graph
                G.add_node(module_name, type_node="obp_module", x=x, y=y, failed=False, backup=is_backup)

                # Add uplink and downlink nodes if not a backup module
                if not is_backup:
                    for i in range(self.scenario_config['system']['uplink_number']):
                        uplink_node = f"{module_name}_uplink_{i}"
                        G.add_node(uplink_node, type_node="uplink_node", x=x, y=y)
                        G.add_edge(uplink_node, module_name, link_type="uplink")

                    for i in range(self.scenario_config['system']['downlink_number']):
                        downlink_node = f"{module_name}_downlink_{i}"
                        G.add_node(downlink_node, type_node="downlink_node", x=x, y=y)
                        G.add_edge(module_name, downlink_node, link_type="downlink")

        # Adding edges between OBP modules using Interlink objects
        for interlink in self.interlinks:
            module1_name = f"OBPModule({interlink.module1.x}, {interlink.module1.y})"
            module2_name = f"OBPModule({interlink.module2.x}, {interlink.module2.y})"
            module1_name = module1
            module2_name = module2

            # Add edges to the graph with Interlink references and attributes
            G.add_edge(module1_name, module2_name, interlink=interlink, capacity=interlink.bandwidth, link_type="interlink")
            G.add_edge(module2_name, module1_name, interlink=interlink, capacity=interlink.bandwidth, link_type="interlink")

        return G



    

    def visualize_obp(self):
        """
        Visualize the OBP graph.
        """
        pos = self.custom_layout(self.graph)

        # Modified edge label generation to handle missing 'weight' attribute
        edge_labels = {}
        for u, v, d in self.graph.edges(data=True):
            if d.get('link_type') == 'interlink':
                weight = d.get('weight', '1')  # Provide a default value if 'weight' is not present
                edge_labels[(u, v)] = f"w={weight}"

        plt.figure(figsize=(20, 20))
        node_colors = ["skyblue" if data["type_node"] == "obp_module" else
                        "green" if data["type_node"] == "uplink_node" else
                        "orange" for _, data in self.graph.nodes(data=True)]

        #nx.draw_networkx(self.graph, pos, node_size=5000, node_color=node_colors, with_labels=False, font_size=35, arrows=True)
        nx.draw_networkx(self.graph, pos, node_size=8000, node_color=node_colors, with_labels=False, font_size=60, arrows=True, arrowsize=25)


        # Adding labels for the nodes
        node_labels = {}
        for node, data in self.graph.nodes(data=True):
            if data["type_node"] == "obp_module":
                # Extract x and y coordinates from the module node name
                coords = node.replace("OBPModule(", "").replace(")", "").split(", ")
                node_labels[node] = f"{coords[0]}, {coords[1]}"
            elif data["type_node"] == "uplink_node":
                # Extract x and y coordinates of related module and index of the node
                module_coords = node.split("_")[0].replace("OBPModule(", "").replace(")", "").split(", ")
                node_index = node.split("_")[-1]
                node_labels[node] = f"{module_coords[0]}, {module_coords[1]}, UP:{node_index}"
            elif data["type_node"] == "downlink_node":
                # Extract x and y coordinates of related module and index of the node
                module_coords = node.split("_")[0].replace("OBPModule(", "").replace(")", "").split(", ")
                node_index = node.split("_")[-1]
                node_labels[node] = f"{module_coords[0]}, {module_coords[1]}, DL:{node_index}"

        nx.draw_networkx_labels(self.graph, pos, labels=node_labels, font_size=40)
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels, font_size=25, font_color="black")

        plt.axis("off")

        # Display the plot
        #plt.show()


        # Define the results directory
        results_folder = 'results'
        scenario_folder = self.scenario_config['scenario_name']
        
        # full_path = os.path.join(results_folder, scenario_folder)
    
        # # Create the packet_size folder if it doesn't exist
        # if not os.path.exists(full_path):
        #     os.makedirs(full_path)
    
        # # Save the figure in PDF and svg formats
        # plt.savefig(os.path.join(full_path, 'obp_graph.pdf'), format='pdf')
        # plt.savefig(os.path.join(full_path, 'obp_graph.svg'), format='svg')
    
        plt.close()





    def create_toroidal_grid(self):
        dim = (self.width, self.height)
        G = nx.DiGraph()
        self.interlinks = []  # Initialize a list to store Interlink objects
        toroidal_edges = []  # Store toroidal edges
        regular_edges = []  # Store regular edges
    
        # Determine backup modules from the configuration
        if self.scenario_config['simulation']['backup_is_considered'] == 'on':
            backup_nodes = [eval(item) for item in self.scenario_config['simulation']['backup']]
        else:
            backup_nodes = []
    
        # Create a 2D array of OBPModule instances
        obp_modules = [[OBPModule(i, j) for j in range(self.height)] for i in range(self.width)]
    
        for i in range(dim[0]):
            for j in range(dim[1]):
                current_module = obp_modules[i][j]
                module_name = f"OBPModule({i}, {j})"
    
                # Check if the current module is a backup
                is_backup = (i, j) in backup_nodes
    
                # Add OBP module node to the graph with backup status
                G.add_node(module_name, type_node="obp_module", x=i, y=j, failed=False, backup=is_backup)
    
                # Add uplink and downlink nodes for each OBP module if it's not a backup
                if not is_backup:
                    for k in range(self.scenario_config['system']['uplink_number']):
                        uplink_node = f"{module_name}_uplink_{k}"
                        G.add_node(uplink_node, type_node="uplink_node", x=i, y=j)
                        G.add_edge(uplink_node, module_name, link_type="uplink")
    
                    for k in range(self.scenario_config['system']['downlink_number']):
                        downlink_node = f"{module_name}_downlink_{k}"
                        G.add_node(downlink_node, type_node="downlink_node", x=i, y=j)
                        G.add_edge(module_name, downlink_node, link_type="downlink")
    
                # Determine neighbors based on toroidal wrap-around
                neighbors = self._get_neighbors(i, j, dim)
    
                # Create Interlinks for each connection
                for ni, nj in neighbors:
                    neighbor_name = f"OBPModule({ni}, {nj})"
                    if not G.has_edge(module_name, neighbor_name):
                        interlink = Interlink(module_name, neighbor_name, self.scenario_config['system']['interlink_capacity'])
                        self.interlinks.append(interlink)
                        G.add_edge(module_name, neighbor_name, interlink=interlink, capacity=interlink.bandwidth, link_type="interlink")
                        if (i, j) < (ni, nj):  # Avoid double counting
                            regular_edges.append((module_name, neighbor_name))
    
        # Handle toroidal edges separately to avoid duplicates
        self._add_toroidal_edges(G, dim, toroidal_edges)
    
        return G, toroidal_edges, regular_edges


##############################################################################################################


    def _get_neighbors(self, i, j, dim):
        
        """
        Get the neighbors of a node in a toroidal grid.
    
        This function calculates the neighbors of a node (i, j) in a toroidal grid with dimensions `dim`.
    
        :param i: The row index of the node.
        :type i: int
        :param j: The column index of the node.
        :type j: int
        :param dim: The dimensions of the toroidal grid (rows, columns).
        :type dim: tuple
        :return: A list of neighboring nodes as (row, column) tuples.
        :rtype: list of tuple
        """        
            
        
        neighbors = []
        if dim[0] > 1:  # More than one row
            neighbors.append(((i + 1) % dim[0], j))  # Right neighbor
            neighbors.append(((i - 1) % dim[0], j))  # Left neighbor
        if dim[1] > 1:  # More than one column
            neighbors.append((i, (j + 1) % dim[1]))  # Bottom neighbor
            neighbors.append((i, (j - 1) % dim[1]))  # Top neighbor
        return neighbors
    
    def _add_toroidal_edges(self, G, dim, toroidal_edges):
        
        """
        Add toroidal edges to the graph.
    
        This function adds toroidal edges to the graph `G` for nodes in a grid with dimensions `dim`.
    
        :param G: The graph to which toroidal edges will be added.
        :type G: networkx.Graph
        :param dim: The dimensions of the toroidal grid (rows, columns).
        :type dim: tuple
        :param toroidal_edges: A list to store the toroidal edges that are added.
        :type toroidal_edges: list of tuple
        """        
        
        
        if dim[0] > 1:
            for j in range(dim[1]):
                src = f"OBPModule(0, {j})"
                tgt = f"OBPModule({dim[0] - 1}, {j})"
                toroidal_edges.extend([(src, tgt), (tgt, src)])
                G.add_edge(src, tgt, capacity=self.scenario_config['system']['interlink_capacity'], link_type="interlink")
                G.add_edge(tgt, src, capacity=self.scenario_config['system']['interlink_capacity'], link_type="interlink")
    
        if dim[1] > 1:
            for i in range(dim[0]):
                src = f"OBPModule({i}, 0)"
                tgt = f"OBPModule({i}, {dim[1] - 1})"
                toroidal_edges.extend([(src, tgt), (tgt, src)])
                G.add_edge(src, tgt, capacity=self.scenario_config['system']['interlink_capacity'], link_type="interlink")
                G.add_edge(tgt, src, capacity=self.scenario_config['system']['interlink_capacity'], link_type="interlink")

########################################################################################################################


    def get_interlinks(self):
        """
        Retrieve details of all interlinks in the network topology.

        Returns:
            list: A list containing dictionaries with details of each interlink.
        """
        interlink_details = []
        for interlink in self.interlinks:
            detail = {
                'module1': (interlink.module1), #.x, interlink.module1.y),
                'module2': (interlink.module2), #.x, interlink.module2.y),
                'bandwidth': self.scenario_config['system']['interlink_capacity']  # interlink_capacity ,
            }
            interlink_details.append(detail)

        return interlink_details


    
    
    
    def print_node_counts(self):
        """
        Print the count of uplink and downlink nodes for each OBP module.
        """
        for node, data in self.graph.nodes(data=True):
            if data["type_node"] == "obp_module":
                uplinks = 0
                downlinks = 0
                for neighbor in self.graph.neighbors(node):
                    if self.graph.nodes[neighbor]["type_node"] == "downlink_node":
                        downlinks += 1
                for predecessor in self.graph.predecessors(node):
                    if self.graph.nodes[predecessor]["type_node"] == "uplink_node":
                        uplinks += 1
                print(f"For OBP module {node}, there are {uplinks} uplink nodes and {downlinks} downlink nodes.")
    



    def get_node_connections(self):
        """
        Return the count of uplink and downlink nodes connected to each OBP module.
        If no uplink or downlink nodes are connected, label as a backup node.
        """
        node_connections = []

        for node, data in self.graph.nodes(data=True):
            if data["type_node"] == "obp_module":
                uplink_count = 0
                downlink_count = 0
                
                for neighbor in self.graph.neighbors(node):
                    if self.graph.nodes[neighbor]["type_node"] == "downlink_node":
                        downlink_count += 1
                for predecessor in self.graph.predecessors(node):
                    if self.graph.nodes[predecessor]["type_node"] == "uplink_node":
                        uplink_count += 1
                
                # Check for backup node
                if uplink_count == 0 and downlink_count == 0:
                    node_connections.append({
                        'OBP Module': node,
                        'Status': 'Backup Node'
                    })
                else:
                    node_connections.append({
                        'OBP Module': node,
                        'Uplink Count': uplink_count,
                        'Downlink Count': downlink_count
                    })

        return node_connections



    
    def get_total_uplinks(self):
        """
        Get the total count of uplink nodes in the OBP graph.

        Returns:
            int: Total count of uplink nodes.
        """
        uplink_count = sum(1 for _, data in self.graph.nodes(data=True) if data["type_node"] == "uplink_node")
        return uplink_count

    def get_total_downlinks(self):
        """
        Get the total count of downlink nodes in the OBP graph.

        Returns:
            int: Total count of downlink nodes.
        """
        downlink_count = sum(1 for _, data in self.graph.nodes(data=True) if data["type_node"] == "downlink_node")
        return downlink_count    
    
    
    
    
    
    
    def extract_uplink_and_downlink_nodes(self):
        """
        Extract the uplink and downlink nodes from the OBP graph.

        Returns:
            tuple: A tuple containing two lists - uplink_nodes and downlink_nodes.
        """
        uplink_nodes = []
        downlink_nodes = []

        for node, data in self.graph.nodes(data=True):
            if data["type_node"] == "uplink_node":
                uplink_nodes.append(node)
            elif data["type_node"] == "downlink_node":
                downlink_nodes.append(node)

        return uplink_nodes, downlink_nodes    


##################################################################################################################################



    
    def generate_demand_matrix(self, num_commodities):
        
        """
        Generate a demand matrix for the OBP network.
    
        This function generates a demand matrix based on the scenario configuration. The demand matrix consists of 
        source-destination pairs, their respective arrival rates, and priorities. It supports both random and fixed 
        demand generation modes.
    
        :param num_commodities: The number of commodities (flows) to generate.
        :type num_commodities: int
        :return: A pandas DataFrame containing the demand matrix.
        :rtype: pandas.DataFrame
        """        
            
        
        
        uplink_nodes, downlink_nodes = self.extract_uplink_and_downlink_nodes()
        
       # uplink_nodes, downlink_nodes = self.extract_uplink_and_downlink_nodes()


        used_uplinks = set()
        used_downlinks = set()
        
        # # Shuffle the node lists to ensure random selection without bias
        # np.random.shuffle(uplink_nodes)
        # np.random.shuffle(downlink_nodes)
        
        demand_matrix = []
        
        demand_matrix_generation =  self.scenario_config['system']['demand_matrix_generation']
        
        if demand_matrix_generation == "random":
            max_priority = self.scenario_config['random_demand']['max_priority']
            minimum_flow_value = self.scenario_config['random_demand']['minimum_flow_value']
            maximum_flow_value = self.scenario_config['random_demand']['maximum_flow_value']
            priorities = np.random.choice(range(1, max_priority + 1), num_commodities, replace=True)

            for i in range(num_commodities):
                # source = random.choice(uplink_nodes)
                # destination = random.choice(downlink_nodes)
                # Ensuring unique uplink or downlink nodes
                
                source = np.random.choice([node for node in uplink_nodes if node not in used_uplinks])
                used_uplinks.add(source)
                
                destination = np.random.choice([node for node in downlink_nodes if node not in used_downlinks])
                
                used_downlinks.add(destination)
                
                
                

                arrival_rate = float(np.random.uniform(minimum_flow_value, maximum_flow_value)) # random.uniform(minimum_flow_value, maximum_flow_value)
                if max_priority > 1:
                    priority = priorities[i] # np.random.randint(1, max_priority + 1 )
                else:
                    priority = 1 
                #priority =  np.random.randint(1, max_priority)

                
                # Assuming 'flow' is equivalent to 'arrival_rate' for simplicity
                # flow = arrival_rate
                demand_matrix.append([source, destination, arrival_rate, priority])
                
              #  flow = arrival_rate
                # demand_matrix.append([source, destination, arrival_rate, flow, priority])
        
        elif demand_matrix_generation == "fixed":
            for i in range(num_commodities):
                source = self.scenario_config['fixed_demand']['source'][i]
                destination = self.scenario_config['fixed_demand']['destination'][i]
                arrival_rate = float(self.scenario_config['fixed_demand']['arrival_rate'][i])
                priority = self.scenario_config['fixed_demand']['priority'][i]  # [1,3,2,1,3,2,1]
                #flow = arrival_rate  # Assuming 'flow' is equivalent to 'arrival_rate'
                #demand_matrix.append([source, destination, arrival_rate, flow, priority])
                demand_matrix.append([source, destination, arrival_rate, priority])
        
        # Convert demand matrix to pandas DataFrame
        df = pd.DataFrame(demand_matrix, columns=["Source", "Destination", "Arrival Rate", "Priority"])  # pd.DataFrame(demand_matrix, columns=["Source", "Destination", "Arrival Rate", "Flow", "Priority"])
        df.insert(0, 'id_flow', range(0, len(df)))
        df['Infeasible'] = False
        
        # Improve display settings for DataFrame
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_colwidth', None)
        
        return df

        

   ###############################################################################################################
    
   # # warning this to test priorities
   #  def generate_demand_matrix(self, num_commodities):
   #      """
   #      Generate a demand matrix for the OBP network.
    
   #      This function generates a demand matrix based on the scenario configuration. The demand matrix consists of 
   #      source-destination pairs, their respective arrival rates, and priorities. It supports both random and fixed 
   #      demand generation modes.
    
   #      :param num_commodities: The number of commodities (flows) to generate.
   #      :type num_commodities: int
   #      :return: A pandas DataFrame containing the demand matrix.
   #      :rtype: pandas.DataFrame
   #      """        
    
   #      uplink_nodes, downlink_nodes = self.extract_uplink_and_downlink_nodes()
        
   #      used_uplinks = set()
   #      used_downlinks = set()
        
   #      demand_matrix = []
        
   #      demand_matrix_generation = "random" #  self.scenario_config['system']['demand_matrix_generation']
        
   #      if demand_matrix_generation == "random":
   #          max_priority = self.scenario_config['random_demand']['max_priority']
   #          minimum_flow_value = self.scenario_config['random_demand']['minimum_flow_value']
   #          maximum_flow_value = self.scenario_config['random_demand']['maximum_flow_value']
            
   #          num_groups = num_commodities // max_priority
            
   #          for _ in range(num_groups):
   #              # Select a new unique source and destination for each group of max_priority
   #              source = np.random.choice([node for node in uplink_nodes if node not in used_uplinks])
   #              used_uplinks.add(source)
                
   #              destination = np.random.choice([node for node in downlink_nodes if node not in used_downlinks])
   #              used_downlinks.add(destination)
                
   #              for priority in range(1, max_priority + 1):
   #                  arrival_rate = float(np.random.uniform(minimum_flow_value, maximum_flow_value))
   #                  demand_matrix.append([source, destination, arrival_rate, priority])
        
   #      elif demand_matrix_generation == "fixed":
   #          for i in range(num_commodities):
   #              source = self.scenario_config['fixed_demand']['source'][i]
   #              destination = self.scenario_config['fixed_demand']['destination'][i]
   #              arrival_rate = float(self.scenario_config['fixed_demand']['arrival_rate'][i])
   #              priority = self.scenario_config['fixed_demand']['priority'][i]
   #              demand_matrix.append([source, destination, arrival_rate, priority])
        
   #      # Convert demand matrix to pandas DataFrame
   #      df = pd.DataFrame(demand_matrix, columns=["Source", "Destination", "Arrival Rate", "Priority"])
   #      df.insert(0, 'id_flow', range(0, len(df)))
   #      df['Infeasible'] = False
        
   #      # Improve display settings for DataFrame
   #      pd.set_option('display.max_rows', None)
   #      pd.set_option('display.max_columns', None)
   #      pd.set_option('display.width', None)
   #      pd.set_option('display.max_colwidth', None)
        
   #      return df
        
       
        
   
    
   
    
   
