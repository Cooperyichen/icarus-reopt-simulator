#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test-driven development (TDD) tests for path ratio preservation functionality.

Tests the path ratio extraction from mcfp_results CSV files and application
to new commodity demands in multi-step simulations.

Following TDD approach: Write tests first, then implement functionality.
"""

import unittest
import sys
import os
import pandas as pd
import tempfile
import shutil

# Add the project src directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

# Import path ratio functions (will be implemented later)
# from simulator.path_ratio_utils import extract_path_ratios_from_csv, apply_path_ratios_to_demand


class TestPathRatioPreservation(unittest.TestCase):
    """Test path ratio preservation functionality using TDD approach."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_data_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # Create sample CSV data for testing
        self.sample_csv_data = {
            'id_flow': [0, 0, 0, 1, 1, 1],
            'Source': ['OBPModule(0, 0)_uplink_0', 'OBPModule(0, 0)_uplink_0', 'OBPModule(0, 0)_uplink_0',
                      'OBPModule(0, 1)_uplink_0', 'OBPModule(0, 1)_uplink_0', 'OBPModule(0, 1)_uplink_0'],
            'Destination': ['OBPModule(3, 0)_downlink_0', 'OBPModule(3, 0)_downlink_0', 'OBPModule(3, 0)_downlink_0',
                           'OBPModule(3, 1)_downlink_0', 'OBPModule(3, 1)_downlink_0', 'OBPModule(3, 1)_downlink_0'],
            'Arrival Rate': [200.0, 300.0, 500.0, 600.0, 700.0, 700.0],
            'Path': [
                'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(1, 0) -> OBPModule(2, 0) -> OBPModule(3, 0) -> OBPModule(3, 0)_downlink_0',
                'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(1, 0) -> OBPModule(2, 1) -> OBPModule(3, 1) -> OBPModule(3, 0)_downlink_0',
                'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(0, 1) -> OBPModule(1, 1) -> OBPModule(2, 1) -> OBPModule(3, 0) -> OBPModule(3, 0)_downlink_0',
                'OBPModule(0, 1)_uplink_0 -> OBPModule(0, 1) -> OBPModule(1, 1) -> OBPModule(2, 1) -> OBPModule(3, 1) -> OBPModule(3, 1)_downlink_0',
                'OBPModule(0, 1)_uplink_0 -> OBPModule(0, 1) -> OBPModule(1, 1) -> OBPModule(2, 2) -> OBPModule(3, 2) -> OBPModule(3, 1)_downlink_0',
                'OBPModule(0, 1)_uplink_0 -> OBPModule(0, 1) -> OBPModule(0, 2) -> OBPModule(1, 2) -> OBPModule(2, 2) -> OBPModule(3, 1) -> OBPModule(3, 1)_downlink_0',
            ],
            'Priority': [1, 1, 1, 1, 1, 1]
        }
        
        # Expected ratios for commodity 0 (total flow = 1000)
        # Path 0: 200/1000 = 0.2
        # Path 1: 300/1000 = 0.3
        # Path 2: 500/1000 = 0.5
        self.expected_ratios_0 = {
            'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(1, 0) -> OBPModule(2, 0) -> OBPModule(3, 0) -> OBPModule(3, 0)_downlink_0': 0.2,
            'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(1, 0) -> OBPModule(2, 1) -> OBPModule(3, 1) -> OBPModule(3, 0)_downlink_0': 0.3,
            'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(0, 1) -> OBPModule(1, 1) -> OBPModule(2, 1) -> OBPModule(3, 0) -> OBPModule(3, 0)_downlink_0': 0.5
        }
        
        # Expected ratios for commodity 1 (total flow = 2000)
        # Path 0: 600/2000 = 0.3
        # Path 1: 700/2000 = 0.35
        # Path 2: 700/2000 = 0.35
        self.expected_ratios_1 = {
            'OBPModule(0, 1)_uplink_0 -> OBPModule(0, 1) -> OBPModule(1, 1) -> OBPModule(2, 1) -> OBPModule(3, 1) -> OBPModule(3, 1)_downlink_0': 0.3,
            'OBPModule(0, 1)_uplink_0 -> OBPModule(0, 1) -> OBPModule(1, 1) -> OBPModule(2, 2) -> OBPModule(3, 2) -> OBPModule(3, 1)_downlink_0': 0.35,
            'OBPModule(0, 1)_uplink_0 -> OBPModule(0, 1) -> OBPModule(0, 2) -> OBPModule(1, 2) -> OBPModule(2, 2) -> OBPModule(3, 1) -> OBPModule(3, 1)_downlink_0': 0.35
        }
    
    def create_test_csv(self, filename='test_mcfp_results.csv'):
        """Create a temporary CSV file with test data."""
        df = pd.DataFrame(self.sample_csv_data)
        csv_path = os.path.join(self.test_data_dir, filename)
        df.to_csv(csv_path, index=False)
        return csv_path
    
    # ============================================================================
    # Phase 1: Path Ratio Extraction Unit Tests
    # ============================================================================
    
    def test_1_1_csv_file_reading(self):
        """
        Test 1.1: CSV file reading and parsing
        
        Purpose: Verify that mcfp_results CSV files can be correctly read and parsed.
        Expected: Successfully read CSV, DataFrame contains correct columns, can group by id_flow.
        """
        # Create test CSV file
        csv_path = self.create_test_csv('test_1_1_mcfp_results.csv')
        
        # Read CSV file
        # TODO: Implement extract_path_ratios_from_csv function
        # For now, test with pandas directly
        df = pd.read_csv(csv_path)
        
        # Verify columns exist
        required_columns = ['id_flow', 'Source', 'Destination', 'Arrival Rate', 'Path', 'Priority']
        for col in required_columns:
            self.assertIn(col, df.columns, f"Required column '{col}' not found in CSV")
        
        # Verify data types
        self.assertTrue(pd.api.types.is_numeric_dtype(df['Arrival Rate']), 
                       "Arrival Rate should be numeric")
        self.assertTrue(pd.api.types.is_numeric_dtype(df['id_flow']), 
                       "id_flow should be numeric")
        
        # Verify grouping capability
        grouped = df.groupby('id_flow')
        self.assertEqual(len(grouped), 2, "Should have 2 commodities (id_flow 0 and 1)")
        
        # Verify commodity 0 has 3 paths
        commodity_0 = df[df['id_flow'] == 0]
        self.assertEqual(len(commodity_0), 3, "Commodity 0 should have 3 paths")
        
        # Verify commodity 1 has 3 paths
        commodity_1 = df[df['id_flow'] == 1]
        self.assertEqual(len(commodity_1), 3, "Commodity 1 should have 3 paths")
        
        print("✓ Test 1.1 PASSED: CSV file reading and parsing")
    
    def test_1_2_ratio_calculation_accuracy(self):
        """
        Test 1.2: Path ratio calculation accuracy
        
        Purpose: Verify path ratios are calculated correctly (path_ratio = path_flow / total_flow)
        Expected: Ratios [0.2, 0.3, 0.5] for commodity 0, [0.3, 0.35, 0.35] for commodity 1, sums = 1.0
        """
        df = pd.DataFrame(self.sample_csv_data)
        
        # Calculate ratios for each commodity
        # TODO: Implement calculate_ratios_from_mcfp_results function
        # For now, implement inline
        ratios_by_commodity = {}
        
        for commodity_id in df['id_flow'].unique():
            commodity_df = df[df['id_flow'] == commodity_id]
            total_flow = commodity_df['Arrival Rate'].sum()
            
            path_ratios = {}
            for _, row in commodity_df.iterrows():
                path = row['Path']
                flow = row['Arrival Rate']
                path_ratios[path] = flow / total_flow
            
            ratios_by_commodity[commodity_id] = path_ratios
        
        # Verify commodity 0 ratios
        commodity_0_ratios = ratios_by_commodity[0]
        for path, expected_ratio in self.expected_ratios_0.items():
            actual_ratio = commodity_0_ratios[path]
            self.assertAlmostEqual(actual_ratio, expected_ratio, places=6,
                                 msg=f"Path ratio mismatch for commodity 0, path: {path[:50]}...")
        
        # Verify commodity 0 ratio sum
        total_ratio_0 = sum(commodity_0_ratios.values())
        self.assertAlmostEqual(total_ratio_0, 1.0, places=6,
                             msg=f"Commodity 0 ratio sum should be 1.0, got {total_ratio_0}")
        
        # Verify commodity 1 ratios
        commodity_1_ratios = ratios_by_commodity[1]
        for path, expected_ratio in self.expected_ratios_1.items():
            actual_ratio = commodity_1_ratios[path]
            self.assertAlmostEqual(actual_ratio, expected_ratio, places=6,
                                 msg=f"Path ratio mismatch for commodity 1, path: {path[:50]}...")
        
        # Verify commodity 1 ratio sum
        total_ratio_1 = sum(commodity_1_ratios.values())
        self.assertAlmostEqual(total_ratio_1, 1.0, places=6,
                             msg=f"Commodity 1 ratio sum should be 1.0, got {total_ratio_1}")
        
        print("✓ Test 1.2 PASSED: Path ratio calculation accuracy")
    
    def test_1_3_path_string_matching(self):
        """
        Test 1.3: Path string matching
        
        Purpose: Verify path strings can be correctly matched (for later ratio application)
        Expected: Exact path matches are correctly identified, format differences handled
        """
        df = pd.DataFrame(self.sample_csv_data)
        
        # Get paths for commodity 0
        commodity_0_paths = df[df['id_flow'] == 0]['Path'].tolist()
        
        # Test exact matching
        test_path = commodity_0_paths[0]
        self.assertIn(test_path, commodity_0_paths, 
                     "Path string should be found in commodity paths")
        
        # Test that paths are strings
        for path in commodity_0_paths:
            self.assertIsInstance(path, str, "Path should be a string")
            self.assertGreater(len(path), 0, "Path should not be empty")
        
        # Test that paths contain required elements
        for path in commodity_0_paths:
            self.assertIn('OBPModule', path, "Path should contain OBPModule")
            self.assertIn('->', path, "Path should contain '->' separator")
        
        print("✓ Test 1.3 PASSED: Path string matching")
    
    # ============================================================================
    # Phase 2: Path Ratio Application Unit Tests
    # ============================================================================
    
    def test_2_1_single_commodity_ratio_application(self):
        """
        Test 2.1: Single commodity ratio application
        
        Purpose: Verify applying path ratios to new demand for one commodity
        Expected: New flows = new_demand × ratio, sum = new_demand
        """
        # Baseline ratios for commodity 0
        baseline_ratios = {0: self.expected_ratios_0}
        new_demand = 1500  # packets/s
        
        # TODO: Implement apply_path_ratios_to_demand function
        # For now, implement inline
        new_flows = {}
        for path, ratio in baseline_ratios[0].items():
            new_flows[path] = new_demand * ratio
        
        # Verify individual path flows
        expected_flows = {
            'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(1, 0) -> OBPModule(2, 0) -> OBPModule(3, 0) -> OBPModule(3, 0)_downlink_0': 300.0,  # 1500 × 0.2
            'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(1, 0) -> OBPModule(2, 1) -> OBPModule(3, 1) -> OBPModule(3, 0)_downlink_0': 450.0,  # 1500 × 0.3
            'OBPModule(0, 0)_uplink_0 -> OBPModule(0, 0) -> OBPModule(0, 1) -> OBPModule(1, 1) -> OBPModule(2, 1) -> OBPModule(3, 0) -> OBPModule(3, 0)_downlink_0': 750.0  # 1500 × 0.5
        }
        
        for path, expected_flow in expected_flows.items():
            actual_flow = new_flows[path]
            self.assertAlmostEqual(actual_flow, expected_flow, places=2,
                                 msg=f"Flow mismatch for path: {path[:50]}...")
        
        # Verify total flow equals new demand
        total_flow = sum(new_flows.values())
        self.assertAlmostEqual(total_flow, new_demand, places=2,
                             msg=f"Total flow should equal new demand {new_demand}, got {total_flow}")
        
        print("✓ Test 2.1 PASSED: Single commodity ratio application")
    
    def test_2_2_multi_commodity_independent_application(self):
        """
        Test 2.2: Multi-commodity independent ratio application
        
        Purpose: Verify multiple commodities can independently apply ratios
        Expected: Each commodity's path flows sum to its new demand, ratios are independent
        """
        # Baseline ratios for both commodities
        baseline_ratios = {
            0: self.expected_ratios_0,
            1: self.expected_ratios_1
        }
        new_demands = [1500, 3000]  # [commodity 0, commodity 1]
        
        # TODO: Implement apply_path_ratios_to_demand function for multiple commodities
        # For now, implement inline
        all_new_flows = {}
        for commodity_id, ratios in baseline_ratios.items():
            new_demand = new_demands[commodity_id]
            commodity_flows = {}
            for path, ratio in ratios.items():
                commodity_flows[path] = new_demand * ratio
            all_new_flows[commodity_id] = commodity_flows
        
        # Verify commodity 0
        commodity_0_flows = all_new_flows[0]
        total_flow_0 = sum(commodity_0_flows.values())
        self.assertAlmostEqual(total_flow_0, new_demands[0], places=2,
                             msg=f"Commodity 0 total flow should be {new_demands[0]}, got {total_flow_0}")
        
        # Verify commodity 1
        commodity_1_flows = all_new_flows[1]
        total_flow_1 = sum(commodity_1_flows.values())
        self.assertAlmostEqual(total_flow_1, new_demands[1], places=2,
                             msg=f"Commodity 1 total flow should be {new_demands[1]}, got {total_flow_1}")
        
        # Verify ratios are independent (commodity 0 ratios unchanged)
        for path, expected_ratio in self.expected_ratios_0.items():
            actual_ratio = commodity_0_flows[path] / total_flow_0
            self.assertAlmostEqual(actual_ratio, expected_ratio, places=6,
                                 msg="Commodity 0 ratios should remain unchanged")
        
        print("✓ Test 2.2 PASSED: Multi-commodity independent ratio application")
    
    def test_2_3_demand_change_edge_cases(self):
        """
        Test 2.3: Demand change edge cases
        
        Purpose: Verify ratio application works for extreme demand changes
        Expected: Ratios remain constant, flows calculated correctly
        """
        baseline_ratios = {0: self.expected_ratios_0}
        
        # Test cases: (multiplier, expected_total)
        test_cases = [
            (2.0, 2000),   # 2x increase
            (0.5, 500),    # 2x decrease
            (10.0, 10000), # 10x increase
            (0.1, 100),    # 10x decrease
        ]
        
        base_demand = 1000
        
        for multiplier, expected_total in test_cases:
            new_demand = base_demand * multiplier
            
            # Apply ratios
            new_flows = {}
            for path, ratio in baseline_ratios[0].items():
                new_flows[path] = new_demand * ratio
            
            # Verify total
            total_flow = sum(new_flows.values())
            self.assertAlmostEqual(total_flow, expected_total, places=2,
                                 msg=f"Total flow should be {expected_total} for {multiplier}x change, got {total_flow}")
            
            # Verify ratios unchanged
            for path, expected_ratio in baseline_ratios[0].items():
                actual_ratio = new_flows[path] / total_flow
                self.assertAlmostEqual(actual_ratio, expected_ratio, places=6,
                                     msg=f"Ratio should remain {expected_ratio} for {multiplier}x change")
        
        print("✓ Test 2.3 PASSED: Demand change edge cases")
    
    # ============================================================================
    # Phase 3: Integration Tests (End-to-End)
    # ============================================================================
    # Note: Integration tests will be added after Phase 1 and 2 tests pass
    # These require actual simulation runs and are more complex


if __name__ == '__main__':
    # Run tests in order
    unittest.main(verbosity=2)

