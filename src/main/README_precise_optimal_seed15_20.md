# Seed 15 和 Seed 20 精确最优解保证

## 审计结果（修改前）

使用 `PRECISE_SOLVER_OPTIONS` (eps_abs=1e-8, eps_rel=1e-8) 时：

| Seed | OPTIMAL | OPTIMAL_INACCURATE |
|------|---------|-------------------|
| 15   | 48      | 2 (step 12, 25)   |
| 20   | 49      | 1 (step 10)       |

高负载步（max_util ≈ 99%）易触发 OPTIMAL_INACCURATE。

## 已做修改

1. **optimizer** (`muti_commodity_optimizer.py`)
   - 添加 `df.attrs['solver_status']` 记录每步的求解器状态
   - 支持 `require_optimal_strict=True`：当得到 OPTIMAL_INACCURATE 时，自动用 ECOS (abstol=1e-9, reltol=1e-9) 重试

2. **run_all_20seeds_precise.py**
   - 新增 `--strict-optimal` 参数
   - 使用 `STRICT_OPTIMAL_OPTIONS` 时启用 `require_optimal_strict`

## 使用方式

```bash
# 对 seed 15 和 20 使用严格最优模式重跑
python -m main.run_all_20seeds_precise --seeds 15,20 --strict-optimal

# 完成后更新 gap/regret 和可视化
python -m main.compute_gap_regret_interevent_20seeds

# 审计 solver 状态（使用 STRICT_OPTIMAL 后应全为 optimal）
python -m main.audit_solver_status_seed15_20
```

## 验证

运行 `audit_solver_status_seed15_20` 后，若汇总显示 `OPTIMAL_INACCURATE=0`，则 seed 15 和 20 的输出均为精确最优解。
