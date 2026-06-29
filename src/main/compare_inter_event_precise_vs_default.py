#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比「精确求解」与「默认求解器」下的 inter-event time 是否发生变化。

使用默认求解器运行 S4 (seed 7, θ=8) 到 baseline 目录，与当前精确求解结果对比。
"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_adaptive_reoptimization

SEED = 7
THETA = 8


def _is_reoptimized(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'yes')
    return bool(value)


def get_reopt_steps_and_dt(stats_path):
    """从 strategy4_stats.csv 读取 reopt 步和 inter-event times。"""
    if not os.path.isfile(stats_path):
        return None, None
    df = pd.read_csv(stats_path)
    reopt = df['reoptimized'].apply(_is_reoptimized)
    steps = sorted(df.loc[reopt, 'step_id'].astype(int).tolist())
    dt = [steps[i + 1] - steps[i] for i in range(len(steps) - 1)] if len(steps) >= 2 else []
    return steps, dt


def main():
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    multi_step_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    baseline_base = os.path.join(src_dir, 'results', 'multi_step_comparison_baseline')
    sequence_name = f'long congested sequence/{SEED}'
    sequence_file = os.path.join(multi_step_base, sequence_name, 'arrival_rate_sequence_50_steps.csv')

    if not os.path.exists(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return

    precise_path = os.path.join(multi_step_base, sequence_name, 'strategy4', 'strategy4_stats.csv')
    steps_precise, dt_precise = get_reopt_steps_and_dt(precise_path)

    if steps_precise is None:
        print("✗ 未找到精确求解的 strategy4_stats.csv")
        return

    print("=" * 60)
    print("对比 Inter-Event Time：精确求解 vs 默认求解器")
    print("=" * 60)
    print(f"\n【精确求解】seed={SEED}, θ={THETA}")
    print(f"  reopt 步: {steps_precise}")
    print(f"  Δt: {dt_precise}")

    # 运行默认求解器
    run_base = os.path.join(baseline_base, sequence_name)
    print(f"\n使用默认求解器运行 S4 (seed={SEED}, θ={THETA}) 到 {run_base}...")
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values

    strategy_stats = execute_strategy_adaptive_reoptimization(
        sequence, config, run_base, threshold=THETA, solver_options=None
    )
    strategy_dir = os.path.join(run_base, 'strategy4')
    os.makedirs(strategy_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    stats_path = os.path.join(strategy_dir, 'strategy4_stats.csv')
    df.to_csv(stats_path, index=False)

    steps_default, dt_default = get_reopt_steps_and_dt(stats_path)
    print(f"\n【默认求解器】seed={SEED}, θ={THETA}")
    print(f"  reopt 步: {steps_default}")
    print(f"  Δt: {dt_default}")

    # 对比
    print("\n" + "=" * 60)
    print("对比结果")
    print("=" * 60)
    if steps_precise == steps_default:
        print("✓ reopt 步完全相同，inter-event time 未发生变化")
    else:
        print("⚠ reopt 步不同，inter-event time 发生了变化")
        print(f"  精确求解 reopt: {steps_precise}")
        print(f"  默认求解 reopt: {steps_default}")
        diff = set(steps_precise) ^ set(steps_default)
        print(f"  差异步: {sorted(diff)}")

    if dt_precise != dt_default:
        print(f"\n  Δt 精确: {dt_precise}")
        print(f"  Δt 默认: {dt_default}")


if __name__ == '__main__':
    main()
