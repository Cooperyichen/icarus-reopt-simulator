#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract dual variables from optimization for all steps.
Requires modifying optimizer to return dual variable information.
"""

import sys
import os
import pandas as pd
import cvxpy as cp

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

# We need to modify the optimizer to extract dual variables
# The dual variables correspond to the demand constraints
# Each commodity has one demand constraint: sum(paths) = demand
# The dual variable value tells us the shadow price of increasing that commodity's demand

print("=" * 80)
print("Dual Variable Extraction")
print("=" * 80)
print()
print("This script requires modification of the optimizer to extract dual variables.")
print("Dual variables are associated with demand constraints.")
print("Each commodity has one dual variable representing the marginal cost of increasing demand.")
print()

