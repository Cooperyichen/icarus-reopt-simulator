#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在排除「infeasible 时移除 commodity」机制的条件下，检查 long congested sequence
各序列每一步的完整问题可行性。

使用 optimizer 的 skip_infeasible_fallback=True 参数，保证每一步都把完整问题给到
optimizer，并返回是否可行（不触发移除 commodity 的 fallback）。

用法: 在 src 目录下运行
  python -m main.check_long_congested_feasibility
"""

import sys
import os
import io
import contextlib
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer

SEEDS = [0, 1, 7, 42, 123, 1234]
SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'results/multi_step_comparison'


@contextlib.contextmanager
def suppress_stdout():
    """临时抑制 stdout，用于静默运行 optimizer。"""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


def check_step_feasibility(step_id, arrival_rates, config, regen_obp, num_commodities, verbose=False):
    """
    检查单步完整问题的可行性（不触发移除 commodity）。

    Returns:
        bool: True 表示可行，False 表示不可行
    """
    step_config = config.copy()
    step_config['fixed_demand'] = config['fixed_demand'].copy()
    step_config['fixed_demand']['arrival_rate'] = arrival_rates
    step_config['simulation'] = config['simulation'].copy()
    step_config['simulation']['num_steps'] = 1

    regen_obp.scenario_config = step_config
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    # 确保无 commodity 被预先标记为 Infeasible
    if 'Infeasible' in demand_matrix.columns:
        demand_matrix['Infeasible'] = False

    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']

    if verbose:
        result = optimizer.solve_mcfp_path_formulation(
            demand_matrix, objective_type, mode,
            skip_infeasible_fallback=True,
            verbose=True
        )
    else:
        with suppress_stdout():
            result = optimizer.solve_mcfp_path_formulation(
                demand_matrix, objective_type, mode,
                skip_infeasible_fallback=True,
                verbose=False
            )

    return result is not None


def main():
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, RESULTS_BASE)
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    out_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(out_dir, exist_ok=True)

    config = load_yaml_file(config_file)
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)

    num_commodities = len(config['fixed_demand']['arrival_rate'])
    all_rows = []

    print("=" * 70)
    print("Long congested sequence 可行性检查（完整问题，不触发 commodity 移除）")
    print("=" * 70)

    for seed in SEEDS:
        sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"
        sequence_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
        if not os.path.isfile(sequence_file):
            print(f"✗ 序列文件不存在: {sequence_file}")
            continue

        sequence_df = pd.read_csv(sequence_file, index_col=0)
        sequence = sequence_df.values
        num_steps = sequence.shape[0]

        print(f"\nSeed {seed}: 检查 {num_steps} 步...")
        infeasible_steps = []

        for step_id in range(1, num_steps + 1):
            arrival_rates = sequence[step_id - 1].tolist()
            feasible = check_step_feasibility(
                step_id, arrival_rates, config, regen_obp, num_commodities, verbose=False
            )
            all_rows.append({
                'seed': seed,
                'step_id': step_id,
                'feasible': feasible,
            })
            if not feasible:
                infeasible_steps.append(step_id)

            if step_id % 10 == 0 or step_id == num_steps:
                print(f"  step 1..{step_id}: {sum(1 for r in all_rows if r['seed']==seed and r['feasible'])}/{step_id} 可行", end='')
                if infeasible_steps:
                    print(f" (不可行: {infeasible_steps})")
                else:
                    print()

        if infeasible_steps:
            print(f"  Seed {seed} 不可行步: {infeasible_steps}")

    df = pd.DataFrame(all_rows)
    summary_path = os.path.join(out_dir, 'full_problem_feasibility_check.csv')
    df.to_csv(summary_path, index=False)
    print(f"\n✓ 详细结果已保存: {summary_path}")

    # 汇总每个 seed 的不可行步
    summary_rows = []
    for seed in SEEDS:
        sub = df[df['seed'] == seed]
        infeasible = sub[~sub['feasible']]['step_id'].tolist()
        summary_rows.append({
            'seed': seed,
            'total_steps': len(sub),
            'feasible_count': sub['feasible'].sum(),
            'infeasible_count': (~sub['feasible']).sum(),
            'infeasible_steps': str(infeasible) if infeasible else '',
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_path = os.path.join(out_dir, 'full_problem_feasibility_summary.csv')
    summary_df.to_csv(summary_path, index=False)
    print(f"✓ 汇总已保存: {summary_path}")

    print("\n" + "=" * 70)
    print(summary_df.to_string(index=False))
    print("=" * 70)


if __name__ == '__main__':
    main()
