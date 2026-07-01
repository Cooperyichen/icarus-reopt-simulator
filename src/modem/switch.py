#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This file defines two classes: SimplePacketSwitch and FairPacketSwitch, which represent packet switches with 
various scheduling mechanisms and bounded buffers for outgoing ports.

The SimplePacketSwitch class uses FIFO bounded buffers for outgoing ports, while the FairPacketSwitch class 
supports WFQ and Priority scheduling.

Each switch object captures essential switch information such as its environment, number of ports, port rate, 
buffer size, element ID, and debug mode.

The `put` method processes and sends packets to the appropriate element, with an optional delay based on the 
obp_rate.

"""

# @author: zineb.garroussi@polymtl.ca

from collections.abc import Callable

from port.port import Port
from demux.fib_demux import FIBDemux
from scheduler.wfq import WFQServer
from scheduler.sp import SPServer
from utils.libs import *



class SimplePacketSwitch:
    """ 
    A class representing a simple packet switch with FIFO bounded buffers on each of the outgoing ports.

    Attributes:
        env (simpy.Environment): The simulation environment.
        ports (list): List of Port objects representing the switch's ports.
        obp_rate (float): The OBP rate for processing delay.
        failed (bool): Track whether the switch is failed.
        debug (bool): If True, prints more verbose debug information.
        element_id (str): The element ID of this component.
        x (int): The x-coordinate of the switch's position.
        y (int): The y-coordinate of the switch's position.

    :param env: The simulation environment.
    :param nports: The total number of ports on this switch.
    :param port_rate: The bit rate of the port.
    :param obp_rate: The OBP rate for processing delay.
    :param buffer_size: The size of an outgoing port's bounded buffer, in packets.
    :param element_id: The element ID of this component.
    :param x: The x-coordinate of the switch's position.
    :param y: The y-coordinate of the switch's position.
    :param debug: If True, prints more verbose debug information.
    :type env: simpy.Environment
    :type nports: int
    :type port_rate: float
    :type obp_rate: float
    :type buffer_size: int
    :type element_id: str
    :type x: int
    :type y: int
    :type debug: bool
    """

    def __init__(self,
                 env,
                 nports: int,
                 port_rate: float,
                 obp_rate:float,
                 buffer_size: int,
                 element_id: str = "",
                 x : int = 0,
                 y : int = 0,
                 limit_bytes: bool = False,
                 debug: bool = False) -> None:

        self.env = env
        self.ports = []
        self.obp_rate = obp_rate # Added obp_rate here to be used in processing delay
        self.failed = False  # Track whether the switch is failed
        self.debug = debug
        self.element_id = element_id
        self.x = x
        self.y = y
        self.limit_bytes = limit_bytes
        self.qlimit = buffer_size
        self.out = None

        self.byte_size = 0  # The current size of the entrance queue in bytes
        self.packets_dropped = 0
        self.entrance_queue = simpy.Store(env)  # Entrance queue for packets entering the switch
        self.packets_received = 0
        self.dropped_by_flow = defaultdict(int)

        for port in range(nports):
            self.ports.append(
                Port(env,
                     rate=port_rate,
                     obp_rate = obp_rate,
                     qlimit=buffer_size,
                     limit_bytes=limit_bytes,
                     element_id=f"{element_id}_{port}",
                     parent_switch=self,
                     debug=debug))
     #   self.demux =  FIBDemux(fib=None, outs=self.ports, default=None)
        self.demux =  FIBDemux(fib=None, outs=self.ports, default=None)
        
        #self.action = env.process(self.run())  # Start processing entrance queue



    # def put(self, packet):
    #     """ Sends a packet to this element. """

    #     self.demux.put(packet)


    def fail(self):

        """
        Fail the switch.
        """
        
        self.failed = True
        print(f"Switch {self.element_id} failed at time {self.env.now}")
        if self.debug:
            print(f"Switch {self.element_id} failed at time {self.env.now}")

    
    
    
    # def put(self, packet):
    #     """ Sends a packet to this element. """
    #     self.demux.put(packet)
        
        
    def put(self, packet):
        """ Sends a packet to this element. """
        self.env.process(self._put(packet))
    

    def _put(self, packet):
        """ Internal method to handle the packet processing with delay. """
        if self.debug:
            print(f"Packet {packet.id} entering switch at {self.env.now}")
        yield self.env.timeout(1.00 / self.obp_rate)
        if self.debug:
            print(f"Packet {packet.id} processed in switch at {self.env.now}")
        self.demux.put(packet)
        
            
   
            
 

#########################################################################################################################   
    
    # def run(self):
    #     """Process packets from the entrance queue."""
    #     while True:
    #         packet = yield self.entrance_queue.get()
    #         yield self.env.timeout(1.00 / self.obp_rate)  # Processing delay
    #         self.byte_size -= packet.size
    #         if self.debug:
    #             print(f"Packet {packet.id} processed at entrance of switch {self.element_id} at time {self.env.now}")
    #         self.demux.put(packet)



    # def put(self, packet):
    #     """Send a packet to this switch."""
    #     self.packets_received += 1
    #     byte_count = self.byte_size + packet.size

    #     if self.failed:
    #         packet.status = "dropped"
    #         self.packets_dropped += 1
    #         self.dropped_by_flow[packet.flow_id] += 1
    #         if self.debug:
    #             print(f"Packet {packet.id} dropped because switch {self.element_id} is failed at time {self.env.now}")
    #         return

    #     if self.qlimit is None:
    #         self.byte_size = byte_count
    #         self.entrance_queue.put(packet)
    #         return

    #     if self.limit_bytes and byte_count >= self.qlimit:
    #         self.drop_packet(packet)
    #     elif not self.limit_bytes and len(self.entrance_queue.items) >= self.qlimit - 1:
    #         self.drop_packet(packet)
    #     else:
    #         self.byte_size = byte_count
    #         self.entrance_queue.put(packet)
            
            

    # def drop_packet(self, packet):
    #     """Drop the packet and update the relevant statistics.

    #     Parameters
    #     ----------
    #     packet: Packet
    #         The packet to be dropped.
    #     """
    #     self.packets_dropped += 1
    #     packet.status = "dropped"
    #     self.dropped_by_flow[packet.flow_id] += 1

    #     if self.debug:
    #         print(
    #             f"Packet dropped: flow id = {packet.flow_id}, packet id = {packet.id}"
    #         )   
    
    
        
###################################################################################################

        
#################################################################################################

class FairPacketSwitch:
    """ 
    A class representing a fair packet switch with WFQ, DRR, Virtual Clock, or Static Priority scheduling and bounded buffers
    on each of the outgoing ports.

    Attributes:
        env (simpy.Environment): The simulation environment.
        ports (list): List of scheduler objects representing the switch's ports.
        obp_rate (float): The OBP rate for processing delay.
        failed (bool): Track whether the switch is failed.
        debug (bool): If True, prints more verbose debug information.
        egress_ports (list): List of Port objects representing the egress ports.

    :param env: The simulation environment.
    :param nports: The total number of ports on this switch.
    :param port_rate: The bit rate of each outgoing port.
    :param obp_rate: The OBP rate for processing delay.
    :param buffer_size: The size of an outgoing port's bounded buffer, in packets.
    :param weights: Weights for the scheduler.
    :param server: The type of the scheduling discipline used for each outgoing port.
    :param flow_classes: Function matching a packet's flow_ids to class_ids.
    :param element_id: The element ID of this component.
    :param x: The x-coordinate of the switch's position.
    :param y: The y-coordinate of the switch's position.
    :param debug: If True, prints more verbose debug information.
    :type env: simpy.Environment
    :type nports: int
    :type port_rate: float
    :type obp_rate: float
    :type buffer_size: int
    :type weights: list or dict
    :type server: str
    :type flow_classes: Callable
    :type element_id: str
    :type x: int
    :type y: int
    :type debug: bool
    """

    def __init__(self,
                 env,
                 nports: int,
                 port_rate: float,
                 obp_rate:float,
                 buffer_size: int,
                 weights,
                 server: str,
                 flow_classes: Callable = lambda p: p.flow_id,
                 element_id: str = "",
                 x : int = 0,
                 y : int = 0,
                 limit_bytes: bool = False,
                 debug: bool = False) -> None:
        self.env = env
        self.ports = []
        self.obp_rate = obp_rate # Added obp_rate here to be used in processing delay
        self.failed = False  # Track whether the switch is failed
        self.limit_bytes = limit_bytes

        self.debug = debug



        self.element_id = element_id
        self.x = x
        self.y = y
        self.qlimit = buffer_size
        self.byte_size = 0  # The current size of the entrance queue in bytes
        self.packets_dropped = 0
        self.entrance_queue = simpy.Store(env)  # Entrance queue for packets entering the switch
        self.packets_received = 0
        self.dropped_by_flow = defaultdict(int)

        self.egress_ports = []


        for port in range(nports):
            egress_port = Port(env,
                               rate=0,
                               obp_rate = obp_rate,
                               qlimit=buffer_size,
                               limit_bytes=False,
                               zero_downstream_buffer=True,
                               element_id=f"{element_id}_{port}",
                               debug=debug)

            scheduler = None
            if server == 'WFQ':
                scheduler = WFQServer(env,
                                      rate=port_rate,
                                      weights=weights,
                                      flow_classes=flow_classes,
                                      zero_buffer=True,
                                      debug=debug)
                
            elif server == 'PRIORITY':
                scheduler = SPServer(env,
                                     rate=port_rate,
                                     priorities=weights,
                                     flow_classes=flow_classes,
                                     zero_buffer=True,
                                     debug=debug)
            else:
                raise ValueError(
                    #"Scheduler type must be 'WFQ', or 'PRIORITY'."
                    "Scheduler type must be 'WFQ', 'PRIORITY'. "

                )

            egress_port.out = scheduler

            self.egress_ports.append(egress_port)
            self.ports.append(scheduler)

        self.demux = FIBDemux(fib=None, outs=self.egress_ports, default=None)

        # self.action = env.process(self.run())  # Start processing entrance queue


    # def put(self, packet):
    #     """ Sends a packet to this element. """
    #     self.demux.put(packet)
        
        
    def put(self, packet):
        """ Sends a packet to this element. """
        self.env.process(self._put(packet))
    

    def _put(self, packet):
        """ Internal method to handle the packet processing with delay. """
        if self.debug:
            print(f"Packet {packet.id} entering switch at {self.env.now}")
        yield self.env.timeout(1.00 / self.obp_rate)
        if self.debug:
            print(f"Packet {packet.id} processed in switch at {self.env.now}")
        self.demux.put(packet)
        
            
   
            
   
    
   
    
    # def run(self):
    #     """Process packets from the entrance queue."""
    #     while True:
    #         packet = yield self.entrance_queue.get()
    #         yield self.env.timeout(1.00 / self.obp_rate)  # Processing delay
    #         self.byte_size -= packet.size
    #         if self.debug:
    #             print(f"Packet {packet.id} processed at entrance of switch {self.element_id} at time {self.env.now}")
    #         self.demux.put(packet)



    # def put(self, packet):
    #     """Send a packet to this switch."""
    #     self.packets_received += 1
    #     byte_count = self.byte_size + packet.size

    #     if self.failed:
    #         packet.status = "dropped"
    #         self.packets_dropped += 1
    #         self.dropped_by_flow[packet.flow_id] += 1
    #         if self.debug:
    #             print(f"Packet {packet.id} dropped because switch {self.element_id} is failed at time {self.env.now}")
    #         return

    #     if self.qlimit is None:
    #         self.byte_size = byte_count
    #         self.entrance_queue.put(packet)
    #         return

    #     if self.limit_bytes and byte_count >= self.qlimit:
    #         self.drop_packet(packet)
    #     elif not self.limit_bytes and len(self.entrance_queue.items) >= self.qlimit - 1:
    #         self.drop_packet(packet)
    #     else:
    #         self.byte_size = byte_count
    #         self.entrance_queue.put(packet)
            
            

    # def drop_packet(self, packet):
    #     """Drop the packet and update the relevant statistics.

    #     Parameters
    #     ----------
    #     packet: Packet
    #         The packet to be dropped.
    #     """
    #     self.packets_dropped += 1
    #     packet.status = "dropped"
    #     self.dropped_by_flow[packet.flow_id] += 1

    #     if self.debug:
    #         print(
    #             f"Packet dropped: flow id = {packet.flow_id}, packet id = {packet.id}"
    #         )   
    
    
