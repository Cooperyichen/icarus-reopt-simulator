#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log-log regression for inter-event cumulative regret on long congested sequences.

For each theta in {4, 6, 8, 10, 12}, we:
1) find consecutive re-optimization intervals from strategy4 stats,
2) compute interval length L = t_{k+1} - t_k,
3) compute interval cumulative regret R = sum_{s=t_k+1..t_{k+1}} (J_event - J_full),
4) fit log(R) = intercept + alpha * log(L) using OLS on points with L>0 and R>0.

Outputs:
- inter_event_regret_loglog_detail.csv
- inter_event_regret_loglog_fit_summary.csv
- inter_event_regret_loglog_fit.png (unless --no-plot)
"""

import argparse
import os
import sys
from typing import List, Dict

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "..")
sys.path.insert(0, src_dir)

SEQUENCE_DIR_NAME = "long congested sequence"
THRESHOLDS = [4, 6, 8, 10, 12]
UTIL_COL = "max_link_utilization"
RESULTS_BASE_DIR = os.path.join(src_dir, "results", "multi_step_comparison")
DEFAULT_OUTPUT_DIR = os.path.join(src_dir, "results", "可视化结果展示", SEQUENCE_DIR_NAME)


def load_feasible_seeds() -> List[int]:
    path = os.path.join(
        src_dir,
        "results",
        "可视化结果展示",
        SEQUENCE_DIR_NAME,
        "feasible_long_congested_seeds_20.csv",
    )
    if os.path.isfile(path):
        return pd.read_csv(path)["seed"].astype(int).tolist()
    return [2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 19, 20, 21, 23, 42, 123, 1234]


def get_s4_path(results_base_dir: str, seed: int, theta: int) -> str:
    if theta == 8:
        return os.path.join(
            results_base_dir,
            SEQUENCE_DIR_NAME,
            str(seed),
            "strategy4",
            "strategy4_stats.csv",
        )
    return os.path.join(
        results_base_dir,
        SEQUENCE_DIR_NAME,
        str(seed),
        f"strategy4_threshold_{theta}",
        "strategy4",
        "strategy4_stats.csv",
    )


def _is_reoptimized(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes")


def collect_interval_rows(seeds: List[int]) -> pd.DataFrame:
    rows = []
    for seed in seeds:
        s1_path = os.path.join(
            RESULTS_BASE_DIR, SEQUENCE_DIR_NAME, str(seed), "strategy1", "strategy1_stats.csv"
        )
        if not os.path.isfile(s1_path):
            continue
        s1_df = pd.read_csv(s1_path)[["step_id", UTIL_COL]].rename(columns={UTIL_COL: "j_full"})

        for theta in THRESHOLDS:
            s4_path = get_s4_path(RESULTS_BASE_DIR, seed, theta)
            if not os.path.isfile(s4_path):
                continue
            s4_df = pd.read_csv(s4_path)
            if UTIL_COL not in s4_df.columns or "step_id" not in s4_df.columns:
                continue
            if "reoptimized" not in s4_df.columns:
                continue

            s4_sub = s4_df[["step_id", UTIL_COL, "reoptimized"]].copy()
            s4_sub = s4_sub.rename(columns={UTIL_COL: "j_event"})
            s4_sub["reoptimized"] = s4_sub["reoptimized"].apply(_is_reoptimized)

            merged = s1_df.merge(s4_sub, on="step_id", how="inner").sort_values("step_id")
            if merged.empty:
                continue
            merged["inst_regret"] = merged["j_event"].astype(float) - merged["j_full"].astype(float)

            reopt_steps = merged.loc[merged["reoptimized"], "step_id"].astype(int).tolist()
            if len(reopt_steps) < 2:
                continue

            for idx in range(len(reopt_steps) - 1):
                t0 = reopt_steps[idx]
                t1 = reopt_steps[idx + 1]
                L = int(t1 - t0)
                if L <= 0:
                    continue
                seg = merged[(merged["step_id"] > t0) & (merged["step_id"] <= t1)]
                if seg.empty:
                    continue
                R = float(seg["inst_regret"].sum())
                rows.append(
                    {
                        "seed": int(seed),
                        "theta": int(theta),
                        "segment_idx": int(idx + 1),
                        "t_start": int(t0),
                        "t_end": int(t1),
                        "L": L,
                        "R": R,
                    }
                )
    return pd.DataFrame(rows)


def fit_loglog(df_detail: pd.DataFrame) -> pd.DataFrame:
    summaries: List[Dict] = []
    for theta in THRESHOLDS:
        sub_all = df_detail[df_detail["theta"] == theta].copy()
        sub_valid = sub_all[(sub_all["L"] > 0) & (sub_all["R"] > 0)].copy()
        n_all = len(sub_all)
        n_used = len(sub_valid)
        n_dropped_nonpositive_r = int((sub_all["R"] <= 0).sum()) if n_all > 0 else 0

        if n_used >= 2:
            x = np.log(sub_valid["L"].values.astype(float))
            y = np.log(sub_valid["R"].values.astype(float))
            alpha, intercept = np.polyfit(x, y, 1)
            y_hat = alpha * x + intercept
            denom = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1.0 - (np.sum((y - y_hat) ** 2) / denom if denom > 0 else 0.0)
        else:
            alpha = np.nan
            intercept = np.nan
            r_squared = np.nan

        summaries.append(
            {
                "theta": int(theta),
                "n_segments_total": int(n_all),
                "n_segments_used": int(n_used),
                "n_dropped_nonpositive_r": int(n_dropped_nonpositive_r),
                "alpha": float(alpha) if np.isfinite(alpha) else np.nan,
                "intercept": float(intercept) if np.isfinite(intercept) else np.nan,
                "r_squared": float(r_squared) if np.isfinite(r_squared) else np.nan,
            }
        )
    return pd.DataFrame(summaries)


def plot_loglog(df_detail: pd.DataFrame, df_summary: pd.DataFrame, out_path: str) -> None:
    # 上三下二：上行 3 等宽；下行 2 个在 6 列网格中居中
    fig = plt.figure(figsize=(14, 8))
    gs = gridspec.GridSpec(2, 6, figure=fig, hspace=0.42, wspace=0.38)
    placements = [
        (0, slice(0, 2)),
        (0, slice(2, 4)),
        (0, slice(4, 6)),
        (1, slice(1, 3)),
        (1, slice(3, 5)),
    ]

    for (row, col_slice), theta in zip(placements, THRESHOLDS):
        ax = fig.add_subplot(gs[row, col_slice])
        sub = df_detail[(df_detail["theta"] == theta) & (df_detail["L"] > 0) & (df_detail["R"] > 0)].copy()
        if sub.empty:
            ax.set_title(f"theta={theta} (no valid data)")
            ax.grid(True, alpha=0.3)
            continue

        x = np.log(sub["L"].values.astype(float))
        y = np.log(sub["R"].values.astype(float))
        ax.scatter(x, y, s=28, alpha=0.8, color="#1f77b4", edgecolors="none")

        row = df_summary[df_summary["theta"] == theta].iloc[0]
        alpha = row["alpha"]
        intercept = row["intercept"]
        r2 = row["r_squared"]
        if np.isfinite(alpha) and np.isfinite(intercept):
            x_line = np.linspace(np.min(x), np.max(x), 100)
            y_line = alpha * x_line + intercept
            ax.plot(
                x_line,
                y_line,
                "--",
                color="#d62728",
                linewidth=2,
                label=f"alpha={alpha:.3f}, R²={r2:.3f}",
            )
            ax.legend(loc="best", fontsize=9)

        ax.set_title(f"theta={theta}")
        ax.set_xlabel("log(L)")
        ax.set_ylabel("log(R)")
        ax.grid(True, alpha=0.3)

    fig.subplots_adjust(left=0.06, right=0.98, top=0.93, bottom=0.10, hspace=0.38, wspace=0.35)
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Log-log regression for inter-event cumulative regret")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--no-plot", action="store_true", help="Skip PNG generation")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    seeds = load_feasible_seeds()
    print(f"Using {len(seeds)} feasible seeds.")

    df_detail = collect_interval_rows(seeds)
    if df_detail.empty:
        print("No interval rows collected. Check strategy1/strategy4 stats availability.")
        return

    detail_path = os.path.join(args.output_dir, "inter_event_regret_loglog_detail.csv")
    df_detail.to_csv(detail_path, index=False)
    print(f"Saved detail: {detail_path} ({len(df_detail)} rows)")

    df_summary = fit_loglog(df_detail)
    summary_path = os.path.join(args.output_dir, "inter_event_regret_loglog_fit_summary.csv")
    df_summary.to_csv(summary_path, index=False)
    print(f"Saved summary: {summary_path}")
    print("\nPer-theta log-log fit results:")
    print(df_summary.to_string(index=False))

    if not args.no_plot:
        plot_path = os.path.join(args.output_dir, "inter_event_regret_loglog_fit.png")
        plot_loglog(df_detail, df_summary, plot_path)
        print(f"Saved plot: {plot_path}")


if __name__ == "__main__":
    main()
