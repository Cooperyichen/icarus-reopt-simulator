#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Global Optimal Ratio Strategy Implementation

Strategy 3: Given a 10-step arrival rate sequence, find a fixed path flow ratio
that minimizes the average maximum link utilization across all 10 steps.
"""

import sys
import os
import pandas as pd
import numpy as np
import cvxpy as cp
from scipy.optimize import minimize

# Add the project src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

# Note: parse_path is defined locally to avoid circular import

def parse_path(path_str):
    """
    Parse path string to extract interlinks (only between OBP modules).
    
    Args:
        path_str: Path string like "OBPModule(0,0)_uplink_0 -> OBPModule(0,0) -> ..."
        
    Returns:
        list: List of (u, v) tuples representing interlinks
    """
    parts = path_str.split(' -> ')
    interlinks = []
    
    # Skip first and last parts (uplink/downlink), only look at OBPModule nodes
    obp_modules = []
    for part in parts:
        if 'OBPModule' in part and '(' in part:
            # Extract coordinates from "OBPModule(x, y)"
            start = part.find('(') + 1
            end = part.find(')')
            if start > 0 and end > start:
                coords_str = part[start:end]
                try:
                    x, y = map(int, coords_str.split(','))
                    obp_modules.append((x, y))
                except ValueError:
                    pass
    
    # Extract interlinks (edges between consecutive OBP modules)
    for i in range(len(obp_modules) - 1):
        u = obp_modules[i]
        v = obp_modules[i + 1]
        # Only include if u != v (actual movement between modules)
        if u != v:
            interlinks.append((u, v))
    
    return interlinks


def extract_paths_from_step1(step1_mcfp_file):
    """
    Extract path set from Step 1 optimization results.
    
    Args:
        step1_mcfp_file: Path to Step 1's mcfp_results CSV file
        
    Returns:
        dict: {commodity_id: [path1, path2, ...]}
    """
    df = pd.read_csv(step1_mcfp_file)
    
    paths_by_commodity = {}
    
    for commodity_id in df['id_flow'].unique():
        commodity_df = df[df['id_flow'] == commodity_id]
        paths = commodity_df['Path'].unique().tolist()
        paths_by_commodity[int(commodity_id)] = paths
    
    return paths_by_commodity


def extract_paths_info_from_step1(step1_mcfp_file):
    """
    Extract path information (including interlink usage) from Step 1 results.
    
    Args:
        step1_mcfp_file: Path to Step 1's mcfp_results CSV file
        
    Returns:
        dict: {
            commodity_id: {
                'paths': [path1, path2, ...],
                'source': source_node,
                'destination': destination_node,
                'priority': priority,
                'interlinks': {path: [interlink1, interlink2, ...]}
            }
        }
    """
    df = pd.read_csv(step1_mcfp_file)
    
    paths_info = {}
    
    for commodity_id in df['id_flow'].unique():
        commodity_df = df[df['id_flow'] == commodity_id]
        
        # Get basic info
        first_row = commodity_df.iloc[0]
        source = first_row['Source']
        destination = first_row['Destination']
        priority = first_row['Priority']
        
        # Extract paths and their interlinks
        paths = []
        interlinks_by_path = {}
        
        for _, row in commodity_df.iterrows():
            path = row['Path']
            if path not in paths:
                paths.append(path)
                # Parse path to get interlinks
                interlinks = parse_path(path)
                interlinks_by_path[path] = interlinks
        
        paths_info[int(commodity_id)] = {
            'paths': paths,
            'source': source,
            'destination': destination,
            'priority': priority,
            'interlinks': interlinks_by_path
        }
    
    return paths_info


def calculate_single_step_utilization(path_ratios, arrival_rates, paths_info, config):
    """
    Calculate maximum link utilization for a single step given path ratios and arrival rates.
    
    Args:
        path_ratios: dict {commodity_id: {path: ratio}}
        arrival_rates: list [rate0, rate1, rate2, rate3] (packets/s)
        paths_info: dict from extract_paths_info_from_step1
        config: Configuration dictionary
        
    Returns:
        float: Maximum link utilization percentage
    """
    interlink_capacity = config['system']['interlink_capacity']  # bits/s
    packet_size = config['simulation']['avg_packet_size']  # bytes
    
    # Calculate interlink traffic
    interlink_traffic = {}
    
    for commodity_id, ratios in path_ratios.items():
        if commodity_id >= len(arrival_rates):
            continue
        
        demand = arrival_rates[commodity_id]
        commodity_info = paths_info.get(commodity_id)
        
        if commodity_info is None:
            continue
        
        interlinks_by_path = commodity_info['interlinks']
        
        # Apply ratios to each path
        for path, ratio in ratios.items():
            if path not in interlinks_by_path:
                continue
            
            # Calculate flow on this path
            path_flow = demand * ratio  # packets/s
            
            # Get interlinks used by this path
            interlinks = interlinks_by_path[path]
            
            # Add traffic to each interlink (in bits/s)
            bits_per_second = path_flow * packet_size * 8
            
            for interlink in interlinks:
                if interlink not in interlink_traffic:
                    interlink_traffic[interlink] = 0.0
                interlink_traffic[interlink] += bits_per_second
    
    # Calculate utilization for each interlink
    max_utilization = 0.0
    for interlink, bits_per_second in interlink_traffic.items():
        utilization = (bits_per_second / interlink_capacity) * 100.0
        max_utilization = max(max_utilization, utilization)
    
    return max_utilization


def calculate_average_max_link_utilization(path_ratios, sequence, paths_info, config):
    """
    Calculate average maximum link utilization across multiple steps.
    
    Args:
        path_ratios: dict {commodity_id: {path: ratio}}
        sequence: numpy array or list of lists, shape (num_steps, num_commodities)
                  Each row is arrival rates for one step
        paths_info: dict from extract_paths_info_from_step1
        config: Configuration dictionary
        
    Returns:
        float: Average maximum link utilization percentage across all steps
    """
    if isinstance(sequence, pd.DataFrame):
        sequence = sequence.values
    
    sequence = np.array(sequence)
    num_steps = sequence.shape[0]
    
    utilizations = []
    for step_idx in range(num_steps):
        arrival_rates = sequence[step_idx, :].tolist()
        step_util = calculate_single_step_utilization(
            path_ratios, arrival_rates, paths_info, config
        )
        utilizations.append(step_util)
    
    avg_utilization = np.mean(utilizations)
    return avg_utilization


def _path_ratios_dict_to_vector(path_ratios_dict, paths_info):
    """
    Convert path ratios from dict format to vector format for optimization.
    
    Args:
        path_ratios_dict: dict {commodity_id: {path: ratio}}
        paths_info: dict from extract_paths_info_from_step1
        
    Returns:
        numpy.array: Flattened vector of ratios, shape (total_num_paths,)
        dict: Mapping from (commodity_id, path_idx) to vector index
    """
    ratios_vector = []
    index_mapping = {}  # (commodity_id, path_idx) -> vector_index
    
    vector_idx = 0
    for commodity_id in sorted(paths_info.keys()):
        paths = paths_info[commodity_id]['paths']
        for path_idx, path in enumerate(paths):
            ratio = path_ratios_dict.get(commodity_id, {}).get(path, 0.0)
            ratios_vector.append(ratio)
            index_mapping[(commodity_id, path_idx)] = vector_idx
            vector_idx += 1
    
    return np.array(ratios_vector), index_mapping


def _path_ratios_vector_to_dict(ratios_vector, paths_info, index_mapping):
    """
    Convert path ratios from vector format back to dict format.
    
    Args:
        ratios_vector: numpy.array of ratios
        paths_info: dict from extract_paths_info_from_step1
        index_mapping: dict from _path_ratios_dict_to_vector
        
    Returns:
        dict: {commodity_id: {path: ratio}}
    """
    path_ratios_dict = {}
    
    for commodity_id in sorted(paths_info.keys()):
        paths = paths_info[commodity_id]['paths']
        path_ratios = {}
        
        for path_idx, path in enumerate(paths):
            vector_idx = index_mapping[(commodity_id, path_idx)]
            ratio = ratios_vector[vector_idx]
            path_ratios[path] = ratio
        
        path_ratios_dict[commodity_id] = path_ratios
    
    return path_ratios_dict


def optimize_global_path_ratios(sequence, paths_info, config, initial_ratios=None, method='SLSQP',
                                minimize_options=None):
    """
    Optimize global path ratios to minimize average maximum link utilization.
    
    Args:
        sequence: numpy array or DataFrame, shape (num_steps, num_commodities)
        paths_info: dict from extract_paths_info_from_step1
        config: Configuration dictionary
        initial_ratios: dict {commodity_id: {path: ratio}} for initial guess (optional)
        method: Optimization method (default: 'SLSQP')
        minimize_options: dict merged into scipy.optimize.minimize(..., options=...)
        
    Returns:
        dict: {
            'optimal_ratios': {commodity_id: {path: optimal_ratio}},
            'optimal_value': float (average max link util),
            'optimization_result': scipy.optimize.OptimizeResult
        }
    """
    # Convert sequence to numpy array
    if isinstance(sequence, pd.DataFrame):
        sequence = sequence.values
    sequence = np.array(sequence)
    
    # Get initial ratios (use Step 1 ratios if not provided)
    if initial_ratios is None:
        # Create uniform initial ratios
        initial_ratios = {}
        for commodity_id, info in paths_info.items():
            paths = info['paths']
            num_paths = len(paths)
            uniform_ratio = 1.0 / num_paths if num_paths > 0 else 0.0
            initial_ratios[commodity_id] = {path: uniform_ratio for path in paths}
    
    # Convert to vector format
    ratios_vector, index_mapping = _path_ratios_dict_to_vector(initial_ratios, paths_info)
    num_vars = len(ratios_vector)
    
    # Build constraint: each commodity's ratios sum to 1.0
    num_commodities = len(paths_info)
    constraint_list = []
    
    # Equality constraints: sum of ratios for each commodity = 1.0
    for commodity_id in sorted(paths_info.keys()):
        paths = paths_info[commodity_id]['paths']
        
        def make_equality_constraint(cid):
            def equality_constraint(x):
                total = 0.0
                for path_idx in range(len(paths_info[cid]['paths'])):
                    vector_idx = index_mapping[(cid, path_idx)]
                    total += x[vector_idx]
                return total - 1.0
            return equality_constraint
        
        constraint_list.append({
            'type': 'eq',
            'fun': make_equality_constraint(commodity_id)
        })
    
    # Bounds: each ratio >= 0 (non-negativity)
    bounds = [(0.0, None) for _ in range(num_vars)]
    
    # Objective function
    def objective(ratios_vec):
        # Convert vector to dict
        ratios_dict = _path_ratios_vector_to_dict(ratios_vec, paths_info, index_mapping)
        
        # Calculate average utilization
        avg_util = calculate_average_max_link_utilization(
            ratios_dict, sequence, paths_info, config
        )
        return avg_util
    
    opt_defaults = {'maxiter': 1000, 'ftol': 1e-9}
    merged_options = {**opt_defaults, **(minimize_options or {})}
    
    # Run optimization
    result = minimize(
        objective,
        ratios_vector,
        method=method,
        bounds=bounds,
        constraints=constraint_list,
        options=merged_options
    )
    
    converged = bool(getattr(result, 'success', False))
    if not converged:
        msg = getattr(result, 'message', '')
        print("\n" + "!" * 80)
        print("WARNING: Global path-ratio optimization (SLSQP) did not report success.")
        print(f"  status={getattr(result, 'status', None)!r} message={msg!r}")
        print("!" * 80 + "\n")
    
    # Convert result back to dict
    optimal_ratios = _path_ratios_vector_to_dict(result.x, paths_info, index_mapping)
    
    # Normalize ratios (ensure they sum to 1.0 for each commodity, accounting for rounding)
    for commodity_id, ratios in optimal_ratios.items():
        total = sum(ratios.values())
        if total > 0:
            for path in ratios:
                ratios[path] /= total
    
    return {
        'optimal_ratios': optimal_ratios,
        'optimal_value': result.fun,
        'optimization_result': result,
        'optimizer_success': converged,
    }


def _collect_all_interlinks(paths_info):
    """All interlink keys that appear on any path in paths_info."""
    seen = set()
    for info in paths_info.values():
        for ilist in info['interlinks'].values():
            for e in ilist:
                seen.add(e)
    return sorted(seen)


def solve_global_optimal_ratio_with_capacity_lp(
    sequence, paths_info, config, cvxpy_solve_kwargs=None,
    max_utilization_percent=100.0,
):
    """
    Minimize average per-step max link utilization (%) subject to fixed path ratios
    and per-step per-interlink utilization <= max_utilization_percent.

    Uses a CVXPY LP with epigraph variables u_t >= max_e util_{t,e}(x).

    Load model matches calculate_single_step_utilization (bits/s on interlinks).

    Args:
        sequence: (num_steps, num_commodities) array or DataFrame
        paths_info: from extract_paths_info_from_step1
        config: scenario config (interlink_capacity, avg_packet_size)
        cvxpy_solve_kwargs: passed to problem.solve(**kwargs)
        max_utilization_percent: capacity limit as percent (default 100)

    Returns:
        dict with keys optimal_ratios (or None), optimal_value (mean u), cvxpy_status,
        feasible (bool), u_values (np.ndarray or None), problem_value
    """
    if isinstance(sequence, pd.DataFrame):
        sequence = sequence.values
    sequence = np.asarray(sequence, dtype=float)
    num_steps, num_commodities = sequence.shape

    interlink_capacity = float(config['system']['interlink_capacity'])
    packet_size = float(config['simulation']['avg_packet_size'])
    bps_per_unit_ratio = packet_size * 8.0  # demand is pkt/s; x multiplies to bits/s path flow

    empty_dict = {cid: {} for cid in paths_info.keys()}
    _, index_mapping = _path_ratios_dict_to_vector(empty_dict, paths_info)
    n = len(index_mapping)
    if n == 0:
        return {
            'optimal_ratios': None,
            'optimal_value': float('nan'),
            'cvxpy_status': 'no_variables',
            'feasible': False,
            'u_values': None,
            'problem_value': float('nan'),
        }

    all_interlinks = _collect_all_interlinks(paths_info)
    scale = interlink_capacity / max_utilization_percent  # load <= scale * u  <=>  util <= u

    x = cp.Variable(n)
    u = cp.Variable(num_steps)
    constraints = [x >= 0, u >= 0]

    for commodity_id in sorted(paths_info.keys()):
        paths = paths_info[commodity_id]['paths']
        idxs = [index_mapping[(commodity_id, path_idx)] for path_idx in range(len(paths))]
        constraints.append(cp.sum(x[idxs]) == 1)

    for t in range(num_steps):
        for e in all_interlinks:
            terms = []
            for commodity_id in sorted(paths_info.keys()):
                if commodity_id >= num_commodities:
                    continue
                demand = sequence[t, commodity_id]
                if demand == 0.0:
                    continue
                info = paths_info[commodity_id]
                for path_idx, path in enumerate(info['paths']):
                    if e not in info['interlinks'].get(path, []):
                        continue
                    j = index_mapping[(commodity_id, path_idx)]
                    coef = demand * bps_per_unit_ratio
                    terms.append(coef * x[j])
            if not terms:
                continue
            load = cp.sum(terms) if len(terms) > 1 else terms[0]
            constraints.append(load <= scale * u[t])

    objective = cp.Minimize(cp.sum(u) / num_steps)
    problem = cp.Problem(objective, constraints)

    solve_kw = {'solver': cp.ECOS, 'verbose': False}
    if cvxpy_solve_kwargs:
        solve_kw.update(cvxpy_solve_kwargs)

    try:
        problem.solve(**solve_kw)
    except cp.error.SolverError:
        try:
            solve_kw_sc = {k: v for k, v in solve_kw.items() if k != 'solver'}
            solve_kw_sc['solver'] = cp.SCS
            problem.solve(**solve_kw_sc)
        except Exception:
            return {
                'optimal_ratios': None,
                'optimal_value': float('nan'),
                'cvxpy_status': 'solver_error',
                'feasible': False,
                'u_values': None,
                'problem_value': float('nan'),
            }

    status = problem.status
    feasible = status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE) or str(status).lower() in (
        'optimal', 'optimal_inaccurate'
    )

    if not feasible or x.value is None:
        return {
            'optimal_ratios': None,
            'optimal_value': float('nan'),
            'cvxpy_status': str(status),
            'feasible': False,
            'u_values': None,
            'problem_value': float('nan'),
        }

    x_val = np.asarray(x.value).flatten()
    u_val = np.asarray(u.value).flatten()
    optimal_ratios = _path_ratios_vector_to_dict(x_val, paths_info, index_mapping)
    for commodity_id, ratios in optimal_ratios.items():
        tot = sum(ratios.values())
        if tot > 0:
            for path in ratios:
                ratios[path] /= tot

    opt_val = float(problem.value) if problem.value is not None else float(np.mean(u_val))
    return {
        'optimal_ratios': optimal_ratios,
        'optimal_value': opt_val,
        'cvxpy_status': str(status),
        'feasible': True,
        'u_values': u_val,
        'problem_value': float(problem.value) if problem.value is not None else opt_val,
    }

