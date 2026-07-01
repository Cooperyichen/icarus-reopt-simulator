#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确求解指定步的 MCFP 最优解，并与 path-ratio（S4）结果对比。

预期：最优解的 max_link_utilization <= path-ratio 解的 max_link_utilization。
若 path-ratio 更低，说明默认求解器返回了次优解。

用法: 在 src 目录下运行
  python -m main.precise_solve_and_compare_path_ratio --seed 7 --step 11
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
THETA = 8


def get_last_reopt_step_before(s4_stats_df, step_id):
    """获取 step_id 之前 S4 最后一次重优化的步。"""
    reopt = s4_stats_df[s4_stats_df['reoptimized'] == True]['step_id'].values
    before = [s for s in reopt if s < step_id]
    return max(before) if before else None


def solve_with_options(optimizer, demand_matrix, objective_type, mode, options_list, verbose=False):
    """
    依次用不同 solver 选项尝试求解，返回第一个成功解的 (df, status_str)。
    """
    for opts in options_list:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                import warnings
                with warnings.catch_warnings(action='ignore'):
                    result = optimizer.solve_mcfp_path_formulation(
                        demand_matrix, objective_type, mode,
                        skip_infeasible_fallback=True,
                        verbose=False,
                        solver_options=opts
                    )
            except Exception as e:
                if verbose:
                    print(f"  选项 {opts} 失败: {e}")
                continue
        if result is not None and len(result) > 0 and result['Arrival Rate'].sum() > 1e-6:
            status_str = opts.get('_label', str(opts))
            return result, status_str
    return None, None


def main():
    parser = argparse.ArgumentParser(description='Precise solve and compare with path-ratio')
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--step', type=int, default=11)
    parser.add_argument('--verbose', action='store_true', help='Print solver output')
    args = parser.parse_args()

    seed, step_id = args.seed, args.step
    results_base = os.path.join(src_dir, RESULTS_BASE)
    base = os.path.join(results_base, SEQUENCE_DIR_NAME, str(seed))
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    sequence_file = os.path.join(base, 'arrival_rate_sequence_50_steps.csv')

    if not os.path.isfile(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return
    if not os.path.isfile(config_file):
        print(f"✗ 配置文件不存在: {config_file}")
        return

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    num_commodities = sequence.shape[1]

    if step_id < 1 or step_id > sequence.shape[0]:
        print(f"✗ step {step_id} 超出范围")
        return

    # 加载 S4 统计，确定 path-ratio 来源步
    s4_path = os.path.join(base, 'strategy4', 'strategy4_stats.csv')
    if not os.path.isfile(s4_path):
        print(f"✗ 缺少 strategy4_stats: {s4_path}")
        return
    s4_df = pd.read_csv(s4_path)
    last_reopt = get_last_reopt_step_before(s4_df, step_id)
    if last_reopt is None:
        print(f"✗ step {step_id} 之前无 S4 重优化步")
        return

    mcfp_reopt_path = os.path.join(base, 'strategy4', f'step_{last_reopt}', 'mcfp_results_flows_4_commodities.csv')
    if not os.path.isfile(mcfp_reopt_path):
        print(f"✗ 缺少 step_{last_reopt} 的 MCFP: {mcfp_reopt_path}")
        return

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

    # 高精度求解选项：ECOS 通常收敛更准，SCS 提高 max_iters 和收紧 eps
    precise_options = [
        {'_label': 'ECOS (abstol=1e-9, reltol=1e-9)', 'abstol': 1e-9, 'reltol': 1e-9},
        {'_label': 'ECOS (abstol=1e-8)', 'abstol': 1e-8, 'reltol': 1e-8},
        {'_label': 'SCS (max_iters=500000, eps_abs=1e-8)', 'max_iters': 500000, 'eps_abs': 1e-8, 'eps_rel': 1e-8},
        {'_label': 'SCS (max_iters=200000)', 'max_iters': 200000, 'eps_abs': 1e-7, 'eps_rel': 1e-7},
    ]

    print("=" * 70)
    print(f"精确求解 step {step_id} (seed={seed})，并与 path-ratio 对比")
    print("=" * 70)
    print(f"Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
    print(f"Path-ratio 来源: step {last_reopt} (S4 上一轮重优化)")
    print()

    # 1) 精确求解
    print("【1】高精度求解 MCFP...")
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
        print("  ✗ 所有高精度选项均未得到有效解")
        return

    print(f"  ✓ 最优: {best_label}, max_link_utilization = {best_util:.6f}%")

    # 2) Path-ratio 解
    print("\n【2】Path-ratio 解（S4 在 step {0} 的 ratio × step {1} 的 demand）...".format(last_reopt, step_id))
    ratios = extract_path_ratios_from_csv(mcfp_reopt_path)
    mcfp_reopt_df = pd.read_csv(mcfp_reopt_path)
    path_ratio_df = apply_path_ratios_to_demand(ratios, arrival_rates, mcfp_reopt_df)
    path_ratio_util = calculate_max_link_utilization(path_ratio_df, step_config)
    print(f"  max_link_utilization = {path_ratio_util:.6f}%")

    # 3) 对比
    print("\n【3】对比结果")
    print("-" * 70)
    s1_df = pd.read_csv(os.path.join(base, 'strategy1', 'strategy1_stats.csv'))
    util_s1 = float(s1_df[s1_df['step_id'] == step_id]['max_link_utilization'].iloc[0])
    util_s4 = float(s4_df[s4_df['step_id'] == step_id]['max_link_utilization'].iloc[0])

    print(f"  精确求解最优值:     {best_util:.6f}%")
    print(f"  Path-ratio (S4):    {path_ratio_util:.6f}%")
    print(f"  S1 实验保存值:       {util_s1:.6f}%")
    print(f"  S4 实验保存值:       {util_s4:.6f}%")

    print("\n  预期: 最优 <= path-ratio <= 任意可行解")
    if best_util <= path_ratio_util + 1e-4:
        print("  ✓ 符合预期：精确最优 <= path-ratio")
    else:
        print(f"  ⚠ 异常：精确最优 ({best_util:.4f}%) > path-ratio ({path_ratio_util:.4f}%)")

    if util_s1 > path_ratio_util + 1e-4:
        print(f"  → S1 实验值 ({util_s1:.4f}%) > path-ratio ({path_ratio_util:.4f}%)，说明默认求解器返回了次优解")
    if best_util < util_s1 - 1e-4:
        print(f"  → 精确最优 ({best_util:.4f}%) < S1 实验值 ({util_s1:.4f}%)，验证了求解器精度不足")

    print("=" * 70)


if __name__ == '__main__':
    main()
