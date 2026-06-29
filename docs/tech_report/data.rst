Data Configuration
==================

This file contains the configuration for the simulation of a regenerative OBP system. 
It includes settings for system parameters, optimization parameters, and simulation details.


YAML Elements Explanation
-------------------------

- **scenario_name**: 
  Name of the scenario, it will appear in plots.
  
- **system**:
  - **width**: 
    Width of the system grid. (Number)
  - **height**: 
    Height of the system grid. (Number)
  - **downlink_number**: 
    Number of downlink connections to each OBP module in our topology. (Number)
  - **uplink_number**: 
    Number of uplink connections to each OBP module in our topology. (Number)
  - **interlink_capacity**: 
    Bandwidth capacity of the interlinks (ports) in bits per time unit (bits / time unit).
  - **demand_matrix_generation**: 
    Method for generating the demand matrix, options are "random" or "fixed".
  - **time_unit**: 
    Unit of time for all configurations, options are "s" for seconds or "ms" for milliseconds.

- **optimization**:
  - **num_commodities**: 
    Number of commodities to be optimized. (Number)
  - **optimization_model**: 
    Type of optimization model used: 'multicommodity'. So far, only the multicommodity model is programmed. To add other algorithms, simply add the Python code for the desired algorithm in the optimizer folder. In the main file, choose which algorithm to run depending on the YAML configuration.
    
  - **max_hops**: 
    Maximum allowed number of hops in a path.
  - **objective_func**: 
    Identifier for the objective function used in optimization. Options are 'minimize_max_flow', 'minimize_hops', 'remaining_capacity_maximization', 'capacity_priority_tradeoff', 'normalized_weighted_capacity_optimization'.
  - **split_commodities**: 
    Whether to split the flow of each commodity. Options: "on" or "off".

- **random_demand**: 
  Parameters for random demand generation (if `demand_matrix_generation` is "random").
  - **minimum_flow_value**: 
    Minimum flow value.
  - **maximum_flow_value**: 
    Maximum flow value.
  - **max_priority**: 
    Maximum priority level.

- **fixed_demand**: 
  Parameters for fixed demand generation (if `demand_matrix_generation` is "fixed").
  - **arrival_rate**: 
    List of arrival rates for each commodity.
  - **priority**: 
    List of priority levels for each commodity, where lower values indicate higher priority.
  - **source**: 
    List of source nodes (uplinks) for each commodity.
  - **destination**: 
    List of destination nodes (downlinks) for each commodity.

- **simulation**:
  - **num_runs**: 
    Number of runs for the simulation for confidence interval.
  - **simulation_time**: 
    Total time for each simulation run in time unit.
  - **generation_finish_time**: 
    Time duration when the generation of packets should stop. (Should be less than simulation time; set to "inf" for infinite generation)
  - **buffer_size**: 
    Buffer size at each OBP node port ('None' for infinite buffer). Unit: depends on `limit_bytes` parameter.
  - **obp_capacity**: 
    Processing rate at the OBP module. Unit: packets/time unit.
  - **fetchingAlgorithm**: 
    Packet fetching algorithm ("fifo", "wfq", "priority").
  - **limit_bytes**: 
    If True, queue limits (`buffer_size` parameter) are in bytes. Otherwise, it's packet-based.
  - **interarrival_time_generation**: 
    Type of interarrival time distribution ("weibull", "uniform", "exponential", "fixed").
  - **interarrival_time_value_if_generation_fixed**: 
    Fixed interarrival time value if `interarrival_time_generation` is "fixed".
  - **packet_distribution_generation**: 
    Type of packet size distribution ("exponential" or "fixed").
  - **avg_packet_size**: 
    Average size of packets in bytes.
  - **weibull_packet_generation**:
    - **shape_weibull**: 
      Shape parameter for Weibull distribution of packet generation.
  - **uniform_packet_generation**:
    - **lower_bound**: 
      Lower bound for uniform distribution of packet generation.
    - **upper_bound**: 
      Upper bound for uniform distribution of packet generation.
    

--------------------------------------------------------
