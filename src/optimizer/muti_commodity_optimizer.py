#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This code defines a class called MultiCommodityOptimizer that represents an optimizer for multi-commodity flow problems.

The class encapsulates the functionality to find paths with limited hops, solve the multi-commodity flow problem using various
objective functions, and handle network constraints. The class uses the NetworkX library for graph operations and the CVXPY library
for convex optimization.

"""
# @author: zineb.garroussi@polymtl.ca


from utils.libs import *  # Importing all libraries centralized in the libs.py module
#from config_loader import config_values
from modem.obp_module import OBPModule
from port.interlink import Interlink


def _solve_kwargs_for_cvxpy_solver(solver, user_opts, verbose):
    """
    Map mixed solver_options (ECOS abstol/reltol or SCS eps_abs/eps_rel) to valid
    problem.solve() kwargs for the given solver.
    """
    u = user_opts or {}
    if solver not in (cp.ECOS, cp.SCS):
        out = {'verbose': verbose}
        out.update(u)
        return out
    if solver == cp.SCS:
        out = {'verbose': verbose}
        eps_a = u.get('eps_abs')
        if eps_a is None and 'abstol' in u:
            eps_a = u['abstol']
        if eps_a is not None:
            out['eps_abs'] = float(eps_a)
        eps_r = u.get('eps_rel')
        if eps_r is None and 'reltol' in u:
            eps_r = u['reltol']
        if eps_r is not None:
            out['eps_rel'] = float(eps_r)
        if 'max_iters' in u:
            out['max_iters'] = int(u['max_iters'])
        return out
    if solver == cp.ECOS:
        out = {'verbose': verbose}
        for key in (
            'abstol', 'reltol', 'feastol',
            'abstol_inacc', 'reltol_inacc', 'feastol_inacc',
            'max_iters',
        ):
            if key in u:
                out[key] = u[key]
        if 'abstol' not in out and 'eps_abs' in u:
            out['abstol'] = float(u['eps_abs'])
        if 'reltol' not in out and 'eps_rel' in u:
            out['reltol'] = float(u['eps_rel'])
        return out
    out = {k: v for k, v in u.items()}
    out['verbose'] = verbose
    return out


class MultiCommodityOptimizer:
    
    """
    A class used to optimize multi-commodity flow problems in a network.

    Attributes
    ----------
    scenario_config : dict
        Configuration for the simulation scenario.
    graph : networkx.Graph
        The network graph.
    interlinks : list
        List of interlink edges in the graph.


    """   
    
    
    
    def __init__(self, scenario_config, graph, interlinks):

        """
        Initializes the MultiCommodityOptimizer with the given configuration, graph, and interlinks.

        Parameters
        ----------
        scenario_config : dict
            Configuration for the simulation scenario.
        graph : networkx.Graph
            The network graph.
        interlinks : list
            List of interlink edges in the graph.
        """        
        
        
        self.scenario_config = scenario_config
        self.graph = graph
        self.interlinks = interlinks

    def find_paths_limited_hops(self, source, destination, max_hops, mode='cold'):
        
        """
        Finds paths between source and destination nodes with a limited number of hops.

        Parameters
        ----------
        source : node
            The source node in the graph.
        destination : node
            The destination node in the graph.
        max_hops : int
            Maximum number of hops allowed in the paths.
        mode : str, optional
            Mode of path finding, by default 'cold'.

        Returns
        -------
        list
            List of paths between the source and destination.
        """        
        
        
        
        
        mode = self.scenario_config['simulation']['path_mode'] 
        
        def dfs(path, visited):
            node = path[-1]
            if node == destination:
                paths.append(list(path))
                return
            if len(path) >= max_hops + 1:
                return
            for neighbor in self.graph[node]:
                if neighbor not in visited and not self.graph.nodes[neighbor].get('failed', False):
                    if mode == 'cold' and self.graph.nodes[neighbor].get('backup', False):
                        continue
                    dfs(path + [neighbor], visited | {neighbor})

        paths = []
        if self.graph.nodes[source].get('failed', False) or (mode == 'cold' and self.graph.nodes[source].get('backup', False)) or \
                self.graph.nodes[destination].get('failed', False) or (mode == 'cold' and self.graph.nodes[destination].get('backup', False)):
            return paths

        dfs([source], {source})
        return paths
    
    
    
    ###########################################################################################################################################################

    def solve_mcfp_path_formulation(self, demand_matrix, objective_type, mode='cold',
                                    skip_infeasible_fallback=False, verbose=True, solver_options=None):
        
        """
        Solves the multi-commodity flow problem using the specified objective type.

        Parameters
        ----------
        demand_matrix : pandas.DataFrame
            DataFrame containing the demand matrix.
        objective_type : str
            The objective type for optimization.
        mode : str, optional
            Mode of failure strategy, by default 'cold'.
        skip_infeasible_fallback : bool, optional
            If True, when the solver reports INFEASIBLE, return None immediately without
            removing any commodity. Use for feasibility checks. Default False.
        verbose : bool, optional
            If True, print solver progress. Default True.
        solver_options : dict, optional
            Extra kwargs passed to problem.solve() for solver tuning (e.g. max_iters, eps_abs).

        Returns
        -------
        pandas.DataFrame or None
            DataFrame containing the results, or None if infeasible and skip_infeasible_fallback=True.
        """        
        mode = self.scenario_config['simulation']['path_mode']  # mode of failure strategy cold or warm
        
        
        if objective_type in ['remaining_capacity_maximization', 'capacity_priority_tradeoff', 'normalized_weighted_capacity_optimization', 'minimize_max_link_utilization'] and len(self.interlinks) == 0:
            raise ValueError("Objective function requires interlinks, but the network configuration does not contain any. Choose another objective function.")

        avg_packet_size = self.scenario_config['simulation']['avg_packet_size']
        if not isinstance(avg_packet_size, (int, float)) or avg_packet_size <= 0:
            raise ValueError("Invalid value for avg_packet_size. It must be a positive number.")

        epsilon = 1e-7
        max_hops = self.scenario_config['optimization']['max_hops']
        interlink_capacity = self.scenario_config['system']['interlink_capacity']
        node_capacity = self.scenario_config['simulation']['obp_capacity']

        if not isinstance(max_hops, (int, float)) or max_hops < 0:
            raise ValueError("Invalid value for max_hops. It must be a non-negative number.")

        commodity_paths_cache = {}
        flow_on_path = {}
        y_p_k = {}

        split_config = self.scenario_config['optimization']['split_commodities']
        if split_config not in ['on', 'off']:
            raise ValueError("Invalid split_config value. It must be either 'on' or 'off'.")

        # Optional: use tight epigraph formulation for minimize_max_link_utilization
        # (explicit z with per-edge utilization constraints).
        use_tight_formulation = bool(
            self.scenario_config.get('optimization', {}).get('use_tight_formulation', False)
        )

        lambda_interlinks = {(u, v): cp.Variable(nonneg=True, name=f"lambda_{u}_{v}")
                             for u, v, data in self.graph.edges(data=True) if data['link_type'] == 'interlink'}

        # Variables to store constraints and feasible matrix for dual variable extraction
        final_demand_constraints = None
        final_feasible_demand_matrix = None
        final_capacity_constraints = None
        final_capacity_edge_mapping = None  # Maps constraint index to edge (u, v)

        while True:
            feasible_demand_matrix = demand_matrix[~demand_matrix['Infeasible']]
            if feasible_demand_matrix.empty:
                print("All commodities are marked as infeasible. Cannot solve the problem.")
                break

            for idx, row in feasible_demand_matrix.iterrows():
                source, destination = row["Source"], row["Destination"]
                if (source, destination) not in commodity_paths_cache:
                    paths_for_commodity = self.find_paths_limited_hops(source, destination, max_hops, mode)
                    commodity_paths_cache[(source, destination)] = paths_for_commodity
                else:
                    paths_for_commodity = commodity_paths_cache[(source, destination)]

                for path_idx, _ in enumerate(paths_for_commodity):
                    flow_on_path[(idx, path_idx)] = cp.Variable(nonneg=True, name=f"flow_commodity_{idx}_path_{path_idx}")
                    # Only needed for split='off' (single-path selection / MILP).
                    if split_config == 'off':
                        y_p_k[(idx, path_idx)] = cp.Variable(boolean=True, name=f"path_selected_{idx}_path_{path_idx}")


            objective = 0
            objective_terms = []
            constraints = []
            capacity_constraints = []
            capacity_constraints_no_split = []
            demand_constraints = []
            constraints_non_neg = []
            single_path_constraints = []
            z_var = None

                

                                    
                                    
            
            
            if objective_type == 'minimize_max_flow': # 'objective4': # Minimize the maximum flow value across all commodities and paths.
                if split_config == 'on':     
                    # objective = cp.Minimize(
                    #     cp.max([flow_on_path[(idx, path_idx)] 
                    #             for idx, row in feasible_demand_matrix.iterrows() 
                    #             for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])])
                    # )
                    
                    
                    # Convert the list of flows into a CVXPY-compatible format
                    flows = cp.hstack([
                        flow_on_path[(idx, path_idx)]
                        for idx, row in feasible_demand_matrix.iterrows()
                        for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
                    ])
                    
                    # Now use cp.max on the CVXPY-compatible expression
                    objective = cp.Minimize(cp.max(flows))
                    
                    
                    
                else:                   
                    # Minimize the maximum flow value across all commodities and paths.
                    # objective = cp.Minimize(
                    #     cp.max([y_p_k[(idx, path_idx)] * row['Arrival Rate']
                    #             for idx, row in feasible_demand_matrix.iterrows() 
                    #             for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])]))

                    
                    # Convert the list of expressions to a CVXPY-compatible format
                    flows = cp.hstack([
                        y_p_k[(idx, path_idx)] * row['Arrival Rate']
                        for idx, row in feasible_demand_matrix.iterrows() 
                        for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
                    ])
                    
                    # Now use cp.max on the CVXPY-compatible expression
                    objective = cp.Minimize(cp.max(flows))                
            

                        

            elif objective_type == 'minimize_hops':  # New objective for minimizing hops
                if split_config == 'on':
                    objective = cp.Minimize(cp.sum([
                        len(commodity_paths_cache[(row["Source"], row["Destination"])][path_idx]) * flow_on_path[(idx, path_idx)]
                        for idx, row in feasible_demand_matrix.iterrows()
                        for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
                    ]))
                else:
                    objective = cp.Minimize(cp.sum([
                        len(commodity_paths_cache[(row["Source"], row["Destination"])][path_idx]) * y_p_k[(idx, path_idx)] * row['Arrival Rate']
                        for idx, row in feasible_demand_matrix.iterrows()
                        for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
                    ]))
                    
            # Explanation: The goal of this objective is to ensure that the network handles traffic in a balanced manner. 
            # It tries to ensure that no single interlink is overly burdened compared to others. By maximizing the minimum remaining capacity,
            #we're aiming for an even distribution of traffic such that the bottleneck edge has the maximum possible capacity left, which in turn implies 
            # a more resilient and balanced network.
            elif objective_type == 'remaining_capacity_maximization': # Maximize the minimum remaining capacity across all interlinks after considering all flows.
            
                if split_config == 'on':     
                                
                    # objective = cp.Maximize(
                    #     cp.min(cp.vstack([float(interlink_capacity) - cp.sum([flow_on_path[(idx, path_idx)] 
                    #                                                   for idx, _ in feasible_demand_matrix.iterrows() 
                    #                                                   if (idx, path_idx) in flow_on_path]) 
                    #             for _, _, data in self.graph.edges(data=True) if data['link_type'] == 'interlink']))
                    # )
                    
                    
                    objective = cp.Maximize(
                        cp.min([
                            float(interlink_capacity) - cp.sum([
                                flow_on_path[(idx, path_idx)] 
                                for idx, row in feasible_demand_matrix.iterrows()
                                for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
                                if interlink in path  # 'interlink in path' is a placeholder condition to check if the path uses this interlink
                            ])
                            for interlink in self.interlinks  # Iterate over interlinks instead of edges
                        ])
                    )
                                        
                    

                    
                else:        
                    # Maximize the minimum remaining capacity across all interlinks after considering all flows.
                    objective = cp.Maximize(
                        cp.min([float(interlink_capacity)- cp.sum([y_p_k[(idx, path_idx)] * row['Arrival Rate'] 
                                                           for idx, _ in feasible_demand_matrix.iterrows() 
                                                           for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]) 
                                                           if (u, v) in path])
                                for u, v, data in self.graph.edges(data=True) if data['link_type'] == 'interlink']))

                                           
                
            
            elif objective_type == 'capacity_priority_tradeoff':  # Combines maximizing the minimum remaining capacity on all interlinks and a weighted term that prioritizes certain flows. The parameter λ determines the trade-off.

                if split_config == 'on': 


                    lambda_param = 1.00
                    original_objective = cp.Maximize(
                        cp.min(cp.vstack([float(interlink_capacity) - cp.sum([flow_on_path[(idx, path_idx)] 
                                                                      for idx, _ in feasible_demand_matrix.iterrows() 
                                                                      if (idx, path_idx) in flow_on_path]) 
                                for _, _, data in self.graph.edges(data=True) if data['link_type'] == 'interlink']))
                    )
                    weighted_priority_term = cp.sum([
                        (2 ** -row['Priority']) * flow_on_path[(idx, path_idx)]
                        for idx, row in feasible_demand_matrix.iterrows() 
                        for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
                    ])
                    objective = cp.Maximize(original_objective.expr + lambda_param * weighted_priority_term)
                    
                else:  
                                
                    # Objective combining maximizing minimum remaining capacity and a weighted term.
                    lambda_param = 0.1
                    objective = cp.Maximize(
                        lambda_param * (cp.min([float(interlink_capacity) - cp.sum([y_p_k[(idx, path_idx)] * row['Arrival Rate']
                                                                             for idx, _ in feasible_demand_matrix.iterrows() 
                                                                             for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]) 
                                                                             if (u, v) in path])
                                        for u, v, data in self.graph.edges(data=True) if data['link_type'] == 'interlink'])) +
                        (1 - lambda_param) * (cp.sum([(2 ** -row['Priority']) * y_p_k[(idx, path_idx)] * row['Arrival Rate']
                                                      for idx, row in feasible_demand_matrix.iterrows() 
                                                      for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])])))
                                
 
    
            #elif objective_type == 'objective9':  #  same as objective8 But i NORMALIZED terms in the objectif function
            elif objective_type == 'normalized_weighted_capacity_optimization':  # Same as objective8 but with normalized terms in the objective function.

                
                # Objective 9: This objective seeks to maximize the minimum remaining capacity 
                # across interlink edges in the network while taking into account the priority 
                # of the commodities. The objectives are normalized to ensure that they are 
                # within a similar range, which helps in maintaining a balance when combining 
                # them.
                if split_config == 'on':
                    # Lambda parameter: A scalar value between 0 and 1 to weight the two objectives.
                    lambda_param = 0.9
                    
                    # Original Objective: Maximizing the minimum remaining capacity across interlink edges.
                    # It's normalized by dividing by the maximum capacity among all 'interlink' edges.
                    max_possible_capacity = max([float(interlink_capacity) for _, _, data in self.graph.edges(data=True) if data['link_type'] == 'interlink'])
                    original_objective_value = cp.min(cp.vstack([float(interlink_capacity) - cp.sum([flow_on_path[(idx, path_idx)] 
                                                                               for idx, _ in feasible_demand_matrix.iterrows() 
                                                                               if (idx, path_idx) in flow_on_path]) 
                                                        for _, _, data in self.graph.edges(data=True) if data['link_type'] == 'interlink']))
                    normalized_original_objective = original_objective_value / max_possible_capacity
                    
                    # Priority Objective: It's a sum of the product of commodity flow and its priority.
                    # It's normalized by dividing by the total flow across all commodities.
                    max_possible_flow = sum([row["Arrival Rate"] for _, row in feasible_demand_matrix.iterrows()])
                    priority_objective_value = cp.sum([(2 ** -row['Priority']) * flow_on_path[(idx, path_idx)] 
                                                      for idx, row in feasible_demand_matrix.iterrows() 
                                                      for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])])
                    normalized_priority_objective = priority_objective_value / max_possible_flow
                    
                    # Combine the normalized objectives
                    objective = cp.Maximize((1 - lambda_param) * normalized_original_objective + lambda_param * normalized_priority_objective)

                else:                      
                    # Normalized combined max-min capacity and priority.
                    lambda_param = 0.9
                    max_capacity = max([float(interlink_capacity) for _, _, data in self.graph.edges(data=True) if data['link_type'] == 'interlink'])
                    total_flow = sum([row['Arrival Rate'] for _, row in feasible_demand_matrix.iterrows()])
                    objective = cp.Maximize(
                        (1 - lambda_param) * (cp.min([float(interlink_capacity) - cp.sum([y_p_k[(idx, path_idx)] * row['Arrival Rate']
                                                                                    for idx, _ in feasible_demand_matrix.iterrows() 
                                                                                    for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]) 
                                                                                    if (u, v) in path])
                                               for u, v, data in self.graph.edges(data=True) if data['link_type'] == 'interlink']) / max_capacity) +
                        lambda_param * (cp.sum([(2 ** -row['Priority']) * y_p_k[(idx, path_idx)] * row['Arrival Rate']
                                                for idx, row in feasible_demand_matrix.iterrows() 
                                                for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])]) / total_flow))

        

                                   
            
            elif objective_type == 'minimize_max_link_utilization':  # Minimize the maximum link utilization across all interlinks.
                # This objective minimizes the maximum utilization percentage on any single interlink.
                # Utilization = (total_flow_bits_per_sec / interlink_capacity) * 100
                # Since we're minimizing and capacity is constant, we can minimize the maximum total flow in bits/s
                
                if split_config == 'on':
                    if use_tight_formulation:
                        # Tight epigraph form:
                        #   minimize z
                        #   s.t. utilization_e <= z for all interlink edges e
                        #   0 <= z <= 100
                        z_var = cp.Variable(nonneg=True, name="z")  # percent
                        constraints_non_neg.append(z_var <= 100.0)
                        objective = cp.Minimize(z_var)
                    else:
                        # Original form: minimize max_e utilization_e
                        interlink_utilizations = []
                        for u, v, data in self.graph.edges(data=True):
                            if data['link_type'] == 'interlink':
                                # Find all paths that use this interlink (u, v)
                                matching_flows = []
                                for idx, row in feasible_demand_matrix.iterrows():
                                    for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]):
                                        # Check if (u, v) edge is in the path
                                        path_pairs = list(zip(path[:-1], path[1:]))
                                        if (u, v) in path_pairs:
                                            matching_flows.append(flow_on_path[(idx, path_idx)])
                                
                                # Calculate total flow in bits/s for this interlink
                                total_flow_bits_per_sec = cp.sum(matching_flows) * float(avg_packet_size) * 8.00 if matching_flows else 0
                                
                                # Calculate utilization as percentage
                                utilization = (total_flow_bits_per_sec / float(interlink_capacity)) * 100.0
                                interlink_utilizations.append(utilization)
                        
                        # Minimize the maximum utilization across all interlinks
                        if interlink_utilizations:
                            objective = cp.Minimize(cp.max(cp.hstack(interlink_utilizations)))
                        else:
                            raise ValueError("No interlinks found in the network.")
                        
                else:  # split_config == 'off'
                    if use_tight_formulation:
                        raise NotImplementedError("Tight formulation is currently supported for split_commodities='on' only.")
                    interlink_utilizations = []
                    for u, v, data in self.graph.edges(data=True):
                        if data['link_type'] == 'interlink':
                            # Find all paths that use this interlink
                            total_demand_through_edge = cp.sum([y_p_k[(idx, path_idx)] * row['Arrival Rate']
                                                                for idx, row in feasible_demand_matrix.iterrows()
                                                                for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
                                                                if (u, v) in zip(path[:-1], path[1:])])
                            
                            # Calculate utilization as percentage
                            total_flow_bits_per_sec = total_demand_through_edge * float(avg_packet_size) * 8.00
                            utilization = (total_flow_bits_per_sec / float(interlink_capacity)) * 100.0
                            interlink_utilizations.append(utilization)
                    
                    # Minimize the maximum utilization across all interlinks
                    if interlink_utilizations:
                        objective = cp.Minimize(cp.max(cp.hstack(interlink_utilizations)))
                    else:
                        raise ValueError("No interlinks found in the network.")

            else: 
                raise ValueError(f"Invalid objective_type: {objective_type}.")                
                




            if split_config == 'on':
                interlink_edges_count = 0
                capacity_edge_mapping = []  # Maps constraint index to edge (u, v)
                tight_active = (
                    use_tight_formulation
                    and objective_type == 'minimize_max_link_utilization'
                    and split_config == 'on'
                )
                if tight_active and z_var is None:
                    raise RuntimeError("Tight formulation requested but z_var was not created.")
                for u, v, data in self.graph.edges(data=True):
                    if data['link_type'] == 'interlink':
                        interlink_edges_count += 1
                        # Filter paths that use this edge
                        matching_flows = []
                        for idx, row in feasible_demand_matrix.iterrows():
                            for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]):
                                # Check if (u, v) edge is in the path
                                path_pairs = list(zip(path[:-1], path[1:]))
                                if (u, v) in path_pairs:
                                    matching_flows.append(flow_on_path[(idx, path_idx)])
                        
                        total_flow_through_edge = cp.sum(matching_flows) if matching_flows else 0
                        total_flow_bits_per_sec = total_flow_through_edge * float(avg_packet_size) * 8.00
                        if tight_active:
                            utilization = (total_flow_bits_per_sec / float(interlink_capacity)) * 100.0
                            constraint = utilization <= z_var
                        else:
                            constraint = total_flow_bits_per_sec <= float(interlink_capacity)
                        capacity_constraints.append(constraint)
                        capacity_edge_mapping.append((u, v))  # Store edge info for this constraint
                
                print(f"\nCapacity constraints added: {len(capacity_constraints)} (for {interlink_edges_count} interlink edges)")

            if split_config == 'off':
                capacity_edge_mapping_no_split = []  # Maps constraint index to edge (u, v)
                for u, v, data in self.graph.edges(data=True):
                    if data['link_type'] == 'interlink':
                        total_demand_through_edge = cp.sum([y_p_k[(idx, path_idx)] * row['Arrival Rate']
                                                            for idx, row in feasible_demand_matrix.iterrows()
                                                            for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
                                                            if (u, v) in zip(path[:-1], path[1:])])
                        constraint = total_demand_through_edge * float(avg_packet_size) * 8.00 <= float(interlink_capacity)
                        capacity_constraints_no_split.append(constraint)
                        capacity_edge_mapping_no_split.append((u, v))  # Store edge info for this constraint

            node_capacity_constraints = []
            
            
            # if split_config == 'on':
            #     for node in self.graph.nodes():
            #         total_incoming_flow = cp.sum([flow_on_path[(idx, path_idx)]
            #                                       for idx, row in feasible_demand_matrix.iterrows()
            #                                       for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
            #                                       if node in path[1:]])
            #         node_capacity_constraints.append(total_incoming_flow <= (float(node_capacity) * float(avg_packet_size) * 8.00))

            # elif split_config == 'off':
            #     for node in self.graph.nodes():
            #         total_incoming_flow = cp.sum([y_p_k[(idx, path_idx)] * row['Arrival Rate']
            #                                       for idx, row in feasible_demand_matrix.iterrows()
            #                                       for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])
            #                                       if node in path[1:]])
            #         node_capacity_constraints.append(total_incoming_flow <= (float(node_capacity) * float(avg_packet_size) * 8.00))



            if split_config == 'on':
                for idx, row in feasible_demand_matrix.iterrows():
                    demand = row["Arrival Rate"]
                    total_flow_for_commodity = cp.sum([flow_on_path[(idx, path_idx)]
                                                       for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])])
                    constraint = (total_flow_for_commodity == demand)
                    demand_constraints.append(constraint)

            elif split_config == 'off':
                for idx, row in feasible_demand_matrix.iterrows():
                    demand = row["Arrival Rate"]
                    for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]):
                        path_flow_constraint = y_p_k[(idx, path_idx)] * demand
                        demand_constraints.append(path_flow_constraint == demand * y_p_k[(idx, path_idx)])

            if split_config == 'on':
                for idx, row in feasible_demand_matrix.iterrows():
                    for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]):
                        constraints_non_neg.append(flow_on_path[(idx, path_idx)] >= epsilon)

            elif split_config == 'off':
                for idx, row in feasible_demand_matrix.iterrows():
                    for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]):
                        constraints_non_neg.append(y_p_k[(idx, path_idx)] >= 0)
                        constraints_non_neg.append(y_p_k[(idx, path_idx)] <= 1)
                        demand = row["Arrival Rate"]
                        constraints_non_neg.append(y_p_k[(idx, path_idx)] * demand <= flow_on_path[(idx, path_idx)])
                        constraints_non_neg.append(y_p_k[(idx, path_idx)] * demand >= flow_on_path[(idx, path_idx)] - epsilon)

            if split_config == "off":
                for idx, row in feasible_demand_matrix.iterrows():
                    single_path_constraints.append(
                        cp.sum([y_p_k[(idx, path_idx)] for path_idx, _ in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])])]) == 1)

            if split_config == "off":
                problem = cp.Problem(objective, capacity_constraints_no_split + demand_constraints + constraints_non_neg + single_path_constraints + node_capacity_constraints)
                print(f"\nProblem constraints (split=off):")
                print(f"  Capacity constraints: {len(capacity_constraints_no_split)}")
                print(f"  Demand constraints: {len(demand_constraints)}")
                print(f"  Non-negativity constraints: {len(constraints_non_neg)}")
                print(f"  Single path constraints: {len(single_path_constraints)}")
                print(f"  Node capacity constraints: {len(node_capacity_constraints)}")
                print(f"  Total constraints: {len(capacity_constraints_no_split) + len(demand_constraints) + len(constraints_non_neg) + len(single_path_constraints) + len(node_capacity_constraints)}")
            else:
                problem = cp.Problem(objective, capacity_constraints + demand_constraints + constraints_non_neg + node_capacity_constraints)
                print(f"\nProblem constraints (split=on):")
                print(f"  Capacity constraints: {len(capacity_constraints)}")
                print(f"  Demand constraints: {len(demand_constraints)}")
                print(f"  Non-negativity constraints: {len(constraints_non_neg)}")
                print(f"  Node capacity constraints: {len(node_capacity_constraints)}")
                print(f"  Total constraints: {len(capacity_constraints) + len(demand_constraints) + len(constraints_non_neg) + len(node_capacity_constraints)}")

            # Try different solvers in order of preference
            # - split='on' is a continuous convex problem (supports dual variables)
            # - split='off' introduces boolean variables (MILP/MICP; duals not generally available)
            require_optimal_strict = solver_options and solver_options.get('require_optimal_strict', False)

            if split_config == 'on':
                # Prefer ECOS when user sets any numerical tolerance (ECOS or SCS style)
                if solver_options and any(
                    k in solver_options for k in (
                        'abstol', 'reltol', 'feastol', 'eps_abs', 'eps_rel',
                        'abstol_inacc', 'reltol_inacc', 'feastol_inacc',
                    )
                ):
                    solvers_to_try = [cp.ECOS, cp.SCS]
                else:
                    solvers_to_try = [cp.SCS, cp.ECOS]
            else:
                solvers_to_try = [cp.ECOS_BB, cp.GLPK_MI]
            solved = False
            user_kw = {}
            if solver_options:
                for k, v in solver_options.items():
                    if k != 'require_optimal_strict':
                        user_kw[k] = v
            for solver in solvers_to_try:
                try:
                    if verbose:
                        print(f"\n{'='*80}")
                        print(f"Trying solver: {solver}")
                        print(f"{'='*80}")
                    skw = _solve_kwargs_for_cvxpy_solver(solver, user_kw, verbose)
                    problem.solve(solver=solver, **skw)
                    if verbose:
                        print(f"\nSolver status: {problem.status}")
                    if problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                        solved = True
                        if verbose:
                            print(f"✅ Solution found with status: {problem.status}")
                        # If ECOS/SCS reports OPTIMAL_INACCURATE, try progressively tighter ECOS
                        if split_config == 'on' and problem.status == cp.OPTIMAL_INACCURATE:
                            for tol in (1e-9, 1e-10, 1e-11):
                                try:
                                    problem.solve(
                                        solver=cp.ECOS,
                                        abstol=tol, reltol=tol, feastol=tol,
                                        abstol_inacc=tol, reltol_inacc=tol, feastol_inacc=tol,
                                        max_iters=int(user_kw.get('max_iters', 500000)),
                                        verbose=verbose,
                                    )
                                    if problem.status == cp.OPTIMAL:
                                        if verbose:
                                            print(f"ECOS tightened retry (tol={tol}): OPTIMAL")
                                        break
                                except Exception:
                                    pass
                            if require_optimal_strict and problem.status == cp.OPTIMAL_INACCURATE:
                                try:
                                    problem.solve(
                                        solver=cp.SCS,
                                        eps_abs=1e-9, eps_rel=1e-9,
                                        max_iters=int(user_kw.get('max_iters', 2500000)),
                                        verbose=verbose,
                                    )
                                except Exception:
                                    pass
                        break
                    elif verbose:
                        print(f"⚠️  Solution status not optimal: {problem.status}")
                except Exception as e:
                    if verbose:
                        print(f"❌ Solver {solver} failed with error: {e}")
                    continue
            
            # If no solver worked, let cvxpy choose automatically (default may be Clarabel)
            # Do not pass solver_options to default - Clarabel etc. may not support eps_abs etc.
            if not solved:
                if verbose:
                    print(f"\n{'='*80}")
                    print("Trying default solver")
                    print(f"{'='*80}")
                problem.solve(verbose=verbose)
                if verbose:
                    print(f"\nDefault solver status: {problem.status}")

            if problem.status == cp.INFEASIBLE:
                if skip_infeasible_fallback:
                    return None
                if self.scenario_config['simulation']['fetchingAlgorithm'] == 'fifo':
                    print("Problem is infeasible. Removing a random commodity and trying again.")
                    random_idx = np.random.choice(feasible_demand_matrix.index)
                    demand_matrix.at[random_idx, 'Infeasible'] = True
                elif self.scenario_config['simulation']['fetchingAlgorithm'] in ['wfq', 'priority']:
                    print("Problem is infeasible. Removing a randomly chosen lowest priority commodity and trying again.")
                    lowest_priority = feasible_demand_matrix['Priority'].max()
                    lowest_priority_commodities = feasible_demand_matrix[feasible_demand_matrix['Priority'] == lowest_priority]
                    random_idx = np.random.choice(feasible_demand_matrix.index)
                    demand_matrix.at[random_idx, 'Infeasible'] = True
            else:
                # Store constraints and feasible matrix for dual variable extraction
                final_demand_constraints = demand_constraints
                final_feasible_demand_matrix = feasible_demand_matrix.copy()
                if split_config == 'on':
                    final_capacity_constraints = capacity_constraints
                    final_capacity_edge_mapping = capacity_edge_mapping
                else:
                    final_capacity_constraints = capacity_constraints_no_split
                    final_capacity_edge_mapping = capacity_edge_mapping_no_split
                break

        flow_data = []
        num_commodities = len(demand_matrix)
        all_commodities = set(range(num_commodities))

        if problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
            print("Solution found!")
            if split_config == "on":
                for idx, row in feasible_demand_matrix.iterrows():
                    if idx not in all_commodities:
                        continue
                    commodity_feasible = False
                    for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]):
                        flow_value = flow_on_path[(idx, path_idx)].value
                        if flow_value > epsilon:
                            flow_data.append({
                                "id_flow": idx,
                                "Source": row["Source"],
                                "Destination": row["Destination"],
                                "Arrival Rate": flow_value,
                                "Path": " -> ".join(map(str, path)),
                                "Priority": row["Priority"]
                            })
                            commodity_feasible = True
                    if not commodity_feasible:
                        flow_data.append({
                            "id_flow": idx,
                            "Source": row["Source"],
                            "Destination": row["Destination"],
                            "Arrival Rate": 0,
                            "Path": None,
                            "Priority": row["Priority"]
                        })
                    all_commodities.remove(idx)

            if split_config == "off":
                for idx, row in feasible_demand_matrix.iterrows():
                    if idx not in all_commodities:
                        continue
                    commodity_feasible = False
                    for path_idx, path in enumerate(commodity_paths_cache[(row["Source"], row["Destination"])]):
                        path_selected = y_p_k[(idx, path_idx)].value
                        if path_selected > epsilon:
                            flow_data.append({
                                "id_flow": idx,
                                "Source": row["Source"],
                                "Destination": row["Destination"],
                                "Arrival Rate": row['Arrival Rate'],
                                "Path": " -> ".join(map(str, path)),
                                "Priority": row["Priority"]
                            })
                            commodity_feasible = True
                            break
                    if not commodity_feasible:
                        flow_data.append({
                            "id_flow": idx,
                            "Source": row["Source"],
                            "Destination": row["Destination"],
                            "Arrival Rate": 0,
                            "Path": None,
                            "Priority": row["Priority"]
                        })
                    all_commodities.remove(idx)

        elif problem.status in [cp.INFEASIBLE, cp.UNBOUNDED]:
            print("Problem is infeasible or unbounded after removing all possible commodities.")

        for idx in all_commodities:
            flow_data.append({
                "id_flow": idx,
                "Source": demand_matrix.loc[idx, "Source"] if idx in demand_matrix.index else None,
                "Destination": demand_matrix.loc[idx, "Destination"] if idx in demand_matrix.index else None,
                "Arrival Rate": 0,
                "Path": None,
                "Priority": demand_matrix.loc[idx, "Priority"] if idx in demand_matrix.index else None
            })

        df = pd.DataFrame(flow_data)
        print('Results with CVXPY:')
        #print(df)
        
        # Extract dual variables for demand constraints (always extract when solution is optimal/inaccurate)
        dual_vars = {}
        if problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE] and final_demand_constraints is not None and final_feasible_demand_matrix is not None:
            if split_config == 'on':
                for i, constraint in enumerate(final_demand_constraints):
                    idx = final_feasible_demand_matrix.index[i]
                    dual_value = constraint.dual_value
                    if dual_value is not None:
                        # NOTE: CVXPY returns dual variables with sign convention that requires negation for equality constraints
                        # For minimize max_link_utilization with constraint (total_flow == demand):
                        # - CVXPY returns negative dual values
                        # - But increasing demand should increase max_link_utilization (positive impact)
                        # - Therefore, we negate the dual values to get the correct sign
                        # Positive dual means: increasing demand increases objective (max_link_utilization)
                        dual_vars[idx] = -float(dual_value)
                    else:
                        # If dual_value is None, set to None to indicate unavailable
                        dual_vars[idx] = None
            elif split_config == 'off':
                # For split='off', demand constraints are structured differently
                # Each commodity has multiple path constraints, need to aggregate or select appropriately
                # TODO: Implement dual variable extraction for split='off' if needed
                # For now, mark as None to indicate not available
                for idx, row in final_feasible_demand_matrix.iterrows():
                    dual_vars[idx] = None
        
        # Store solver status for audit (OPTIMAL vs OPTIMAL_INACCURATE)
        df.attrs['solver_status'] = str(problem.status)

        # Store dual variables as DataFrame attribute
        df.attrs['dual_variables'] = dual_vars
        
        # Extract dual variables for capacity constraints
        capacity_dual_vars = {}
        if problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE] and final_capacity_constraints is not None and final_capacity_edge_mapping is not None:
            # Access constraints from the problem object to get dual values
            # The constraints in the problem are in the order: capacity_constraints + demand_constraints + ...
            problem_constraints = problem.constraints
            num_capacity_constraints = len(final_capacity_constraints)
            
            for i in range(num_capacity_constraints):
                if i < len(final_capacity_edge_mapping) and i < len(problem_constraints):
                    edge = final_capacity_edge_mapping[i]
                    constraint = problem_constraints[i]
                    
                    # Check if constraint is a CVXPY constraint object
                    if hasattr(constraint, 'dual_value'):
                        try:
                            dual_value = constraint.dual_value
                            if dual_value is not None:
                                # For capacity constraint: flow_e_bits <= capacity_e
                                # Dual variable μ_e represents: if capacity increases by 1 bits/s, 
                                # objective (max utilization %) decreases by μ_e %
                                # Since it's an inequality constraint (<=), dual should be non-negative
                                # CVXPY returns non-negative dual for <= constraints
                                capacity_dual_vars[edge] = float(dual_value)
                            else:
                                capacity_dual_vars[edge] = None
                        except (AttributeError, TypeError):
                            capacity_dual_vars[edge] = None
                    else:
                        # Constraint is not a CVXPY constraint object (might be bool or other type)
                        capacity_dual_vars[edge] = None
        
        # Store capacity dual variables as DataFrame attribute
        df.attrs['capacity_dual_variables'] = capacity_dual_vars
        
        # Print dual variables for debugging
        if dual_vars:
            print(f"\nDual Variables for Demand Constraints:")
            for idx, dual_val in sorted(dual_vars.items()):
                if dual_val is not None:
                    print(f"  Commodity {idx}: {dual_val:.6e}")
        
        # Print capacity dual variables for debugging (only non-zero ones)
        if capacity_dual_vars:
            non_zero_capacity_duals = {edge: val for edge, val in capacity_dual_vars.items() 
                                     if val is not None and val > 1e-10}
            if non_zero_capacity_duals:
                print(f"\nCapacity Constraint Dual Variables (non-zero):")
                for edge, dual_val in sorted(non_zero_capacity_duals.items(), key=lambda x: x[1], reverse=True):
                    print(f"  Edge {edge}: {dual_val:.6e} %/(bits/s)")
        
        return df

