#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TDD Test Suite for Global Optimal Ratio Strategy (Strategy 3)

Test phases:
1. Phase 1: Path set extraction and validation
2. Phase 2: Single-step utilization calculation
3. Phase 3: Multi-step average utilization calculation
4. Phase 4: Optimization problem setup and solving
5. Phase 5: End-to-end integration and comparison
"""

import sys
import os
import pandas as pd
import numpy as np
import unittest

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from main.global_optimal_ratio import (
    extract_paths_from_step1,
    extract_paths_info_from_step1,
    calculate_single_step_utilization,
    calculate_average_max_link_utilization,
    optimize_global_path_ratios,
    _path_ratios_dict_to_vector,
    _path_ratios_vector_to_dict
)
from main.test_path_ratio_preservation import extract_path_ratios_from_csv
from main.multi_step_comparison_experiment import calculate_max_link_utilization


class TestGlobalOptimalRatioPhase1(unittest.TestCase):
    """Phase 1: Path set extraction and validation tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.src_dir = src_dir
        self.result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
        
        # Use Strategy 2 Step 1 results (or Strategy 1 Step 1 if Strategy 2 doesn't exist)
        self.step1_mcfp_file = os.path.join(
            self.result_dir_base, 'strategy2', 'step_1',
            'mcfp_results_flows_4_commodities.csv'
        )
        
        # Fallback to strategy1 if strategy2 doesn't exist
        if not os.path.exists(self.step1_mcfp_file):
            self.step1_mcfp_file = os.path.join(
                self.result_dir_base, 'strategy1', 'step_1',
                'mcfp_results_flows_4_commodities.csv'
            )
    
    def test_1_1_path_extraction(self):
        """
        Test 1.1: Path set extraction from Step 1 CSV file.
        
        Purpose: Verify that paths can be correctly extracted from Step 1 results.
        """
        if not os.path.exists(self.step1_mcfp_file):
            self.skipTest(f"Step 1 MCFP file not found: {self.step1_mcfp_file}")
        
        # Extract paths
        paths_by_commodity = extract_paths_from_step1(self.step1_mcfp_file)
        
        # Verify structure
        self.assertIsInstance(paths_by_commodity, dict, "Result should be a dictionary")
        self.assertEqual(len(paths_by_commodity), 4, "Should have 4 commodities")
        
        # Verify each commodity has paths
        for commodity_id in [0, 1, 2, 3]:
            self.assertIn(commodity_id, paths_by_commodity, 
                         f"Commodity {commodity_id} should be present")
            paths = paths_by_commodity[commodity_id]
            self.assertIsInstance(paths, list, f"Commodity {commodity_id} paths should be a list")
            self.assertGreater(len(paths), 0, f"Commodity {commodity_id} should have at least one path")
            
            # Verify path format
            for path in paths:
                self.assertIsInstance(path, str, "Path should be a string")
                self.assertIn('OBPModule', path, "Path should contain 'OBPModule'")
                self.assertIn('->', path, "Path should contain '->' separator")
        
        print(f"\n✓ Test 1.1 PASSED")
        print(f"  Commodities: {list(paths_by_commodity.keys())}")
        for commodity_id, paths in sorted(paths_by_commodity.items()):
            print(f"  Commodity {commodity_id}: {len(paths)} paths")
    
    def test_1_2_path_uniqueness(self):
        """
        Test 1.2: Path uniqueness validation.
        
        Purpose: Verify that paths within each commodity are unique.
        """
        if not os.path.exists(self.step1_mcfp_file):
            self.skipTest(f"Step 1 MCFP file not found: {self.step1_mcfp_file}")
        
        # Extract paths
        paths_by_commodity = extract_paths_from_step1(self.step1_mcfp_file)
        
        # Verify uniqueness within each commodity
        for commodity_id, paths in paths_by_commodity.items():
            # Check for duplicates
            unique_paths = set(paths)
            self.assertEqual(len(unique_paths), len(paths),
                           f"Commodity {commodity_id} has duplicate paths")
        
        # Also test with paths_info extraction
        paths_info = extract_paths_info_from_step1(self.step1_mcfp_file)
        
        for commodity_id, info in paths_info.items():
            paths = info['paths']
            unique_paths = set(paths)
            self.assertEqual(len(unique_paths), len(paths),
                           f"Commodity {commodity_id} has duplicate paths in paths_info")
        
        print(f"\n✓ Test 1.2 PASSED")
        print(f"  All paths are unique within each commodity")


class TestGlobalOptimalRatioPhase2(unittest.TestCase):
    """Phase 2: Single-step utilization calculation tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.src_dir = src_dir
        self.result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
        
        # Use Strategy 2 Step 1 results
        self.step1_mcfp_file = os.path.join(
            self.result_dir_base, 'strategy2', 'step_1',
            'mcfp_results_flows_4_commodities.csv'
        )
        
        # Fallback to strategy1
        if not os.path.exists(self.step1_mcfp_file):
            self.step1_mcfp_file = os.path.join(
                self.result_dir_base, 'strategy1', 'step_1',
                'mcfp_results_flows_4_commodities.csv'
            )
        
        # Load config
        config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
        self.config = load_yaml_file(config_file)
        
        # Extract paths info
        if os.path.exists(self.step1_mcfp_file):
            self.paths_info = extract_paths_info_from_step1(self.step1_mcfp_file)
        else:
            self.paths_info = None
    
    def test_2_1_single_step_utilization(self):
        """
        Test 2.1: Single-step utilization calculation.
        
        Purpose: Verify that given path ratios and arrival rates, 
        we can correctly calculate maximum link utilization.
        """
        if self.paths_info is None or not os.path.exists(self.step1_mcfp_file):
            self.skipTest(f"Step 1 MCFP file not found: {self.step1_mcfp_file}")
        
        # Load Step 1 ratios
        path_ratios = extract_path_ratios_from_csv(self.step1_mcfp_file)
        
        # Use Step 1 arrival rates (load from sequence or config)
        sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
        if os.path.exists(sequence_file):
            sequence_df = pd.read_csv(sequence_file, index_col=0)
            arrival_rates = sequence_df.iloc[0].values.tolist()  # Step 1
        else:
            arrival_rates = self.config['fixed_demand']['arrival_rate']
        
        # Calculate utilization
        max_util = calculate_single_step_utilization(
            path_ratios, arrival_rates, self.paths_info, self.config
        )
        
        # Verify result
        self.assertIsInstance(max_util, (int, float), "Result should be a number")
        self.assertGreaterEqual(max_util, 0.0, "Utilization should be non-negative")
        self.assertLessEqual(max_util, 100.0, "Utilization should not exceed 100%")
        
        print(f"\n✓ Test 2.1 PASSED")
        print(f"  Maximum link utilization: {max_util:.4f}%")
        print(f"  Arrival rates: {[f'{r:.2f}' for r in arrival_rates]}")
    
    def test_2_2_compare_with_existing_function(self):
        """
        Test 2.2: Compare with existing calculate_max_link_utilization function.
        
        Purpose: Verify that our calculation matches the existing function 
        when using Step 1's path ratios and arrival rates.
        """
        if self.paths_info is None or not os.path.exists(self.step1_mcfp_file):
            self.skipTest(f"Step 1 MCFP file not found: {self.step1_mcfp_file}")
        
        # Load Step 1 data
        step1_df = pd.read_csv(self.step1_mcfp_file)
        path_ratios = extract_path_ratios_from_csv(self.step1_mcfp_file)
        
        # Get Step 1 arrival rates
        sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
        if os.path.exists(sequence_file):
            sequence_df = pd.read_csv(sequence_file, index_col=0)
            arrival_rates = sequence_df.iloc[0].values.tolist()
        else:
            arrival_rates = self.config['fixed_demand']['arrival_rate']
        
        # Calculate using our function
        our_util = calculate_single_step_utilization(
            path_ratios, arrival_rates, self.paths_info, self.config
        )
        
        # Calculate using existing function (should be the same for Step 1)
        existing_util = calculate_max_link_utilization(step1_df, self.config)
        
        # Compare (allow small numerical error)
        diff = abs(our_util - existing_util)
        tolerance = 0.01  # 0.01%
        
        self.assertLess(diff, tolerance,
                       f"Utilization difference {diff:.6f}% exceeds tolerance {tolerance}%")
        
        print(f"\n✓ Test 2.2 PASSED")
        print(f"  Our function: {our_util:.6f}%")
        print(f"  Existing function: {existing_util:.6f}%")
        print(f"  Difference: {diff:.6f}%")


class TestGlobalOptimalRatioPhase3(unittest.TestCase):
    """Phase 3: Multi-step average utilization calculation tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.src_dir = src_dir
        self.result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
        
        # Use Strategy 2 Step 1 results
        self.step1_mcfp_file = os.path.join(
            self.result_dir_base, 'strategy2', 'step_1',
            'mcfp_results_flows_4_commodities.csv'
        )
        
        # Fallback to strategy1
        if not os.path.exists(self.step1_mcfp_file):
            self.step1_mcfp_file = os.path.join(
                self.result_dir_base, 'strategy1', 'step_1',
                'mcfp_results_flows_4_commodities.csv'
            )
        
        # Load config
        config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
        self.config = load_yaml_file(config_file)
        
        # Extract paths info and ratios
        if os.path.exists(self.step1_mcfp_file):
            self.paths_info = extract_paths_info_from_step1(self.step1_mcfp_file)
            self.path_ratios = extract_path_ratios_from_csv(self.step1_mcfp_file)
        else:
            self.paths_info = None
            self.path_ratios = None
    
    def test_3_1_average_utilization(self):
        """
        Test 3.1: Multi-step average utilization calculation.
        
        Purpose: Verify that we can correctly calculate average maximum 
        link utilization across multiple steps.
        """
        if self.paths_info is None or self.path_ratios is None:
            self.skipTest(f"Step 1 MCFP file not found: {self.step1_mcfp_file}")
        
        # Load 10-step sequence
        sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
        if not os.path.exists(sequence_file):
            self.skipTest(f"Sequence file not found: {sequence_file}")
        
        sequence_df = pd.read_csv(sequence_file, index_col=0)
        
        # Calculate average utilization
        avg_util = calculate_average_max_link_utilization(
            self.path_ratios, sequence_df, self.paths_info, self.config
        )
        
        # Verify result
        self.assertIsInstance(avg_util, (int, float), "Result should be a number")
        self.assertGreaterEqual(avg_util, 0.0, "Utilization should be non-negative")
        self.assertLessEqual(avg_util, 100.0, "Utilization should not exceed 100%")
        
        print(f"\n✓ Test 3.1 PASSED")
        print(f"  Average maximum link utilization: {avg_util:.4f}%")
        print(f"  Number of steps: {len(sequence_df)}")
    
    def test_3_2_edge_cases(self):
        """
        Test 3.2: Edge case handling.
        
        Purpose: Verify that edge cases (same rates, zero ratios) are handled correctly.
        """
        if self.paths_info is None or self.path_ratios is None:
            self.skipTest(f"Step 1 MCFP file not found: {self.step1_mcfp_file}")
        
        # Test case 1: All steps have the same arrival rates
        # Result should equal single-step utilization
        single_step_rates = [540.0, 780.0, 300.0, 780.0]
        single_util = calculate_single_step_utilization(
            self.path_ratios, single_step_rates, self.paths_info, self.config
        )
        
        # Create a sequence with all steps equal
        same_sequence = np.array([single_step_rates] * 10)
        avg_util = calculate_average_max_link_utilization(
            self.path_ratios, same_sequence, self.paths_info, self.config
        )
        
        # Should be approximately equal
        diff = abs(avg_util - single_util)
        self.assertLess(diff, 0.001, 
                       f"Average util ({avg_util}) should equal single util ({single_util})")
        
        print(f"\n✓ Test 3.2 PASSED")
        print(f"  Single-step util: {single_util:.6f}%")
        print(f"  10-step average (same rates): {avg_util:.6f}%")
        print(f"  Difference: {diff:.6f}%")


class TestGlobalOptimalRatioPhase4(unittest.TestCase):
    """Phase 4: Optimization problem setup and solving tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.src_dir = src_dir
        self.result_dir_base = os.path.join(src_dir, 'results', 'multi_step_comparison')
        
        # Use Strategy 2 Step 1 results
        self.step1_mcfp_file = os.path.join(
            self.result_dir_base, 'strategy2', 'step_1',
            'mcfp_results_flows_4_commodities.csv'
        )
        
        # Fallback to strategy1
        if not os.path.exists(self.step1_mcfp_file):
            self.step1_mcfp_file = os.path.join(
                self.result_dir_base, 'strategy1', 'step_1',
                'mcfp_results_flows_4_commodities.csv'
            )
        
        # Load config
        config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
        self.config = load_yaml_file(config_file)
        
        # Extract paths info and ratios
        if os.path.exists(self.step1_mcfp_file):
            self.paths_info = extract_paths_info_from_step1(self.step1_mcfp_file)
            self.path_ratios = extract_path_ratios_from_csv(self.step1_mcfp_file)
        else:
            self.paths_info = None
            self.path_ratios = None
    
    def test_4_1_optimization_variables(self):
        """
        Test 4.1: Optimization variable definition.
        
        Purpose: Verify that optimization variables are correctly defined.
        """
        if self.paths_info is None:
            self.skipTest(f"Paths info not available")
        
        # Test vector conversion
        ratios_vector, index_mapping = _path_ratios_dict_to_vector(
            self.path_ratios, self.paths_info
        )
        
        # Verify vector structure
        self.assertIsInstance(ratios_vector, np.ndarray, "Vector should be numpy array")
        
        # Count expected number of paths
        expected_num_paths = sum(len(info['paths']) for info in self.paths_info.values())
        self.assertEqual(len(ratios_vector), expected_num_paths,
                        f"Vector length should be {expected_num_paths}")
        
        # Verify we can convert back
        ratios_dict_back = _path_ratios_vector_to_dict(
            ratios_vector, self.paths_info, index_mapping
        )
        
        # Verify structure matches original
        self.assertEqual(len(ratios_dict_back), len(self.path_ratios),
                        "Dict should have same number of commodities")
        
        print(f"\n✓ Test 4.1 PASSED")
        print(f"  Number of variables: {len(ratios_vector)}")
        print(f"  Commodities: {len(self.paths_info)}")
        for cid in sorted(self.paths_info.keys()):
            print(f"    Commodity {cid}: {len(self.paths_info[cid]['paths'])} paths")
    
    def test_4_2_constraints(self):
        """
        Test 4.2: Constraint verification.
        
        Purpose: Verify that constraints are correctly satisfied.
        """
        if self.paths_info is None:
            self.skipTest(f"Paths info not available")
        
        # Test ratio sum constraints
        for commodity_id, ratios in self.path_ratios.items():
            total = sum(ratios.values())
            self.assertAlmostEqual(total, 1.0, places=6,
                                  msg=f"Commodity {commodity_id} ratios should sum to 1.0")
        
        # Test non-negativity
        for commodity_id, ratios in self.path_ratios.items():
            for path, ratio in ratios.items():
                self.assertGreaterEqual(ratio, 0.0,
                                       msg=f"Ratio for commodity {commodity_id}, path {path} should be >= 0")
        
        print(f"\n✓ Test 4.2 PASSED")
        print(f"  All constraints satisfied:")
        print(f"    - Ratio sum = 1.0 for all commodities")
        print(f"    - All ratios >= 0")
    
    def test_4_3_optimization_solve(self):
        """
        Test 4.3: Optimization solving.
        
        Purpose: Verify that optimization can converge and constraints are satisfied.
        """
        if self.paths_info is None:
            self.skipTest(f"Paths info not available")
        
        # Load sequence
        sequence_file = os.path.join(src_dir, 'results', 'arrival_rate_sequence_10_steps.csv')
        if not os.path.exists(sequence_file):
            self.skipTest(f"Sequence file not found: {sequence_file}")
        
        sequence_df = pd.read_csv(sequence_file, index_col=0)
        
        # Run optimization (use Step 1 ratios as initial guess)
        print("\n  Running optimization (this may take a moment)...")
        result = optimize_global_path_ratios(
            sequence_df, self.paths_info, self.config,
            initial_ratios=self.path_ratios, method='SLSQP'
        )
        
        # Verify optimization status
        opt_result = result['optimization_result']
        self.assertTrue(opt_result.success,
                       f"Optimization should succeed, but got: {opt_result.message}")
        
        # Verify constraints are satisfied
        optimal_ratios = result['optimal_ratios']
        for commodity_id, ratios in optimal_ratios.items():
            total = sum(ratios.values())
            self.assertAlmostEqual(total, 1.0, places=5,
                                  msg=f"Optimal ratios for commodity {commodity_id} should sum to 1.0")
            
            for path, ratio in ratios.items():
                self.assertGreaterEqual(ratio, -1e-6,  # Allow small negative due to numerical error
                                       msg=f"Optimal ratio should be >= 0")
        
        print(f"\n✓ Test 4.3 PASSED")
        print(f"  Optimization status: {opt_result.status}")
        print(f"  Optimal average utilization: {result['optimal_value']:.4f}%")
        print(f"  Number of iterations: {opt_result.nit}")
        print(f"  Constraints satisfied: Yes")


def run_phase1_tests():
    """Run Phase 1 tests."""
    print("=" * 80)
    print("Phase 1: Path Set Extraction and Validation")
    print("=" * 80)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGlobalOptimalRatioPhase1)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_phase2_tests():
    """Run Phase 2 tests."""
    print("=" * 80)
    print("Phase 2: Single-Step Utilization Calculation")
    print("=" * 80)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGlobalOptimalRatioPhase2)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_phase3_tests():
    """Run Phase 3 tests."""
    print("=" * 80)
    print("Phase 3: Multi-Step Average Utilization Calculation")
    print("=" * 80)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGlobalOptimalRatioPhase3)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_phase4_tests():
    """Run Phase 4 tests."""
    print("=" * 80)
    print("Phase 4: Optimization Problem Setup and Solving")
    print("=" * 80)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGlobalOptimalRatioPhase4)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_all_phases():
    """Run all test phases sequentially."""
    phases = [
        ("Phase 1", run_phase1_tests),
        ("Phase 2", run_phase2_tests),
        ("Phase 3", run_phase3_tests),
        ("Phase 4", run_phase4_tests),
    ]
    
    results = {}
    for phase_name, test_func in phases:
        success = test_func()
        results[phase_name] = success
        print()
        
        if not success:
            print(f"✗ {phase_name} FAILED - Stopping here")
            break
    
    return all(results.values())


if __name__ == '__main__':
    # Check if specific phase is requested
    import sys
    if len(sys.argv) > 1:
        phase = sys.argv[1]
        if phase == '1':
            success = run_phase1_tests()
        elif phase == '2':
            success = run_phase2_tests()
        elif phase == '3':
            success = run_phase3_tests()
        elif phase == '4':
            success = run_phase4_tests()
        else:
            success = run_all_phases()
    else:
        success = run_all_phases()
    
    sys.exit(0 if success else 1)

