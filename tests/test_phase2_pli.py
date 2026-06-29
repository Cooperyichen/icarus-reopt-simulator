#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2: PLI calculation verification tests.

Tests that step PLI includes Time Limit Drops and overall PLI excludes recovered packets.
"""

import unittest
import sys
import os

# Add the project src directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

from tests.utils.test_helpers import create_test_config


class TestPhase2PLI(unittest.TestCase):
    """Phase 2: PLI calculation verification tests."""
    
    def test_2_1_step_pli_includes_time_limit_drops(self):
        """
        Test 2.1: Step PLI Includes Time Limit Drops
        Purpose: Verify that step PLI correctly includes Time Limit Drops
        """
        config = create_test_config()
        # Configure for short simulation to create Time Limit Drops
        config['simulation']['simulation_time'] = 20  # 20ms - short to create packets in transit
        config['simulation']['generation_finish_time'] = 20
        config['fixed_demand']['arrival_rate'] = [100, 100]  # 100 packets/s
        
        result_dir = os.path.join(project_path, 'tests', 'test_results_phase2')
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
        
        # Run simulation
        all_flows, switches, blocked_flows = simulator.run_simulation_with_rb(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        # Calculate step PLI
        step_stats = simulator.calculate_step_pli(step_id=1, all_flows=all_flows)
        
        print(f"\nTest 2.1 Results:")
        print(f"  Step Sent: {step_stats['step_sent']}")
        print(f"  Step Received: {step_stats['step_received']}")
        print(f"  Buffer Drops: {step_stats['step_buffer_drops']}")
        print(f"  Time Limit Drops: {step_stats['step_time_limit_drops']}")
        print(f"  Step PLI: {step_stats['step_pli']:.2f}%")
        
        # Pre-condition check: if no packets were sent, skip the test
        if step_stats['step_sent'] == 0:
            self.skipTest("No packets sent in simulation")
        
        # Verify: step_sent = step_received + step_buffer_drops + step_time_limit_drops
        calculated_total = (step_stats['step_received'] + 
                           step_stats['step_buffer_drops'] + 
                           step_stats['step_time_limit_drops'])
        
        self.assertEqual(step_stats['step_sent'], calculated_total,
                        msg=f"Step sent ({step_stats['step_sent']}) != received + buffer + time_limit ({calculated_total})")
        
        # Verify: step_pli includes Time Limit Drops
        expected_pli = ((step_stats['step_buffer_drops'] + step_stats['step_time_limit_drops']) / 
                       step_stats['step_sent'] * 100) if step_stats['step_sent'] > 0 else 0
        
        self.assertAlmostEqual(step_stats['step_pli'], expected_pli, places=1,
                              msg=f"Step PLI ({step_stats['step_pli']}) != expected ({expected_pli})")
        
        return {
            'step_sent': step_stats['step_sent'],
            'step_received': step_stats['step_received'],
            'step_buffer_drops': step_stats['step_buffer_drops'],
            'step_time_limit_drops': step_stats['step_time_limit_drops'],
            'step_pli': step_stats['step_pli'],
            'status': 'PASS'
        }
    
    def test_2_2_overall_pli_excludes_recovered(self):
        """
        Test 2.2: Overall PLI Excludes Recovered Packets
        Purpose: Verify that overall PLI correctly excludes recovered Time Limit Drops
        This test uses REAL multi-step simulation (not manual simulation)
        """
        config = create_test_config()
        # Configure for 2-step simulation
        config['simulation']['num_steps'] = 2
        config['simulation']['step_duration'] = 50  # 50ms per step
        # Step 1: Short time to create Time Limit Drops
        config['simulation']['simulation_time'] = 50  # Will be overridden by step_duration
        config['simulation']['generation_finish_time'] = 50  # Generate for full step 1 time
        config['fixed_demand']['arrival_rate'] = [150, 150]  # High rate to create Time Limit Drops
        
        result_dir = os.path.join(project_path, 'tests', 'test_results_phase2')
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
        
        # Run REAL multi-step simulation
        all_flows, switches, blocked_flows, multi_step_stats = simulator.run_multi_step_simulation(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        # Extract step statistics
        step1_stats = multi_step_stats['all_steps_stats'][0]
        step2_stats = multi_step_stats['all_steps_stats'][1]
        overall_stats = multi_step_stats['overall_stats']
        
        print(f"\nTest 2.2 Results:")
        print(f"  Step 1 - Sent: {step1_stats['step_sent']}, Received: {step1_stats['step_received']}, Time Limit Drops: {step1_stats['step_time_limit_drops']}")
        print(f"  Step 2 - Sent: {step2_stats['step_sent']}, Received: {step2_stats['step_received']}")
        print(f"  Total Time Limit Drops: {overall_stats['total_time_limit_drops']}")
        print(f"  Recovered Time Limit: {overall_stats['recovered_time_limit_count']}")
        print(f"  Final Unrecovered: {overall_stats['final_unrecovered_time_limit']}")
        print(f"  Overall PLI: {overall_stats['overall_pli']:.2f}%")
        
        # Pre-condition: Step 1 should have Time Limit Drops
        if step1_stats['step_time_limit_drops'] == 0:
            self.skipTest("No Time Limit Drops in Step 1 - cannot test recovery")
        
        # Verify: Recovered packets were actually received (not just manually marked)
        # This is the key verification - recovered packets should be > 0 in real simulation
        self.assertGreater(overall_stats['recovered_time_limit_count'], 0,
                          "Recovered packets should be > 0 in real multi-step simulation")
        
        # Verify: Recovered count should not exceed Step 1 Time Limit Drops
        step1_time_limit_drops = step1_stats['step_time_limit_drops']
        self.assertLessEqual(overall_stats['recovered_time_limit_count'], step1_time_limit_drops,
                            msg=f"Recovered count ({overall_stats['recovered_time_limit_count']}) should not exceed Step 1 Time Limit Drops ({step1_time_limit_drops})")
        
        # Verify: Final unrecovered = total - recovered
        expected_unrecovered = overall_stats['total_time_limit_drops'] - overall_stats['recovered_time_limit_count']
        self.assertEqual(overall_stats['final_unrecovered_time_limit'], expected_unrecovered,
                        msg=f"Unrecovered mismatch: {overall_stats['final_unrecovered_time_limit']} != {expected_unrecovered}")
        
        # Verify: Overall PLI calculation is correct
        expected_overall_pli = ((overall_stats['total_buffer_drops'] + 
                                overall_stats['final_unrecovered_time_limit']) / 
                               overall_stats['total_sent_all_steps'] * 100) if overall_stats['total_sent_all_steps'] > 0 else 0
        
        self.assertAlmostEqual(overall_stats['overall_pli'], expected_overall_pli, places=1,
                              msg=f"Overall PLI ({overall_stats['overall_pli']}) != expected ({expected_overall_pli})")
        
        # Verify: Step 2 received packets should include recovered packets
        # Step 2 received should be >= recovered count (some recovered packets should be received)
        self.assertGreaterEqual(step2_stats['step_received'], overall_stats['recovered_time_limit_count'] * 0.5,
                               msg=f"Step 2 should receive at least 50% of recovered packets. Received: {step2_stats['step_received']}, Recovered: {overall_stats['recovered_time_limit_count']}")
        
        return {
            'step1_time_limit_drops': step1_stats['step_time_limit_drops'],
            'step2_received': step2_stats['step_received'],
            'total_time_limit_drops': overall_stats['total_time_limit_drops'],
            'recovered_count': overall_stats['recovered_time_limit_count'],
            'final_unrecovered': overall_stats['final_unrecovered_time_limit'],
            'overall_pli': overall_stats['overall_pli'],
            'status': 'PASS'
        }
    
    def test_2_3_pli_consistency(self):
        """
        Test 2.3: PLI Calculation Consistency
        Purpose: Verify that PLI calculations are consistent
        """
        config = create_test_config()
        config['simulation']['simulation_time'] = 20
        config['simulation']['generation_finish_time'] = 20
        config['fixed_demand']['arrival_rate'] = [100, 100]
        
        result_dir = os.path.join(project_path, 'tests', 'test_results_phase2')
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
        
        # Run simulation
        all_flows, switches, blocked_flows = simulator.run_simulation_with_rb(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        # Calculate step PLI
        step_stats = simulator.calculate_step_pli(step_id=1, all_flows=all_flows)
        
        # Calculate overall PLI (single step)
        all_steps_stats = [step_stats]
        overall_stats = simulator.calculate_overall_pli(
            all_steps_stats=all_steps_stats,
            final_flows=all_flows,
            final_switches=switches
        )
        
        print(f"\nTest 2.3 Results:")
        print(f"  Step Sent: {step_stats['step_sent']}")
        print(f"  Step PLI: {step_stats['step_pli']:.2f}%")
        print(f"  Overall Sent: {overall_stats['total_sent_all_steps']}")
        print(f"  Overall PLI: {overall_stats['overall_pli']:.2f}%")
        
        # Verify consistency: step_sent = total_sent_all_steps (for single step)
        self.assertEqual(step_stats['step_sent'], overall_stats['total_sent_all_steps'],
                        msg=f"Step sent ({step_stats['step_sent']}) != overall sent ({overall_stats['total_sent_all_steps']})")
        
        # Verify: step PLI and overall PLI should be the same for single step (if no recovery)
        # But overall PLI excludes recovered packets, so they might differ
        # For this test, we verify the calculation logic is consistent
        
        # Verify: breakdown is consistent
        breakdown = overall_stats['breakdown']
        calculated_total_loss = breakdown['buffer_overflow_loss'] + breakdown['unrecovered_time_limit_loss']
        self.assertEqual(breakdown['total_loss'], calculated_total_loss,
                        msg=f"Total loss ({breakdown['total_loss']}) != buffer + unrecovered ({calculated_total_loss})")
        
        return {
            'step_sent': step_stats['step_sent'],
            'overall_sent': overall_stats['total_sent_all_steps'],
            'step_pli': step_stats['step_pli'],
            'overall_pli': overall_stats['overall_pli'],
            'status': 'PASS'
        }


if __name__ == '__main__':
    unittest.main()

