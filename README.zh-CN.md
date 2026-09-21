# [MutualExclusionAllocator](https://github.com/Testiphi/MutualExclusionAllocator)

[English](README.md) | **中文**

> 🌐 **在线演示**：[testiphi.github.io/MutualExclusionAllocator](https://testiphi.github.io/MutualExclusionAllocator/)

一个基于约束的资源分配工具，支持 Pareto 最优过滤、多用户档位与替代路线启发式。

---

## 概述

本工具求解的是一个**多组互斥分配问题**：

- 你有一个**资源池**（例如物品、代理、资产），每个资源有「可用」与「不可用」两种状态。
- 你定义至多 **N 个分配组**，每组带一个**按优先级排序的候选子集列表**。
- 每个候选子集包含一个或多个资源，它们在该槽位上**互相可替换**。
- 一个资源被分配到某个槽位后，**不能再被其它槽位复用**。
- 部分条目可能有**替代路线**，产生不同的效率指标，可按槽位单独启用。

算法通过**回溯枚举**找出全部可行分配方案，再施加 **Pareto 非支配过滤**，只返回那些在所有维度上都无法被严格改进的方案。

---

## 算法

### 1. 数据模型

每个轨道（分配槽位）持有一组**条目组**。组内资源互相可替换 —— 任选其一即可在该优先级上满足该槽位。

```
槽位: "Slot A"
  组 0: {资源 X, 资源 Y}  ← 优先级 0（最优）
  组 1: {资源 Z}           ← 优先级 1
  组 2: {资源 W}           ← 优先级 2
  ...
```

部分条目带有 `sc`（特殊／启发式路线）标记，可选带子类型（`sc_type`）与备注。当某条启发式路线被启用时，其 sc 版本会**替换**同一优先级上的普通对应条目。

### 2. 回溯枚举

```
for 每个槽位（按顺序）:
  for 每个条目组（按优先级升序）:
    for 组内每个资源:
      if 该资源未被占用 AND 可用:
        分配 → 递归进入下一槽位
```

若某槽位没有任何可用资源，则将其留空并继续枚举（**允许部分分配**）。

### 3. Pareto 非支配过滤

每个完整分配产生一个**优先级向量** `[p₀, p₁, ..., pₙ₋₁]`，其中 `pᵢ` 是分配给槽位 `i` 的资源的优先级（**越小越好**）。未分配的槽位取哨兵值。

**方案 A 支配方案 B**，当且仅当 `∀i : A[i] ≤ B[i]` 且 `∃j : A[j] < B[j]`。

仅返回位于 **Pareto 前沿**（非支配集）上的方案，并按优先级总和排序。

---

## 档位

系统支持多个数据档位以适配不同用途：

| 档位 | 用途 |
|------|------|
| **理论** | 含已知最优效率指标的参考数据，包含启发式路线成绩。 |
| **高手** | 实战数据，含逐项效率分数与可选星级。 |
| **普通** | 高手档的子集，排除特定条目（黑名单），不含分数。 |
| **自动** | 白名单模式 —— 仅一组精选条目可用。 |

各档位共享同一套槽位结构，但在「哪些条目可用」与「条目内哪些资源可用」上不同。切换档位会重建分配索引，但不改变底层算法。

---

## 启发式路线（特殊路线）

部分槽位的条目可能带 `sc: true` 标记，代表不同的操作方式（例如不同技巧、捷径、取巧手段），产生不同的效率指标。

- **按槽位开关**：每条启发式路线可独立启用或停用。
- **多子类型**：一个槽位可有若干种不同的启发式方法，各带独立开关（例如「方法 A」「方法 B」）。
- **替换语义**：启用后，启发式条目**替换**同一优先级上针对相同资源的普通条目，不会新增重复项。
- **影响范围**：既影响分配次序（算法先尝试哪些资源），也影响展示的效率分数。

---

## 双区模式

每个槽位可持有两套独立的优先级列表（例如「A 区」与「B 区」）。用户在两个区之间切换；切换时会相应过滤候选列表与资源池。

---

## 数据格式

```json
{
  "tier_info": {
    "theory": { "label": "Theory", "desc": "..." },
    "expert": { "label": "Expert", "desc": "..." }
  },
  "tracks": [
    {
      "category": "Region A",
      "slot": "Slot 1",
      "has_heuristic_route": true,
      "zones": {
        "primary": {
          "theory": [
            {"items": [{"id": "X"}, {"id": "Y"}], "score": 12.5},
            {"items": [{"id": "X"}], "score": 8.3, "heuristic": true, "heuristic_type": "route_A"}
          ],
          "expert": [
            {"items": [{"id": "X", "stars": 5}], "score": 12.5},
            ...
          ],
          "normal": [{"items": [{"id": "X"}]}, ...],
          "auto": [{"items": [{"id": "X"}]}, ...]
        },
        "secondary": { ... }
      }
    }
  ]
}
```

### 条目属性

| 字段 | 类型 | 说明 |
|------|------|------|
| `items` | `[{id, ?stars}]` | 候选资源；任选其一 |
| `score` | number/null | 效率指标（越小越好） |
| `heuristic` | bool | 标记为启发式路线条目 |
| `heuristic_type` | string | 多启发式槽位的子类型 |
| `heuristic_note` | string | 人类可读备注 |

---

## 架构

纯客户端静态应用：

```
config → 数据加载层（api 抽象）→ 应用逻辑（IIFE）
```

- **Config** —— 路径、键名、存储设置
- **数据加载层** —— 拉取 JSON 数据，处理静态模式与 API 模式
- **应用逻辑** —— 构建槽位索引、执行回溯 + Pareto 过滤、渲染界面
- **状态持久化** —— 资源池状态保存至 localStorage

无需服务器、无构建步骤、无数据库。

---

## 开发

### 数据处理流水线

安装、路径、审核步骤与恢复方式见 [Python 维护工具](PYTHON_TOOLS.md)。

1. 导出一份独立基准：`python export_xlsx.py --output baseline.xlsx`。
2. 生成键控审核清单：`python diff_xlsx.py --base baseline.xlsx --user user.xlsx --output changes.review.json`。
3. 逐条审核；仅对已批准的条目把 `accepted` 置为 `true`。
4. 预检：`python apply_changes.py --review changes.review.json`；用 `--output` 可单独输出预览。
5. 用 `--write` 应用，运行 `python validate_data.py`，然后重新导出并比对。

既有目标文件在原子替换前会先备份。历史带日期的脚本作为记录保留。
运行回归检查：`python -m unittest test_data_tools -v`。

### 算法说明

- 复杂度：最坏情况 `O(k^n)`，其中 `k` = 条目组数量的平均值，`n` = 槽位数量。在现实约束下（`n ≤ 5`、`k ≤ ~25`），枚举几乎瞬时完成。
- 部分分配：无可用资源的槽位留空，而不是阻断整个解。
- Pareto 过滤在完整枚举输出上运行；资源池极大时，方案数量可能被截断。

---

## 部署

- **GitHub Pages**：[testiphi.github.io/MutualExclusionAllocator](https://testiphi.github.io/MutualExclusionAllocator/)
- **仓库**：[github.com/Testiphi/MutualExclusionAllocator](https://github.com/Testiphi/MutualExclusionAllocator)

静态托管（GitHub Pages、Netlify，或任意 Web 服务器均可）。

依赖文件：`index.html`、`gauntlet_data.json`、`cars.json`（或等价的数据文件）。

---

## 后续方向

| 优先级 | 功能 |
|--------|------|
| P0 | 高手档按时间排序（当前使用任意索引顺序） |
| P1 | 逐项星级评定 UI（影响可用性与优先级） |
| P2 | 更完善的分数展示（单位、空值处理、启发式路线标注） |
| P3 | 普通档黑名单配置 |
| P4 | 理论档的双区数据 |
| P5 | 高手档的启发式路线数据 |
| P6 | 界面打磨（页头显示档位名、详细方案信息） |
