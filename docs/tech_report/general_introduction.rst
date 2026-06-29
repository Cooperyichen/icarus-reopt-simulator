General Introduction
=====================

The sim_net_hts project is designed to simulate and optimize multi-commodity flow problems in a network, particularly focusing on load balancing problem. The core functionality includes:

- **Topology Generation**: Creating a toroidal topology for the network, including the setup of interlinks (ports) and nodes (obp bank = switch).
- **Path Finding**: Identifying paths with limited hops between nodes.
- **Optimization**: Solving the multi-commodity flow problem using multi-commodity flow problems and different objective functions.
- **Simulation**: Running the simulation to observe network behavior under different configurations and scenarios.
- **Analysis and Visualization**: Analyzing the simulation results and generating plots to visualize the network performance and efficiency.

The project employs the NetworkX library for graph operations and the CVXPY library for convex optimization, ensuring robust and scalable simulations.

=================
Workflow Overview
=================

1. **Initialization and Configuration**:
    - The main script starts by loading the necessary libraries and modules.
    - Scenario configurations are loaded from YAML files, defining the simulation parameters and network settings.

2. **Topology Generation**:
    - The `ToroidalTopo` class is used to create a toroidal topology of the network, specifying the width and height of the grid.
    - The topology, including nodes and interlinks, is visualized and stored.

3. **Demand Matrix Generation**:
    - A demand matrix is generated, representing the network traffic demands for various commodities.

4. **Optimization**:
    - The `MultiCommodityOptimizer` class is instantiated to solve the multi-commodity flow problem.
    - Different objective functions can be chosen, such as minimizing hops, maximizing remaining capacity, or balancing capacity and priority.

5. **Simulation**:
    - The `Simulator` class runs the simulation based on the optimized flow paths using `simpy` python framework.
    - The simulation considers various factors, including packet arrival rates and network capacity.
    - Results, including blocked flows and overall network performance, are recorded.

6. **Analysis and Visualization**:
    - Results from the simulation are saved and analyzed.
    - Various plots are generated to visualize the network performance, including average delay, packet loss, and traffic distribution index.
    - Summary statistics are printed and saved for further analysis.

7. **Main Function Execution**:
    - The `main()` function orchestrates the entire workflow, iterating over different scenarios and running simulations for each configuration.
    - Results are aggregated and plotted to provide a comprehensive view of the network's performance under different scenarios.


-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
