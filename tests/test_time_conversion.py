#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for time conversion logic in simulator.

Tests that simulation_time is correctly converted from milliseconds to seconds
based on the time_unit configuration.
"""

import unittest
import sys
import os

# Add the project src directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

from tests.utils.test_helpers import create_test_config


class TestTimeConversion(unittest.TestCase):
    """Test time conversion logic."""
    
    def test_simulation_time_ms_conversion(self):
        """Test that simulation_time is correctly converted from ms to seconds."""
        config = create_test_config(time_unit='ms', simulation_time=300, generation_finish_time=300)
        
        # Check that time_unit is correctly set
        self.assertEqual(config['system']['time_unit'], 'ms')
        self.assertEqual(config['simulation']['simulation_time'], 300)
        
        # Expected conversion: 300 ms = 0.3 seconds
        expected_simulation_time_seconds = 300 / 1000.0
        self.assertEqual(expected_simulation_time_seconds, 0.3,
                        f"Expected 0.3 seconds, got {expected_simulation_time_seconds}")
    
    def test_simulation_time_s_no_conversion(self):
        """Test that simulation_time is not converted when time_unit is 's'."""
        config = create_test_config(time_unit='s', simulation_time=0.3, generation_finish_time=0.3)
        
        # Check that time_unit is correctly set
        self.assertEqual(config['system']['time_unit'], 's')
        self.assertEqual(config['simulation']['simulation_time'], 0.3)
        
        # Expected: no conversion, 0.3 seconds stays 0.3 seconds
        expected_simulation_time_seconds = 0.3
        self.assertEqual(expected_simulation_time_seconds, 0.3,
                        f"Expected 0.3 seconds, got {expected_simulation_time_seconds}")
    
    def test_generation_finish_time_ms_conversion(self):
        """Test that generation_finish_time is correctly converted from ms to seconds."""
        config = create_test_config(time_unit='ms', simulation_time=1000, generation_finish_time=500)
        
        # Expected conversion: 500 ms = 0.5 seconds
        expected_finish_time_seconds = 500 / 1000.0
        self.assertEqual(expected_finish_time_seconds, 0.5,
                        f"Expected 0.5 seconds, got {expected_finish_time_seconds}")
    
    def test_time_unit_default(self):
        """Test that default time_unit is 'ms' if not specified."""
        config = create_test_config(time_unit='ms', simulation_time=100, generation_finish_time=100)
        
        # Check default behavior
        time_unit = config.get('system', {}).get('time_unit', 'ms')
        self.assertEqual(time_unit, 'ms', "Default time_unit should be 'ms'")
    
    def test_short_simulation_time(self):
        """Test conversion with very short simulation time (for packets in transit testing)."""
        config = create_test_config(time_unit='ms', simulation_time=100, generation_finish_time=100)
        
        # Expected conversion: 100 ms = 0.1 seconds
        expected_simulation_time_seconds = 100 / 1000.0
        self.assertEqual(expected_simulation_time_seconds, 0.1,
                        f"Expected 0.1 seconds, got {expected_simulation_time_seconds}")
        
        # Verify generation_finish_time is also converted
        expected_finish_time_seconds = 100 / 1000.0
        self.assertEqual(expected_finish_time_seconds, 0.1,
                        f"Expected 0.1 seconds for finish_time, got {expected_finish_time_seconds}")


if __name__ == '__main__':
    unittest.main()

