#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单步验证：对 step 35（seed 0, long congested）重新跑 S1 的 MCFP 求解器，
确认控制台输出的 Solver status 是否达到 OPTIMAL，并对比返回解的 max_link_utilization
与 strategy1_stats 中 step 35 的记录、以及 S4 同步的 max_link_utilization。

用法: 在 src 目录下运行
  python -m main.verify_s1_solver_step35
运行时请查看控制台中的 "Solver status:" 或 "Default solver status:" 输出。
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
from main.multi_step_comparison_experiment import calculate_max_link_utilization

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'results/multi_step_comparison'
SEED = 0
CHECK_STEP = 35


def main():
    results_base = os.path.join(src_dir, RESULTS_BASE)
    base = os.path.join(results_base, SEQUENCE_DIR_NAME, str(SEED))
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    sequence_file = os.path.join(results_base, SEQUENCE_DIR_NAME, str(SEED), 'arrival_rate_sequence_50_steps.csv')

    if not os.path.isfile(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return
    if not os.path.isfile(config_file):
        print(f"✗ 配置文件不存在: {config_file}")
        return

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    num_steps, num_commodities = sequence.shape

    if CHECK_STEP < 1 or CHECK_STEP > num_steps:
        print(f"✗ CHECK_STEP={CHECK_STEP} 超出范围 [1, {num_steps}]")
        return

    arrival_rates = sequence[CHECK_STEP - 1].tolist()
    step_config = config.copy()
    step_config['fixed_demand'] = config['fixed_demand'].copy()
    step_config['fixed_demand']['arrival_rate'] = arrival_rates
    step_config['simulation'] = config['simulation'].copy()
    step_config['simulation']['num_steps'] = 1

    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=step_config, width=width, height=height)
    regen_obp.scenario_config = step_config
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)

    print("=" * 70)
    print(f"重新运行 S1 求解器：step {CHECK_STEP} (seed={SEED}, long congested)")
    print("=" * 70)
    print(f"Arrival rates (step {CHECK_STEP}): {[f'{r:.2f}' for r in arrival_rates]}")
    print("\n下方将出现求解器输出，请留意 'Solver status:' 或 'Default solver status:' 是否为 optimal / optimal_inaccurate。\n")

    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']
    updated_demand_matrix = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)

    if updated_demand_matrix is None or len(updated_demand_matrix) == 0:
        print("\n✗ 求解器未返回有效解")
        return

    util_recomputed = calculate_max_link_utilization(updated_demand_matrix, step_config)
    print("\n" + "=" * 70)
    print("单步验证结果")
    print("=" * 70)
    print(f"本脚本用返回的 MCFP 计算的 max_link_utilization: {util_recomputed:.4f}%")

    s1_stats_path = os.path.join(base, 'strategy1', 'strategy1_stats.csv')
    s4_stats_path = os.path.join(base, 'strategy4', 'strategy4_stats.csv')
    if os.path.isfile(s1_stats_path):
        s1_df = pd.read_csv(s1_stats_path)
        row = s1_df[s1_df['step_id'] == CHECK_STEP]
        if len(row) > 0:
            util_s1_saved = float(row['max_link_utilization'].iloc[0])
            print(f"strategy1_stats 中 step {CHECK_STEP} 的 max_link_utilization: {util_s1_saved:.4f}%")
            if abs(util_recomputed - util_s1_saved) < 1e-6:
                print("  ✓ 与本次重算一致，说明实验保存的 S1 值确为求解器输出。")
            else:
                print(f"  ⚠ 与本次重算不一致（差 {abs(util_recomputed - util_s1_saved):.6f}%），请检查实验保存逻辑。")
    if os.path.isfile(s4_stats_path):
        s4_df = pd.read_csv(s4_stats_path)
        row = s4_df[s4_df['step_id'] == CHECK_STEP]
        if len(row) > 0:
            util_s4 = float(row['max_link_utilization'].iloc[0])
            print(f"strategy4_stats 中 step {CHECK_STEP} 的 max_link_utilization: {util_s4:.4f}%")
            if util_recomputed > util_s4:
                print("  → J_full (S1) > J_event (S4)，即该步存在负 regret；若上方求解器 status 为 optimal，则理论上不应出现，需进一步排查。")

    print("\n说明：若上方出现 'Problem is infeasible. Removing a random commodity and trying again.'，")
    print("则 step 35 的 4-commodity 问题不可行，S1 实际求解的是「去掉一个 commodity」后的 3-commodity 问题；")
    print("此时 S4 的全量 path-ratio 解与 S1 的解并非同一问题的解，负 regret 可解释为：S4 对全量需求可行且 max_util 更低。")
    print("=" * 70)


if __name__ == '__main__':
    main()
