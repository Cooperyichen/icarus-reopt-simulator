#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调查 step 10 附近时间步上 S1 策略求解得到的对偶变量，检查是否发生剧烈变化。

对 seed 20 和 seed 15，在 steps 7-15 上独立运行 S1 的优化器，提取 demand 对偶变量，
并输出表格和简要分析。
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

SEQUENCE_DIR = 'long congested sequence'
PRECISE_SOLVER_OPTIONS = {'eps_abs': 1e-8, 'eps_rel': 1e-8, 'max_iters': 500000}
STRICT_OPTIMAL_OPTIONS = {**PRECISE_SOLVER_OPTIONS, 'require_optimal_strict': True}


def extract_dual_variables_and_util(config, arrival_rates, solver_options=None):
    """对给定 arrival_rates 运行优化器并提取 demand 对偶变量及 max_link_utilization"""
    from main.multi_step_comparison_experiment import calculate_max_link_utilization
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
    max_util = np.nan
    if result_df is not None and len(result_df) > 0:
        if hasattr(result_df, 'attrs') and 'dual_variables' in result_df.attrs:
            dual_vars = result_df.attrs['dual_variables']
        max_util = calculate_max_link_utilization(result_df, step_config)
    return dual_vars, max_util


def investigate_seed(seed, steps_range=(7, 16), solver_options=None):
    """对指定 seed 在 steps_range 内提取对偶变量及 S4 θ=4 的 pli/delay 等"""
    opts = solver_options or STRICT_OPTIMAL_OPTIONS
    result_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    sequence_file = os.path.join(result_base, SEQUENCE_DIR, str(seed), 'arrival_rate_sequence_50_steps.csv')
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    s1_stats_file = os.path.join(result_base, SEQUENCE_DIR, str(seed), 'strategy1', 'strategy1_stats.csv')
    s4_th4_stats_file = os.path.join(result_base, SEQUENCE_DIR, str(seed),
                                     'strategy4_threshold_4', 'strategy4', 'strategy4_stats.csv')

    if not os.path.exists(sequence_file):
        print(f"✗ seed {seed}: 序列文件不存在")
        return None

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    s1_df = pd.read_csv(s1_stats_file) if os.path.exists(s1_stats_file) else None
    s4_th4_df = pd.read_csv(s4_th4_stats_file) if os.path.exists(s4_th4_stats_file) else None

    rows = []
    for step_id in range(steps_range[0], steps_range[1]):
        arrival_rates = sequence[step_id - 1].tolist()
        dual_vars, max_util_opt = extract_dual_variables_and_util(config, arrival_rates, opts)
        row = {'step_id': step_id, 'arrival_rates': str([f'{x:.1f}' for x in arrival_rates])}
        for i in range(4):
            row[f'dual_{i}'] = dual_vars.get(i, np.nan)
            if row[f'dual_{i}'] is None:
                row[f'dual_{i}'] = np.nan
        row['max_util_from_optimizer'] = max_util_opt
        if s1_df is not None:
            s1_row = s1_df[s1_df['step_id'] == step_id]
            if len(s1_row) > 0:
                row['max_util_s1'] = float(s1_row.iloc[0]['max_link_utilization'])
        if s4_th4_df is not None:
            s4_row = s4_th4_df[s4_th4_df['step_id'] == step_id]
            if len(s4_row) > 0:
                r = s4_row.iloc[0]
                row['max_util_s4_th4'] = float(r['max_link_utilization'])
                row['pli_s4_th4'] = float(r['pli'])
                row['avg_delay_s4_th4'] = float(r['avg_delay'])
                row['reoptimized_s4_th4'] = bool(r['reoptimized']) if 'reoptimized' in r else np.nan
        rows.append(row)

    return pd.DataFrame(rows)


def main():
    print("=" * 80)
    print("调查 step 10 附近对偶变量变化 (STRICT_OPTIMAL_OPTIONS)")
    print("=" * 80)

    for seed in [20, 15, 14]:
        print(f"\n{'='*60}")
        print(f"Seed {seed}")
        print(f"{'='*60}")
        df = investigate_seed(seed, steps_range=(7, 16))
        if df is None:
            continue

        # 打印表格
        print("\n对偶变量 (demand constraints, λ_i) 及 S4 θ=4 指标:")
        print("-" * 100)
        dual_cols = [c for c in df.columns if c.startswith('dual_')]
        header = "Step  " + "  ".join([f"λ_{i:8}" for i in range(4)]) + "  max_util_opt  max_util_s4  pli_s4  delay_s4  reopt"
        print(header)
        print("-" * 100)
        for _, r in df.iterrows():
            duals = [r[c] for c in dual_cols]
            dual_str = "  ".join([f"{x:.4e}" if not np.isnan(x) else "   N/A  " for x in duals])
            u_opt = r.get('max_util_from_optimizer', np.nan)
            u_s4 = r.get('max_util_s4_th4', np.nan)
            pli = r.get('pli_s4_th4', np.nan)
            delay = r.get('avg_delay_s4_th4', np.nan)
            reopt = r.get('reoptimized_s4_th4', np.nan)
            u_opt_str = f"{u_opt:.2f}%" if not np.isnan(u_opt) else "N/A"
            u_s4_str = f"{u_s4:.2f}%" if not np.isnan(u_s4) else "N/A"
            pli_str = f"{pli:.2f}%" if not np.isnan(pli) else "N/A"
            delay_str = f"{delay:.4f}s" if not np.isnan(delay) else "N/A"
            reopt_str = str(reopt) if not (isinstance(reopt, float) and np.isnan(reopt)) else "N/A"
            print(f"  {int(r['step_id']):2d}   {dual_str}  {u_opt_str:>8}  {u_s4_str:>8}  {pli_str:>6}  {delay_str:>8}  {reopt_str}")
        print("-" * 100)

        # 分析变化
        dual_cols = [f'dual_{i}' for i in range(4)]
        vals = df[dual_cols].values
        step_ids = df['step_id'].values
        print("\n变化分析:")
        for i in range(len(step_ids) - 1):
            s_curr, s_next = int(step_ids[i]), int(step_ids[i + 1])
            curr = vals[i]
            nxt = vals[i + 1]
            ratios = []
            for j in range(4):
                if not (np.isnan(curr[j]) or np.isnan(nxt[j]) or curr[j] == 0):
                    r = nxt[j] / curr[j]
                    ratios.append(r)
            if ratios:
                mean_r = np.mean(ratios)
                max_r = max(ratios)
                min_r = min(ratios)
                flag = " <<< 剧烈变化" if (max_r > 2 or min_r < 0.5) else ""
                print(f"  Step {s_curr} → {s_next}: 比值 mean={mean_r:.3f}, min={min_r:.3f}, max={max_r:.3f}{flag}")

    # 保存 CSV
    out_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR)
    os.makedirs(out_dir, exist_ok=True)
    for seed in [20, 15, 14]:
        df = investigate_seed(seed, steps_range=(7, 16))
        if df is not None:
            path = os.path.join(out_dir, f'dual_variables_around_step10_seed{seed}.csv')
            df.to_csv(path, index=False)
            print(f"\n✓ 已保存: {path}")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
