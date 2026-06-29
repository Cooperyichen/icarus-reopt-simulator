#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This is the OBPModule class, which represents an OBP module in a network or a grid.
Each OBPModule has an (x, y) position and a set of neighboring modules.

"""

# @author: zineb.garroussi@polymtl.ca


class OBPModule:
    """
    A class representing an OBP module in a network or grid.

    Attributes:
        x (int): The x-coordinate of the module.
        y (int): The y-coordinate of the module.
        neighbors (set): A set of neighboring OBPModule instances.
    """
    def __init__(self, x, y):
        """
        Initializes an OBPModule instance with a specified position.

        :param x: The x-coordinate of the module.
        :type x: int
        :param y: The y-coordinate of the module.
        :type y: int
        """
        self.x = x  # Represents the x-coordinate of the module
        self.y = y  # Represents the y-coordinate of the module
        self.neighbors = set()  # Use set to store neighbors for faster insertion and search

    def add_neighbor(self, neighbor):
        """
        Adds a neighboring module to the set of neighbors.

        :param neighbor: The neighboring OBPModule to be added.
        :type neighbor: OBPModule
        """
        self.neighbors.add(neighbor)

    def __repr__(self):
        """
        Returns a string representation of the OBPModule instance.

        :return: A string representation of the OBPModule.
        :rtype: str
        """
        return f"OBPModule({self.x}, {self.y})"

    @property
    def name(self):
        """
        Gets the name of the module based on its coordinates.

        :return: The name of the module.
        :rtype: str
        """
        return f"OBPModule({self.x}, {self.y})"

    @classmethod
    def get_all_instances(cls):
        """
        Returns a list of all created instances of OBPModule.

        :return: A list of all instances of OBPModule.
        :rtype: list
        """
        return cls.instances

    def __eq__(self, other):
        """
        Checks equality with another OBPModule based on their coordinates.

        :param other: Another instance of OBPModule to compare with.
        :type other: OBPModule
        :return: True if both modules have the same coordinates, False otherwise.
        :rtype: bool
        """
        if isinstance(other, OBPModule):
            return self.x == other.x and self.y == other.y
        return False

    def __hash__(self):
        """
        Provides a hash based on the module's coordinates for use in hash-based collections.

        :return: The hash value of the module.
        :rtype: int
        """
        return hash((self.x, self.y))
