#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审计 seed 15 和 seed 20 上 S1 每步的求解器状态，检查是 OPTIMAL 还是 OPTIMAL_INACCURATE。
使用当前 PRECISE_SOLVER_OPTIONS (eps_abs=1e-8, eps_rel=1e-8)。
"""

import sys
import os
import warnings
warnings.filterwarnings('ignore')

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

import pandas as pd
import numpy as np

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer

SEQUENCE_DIR = 'long congested sequence'
PRECISE_SOLVER_OPTIONS = {'eps_abs': 1e-8, 'eps_rel': 1e-8, 'max_iters': 500000}
STRICT_OPTIMAL_OPTIONS = {**PRECISE_SOLVER_OPTIONS, 'require_optimal_strict': True}


def audit_seed(seed, max_steps=50):
    """对指定 seed 审计 S1 每步的 solver status"""
    result_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    sequence_file = os.path.join(result_base, SEQUENCE_DIR, str(seed), 'arrival_rate_sequence_50_steps.csv')
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')

    if not os.path.exists(sequence_file):
        print(f"✗ seed {seed}: 序列文件不存在")
        return None

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values

    rows = []
    for step_id in range(1, min(max_steps + 1, len(sequence) + 1)):
        arrival_rates = sequence[step_id - 1].tolist()
        step_config = config.copy()
        step_config['fixed_demand'] = config['fixed_demand'].copy()
        step_config['fixed_demand']['arrival_rate'] = arrival_rates
        regen_obp = ToroidalTopo(scenario_config=step_config, width=config['system']['width'], height=config['system']['height'])
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=len(arrival_rates))
        optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
        result_df = optimizer.solve_mcfp_path_formulation(
            demand_matrix, step_config['optimization']['objective_func'],
            step_config['simulation']['failure_strategy'],
            verbose=False, solver_options=STRICT_OPTIMAL_OPTIONS
        )
        status = result_df.attrs.get('solver_status', 'unknown') if result_df is not None else 'no_result'
        rows.append({'step_id': step_id, 'solver_status': status})
        print(f"  Step {step_id:2d}: {status}")

    return pd.DataFrame(rows)


def main():
    print("=" * 70)
    print("审计 seed 15 和 seed 20 的 S1 求解器状态 (STRICT_OPTIMAL_OPTIONS)")
    print("=" * 70)

    for seed in [15, 20]:
        print(f"\n--- Seed {seed} ---")
        df = audit_seed(seed)
        if df is not None:
            optimal = (df['solver_status'] == 'optimal').sum()
            inaccurate = (df['solver_status'] == 'optimal_inaccurate').sum()
            other = len(df) - optimal - inaccurate
            print(f"  汇总: OPTIMAL={optimal}, OPTIMAL_INACCURATE={inaccurate}, 其他={other}")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
