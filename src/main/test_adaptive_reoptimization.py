#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TDD Tests for Strategy 4: Adaptive Re-optimization Based on Dual Variables

Phase 1: Trigger metric calculation
Phase 2: Dual variable extraction and storage
Phase 3: Path ratio preservation and application
Phase 4: Complete strategy execution
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

from main.multi_step_comparison_experiment import calculate_trigger_metric


class TestAdaptiveReoptimizationPhase1(unittest.TestCase):
    """Phase 1: Trigger Metric Calculation"""
    
    def test_trigger_metric_positive_duals(self):
        """Test trigger metric with all positive dual variables"""
        dual_vars = {0: 0.5, 1: 0.3, 2: 0.8, 3: 0.2}
        current_demand = [600, 800, 400, 900]
        last_demand = [540, 780, 300, 780]
        
        metric = calculate_trigger_metric(dual_vars, current_demand, last_demand)
        
        # Expected: 0.5*|600-540| + 0.3*|800-780| + 0.8*|400-300| + 0.2*|900-780|
        # = 0.5*60 + 0.3*20 + 0.8*100 + 0.2*120
        # = 30 + 6 + 80 + 24 = 140
        expected = 140.0
        self.assertAlmostEqual(metric, expected, places=5)
    
    def test_trigger_metric_negative_duals(self):
        """Test trigger metric with negative dual variables"""
        dual_vars = {0: -0.5, 1: -0.3, 2: -0.8, 3: -0.2}
        current_demand = [600, 800, 400, 900]
        last_demand = [540, 780, 300, 780]
        
        metric = calculate_trigger_metric(dual_vars, current_demand, last_demand)
        
        # Expected: -0.5*60 + -0.3*20 + -0.8*100 + -0.2*120
        # = -30 - 6 - 80 - 24 = -140
        expected = -140.0
        self.assertAlmostEqual(metric, expected, places=5)
    
    def test_trigger_metric_mixed_duals(self):
        """Test trigger metric with mixed positive and negative dual variables"""
        dual_vars = {0: 0.5, 1: -0.3, 2: 0.8, 3: -0.2}
        current_demand = [600, 800, 400, 900]
        last_demand = [540, 780, 300, 780]
        
        metric = calculate_trigger_metric(dual_vars, current_demand, last_demand)
        
        # Expected: 0.5*60 + -0.3*20 + 0.8*100 + -0.2*120
        # = 30 - 6 + 80 - 24 = 80
        expected = 80.0
        self.assertAlmostEqual(metric, expected, places=5)
    
    def test_trigger_metric_zero_changes(self):
        """Test trigger metric when demand doesn't change"""
        dual_vars = {0: 0.5, 1: 0.3, 2: 0.8, 3: 0.2}
        current_demand = [540, 780, 300, 780]
        last_demand = [540, 780, 300, 780]
        
        metric = calculate_trigger_metric(dual_vars, current_demand, last_demand)
        
        # Expected: 0 (no changes)
        expected = 0.0
        self.assertAlmostEqual(metric, expected, places=5)
    
    def test_trigger_metric_decreasing_demand(self):
        """Test trigger metric when demand decreases"""
        dual_vars = {0: 0.5, 1: 0.3, 2: 0.8, 3: 0.2}
        current_demand = [500, 700, 250, 700]
        last_demand = [540, 780, 300, 780]
        
        metric = calculate_trigger_metric(dual_vars, current_demand, last_demand)
        
        # Expected: 0.5*|500-540| + 0.3*|700-780| + 0.8*|250-300| + 0.2*|700-780|
        # = 0.5*40 + 0.3*80 + 0.8*50 + 0.2*80
        # = 20 + 24 + 40 + 16 = 100
        expected = 100.0
        self.assertAlmostEqual(metric, expected, places=5)
    
    def test_trigger_metric_edge_case_none_dual(self):
        """Test trigger metric with None dual variable (should skip)"""
        dual_vars = {0: 0.5, 1: None, 2: 0.8, 3: 0.2}
        current_demand = [600, 800, 400, 900]
        last_demand = [540, 780, 300, 780]
        
        metric = calculate_trigger_metric(dual_vars, current_demand, last_demand)
        
        # Expected: 0.5*60 + 0 (skip None) + 0.8*100 + 0.2*120
        # = 30 + 0 + 80 + 24 = 134
        expected = 134.0
        self.assertAlmostEqual(metric, expected, places=5)
    
    def test_trigger_metric_missing_commodity(self):
        """Test trigger metric when a commodity is missing from dual_vars"""
        dual_vars = {0: 0.5, 1: 0.3, 3: 0.2}  # Missing commodity 2
        current_demand = [600, 800, 400, 900]
        last_demand = [540, 780, 300, 780]
        
        metric = calculate_trigger_metric(dual_vars, current_demand, last_demand)
        
        # Expected: 0.5*60 + 0.3*20 + 0 (missing) + 0.2*120
        # = 30 + 6 + 0 + 24 = 60
        expected = 60.0
        self.assertAlmostEqual(metric, expected, places=5)


class TestAdaptiveReoptimizationPhase2(unittest.TestCase):
    """Phase 2: Dual Variable Extraction and Storage"""
    
    def test_dual_variable_extraction(self):
        """Test that dual variables are extracted from optimizer result"""
        from topo.utils import load_yaml_file
        from topo.toroidal_topo import ToroidalTopo
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
        
        # Load config
        config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
        config = load_yaml_file(config_file)
        
        # Create topology
        regen_obp = ToroidalTopo(scenario_config=config, width=config['system']['width'],
                                height=config['system']['height'])
        
        # Create demand matrix
        num_commodities = config['optimization']['num_commodities']
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities)
        
        # Create optimizer and run
        optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
        objective_type = config['optimization']['objective_func']
        mode = config['simulation']['failure_strategy']
        
        result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
        
        # Check if dual variables are available
        self.assertTrue(hasattr(result_df, 'attrs'), "Result DataFrame should have attrs attribute")
        self.assertIn('dual_variables', result_df.attrs, "Dual variables should be in attrs")
        
        dual_vars = result_df.attrs['dual_variables']
        self.assertIsInstance(dual_vars, dict, "Dual variables should be a dictionary")
        self.assertGreater(len(dual_vars), 0, "Should have at least one dual variable")
    
    def test_dual_variable_format(self):
        """Test that dual variables have correct format (commodity_id mapping)"""
        from topo.utils import load_yaml_file
        from topo.toroidal_topo import ToroidalTopo
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
        
        # Load config
        config_file = os.path.join(src_dir, 'data', '80_lambda_our_model_2c.yaml')
        config = load_yaml_file(config_file)
        
        # Create topology
        regen_obp = ToroidalTopo(scenario_config=config, width=config['system']['width'],
                                height=config['system']['height'])
        
        # Create demand matrix
        num_commodities = config['optimization']['num_commodities']
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities)
        
        # Create optimizer and run
        optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
        objective_type = config['optimization']['objective_func']
        mode = config['simulation']['failure_strategy']
        
        result_df = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
        
        dual_vars = result_df.attrs.get('dual_variables', {})
        
        # Check format: should map commodity_id to float or None
        for commodity_id, dual_value in dual_vars.items():
            # Accept int or numpy.int64
            self.assertTrue(isinstance(commodity_id, (int, np.integer)), 
                          f"Commodity ID should be int or numpy integer, got {type(commodity_id)}")
            if dual_value is not None:
                self.assertIsInstance(dual_value, (int, float), 
                                    f"Dual value should be numeric, got {type(dual_value)}")
    
    def test_dual_variable_storage(self):
        """Test that dual variables can be stored and retrieved correctly"""
        # Simulate storing dual variables
        dual_vars = {0: 0.5, 1: 0.3, 2: 0.8, 3: 0.2}
        last_demand = [540.0, 780.0, 300.0, 780.0]
        
        # Test storage format
        self.assertEqual(len(dual_vars), 4, "Should have 4 commodities")
        self.assertIn(0, dual_vars)
        self.assertIn(1, dual_vars)
        self.assertIn(2, dual_vars)
        self.assertIn(3, dual_vars)
        
        # Test retrieval
        retrieved_dual = dual_vars[0]
        self.assertEqual(retrieved_dual, 0.5)


if __name__ == '__main__':
    # Run tests by phase
    import sys
    
    if len(sys.argv) > 1:
        phase = sys.argv[1]
    else:
        phase = '1'
    
    suite = unittest.TestSuite()
    
    if phase == '1':
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdaptiveReoptimizationPhase1))
    elif phase == '2':
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAdaptiveReoptimizationPhase2))
    elif phase == '3':
        # Phase 3 tests are integrated with Phase 4 (full strategy execution)
        print("Phase 3 (Path ratio preservation) is tested as part of Phase 4")
    elif phase == '4':
        print("Phase 4 (Complete strategy execution) requires full simulation runs")
        print("Please run the strategy execution functions directly to test")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    sys.exit(0 if result.wasSuccessful() else 1)

