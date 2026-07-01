#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The objective of this code is to implement a tagged and ordered variant of the SimPy Store class. 

In this variant, each item stored in the TaggedStore is associated with a tag that is used to sort the elements. 


This sorting is crucial for the removal ordering of items from the store, which allows for the implementation of more sophisticated queueing disciplines such as Weighted Fair Queueing and Virtual Clock.

 - The tag ensures that items can be retrieved based on their priority or other ordering criteria, rather than the default first-in, first-out (FIFO) method. 
 
 - The TaggedStore class leverages Python's heapq module to maintain the items in a heap structure, ensuring efficient insertion and removal operations based on the tags. 
 

This functionality is particularly useful in simulations and systems where order and priority of processing are essential.



"""

from heapq import heappop, heappush
from simpy.core import BoundClass
from simpy.resources import base

class TaggedStorePut(base.Put):
    """Put `item` into the store if possible, or wait until it is.
    The item must be a tuple (tag, contents) where the tag is used
    to sort the content in the TaggedStore.

    Parameters
    ----------
    resource : TaggedStore
        The store where the item should be put.
    item : tuple
        The item to be put into the store, consisting of a tag and contents.
    """
    def __init__(self, resource, item):
        self.item = item  # The item to be put into the store.
        super().__init__(resource)  # Call the base class constructor.

class TaggedStoreGet(base.Get):
    """Get an item from the store or wait until one is available.

    Parameters
    ----------
    resource : TaggedStore
        The store from which the item should be retrieved.
    """

class TaggedStore(base.BaseResource):
    """Models the production and consumption of concrete Python objects.

    Items put into the store can be of any type. By default, they are put and
    retrieved from the store in a first-in first-out order.

    Parameters
    ----------
    env : simpy.Environment
        The simulation environment.
    capacity : float, optional
        The maximum size of the store. Default is infinite capacity.

    Raises
    ------
    ValueError
        If capacity is not greater than 0.
    """
    def __init__(self, env, capacity=float('inf')):
        super().__init__(env, capacity=capacity)

        if capacity <= 0:
            raise ValueError('"capacity" must be > 0.')

        self._capacity = capacity  # Store capacity.
        self.items = []  # List to store items, maintained as a heap.
        self.event_count = 0  # Used to break ties in the heap.

    @property
    def capacity(self):
        """The maximum capacity of the tagged store."""
        return self._capacity

    put = BoundClass(TaggedStorePut)
    """Create a new `StorePut` event."""

    get = BoundClass(TaggedStoreGet)
    """Create a new `StoreGet` event."""

    def _do_put(self, event):
        """Internal method to handle putting an item into the store.

        Parameters
        ----------
        event : TaggedStorePut
            The put event containing the item to be added.
        """
        self.event_count += 1  # Increment the event count to break ties.
        if len(self.items) < self._capacity:
            # Push the item onto the heap, maintaining order by tag and event count.
            heappush(self.items, [event.item[0], self.event_count, event.item[1]])
            event.succeed()  # Mark the put event as successful.

    def _do_get(self, event):
        """Internal method to handle getting an item from the store.

        Parameters
        ----------
        event : TaggedStoreGet
            The get event requesting an item from the store.
        """
        if self.items:
            # Pop the item with the lowest tag (and event count) from the heap.
            event.succeed(heappop(self.items)[2])  # Return only the content of the item.

