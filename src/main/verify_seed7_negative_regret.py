#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
针对 seed 7 的负 regret 步做两种验证：
1) 验证方式一：重新跑 S1 求解器，检查 Solver status 是否为 optimal/optimal_inaccurate
2) 验证方式二：对比 S1 与 S4 的 max_link_utilization 数值，并重算 S1 验证保存值一致性

用法: 在 src 目录下运行
  python -m main.verify_seed7_negative_regret
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
from main.multi_step_comparison_experiment import calculate_max_link_utilization

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'results/multi_step_comparison'
SEED = 7
THETA = 8
UTIL_COL = 'max_link_utilization'


def find_negative_regret_steps(results_base_dir):
    """找出 seed 7 在 θ=8 下 regret 为负的步。"""
    s1_path = os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(SEED), 'strategy1', 'strategy1_stats.csv')
    s4_path = os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(SEED), 'strategy4', 'strategy4_stats.csv')
    if not os.path.isfile(s1_path) or not os.path.isfile(s4_path):
        return None, None, []
    s1_df = pd.read_csv(s1_path)
    s4_df = pd.read_csv(s4_path)
    m = s1_df[['step_id', UTIL_COL]].merge(
        s4_df[['step_id', UTIL_COL]],
        on='step_id', how='inner', suffixes=('_s1', '_s4')
    )
    m['instantaneous_regret'] = m[UTIL_COL + '_s4'] - m[UTIL_COL + '_s1']
    negative = m[m['instantaneous_regret'] < 0].sort_values('step_id')
    return s1_df, s4_df, negative


def run_s1_for_step(step_id, config, regen_obp, sequence, num_commodities, verbose=True):
    """对指定步运行 S1 优化器，返回 (mcfp_df, max_util) 或 (None, None)。"""
    arrival_rates = sequence[step_id - 1].tolist()
    step_config = config.copy()
    step_config['fixed_demand'] = config['fixed_demand'].copy()
    step_config['fixed_demand']['arrival_rate'] = arrival_rates
    step_config['simulation'] = config['simulation'].copy()
    step_config['simulation']['num_steps'] = 1
    regen_obp.scenario_config = step_config
    demand_matrix = regen_obp.generate_demand_matrix(num_commodities=num_commodities)
    if 'Infeasible' in demand_matrix.columns:
        demand_matrix['Infeasible'] = False

    optimizer = MultiCommodityOptimizer(step_config, regen_obp.graph, regen_obp.interlinks)
    objective_type = step_config['optimization']['objective_func']
    mode = step_config['simulation']['failure_strategy']

    result = optimizer.solve_mcfp_path_formulation(
        demand_matrix, objective_type, mode,
        skip_infeasible_fallback=False,  # 正常模式，不绕过 fallback
        verbose=verbose
    )
    if result is None or len(result) == 0:
        return None, None
    util = calculate_max_link_utilization(result, step_config)
    return result, util


def main():
    results_base_dir = os.path.join(src_dir, RESULTS_BASE)
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    sequence_file = os.path.join(results_base_dir, SEQUENCE_DIR_NAME, str(SEED), 'arrival_rate_sequence_50_steps.csv')
    out_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(out_dir, exist_ok=True)

    s1_df, s4_df, negative = find_negative_regret_steps(results_base_dir)
    if negative is None or len(negative) == 0:
        print("未找到 seed 7 的负 regret 步（θ=8）")
        return

    print("=" * 70)
    print(f"Seed 7 负 regret 步（θ={THETA}）: {list(negative['step_id'].astype(int).values)}")
    print("=" * 70)

    # ----- 验证方式二：对比 S1 与 S4 的 max_link_utilization -----
    print("\n【验证方式二】S1 vs S4 的 max_link_utilization 对比")
    print("-" * 70)
    rows = []
    for _, r in negative.iterrows():
        step_id = int(r['step_id'])
        j_full = float(r[UTIL_COL + '_s1'])
        j_event = float(r[UTIL_COL + '_s4'])
        diff = j_event - j_full  # 负值表示 J_event < J_full
        rows.append({
            'step_id': step_id,
            'J_full_S1': j_full,
            'J_event_S4': j_event,
            'instantaneous_regret': diff,
            'J_full_minus_J_event': j_full - j_event,  # 正值表示 S1 更高
        })
    df_v2 = pd.DataFrame(rows)
    print(df_v2.to_string(index=False))
    csv_v2 = os.path.join(out_dir, 'seed7_negative_regret_verification2.csv')
    df_v2.to_csv(csv_v2, index=False)
    print(f"\n已保存: {csv_v2}")

    # ----- 验证方式一：重新跑 S1 求解器，检查 Solver status -----
    check_step = int(negative.iloc[0]['step_id'])  # 取第一个负 regret 步
    print("\n【验证方式一】重新运行 S1 求解器，检查 Solver status")
    print("-" * 70)
    print(f"选取 step {check_step} 进行验证。下方将输出求解器日志，请留意 'Solver status:' 或 'Default solver status:'。\n")

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    num_commodities = sequence.shape[1]
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)

    mcfp_df, util_recomputed = run_s1_for_step(
        check_step, config, regen_obp, sequence, num_commodities, verbose=True
    )

    print("\n" + "=" * 70)
    print("验证方式一结果")
    print("=" * 70)
    if mcfp_df is not None:
        print(f"Step {check_step} 重算 max_link_utilization: {util_recomputed:.4f}%")
        util_s1_saved = float(s1_df[s1_df['step_id'] == check_step][UTIL_COL].iloc[0])
        util_s4 = float(s4_df[s4_df['step_id'] == check_step][UTIL_COL].iloc[0])
        print(f"strategy1_stats 保存值: {util_s1_saved:.4f}%")
        print(f"strategy4_stats 保存值: {util_s4:.4f}%")
        if abs(util_recomputed - util_s1_saved) < 1e-4:
            print("  ✓ 重算与 S1 保存值一致")
        else:
            print(f"  ⚠ 重算与 S1 保存值差 {abs(util_recomputed - util_s1_saved):.6f}%")
        if util_s1_saved > util_s4:
            print(f"  → J_full > J_event，该步存在负 regret（差 {util_s1_saved - util_s4:.4f}%）")
    else:
        print("✗ 求解器未返回有效解")

    # 对剩余负 regret 步做静默重算，检查重算值与保存值一致性
    print("\n【验证方式二补充】对其余负 regret 步静默重算 S1，检查保存值一致性")
    print("-" * 70)
    for _, r in negative.iterrows():
        step_id = int(r['step_id'])
        if step_id == check_step:
            continue
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                import warnings
                with warnings.catch_warnings(action='ignore'):
                    _, util_recomp = run_s1_for_step(
                        step_id, config, regen_obp, sequence, num_commodities, verbose=False
                    )
            except Exception:
                util_recomp = None
        util_saved = float(r[UTIL_COL + '_s1'])
        if util_recomp is not None:
            ok = abs(util_recomp - util_saved) < 1e-4
            print(f"  step {step_id}: 重算={util_recomp:.4f}%, 保存={util_saved:.4f}% {'✓' if ok else '⚠ 不一致'}")
        else:
            print(f"  step {step_id}: 重算失败")

    print("\n" + "=" * 70)
    print("请根据上方求解器输出中的 Solver status 判断验证方式一：")
    print("  - 若为 optimal 或 optimal_inaccurate，则 S1 在该步达到（近似）最优；")
    print("  - 若 J_full > J_event 仍成立，可能为多解或数值精度导致。")
    print("=" * 70)


if __name__ == '__main__':
    main()
