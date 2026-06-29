"""
The objective of this code is to implement a Two Rate Three Color Marker (TrTCM) 
as defined in RFC 2698, which is used to categorize network packets based on their 
compliance with defined traffic rates and burst sizes. The TrTCM marks each packet 
with one of three colors (green, yellow, or red) depending on whether the packet 
conforms to or exceeds specified rate limits: the Peak Information Rate (PIR) and 
the Committed Information Rate (CIR), as well as their respective burst sizes (PBS 
and CBS).

This categorization helps in managing network traffic by enabling differentiated 
handling of packets:

Green packets (marked with 0) are within both the committed and peak rate limits, 
indicating they conform to the expected traffic profile.
Yellow packets (marked with 1) exceed the committed rate but are within the peak 
rate, indicating they are less critical but still acceptable.
Red packets (marked with 2) exceed both the committed and peak rates, indicating 
they should be dropped or given the lowest priority.

By using this marking system, network devices can prioritize traffic, ensuring 
that high-priority traffic (green packets) is delivered reliably, while lower-priority 
or excessive traffic (yellow and red packets) is handled appropriately based on 
available network resources. This mechanism is crucial for maintaining Quality of 
Service (QoS) in networks, particularly in scenarios with limited bandwidth or 
varying traffic loads.

Implements a two rate tricolor marker. It uses the flow_id packet field to mark each
packet with green = 0, yellow = 1, red = 2.

Reference:
RFC 2698: A Two Rate Three Color Marker
https://datatracker.ietf.org/doc/html/rfc2698

Example Usage
-------------
import simpy

# Define a simple packet class
class Packet:
    def __init__(self, size):
        self.size = size
        self.color = None  # Will be set by the TrTCM

# Define a process that uses the TrTCM
def producer(env, trtcm, packet_size):
    while True:
        packet = Packet(packet_size)
        yield env.timeout(1)  # Produce a packet every 1 time unit
        trtcm.put(packet)
        print(f'Packet marked {packet.color} at time {env.now}')

env = simpy.Environment()
trtcm = TrTCM(env, pir=8000, pbs=1000, cir=4000, cbs=500)
env.process(producer(env, trtcm, packet_size=200))
env.run(until=10)
"""



class TrTCM:
    """ 
    A Two Rate Three Color Marker (TrTCM). Uses the flow_id packet field to
    mark the packet with green = 0, yellow = 1, red = 2.

    Parameters
    ----------
    env : simpy.Environment
        The simulation environment.
    pir : int
        The Peak Information Rate in units of bits (slightly different from RFC).
    pbs : int
        The Peak Burst Size in units of bytes.
    cir : int
        The Committed Information Rate in units of bits.
    cbs : int
        The Committed Burst Size in bytes.
    """
    def __init__(self, env, pir: int, pbs: int, cir: int, cbs: int):
        """ Initializes the TrTCM with the provided parameters. """
        self.env = env  # Simulation environment
        self.out = None  # The next element in the simulation pipeline
        self.pir = pir  # Peak Information Rate in bits
        self.pbs = pbs  # Peak Burst Size in bytes
        self.cir = cir  # Committed Information Rate in bits
        self.cbs = cbs  # Committed Burst Size in bytes
        self.peak_bucket = pbs  # Initial peak bucket size
        self.committed_bucket = cbs  # Initial committed bucket size
        self.last_time = 0.0  # Last time the buckets were updated

    def put(self, packet):
        """ Sends a packet to this element and marks it with a color based on the bucket levels.

        Parameters
        ----------
        packet : Packet
            The packet to be marked and sent to the next element.
        """
        # Calculate time increment since the last bucket update
        time_inc = self.env.now - self.last_time
        self.last_time = self.env.now

        # Refill the peak bucket
        self.peak_bucket += self.pir * time_inc / 8.0
        if self.peak_bucket > self.pbs:
            self.peak_bucket = self.pbs

        # Refill the committed bucket
        self.committed_bucket += self.cir * time_inc / 8.0
        if self.committed_bucket > self.cbs:
            self.committed_bucket = self.cbs

        # Determine the color of the packet based on bucket levels
        if self.peak_bucket - packet.size < 0:
            packet.color = 'red'
        elif self.committed_bucket - packet.size < 0:
            packet.color = 'yellow'
            self.peak_bucket -= packet.size
        else:
            packet.color = 'green'
            self.peak_bucket -= packet.size
            self.committed_bucket -= packet.size

        # Send the packet to the next element
        self.out.put(packet)

