#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for multi-step simulation integration.

Tests the complete multi-step simulation flow including state saving, restoration, and PLI calculation.
"""

import unittest
import sys
import os
import simpy

# Add the project src directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

from tests.utils.test_helpers import create_test_config


class TestMultiStepSimulation(unittest.TestCase):
    """Test multi-step simulation integration."""
    
    def test_two_step_simulation(self):
        """
        Test two-step simulation with temporal causality verification.
        Purpose: Verify that packets from Step 1 Time Limit Drops are recovered and received in Step 2
        """
        config = create_test_config()
        # Configure for 2 steps
        config['simulation']['num_steps'] = 2
        config['simulation']['step_duration'] = 20  # Step 1: 20ms (short to create Time Limit Drops)
        config['simulation']['simulation_time'] = 20  # Will be overridden by step_duration per step
        # Step 1: Short time with high traffic to create Time Limit Drops
        config['simulation']['generation_finish_time'] = 20  # Generate for full step 1 time
        config['fixed_demand']['arrival_rate'] = [800, 800]  # High rate but feasible for optimizer
        config['simulation']['buffer_size'] = 8000  # Smaller buffer to create congestion
        config['system']['interlink_capacity'] = 5000000  # Lower capacity (5 Mbps) to slow down transmission
        # Note: Step 2 will use 10x longer duration (200ms) to allow recovered packets to reach sink
        
        result_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(result_dir, exist_ok=True)
        
        from topo.toroidal_topo import ToroidalTopo
        regen_obp = ToroidalTopo(scenario_config=config, width=4, height=4)
        
        # Generate demand matrix
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=2)
        
        # Run optimization
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
        optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
        objective_type = config['optimization']['objective_func']
        mode = config['simulation']['failure_strategy']
        updated_demand_matrix = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
        
        # Create simulator
        from simulator.simulator import Simulator
        simulator = Simulator(regen_obp, config, result_dir, 1, 'multicommodity', demand_matrix, updated_demand_matrix)
        
        # Run multi-step simulation
        all_flows, switches, blocked_flows, multi_step_stats = simulator.run_multi_step_simulation(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        # Verify basic results
        self.assertIsNotNone(all_flows)
        self.assertIsNotNone(switches)
        self.assertIsNotNone(multi_step_stats)
        self.assertEqual(len(multi_step_stats['all_steps_stats']), 2)
        self.assertIn('overall_stats', multi_step_stats)
        
        # Verify step statistics
        step1_stats = multi_step_stats['all_steps_stats'][0]
        step2_stats = multi_step_stats['all_steps_stats'][1]
        self.assertEqual(step1_stats['step_id'], 1)
        self.assertEqual(step2_stats['step_id'], 2)
        
        # Verify overall statistics
        overall_stats = multi_step_stats['overall_stats']
        self.assertIn('total_sent_all_steps', overall_stats)
        self.assertIn('overall_pli', overall_stats)
        self.assertGreater(overall_stats['total_sent_all_steps'], 0,
                          "No packets sent in multi-step simulation")
        
        print(f"\nTest Two-Step Simulation Results:")
        print(f"  Step 1 - Sent: {step1_stats['step_sent']}, Received: {step1_stats['step_received']}, Time Limit Drops: {step1_stats['step_time_limit_drops']}")
        print(f"  Step 2 - Sent: {step2_stats['step_sent']}, Received: {step2_stats['step_received']}")
        print(f"  Recovered Time Limit Drops: {overall_stats['recovered_time_limit_count']}")
        print(f"  Final Unrecovered: {overall_stats['final_unrecovered_time_limit']}")
        
        # KEY VERIFICATION 1: Step 1 should have Time Limit Drops
        self.assertGreater(step1_stats['step_time_limit_drops'], 0,
                          "Step 1 must have Time Limit Drops to test temporal causality")
        
        # KEY VERIFICATION 2: Recovered packets should be received in Step 2
        # This verifies temporal causality - packets from Step 1 are recovered and received in Step 2
        self.assertGreater(overall_stats['recovered_time_limit_count'], 0,
                          "Recovered packets should be > 0 - temporal causality not working")
        
        # KEY VERIFICATION 3: Step 2 should receive at least some of the recovered packets
        # Step 2 received should be >= 50% of Step 1 Time Limit Drops (at least partial recovery)
        min_expected_recovery = step1_stats['step_time_limit_drops'] * 0.5
        self.assertGreaterEqual(step2_stats['step_received'], min_expected_recovery,
                               f"Step 2 should receive at least 50% of Step 1 Time Limit Drops. "
                               f"Received: {step2_stats['step_received']}, Expected: {min_expected_recovery}")
        
        # Verify: Recovered count should not exceed Step 1 Time Limit Drops
        self.assertLessEqual(overall_stats['recovered_time_limit_count'], step1_stats['step_time_limit_drops'],
                            msg=f"Recovered count ({overall_stats['recovered_time_limit_count']}) should not exceed Step 1 Time Limit Drops ({step1_stats['step_time_limit_drops']})")
        
        # Verify: Overall PLI should correctly exclude recovered packets
        expected_unrecovered = step1_stats['step_time_limit_drops'] - overall_stats['recovered_time_limit_count']
        self.assertEqual(overall_stats['final_unrecovered_time_limit'], expected_unrecovered,
                        msg=f"Final unrecovered mismatch: {overall_stats['final_unrecovered_time_limit']} != {expected_unrecovered}")
    
    def test_3_2_packet_recovery_and_transmission(self):
        """
        Test 3.2: Packet Recovery and Transmission
        Purpose: Specifically verify that recovered packets are actually transmitted and received in subsequent steps
        """
        config = create_test_config()
        # Configure for 2-step simulation
        config['simulation']['num_steps'] = 2
        config['simulation']['step_duration'] = 200  # 200ms per step
        config['simulation']['simulation_time'] = 400
        # Step 1: Short time (20ms effective), high traffic to create Time Limit Drops
        # Step 2: Long time (200ms), low traffic to allow recovery
        config['simulation']['generation_finish_time'] = 20  # Only generate in first 20ms of step 1
        config['fixed_demand']['arrival_rate'] = [200, 200]  # High rate for Step 1
        
        result_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(result_dir, exist_ok=True)
        
        from topo.toroidal_topo import ToroidalTopo
        regen_obp = ToroidalTopo(scenario_config=config, width=4, height=4)
        
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=2)
        
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
        optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
        objective_type = config['optimization']['objective_func']
        mode = config['simulation']['failure_strategy']
        updated_demand_matrix = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
        
        from simulator.simulator import Simulator
        simulator = Simulator(regen_obp, config, result_dir, 1, 'multicommodity', demand_matrix, updated_demand_matrix)
        
        # Run multi-step simulation
        all_flows, switches, blocked_flows, multi_step_stats = simulator.run_multi_step_simulation(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        step1_stats = multi_step_stats['all_steps_stats'][0]
        step2_stats = multi_step_stats['all_steps_stats'][1]
        overall_stats = multi_step_stats['overall_stats']
        
        print(f"\nTest 3.2 Results:")
        print(f"  Step 1 - Sent: {step1_stats['step_sent']}, Received: {step1_stats['step_received']}, Time Limit Drops: {step1_stats['step_time_limit_drops']}")
        print(f"  Step 2 - Sent: {step2_stats['step_sent']}, Received: {step2_stats['step_received']}")
        print(f"  Recovered Count: {overall_stats['recovered_time_limit_count']}")
        print(f"  Step 2 Received >= Recovered: {step2_stats['step_received']} >= {overall_stats['recovered_time_limit_count']}")
        
        # Pre-condition: Step 1 should have Time Limit Drops
        if step1_stats['step_time_limit_drops'] == 0:
            self.skipTest("No Time Limit Drops in Step 1 - cannot test recovery and transmission")
        
        step1_time_limit = step1_stats['step_time_limit_drops']
        recovered_count = overall_stats['recovered_time_limit_count']
        step2_received = step2_stats['step_received']
        
        # KEY VERIFICATION 1: Recovered packets should be > 0
        self.assertGreater(recovered_count, 0,
                          "Recovered packets should be > 0 - recovery mechanism not working")
        
        # KEY VERIFICATION 2: Step 2 received packets should include recovered packets
        # Step 2 received should be >= recovered count (recovered packets should be received)
        self.assertGreaterEqual(step2_received, recovered_count,
                               f"Step 2 received packets ({step2_received}) should be >= recovered count ({recovered_count})")
        
        # KEY VERIFICATION 3: Overall PLI should correctly exclude recovered packets
        expected_unrecovered = step1_time_limit - recovered_count
        self.assertEqual(overall_stats['final_unrecovered_time_limit'], expected_unrecovered,
                        msg=f"Final unrecovered mismatch: {overall_stats['final_unrecovered_time_limit']} != {expected_unrecovered}")
        
        # Verify: Recovered count should not exceed Step 1 Time Limit Drops
        self.assertLessEqual(recovered_count, step1_time_limit,
                            msg=f"Recovered count ({recovered_count}) should not exceed Step 1 Time Limit Drops ({step1_time_limit})")
    
    def test_3_3_temporal_causality(self):
        """
        Test 3.3: Temporal Causality (Core Test)
        Purpose: Verify temporal causality - packets from previous steps continue transmission in subsequent steps
        This is the most critical test for multi-step simulation correctness
        """
        config = create_test_config()
        # Configure for 2-step simulation with extreme conditions
        config['simulation']['num_steps'] = 2
        config['simulation']['step_duration'] = 15  # Step 1: Very short time (15ms), high traffic
        config['simulation']['simulation_time'] = 515  # Step 2: Very long time (500ms), very low traffic
        # Step 1: Very short time (15ms), high traffic to create many Time Limit Drops
        # Step 2: Very long time (500ms), very low traffic to allow recovery
        config['simulation']['generation_finish_time'] = 15  # Generate for full step 1 time
        config['fixed_demand']['arrival_rate'] = [1000, 1000]  # High rate but feasible for optimizer
        config['simulation']['buffer_size'] = 6000  # Smaller buffer to create congestion
        config['system']['interlink_capacity'] = 3000000  # Lower capacity (3 Mbps) to slow down transmission
        
        result_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(result_dir, exist_ok=True)
        
        from topo.toroidal_topo import ToroidalTopo
        regen_obp = ToroidalTopo(scenario_config=config, width=4, height=4)
        
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=2)
        
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
        optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
        objective_type = config['optimization']['objective_func']
        mode = config['simulation']['failure_strategy']
        updated_demand_matrix = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
        
        from simulator.simulator import Simulator
        simulator = Simulator(regen_obp, config, result_dir, 1, 'multicommodity', demand_matrix, updated_demand_matrix)
        
        # Run multi-step simulation
        all_flows, switches, blocked_flows, multi_step_stats = simulator.run_multi_step_simulation(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        step1_stats = multi_step_stats['all_steps_stats'][0]
        step2_stats = multi_step_stats['all_steps_stats'][1]
        overall_stats = multi_step_stats['overall_stats']
        
        print(f"\nTest 3.3 (Temporal Causality) Results:")
        print(f"  Step 1 - Sent: {step1_stats['step_sent']}, Received: {step1_stats['step_received']}, Time Limit Drops: {step1_stats['step_time_limit_drops']}")
        print(f"  Step 2 - Sent: {step2_stats['step_sent']}, Received: {step2_stats['step_received']}")
        print(f"  Recovered Count: {overall_stats['recovered_time_limit_count']}")
        print(f"  Final Unrecovered: {overall_stats['final_unrecovered_time_limit']}")
        
        step1_time_limit = step1_stats['step_time_limit_drops']
        recovered_count = overall_stats['recovered_time_limit_count']
        step2_received = step2_stats['step_received']
        step2_new_sent = step2_stats['step_sent']  # Step 2 new packets (should be very few due to low generation)
        
        # KEY VERIFICATION 1: Step 1 must have significant Time Limit Drops
        self.assertGreaterEqual(step1_time_limit, 10,
                               f"Step 1 must have at least 10 Time Limit Drops to test temporal causality. Actual: {step1_time_limit}")
        
        # KEY VERIFICATION 2: Recovered packets should be a significant portion of Step 1 Time Limit Drops
        # This verifies that the recovery mechanism is working
        recovery_rate = recovered_count / step1_time_limit if step1_time_limit > 0 else 0
        self.assertGreaterEqual(recovery_rate, 0.8,
                               f"Recovery rate should be >= 80%. Actual: {recovery_rate:.2%} ({recovered_count}/{step1_time_limit})")
        
        # KEY VERIFICATION 3: Step 2 received packets should mainly come from recovered packets
        # Since Step 2 has very low traffic (generation_finish_time=10, but step_duration=500),
        # most received packets should be from Step 1 recovery
        self.assertGreaterEqual(step2_received, recovered_count,
                               f"Step 2 received packets ({step2_received}) should be >= recovered count ({recovered_count})")
        
        # KEY VERIFICATION 4: Overall PLI should correctly reflect recovery
        expected_unrecovered = step1_time_limit - recovered_count
        self.assertEqual(overall_stats['final_unrecovered_time_limit'], expected_unrecovered,
                        msg=f"Final unrecovered mismatch: {overall_stats['final_unrecovered_time_limit']} != {expected_unrecovered}")
        
        # Additional verification: Step 2 received should be significantly higher than Step 2 new sent
        # This indicates that recovered packets are being received
        if step2_new_sent > 0:
            recovery_ratio = step2_received / step2_new_sent
            print(f"  Step 2 Recovery Ratio (received/new_sent): {recovery_ratio:.2f}")
            # If Step 2 received is much higher than new sent, it indicates recovered packets are being received
            self.assertGreater(recovery_ratio, 1.0,
                              f"Step 2 received ({step2_received}) should be > new sent ({step2_new_sent}) if recovery is working")
    
    def test_single_step_fallback(self):
        """Test that num_steps=1 falls back to single-step simulation."""
        config = create_test_config()
        config['simulation']['num_steps'] = 1
        
        result_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(result_dir, exist_ok=True)
        
        from topo.toroidal_topo import ToroidalTopo
        regen_obp = ToroidalTopo(scenario_config=config, width=4, height=4)
        
        demand_matrix = regen_obp.generate_demand_matrix(num_commodities=2)
        
        from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
        optimizer = MultiCommodityOptimizer(config, regen_obp.graph, regen_obp.interlinks)
        objective_type = config['optimization']['objective_func']
        mode = config['simulation']['failure_strategy']
        updated_demand_matrix = optimizer.solve_mcfp_path_formulation(demand_matrix, objective_type, mode)
        
        from simulator.simulator import Simulator
        simulator = Simulator(regen_obp, config, result_dir, 1, 'multicommodity', demand_matrix, updated_demand_matrix)
        
        # Run multi-step simulation (should fall back to single-step)
        all_flows, switches, blocked_flows, multi_step_stats = simulator.run_multi_step_simulation(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        # Verify it ran as single-step
        self.assertEqual(len(multi_step_stats['all_steps_stats']), 1)
        self.assertEqual(multi_step_stats['all_steps_stats'][0]['step_id'], 1)


if __name__ == '__main__':
    unittest.main()

