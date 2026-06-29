#!/usr/bin/env python3
# -*- coding: utf-8 -*-



"""
This file defines the Packet class which represents a data packet in a network simulation.

Each Packet object captures essential packet information such as its creation timestamp, size in bytes, unique ID, source 
and destination addresses, flow identifier, and priority. The flow identifier helps associate the packet with a particular 
flow in the network, while the priority can be used for QoS (Quality of Service) applications or priority queueing.

The `__repr__` method provides a human-readable string representation of the Packet object, useful for debugging and logging.


"""

# @author: zineb.garroussi@polymtl.ca



class Packet:

    """
    A class representing a data packet in a network system.

    Attributes:
        timestamp (float): The time at which the packet was created.
        size (int): Packet size in bytes.
        id (int): Unique identifier for the packet.
        src (str): Ingress source address.
        dst (str): Egress destination address.
        flow_id (int): Identifier for the flow related to this packet.
        priority (int): Priority level of the packet (lower number indicates higher priority).
        status (str): The current status of the packet ("delivered", "dropped", "blocked").

    :param timestamp: The time at which the packet was created.
    :param size: Packet size in bytes.
    :param id: Unique identifier for the packet.
    :param src: Ingress source address.
    :param dst: Egress destination address.
    :param flow_id: Identifier for the flow related to this packet.
    :param priority: Priority level of the packet.
    :type timestamp: float
    :type size: int
    :type id: int
    :type src: str
    :type dst: str
    :type flow_id: int
    :type priority: int
    :type status: str
    """    

    def __init__(self, 
                 timestamp,  # the time when the packet is generated
                 size,    # the size of the packet in bytes
                 id,   # an identifier for the packet
                 flow_id,  # flow identifier 
                 original_flow_id,  # original flow identifier
                 src = "source", # source identifier
                 dst = "destination",   # destination identifier
                 priority =0, 
                 payload=None,  # payload data (default None)
                 status="delivered"):
        self.timestamp = timestamp #  The time at which the packet was created
        
        self.original_flow_id = original_flow_id  # original flow identifier
        self.size = size # packet size (bytes)
        self.id = id  # # store the packet identifier 
        self.src = src # ingress source (string)
        self.dst = dst # egress destination (string)
        self.flow_id = flow_id # used to identify the flow related to this packet (int)
        self.payload = payload  # store the payload data
        self.priority = priority # priority level (int, lower number is higher priority)
        self.status = status # status (str): The current status of the packet ("delivered", "dropped", "blocked").
        self.perhop_time = {}  # initialize per-hop time dictionary (used by Port to record per-hop arrival times)
        self.prio = {}  # used by the Static Priority scheduler
        
        # Multi-step simulation tracking attributes
        self.current_time = 0  # Current time when packet enters a Wire (used by Wire element for delay calculation)
        self._time_limit_drop_step = None  # Step ID when this packet became a Time Limit Drop (None if not a Time Limit Drop)
        self._recovered_from_time_limit = False  # Flag indicating if this packet was recovered from a Time Limit Drop state
        
                



    def __repr__(self):
        return ("Packet(id: {}, timestamp: {}, size: {}, src: {}, dst: {}, "
                "flow_id: {}, original_flow_id: {}, priority: {}, status: {})").format(
                    self.id, self.timestamp, self.size, self.src, 
                    self.dst, self.flow_id, self.original_flow_id, self.priority, self.status)


    def drop(self):
        """
        Marks the packet as dropped.
        """
        self.status = "dropped"

    def block(self):
        """
        Marks the packet as blocked.
        """
        self.status = "blocked"
    
    def __deepcopy__(self, memo):
        """
        Deep copy method for Packet objects.
        Used when saving simulation state to avoid reference issues.
        
        :param memo: Memo dictionary used by copy.deepcopy()
        :return: A deep copy of this Packet object
        """
        import copy
        # Create a new Packet instance with copied attributes
        new_packet = Packet(
            timestamp=self.timestamp,
            size=self.size,
            id=self.id,
            flow_id=self.flow_id,
            original_flow_id=self.original_flow_id,
            src=self.src,
            dst=self.dst,
            priority=self.priority,
            payload=copy.deepcopy(self.payload, memo) if self.payload else None,
            status=self.status
        )
        # Copy mutable attributes
        new_packet.perhop_time = copy.deepcopy(self.perhop_time, memo)
        new_packet.prio = copy.deepcopy(self.prio, memo)
        new_packet.current_time = self.current_time
        new_packet._time_limit_drop_step = self._time_limit_drop_step
        new_packet._recovered_from_time_limit = self._recovered_from_time_limit
        return new_packet
 
    # def __lt__(self, other):
    #     """
    #     Define the behavior for the less-than operator (<).
    #     In a priority queue, a packet with a lower priority value (where lower number indicates higher priority)
    #     is considered 'less' than one with a higher priority value.
    #     """
    #     return self.priority < other.priority

