#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for state saving functionality in multi-step simulation.

Tests that packets in queues and wires are correctly saved.
"""

import unittest
import sys
import os
import simpy
import copy

# Add the project src directory to the Python path
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_path, 'src')
sys.path.insert(0, src_path)

from port.wire import Wire
from port.port import Port
from packet.packet import Packet
from modem.switch import SimplePacketSwitch
from tests.utils.test_helpers import create_test_config, create_test_simulator


class TestStateSaving(unittest.TestCase):
    """Test state saving functionality."""
    
    def test_save_packets_in_queues(self):
        """Test that packets in queues are correctly saved."""
        config = create_test_config()
        result_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(result_dir, exist_ok=True)
        
        from topo.toroidal_topo import ToroidalTopo
        regen_obp = ToroidalTopo(scenario_config=config, width=4, height=4)
        
        from simulator.simulator import Simulator
        simulator = Simulator(regen_obp, config, result_dir, 1, 'fifo', None, None)
        
        # Create a simple switch and port for testing
        switch = SimplePacketSwitch(
            env=simulator.env,
            nports=1,
            port_rate=10000000,
            obp_rate=1000,
            buffer_size=15000,
            element_id="TestSwitch",
            x=0,
            y=0,
            limit_bytes=True,
            debug=False
        )
        simulator.switches[(0, 0)] = switch
        port = switch.ports[0]
        
        # Create and add packets to the queue
        packet1 = Packet(
            timestamp=0.0,
            size=1500,
            id=1,
            flow_id=0,
            original_flow_id=0,
            priority=1
        )
        packet2 = Packet(
            timestamp=0.1,
            size=1500,
            id=2,
            flow_id=0,
            original_flow_id=0,
            priority=1
        )
        
        # Put packets in the queue
        port.store.put(packet1)
        port.store.put(packet2)
        
        # Save state
        saved_queues = simulator.save_packets_in_queues()
        
        # Verify
        self.assertIn(((0, 0), port.element_id), saved_queues)
        saved_packets = saved_queues[((0, 0), port.element_id)]
        self.assertEqual(len(saved_packets), 2)
        self.assertEqual(saved_packets[0].id, 1)
        self.assertEqual(saved_packets[1].id, 2)
        
        # Verify deep copy (modifying saved packet shouldn't affect original)
        saved_packets[0].id = 999
        self.assertEqual(packet1.id, 1)  # Original should be unchanged
    
    def test_save_packets_in_wires(self):
        """Test that packets in wires are correctly saved."""
        config = create_test_config()
        result_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(result_dir, exist_ok=True)
        
        from topo.toroidal_topo import ToroidalTopo
        regen_obp = ToroidalTopo(scenario_config=config, width=4, height=4)
        
        from simulator.simulator import Simulator
        simulator = Simulator(regen_obp, config, result_dir, 1, 'fifo', None, None)
        
        # Create a switch and wire
        switch = SimplePacketSwitch(
            env=simulator.env,
            nports=1,
            port_rate=10000000,
            obp_rate=1000,
            buffer_size=15000,
            element_id="TestSwitch",
            x=0,
            y=0,
            limit_bytes=True,
            debug=False
        )
        simulator.switches[(0, 0)] = switch
        port = switch.ports[0]
        
        # Create a wire
        delay_dist = lambda: 0.01  # 10ms delay
        wire = Wire(
            env=simulator.env,
            delay_dist=delay_dist,
            src_coords=(0, 0),
            dst_coords=(1, 1),
            wire_id="TestWire",
            debug=False
        )
        port.out = wire
        
        # Create and add packet to wire
        packet = Packet(
            timestamp=0.0,
            size=1500,
            id=1,
            flow_id=0,
            original_flow_id=0,
            priority=1
        )
        packet.current_time = simulator.env.now
        wire.store.put(packet)
        
        # Save state
        saved_wires = simulator.save_packets_in_wires()
        
        # Verify
        wire_key = (wire.src_coords, wire.dst_coords)
        self.assertIn(wire_key, saved_wires)
        wire_packets_info = saved_wires[wire_key]
        self.assertEqual(len(wire_packets_info), 1)
        self.assertEqual(wire_packets_info[0]['packet'].id, 1)
        self.assertIn('remaining_delay', wire_packets_info[0])
        self.assertIn('wire_id', wire_packets_info[0])
    
    def test_save_port_statistics(self):
        """Test that port statistics are correctly saved."""
        config = create_test_config()
        result_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(result_dir, exist_ok=True)
        
        from topo.toroidal_topo import ToroidalTopo
        regen_obp = ToroidalTopo(scenario_config=config, width=4, height=4)
        
        from simulator.simulator import Simulator
        simulator = Simulator(regen_obp, config, result_dir, 1, 'fifo', None, None)
        
        # Create a switch and port
        switch = SimplePacketSwitch(
            env=simulator.env,
            nports=1,
            port_rate=10000000,
            obp_rate=1000,
            buffer_size=15000,
            element_id="TestSwitch",
            x=0,
            y=0,
            limit_bytes=True,
            debug=False
        )
        simulator.switches[(0, 0)] = switch
        port = switch.ports[0]
        
        # Modify port statistics
        port.packets_received = 100
        port.packets_dropped = 5
        
        # Save statistics
        saved_stats = simulator.save_port_statistics()
        
        # Verify
        key = ((0, 0), port.element_id)
        self.assertIn(key, saved_stats)
        self.assertEqual(saved_stats[key]['packets_received'], 100)
        self.assertEqual(saved_stats[key]['packets_dropped'], 5)
    
    def test_save_completeness(self):
        """Test that all state is saved (completeness check)."""
        config = create_test_config()
        result_dir = os.path.join(project_path, 'tests', 'test_results')
        os.makedirs(result_dir, exist_ok=True)
        
        from topo.toroidal_topo import ToroidalTopo
        regen_obp = ToroidalTopo(scenario_config=config, width=4, height=4)
        
        from simulator.simulator import Simulator
        simulator = Simulator(regen_obp, config, result_dir, 1, 'fifo', None, None)
        
        # Create switches with packets in queues
        switch1 = SimplePacketSwitch(
            env=simulator.env,
            nports=2,
            port_rate=10000000,
            obp_rate=1000,
            buffer_size=15000,
            element_id="Switch1",
            x=0,
            y=0,
            limit_bytes=True,
            debug=False
        )
        simulator.switches[(0, 0)] = switch1
        
        # Add packets to queues
        packet1 = Packet(0.0, 1500, 1, 0, 0, priority=1)
        packet2 = Packet(0.1, 1500, 2, 0, 0, priority=1)
        switch1.ports[0].store.put(packet1)
        switch1.ports[1].store.put(packet2)
        
        # Create wire with packet
        wire = Wire(
            env=simulator.env,
            delay_dist=lambda: 0.01,
            src_coords=(0, 0),
            dst_coords=(1, 1),
            wire_id="TestWire",
            debug=False
        )
        switch1.ports[0].out = wire
        packet3 = Packet(0.2, 1500, 3, 0, 0, priority=1)
        packet3.current_time = simulator.env.now
        wire.store.put(packet3)
        
        # Save complete state
        from flow.flow import Flow
        from packet.dist_generator import PacketGenerator
        from packet.sink import PacketSink
        
        flow = Flow(
            fid=0,
            src="src",
            dst="dst",
            path="path",
            flow_value=100.0
        )
        flow.pkt_gen = PacketGenerator(simulator.env, 0, lambda: 0.1, lambda: 1500)
        flow.pkt_sink = PacketSink(simulator.env)
        all_flows = [flow]
        
        state = simulator.save_simulation_state(step_id=1, all_flows=all_flows)
        
        # Verify completeness
        self.assertEqual(state['step_id'], 1)
        self.assertIn('step_end_time', state)
        self.assertIn('packets_in_queues', state)
        self.assertIn('packets_in_wires', state)
        self.assertIn('port_statistics', state)
        self.assertIn('flow_statistics', state)
        
        # Verify packets were saved
        self.assertGreater(len(state['packets_in_queues']), 0)
        self.assertGreater(len(state['packets_in_wires']), 0)


if __name__ == '__main__':
    unittest.main()


