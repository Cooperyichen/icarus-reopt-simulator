#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Visualize controlled dual-validation experiment (optimal vs predictions).

Reads:
  src/results/multi_step_comparison/dual_validation/controlled/controlled_dual_prediction_comparison.csv

Writes figures to:
  src/results/可视化结果展示/对偶变量验证/
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..")
sys.path.insert(0, src_dir)


def visualize_controlled_dual_validation():
    result_dir = os.path.join(
        src_dir, "results", "multi_step_comparison", "dual_validation", "controlled"
    )
    csv_file = os.path.join(result_dir, "controlled_dual_prediction_comparison.csv")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Missing comparison csv: {csv_file}")

    df = pd.read_csv(csv_file)

    out_dir = os.path.join(src_dir, "results", "可视化结果展示", "对偶变量验证")
    os.makedirs(out_dir, exist_ok=True)

    # 1) Optimal vs predictions (line)
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(
        df["step_id"],
        df["z_optimal"],
        marker="o",
        linewidth=2.5,
        label="Optimal (re-optimized)",
        color="#1f77b4",
        zorder=3,
    )
    ax.plot(
        df["step_id"],
        df["pred_lambda"],
        marker="s",
        linewidth=2.5,
        linestyle="--",
        label="Predicted (λ-only)",
        color="#ff7f0e",
        zorder=4,
    )
    ax.plot(
        df["step_id"],
        df["pred_lambda_mu"],
        marker="^",
        linewidth=2.5,
        linestyle="--",
        label="Predicted (λ+μ)",
        color="#2ca02c",
        zorder=5,
        markerfacecolor="none",
    )
    ax.set_xlabel("Time Step", fontweight="bold")
    ax.set_ylabel("Max Link Utilization (%)", fontweight="bold")
    ax.set_title("Optimal vs Predicted Max Link Utilization (Controlled Experiment)", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_xticks(df["step_id"])
    ax.legend(loc="best")

    # Add a zoomed inset so small differences are visually distinguishable
    # Focus on steps 2..10 where predictions differ
    x1, x2 = 2, int(df["step_id"].max())
    mask = (df["step_id"] >= x1) & (df["step_id"] <= x2)
    ymin = float(
        min(
            df.loc[mask, "z_optimal"].min(),
            df.loc[mask, "pred_lambda"].min(),
            df.loc[mask, "pred_lambda_mu"].min(),
        )
    )
    ymax = float(
        max(
            df.loc[mask, "z_optimal"].max(),
            df.loc[mask, "pred_lambda"].max(),
            df.loc[mask, "pred_lambda_mu"].max(),
        )
    )
    # Tight margin around the zoom region
    margin = max(0.05, 0.02 * (ymax - ymin))

    axins = inset_axes(ax, width="38%", height="45%", loc="lower right", borderpad=1.2)
    axins.plot(df["step_id"], df["z_optimal"], marker="o", linewidth=2.0, color="#1f77b4", zorder=3)
    axins.plot(df["step_id"], df["pred_lambda"], marker="s", linewidth=2.0, linestyle="--", color="#ff7f0e", zorder=4)
    axins.plot(df["step_id"], df["pred_lambda_mu"], marker="^", linewidth=2.0, linestyle="--", color="#2ca02c", zorder=5, markerfacecolor="none")
    axins.set_xlim(x1 - 0.2, x2 + 0.2)
    axins.set_ylim(ymin - margin, ymax + margin)
    axins.grid(True, alpha=0.25)
    axins.set_xticks([2, 4, 6, 8, 10] if x2 >= 10 else sorted(df["step_id"].unique().tolist()))
    axins.tick_params(labelsize=9)
    mark_inset(ax, axins, loc1=2, loc2=4, fc="none", ec="0.4", lw=1.0)

    plt.tight_layout()
    out1 = os.path.join(out_dir, "dual_prediction_controlled_comparison.png")
    plt.savefig(out1, dpi=300, bbox_inches="tight")
    plt.close()

    # 2) Absolute error comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        df["step_id"],
        df["abs_err_lambda"],
        marker="o",
        linewidth=2.5,
        label="|err| (λ-only)",
        color="#1f77b4",
        zorder=4,
    )
    ax.plot(
        df["step_id"],
        df["abs_err_lambda_mu"],
        marker="s",
        linewidth=2.5,
        label="|err| (λ+μ)",
        color="#ff7f0e",
        zorder=5,
        markerfacecolor="none",
    )
    ax.set_xlabel("Time Step", fontweight="bold")
    ax.set_ylabel("Absolute Error (%)", fontweight="bold")
    ax.set_title("Prediction Absolute Error (Controlled Experiment)", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_xticks(df["step_id"])
    ax.legend(loc="best")
    plt.tight_layout()
    out2 = os.path.join(out_dir, "dual_prediction_controlled_abs_error.png")
    plt.savefig(out2, dpi=300, bbox_inches="tight")
    plt.close()

    # 3) Relative error comparison
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(
        df["step_id"],
        df["rel_err_lambda"],
        marker="o",
        linewidth=2.5,
        label="rel err (λ-only)",
        color="#1f77b4",
        zorder=4,
    )
    ax.plot(
        df["step_id"],
        df["rel_err_lambda_mu"],
        marker="s",
        linewidth=2.5,
        label="rel err (λ+μ)",
        color="#ff7f0e",
        zorder=5,
        markerfacecolor="none",
    )
    ax.set_xlabel("Time Step", fontweight="bold")
    ax.set_ylabel("Relative Error (%)", fontweight="bold")
    ax.set_title("Prediction Relative Error (Controlled Experiment)", fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.set_xticks(df["step_id"])
    ax.legend(loc="best")
    plt.tight_layout()
    out3 = os.path.join(out_dir, "dual_prediction_controlled_rel_error.png")
    plt.savefig(out3, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"✓ Saved: {out1}")
    print(f"✓ Saved: {out2}")
    print(f"✓ Saved: {out3}")


def main():
    visualize_controlled_dual_validation()


if __name__ == "__main__":
    main()

