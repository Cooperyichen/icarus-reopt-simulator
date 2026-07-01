Results Folder
==============

- In the `results` folder, each subfolder represents a scenario. The name of each subfolder corresponds to the scenario name in the related YAML file located in the `data` folder.

- Each scenario folder contains CSV files for each run. For example, if there are 20 runs, 20 run folders will be generated.

- Each run folder contains the following CSV files:

  - `demand_matrix.csv`: Contains the demand with flow ID, source, destination, arrival rate, priority, and an infeasible flag initialized to False.

  - `mcfp_results_flows_8_commodities.csv`: Here, `8` indicates that there are 8 commodities (or flows as set in the YAML file). This file contains the same columns as the demand matrix, plus paths. If a flow is bifurcated, multiple lines for the same flow ID will appear with different paths and different fractions of the arrival rate.

- The `results/summary_statistics.txt` file contains a summary of the simulation.

- The `results/summary_statistics_per_priority.txt` file contains a summary of the simulation by priority.

- The `results` folder also contains plots in PDF format generated at the end of the simulation execution.

