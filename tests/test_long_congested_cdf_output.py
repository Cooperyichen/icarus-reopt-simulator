#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验收测试 2：long congested sequence Figure 1（inter-event CDF）输出。

通过条件：
1. inter_event_cdf.png 存在
2. 文件大小 > 1KB（确保非空图）
3. 若存在 inter_event_summary.csv，则验证其结构合理（如含 seed, reopt_count, mean_dt 等）
"""

import unittest
import sys
import os
import pandas as pd

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

OUTPUT_DIR = os.path.join(src_path, 'results', '可视化结果展示', 'long congested sequence')
CDF_FILE = os.path.join(OUTPUT_DIR, 'inter_event_cdf.png')
SUMMARY_FILE = os.path.join(OUTPUT_DIR, 'inter_event_summary.csv')
MIN_CDF_SIZE_BYTES = 1024
SUMMARY_COLUMNS = ['seed', 'reopt_count', 'num_inter_events', 'mean_dt']


class TestLongCongestedCdfOutput(unittest.TestCase):
    """Phase 2 验收：Figure 1 CDF 及汇总文件。"""

    def test_1_inter_event_cdf_exists(self):
        """inter_event_cdf.png 存在"""
        self.assertTrue(os.path.isfile(CDF_FILE), f"文件不存在: {CDF_FILE}")

    def test_2_inter_event_cdf_non_empty(self):
        """inter_event_cdf.png 文件大小 > 1KB"""
        self.assertTrue(os.path.isfile(CDF_FILE), "inter_event_cdf.png 不存在")
        size = os.path.getsize(CDF_FILE)
        self.assertGreater(size, MIN_CDF_SIZE_BYTES, f"inter_event_cdf.png 大小 {size} <= {MIN_CDF_SIZE_BYTES} bytes")

    def test_3_inter_event_summary_structure_if_present(self):
        """若存在 inter_event_summary.csv，则验证其结构合理"""
        if not os.path.isfile(SUMMARY_FILE):
            self.skipTest("inter_event_summary.csv 不存在，跳过结构检查")
        df = pd.read_csv(SUMMARY_FILE)
        for col in SUMMARY_COLUMNS:
            self.assertIn(col, df.columns, f"inter_event_summary.csv 缺少列: {col}")


if __name__ == '__main__':
    unittest.main()
