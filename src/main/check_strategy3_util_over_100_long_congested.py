#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检验 Strategy 3 在 long congested sequence（20 个可行 seed）上是否存在单步 link utilization 超过 100%。

检查 max_link_utilization（理论）与 max_link_utilization_actual（若存在）。

  python -m main.check_strategy3_util_over_100_long_congested

输出:
  - 终端醒目标记与逐条 (seed, step_id, theoretical, actual)
  - 可视化目录下 strategy3_infeasibility_report.csv（所有超限行）
  - strategy3_infeasibility_summary.csv（每 seed 摘要）
"""

import sys
import os
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
THRESHOLD = 100.0


def load_feasible_seeds():
    path = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME,
                        'feasible_long_congested_seeds_20.csv')
    if os.path.isfile(path):
        return pd.read_csv(path)['seed'].astype(int).tolist()
    return [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 19, 20, 21, 23, 42, 123, 1234]


def main():
    results_base_dir = os.path.join(src_dir, 'results', RESULTS_BASE)
    long_base = os.path.join(results_base_dir, SEQUENCE_DIR_NAME)
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)

    seeds = load_feasible_seeds()
    util_col = 'max_link_utilization'
    actual_col = 'max_link_utilization_actual'

    print("=" * 70)
    print("Strategy 3 — link utilization 超过 100% 检验（long congested, 20 seeds）")
    print("=" * 70)

    any_over_100 = False
    summary_rows = []
    detail_rows = []

    for seed in seeds:
        path = os.path.join(long_base, str(seed), 'strategy3', 'strategy3_stats.csv')
        if not os.path.isfile(path):
            print(f"\nseed {seed}: 缺少 strategy3_stats.csv，跳过")
            summary_rows.append({
                'seed': seed,
                'file_found': False,
                'max_theoretical': float('nan'),
                'max_actual': float('nan'),
                'any_step_over_100_theoretical': False,
                'any_step_over_100_actual': False,
                'num_steps_over_100_theoretical': 0,
                'num_steps_over_100_actual': 0,
            })
            continue

        df = pd.read_csv(path)
        max_util = df[util_col].max() if util_col in df.columns else float('nan')
        has_actual = actual_col in df.columns
        max_actual = df[actual_col].max() if has_actual else float('nan')

        over_th = df[df[util_col] > THRESHOLD] if util_col in df.columns else pd.DataFrame()
        over_act = df[df[actual_col] > THRESHOLD] if has_actual else pd.DataFrame()

        n_th = len(over_th)
        n_act = len(over_act)
        if n_th > 0 or n_act > 0:
            any_over_100 = True

        summary_rows.append({
            'seed': seed,
            'file_found': True,
            'max_theoretical': max_util,
            'max_actual': max_actual,
            'any_step_over_100_theoretical': n_th > 0,
            'any_step_over_100_actual': n_act > 0,
            'num_steps_over_100_theoretical': n_th,
            'num_steps_over_100_actual': n_act,
        })

        print(f"\nseed {seed}:")
        print(f"  理论最大利用率（逐步峰值）: {max_util:.4f}%")
        if has_actual:
            print(f"  实际最大利用率（逐步峰值）: {max_actual:.4f}%")
        if n_th > 0:
            for _, r in over_th.iterrows():
                sid = int(r['step_id'])
                th = float(r[util_col])
                ac = float(r[actual_col]) if has_actual else float('nan')
                detail_rows.append({
                    'seed': seed, 'step_id': sid,
                    'max_link_utilization': th,
                    'max_link_utilization_actual': ac,
                    'theoretical_over_100': True,
                    'actual_over_100': (ac > THRESHOLD) if has_actual and pd.notna(ac) else False,
                })
            steps_th = over_th['step_id'].astype(int).tolist()
            print(f"  ⚠ 理论 > 100%: {n_th} 步, step_id={steps_th}")
        else:
            print(f"  ✓ 理论利用率均 ≤ 100%")
        if has_actual:
            if n_act > 0:
                for _, r in over_act.iterrows():
                    sid = int(r['step_id'])
                    already = any(
                        d['seed'] == seed and d['step_id'] == sid for d in detail_rows
                    )
                    if not already:
                        detail_rows.append({
                            'seed': seed, 'step_id': sid,
                            'max_link_utilization': float(r[util_col]),
                            'max_link_utilization_actual': float(r[actual_col]),
                            'theoretical_over_100': False,
                            'actual_over_100': True,
                        })
                steps_act = over_act['step_id'].astype(int).tolist()
                print(f"  ⚠ 实际 > 100%: {n_act} 步, step_id={steps_act}")
            else:
                print(f"  ✓ 实际利用率均 ≤ 100%")

    summary_path = os.path.join(output_dir, 'strategy3_infeasibility_summary.csv')
    pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
    print(f"\n已保存摘要: {summary_path}")

    report_path = os.path.join(output_dir, 'strategy3_infeasibility_report.csv')
    if detail_rows:
        dfd = pd.DataFrame(detail_rows)
        dfd = dfd.drop_duplicates(subset=['seed', 'step_id'], keep='first')
        dfd.to_csv(report_path, index=False)
        print(f"已保存明细: {report_path}")
    else:
        pd.DataFrame(columns=[
            'seed', 'step_id', 'max_link_utilization', 'max_link_utilization_actual',
            'theoretical_over_100', 'actual_over_100',
        ]).to_csv(report_path, index=False)
        print(f"无超限行，已写入空表头: {report_path}")

    print("\n" + "=" * 70)
    if any_over_100:
        print("*** 结论: Strategy 3 在至少一个序列/步上出现 link utilization 超过 100% ***")
        print("*** 详见 strategy3_infeasibility_report.csv 与上文逐 seed 输出 ***")
    else:
        print("结论: 在已检查的 Strategy 3 结果中，未发现单步利用率超过 100%（或缺少 stats 文件）")
    print("=" * 70)


if __name__ == '__main__':
    main()
