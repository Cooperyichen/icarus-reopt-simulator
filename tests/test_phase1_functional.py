#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1: Functional tests for state saving and restoration in real simulation scenarios.

These tests verify the complete functionality in realistic simulation environments,
unlike unit tests which test individual methods in isolation.
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


class TestPhase1Functional(unittest.TestCase):
    """Phase 1: Functional tests for state saving and restoration."""
    
    def test_1_1_state_saving_completeness(self):
        """
        Test 1.1: State Saving Completeness
        Purpose: Verify that state saving is complete, all packets are correctly saved
        """
        config = create_test_config()
        # Configure for very short simulation to create packets in queues and wires
        config['simulation']['simulation_time'] = 10  # 10ms - very short to create packets in transit
        config['simulation']['generation_finish_time'] = 10
        config['fixed_demand']['arrival_rate'] = [50, 50]  # 50 packets/s - lower rate for faster test
        
        result_dir = os.path.join(project_path, 'tests', 'test_results_phase1')
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
        
        # Run simulation to create packets in queues and wires
        all_flows, switches, blocked_flows = simulator.run_simulation_with_rb(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        # Save complete state
        state = simulator.save_simulation_state(step_id=1, all_flows=all_flows)
        
        # Count packets in queues
        packets_in_queues_count = sum(len(packets) for packets in state['packets_in_queues'].values())
        
        # Count packets in wires
        packets_in_wires_count = sum(len(packet_info_list) for packet_info_list in state['packets_in_wires'].values())
        
        total_saved_packets = packets_in_queues_count + packets_in_wires_count
        
        # Verify completeness
        print(f"\nTest 1.1 Results:")
        print(f"  Packets in queues: {packets_in_queues_count}")
        print(f"  Packets in wires: {packets_in_wires_count}")
        print(f"  Total saved packets: {total_saved_packets}")
        
        # Verify: state should contain all necessary components
        self.assertIn('packets_in_queues', state)
        self.assertIn('packets_in_wires', state)
        self.assertIn('port_statistics', state)
        self.assertIn('flow_statistics', state)
        
        # Verify: should have some packets saved to test state saving
        self.assertGreater(total_saved_packets, 0, 
                          "No packets saved - cannot verify state saving functionality")
        
        return {
            'packets_in_queues': packets_in_queues_count,
            'packets_in_wires': packets_in_wires_count,
            'total_saved': total_saved_packets,
            'status': 'PASS'
        }
    
    def test_1_2_state_restoration_correctness(self):
        """
        Test 1.2: State Restoration Correctness
        Purpose: Verify that state restoration is correct, restored packets are in correct locations
        """
        config = create_test_config()
        config['simulation']['simulation_time'] = 50
        config['simulation']['generation_finish_time'] = 50
        config['fixed_demand']['arrival_rate'] = [100, 100]
        
        result_dir = os.path.join(project_path, 'tests', 'test_results_phase1')
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
        
        # Step 1: Run simulation and save state
        all_flows, switches, blocked_flows = simulator.run_simulation_with_rb(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        # Save state
        previous_state = simulator.save_simulation_state(step_id=1, all_flows=all_flows)
        
        saved_queues_count = sum(len(packets) for packets in previous_state['packets_in_queues'].values())
        saved_wires_count = sum(len(packet_info_list) for packet_info_list in previous_state['packets_in_wires'].values())
        total_saved = saved_queues_count + saved_wires_count
        
        # Step 2: Create new environment and restore state
        simulator.env = simpy.rt.RealtimeEnvironment(initial_time=0, factor=0.0000001, strict=False)
        
        # Temporarily adjust generation_finish_time for infrastructure creation
        original_finish_time = config['simulation']['generation_finish_time']
        config['simulation']['generation_finish_time'] = 0.001  # Match minimal simulation time
        
        # Re-run simulation to create infrastructure (switches and wires)
        # Use minimal time to just create infrastructure
        temp_flows, temp_switches, temp_blocked = simulator.run_simulation_with_rb(
            updated_demand_matrix, demand_matrix, 0.001, 1  # 1ms just to create infrastructure
        )
        
        # Restore original finish_time
        config['simulation']['generation_finish_time'] = original_finish_time
        
        # Restore state
        time_offset = 0.1  # 100ms offset
        restore_result = simulator.restore_simulation_state(previous_state, time_offset=time_offset)
        
        # Count restored packets
        restored_queue_count = len(restore_result['recovered_queue_packets'])
        restored_wire_count = len(restore_result['recovered_wire_packets'])
        total_restored = restore_result['total_recovered']
        
        print(f"\nTest 1.2 Results:")
        print(f"  Saved - Queues: {saved_queues_count}, Wires: {saved_wires_count}, Total: {total_saved}")
        print(f"  Restored - Queues: {restored_queue_count}, Wires: {restored_wire_count}, Total: {total_restored}")
        
        # Pre-condition check: if no packets were saved, skip the test
        if total_saved == 0:
            self.skipTest("No packets saved - cannot test restoration")
        
        # If packets were saved but none restored, this indicates a problem
        if total_saved > 0 and total_restored == 0:
            self.fail(f"Saved {total_saved} packets but restored 0 - restoration may have failed")
        
        # Verify: should have restored some packets
        self.assertGreater(total_restored, 0, "No packets restored")
        self.assertEqual(total_restored, restored_queue_count + restored_wire_count)
        
        # Count packets in queues after restoration (before running simulation)
        initial_queue_count = sum(len(port.store.items) for (x, y), switch in simulator.switches.items()
                                 for port in (switch.ports if hasattr(switch, 'ports') else switch.egress_ports)
                                 if hasattr(port, 'store'))
        
        # Record initial packets_received count
        initial_received = {}
        for flow in temp_flows:
            if hasattr(flow, 'pkt_sink') and hasattr(flow.pkt_sink, 'packets_received'):
                initial_received[flow.fid] = flow.pkt_sink.packets_received.get(flow.fid, 0)
        
        # NEW: Run a brief simulation to process restored packets
        # Temporarily adjust generation_finish_time to prevent new packet generation
        original_finish_time_2 = config['simulation']['generation_finish_time']
        config['simulation']['generation_finish_time'] = 0.0  # No new packets
        
        # Run brief simulation (10ms) to process restored packets
        brief_sim_time = 0.01  # 10ms in seconds
        try:
            # Re-run simulation briefly to process restored packets
            # Note: This will re-create flows, but switches should be reused
            processed_flows, processed_switches, processed_blocked = simulator.run_simulation_with_rb(
                updated_demand_matrix, demand_matrix, brief_sim_time, 1
            )
        finally:
            # Restore original finish_time
            config['simulation']['generation_finish_time'] = original_finish_time_2
        
        # Count packets in queues after brief simulation
        final_queue_count = sum(len(port.store.items) for (x, y), switch in simulator.switches.items()
                               for port in (switch.ports if hasattr(switch, 'ports') else switch.egress_ports)
                               if hasattr(port, 'store'))
        
        # Count packets received after brief simulation
        final_received = {}
        total_received_increase = 0
        for flow in processed_flows:
            if hasattr(flow, 'pkt_sink') and hasattr(flow.pkt_sink, 'packets_received'):
                fid = flow.fid
                final_received[fid] = flow.pkt_sink.packets_received.get(fid, 0)
                received_increase = final_received[fid] - initial_received.get(fid, 0)
                total_received_increase += received_increase
        
        print(f"  Initial queue count: {initial_queue_count}")
        print(f"  Final queue count: {final_queue_count}")
        print(f"  Packets received increase: {total_received_increase}")
        
        # Verify: Restored packets were processed
        # Either queue count decreased (packets were transmitted) or packets_received increased (packets were received)
        packets_processed = (initial_queue_count - final_queue_count) + total_received_increase
        self.assertGreater(packets_processed, 0, 
                          f"Restored packets were not processed: queue decrease={initial_queue_count - final_queue_count}, received increase={total_received_increase}")
        
        print(f"  Packets processed: {packets_processed} (queue decrease: {initial_queue_count - final_queue_count}, received: {total_received_increase})")
        
        return {
            'saved_queues': saved_queues_count,
            'saved_wires': saved_wires_count,
            'total_saved': total_saved,
            'restored_queues': restored_queue_count,
            'restored_wires': restored_wire_count,
            'total_restored': total_restored,
            'status': 'PASS'
        }
    
    def test_1_3_timestamp_adjustment_correctness(self):
        """
        Test 1.3: Timestamp Adjustment Correctness
        Purpose: Verify that timestamps of restored packets are correctly adjusted
        """
        config = create_test_config()
        config['simulation']['simulation_time'] = 50
        config['simulation']['generation_finish_time'] = 50
        config['fixed_demand']['arrival_rate'] = [100, 100]
        
        result_dir = os.path.join(project_path, 'tests', 'test_results_phase1')
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
        
        # Step 1: Run simulation and save state
        all_flows, switches, blocked_flows = simulator.run_simulation_with_rb(
            updated_demand_matrix, demand_matrix, config['simulation']['simulation_time'], 1
        )
        
        # Save state and record original timestamps
        previous_state = simulator.save_simulation_state(step_id=1, all_flows=all_flows)
        
        # Extract original timestamps from saved packets
        original_timestamps = []
        for packets in previous_state['packets_in_queues'].values():
            for packet in packets:
                original_timestamps.append(packet.timestamp)
        
        for packet_info_list in previous_state['packets_in_wires'].values():
            for packet_info in packet_info_list:
                original_timestamps.append(packet_info['packet'].timestamp)
        
        if len(original_timestamps) == 0:
            self.skipTest("No packets to test timestamp adjustment")
        
        # Step 2: Create new environment and restore state
        simulator.env = simpy.rt.RealtimeEnvironment(initial_time=0, factor=0.0000001, strict=False)
        
        # Temporarily adjust generation_finish_time for infrastructure creation
        original_finish_time = config['simulation']['generation_finish_time']
        config['simulation']['generation_finish_time'] = 0.001  # Match minimal simulation time
        
        # Create infrastructure
        temp_flows, temp_switches, temp_blocked = simulator.run_simulation_with_rb(
            updated_demand_matrix, demand_matrix, 0.001, 1
        )
        
        # Restore original finish_time
        config['simulation']['generation_finish_time'] = original_finish_time
        
        # Restore with time offset
        time_offset = 1.0  # 1 second offset
        restore_result = simulator.restore_simulation_state(previous_state, time_offset=time_offset)
        
        # Extract adjusted timestamps from restored packets
        adjusted_timestamps = []
        for (x, y), switch in simulator.switches.items():
            ports = switch.ports if hasattr(switch, 'ports') else switch.egress_ports
            for port in ports:
                if hasattr(port, 'store'):
                    for packet in port.store.items:
                        adjusted_timestamps.append(packet.timestamp)
        
        print(f"\nTest 1.3 Results:")
        print(f"  Original timestamps: {original_timestamps[:5]}...")  # Show first 5
        print(f"  Adjusted timestamps: {adjusted_timestamps[:5]}...")  # Show first 5
        print(f"  Time offset: {time_offset}")
        
        # Verify: should have restored packets to verify timestamp adjustment
        if len(adjusted_timestamps) == 0:
            self.fail("No packets restored to verify timestamp adjustment")
        
        # Verify: adjusted timestamps should be original + time_offset
        # Note: We can only verify packets that are still in queues (not processed)
        if len(adjusted_timestamps) > 0:
            for i, adjusted_ts in enumerate(adjusted_timestamps[:len(original_timestamps)]):
                expected_ts = original_timestamps[i] + time_offset
                self.assertAlmostEqual(adjusted_ts, expected_ts, places=5,
                                    msg=f"Timestamp {i} not adjusted correctly: {adjusted_ts} != {expected_ts}")
        
        # Verify monotonicity: timestamps should be monotonically increasing
        if len(adjusted_timestamps) > 1:
            for i in range(len(adjusted_timestamps) - 1):
                self.assertLessEqual(adjusted_timestamps[i], adjusted_timestamps[i+1],
                                  msg=f"Timestamps not monotonic: {adjusted_timestamps[i]} > {adjusted_timestamps[i+1]}")
        
        return {
            'original_timestamps_count': len(original_timestamps),
            'adjusted_timestamps_count': len(adjusted_timestamps),
            'time_offset': time_offset,
            'status': 'PASS'
        }


if __name__ == '__main__':
    unittest.main()

