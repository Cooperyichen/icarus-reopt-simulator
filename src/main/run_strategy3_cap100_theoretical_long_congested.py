#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在 long congested sequence 上运行 Strategy 3 的容量约束 LP 变体（仅理论利用率，无仿真）。

排除 seed 3, 7, 12, 14, 42（其余 15 个可行 seed）。结果写入
  multi_step_comparison/long congested sequence/{seed}/strategy3_cap100_theoretical/

  python -m main.run_strategy3_cap100_theoretical_long_congested
  python -m main.run_strategy3_cap100_theoretical_long_congested --strict-optimal
"""

import sys
import os
import json
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_global_optimal_ratio_cap100_theoretical_only
from main.run_all_20seeds_precise import PRECISE_SOLVER_OPTIONS, STRICT_OPTIMAL_OPTIONS

SEQUENCE_DIR_NAME = 'long congested sequence'
EXCLUDE_SEEDS = {3, 7, 12, 14, 42}

# 与 PRECISE_SOLVER_OPTIONS 量级对齐的 CVXPY / ECOS 容差
DEFAULT_CVXPY_SOLVE_KW = {
    'abstol': 1e-8,
    'reltol': 1e-8,
    'max_iters': 500000,
}


def load_feasible_seeds():
    path = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME,
                        'feasible_long_congested_seeds_20.csv')
    if os.path.isfile(path):
        return pd.read_csv(path)['seed'].astype(int).tolist()
    return [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 19, 20, 21, 23, 42, 123, 1234]


def run_one_seed(seed, config, result_dir_base, solver_options, cvxpy_kw):
    long_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    sequence_file = os.path.join(long_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
    sequence_name = f"{SEQUENCE_DIR_NAME}/{seed}"
    run_base = os.path.join(result_dir_base, sequence_name)

    if not os.path.exists(sequence_file):
        print(f"✗ seed {seed}: 缺少序列文件")
        return {'seed': seed, 'feasible': None, 'error': 'missing_sequence'}

    sequence = pd.read_csv(sequence_file, index_col=0).values
    print("\n" + "=" * 80)
    print(f"Strategy 3 cap100 theoretical — seed {seed}")
    print("=" * 80)

    out_root = os.path.join(run_base, 'strategy3_cap100_theoretical')

    stats = execute_strategy_global_optimal_ratio_cap100_theoretical_only(
        sequence, config, run_base,
        solver_options=solver_options,
        cvxpy_solve_kwargs=cvxpy_kw,
        max_utilization_percent=100.0,
    )

    if stats:
        os.makedirs(out_root, exist_ok=True)
        df = pd.DataFrame(stats)
        if 'arrival_rates' in df.columns:
            df['arrival_rates'] = df['arrival_rates'].apply(
                lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
            )
        df.to_csv(os.path.join(out_root, 'strategy3_stats.csv'), index=False)
        print(f"✓ strategy3_stats.csv -> {out_root}")
        return {'seed': seed, 'feasible': True, 'error': '', 'cvxpy_status': 'optimal'}

    cvxpy_status = ''
    meta = os.path.join(out_root, 'run_infeasible.json')
    if os.path.isfile(meta):
        with open(meta, encoding='utf-8') as f:
            cvxpy_status = json.load(f).get('cvxpy_status', '')
    return {
        'seed': seed,
        'feasible': False,
        'error': 'lp_infeasible_or_failed',
        'cvxpy_status': cvxpy_status,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Strategy 3 LP cap 100% theoretical-only (15 seeds, excludes 3,7,12,14,42)'
    )
    parser.add_argument('--seeds', type=str, default=None, help='Override comma-separated seeds')
    parser.add_argument('--strict-optimal', action='store_true', help='Strict MCFP Step 1 (STRICT_OPTIMAL_OPTIONS)')
    args = parser.parse_args()

    if args.seeds:
        seeds = [int(s.strip()) for s in args.seeds.split(',')]
    else:
        seeds = [s for s in load_feasible_seeds() if s not in EXCLUDE_SEEDS]

    solver_opts = STRICT_OPTIMAL_OPTIONS if args.strict_optimal else PRECISE_SOLVER_OPTIONS
    cvxpy_kw = dict(DEFAULT_CVXPY_SOLVE_KW)

    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    config = load_yaml_file(config_file)

    vis_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(vis_dir, exist_ok=True)
    infeasible_rows = []
    ok_rows = []

    print("=" * 80)
    print(f"Seeds: {len(seeds)} (excluded {sorted(EXCLUDE_SEEDS)})")
    print("=" * 80)

    for i, seed in enumerate(seeds):
        print(f"\n[{i + 1}/{len(seeds)}]")
        r = run_one_seed(seed, config, result_dir_base, solver_opts, cvxpy_kw)
        if r['feasible'] is False:
            infeasible_rows.append({
                'seed': r['seed'],
                'note': r['error'],
                'cvxpy_status': r.get('cvxpy_status', ''),
            })
        elif r['feasible'] is True:
            ok_rows.append({'seed': r['seed']})

    inf_path = os.path.join(vis_dir, 'strategy3_cap100_theoretical_infeasible.csv')
    pd.DataFrame(infeasible_rows).to_csv(inf_path, index=False)
    print(f"\n✓ Infeasible / failed summary: {inf_path} ({len(infeasible_rows)} row(s))")

    ok_path = os.path.join(vis_dir, 'strategy3_cap100_theoretical_feasible_seeds.csv')
    pd.DataFrame(ok_rows).to_csv(ok_path, index=False)
    print(f"✓ Feasible seeds list: {ok_path} ({len(ok_rows)} row(s))")


if __name__ == '__main__':
    main()
