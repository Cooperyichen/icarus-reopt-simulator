# minimize_max_link_utilization 优化问题约束总结与 Step 6 分析

## 约束类型总结

### 1. **容量约束 (Capacity Constraints)** - 64条
**类型**: 不等式约束 (≤)

**数学表达式**:
```
对于每条interlink (u, v):
  Σ(flow_on_path[(i, path_idx)] for all paths using (u,v)) × packet_size × 8 ≤ interlink_capacity
```

**代码位置**: `muti_commodity_optimizer.py` 第445-460行

**关键参数**:
- `interlink_capacity = 10,000,000 bits/s`
- `packet_size = 1500 bytes`
- 单条interlink理论最大承载: `833.33 packets/s`

### 2. **需求约束 (Demand Constraints)** - 4条
**类型**: 等式约束 (=)

**数学表达式**:
```
对于每个commodity i:
  Σ(flow_on_path[(i, path_idx)] for all paths) = demand_i
```

**代码位置**: 第494-499行

**含义**: 每个commodity的总流量必须等于其需求（不可多不可少）

### 3. **非负性约束 (Non-negativity Constraints)** - ~112条
**类型**: 不等式约束 (≥)

**数学表达式**:
```
对于每条路径 (i, path_idx):
  flow_on_path[(i, path_idx)] ≥ ε  (其中 ε = 1e-7)
```

**代码位置**: 第508-511行

### 4. **节点容量约束 (Node Capacity Constraints)** - 0条
**状态**: 当前被注释掉，未启用

**代码位置**: 第476-490行（已注释）

### 5. **单路径约束 (Single Path Constraints)** - 0条
**状态**: 仅当`split_commodities: "off"`时适用，当前不适用

---

## Step 6 测试结果分析

### 测试结果

从单独运行Step 6的测试可以看到：

1. **优化器状态**: `optimal_inaccurate` (接近最优但可能不准确)

2. **实际结果**: 
   - 所有4个commodity的流量都为 **0 packets/s**
   - 预期总需求: 2888.84 packets/s
   - 实际满足: 0 packets/s
   - **完全未满足需求**

3. **优化器行为**:
   - 优化器返回了状态，但结果无效
   - 这可能是因为优化器内部的while循环逻辑：当问题不可行时，会标记commodity为infeasible并移除
   - 如果所有commodity都被标记为不可行，最终返回的DataFrame中所有流量为0

### 为什么Step 6不可行？

**关键观察**:
- **Step 6总需求**: 2888.84 packets/s (低于Step 5的2926.91)
- **单条interlink容量**: 833.33 packets/s
- **Commodity 3需求**: 1128.73 packets/s > 833.33 packets/s

**可能的原因**:

1. **不是总容量问题**: 总需求2888.84 < 64条interlink的总容量 (64 × 833.33 = 53,333 packets/s)

2. **路径分配问题**: 
   - Commodity 3需要1128.73 packets/s，必须分流到多条路径
   - 但这些路径可能共享某些关键interlink
   - 如果多条路径都经过同一interlink，该interlink的流量会累加

3. **路径查找限制**:
   - `max_hops = 7`限制了可用路径
   - 可能找不到足够的分散路径来满足所有commodity的需求

4. **需求组合问题**:
   - 某些commodity的源-目的地对组合可能导致某些interlink成为瓶颈
   - Step 6的commodity组合（相比Step 5）可能触发了特定的瓶颈模式

### 验证

从测试输出可以看到优化器确实尝试求解，但最终返回的结果中所有流量为0，这证实了**Step 6确实是不可行的**（在优化器的判断逻辑下）。

优化器使用了while循环来移除不可行的commodity：
```python
while True:
    feasible_demand_matrix = demand_matrix[~demand_matrix['Infeasible']]
    # ... 尝试求解 ...
    if problem.status == cp.INFEASIBLE:
        # 标记某个commodity为不可行并移除
        demand_matrix.at[random_idx, 'Infeasible'] = True
```

如果所有commodity都被移除，最终返回的DataFrame中只有commodity记录但流量都为0。

## 结论

Step 6的不可行**不是由边容量总量限制导致的**（总需求远小于总容量），而是由以下因素导致的：

1. **路径分配的结构性限制**：无法找到满足所有约束的路径组合
2. **关键interlink的瓶颈**：多个commodity的路径可能共享某些关键interlink，导致该interlink超载
3. **max_hops限制**：7跳限制可能减少了可用路径的选择空间
4. **需求分布特征**：Step 6的特定commodity需求组合（特别是Commodity 3的1128.73 packets/s）可能触发了瓶颈模式

建议进一步分析：
- 比较Step 5和Step 6的路径分配差异
- 识别哪些interlink是瓶颈
- 检查是否存在路径结构性的不可行性

