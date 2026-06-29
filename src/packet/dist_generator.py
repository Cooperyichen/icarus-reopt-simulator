"""
This class implements a packet generator that simulates the generation of packets 
with specified inter-arrival time and packet size distributions. Users can configure 
an initial delay before packet generation starts and specify a finish time to stop 
generation. Additionally, the generator allows setting the source ID and flow IDs 
for the generated packets. The `PacketGenerator` class has an `out` member 
variable, which is used to connect the generator to any network element that has a 
`put()` method for receiving packets.
"""

from packet.packet import Packet  # Import the Packet class from the packet.packet module
from utils.libs import *  # Importing all libraries centralized in the libs.py module


class PacketGenerator:
    """
    A packet generator using the simpy library.

    Attributes:
        id (int): Unique identifier for this packet generator.
        env (simpy.Environment): The simulation environment from simpy.
        adist (function): A callable that returns the inter-arrival time for packets.
        sdist (function): A callable that returns the size for the generated packets.
        initial_delay (float): The time duration (in simulation units) to wait before starting the packet generation.
        finish (float): The time duration (in simulation units) indicating when to stop packet generation.
        out (simpy.Store): The output target for generated packets (network element with a `put()` function).
        packets_sent (int): Counter for the number of packets that have been generated and sent.
        action (simpy.Process): A simpy process that runs the packet generation simulation. It's started when an instance of the class is created.
        flow_id (int): An identifier for the flow to which this packet generator belongs.
        priority (int): The priority level for the packets that are generated. Lower numbers indicate higher priority.
        generated_sizes (list): A list to store sizes of generated packets for further analysis, e.g., histogram plotting.
        arrival_packets (list): A list to store inter-arrival times of packets for further analysis.

    :param env: The simulation environment from simpy.
    :param id: Unique identifier for this packet generator.
    :param adist: A callable that returns the inter-arrival time for packets.
    :param sdist: A callable that returns the size for the generated packets.
    :param initial_delay: The time duration (in simulation units) to wait before starting the packet generation.
    :param finish: The time duration (in simulation units) indicating when to stop packet generation.
    :param size: Maximum size of packets to send.
    :param flow_id: An identifier for the flow to which this packet generator belongs.
    :param original_flow_id: Original flow ID before any remapping.
    :param rec_flow: Flag to record statistics of packets generated.
    :param debug: Flag to enable debug printing.
    :type env: simpy.Environment
    :type id: int
    :type adist: function
    :type sdist: function
    :type initial_delay: float
    :type finish: float
    :type size: float
    :type flow_id: int
    :type original_flow_id: int
    :type rec_flow: bool
    :type debug: bool
    """
    
    def __init__(self, env, id, adist, sdist, initial_delay=0, finish=None, size=None, flow_id=0, original_flow_id=0, rec_flow=False, debug=False):
        self.id = id  # Identifier for this packet generator
        self.env = env  # Simulation environment
        self.debug = debug  # Set the debug flag
        self.initial_delay = initial_delay  # Delay before starting packet generation
        self.finish = float("inf") if finish is None else finish  # Set the finish time for packet generation
        self.adist = adist  # Inter-arrival time distribution function
        self.sdist = sdist  # Packet size distribution function
        self.out = None  # Output target for generated packets
        self.flow_id = flow_id  # Identifier for the flow this packet generator belongs to
        self.original_flow_id = original_flow_id  # Original flow ID before any remapping
        self.packets_sent = 0  # Counter for the number of packets sent
        self.rec_flow = rec_flow  # Flag to record packet statistics
        self.size = float("inf") if size is None else size  # Maximum size of packets to send
        self.sent_size = 0  # Counter for the total size of packets sent

        self.action = env.process(self.run())  # Start the run() method as a SimPy process

        self.time_rec = []  # List to record packet generation times
        self.size_rec = []  # List to record packet sizes

    def run(self):
        """
        The generator function used in simulations.

        This function simulates packet generation, considering the inter-arrival times and packet sizes,
        and handles the output of generated packets.
        """
        yield self.env.timeout(self.initial_delay)  # Wait for the initial delay

        while self.env.now < self.finish and self.sent_size < self.size:
            # Continue generating packets until the finish time or size limit is reached
            packet = Packet(
                self.env.now,  # Current simulation time as the generation time
                self.sdist(),  # Generate packet size using the size distribution function
                self.packets_sent,  # Packet ID based on the number of packets sent
                src=self.id,  # Source ID for the packet
                flow_id=self.flow_id,  # Flow ID for the packet
                original_flow_id=self.original_flow_id  # Original flow ID
            )

            self.out.put(packet)  # Send the packet to the output target

            self.packets_sent += 1  # Increment the packet sent counter
            self.sent_size += packet.size  # Add the packet size to the total sent size

            if self.rec_flow:
                # Record packet statistics if the rec_flow flag is set
                self.time_rec.append(packet.timestamp)  # Record the packet generation time
                self.size_rec.append(packet.size)  # Record the packet size

            if self.debug:
                # Print debug information if the debug flag is set
                print(
                    "PacketGenerator {} sent packet {} with size {}, "
                    "flow_id {} at time {:.4f}.".format(
                        self.id,
                        packet.id,
                        packet.size,
                        packet.flow_id,
                        self.env.now,
                    )
                )

            # Wait for the next packet generation based on the inter-arrival time distribution
            yield self.env.timeout(self.adist())
