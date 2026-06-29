#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controlled dual-validation experiment (baseline optimal vs step1-only prediction).

Baseline:
  - Re-optimize at every step to get the per-step optimal objective z*_t

Prediction:
  - Optimize only at step 1 to get:
      - z*_1
      - demand duals (lambda)
      - tight utilization constraint duals (mu)
  - For steps t>=2, do NOT solve; predict z_t using:
      - lambda-only: z_hat = z1 + lambda_k * Δdk
      - enhanced:    z_hat = z1 + lambda_k * Δdk + mu_e * Δu_e
        where Δu_e is the utilization change (%) on the step-1 max edge under
        preserved path ratios, computed from step-1 routing output.

Outputs:
  - src/results/multi_step_comparison/dual_validation/controlled/controlled_dual_prediction_comparison.csv
"""

import os
import sys
import pandas as pd
import numpy as np

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..")
sys.path.insert(0, src_dir)

from topo.utils import load_yaml_file
from topo.toroidal_topo import ToroidalTopo
from optimizer.muti_commodity_optimizer import MultiCommodityOptimizer
from main.multi_step_comparison_experiment import calculate_max_link_utilization
from main.enhanced_dual_analysis import find_max_utilization_edge, calculate_edge_flow_change
from main.analyze_all_dual_variables import match_edge_in_capacity_duals


def _solve_step(config, arrival_rates):
    step_config = config.copy()
    step_config["fixed_demand"] = config["fixed_demand"].copy()
    step_config["fixed_demand"]["arrival_rate"] = arrival_rates

    width = step_config["system"]["width"]
    height = step_config["system"]["height"]
    topo = ToroidalTopo(scenario_config=step_config, width=width, height=height)

    demand_matrix = topo.generate_demand_matrix(num_commodities=len(arrival_rates))
    optimizer = MultiCommodityOptimizer(step_config, topo.graph, topo.interlinks)

    df = optimizer.solve_mcfp_path_formulation(
        demand_matrix,
        step_config["optimization"]["objective_func"],
        step_config["simulation"]["failure_strategy"],
    )
    z_opt = calculate_max_link_utilization(df, step_config)
    max_edge, _ = find_max_utilization_edge(df, step_config)

    return df, z_opt, max_edge, step_config


def run_controlled_dual_validation():
    config_file = os.path.join(src_dir, "data", "80_lambda_our_model_2c.yaml")
    config = load_yaml_file(config_file)

    # Ensure we use the tight formulation for this controlled experiment
    config["optimization"] = config.get("optimization", {}).copy()
    config["optimization"]["use_tight_formulation"] = True

    sequence_file = os.path.join(src_dir, "results", "arrival_rate_sequence_dual_validation.csv")
    sequence_df = pd.read_csv(sequence_file, index_col=0)
    # Note: we only use this file for the number of time steps.
    num_steps = int(sequence_df.shape[0])
    num_commodities = int(sequence_df.shape[1])

    # Change requested: commodity 3 increases over time; 0/1/2 stay fixed at step-1 values.
    varying_commodity_id = 3
    delta_per_step = 50.0  # packets/s per step (same magnitude as prior dual-validation setup)

    output_base = os.path.join(src_dir, "results", "multi_step_comparison", "dual_validation", "controlled")
    os.makedirs(output_base, exist_ok=True)

    # Step 1: solve once for prediction parameters
    step1_rates = sequence_df.iloc[0].values.tolist()
    if varying_commodity_id >= len(step1_rates):
        raise ValueError(f"varying_commodity_id={varying_commodity_id} out of range for {len(step1_rates)} commodities")

    # Build a modified sequence where only commodity 3 changes; others are fixed at step-1 values.
    modified_sequence = []
    base = float(step1_rates[varying_commodity_id])
    for t in range(num_steps):
        rates = step1_rates.copy()
        rates[varying_commodity_id] = base + delta_per_step * t
        modified_sequence.append(rates)
    step1_df, z1, step1_max_edge, step1_config = _solve_step(config, step1_rates)

    demand_duals = step1_df.attrs.get("dual_variables", {})
    capacity_duals = step1_df.attrs.get("capacity_dual_variables", {})

    lambda_k = demand_duals.get(varying_commodity_id, None)
    matched_key, mu_e = match_edge_in_capacity_duals(step1_max_edge, capacity_duals)

    if lambda_k is None:
        raise RuntimeError(f"λ_{varying_commodity_id} not found in step-1 demand duals; cannot run prediction.")
    if mu_e is None:
        # Keep mu_e=None to fall back to lambda-only prediction
        mu_e = None

    interlink_capacity = float(step1_config["system"]["interlink_capacity"])

    rows = []
    step1_dk = float(step1_rates[varying_commodity_id])

    for step_id in range(1, num_steps + 1):
        rates = modified_sequence[step_id - 1]
        dk = float(rates[varying_commodity_id])
        delta_dk = dk - step1_dk

        # Baseline: per-step optimal
        _, z_opt, max_edge_opt, _ = _solve_step(config, rates)

        # Prediction: lambda-only
        pred_lambda = z1 + lambda_k * delta_dk

        # Enhanced: lambda + mu * Δu_e (Δu computed on step-1 max edge under step-1 ratios)
        delta_flow_bits = calculate_edge_flow_change(
            step1_df,
            step1_max_edge,
            {varying_commodity_id: delta_dk},
            step1_config,
        )
        delta_util = (delta_flow_bits / interlink_capacity) * 100.0
        if mu_e is not None:
            pred_lambda_mu = z1 + lambda_k * delta_dk + mu_e * delta_util
        else:
            pred_lambda_mu = pred_lambda

        abs_err_lambda = abs(z_opt - pred_lambda)
        abs_err_lambda_mu = abs(z_opt - pred_lambda_mu)
        rel_err_lambda = (abs_err_lambda / z_opt * 100.0) if z_opt > 0 else 0.0
        rel_err_lambda_mu = (abs_err_lambda_mu / z_opt * 100.0) if z_opt > 0 else 0.0

        rows.append(
            {
                "step_id": step_id,
                "varying_commodity_id": varying_commodity_id,
                "commodity_3_demand": dk,
                "demand_change": delta_dk,
                "z_optimal": z_opt,
                "pred_lambda": pred_lambda,
                "pred_lambda_mu": pred_lambda_mu,
                "abs_err_lambda": abs_err_lambda,
                "abs_err_lambda_mu": abs_err_lambda_mu,
                "rel_err_lambda": rel_err_lambda,
                "rel_err_lambda_mu": rel_err_lambda_mu,
                "step1_max_edge": str(step1_max_edge),
                "step1_mu_edge_key": str(matched_key),
                "lambda_3": lambda_k,
                "mu_e": mu_e,
                "baseline_max_edge": str(max_edge_opt),
            }
        )

    out_df = pd.DataFrame(rows)
    out_csv = os.path.join(output_base, "controlled_dual_prediction_comparison.csv")
    out_df.to_csv(out_csv, index=False)

    print(f"✓ Controlled comparison saved: {out_csv}")


def main():
    run_controlled_dual_validation()


if __name__ == "__main__":
    main()

