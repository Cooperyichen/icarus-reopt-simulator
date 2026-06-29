# minimize_max_link_utilization 优化问题约束总结与 Step 6 分析

## 约束类型总结（split_commodities: "on"）

### 1. **容量约束 (Capacity Constraints)** - 64条
**类型**: 不等式约束 (≤)

**数学表达式**:
```
对于每条interlink (u, v):
  Σ(flow_on_path[(i, path_idx)] for all paths using (u,v)) × packet_size × 8 ≤ interlink_capacity
```

**关键参数**:
- `interlink_capacity = 10,000,000 bits/s`
- `packet_size = 1500 bytes`
- **单条interlink理论最大承载**: `833.33 packets/s`

### 2. **需求约束 (Demand Constraints)** - 4条
**类型**: 等式约束 (=)

**数学表达式**:
```
对于每个commodity i:
  Σ(flow_on_path[(i, path_idx)] for all paths) = demand_i
```

**含义**: 每个commodity的总流量必须等于其需求（不可多不可少）

**对偶变量**: 每个commodity对应一个对偶变量λ_i，表示如果demand_i增加1单位，目标函数值（最大链路利用率）的边际变化。

### 3. **非负性约束 (Non-negativity Constraints)** - ~112条
**类型**: 不等式约束 (≥)

**数学表达式**:
```
对于每条路径 (i, path_idx):
  flow_on_path[(i, path_idx)] ≥ ε  (其中 ε = 1e-7)
```

### 4. **节点容量约束 (Node Capacity Constraints)** - 0条
**状态**: 当前被注释掉，未启用

### 5. **单路径约束 (Single Path Constraints)** - 0条
**状态**: 仅当`split_commodities: "off"`时适用

---

## 约束总结表

| 约束类型 | 数量 | 类型 | 作用 | 可能导致不可行的原因 |
|---------|------|------|------|---------------------|
| **容量约束** | 64 | 不等式 (≤) | 限制每条interlink的最大流量 | 多个commodity路径共享关键interlink导致超载 |
| **需求约束** | 4 | 等式 (=) | 确保每个commodity的需求被满足 | 无法找到满足所有约束的路径组合 |
| **非负性约束** | ~112 | 不等式 (≥) | 确保流量非负 | 通常不会直接导致不可行 |
| **节点容量约束** | 0 | - | 已禁用 | - |
| **单路径约束** | 0 | - | 不适用 | - |
| **总计** | **~180** | - | - | - |

---

## Step 6 测试结果分析

### 关键发现：代码Bug导致误判

**问题**: 代码第591行只检查`problem.status == cp.OPTIMAL`，没有包含`cp.OPTIMAL_INACCURATE`。

**影响**: 
- 优化器求解器返回`optimal_inaccurate`状态（接近最优但可能数值不精确）
- 代码未正确处理，导致结果中所有流量为0
- 在多步实验中被误判为"不可行"

### 修复后的测试结果

**Step 6 Arrival Rates**: `[620.71, 731.22, 408.18, 1128.73]` packets/s

**优化结果**:
```
✓ Optimization SUCCEEDED - All demand satisfied

Commodity Flow Satisfaction:
  Commodity 0: ✓ 620.71 / 620.71 packets/s
  Commodity 1: ✓ 731.22 / 731.22 packets/s
  Commodity 2: ✓ 408.18 / 408.18 packets/s
  Commodity 3: ✓ 1128.73 / 1128.73 packets/s

Result Statistics:
  Number of paths in result: 112
  Total flow in result: 2888.84 packets/s
  Expected total: 2888.84 packets/s
  Difference: 0.00 packets/s
```

**结论**: Step 6实际上是**可行的**！之前的"不可行"判断是代码bug导致的误判。

### 为什么会出现"optimal_inaccurate"？

1. **数值精度**: 求解器ECOS_BB在达到最大迭代次数时可能返回接近最优的解
2. **收敛容差**: 在数值容差范围内被认为是可接受的解
3. **求解器行为**: ECOS_BB可能在达到迭代限制时返回最佳已知解

### 代码修复

已修复两处代码：
1. **第591行**: `if problem.status == cp.OPTIMAL:` → `if problem.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:`
2. **第668行**: 对偶变量提取时的相同问题

---

## 约束违反分析

既然Step 6实际上是可行的，那么**之前的"不可行"判断是错误的**。

可能的原因（如果真正不可行时）：
1. **容量约束违反**: 某些interlink在满足所有需求时可能超载
2. **路径分配限制**: `max_hops = 7`限制了可用路径选择
3. **需求组合问题**: 某些commodity组合可能导致路径冲突

但根据测试结果，Step 6在当前约束下是**可行的**。

---

## 对偶变量提取

每个commodity的需求约束对应一个对偶变量λ_i：

- **λ_0**: Commodity 0的对偶变量
- **λ_1**: Commodity 1的对偶变量
- **λ_2**: Commodity 2的对偶变量
- **λ_3**: Commodity 3的对偶变量

**对偶变量的含义**: 如果commodity i的需求增加1单位（packets/s），目标函数值（最大链路利用率，单位：%）会增加多少。

**提取方法**: 需要在优化器代码中访问`demand_constraints[i].dual_value`（在problem.solve()之后）。

由于对偶变量提取需要修改优化器代码结构，建议单独实现。

---

## 总结

1. **约束类型**: 主要包括容量约束（64条）、需求约束（4条）和非负性约束（~112条）

2. **Step 6状态**: 
   - 之前被误判为不可行（代码bug）
   - 修复后证实是**可行的**
   - 所有commodity需求都能被满足

3. **代码修复**: 已修复`OPTIMAL_INACCURATE`状态的处理问题

4. **对偶变量**: 需要修改优化器代码才能提取，建议单独实现

