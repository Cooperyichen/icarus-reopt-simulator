#!/usr/bin/env python3
# -*- coding: utf-8 -*-



"""
A dataclass for keeping track of all the properties of a network flow.

This dataclass, `Flow`, encapsulates all relevant properties of a network flow,
including attributes for flow identification, source and destination elements, 
flow size, timing details and packet distribution characteristics.
It supports multiple paths for a single flow, with each path carrying a fraction 
of the flow calculated from an optimization problem. The class includes methods 
to represent the flow, initialize the send buffer, and determine the next send buffer 
based on the flow type and current time.

"""

# :author: zineb.garroussi@polymtl.ca


from dataclasses import dataclass, field
from collections.abc import Callable
from typing import List, Dict




@dataclass
class Flow:
    """
    A dataclass for keeping track of all the properties of a network flow.

    :param fid: Flow id, a unique identifier for the flow.
    :param src: Source element, the origin of the flow.
    :param dst: Destination element, the target of the flow.
    :param path: Paths the flow takes.
    :param flow_value: Value of the flow.
    :param size: Flow size in bytes, total size of the flow.
    :param start_time: The time when the flow starts.
    :param finish_time: The time when the flow finishes.
    :param arrival_dist: Packet arrival distribution function.
    :param size_dist: Packet size distribution function.
    :param pkt_gen: Packet generator object.
    :param pkt_sink: Packet sink object.
    :param last_arrival: The time of the last packet arrival.
    :param priority: Priority of the flow.
    :type fid: int
    :type src: str
    :type dst: str
    :type path: str
    :type flow_value: float
    :type size: int, optional
    :type start_time: float, optional
    :type finish_time: float, optional
    :type arrival_dist: Callable, optional
    :type size_dist: Callable, optional
    :type pkt_gen: object, optional
    :type pkt_sink: object, optional
    :type last_arrival: float
    :type priority: int
    """

    fid: int
    src: str
    dst: str
    path: str
    flow_value: float
    size: int = None
    start_time: float = None
    finish_time: float = None
    arrival_dist: Callable = None
    size_dist: Callable = None
    pkt_gen: object = None
    pkt_sink: object = None
    last_arrival: float = 0
    priority: int = 0

    def __repr__(self) -> str:
        """
        String representation of the Flow instance.

        :return: A string representing the Flow instance.
        :rtype: str
        """
        return f"Flow {self.fid} with path {self.path} and flow value {self.flow_value}"


