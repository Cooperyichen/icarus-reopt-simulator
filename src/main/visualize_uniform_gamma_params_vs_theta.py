#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plot gamma parameters vs theta for uniform long congested sequence and compare baseline."""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

OUTPUT_DIR = os.path.join(src_dir, 'results', '可视化结果展示', 'uniform long congested sequence')
BASELINE_DIR = os.path.join(src_dir, 'results', '可视化结果展示', 'long congested sequence')


def linear_fit(x, y):
    coef = np.polyfit(x, y, 1)
    p = np.poly1d(coef)
    den = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - np.sum((y - p(x)) ** 2) / den if den > 0 else np.nan
    return coef, p, r2


def main():
    fit_csv = os.path.join(OUTPUT_DIR, 'inter_event_envelope_fit_evaluation.csv')
    if not os.path.isfile(fit_csv):
        raise FileNotFoundError(f'File not found: {fit_csv}')

    df = pd.read_csv(fit_csv)
    gamma_df = df[df['dist'] == 'gamma'].copy().sort_values('theta').reset_index(drop=True)

    theta = gamma_df['theta'].values
    shape = gamma_df['shape'].values
    scale = gamma_df['scale'].values
    mean_val = shape * scale

    coef_shape, p_shape, r2_shape = linear_fit(theta, shape)
    coef_scale, p_scale, r2_scale = linear_fit(theta, scale)
    coef_mean, p_mean, r2_mean = linear_fit(theta, mean_val)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    theta_smooth = np.linspace(theta.min(), theta.max(), 100)

    axes[0].scatter(theta, shape, s=80, c='#2E86AB', edgecolors='black', linewidths=1.2, zorder=3)
    axes[0].plot(theta_smooth, p_shape(theta_smooth), '--', color='#E94F37', linewidth=2,
                 label=f'Linear fit: shape = {coef_shape[0]:.3f}θ + {coef_shape[1]:.3f}\nR² = {r2_shape:.4f}')
    axes[0].set_xlabel('θ (threshold)')
    axes[0].set_ylabel('Gamma shape (k)')
    axes[0].set_title('Shape vs θ')
    axes[0].legend(loc='lower right', fontsize=9)
    axes[0].grid(True, alpha=0.3)
    axes[0].set_xticks(theta)

    axes[1].scatter(theta, scale, s=80, c='#A23B72', edgecolors='black', linewidths=1.2, zorder=3)
    axes[1].plot(theta_smooth, p_scale(theta_smooth), '--', color='#E94F37', linewidth=2,
                 label=f'Linear fit: scale = {coef_scale[0]:.3f}θ + {coef_scale[1]:.3f}\nR² = {r2_scale:.4f}')
    axes[1].set_xlabel('θ (threshold)')
    axes[1].set_ylabel('Gamma scale (θ_g)')
    axes[1].set_title('Scale vs θ')
    axes[1].legend(loc='lower right', fontsize=9)
    axes[1].grid(True, alpha=0.3)
    axes[1].set_xticks(theta)

    axes[2].scatter(theta, mean_val, s=80, c='#44AF69', edgecolors='black', linewidths=1.2, zorder=3)
    axes[2].plot(theta_smooth, p_mean(theta_smooth), '--', color='#E94F37', linewidth=2,
                 label=f'Linear fit: E[Δt] = {coef_mean[0]:.3f}θ + {coef_mean[1]:.3f}\nR² = {r2_mean:.4f}')
    axes[2].set_xlabel('θ (threshold)')
    axes[2].set_ylabel('E[Δt] = shape × scale')
    axes[2].set_title('Inter-event Mean vs θ')
    axes[2].legend(loc='lower right', fontsize=9)
    axes[2].grid(True, alpha=0.3)
    axes[2].set_xticks(theta)

    plt.suptitle('Gamma Parameters vs θ (Uniform Long Congested, Strategy 4)', fontsize=14, y=1.02)
    plt.tight_layout()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, 'gamma_params_vs_theta.png')
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Saved: {out_path}')

    print('\n--- Uniform linear fit results ---')
    print(f'shape(θ) ≈ {coef_shape[0]:.4f} × θ + {coef_shape[1]:.4f}  (R² = {r2_shape:.4f})')
    print(f'scale(θ) ≈ {coef_scale[0]:.4f} × θ + {coef_scale[1]:.4f}  (R² = {r2_scale:.4f})')
    print(f'E[Δt](θ) ≈ {coef_mean[0]:.4f} × θ + {coef_mean[1]:.4f}  (R² = {r2_mean:.4f})')

    baseline_csv = os.path.join(BASELINE_DIR, 'inter_event_envelope_fit_evaluation.csv')
    if os.path.isfile(baseline_csv):
        bdf = pd.read_csv(baseline_csv)
        bg = bdf[bdf['dist'] == 'gamma'].copy().sort_values('theta')
        if len(bg) >= 2:
            btheta = bg['theta'].values
            bshape = bg['shape'].values
            bscale = bg['scale'].values
            bmean = bshape * bscale
            bcoef_shape, _, br2_shape = linear_fit(btheta, bshape)
            bcoef_scale, _, br2_scale = linear_fit(btheta, bscale)
            bcoef_mean, _, br2_mean = linear_fit(btheta, bmean)

            cmp_path = os.path.join(OUTPUT_DIR, 'gamma_params_vs_theta_comparison.csv')
            cmp_df = pd.DataFrame([
                {'metric': 'shape', 'uniform_slope': coef_shape[0], 'uniform_intercept': coef_shape[1], 'uniform_r2': r2_shape,
                 'baseline_slope': bcoef_shape[0], 'baseline_intercept': bcoef_shape[1], 'baseline_r2': br2_shape,
                 'slope_diff_abs': abs(coef_shape[0] - bcoef_shape[0])},
                {'metric': 'scale', 'uniform_slope': coef_scale[0], 'uniform_intercept': coef_scale[1], 'uniform_r2': r2_scale,
                 'baseline_slope': bcoef_scale[0], 'baseline_intercept': bcoef_scale[1], 'baseline_r2': br2_scale,
                 'slope_diff_abs': abs(coef_scale[0] - bcoef_scale[0])},
                {'metric': 'mean', 'uniform_slope': coef_mean[0], 'uniform_intercept': coef_mean[1], 'uniform_r2': r2_mean,
                 'baseline_slope': bcoef_mean[0], 'baseline_intercept': bcoef_mean[1], 'baseline_r2': br2_mean,
                 'slope_diff_abs': abs(coef_mean[0] - bcoef_mean[0])},
            ])
            cmp_df.to_csv(cmp_path, index=False)
            print(f'✓ comparison saved: {cmp_path}')
            print(cmp_df.to_string(index=False))


if __name__ == '__main__':
    main()
