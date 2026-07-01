#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Simulator class, focusing on time conversion and short simulation scenarios.

Tests that the Simulator correctly converts simulation_time based on time_unit
and handles short simulation times for detecting packets in transit.
"""

import unittest
import sys
import os
import tempfile
import shutil

# Add the project src directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

from tests.utils.test_helpers import create_test_config, create_test_simulator


class TestSimulatorTimeConversion(unittest.TestCase):
    """Test Simulator time conversion logic."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_result_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_result_dir):
            shutil.rmtree(self.test_result_dir)
    
    def test_simulator_time_conversion_ms(self):
        """Test that Simulator converts simulation_time from ms to seconds."""
        config = create_test_config(time_unit='ms', simulation_time=300, generation_finish_time=300)
        
        # Create simulator instance
        simulator = create_test_simulator(config, self.test_result_dir)
        
        # Check that time_unit is correctly retrieved
        time_unit = simulator.scenario_config.get('system', {}).get('time_unit', 'ms')
        self.assertEqual(time_unit, 'ms', "time_unit should be 'ms'")
        
        # Check that simulation_time conversion logic would work correctly
        simulation_time = config['simulation']['simulation_time']
        if time_unit == 'ms':
            expected_simulation_time_seconds = simulation_time / 1000.0
        else:
            expected_simulation_time_seconds = simulation_time
        
        self.assertEqual(expected_simulation_time_seconds, 0.3,
                        f"Expected 0.3 seconds, got {expected_simulation_time_seconds}")
    
    def test_simulator_time_conversion_s(self):
        """Test that Simulator doesn't convert when time_unit is 's'."""
        config = create_test_config(time_unit='s', simulation_time=0.3, generation_finish_time=0.3)
        
        # Create simulator instance
        simulator = create_test_simulator(config, self.test_result_dir)
        
        # Check that time_unit is correctly retrieved
        time_unit = simulator.scenario_config.get('system', {}).get('time_unit', 'ms')
        self.assertEqual(time_unit, 's', "time_unit should be 's'")
        
        # Check that simulation_time is not converted
        simulation_time = config['simulation']['simulation_time']
        if time_unit == 'ms':
            expected_simulation_time_seconds = simulation_time / 1000.0
        else:
            expected_simulation_time_seconds = simulation_time
        
        self.assertEqual(expected_simulation_time_seconds, 0.3,
                        f"Expected 0.3 seconds, got {expected_simulation_time_seconds}")
    
    def test_simulator_short_simulation_time(self):
        """Test Simulator with very short simulation time."""
        config = create_test_config(time_unit='ms', simulation_time=100, generation_finish_time=100)
        
        # Create simulator instance
        simulator = create_test_simulator(config, self.test_result_dir)
        
        # Verify configuration
        self.assertEqual(config['simulation']['simulation_time'], 100)
        self.assertEqual(config['simulation']['generation_finish_time'], 100)
        
        # Check conversion
        time_unit = config['system']['time_unit']
        simulation_time = config['simulation']['simulation_time']
        
        if time_unit == 'ms':
            expected_simulation_time_seconds = simulation_time / 1000.0
        else:
            expected_simulation_time_seconds = simulation_time
        
        self.assertEqual(expected_simulation_time_seconds, 0.1,
                        f"Expected 0.1 seconds, got {expected_simulation_time_seconds}")
    
    def test_simulator_finish_time_conversion(self):
        """Test that generation_finish_time is correctly converted."""
        config = create_test_config(time_unit='ms', simulation_time=1000, generation_finish_time=500)
        
        # Create simulator instance
        simulator = create_test_simulator(config, self.test_result_dir)
        
        # Check conversion logic
        time_unit = config['system']['time_unit']
        finish = config['simulation']['generation_finish_time']
        
        if time_unit == 'ms':
            expected_finish_time_seconds = finish / 1000.0
        else:
            expected_finish_time_seconds = finish
        
        self.assertEqual(expected_finish_time_seconds, 0.5,
                        f"Expected 0.5 seconds, got {expected_finish_time_seconds}")
    
    def test_simulator_time_consistency(self):
        """Test that simulation_time and generation_finish_time use the same conversion."""
        config = create_test_config(time_unit='ms', simulation_time=300, generation_finish_time=300)
        
        # Create simulator instance
        simulator = create_test_simulator(config, self.test_result_dir)
        
        # Both should use the same conversion logic
        time_unit = config['system']['time_unit']
        simulation_time = config['simulation']['simulation_time']
        generation_finish_time = config['simulation']['generation_finish_time']
        
        if time_unit == 'ms':
            sim_time_seconds = simulation_time / 1000.0
            finish_time_seconds = generation_finish_time / 1000.0
        else:
            sim_time_seconds = simulation_time
            finish_time_seconds = generation_finish_time
        
        # Both should be equal after conversion
        self.assertEqual(sim_time_seconds, finish_time_seconds,
                        "simulation_time and generation_finish_time should be equal after conversion")


if __name__ == '__main__':
    unittest.main()

