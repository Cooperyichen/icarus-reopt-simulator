#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract dual variables for Strategy 4 on increasing_sequence with threshold=5.
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer


def extract_dual_variables_from_step(step_dir, config, arrival_rates):
    """Extract dual variables by re-running optimization."""
    step_config = config.copy()
    step_config['fixed_demand'] = config['fixed_demand'].copy()
    step_config['fixed_demand']['arrival_rate'] = arrival_rates
    
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=step_config, width=width, height=height)
    
    num_commodities = len(arrival_rates)
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    
    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']
    
    result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
    
    dual_vars = {}
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
    
    return dual_vars


def main():
    """Extract dual variables for Strategy 4 on increasing_sequence."""
    
    print("=" * 80)
    print("Extract Dual Variables: increasing_sequence / Strategy 4 (threshold=5)")
    print("=" * 80)
    
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    sequence_name = 'increasing_sequence'
    strategy_name = 'strategy4'
    
    config = load_yaml_file(config_file)
    sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_increasing.csv')
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    
    stats_file = os.path.join(result_base_dir, sequence_name, strategy_name, f'{strategy_name}_stats.csv')
    if not os.path.exists(stats_file):
        print(f"✗ Stats file not found: {stats_file}")
        return
    
    stats_df = pd.read_csv(stats_file)
    
    all_dual_data = []
    num_steps = len(stats_df)
    num_commodities = len(sequence[0])
    
    for idx, row in stats_df.iterrows():
        step_id = int(row['step_id'])
        arrival_rates_str = row['arrival_rates']
        
        if isinstance(arrival_rates_str, str):
            arrival_rates = [float(x.strip()) for x in arrival_rates_str.strip('[]').split(',')]
        else:
            arrival_rates = sequence[step_id - 1].tolist()
        
        print(f"  Step {step_id}/{num_steps}: {[f'{r:.2f}' for r in arrival_rates]}")
        
        step_dir = os.path.join(result_base_dir, sequence_name, strategy_name, f'step_{step_id}')
        dual_vars = extract_dual_variables_from_step(step_dir, config, arrival_rates)
        
        for commodity_id in range(num_commodities):
            dual_value = dual_vars.get(commodity_id, None)
            all_dual_data.append({
                'step_id': step_id,
                'commodity_id': commodity_id,
                'dual_value': dual_value,
                'arrival_rate': arrival_rates[commodity_id]
            })
        
        # Print dual variables
        print(f"    Dual variables: {[dual_vars.get(i, None) for i in range(num_commodities)]}")
    
    # Create DataFrame
    dual_df = pd.DataFrame(all_dual_data)
    
    # Save
    output_file = os.path.join(result_base_dir, sequence_name, strategy_name, 'dual_variables_strategy4.csv')
    dual_df.to_csv(output_file, index=False)
    print(f"\n✓ Dual variables saved to: {output_file}")
    
    # Create pivot table
    pivot_df = dual_df.pivot(index='step_id', columns='commodity_id', values='dual_value')
    pivot_file = os.path.join(result_base_dir, sequence_name, strategy_name, 'dual_variables_pivot_strategy4.csv')
    pivot_df.to_csv(pivot_file)
    print(f"✓ Pivot table saved: {pivot_file}")
    
    print(f"\n✓ Extraction complete: {len(dual_df)} records")


if __name__ == '__main__':
    main()

