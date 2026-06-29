#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate 20-seed uniform long congested arrival rate sequences."""

import os
import sys
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.generate_arrival_rate_sequence import generate_arrival_rate_sequence_uniform

SEQUENCE_DIR_NAME = 'uniform long congested sequence'
BASELINE_SEEDS_FILE = os.path.join(
    src_dir, 'results', '可视化结果展示', 'long congested sequence', 'feasible_long_congested_seeds_20.csv'
)
NUM_STEPS = 50
PERTURB_VARIANCE = 2500.0


def load_seeds():
    if not os.path.isfile(BASELINE_SEEDS_FILE):
        raise FileNotFoundError(f'未找到 seed 列表: {BASELINE_SEEDS_FILE}')
    return pd.read_csv(BASELINE_SEEDS_FILE)['seed'].astype(int).tolist()


def save_sequence(sequence, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    columns = [f'Commodity_{i}' for i in range(sequence.shape[1])]
    df = pd.DataFrame(sequence, columns=columns)
    df.index.name = 'Time_Step'
    df.index = df.index + 1
    path = os.path.join(out_dir, 'arrival_rate_sequence_50_steps.csv')
    df.to_csv(path, index=True)
    return path


def main():
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    config = load_yaml_file(config_file)

    initial_rates = config['fixed_demand']['arrival_rate']
    seeds = load_seeds()

    out_root = os.path.join(src_dir, 'results', 'multi_step_comparison', SEQUENCE_DIR_NAME)
    os.makedirs(out_root, exist_ok=True)

    print('=' * 80)
    print('Generate uniform long congested sequence (20 seeds)')
    print('=' * 80)
    print(f'Initial rates: {initial_rates}')
    print(f'Variance target: {PERTURB_VARIANCE} (uniform U(-a,a), a=sqrt(3*variance))')
    print(f'Steps: {NUM_STEPS}, seeds: {len(seeds)}')

    for i, seed in enumerate(seeds, start=1):
        seq = generate_arrival_rate_sequence_uniform(
            initial_rates=initial_rates,
            num_steps=NUM_STEPS,
            variance=PERTURB_VARIANCE,
            seed=seed,
        )
        out_dir = os.path.join(out_root, str(seed))
        path = save_sequence(seq, out_dir)
        print(f'[{i:02d}/{len(seeds)}] seed={seed} -> {path}')

    out_vis = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(out_vis, exist_ok=True)
    out_seed_file = os.path.join(out_vis, 'feasible_uniform_long_congested_seeds_20.csv')
    pd.DataFrame({'seed': seeds}).to_csv(out_seed_file, index=False)
    print(f'✓ seeds saved: {out_seed_file}')


if __name__ == '__main__':
    main()
