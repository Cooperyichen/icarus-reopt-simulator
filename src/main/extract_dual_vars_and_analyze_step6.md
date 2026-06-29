# Step 6 不可行性分析和对偶变量提取方案

## 问题分析

根据实验记录，Step 6被标记为`infeasible_using_previous`，这意味着优化器无法找到可行解。

## 当前限制

1. **优化器的不可行处理机制**：当问题不可行时，优化器使用while循环逐一轮流移除commodity，这使得难以定位具体的约束违反原因。

2. **对偶变量提取**：需要修改优化器代码，在求解后提取demand constraints的对偶变量。

## 需要的修改

### 1. 修改优化器以提取对偶变量

在`solve_mcfp_path_formulation`方法中，需要：
- 保存`demand_constraints`列表的引用
- 在问题求解后，访问`constraint.dual_value`
- 返回对偶变量值（例如，通过DataFrame.attrs或单独返回值）

### 2. 分析Step 6的不可行原因

需要：
- 比较Step 5和Step 6的arrival rates变化
- 检查capacity constraints的违反情况
- 分析路径结构的变化

## 临时解决方案

由于完整实现需要修改优化器核心代码，建议：
1. 先手动检查Step 6的arrival rates和网络容量
2. 运行优化器并观察verbose输出
3. 比较Step 5、6、7的差异

## 对偶变量含义

每个commodity对应一个demand constraint：
```
sum(flows on all paths for commodity i) = demand_i
```

对偶变量λ_i表示：如果demand_i增加1单位，目标函数值（最大链路利用率）会增加多少。

## 实现步骤

1. 修改`muti_commodity_optimizer.py`，在problem.solve()之后提取对偶变量
2. 修改返回值，包含对偶变量信息
3. 创建分析脚本提取所有步骤的对偶变量

