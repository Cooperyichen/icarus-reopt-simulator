#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仅对 seed 0 运行 Strategy 4（θ=6），补齐 strategy4_threshold_6/strategy4/strategy4_stats.csv。"""

import sys
import os
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.multi_step_comparison_experiment import execute_strategy_adaptive_reoptimization

SEED = 0
THRESHOLD = 6
SEQUENCE_DIR_NAME = 'long congested sequence'


def main():
    config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
    result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
    long_congested_base = os.path.join(result_dir_base, SEQUENCE_DIR_NAME)
    sequence_name = f"{SEQUENCE_DIR_NAME}/{SEED}"
    sequence_file = os.path.join(long_congested_base, str(SEED), 'arrival_rate_sequence_50_steps.csv')

    if not os.path.exists(sequence_file):
        print(f"✗ 序列文件不存在: {sequence_file}")
        return

    config = load_yaml_file(config_file)
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    sequence = sequence_df.values
    run_result_base = os.path.join(result_dir_base, sequence_name, f'strategy4_threshold_{THRESHOLD}')

    print(f"运行 Strategy 4（θ={THRESHOLD}）seed={SEED} ...")
    try:
        strategy_stats = execute_strategy_adaptive_reoptimization(
            sequence, config, run_result_base, threshold=THRESHOLD
        )
    except Exception as e:
        print(f"✗ 出错: {e}")
        import traceback
        traceback.print_exc()
        return

    strategy_dir = os.path.join(run_result_base, 'strategy4')
    os.makedirs(strategy_dir, exist_ok=True)
    df = pd.DataFrame(strategy_stats)
    stats_file = os.path.join(strategy_dir, 'strategy4_stats.csv')
    if 'arrival_rates' in df.columns:
        df['arrival_rates'] = df['arrival_rates'].apply(
            lambda x: str(x) if isinstance(x, (list, np.ndarray)) else x
        )
    df.to_csv(stats_file, index=False)
    print(f"✓ 已保存: {stats_file}")


if __name__ == '__main__':
    main()
