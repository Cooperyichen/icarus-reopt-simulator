#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This module defines the FIBDemux class, a demultiplexing element that forwards incoming packets 
to one of its output ports based on a forwarding information base (FIB) dictionary.

The FIBDemux class uses a FIB dictionary to map flow IDs to specific output ports. 
Packets can be forwarded based on predefined rules in the FIB, a list of downstream elements, 
or directly based on specific flow IDs.

"""

# Author: zineb.garroussi@polymtl.ca


class FIBDemux:
    """
    A demultiplexing element that forwards incoming packets to one of its
    output ports based on a forwarding information base (FIB) dictionary.

    The constructor takes a list of downstream elements for the corresponding
    output ports as its input.

    Attributes:
        fib (dict): Forwarding Information Base (FIB). A dictionary where the key is the
            flow id and the value is the corresponding output port index in 'outs'.
        outs (list): List of downstream elements corresponding to the output ports.
        ends (dict): Dictionary of downstream elements corresponding to specific flow ids.
            Packets with flow ids in this dictionary will be forwarded directly
            to the corresponding downstream element.
        default (optional): Default downstream element to handle packets with flow ids that do not
            have a corresponding entry in the FIB or 'ends'.

    :param fib: Forwarding Information Base (FIB). A dictionary where the key is the
        flow id and the value is the corresponding output port index in 'outs'.
    :type fib: dict, optional
    :param outs: List of downstream elements corresponding to the output ports.
    :type outs: list, optional
    :param ends: Dictionary of downstream elements corresponding to specific flow ids.
        Packets with flow ids in this dictionary will be forwarded directly
        to the corresponding downstream element.
    :type ends: dict, optional
    :param default: Default downstream element to handle packets with flow ids that do not
        have a corresponding entry in the FIB or 'ends'.
    :type default: optional
    """

    def __init__(self, fib=None, outs=None, ends=None, default=None):
        """
        Constructor.

        Parameters
        ----------
        fib : dict, optional
            Forwarding Information Base (FIB). A dictionary where the key is the
            flow id and the value is the corresponding output port index in 'outs'.
        outs : list, optional
            List of downstream elements corresponding to the output ports.
        ends : dict, optional
            Dictionary of downstream elements corresponding to specific flow ids.
            Packets with flow ids in this dictionary will be forwarded directly
            to the corresponding downstream element.
        default : optional
            Default downstream element to handle packets with flow ids that do not
            have a corresponding entry in the FIB or 'ends'.
        """
        self.fib = fib if fib is not None else {}
        self.outs = outs if outs is not None else []
        self.ends = ends if ends is not None else {}
        self.default = default
        self.packets_received = 0

    def put(self, packet):
        """
        Sends a packet to this element and forwards it to the appropriate
        downstream element based on the FIB or 'ends' dictionary.

        If the packet's flow_id is found in the 'ends' dictionary, it is
        forwarded to the corresponding downstream element in 'ends'.
        If the flow_id is found in the FIB, the packet is forwarded to the
        corresponding output port in 'outs'. If the flow_id is not found
        in the FIB or 'ends', the packet is forwarded to the default port
        if one is provided.

        Parameters
        ----------
        packet : Packet
            The packet to be routed.
        """
        self.packets_received += 1
        flow_id = packet.flow_id

        if flow_id in self.ends:
            # Directly forward to the specific downstream element for this flow_id
            self.ends[flow_id].put(packet)
        elif flow_id in self.fib:
            # Forward to the output port based on the FIB
            if isinstance(self.fib[flow_id], list):
                for idx in self.fib[flow_id]:
                    self.outs[idx].put(packet)
            else:
                self.outs[self.fib[flow_id]].put(packet)
        else:
            # If the flow_id is not in the FIB or ends, use the default output (if specified)
            if self.default:
                self.default.put(packet)
