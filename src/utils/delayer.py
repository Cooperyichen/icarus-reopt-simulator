"""
Implements a delayer that adds arbitrary delay within [0, D] without changing the order
of packets arrived.



The objective of the Delayer and StackDelayer classes is to simulate network packet delays within a SimPy-based simulation environment. 

The Delayer class introduces arbitrary delays to packets within a specified range without altering the order of their arrival, mimicking variable network latency. 

This is useful for testing how a network or system handles unpredictable delays. 

The StackDelayer class, on the other hand, delays packets based on their size and a defined transmission speed, simulating the time it takes for packets to be transmitted over a network link with limited bandwidth. 





"""

from copy import copy
from random import uniform
import simpy

class Delayer:
    """
    Delays packets by a random amount of time within the range [0, max_delay] 
    without changing the order of arrival.

    Parameters
    ----------
    env : simpy.Environment
        The simulation environment.
    max_delay : float
        The maximum amount of delay to be added to packets.
    """
    def __init__(self, env, max_delay):
        self.env = env  # Simulation environment
        self.max_delay = max_delay  # Maximum delay time
        self.waiting_queue = []  # Queue to hold packets and their scheduled times
        self.queue = simpy.Store(env)  # SimPy store for synchronization
        self.out = None  # The next element in the simulation pipeline
        self.action = env.process(self.run())  # Start the run process

    def run(self):
        """The generator function used in simulations."""
        while True:
            if len(self.waiting_queue) == 0:
                yield self.queue.get()  # Wait for a packet to arrive
            else:
                packet, scheduled_time = self.waiting_queue.pop(0)
                if self.env.now < scheduled_time:
                    yield self.env.timeout(scheduled_time - self.env.now)  # Wait until the scheduled time
                self.out.put(packet)  # Send the packet to the next element

    def put(self, packet):
        """Sends a packet to this element.
        
        Parameters
        ----------
        packet : Packet
            The packet to be delayed.
        """
        new_packet = copy(packet)  # Create a copy of the packet
        delay_time = uniform(0, self.max_delay)  # Calculate a random delay
        self.waiting_queue.append((new_packet, self.env.now + delay_time))  # Schedule the packet with the delay
        self.queue.put(True)  # Notify the run process





class StackDelayer:
    """
    Delays packets based on their size and a defined transmission speed.

    Parameters
    ----------
    env : simpy.Environment
        The simulation environment.
    speed : float
        The transmission speed in bytes per unit time.
    """
    def __init__(self, env, speed):
        self.env = env  # Simulation environment
        self.waiting_queue = []  # Queue to hold packets
        self.speed = speed  # Transmission speed
        self.queue = simpy.Store(env)  # SimPy store for synchronization
        self.out = None  # The next element in the simulation pipeline
        self.action = env.process(self.run())  # Start the run process

    def run(self):
        """The generator function used in simulations."""
        while True:
            if len(self.waiting_queue) == 0:
                yield self.queue.get()  # Wait for a packet to arrive
            else:
                packet = self.waiting_queue.pop(0)
                delay_time = packet.size / self.speed  # Calculate the delay based on packet size and speed
                yield self.env.timeout(delay_time)  # Wait for the calculated delay
                self.out.put(packet)  # Send the packet to the next element

    def put(self, packet):
        """Sends a packet to this element.
        
        Parameters
        ----------
        packet : Packet
            The packet to be delayed.
        """
        new_packet = copy(packet)  # Create a copy of the packet
        self.waiting_queue.append(new_packet)  # Add the packet to the queue
        self.queue.put(True)  # Notify the run process

