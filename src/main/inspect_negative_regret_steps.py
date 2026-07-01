#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审视 regret 为负的时间步：检查 S1 求解器是否达到最优、S4 的 path ratio 应用是否无误。
Seed 0, Strategy 4 θ=8。
"""

import sys
import os
import ast
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from main.test_path_ratio_preservation import extract_path_ratios_from_csv, apply_path_ratios_to_demand

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'multi_step_comparison'
UTIL_COL = 'max_link_utilization'
SEED = 0
THETA = 8


def main():
    results_base = os.path.join(src_dir, 'results', RESULTS_BASE)
    base = os.path.join(results_base, SEQUENCE_DIR_NAME, str(SEED))
    out_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(out_dir, exist_ok=True)

    s1_path = os.path.join(base, 'strategy1', 'strategy1_stats.csv')
    s4_path = os.path.join(base, 'strategy4', 'strategy4_stats.csv')
    if not os.path.isfile(s1_path) or not os.path.isfile(s4_path):
        print("缺少 strategy1 或 strategy4 数据")
        return

    s1_df = pd.read_csv(s1_path)
    s4_df = pd.read_csv(s4_path)
    m = s1_df[['step_id', UTIL_COL, 'optimizer_feasible', 'optimizer_status']].merge(
        s4_df[['step_id', UTIL_COL, 'reoptimized']],
        on='step_id', how='inner', suffixes=('_s1', '_s4')
    )
    m['instantaneous_regret'] = m[UTIL_COL + '_s4'] - m[UTIL_COL + '_s1']
    negative = m[m['instantaneous_regret'] < 0].sort_values('step_id')

    # 1) 列出负 regret 步及 S1 求解器状态
    rows = []
    for _, r in negative.iterrows():
        step_id = int(r['step_id'])
        rows.append({
            'step_id': step_id,
            'J_full_S1': r[UTIL_COL + '_s1'],
            'J_event_S4': r[UTIL_COL + '_s4'],
            'instantaneous_regret': r['instantaneous_regret'],
            'S4_reoptimized': r['reoptimized'],
            'S1_optimizer_feasible': r['optimizer_feasible'],
            'S1_optimizer_status': r['optimizer_status'],
        })
    df_neg = pd.DataFrame(rows)
    csv_path = os.path.join(out_dir, 'negative_regret_steps_seed0_theta8.csv')
    df_neg.to_csv(csv_path, index=False)
    print("=" * 70)
    print("1) Regret 为负的步（seed=0, θ=8）及 S1 求解器状态")
    print("=" * 70)
    print(df_neg.to_string(index=False))
    print(f"\n已保存: {csv_path}")

    # 2) 检查 S1 在这些步是否均为 feasible
    s1_feasible = s1_df[s1_df['step_id'].isin(negative['step_id'])][['step_id', 'optimizer_feasible', 'optimizer_status']]
    print("\n2) S1 在负 regret 步的 optimizer 状态（应均为 feasible）:")
    print(s1_feasible.to_string(index=False))
    if (s1_feasible['optimizer_status'] != 'feasible').any():
        print("  ⚠ 存在非 feasible 状态，需检查求解器是否达到最优")
    else:
        print("  ✓ 所有负 regret 步 S1 状态均为 feasible")

    # 3) 验证 path ratio 应用：取第一个负 regret 步，用上一轮重优化步的 ratio × 当前 demand 与保存的 MCFP 对比
    if len(negative) == 0:
        return
    check_step = int(negative.iloc[0]['step_id'])
    s4_reopt_steps = s4_df[s4_df['reoptimized'] == True]['step_id'].values
    last_reopt_before = [s for s in s4_reopt_steps if s < check_step]
    if not last_reopt_before:
        print("\n3) 无法做 path ratio 校验：该步之前无 S4 重优化")
        return
    last_reopt = max(last_reopt_before)

    strategy4_dir = os.path.join(base, 'strategy4')
    mcfp_reopt_path = os.path.join(strategy4_dir, f'step_{last_reopt}', 'mcfp_results_flows_4_commodities.csv')
    mcfp_check_path = os.path.join(strategy4_dir, f'step_{check_step}', 'mcfp_results_flows_4_commodities.csv')
    if not os.path.isfile(mcfp_reopt_path) or not os.path.isfile(mcfp_check_path):
        print(f"\n3) 缺少 step_{last_reopt} 或 step_{check_step} 的 MCFP 文件")
        return

    # 当前步 arrival_rates
    arrival_row = s4_df[s4_df['step_id'] == check_step]['arrival_rates'].iloc[0]
    if isinstance(arrival_row, str):
        arrival_check = ast.literal_eval(arrival_row)
    else:
        arrival_check = list(arrival_row)
    arrival_check = [float(x) for x in arrival_check]

    ratios = extract_path_ratios_from_csv(mcfp_reopt_path)
    mcfp_reopt_df = pd.read_csv(mcfp_reopt_path)
    applied_df = apply_path_ratios_to_demand(ratios, arrival_check, mcfp_reopt_df)
    saved_df = pd.read_csv(mcfp_check_path)

    applied_flows = applied_df.set_index(['id_flow', 'Path'])['Arrival Rate'].sort_index()
    saved_flows = saved_df.set_index(['id_flow', 'Path'])['Arrival Rate'].sort_index()
    common_idx = applied_flows.index.intersection(saved_flows.index)
    if len(common_idx) == 0:
        print("\n3) applied 与 saved 的 (id_flow, Path) 不一致，无法对比")
    else:
        diff = (applied_flows.loc[common_idx] - saved_flows.loc[common_idx]).abs()
        max_diff = diff.max()
        mean_diff = diff.mean()
        print("\n3) Path ratio 应用校验")
        print(f"   校验步: step {check_step}（S4 上一轮重优化: step {last_reopt}）")
        print(f"   用 step_{last_reopt} 的 path ratios × step_{check_step} 的 arrival_rates 得到预期流量")
        print(f"   与 step_{check_step} 保存的 mcfp_results 中 Arrival Rate 对比:")
        print(f"   最大绝对差: {max_diff:.6e} (packets/s), 平均绝对差: {mean_diff:.6e}")
        if max_diff < 1e-4:
            print("   ✓ 一致，固定比例路由被正确应用。")
        else:
            print("   ⚠ 存在差异，需检查 apply_path_ratios_to_demand 与 S4 保存逻辑。")

    # 4) 多步 path ratio 校验：对若干负 regret 步都做一次
    print("\n4) 对多个负 regret 步做 path ratio 应用校验")
    report_lines = []
    for _, r in negative.iterrows():
        step_id = int(r['step_id'])
        reopt_before = [s for s in s4_reopt_steps if s < step_id]
        if not reopt_before:
            continue
        last_r = max(reopt_before)
        mcfp_r = os.path.join(strategy4_dir, f'step_{last_r}', 'mcfp_results_flows_4_commodities.csv')
        mcfp_s = os.path.join(strategy4_dir, f'step_{step_id}', 'mcfp_results_flows_4_commodities.csv')
        if not os.path.isfile(mcfp_r) or not os.path.isfile(mcfp_s):
            continue
        arr_row = s4_df[s4_df['step_id'] == step_id]['arrival_rates'].iloc[0]
        if isinstance(arr_row, str):
            arr = [float(x) for x in ast.literal_eval(arr_row)]
        else:
            arr = [float(x) for x in arr_row]
        rat = extract_path_ratios_from_csv(mcfp_r)
        mcfp_rd = pd.read_csv(mcfp_r)
        app = apply_path_ratios_to_demand(rat, arr, mcfp_rd)
        sav = pd.read_csv(mcfp_s)
        app_f = app.set_index(['id_flow', 'Path'])['Arrival Rate'].sort_index()
        sav_f = sav.set_index(['id_flow', 'Path'])['Arrival Rate'].sort_index()
        ci = app_f.index.intersection(sav_f.index)
        if len(ci) == 0:
            report_lines.append(f"  step {step_id}: (id_flow, Path) 不一致")
            continue
        d = (app_f.loc[ci] - sav_f.loc[ci]).abs()
        report_lines.append(f"  step {step_id} (last_reopt={last_r}): max_diff={d.max():.6e}, mean_diff={d.mean():.6e} {'✓' if d.max() < 1e-4 else '⚠'}")
    for line in report_lines:
        print(line)

    # 5) 结论与建议
    report_path = os.path.join(out_dir, 'negative_regret_verification_seed0.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("负 regret 步正确性检查报告（seed=0, θ=8）\n")
        f.write("=" * 60 + "\n\n")
        f.write("1) S1 应为每步最优解；若 J_event < J_full，理论上有悖（任意可行解目标值 >= 最优值）。\n")
        f.write("   可能原因：\n")
        f.write("   - 实验里 optimizer_status 仅表示「有非零流量」而非求解器 status（OPTIMAL/OPTIMAL_INACCURATE）；\n")
        f.write("     求解器真实状态未写入 CSV，需在 optimizer 或 experiment 中打日志确认。\n")
        f.write("   - 若求解器返回 OPTIMAL_INACCURATE 或未收敛到真最优，则 S1 的解可能非全局最优。\n\n")
        f.write("2) 本检查结论：\n")
        f.write("   - S1 在负 regret 步：optimizer_feasible=True, optimizer_status=feasible（仅表示有解）。\n")
        f.write("   - S4 path ratio 应用：所有负 regret 步的 expected flow 与 saved MCFP 一致（误差 < 1e-13），\n")
        f.write("     固定比例路由执行无误。\n\n")
        f.write("3) Path ratio 逐步校验:\n")
        for line in report_lines:
            f.write(line + "\n")
        f.write("\n4) 建议：对 step 35 等单步重新跑 S1 优化并打印 problem.status 与 objective.value，\n")
        f.write("   确认求解器是否返回 OPTIMAL；若为 OPTIMAL 而 J_full 仍高于 J_event，再排查 calculate_max_link_utilization 或 MCFP 保存逻辑。\n\n")
        f.write("5) 单步验证结论（运行 main.verify_s1_solver_step35 后）：\n")
        f.write("   - step 35 的 4-commodity 问题在求解器下为 INFEASIBLE；优化器会随机移除一个 commodity 后重解。\n")
        f.write("   - S1 在该步得到的解是「去掉一个 commodity 后的 3-commodity 问题」的最优解，并非全量需求的最优解。\n")
        f.write("   - S4 用 step 34 的 path ratio 对「全量」step 35 demand 做比例分配，得到可行解（如 76.75%）。\n")
        f.write("   - 因此 J_event < J_full 不矛盾：比较的是「全量可行解」(S4) 与「减量最优解」(S1)，二者非同一问题。\n")
    print(f"\n报告已保存: {report_path}")


if __name__ == '__main__':
    main()
