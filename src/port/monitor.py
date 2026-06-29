#!/usr/bin/env python3
# -*- coding: utf-8 -*-



"""
A monitoring element that observes the number of items in the Port, including 
both in service and in the queue, and records that information in the `sizes` list.

This class simulates a monitor that periodically checks the state of a port 
and records the number of items (packets) present. The monitoring intervals 
are determined by a given distribution function.

Parameters
----------
env : simpy.Environment
    The simulation environment.
port : Port
    The switch port object to be monitored.
dist : function
    A no-parameter function that returns the successive inter-arrival times 
    for the monitoring events.
pkt_in_service_included : bool, optional
    A flag to indicate whether to include the packet in service in the count. 
    Defaults to False.

The monitor periodically checks the port at intervals defined by `dist`. 
If `pkt_in_service_included` is True, it includes the packet being serviced 
in the count; otherwise, it only counts the packets in the queue.

@author: zineb.garroussi@polymtl.ca
"""

class PortMonitor:
    """
    Looks at the number of items in the Port, in service + in the queue,
    and records that info in the sizes[] list. The monitor looks at the port
    at time intervals given by the distribution dist.

    Parameters
    ----------
    env : simpy.Environment
        The simulation environment.
    port : Port
        The switch port object to be monitored.
    dist : function
        A no-parameter function that returns the successive inter-arrival
        times of the packets.
    pkt_in_service_included : bool, optional
        Flag to include the packet in service in the count. Defaults to False.
    """
    def __init__(self, env, port, dist, pkt_in_service_included=False):
        '''
        Initialize the PortMonitor with the given simulation environment, port, 
        distribution function, and an optional flag to include the packet in service.
        '''
        self.port = port  # Store the port to be monitored
        self.env = env  # Set the simulation environment
        self.dist = dist  # Store the distribution function for monitoring intervals
        self.sizes = []  # Initialize the list to store the counts of packets
        self.sizes_byte = []  # Initialize the list to store the byte sizes of packets
        self.action = env.process(self.run())  # Start the monitoring process
        self.pkt_in_service_included = pkt_in_service_included  # Set the flag to include packet in service

    def run(self):
        """
        The generator function used in simulations.
        """
        while True:
            yield self.env.timeout(self.dist())  # Wait for the next monitoring interval

            if self.pkt_in_service_included:
                total_byte = self.port.byte_size + self.port.busy_packet_size  # Include packet in service
                total = len(self.port.store.items) + self.port.busy  # Include packet in service
            else:
                total_byte = self.port.byte_size  # Only count the packets in the queue
                total = len(self.port.store.items)  # Only count the packets in the queue

            self.sizes.append(total)  # Record the total number of packets
            self.sizes_byte.append(total_byte)  # Record the total byte size of packets

