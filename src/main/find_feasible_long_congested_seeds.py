#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过不同随机种子筛选出 20 个 long congested 序列，要求精确求解时每步均可行（无 infeasible）。

策略：
1. 使用默认（较快）求解器筛查，若某步 infeasible 则丢弃该序列
2. 保留 seeds 7, 42, 123, 1234（已知可行）
3. 从候选种子中筛选出额外 16 个全可行序列

用法（在 src 目录下）:
  python -m main.find_feasible_long_congested_seeds
"""

import sys
import os
import io
import contextlib
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore', message='Solution may be inaccurate', category=UserWarning)

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from main.generate_arrival_rate_sequence import generate_arrival_rate_sequence

SEQUENCE_DIR_NAME = 'long congested sequence'
RESULTS_BASE = 'results/multi_step_comparison'
REQUIRED_SEEDS = [7, 42, 123, 1234]
TARGET_COUNT = 20
NUM_STEPS = 50
STD_DEV = 50


@contextlib.contextmanager
def suppress_stdout():
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


def check_sequence_feasibility(sequence, config, regen_obp, num_commodities):
    """检查序列每步可行性，使用默认求解器（较快）。返回 (all_feasible, infeasible_steps)。"""
    infeasible_steps = []
    for step_id in range(1, sequence.shape[0] + 1):
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
        with suppress_stdout():
            result = optimizer.solve_mcfp_path_formulation(
                demand_matrix,
                step_config['optimization']['objective_func'],
                step_config['simulation']['failure_strategy'],
                skip_infeasible_fallback=True,
                verbose=False,
                solver_options=None,
            )
        if result is None:
            infeasible_steps.append(step_id)
    return len(infeasible_steps) == 0, infeasible_steps


def save_sequence(sequence, seed, output_dir, num_commodities):
    """保存序列到 arrival_rate_sequence_50_steps.csv"""
    os.makedirs(output_dir, exist_ok=True)
    columns = [f'Commodity_{i}' for i in range(num_commodities)]
    df = pd.DataFrame(sequence, columns=columns)
    df.index.name = 'Time_Step'
    df.index = df.index + 1
    path = os.path.join(output_dir, 'arrival_rate_sequence_50_steps.csv')
    df.to_csv(path, index=True)
    return path


def main():
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)
    long_congested_base = os.path.join(src_dir, RESULTS_BASE, SEQUENCE_DIR_NAME)
    initial_rates = config['fixed_demand']['arrival_rate']
    num_commodities = config['optimization']['num_commodities']
    width = config['system']['width']
    height = config['system']['height']
    regen_obp = ToroidalTopo(scenario_config=config, width=width, height=height)

    print("=" * 70)
    print("筛选 20 个全可行 long congested 序列（默认求解器筛查）")
    print("=" * 70)
    print(f"目标: {TARGET_COUNT} 个序列，包含 seeds {REQUIRED_SEEDS}")
    print()

    feasible_seeds = []
    # 先验证并加入已知可行的 seeds
    for seed in REQUIRED_SEEDS:
        seq_file = os.path.join(long_congested_base, str(seed), 'arrival_rate_sequence_50_steps.csv')
        if not os.path.isfile(seq_file):
            print(f"✗ seed {seed} 序列文件不存在，将重新生成")
            sequence = generate_arrival_rate_sequence(
                initial_rates, num_steps=NUM_STEPS, std_dev=STD_DEV, seed=seed
            )
            ok, bad = check_sequence_feasibility(sequence, config, regen_obp, num_commodities)
            if ok:
                save_sequence(sequence, seed, os.path.join(long_congested_base, str(seed)), num_commodities)
                feasible_seeds.append(seed)
                print(f"  ✓ seed {seed} 全可行，已保存")
            else:
                print(f"  ✗ seed {seed} 不可行步: {bad[:5]}{'...' if len(bad)>5 else ''}")
        else:
            sequence = pd.read_csv(seq_file, index_col=0).values
            ok, bad = check_sequence_feasibility(sequence, config, regen_obp, num_commodities)
            if ok:
                feasible_seeds.append(seed)
                print(f"  ✓ seed {seed} 已验证全可行")
            else:
                print(f"  ✗ seed {seed} 存在不可行步: {bad[:5]}{'...' if len(bad)>5 else ''}")

    # 候选种子：排除已知 bad (0,1) 和已加入的
    exclude = {0, 1} | set(REQUIRED_SEEDS)
    candidates = [s for s in range(2, 500) if s not in exclude]
    print(f"\n从候选种子 {candidates[:20]}... 中筛选，直至凑满 {TARGET_COUNT} 个")
    print()

    for seed in candidates:
        if len(feasible_seeds) >= TARGET_COUNT:
            break
        sequence = generate_arrival_rate_sequence(
            initial_rates, num_steps=NUM_STEPS, std_dev=STD_DEV, seed=seed
        )
        ok, bad = check_sequence_feasibility(sequence, config, regen_obp, num_commodities)
        if ok:
            out_dir = os.path.join(long_congested_base, str(seed))
            save_sequence(sequence, seed, out_dir, num_commodities)
            feasible_seeds.append(seed)
            print(f"  ✓ seed {seed} 全可行，已保存 ({len(feasible_seeds)}/{TARGET_COUNT})")
        else:
            if (seed - 2) % 20 == 0 or seed <= 30:
                print(f"  ✗ seed {seed} 丢弃（不可行步: {len(bad)}）")

    feasible_seeds = sorted(feasible_seeds)[:TARGET_COUNT]
    print()
    print("=" * 70)
    print(f"最终 {len(feasible_seeds)} 个可行种子: {feasible_seeds}")
    print("=" * 70)

    out_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(out_dir, exist_ok=True)
    summary_path = os.path.join(out_dir, 'feasible_long_congested_seeds_20.csv')
    pd.DataFrame({'seed': feasible_seeds}).to_csv(summary_path, index=False)
    print(f"✓ 种子列表已保存: {summary_path}")


if __name__ == '__main__':
    main()
