#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为 long congested sequence 的 Strategy 4 结果生成 Figure 1：Inter-Event Time CDF。

读取各 seed 的 strategy4_stats.csv，计算相邻重优化步之间的步数 Δt，
合并所有 seed 的 Δt 绘制经验 CDF，保存到 可视化结果展示/long congested sequence/。
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats

script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..')
sys.path.insert(0, src_dir)

SEEDS = [7, 42, 123, 1234]  # 可由 feasible_long_congested_seeds_20.csv 覆盖
SEQUENCE_DIR_NAME = 'long congested sequence'

# θ=8 存在 strategy4/，其余在 strategy4_threshold_{t}/strategy4/
THRESHOLDS_FOR_HIST = [4, 6, 8, 10, 12]


def _is_reoptimized(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'yes')
    return bool(value)


def load_strategy4_stats(results_base_dir):
    """加载所有存在的 strategy4_stats.csv（θ=8，路径 strategy4/），返回 {seed: DataFrame}。跳过缺失的 seed。"""
    long_congested_base = os.path.join(results_base_dir, SEQUENCE_DIR_NAME)
    out = {}
    for seed in SEEDS:
        path = os.path.join(long_congested_base, str(seed), 'strategy4', 'strategy4_stats.csv')
        if os.path.isfile(path):
            out[seed] = pd.read_csv(path)
    if not out:
        raise FileNotFoundError(
            f"未找到任何 strategy4_stats.csv，请先运行 main.run_strategy4_long_congested"
        )
    return out


def load_strategy4_stats_for_threshold(results_base_dir, threshold):
    """加载指定阈值 θ 的 strategy4_stats。θ=8 用 strategy4/，θ=6/10 用 strategy4_threshold_{t}/strategy4/。"""
    long_congested_base = os.path.join(results_base_dir, SEQUENCE_DIR_NAME)
    out = {}
    for seed in SEEDS:
        if threshold == 8:
            path = os.path.join(long_congested_base, str(seed), 'strategy4', 'strategy4_stats.csv')
        else:
            path = os.path.join(
                long_congested_base, str(seed), f'strategy4_threshold_{threshold}', 'strategy4',
                'strategy4_stats.csv'
            )
        if os.path.isfile(path):
            out[seed] = pd.read_csv(path)
    return out


def compute_inter_event_times(reoptimized_steps):
    """
    由重优化步号列表计算相邻事件间隔步数 Δt。
    reoptimized_steps 已排序，如 [1, 6, 12, 25] -> Δt = [5, 6, 13]
    """
    if len(reoptimized_steps) < 2:
        return []
    return [reoptimized_steps[i + 1] - reoptimized_steps[i] for i in range(len(reoptimized_steps) - 1)]


def collect_all_delta_ts(stats_by_seed):
    """从各 seed 的 stats 中收集所有 Δt 及每 seed 的统计，用于 CDF 和 summary."""
    all_delta_ts = []
    summary_rows = []

    for seed, df in stats_by_seed.items():
        reopt = df['reoptimized'].apply(_is_reoptimized)
        reoptimized_steps = sorted(df.loc[reopt, 'step_id'].astype(int).tolist())
        delta_ts = compute_inter_event_times(reoptimized_steps)
        all_delta_ts.extend(delta_ts)

        reopt_count = len(reoptimized_steps)
        mean_dt = np.mean(delta_ts) if delta_ts else np.nan
        summary_rows.append({
            'seed': seed,
            'reopt_count': reopt_count,
            'num_inter_events': len(delta_ts),
            'mean_dt': mean_dt,
            'min_dt': min(delta_ts) if delta_ts else np.nan,
            'max_dt': max(delta_ts) if delta_ts else np.nan,
        })

    return np.array(all_delta_ts), pd.DataFrame(summary_rows)


def plot_inter_event_cdf(delta_ts, output_file):
    """绘制 inter-event time 的经验 CDF（Figure 1）。"""
    if len(delta_ts) == 0:
        raise ValueError("没有 Δt 数据，无法绘制 CDF")

    sorted_ts = np.sort(delta_ts)
    n = len(sorted_ts)
    cdf = np.arange(1, n + 1, dtype=float) / n

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.step(sorted_ts, cdf, where='post', color='#2ca02c', linewidth=2)
    ax.set_xlabel('Inter-event time Δt (steps)', fontsize=12)
    ax.set_ylabel('CDF', fontsize=12)
    ax.set_title('Inter-Event Time CDF (Long Congested Sequence, Strategy 4 θ=8)', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(left=0)
    ax.set_ylim(0, 1.02)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"✓ CDF 图已保存: {output_file}")


def collect_delta_ts_from_stats(stats_by_seed):
    """从 stats_by_seed 收集所有 Δt，返回一维数组。"""
    all_delta_ts = []
    for seed, df in stats_by_seed.items():
        reopt = df['reoptimized'].apply(_is_reoptimized)
        reoptimized_steps = sorted(df.loc[reopt, 'step_id'].astype(int).tolist())
        delta_ts = compute_inter_event_times(reoptimized_steps)
        all_delta_ts.extend(delta_ts)
    return np.array(all_delta_ts) if all_delta_ts else np.array([])


def plot_inter_event_histogram(delta_ts, output_file):
    """
    绘制 inter-event time 的柱状图。
    量程：1 到 max(Δt)+1；组距为 1 步（整数步数）。
    """
    if len(delta_ts) == 0:
        raise ValueError("没有 Δt 数据，无法绘制柱状图")

    delta_ts = np.asarray(delta_ts, dtype=float)
    x_min, x_max = 1, int(np.max(delta_ts)) + 1
    # 组距 1：左闭右开区间 [1,2), [2,3), ..., [x_max-1, x_max]
    bin_edges = np.arange(x_min, x_max + 1, dtype=float)

    fig, ax = plt.subplots(figsize=(8, 5))
    counts, _, patches = ax.hist(
        delta_ts,
        bins=bin_edges,
        align='left',
        rwidth=0.75,
        color='#2ca02c',
        edgecolor='#1a5f1a',
        linewidth=1.2,
    )
    ax.set_xlabel('Inter-event time Δt (steps)', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('Inter-Event Time Histogram (Long Congested Sequence, Strategy 4 θ=8)', fontsize=14)
    ax.set_xlim(x_min - 0.5, x_max)
    ax.set_ylim(0, max(counts) * 1.15 if counts.size else 1)
    ax.set_xticks(np.arange(x_min, x_max, dtype=int))
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"✓ 柱状图已保存: {output_file}")


def plot_inter_event_histogram_multi_theta(delta_ts_by_theta, output_file):
    """
    在同一幅图中绘制 θ=6, 8, 10 的 inter-event time 柱状图（组距 1，统一量程）。
    delta_ts_by_theta: dict, key 为 theta (6/8/10)，value 为 Δt 数组（可为空）。
    """
    thetas = sorted([t for t in THRESHOLDS_FOR_HIST if t in delta_ts_by_theta])
    if not thetas:
        raise ValueError("没有可用的 θ 数据，无法绘制多阈值柱状图")

    all_ts = np.concatenate([np.asarray(delta_ts_by_theta[t], dtype=float) for t in thetas])
    x_min = 1
    x_max = int(np.max(all_ts)) + 1 if len(all_ts) > 0 else 22
    bin_edges = np.arange(x_min, x_max + 1, dtype=float)
    bin_centers = np.arange(x_min, x_max, dtype=float)
    n_theta = len(thetas)
    width = 0.26  # 每组内柱宽
    # 颜色固定：θ=6 蓝、θ=8 绿、θ=10 橙
    color_map = {6: '#1f77b4', 8: '#2ca02c', 10: '#ff7f0e'}

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, theta in enumerate(thetas):
        ts = np.asarray(delta_ts_by_theta[theta], dtype=float)
        counts, _ = np.histogram(ts, bins=bin_edges)
        offset = (i - (n_theta - 1) / 2) * width
        ax.bar(
            bin_centers + offset,
            counts,
            width=width,
            label=f'θ={theta}',
            color=color_map.get(theta, '#888'),
            edgecolor='#333',
            linewidth=0.8,
        )

    ax.set_xlabel('Inter-event time Δt (steps)', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('Inter-Event Time Histogram (Long Congested Sequence, Strategy 4)', fontsize=14)
    ax.set_xticks(bin_centers.astype(int))
    ax.set_xlim(x_min - 0.6, x_max - 0.4)
    y_max = max(np.histogram(all_ts, bins=bin_edges)[0]) * 1.2 if len(all_ts) else 1
    ax.set_ylim(0, max(y_max, 1))
    ax.legend(loc='upper right', fontsize=11)
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"✓ 多阈值柱状图已保存: {output_file}")


def _discretized_pmf(k_vals, dist, *args, **kwargs):
    """连续分布离散化：P(Δt=k) = F(k+0.5) - F(k-0.5)，k>=1。"""
    pmf = np.zeros_like(k_vals, dtype=float)
    for i, k in enumerate(k_vals):
        if k >= 0.5:
            pmf[i] = max(0, dist.cdf(k + 0.5, *args, **kwargs) - dist.cdf(k - 0.5, *args, **kwargs))
    s = pmf.sum()
    if s > 0:
        pmf /= s
    return pmf


def _fit_and_evaluate(delta_ts, k_range, dist_name='gamma'):
    """
    拟合分布并计算拟合曲线与评估指标。
    返回 (expected_counts, params, rmse, mae)。
    """
    ts = np.asarray(delta_ts, dtype=float)
    n = len(ts)
    if n < 3:
        return None, None, np.nan, np.nan

    # 经验直方图：bins [0.5,1.5), [1.5,2.5), ... 对应 k=1,2,...
    bins_emp = np.concatenate([[0.5], k_range.astype(float) + 0.5])
    emp_hist, _ = np.histogram(ts, bins=bins_emp)
    if len(emp_hist) < len(k_range):
        emp_hist = np.pad(emp_hist, (0, len(k_range) - len(emp_hist)))

    try:
        if dist_name == 'gamma':
            a, loc, scale = scipy_stats.gamma.fit(ts, floc=0)
            pmf = _discretized_pmf(k_range, scipy_stats.gamma, a, loc=loc, scale=scale)
            params = {'shape': a, 'scale': scale}
        else:
            c, loc, scale = scipy_stats.weibull_min.fit(ts, floc=0)
            pmf = _discretized_pmf(k_range, scipy_stats.weibull_min, c, loc=loc, scale=scale)
            params = {'shape': c, 'scale': scale}
    except Exception:
        return None, None, np.nan, np.nan

    expected = pmf * n
    emp_hist = emp_hist[:len(expected)]
    diff = expected - emp_hist
    rmse = np.sqrt(np.mean(diff ** 2))
    mae = np.mean(np.abs(diff))
    return expected, params, rmse, mae


def plot_inter_event_histogram_multi_theta_with_envelope(delta_ts_by_theta, output_file, output_fit_csv, title=None):
    """
    绘制 θ=6, 8, 10 的 inter-event time 柱状图，叠加 Gamma 与 Weibull 拟合包络曲线，
    并评估拟合效果。
    title: 可选，图标题；默认 "Long Congested Sequence"。
    """
    thetas = sorted([t for t in THRESHOLDS_FOR_HIST if t in delta_ts_by_theta])
    if not thetas:
        raise ValueError("没有可用的 θ 数据，无法绘制多阈值柱状图")

    all_ts = np.concatenate([np.asarray(delta_ts_by_theta[t], dtype=float) for t in thetas])
    x_min = 1
    x_max = max(int(np.max(all_ts)) + 1, 25) if len(all_ts) > 0 else 25
    k_range = np.arange(x_min, x_max, dtype=float)
    bin_edges = np.arange(x_min, x_max + 1, dtype=float)
    bin_centers = np.arange(x_min, x_max, dtype=float)
    n_theta = len(thetas)
    width = 0.18 if n_theta > 3 else 0.22
    color_map = {4: '#9467bd', 6: '#1f77b4', 8: '#2ca02c', 10: '#ff7f0e', 12: '#d62728'}
    fit_rows = []
    added_gamma_leg = False
    added_weibull_leg = False
    max_y_data = 1.0  # max over per-θ bar heights and fit curves (not pooled histogram)

    fig, ax = plt.subplots(figsize=(11, 6))
    for i, theta in enumerate(thetas):
        ts = np.asarray(delta_ts_by_theta[theta], dtype=float)
        counts, _ = np.histogram(ts, bins=bin_edges)
        if len(counts):
            max_y_data = max(max_y_data, float(np.max(counts)))
        offset = (i - (n_theta - 1) / 2) * width
        ax.bar(
            bin_centers + offset,
            counts,
            width=width,
            label=f'θ={theta}',
            color=color_map.get(theta, '#888'),
            edgecolor='#333',
            linewidth=0.8,
            alpha=0.8,
        )

        # Gamma 拟合
        exp_g, params_g, rmse_g, mae_g = _fit_and_evaluate(ts, k_range, 'gamma')
        if exp_g is not None:
            max_y_data = max(max_y_data, float(np.nanmax(exp_g)))
            ax.plot(k_range, exp_g, color=color_map.get(theta, '#888'), linestyle='-',
                    linewidth=2, alpha=0.9, zorder=1)
            if not added_gamma_leg:
                ax.plot([], [], color='gray', linestyle='-', linewidth=2, label='Gamma fit')
                added_gamma_leg = True
            fit_rows.append({
                'theta': theta, 'dist': 'gamma', 'shape': params_g.get('shape', np.nan),
                'scale': params_g.get('scale', np.nan), 'rmse': rmse_g, 'mae': mae_g, 'n': len(ts)
            })

        # Weibull 拟合
        exp_w, params_w, rmse_w, mae_w = _fit_and_evaluate(ts, k_range, 'weibull')
        if exp_w is not None:
            max_y_data = max(max_y_data, float(np.nanmax(exp_w)))
            ax.plot(k_range, exp_w, color=color_map.get(theta, '#888'), linestyle='--',
                    linewidth=1.5, alpha=0.9, zorder=1)
            if not added_weibull_leg:
                ax.plot([], [], color='gray', linestyle='--', linewidth=2, label='Weibull fit')
                added_weibull_leg = True
            fit_rows.append({
                'theta': theta, 'dist': 'weibull', 'shape': params_w.get('shape', np.nan),
                'scale': params_w.get('scale', np.nan), 'rmse': rmse_w, 'mae': mae_w, 'n': len(ts)
            })

    ax.set_xlabel('Inter-event time Δt (steps)', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    if title:
        ax.set_title(title, fontsize=14)
    ax.set_xticks(bin_centers.astype(int))
    ax.set_xlim(x_min - 0.6, x_max - 0.4)
    # y 轴：按分组柱与包络线的实际最大值 + 小边距（避免用合并样本直方图导致纵轴过高）
    y_top = max_y_data * 1.08
    ax.set_ylim(0, max(y_top, 1.0))
    ax.legend(loc='upper right', fontsize=10, ncol=2)
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_file, dpi=150)
    plt.close()
    print(f"✓ 多阈值柱状图（含包络）已保存: {output_file}")

    if fit_rows:
        fit_df = pd.DataFrame(fit_rows)
        fit_df.to_csv(output_fit_csv, index=False)
        # 追加 Gamma vs Weibull 评估摘要
        eval_rows = []
        gamma_by_theta = {r['theta']: r for r in fit_rows if r['dist'] == 'gamma'}
        weibull_by_theta = {r['theta']: r for r in fit_rows if r['dist'] == 'weibull'}
        thetas_fit = sorted(set(gamma_by_theta.keys()) | set(weibull_by_theta.keys()))
        for t in thetas_fit:
            g, w = gamma_by_theta.get(t), weibull_by_theta.get(t)
            if g and w:
                better = 'gamma' if g['rmse'] < w['rmse'] else 'weibull'
                eval_rows.append({'theta': t, 'better_envelope': better, 'gamma_rmse': g['rmse'], 'weibull_rmse': w['rmse']})
        if eval_rows:
            eval_df = pd.DataFrame(eval_rows)
            eval_path = output_fit_csv.replace('.csv', '_gamma_vs_weibull.csv')
            eval_df.to_csv(eval_path, index=False)
            print(f"✓ Gamma vs Weibull 评估已保存: {eval_path}")
        print(f"✓ 拟合评估已保存: {output_fit_csv}")
        for r in fit_rows:
            print(f"  θ={r['theta']} {r['dist']}: shape={r['shape']:.3f}, scale={r['scale']:.3f}, RMSE={r['rmse']:.3f}, MAE={r['mae']:.3f}")

        # Gamma vs Weibull 评估
        gamma_rows = [r for r in fit_rows if r['dist'] == 'gamma']
        weibull_rows = [r for r in fit_rows if r['dist'] == 'weibull']
        gamma_by_theta = {r['theta']: r for r in gamma_rows}
        weibull_by_theta = {r['theta']: r for r in weibull_rows}
        thetas_fit = sorted(set(gamma_by_theta.keys()) | set(weibull_by_theta.keys()))
        gamma_wins = weibull_wins = 0
        print("\n--- Gamma vs Weibull 包络评估 ---")
        for t in thetas_fit:
            g, w = gamma_by_theta.get(t), weibull_by_theta.get(t)
            if g and w:
                rmse_g, mae_g = g['rmse'], g['mae']
                rmse_w, mae_w = w['rmse'], w['mae']
                better_rmse = 'Gamma' if rmse_g < rmse_w else 'Weibull'
                better_mae = 'Gamma' if mae_g < mae_w else 'Weibull'
                if rmse_g < rmse_w:
                    gamma_wins += 1
                else:
                    weibull_wins += 1
                print(f"  θ={t}: RMSE 更优={better_rmse} (Γ={rmse_g:.3f}, W={rmse_w:.3f}), MAE 更优={better_mae} (Γ={mae_g:.3f}, W={mae_w:.3f})")
        print(f"  汇总: Gamma 更优 {gamma_wins} 次, Weibull 更优 {weibull_wins} 次 (按 RMSE)")
        if gamma_wins >= weibull_wins:
            print("  → 建议: Gamma 包络整体略优")
        else:
            print("  → 建议: Weibull 包络整体略优")


def main():
    global SEEDS
    seeds_file = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME, 'feasible_long_congested_seeds_20.csv')
    if os.path.isfile(seeds_file):
        SEEDS = pd.read_csv(seeds_file)['seed'].astype(int).tolist()
    results_base_dir = os.path.join(src_dir, 'results', 'multi_step_comparison')
    output_dir = os.path.join(src_dir, 'results', '可视化结果展示', SEQUENCE_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)

    print("加载 strategy4_stats...")
    stats_by_seed = load_strategy4_stats(results_base_dir)

    print("计算 inter-event times...")
    all_delta_ts, summary_df = collect_all_delta_ts(stats_by_seed)

    if len(all_delta_ts) == 0:
        print("✗ 没有任何 Δt 数据（需至少两个重优化步），无法生成 CDF")
        return

    cdf_path = os.path.join(output_dir, 'inter_event_cdf.png')
    plot_inter_event_cdf(all_delta_ts, cdf_path)

    hist_path = os.path.join(output_dir, 'inter_event_histogram.png')
    plot_inter_event_histogram(all_delta_ts, hist_path)

    # 若存在多阈值数据，则绘制多阈值柱状图（θ=4,6,8,10,12）
    delta_ts_by_theta = {}
    for t in THRESHOLDS_FOR_HIST:
        stats_t = load_strategy4_stats_for_threshold(results_base_dir, t)
        if stats_t:
            delta_ts_by_theta[t] = collect_delta_ts_from_stats(stats_t)
    if len(delta_ts_by_theta) >= 2:
        hist_multi_path = os.path.join(output_dir, 'inter_event_histogram_multi_theta.png')
        fit_csv_path = os.path.join(output_dir, 'inter_event_envelope_fit_evaluation.csv')
        plot_inter_event_histogram_multi_theta_with_envelope(
            delta_ts_by_theta, hist_multi_path, fit_csv_path
        )
    else:
        print("提示: 未找到 θ=6 或 θ=10 数据，跳过多阈值柱状图。运行 python -m main.run_strategy4_long_congested_multiple_thresholds 可生成。")

    summary_path = os.path.join(output_dir, 'inter_event_summary.csv')
    summary_df.to_csv(summary_path, index=False)
    print(f"✓ 汇总表已保存: {summary_path}")

    print("=" * 60)
    print("Figure 1 与汇总已生成完成。")
    print(f"输出目录: {output_dir}")


if __name__ == '__main__':
    main()
