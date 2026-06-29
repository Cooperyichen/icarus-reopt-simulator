#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立验证 seed 20 和 seed 15 上 θ=4 的 Strategy 4 计算是否正确。

从零开始模拟 Strategy 4 逻辑，不依赖已保存的 reoptimized 决策，
独立计算 trigger 并做出 reoptimize 决策，与 strategy4_stats.csv 对比。
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
from main.multi_step_comparison_experiment import calculate_trigger_metric

SEQUENCE_DIR = 'long congested sequence'
THRESHOLD = 4
PRECISE_SOLVER_OPTIONS = {'eps_abs': 1e-8, 'eps_rel': 1e-8, 'max_iters': 500000}


def extract_dual_variables(config, arrival_rates, solver_options=None):
    """对给定 arrival_rates 运行优化器并提取对偶变量"""
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
    result_df = optimizer.solve_mcfp_path_formulation(
        demand_matrix, objective_type, mode,
        verbose=False, solver_options=solver_options
    )
    dual_vars = {}
    if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
        dual_vars = result_df.attrs['dual_variables']
    return dual_vars


def parse_arrival_rates(s):
    """从 CSV 的 arrival_rates 字符串解析为 list"""
    if isinstance(s, (list, np.ndarray)):
        return [float(x) for x in s]
    return [float(x.strip()) for x in str(s).strip('[]').split(',')]


def verify_seed(seed, max_steps=50):
    """独立模拟 θ=4 的 Strategy 4，与保存结果对比"""
    result_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    sequence_file = os.path.join(result_base, SEQUENCE_DIR, str(seed), 'arrival_rate_sequence_50_steps.csv')
    stats_file = os.path.join(result_base, SEQUENCE_DIR, str(seed),
                              f'strategy4_threshold_{THRESHOLD}', 'strategy4', 'strategy4_stats.csv')
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')

    if not os.path.exists(sequence_file):
        print(f"✗ seed {seed}: 序列文件不存在")
        return
    if not os.path.exists(stats_file):
        print(f"✗ seed {seed}: strategy4_stats 不存在")
        return

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    saved_df = pd.read_csv(stats_file)

    print(f"\n{'='*80}")
    print(f"Seed {seed}, θ={THRESHOLD}: 独立验证 (max_steps={max_steps})")
    print(f"{'='*80}\n")

    last_dual_variables = None
    last_demand = None
    mismatches = []

    for step_id in range(1, min(max_steps + 1, len(sequence) + 1)):
        arrival_rates = sequence[step_id - 1].tolist()
        saved_row = saved_df[saved_df['step_id'] == step_id].iloc[0]
        saved_reopt = str(saved_row['reoptimized']).strip().lower() in ('true', '1', 'yes')
        saved_trigger = saved_row['trigger_metric']
        if pd.isna(saved_trigger):
            saved_trigger = None
        else:
            saved_trigger = float(saved_trigger)

        # 独立计算
        if step_id == 1:
            computed_reopt = True
            computed_trigger = None
            last_dual_variables = extract_dual_variables(config, arrival_rates, PRECISE_SOLVER_OPTIONS)
            last_demand = arrival_rates.copy()
        else:
            if last_dual_variables is not None and last_demand is not None:
                computed_trigger = calculate_trigger_metric(last_dual_variables, arrival_rates, last_demand)
                computed_reopt = computed_trigger > THRESHOLD
                if computed_reopt:
                    last_dual_variables = extract_dual_variables(config, arrival_rates, PRECISE_SOLVER_OPTIONS)
                    last_demand = arrival_rates.copy()
            else:
                computed_trigger = None
                computed_reopt = True

        # 对比
        trigger_ok = (saved_trigger is None and computed_trigger is None) or \
                     (saved_trigger is not None and computed_trigger is not None and abs(saved_trigger - computed_trigger) < 1e-4)
        reopt_ok = saved_reopt == computed_reopt

        status = "✓" if (trigger_ok and reopt_ok) else "✗"
        if not (trigger_ok and reopt_ok):
            mismatches.append({
                'step': step_id,
                'saved_trigger': saved_trigger,
                'computed_trigger': computed_trigger,
                'saved_reopt': saved_reopt,
                'computed_reopt': computed_reopt,
            })

        trigger_str = f"{computed_trigger:.4f}" if computed_trigger is not None else "N/A"
        saved_trigger_str = f"{saved_trigger:.4f}" if saved_trigger is not None else "N/A"
        print(f"Step {step_id:2d}: {status} trigger={trigger_str} (saved={saved_trigger_str}) "
              f"reopt={computed_reopt} (saved={saved_reopt})")

    print(f"\n--- Seed {seed} 汇总 ---")
    if mismatches:
        print(f"✗ 发现 {len(mismatches)} 处不一致:")
        for m in mismatches:
            print(f"  Step {m['step']}: trigger 计算={m['computed_trigger']} vs 保存={m['saved_trigger']}, "
                  f"reopt 决策={m['computed_reopt']} vs 保存={m['saved_reopt']}")
    else:
        print(f"✓ 所有 {max_steps} 步的 trigger 与 reoptimized 决策与保存结果一致")
    return len(mismatches) == 0


def main():
    print("=" * 80)
    print("验证 seed 20 和 seed 15 上 θ=4 的 Strategy 4 计算")
    print("=" * 80)
    ok20 = verify_seed(20, max_steps=15)  # 先验证前15步（含关键 step 10-11）
    ok15 = verify_seed(15, max_steps=15)
    print("\n" + "=" * 80)
    if ok20 and ok15:
        print("✓ 验证通过：θ=4 的计算与保存结果一致")
    else:
        print("✗ 验证未通过：存在不一致，请检查")
    print("=" * 80)


if __name__ == '__main__':
    main()
