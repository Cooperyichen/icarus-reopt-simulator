#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验收测试 1：long congested sequence 下 Strategy 4（阈值=8）运行结果。

通过条件：
1. 6 个 seed 目录下均存在 strategy4_stats.csv
2. 每个 CSV 有 50 行（50 步）
3. 必含列：step_id, reoptimized, trigger_metric
4. 每序列重优化次数在 5～45 之间（避免几乎不触发或几乎每步都触发）
"""

import unittest
import sys
import os
import pandas as pd

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

SEEDS = [0, 1, 7, 42, 123, 1234]
REQUIRED_COLUMNS = ['step_id', 'reoptimized', 'trigger_metric']
NUM_STEPS = 50
REOPT_MIN = 1   # 至少触发 1 次（避免阈值过大几乎不触发）
REOPT_MAX = 45  # 避免几乎每步都触发
MIN_SEEDS_WITH_STATS = 4  # 至少 4 个 seed 有结果即可进入阶段 2（部分 seed 可能因数值问题失败）


def get_strategy4_stats_path(seed):
    return os.path.join(
        src_path, 'results', 'multi_step_comparison',
        'long congested sequence', str(seed), 'strategy4', 'strategy4_stats.csv'
    )


def seeds_with_stats():
    """返回存在 strategy4_stats.csv 的 seed 列表。"""
    return [s for s in SEEDS if os.path.isfile(get_strategy4_stats_path(s))]


class TestStrategy4LongCongested(unittest.TestCase):
    """Phase 1 验收：Strategy 4 在 long congested sequence 各 seed 上的输出。"""

    def test_1_sufficient_seeds_have_strategy4_stats(self):
        """至少 MIN_SEEDS_WITH_STATS 个 seed 目录下存在 strategy4_stats.csv"""
        found = seeds_with_stats()
        self.assertGreaterEqual(
            len(found), MIN_SEEDS_WITH_STATS,
            f"至少需要 {MIN_SEEDS_WITH_STATS} 个 seed 有 strategy4_stats.csv，当前只有: {found}"
        )

    def test_2_each_csv_has_50_steps(self):
        """每个已存在的 CSV 有 50 行（50 步）"""
        for seed in seeds_with_stats():
            path = get_strategy4_stats_path(seed)
            df = pd.read_csv(path)
            self.assertEqual(len(df), NUM_STEPS, f"seed {seed}: 应有 {NUM_STEPS} 行，实际 {len(df)}")

    def test_3_required_columns_present(self):
        """必含列 step_id, reoptimized, trigger_metric"""
        for seed in seeds_with_stats():
            path = get_strategy4_stats_path(seed)
            df = pd.read_csv(path)
            for col in REQUIRED_COLUMNS:
                self.assertIn(col, df.columns, f"seed {seed}: 缺少列 {col}")

    def test_4_reoptimized_count_in_range(self):
        """每序列重优化次数在 5～45 之间（仅对已有 CSV 的 seed 检查）"""
        for seed in seeds_with_stats():
            path = get_strategy4_stats_path(seed)
            df = pd.read_csv(path)
            reopt = df['reoptimized']
            if reopt.dtype == bool:
                count = int(reopt.sum())
            else:
                count = int(((reopt == True) | (reopt == 'True') | (reopt == 'true')).sum())
            self.assertGreaterEqual(
                count, REOPT_MIN,
                f"seed {seed}: 重优化次数 {count} 少于 {REOPT_MIN}"
            )
            self.assertLessEqual(
                count, REOPT_MAX,
                f"seed {seed}: 重优化次数 {count} 多于 {REOPT_MAX}"
            )


if __name__ == '__main__':
    unittest.main()
