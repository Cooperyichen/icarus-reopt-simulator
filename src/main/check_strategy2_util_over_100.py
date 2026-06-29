#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检验 Strategy 2 在 long congested sequence 的 6 个序列上，是否存在 link utilization 超过 100% 的步。
检查 max_link_utilization（理论）与 max_link_utilization_actual（实际仿真）两列。
"""

import sys
import os
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEEDS = [0, 1, 7, 42, 123, 1234]
SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
THRESHOLD = 100.0


def main():
    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    long_base = os.path.join(results_base_dir, SEQUENCE_DIR_NAME)

    print("=" * 70)
    print("Strategy 2 link utilization 超过 100% 检验（long congested sequence）")
    print("=" * 70)

    any_over_100 = False
    summary_rows = []

    for seed in SEEDS:
        path = os.path.join(long_base, str(seed), 'strategy2', 'strategy2_stats.csv')
        if not os.path.isfile(path):
            print(f"\nseed {seed}: 缺少 strategy2_stats.csv，跳过")
            continue

        df = pd.read_csv(path)
        util_col = 'max_link_utilization'
        actual_col = 'max_link_utilization_actual' if 'max_link_utilization_actual' in df.columns else None

        over_theoretical = df[df[util_col] > THRESHOLD] if util_col in df.columns else pd.DataFrame()
        over_actual = df[df[actual_col] > THRESHOLD] if actual_col and actual_col in df.columns else pd.DataFrame()

        max_util = df[util_col].max() if util_col in df.columns else float('nan')
        max_actual = df[actual_col].max() if actual_col and actual_col in df.columns else float('nan')

        n_over_th = len(over_theoretical)
        n_over_act = len(over_actual)

        if n_over_th > 0 or n_over_act > 0:
            any_over_100 = True

        summary_rows.append({
            'seed': seed,
            'max_theoretical': max_util,
            'max_actual': max_actual,
            'steps_over_100_theoretical': n_over_th,
            'steps_over_100_actual': n_over_act,
        })

        print(f"\nseed {seed}:")
        print(f"  理论最大利用率: {max_util:.2f}% (峰值)")
        print(f"  实际最大利用率: {max_actual:.2f}% (峰值)")
        if n_over_th > 0:
            steps_th = over_theoretical['step_id'].tolist()
            print(f"  ⚠ 理论 > 100% 的步数: {n_over_th}/50, 步号: {steps_th}")
        else:
            print(f"  ✓ 理论利用率均 ≤ 100%")
        if actual_col:
            if n_over_act > 0:
                steps_act = over_actual['step_id'].tolist()
                print(f"  ⚠ 实际 > 100% 的步数: {n_over_act}/50, 步号: {steps_act}")
            else:
                print(f"  ✓ 实际利用率均 ≤ 100%")

    print("\n" + "=" * 70)
    if any_over_100:
        print("结论: Strategy 2 在部分步出现 link utilization 超过 100% 的情况")
    else:
        print("结论: Strategy 2 在这 6 个序列上 link utilization 均未超过 100%")
    print("=" * 70)


if __name__ == '__main__':
    main()
