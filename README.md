# MutualExclusionAllocator

加拉帕戈斯（Asphalt 9: Legends）擂台选车助手 — 基于帕累托最优的互斥资源分配器。

A9 Gauntlet car selector with Pareto-optimal matching, tier-based data, and special-route support.

---

## 功能概览

### 🏎️ 擂台选车
- 选 1-5 张地图（大地图互斥不可重复），自动分配最优车辆
- 基于回溯枚举 + 帕累托非支配过滤，只展示不可被全面超越的方案
- 车库可自由开关车辆，持久化到 localStorage

### 📊 四档位切换
| 档位 | 说明 |
|------|------|
| 理论档 | 金车理论成绩（满星，含特殊跑法如 BWO/跳图），按时间排序 |
| 高手档 | 当前擂台选车数据，有成绩/星级字段，默认 ★6 |
| 普通档 | 高手档基础上 ban 部分车（目前空 ban，待配置） |
| 自动档 | 白名单模式，只保留 11 辆好开车 + 个别赛道特例 |

### 🏃 特殊跑法开关
9 条赛道有特殊跑法（BWO 跳图、超绝跳图、低 pf 等）：
- 单类型 → 开启/关闭 toggle
- 多类型（地心探险：新跳图/旧跳图/稳定跳图）→ 下拉选择器
- 关闭时只显示正常跑法成绩，开启时 sc 版本替换普通版本

### 🔄 四区模式
- 一键切换五区/四区选车
- 四区独立数据排序，车库自动过滤
- 模式持久化到 localStorage

### 🔍 车库增强
- 搜索过滤（支持昵称和真名）
- 排序切换（默认/分↓/分↑）
- 等级筛选（R/S/A/B/C/D）
- 70+ 昵称映射 → 320 辆全量数据

---

## 架构

纯静态前端应用，3 个 `<script>`：

```
config.js → api.js → index.html (inline IIFE)
```

所有逻辑在 IIFE 内，变量不暴露到 window。

---

## 数据格式 (gauntlet_data.json)

```json
{
  "_version": 2,
  "tier_info": {
    "理论": {"label": "理论档", "desc": "..."},
    "高手": {"label": "高手档", "desc": "..."},
    "普通": {"label": "普通档", "desc": "..."},
    "自动": {"label": "自动档", "desc": "..."}
  },
  "tracks": [
    {
      "大地图": "冰火岛",
      "小地图": "地心探险",
      "has_special_route": true,
      "special_route_note": "BWO新跳图 / BWO旧跳图 / BWO稳定跳图",
      "五区": {
        "理论": [
          {"cars": [{"name": "9x8"}], "time": 14.7, "sc": true, "sc_type": "新跳图"},
          {"cars": [{"name": "秋王"}], "time": 16.0, "sc": true, "sc_type": "新跳图"},
          ...
        ],
        "高手": [
          {"cars": [{"name": "恶魔", "stars": 6}], "time": 36.7},
          ...
        ],
        "普通": [{"cars": [{"name": "恶魔"}]}, ...],
        "自动": [{"cars": [{"name": "玻璃"}]}, ...]
      },
      "四区": { ... }
    }
  ]
}
```

### 特殊跑法标记

```json
// 单类型 sc
{"cars": [{"name": "杰皇"}], "time": 19.5, "sc": true, "sc_note": "超绝跳图版"}

// 多类型 sc（地心探险）
{"cars": [{"name": "9x8"}], "time": 14.7, "sc": true, "sc_type": "新跳图", "sc_note": "BWO新跳图"}
```

---

## 文件结构

```
MutualExclusionAllocator/
├── index.html              # 单页应用
├── config.js               # 配置文件（dataJson 路径等）
├── api.js                  # 数据加载抽象层
├── gauntlet_data.json      # 统一赛道数据（4 档位）
├── cars.json               # 320 辆车辆数据（昵称+性能）
├── ban_config.json         # 普通/自动档的 ban/allow 配置
├── migrate_v2.py           # 迁移脚本
├── reformat_json.py        # JSON 格式化脚本
└── README.md
```

---

## 开发

### 数据更新流程

1. 修改 `theory.json`（理论档数据）或 `ban_config.json`（ban 配置）
2. 跑迁移：`python migrate_v2.py`
3. 格式化：`python reformat_json.py`
4. 复制到 repo：`copy gauntlet_data.json repo/`
5. 部署：`git push`

### 算法

- 回溯枚举所有可行分配（车不重复，图不重复）
- 帕累托非支配过滤
- 按总优先级分升序排列
- 某图无可用车时留空，不阻断整体方案

---

## 部署

GitHub Pages: [https://testiphi.github.io/MutualExclusionAllocator/](https://testiphi.github.io/MutualExclusionAllocator/)

强制刷新（Ctrl+F5）清除 CDN 缓存。

---

## 待办 / 下一步

| 优先级 | 目标 |
|--------|------|
| P0 | 高手档按 time 排序（当前仍按数组下标） |
| P1 | 星级自定义 UI（1-6★，影响可用性和排序） |
| P2 | 成绩展示优化（s 后缀、sc 标注、null 隐藏） |
| P3 | 普通档 ban 配置 |
| P4 | 理论档四区数据补充 |
| P5 | 高手档特殊跑法数据 |
| P6 | 界面微调（档位名显示、方案详情等） |
