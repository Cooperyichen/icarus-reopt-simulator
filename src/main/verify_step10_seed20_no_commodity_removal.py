#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 seed 20 step 10：确保 optimizer 未移除任何 commodity，并对比 θ=4/θ=6 的 max link utilization。

使用 skip_infeasible_fallback=True 强制完整问题求解，若 infeasible 则直接返回 None（不移除 commodity）。

用法: 在 src 目录下运行
  python -m main.verify_step10_seed20_no_commodity_removal
"""

import sys
import os
import io
import contextlib
import argparse
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from main.multi_step_comparison_experiment import calculate_max_link_utilization
from main.test_path_ratio_preservation import extract_path_ratios_from_csv, apply_path_ratios_to_demand

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'results/multi_step_comparison'
SEED = 20
STEP = 10


def main():
    parser = argparse.ArgumentParser(description='Verify step 10 seed 20, no commodity removal')
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--step', type=int, default=STEP)
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    seed, step_id = args.seed, args.step
    results_base = os.path.join(src_dir, RESULTS_BASE)
    base = os.path.join(results_base, SEQUENCE_DIR_NAME, str(seed))
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    sequence_file = os.path.join(base, 'arrival_rate_sequence_50_steps.csv')

    if not os.path.isfile(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return 1
    if not os.path.isfile(config_file):
        print(f"✗ 配置文件不存在: {config_file}")
        return 1

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    num_commodities = sequence.shape[1]

    if step_id < 1 or step_id > sequence.shape[0]:
        print(f"✗ step {step_id} 超出范围 [1, {sequence.shape[0]}]")
        return 1

    arrival_rates = sequence[step_id - 1].tolist()
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
    if 'Infeasible' in demand_matrix.columns:
        demand_matrix['Infeasible'] = False

    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']

    # 高精度求解，且 skip_infeasible_fallback=True 确保不移除 commodity
    precise_options = [
        {'_label': 'ECOS (abstol=1e-9)', 'abstol': 1e-9, 'reltol': 1e-9},
        {'_label': 'SCS (eps_abs=1e-8)', 'max_iters': 500000, 'eps_abs': 1e-8, 'eps_rel': 1e-8},
    ]

    print("=" * 70)
    print(f"验证 seed={seed} step={step_id}：确保无 commodity 被移除")
    print("=" * 70)
    print(f"Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
    print(f"期望 commodity 数: {num_commodities}")
    print(f"使用 skip_infeasible_fallback=True（infeasible 时不移除 commodity）")
    print()

    # 1) 精确求解（不移除 commodity）
    print("【1】Optimizer 求解（skip_infeasible_fallback=True）...")
    best_df = None
    best_util = None
    best_label = None

    for opts_entry in precise_options:
        opts = {k: v for k, v in opts_entry.items() if k != '_label'}
        label = opts_entry.get('_label', str(opts))
        if args.verbose:
            print(f"  尝试: {label}")
        with contextlib.redirect_stdout(io.StringIO() if not args.verbose else sys.stdout):
            with contextlib.redirect_stderr(io.StringIO() if not args.verbose else sys.stderr):
                try:
                    import warnings
                    with warnings.catch_warnings(action='ignore'):
                        result = optimizer.solve_mcfp_path_formulation(
                            demand_matrix.copy(),
                            objective_type, mode,
                            skip_infeasible_fallback=True,
                            verbose=args.verbose,
                            solver_options=opts
                        )
                except Exception as e:
                    if args.verbose:
                        print(f"    失败: {e}")
                    continue
        if result is not None and len(result) > 0 and result['Arrival Rate'].sum() > 1e-6:
            util = calculate_max_link_utilization(result, step_config)
            if best_util is None or util < best_util:
                best_df = result
                best_util = util
                best_label = label
            if args.verbose:
                print(f"  {label}: max_util={util:.4f}%")

    if best_df is None:
        print("  ✗ 所有求解选项均未得到有效解（可能问题 infeasible，且未移除 commodity）")
        return 1

    # 检查 commodity 数量
    commodities_in_result = best_df['id_flow'].nunique()
    total_flow = best_df.groupby('id_flow')['Arrival Rate'].sum()
    demand_satisfied = all(
        abs(total_flow.get(i, 0) - arrival_rates[i]) < 1e-4
        for i in range(num_commodities)
    )

    print(f"  ✓ 求解成功: {best_label}")
    print(f"  max_link_utilization = {best_util:.6f}%")
    print(f"  解中 commodity 数: {commodities_in_result} / {num_commodities}")
    if commodities_in_result == num_commodities:
        print("  ✓ 无 commodity 被移除")
    else:
        print(f"  ⚠ 异常：commodity 数不足（可能被移除）")
    if demand_satisfied:
        print("  ✓ 各 commodity 需求均满足")
    else:
        print("  ⚠ 需求满足检查异常")

    # 2) Path-ratio 解（θ=6 在 step 10 使用 step 1 的 ratio）
    step1_mcfp_path = os.path.join(
        base, 'strategy4_threshold_6', 'strategy4', 'step_1', 'mcfp_results_flows_4_commodities.csv'
    )
    if not os.path.isfile(step1_mcfp_path):
        print(f"\n✗ 缺少 step 1 MCFP: {step1_mcfp_path}")
        return 1

    print("\n【2】Path-ratio 解（θ=6 在 step 10 使用 step 1 的 ratio × step 10 demand）...")
    ratios = extract_path_ratios_from_csv(step1_mcfp_path)
    mcfp_step1_df = pd.read_csv(step1_mcfp_path)
    path_ratio_df = apply_path_ratios_to_demand(ratios, arrival_rates, mcfp_step1_df)
    path_ratio_util = calculate_max_link_utilization(path_ratio_df, step_config)
    path_ratio_commodities = path_ratio_df['id_flow'].nunique()
    print(f"  max_link_utilization = {path_ratio_util:.6f}%")
    print(f"  commodity 数: {path_ratio_commodities}")

    # 3) 与实验保存值对比
    print("\n【3】与实验保存值对比")
    print("-" * 70)
    s4_th4_path = os.path.join(base, 'strategy4_threshold_4', 'strategy4', 'strategy4_stats.csv')
    s4_th6_path = os.path.join(base, 'strategy4_threshold_6', 'strategy4', 'strategy4_stats.csv')

    if os.path.isfile(s4_th4_path):
        s4_th4 = pd.read_csv(s4_th4_path)
        row = s4_th4[s4_th4['step_id'] == step_id].iloc[0]
        util_th4 = float(row['max_link_utilization'])
        reopt_th4 = bool(row['reoptimized'])
        print(f"  θ=4 (step 10 重优化): max_util={util_th4:.6f}%, reoptimized={reopt_th4}")
    else:
        util_th4 = None
        print("  θ=4 数据不存在")

    if os.path.isfile(s4_th6_path):
        s4_th6 = pd.read_csv(s4_th6_path)
        row = s4_th6[s4_th6['step_id'] == step_id].iloc[0]
        util_th6 = float(row['max_link_utilization'])
        reopt_th6 = bool(row['reoptimized'])
        print(f"  θ=6 (step 10 沿用比例): max_util={util_th6:.6f}%, reoptimized={reopt_th6}")
    else:
        util_th6 = None
        print("  θ=6 数据不存在")

    print("\n  验证结论:")
    if best_util is not None and path_ratio_util is not None:
        if best_util <= path_ratio_util + 1e-4:
            print("  ✓ 最优解 max_util <= path-ratio max_util（符合预期）")
        else:
            print(f"  ⚠ 最优解 ({best_util:.4f}%) > path-ratio ({path_ratio_util:.4f}%)，存在异常")
    if commodities_in_result == num_commodities:
        print("  ✓ 无 commodity 被移除")
    print("=" * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())
