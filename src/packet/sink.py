#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Implements a PacketSink, designed to record both arrival times and waiting times
from the incoming packets.

This class simulates a network element that records statistics about the packets 
it receives. It can record both absolute and inter-arrival times, as well as 
waiting times experienced by the packets.

The PacketSink stores various metrics, including arrival times, waiting times, 
packet sizes, and more. It helps in analyzing the performance of the network 
by providing detailed statistics for each packet flow.

Author: zineb.garroussi@polymtl.ca
"""

from collections import defaultdict as dd
import simpy
import os

class PacketSink:
    """
    A PacketSink is designed to record both arrival times and waiting times from the incoming
    packets. By default, it records absolute arrival times, but it can also be initialized to record
    inter-arrival times.

    Attributes:
        env (simpy.Environment): The simulation environment.
        rec_arrivals (bool): If True, arrivals will be recorded.
        absolute_arrivals (bool): If True, absolute arrival times will be recorded; otherwise, the time between
            consecutive arrivals is recorded.
        rec_waits (bool): If True, the waiting times experienced by the packets are recorded.
        rec_flow_ids (bool): If True, the flow IDs that the packets are used as the index for recording;
            otherwise, the 'src' field in the packets are used.
        debug (bool): If True, prints more verbose debug information.

    :param env: The simulation environment.
    :param rec_arrivals: If True, arrivals will be recorded (default is True).
    :param absolute_arrivals: If True, absolute arrival times will be recorded; otherwise, the time between
        consecutive arrivals is recorded (default is True).
    :param rec_waits: If True, the waiting times experienced by the packets are recorded (default is True).
    :param rec_flow_ids: If True, the flow IDs that the packets are used as the index for recording;
        otherwise, the 'src' field in the packets are used (default is True).
    :param debug: If True, prints more verbose debug information (default is False).
    :type env: simpy.Environment
    :type rec_arrivals: bool
    :type absolute_arrivals: bool
    :type rec_waits: bool
    :type rec_flow_ids: bool
    :type debug: bool
    """

    def __init__(
        self,
        env,
        rec_arrivals: bool = True,
        absolute_arrivals: bool = True,
        rec_waits: bool = True,
        rec_flow_ids: bool = True,
        debug: bool = False,
    ):
        """
        Initializes the PacketSink class.

        :param env: The simulation environment.
        :type env: simpy.Environment
        :param rec_arrivals: If True, arrivals will be recorded (default is True).
        :type rec_arrivals: bool, optional
        :param absolute_arrivals: If True, absolute arrival times will be recorded; otherwise, the time between
            consecutive arrivals is recorded (default is True).
        :type absolute_arrivals: bool, optional
        :param rec_waits: If True, the waiting times experienced by the packets are recorded (default is True).
        :type rec_waits: bool, optional
        :param rec_flow_ids: If True, the flow IDs that the packets are used as the index for recording;
            otherwise, the 'src' field in the packets are used (default is True).
        :type rec_flow_ids: bool, optional
        :param debug: If True, prints more verbose debug information (default is False).
        :type debug: bool, optional
        """
        self.store = simpy.Store(env)  # Initialize the store for packets
        self.env = env  # Set the simulation environment
        self.rec_waits = rec_waits  # Flag to record waiting times
        self.rec_flow_ids = rec_flow_ids  # Flag to use flow IDs for recording
        self.rec_arrivals = rec_arrivals  # Flag to record arrival times
        self.absolute_arrivals = absolute_arrivals  # Flag to record absolute arrival times
        self.waits = dd(list)  # Dictionary to store waiting times
        self.arrivals = dd(list)  # Dictionary to store arrival times
        self.packets_received = dd(lambda: 0)  # Dictionary to count packets received
        self.bytes_received = dd(lambda: 0)  # Dictionary to count bytes received
        self.packet_sizes = dd(list)  # Dictionary to store packet sizes
        self.packet_times = dd(list)  # Dictionary to store packet times
        self.perhop_times = dd(list)  # Dictionary to store per-hop times
        self.first_arrival = dd(lambda: 0)  # Dictionary to store the first arrival time
        self.last_arrival = dd(lambda: 0)  # Dictionary to store the last arrival time
        self.debug = debug  # Flag for debug mode
        self.recovered_time_limit_packets = []  # List to track packets recovered from Time Limit Drops

    def put(self, packet):
        """
        Sends a packet to this element.

        This method records the arrival time and waiting time of the packet, and updates
        the corresponding statistics. It also prints debug information if debug mode is enabled.

        :param packet: The packet to be recorded.
        :type packet: Packet
        """
        now = self.env.now  # Get the current simulation time

        # Determine the recording index based on flow ID or source
        if self.rec_flow_ids:
            rec_index = packet.flow_id
        else:
            rec_index = packet.src

        # Record waiting times if enabled
        if self.rec_waits:
            self.waits[rec_index].append(self.env.now - packet.timestamp)  # Calculate and store waiting time
            self.packet_sizes[rec_index].append(packet.size)  # Store packet size
            self.packet_times[rec_index].append(packet.timestamp)  # Store packet time
            self.perhop_times[rec_index].append(packet.perhop_time)  # Store per-hop time
            self.arrivals[rec_index].append(self.env.now)  # Store arrival time

        # Record arrival times if enabled
        if self.rec_arrivals:
            self.arrivals[rec_index].append(now)  # Store the current time as arrival time
            if len(self.arrivals[rec_index]) == 1:
                self.first_arrival[rec_index] = now  # Store the first arrival time

            if not self.absolute_arrivals:
                self.arrivals[rec_index][-1] = now - self.last_arrival[rec_index]  # Calculate inter-arrival time

            self.last_arrival[rec_index] = now  # Update the last arrival time

        # Print debug information if enabled
        if self.debug:
            print(
                "At time {:.2f}, packet {:d} in flow {:d} arrived.".format(
                    now, packet.id, packet.flow_id
                )
            )
            if self.rec_waits and len(self.packet_sizes[rec_index]) >= 10:
                bytes_received = sum(self.packet_sizes[rec_index][-9:])  # Sum the sizes of the last 10 packets
                time_elapsed = self.env.now - (
                    self.packet_times[rec_index][-10] + self.waits[rec_index][-10]
                )
                print(
                    "Average throughput (last 10 packets): {:.2f} bytes/time unit.".format(
                        float(bytes_received) / time_elapsed
                    )
                )

        # Check if packet was recovered from Time Limit Drop
        if hasattr(packet, '_recovered_from_time_limit') and packet._recovered_from_time_limit:
            print(f"[DEBUG] Recovered packet {packet.id} from flow {packet.flow_id} arrived at sink at time {self.env.now:.6f}")
            if hasattr(packet, '_time_limit_drop_step'):
                print(f"  Packet was a Time Limit Drop from step {packet._time_limit_drop_step}")
            self.recovered_time_limit_packets.append(packet.id)
            # Reset the flag after recording
            packet._recovered_from_time_limit = False
        elif hasattr(packet, '_time_limit_drop_step') and packet._time_limit_drop_step is not None:
            # Packet was marked as Time Limit Drop but _recovered_from_time_limit is False
            print(f"[DEBUG] Packet {packet.id} (marked as Time Limit Drop from step {packet._time_limit_drop_step}) arrived at sink at time {self.env.now:.6f} but NOT marked as recovered")
        
        self.packets_received[rec_index] += 1  # Increment the packet received count
        self.bytes_received[rec_index] += packet.size  # Increment the bytes received count

        # If debug mode is enabled, write packet attributes to the CSV file
        if self.debug:
            delay = now - packet.timestamp 

            # Ensure the 'results' directory exists
            results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results'))
            os.makedirs(results_dir, exist_ok=True)
            csv_file = os.path.join(results_dir, 'received_packets.csv')

            # Initialize the CSV file with headers if it doesn't exist
            if not os.path.exists(csv_file) or os.path.getsize(csv_file) == 0:
                with open(csv_file, 'w') as file:
                    file.write('Timestamp;Size;ID;Flow ID;Delay\n')

            # Write packet attributes to the CSV file
            with open(csv_file, 'a') as file:
                file.write(f"{packet.timestamp};{packet.size};{packet.id};{packet.original_flow_id};{delay}\n")
