# minimize_max_link_utilization 优化问题的约束类型

根据 `muti_commodity_optimizer.py` 中的实现（`split_commodities: "on"`），该优化问题包含以下约束：

## 1. 容量约束 (Capacity Constraints)

**数量**: 每个interlink一条，共64条（4×4网格）

**数学表达式**:
```
对于每条interlink (u, v):
  Σ(所有经过该interlink的路径上的流量) × packet_size × 8 ≤ interlink_capacity
```

**代码位置**: 第445-460行

**含义**: 每条interlink上的总流量（以bits/s为单位）不能超过其容量。

**示例**: 
- `interlink_capacity = 10,000,000 bits/s`
- `packet_size = 1500 bytes`
- 单条interlink最大承载流量: `10,000,000 / (1500 × 8) = 833.33 packets/s`

## 2. 需求约束 (Demand Constraints)

**数量**: 每个commodity一条，共4条（4个commodity）

**数学表达式**:
```
对于每个commodity i:
  Σ(commodity i在所有路径上的流量) = demand_i
```

**代码位置**: 第494-499行

**含义**: 每个commodity的总流量必须等于其需求量。这是等式约束。

**示例**:
- Commodity 0: 所有路径流量之和 = 620.71 packets/s
- Commodity 1: 所有路径流量之和 = 731.22 packets/s
- Commodity 2: 所有路径流量之和 = 408.18 packets/s  
- Commodity 3: 所有路径流量之和 = 1128.73 packets/s

## 3. 非负性约束 (Non-negativity Constraints)

**数量**: 每个路径一条，约112条（每个commodity约有28条路径）

**数学表达式**:
```
对于每条路径 (i, path_idx):
  flow_on_path[(i, path_idx)] ≥ ε  (其中 ε = 1e-7)
```

**代码位置**: 第508-511行

**含义**: 每条路径上的流量必须非负（大于等于小的正数ε，避免数值问题）。

## 4. 节点容量约束 (Node Capacity Constraints)

**数量**: 当前被注释掉，为0条

**代码位置**: 第476-490行（已注释）

**含义**: 原本用于限制每个节点的总入站流量，但当前未启用。

## 5. 单路径约束 (Single Path Constraints)

**数量**: 仅当`split_config == "off"`时存在，当前为0条

**代码位置**: 第522-525行（仅用于`split_commodities: "off"`）

**含义**: 当不允许分流时，每个commodity只能选择一条路径。

---

## 总结

当`split_commodities: "on"`且使用`minimize_max_link_utilization`目标时：

| 约束类型 | 数量 | 类型 | 作用 |
|---------|------|------|------|
| **容量约束** | 64 | 不等式 (≤) | 限制每条interlink的最大流量 |
| **需求约束** | 4 | 等式 (=) | 确保每个commodity的需求被满足 |
| **非负性约束** | ~112 | 不等式 (≥) | 确保流量非负 |
| **节点容量约束** | 0 | - | 已禁用 |
| **单路径约束** | 0 | - | 不适用（允许分流） |
| **总计** | ~180 | - | - |

## 可能导致不可行的原因

1. **容量约束违反**: 即使总需求小于总容量，如果某些interlink被所有路径共享，可能无法满足所有需求。
2. **路径限制**: `max_hops = 7`限制了可用路径，可能找不到满足所有约束的路径组合。
3. **需求组合问题**: 某些commodity的源-目的地对可能导致特定interlink成为瓶颈。

## Step 6 特殊分析

Step 6的arrival rates: `[620.71, 731.22, 408.18, 1128.73]` packets/s

- **Commodity 3的需求最高**: 1128.73 packets/s，超过单条interlink容量（833.33 packets/s）
- **必须分流**: 需要通过多条路径分流
- **可能的瓶颈**: 如果多条路径共享某些关键interlink，可能导致不可行

