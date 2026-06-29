"""
Implemented variants of a packet splitter element, which sends a copy of
the arriving packets to each downstream element.

This module provides two classes, `Splitter` and `NWaySplitter`, which
are used to replicate packets and forward them to multiple downstream
elements. These classes can be used in network simulations where
broadcasting packets to multiple destinations is required.

Classes
-------
Splitter : A two-way splitter that sends a copy of the arriving packets
           to each of its two downstream elements.
NWaySplitter : An N-way splitter that sends a copy of the arriving packets
               to each of its N downstream elements.

Example
-------
Assume we have three downstream elements: port1, port2, and port3.

For the `Splitter` class:
    splitter = Splitter()
    splitter.out1 = port1
    splitter.out2 = port2

    When a packet arrives at the splitter, it is sent to both port1
    and port2.

For the `NWaySplitter` class:
    n_way_splitter = NWaySplitter(3)
    n_way_splitter.outs[0] = port1
    n_way_splitter.outs[1] = port2
    n_way_splitter.outs[2] = port3

    When a packet arrives at the N-way splitter, it is sent to all three
    ports: port1, port2, and port3.

Author
------
zineb.garroussi@polymtl.ca
"""


import copy


class Splitter:
    """A simple two-way splitter with two downstream elements."""
    
    def __init__(self) -> None:
        """ Initializes the splitter with no downstream elements. """
        self.out1 = None  # The first downstream element
        self.out2 = None  # The second downstream element

    def put(self, packet):
        """ Sends a packet to this element and duplicates it for each downstream element.
        
        Parameters
        ----------
        packet : Packet
            The packet to be routed to downstream elements.
        """
        if self.out1:
            self.out1.put(packet)  # Forward the packet to the first downstream element

        if self.out2:
            self.out2.put(copy.copy(packet))  # Forward a copy of the packet to the second downstream element


class NWaySplitter:
    """An N-way splitter with *N* downstream elements."""
    
    def __init__(self, N) -> None:
        """ Initializes the splitter with N downstream elements.
        
        Parameters
        ----------
        N : int
            The number of downstream elements. Must be larger than 1.
        
        Raises
        ------
        ValueError
            If N is less than or equal to 1.
        TypeError
            If N is not an integer.
        """
        if isinstance(N, int):
            if N > 1:
                self.outs = [None] * N  # Initialize the list of downstream elements
                self.N = N  # Store the number of downstream elements
            else:
                raise ValueError("N should be larger than 1.")
        else:
            raise TypeError("N should be an integer larger than 1.")

    def put(self, packet):
        """ Sends a packet to this element and duplicates it for each downstream element.
        
        Parameters
        ----------
        packet : Packet
            The packet to be routed to downstream elements.
        """
        self.outs[0].put(packet)  # Forward the original packet to the first downstream element

        for i in range(self.N - 1):
            packet_copy = copy.copy(packet)  # Create a copy of the packet
            self.outs[i + 1].put(packet_copy)  # Forward the copied packet to the corresponding downstream element

