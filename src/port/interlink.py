#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from modem.obp_module import OBPModule
"""
This is the Interlink class, designed to represent a communication link between two modules in a network. An interlink is characterized by the two modules it connects and its communication properties, such as bandwidth and latency.

The Interlink class is essential for simulating the behavior of data transmission in a network, particularly focusing on the interaction between different network modules or nodes. By defining bandwidth and latency, it models the capacity and speed of the data link between these modules.

Attributes:
- module1 (OBPModule): The first module connected by the interlink.
- module2 (OBPModule): The second module connected by the interlink.
- bandwidth (float): The bandwidth of the interlink, typically measured in bps (bits per second). This attribute defines the data transmission capacity of the interlink.

The Interlink class also includes a special method (__repr__) to provide a human-readable representation of its instances, which is particularly useful for debugging and logging purposes.

"""

class Interlink:
    def __init__(self, module1, module2, bandwidth):
        self.module1 = module1  # First module connected by the interlink
        self.module2 = module2  # Second module connected by the interlink
        self.bandwidth = bandwidth  # Bandwidth of the interlink ( in bps)

    # def __repr__(self):
    #     return f"Interlink({self.module1.name}, {self.module2.name}, Bandwidth: {self.bandwidth} bps)"


    # def __repr__(self):
    #     # Updated to use x and y attributes for module representation
    #     return f"Interlink(Module1: ({self.module1.x}, {self.module1.y}), Module2: ({self.module2.x}, {self.module2.y}), Bandwidth: {self.bandwidth} bps)"



    def __repr__(self):
        # Ensure module1 and module2 are instances of OBPModule
        if isinstance(self.module1, OBPModule) and isinstance(self.module2, OBPModule):
            # Updated to use x and y attributes for module representation
            return f"Interlink(Module1: ({self.module1.x}, {self.module1.y}), Module2: ({self.module2.x}, {self.module2.y}), Bandwidth: {self.bandwidth} bps)"
        else:
            # Handle cases where module1 or module2 is not an instance of OBPModule
            return f"Interlink(Module1: {self.module1}, Module2: {self.module2}, Bandwidth: {self.bandwidth} bps)"