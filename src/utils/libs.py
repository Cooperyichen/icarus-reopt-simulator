#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Project ICARUS-MDA-POLY MTL Load balancing python code
# Created on Thu May 11 09:20:59 2023
# Importing the necessary libraries

"""
This project imports necessary packages. Each package serves a specific purpose, ranging from data manipulation, numerical computations, network analysis, plotting, optimization, and simulation.


Explanation of imported packages:
---------------------------------

- **collections**: Provides alternatives to Python's general-purpose built-in containers, such as dict, list, set, and tuple.
  - `deque`: Provides a double-ended queue.

- **time**: Provides various time-related functions.

- **networkx**: A package for the creation, manipulation, and study of the structure, dynamics, and functions of complex networks.

- **matplotlib.pyplot**: A plotting library for creating visualizations.

- **numpy**: The fundamental package for scientific computing with Python.

- **pandas**: A powerful, flexible, and easy-to-use open-source data analysis and data manipulation library.

- **scipy.optimize**: Provides optimization algorithms.
  - `minimize`: General-purpose optimization.
  - `linprog`: Linear programming optimization.

- **datetime**: Supplies classes for manipulating dates and times.

- **statistics**: Provides functions for calculating mathematical statistics of numeric data.
  - `mean`: Calculates the arithmetic mean.

- **random**: Implements pseudo-random number generators for various distributions.

- **yaml**: A human-friendly data serialization standard. Used for reading and writing YAML files.

- **cvxpy**: A Python-embedded modeling language for convex optimization problems.

- **re**: Provides regular expression matching operations.

- **math**: Provides mathematical functions defined by the C standard.

- **simpy**: A process-based discrete-event simulation framework based on standard Python.

- **copy**: Provides generic (shallow and deep) copying operations.

- **heapq**: Provides an implementation of the heap queue algorithm, also known as the priority queue algorithm.
  - `heappush`: Push item onto heap.
  - `heappop`: Pop the smallest item off the heap.

- **functools**: Higher-order functions: functions that act on or return other functions.

- **csv**: Implements classes to read and write tabular data in CSV format.

- **os**: Provides a way of using operating system-dependent functionality.

- **matplotlib.patches**: Provides classes for various shapes that are drawn inside a plot.

- **mpl_toolkits.mplot3d**: Provides tools for 3D plotting in matplotlib.

- **seaborn**: A Python data visualization library based on matplotlib.

- **glob**: Finds all the pathnames matching a specified pattern according to the rules used by the Unix shell.

- **sys**: Provides access to some variables used or maintained by the interpreter and to functions that interact strongly with the interpreter.

- **scipy.stats**: Contains a large number of probability distributions as well as a growing library of statistical functions.
  - `t`: For t-distribution, used in confidence interval calculation.

- **collections.defaultdict**: Dictionary subclass that calls a factory function to supply missing values.

- **itertools**: Implements a number of iterator building blocks inspired by constructs from APL, Haskell, and SML.

- **simpy.rt**: Real-time simulation with SimPy.

- **random.sample**: For random sampling.



"""
# @author: zineb.garroussi@polymtl.ca

# Importing the necessary libraries

from collections import deque  # Provides a double-ended queue
import time  # Provides functions for working with time
import networkx as nx  # Library for studying the structure and dynamics of complex networks
import matplotlib.pyplot as plt  # Plotting library for creating visualizations
import numpy as np  # Library for numerical computations
import pandas as pd  # Library for data manipulation and analysis
from scipy.optimize import minimize  # Provides optimization algorithms
import scipy.optimize  # Importing the scipy.optimize module for optimization functions
from scipy.optimize import linprog  # Linear programming optimization function
from datetime import datetime  # Library for working with dates and times
from statistics import mean  # Provides statistical functions
import datetime  # This module supplies classes for manipulating dates and times in both simple and complex ways.
import random  # Provides functions for generating random numbers
import yaml     # This module provides a Python interface for YAML, a human-friendly data serialization standard. It's used for reading and writing YAML files.
import cvxpy as cp  # cvxpy is a Python-embedded modeling language for convex optimization problems. It allows you to express your problem in a natural way that follows the math, rather than in the restrictive standard form required by solvers.
import re  # Importing the 're' module for regular expression operations
import math # Importing the 'math' module for mathematical operations
import random  # Importing the random library for generating random numbers
import simpy  # Importing the SimPy library for discrete-event simulation
# from random import expovariate  # Importing the expovariate function for exponential distribution
import copy  # Importing the copy library for deep and shallow copy functionalities
from simpy.core import BoundClass  # Importing BoundClass from SimPy core for class binding
from simpy.resources import base  # Importing base from Simpy's resources for resource-based functionalities
from heapq import heappush, heappop  # Importing heappush and heappop for heap queue (priority queue) operations
import functools # Importing functools for functional programming tools
import csv # Import the csv module to read/write data from/to .csv files.
import os # Import the os module to interact with the operating system, e.g., file and directory operations.
#import warnings
#warnings.simplefilter(action='ignore', category=Warning)
# Import patches from matplotlib to draw shapes, such as rectangles or circles.
import matplotlib.patches as patches
# Import Axes3D from mpl_toolkits.mplot3d to support 3D plotting.
from mpl_toolkits.mplot3d import Axes3D
# Import the datetime module to handle date and time operations.
import datetime
# Import seaborn for advanced data visualization, typically used for statistical plots.
import seaborn as sns #  'seaborn' is a Python data visualization library based on matplotlib.
import glob # #'glob' is used for finding all the pathnames matching a specified pattern according to the rules used by the Unix shell.
import sys  # Import the sys module

import copy # 'copy' provides methods that allow for the creation of shallow or deep copy of objects.

from scipy.stats import t  # For t-distribution, used in confidence interval calculation

from collections import defaultdict

import cProfile
import itertools

from scipy import stats

import simpy.rt

# import random
from random import sample

import seaborn as sns
from matplotlib.ticker import ScalarFormatter


import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

from functools import partial

# at this time numba does not support operation of cvxpy  and simpy 
# from numba import njit # Numba is a just-in-time compiler for Python that works best with heavy numerical functions. It can significantly speed up the execution of code that involves large arrays, loops, and mathematical computations.



# Importing the 'gurobipy' library
# 'gurobipy' is a Python module that provides an interface to Gurobi Optimizer, which is a popular software for mathematical optimization.
# The Gurobi Optimizer is capable of solving linear programming (LP), quadratic programming (QP), quadratically constrained programming (QCP), mixed-integer linear programming (MILP), mixed-integer quadratic programming (MIQP), and mixed-integer quadratically constrained programming (MIQCP) problems.
# The 'gurobipy' module allows Python users to build, optimize, and query optimization models in a natural and intuitive way.
#import gurobipy
