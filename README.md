# [MutualExclusionAllocator](https://github.com/Testiphi/MutualExclusionAllocator)

**English** | [中文](README.zh-CN.md)

> 🌐 **Live demo**: [testiphi.github.io/MutualExclusionAllocator](https://testiphi.github.io/MutualExclusionAllocator/)

A constraint-based resource allocation tool with Pareto-optimal filtering, supporting multiple user tiers and alternative-route heuristics.

---

## Overview

This tool solves a **multi-group mutual-exclusion allocation problem**:

- You have a **pool of resources** (e.g., items, agents, assets), each available or unavailable.
- You define up to **N allocation groups**, each with a **priority-ordered list of candidate subsets**.
- Each candidate subset is one or more resources that are mutually interchangeable for that slot.
- A resource assigned to one slot **cannot be reused** elsewhere.
- Some entries may have **alternative routes** that yield different efficiency metrics, enabled per-slot.

The algorithm finds all feasible assignments via **backtracking enumeration**, then applies **Pareto non-dominated filtering** to return only schemes that cannot be strictly improved across all dimensions.

---

## Algorithm

### 1. Data Model

Each track (allocation slot) has a list of **entry groups**. Within each group, resources are mutually interchangeable — picking any one satisfies that slot at that priority level.

```
Slot: "Slot A"
  Group 0: {Resource X, Resource Y}  ← priority 0 (best)
  Group 1: {Resource Z}               ← priority 1
  Group 2: {Resource W}               ← priority 2
  ...
```

Some entries carry an `sc` (special/heuristic route) flag with optional subtype (`sc_type`) and note. When a heuristic route is enabled, the sc version replaces its normal counterpart at the same priority slot.

### 2. Backtracking Enumeration

```
for each slot (in order):
  ① leave the slot unassigned → recurse to next slot
  ② for each entry group (by ascending priority):
       for each resource in the group:
         if resource is not already used AND is available:
           assign → recurse to next slot
```

**Leaving a slot unassigned is itself a feasible scheme** (partial assignments are allowed), so the
"leave blank" branch is enumerated explicitly for *every* slot: a resource that is available for one
slot may be worth saving for a later one, and the two schemes differ in their priority vectors without
dominating each other.

> If "leave blank" were only tried when the slot has no resource left, earlier slots would gain
> **absolute priority** over scarce resources, and a set of non-dominated schemes would be silently
> dropped (e.g. two slots that can only take resource A: `[blank, A]` was never enumerated).
> Leaving a slot blank costs the sentinel value (below), so when resources are plentiful the blank
> branches are always dominated and never reach the front.

### 3. Pareto Non-Dominated Filtering

Each complete assignment produces a **priority vector** `[p₀, p₁, ..., pₙ₋₁]` where `pᵢ` is the priority of the resource assigned to slot `i` (lower = better). Unassigned slots get a sentinel value.

**Scheme A dominates scheme B** iff `∀i : A[i] ≤ B[i]` and `∃j : A[j] < B[j]`.

Only schemes on the **Pareto front** (non-dominated set) are returned, sorted by total priority sum.

---

## Tiers

The system supports multiple data tiers for different use cases:

| Tier | Purpose |
|------|---------|
| **Theory** | Reference data with best-known efficiency metrics. Includes heuristic route times. |
| **Expert** | Practical data with per-item efficiency scores and optional star ratings. |
| **Normal** | Subset of Expert with certain items excluded (ban list). No scores. |
| **Auto** | Allow-list mode — only a curated set of items is available. |

Tiers share the same slot structure but differ in which entries and which items within each entry are available. Switching tiers rebuilds the allocation index without changing the underlying algorithm.

---

## Heuristic Routes (Special Routes)

Certain slots may have entries flagged with `sc: true`, representing alternative approaches (e.g., different techniques, shortcuts, workarounds) that yield different efficiency metrics.

- **Per-slot toggle**: each heuristic route can be enabled or disabled independently.
- **Three states**: `all` (default) / a specific route type / `off`. When off, all `sc` entries for that
  slot are dropped; when a specific type is selected, only entries with a matching `sc_type` are kept.
- **Additive semantics (not replacement)**: `sc` entries compete as **additional candidates** alongside
  the normal entries of the same slot, each ranked by its own metric. Disabling a route does not change
  the ranking of normal entries.
- **Affects**: both the allocation order (which items the algorithm tries first) and the displayed efficiency score.
- Every `sc_type` must be registered in `SC_TYPES` (`repo/data_tools.py`, currently 9 values);
  new route types must be added to that constant first.

---

## Multi-Zone Mode

Each slot can have two independent priority lists (e.g., "Zone A" and "Zone B"). The user switches between zones; switching filters the candidate list and resource pool accordingly.

The two resource pools, and the per-item star-rating rules, are declared per item in `cars.json`
(`zones` / `star_rule`) and shared with the Python validation scripts — see "Architecture".

---

## Data Format

`gauntlet_data.json` (tracks) and `cars.json` (vehicle library, which also carries the rules) are both
real files of this project and use fixed Chinese field names. Below is the actual structure
(abridged from the real files):

```json
// gauntlet_data.json
{
  "_version": 1,
  "_comment": "...",
  "tier_info": { "理论": { "label": "...", "desc": "..." } },
  "tracks": [
    {
      "大地图": "古老斗技场",
      "小地图": "偏僻小道",
      "has_special_route": true,
      "special_route_note": "...",
      "五区": {
        "理论": [ { "cars": [ { "name": "9x8" } ], "time": 16.9,
                    "sc": true, "sc_type": "跳图" } ],
        "高手": [ { "cars": [ { "name": "r兔", "stars": 6 } ], "time": 18.59 } ],
        "普通": [ { "cars": [ { "name": "r兔", "stars": 6 } ] } ],
        "自动": [ { "cars": [ { "name": "白龙" } ] } ]
      },
      "四区": { "理论": [], "高手": [], "普通": [], "自动": [] }
    }
  ]
}
```

### Entry Properties

| Field | Type | Description |
|-------|------|-------------|
| `cars` | `[{name, ?stars}]` | Candidate resources; always a single-element array here (one per group) |
| `time` | number / absent | Efficiency metric (lower = better). **Absent means "no result yet"**, not a placeholder value |
| `sc` | bool | Marks the entry as an alternative (heuristic) route |
| `sc_type` | string | Route type; must belong to `data_tools.SC_TYPES` |

Theory/expert tiers are kept sorted by `time` ascending, with result-less entries last; the normal/auto
tiers only express availability (no `time`). Every expert entry must have a matching normal-tier mirror
(enforced by validation).

```json
// cars.json
{
  "_comment": "...",
  "_nickname_map": { "007s": "Glickenhaus 007S" },
  "cars": [
    {
      "title": "W Motors Lykan Hypersport",
      "nickname": "狼崽",
      "score": 4083, "class": "S", "max_stars": 5,
      "max_speed": 407.6, "acceleration": 80.48, "handling": 40.97, "nitro": 58.46,
      "zones": ["五区", "四区"],
      "star_rule": { "min": 5, "max": 5, "default": 5 }
    }
  ]
}
```

`nickname` is the name used to reference this vehicle in the data file. `zones` and `star_rule` are the
**hand-maintained** pool membership and star limits, shared by the frontend and the Python validation
scripts (see "Architecture").

---

## Architecture

Pure client-side static application:

```
config → data loader (api abstraction) → application logic (IIFE)
```

- **Config** — paths, keys, storage settings
- **Data loader** — fetches JSON data, handles static and API modes
- **Rule derivation** — the zone pools (`zones`) and star rules (`star_rule`) are derived from
  `cars.json` by `buildCarRules()` in `index.html`; **this is the single source of truth** and the page
  no longer keeps a hardcoded copy
- **Application logic** — builds slot indexes, runs backtracking + Pareto filtering, renders UI
- **State persistence** — resource pool state saved to localStorage

No server, no build step, no database.

> **Single source of truth for rules**: the pools and star rules used to be hardcoded in `index.html`,
> with a second, simplified table on the Python side (`data_tools.ZONE4_MAX`). The two had drifted —
> the frontend knew rules for 72 cars while Python knew 15 and never checked the minimum star level.
> They now live in `cars.json` as `zones` / `star_rule` and are read by both the page and
> `python validate_data.py`. Change vehicle rules in `cars.json`.

---

## Development

### Data Pipeline

See [Python maintenance tools](PYTHON_TOOLS.md) for installation, paths, review steps and recovery.

1. Export a separate baseline: `python export_xlsx.py --output baseline.xlsx`.
2. Generate a keyed review list: `python diff_xlsx.py --base baseline.xlsx --user user.xlsx --output changes.review.json`.
3. Review individually; set `accepted` to `true` only for approved entries.
4. Preflight: `python apply_changes.py --review changes.review.json`; use `--output` for a separate preview.
5. Apply with `--write`, run `python validate_data.py`, then re-export and compare.

Existing destinations are backed up before atomic replacement. Historical dated scripts and user-workbook
snapshots are **not kept locally** — use the git commit history to trace a past round.
Run regression checks:

```bash
python -m unittest test_data_tools -v      # data tools and validation
node --test test_allocator.js              # allocator boundary cases
node test_boot_smoke.js                    # page boot smoke test (DOM stub, no browser)
```

### Algorithm Notes

- Complexity: `O(k^n)` worst case where `k` = candidates per slot and `n` = slot count.
  Because every slot also enumerates a "leave blank" branch, the search is roughly 1.5–2× the size of
  an enumeration that only allows blanks when no resource is available.
- **Measured performance (Node 22, 2026-09-28; `n = 5`, full pool, five candidate-heaviest maps)**:

  | Zone / tier | Candidates | Enumerated leaves | Time | Heap growth |
  |---|---|---|---|---|
  | Five-zone / theory | 25/23/22/21/19 | 4,456,946 | **1714 ms** | **~1140 MB** |
  | Five-zone / expert | 23/14/14/14/12 | 638,446 | 143 ms | ~181 MB |
  | Four-zone / theory | 12/12/12/11/10 | 220,459 | 64 ms | ~56 MB |
  | Four-zone / expert | 10/10/10/9/9 | 68,656 | 19 ms | ~15 MB |

  So it is **not "near-instant"**: the worst case costs ~1.7 s and over a gigabyte of heap, because
  `allSchemes` materialises every enumerated scheme before filtering.
  `SCHEME_LIMIT = 25` caps only the schemes **returned/displayed**, not the computation or memory.
  The solve runs synchronously on the browser main thread; `requestAnimationFrame` + `setTimeout`
  only defer the start, they do not reduce the work. **No browser-side stress test has been run yet** —
  the figures above are algorithm-level and exclude rendering.
- Partial assignments: any slot may be left blank, and the blank branch is enumerated explicitly like
  any other. A blank costs the sentinel value (99), so when resources are plentiful blank schemes are
  always dominated and never appear on the front.
- The Pareto filter runs on the full enumeration output; `SCHEME_LIMIT` caps only the number of
  schemes **returned/displayed**, not the amount of computation.

---

## Deployment

- **GitHub Pages**: [testiphi.github.io/MutualExclusionAllocator](https://testiphi.github.io/MutualExclusionAllocator/)
- **Repo**: [github.com/Testiphi/MutualExclusionAllocator](https://github.com/Testiphi/MutualExclusionAllocator)

Static hosting (GitHub Pages, Netlify, any web server).

Required files (all three): `index.html`, `gauntlet_data.json`, `cars.json`.
Besides vehicle data, `cars.json` carries the zone pools and star rules, so it is a **hard dependency** —
if it fails to load the page reports the error instead of degrading.

---

## Known Limitations & Future Directions

(Implemented features are no longer listed here; only items confirmed as unfinished.)

| Item | Status |
|------|--------|
| Solve performance | Worst case ~1.7 s and ~1.1 GB heap (see "Algorithm Notes"). Options: stop materialising all schemes, incremental front filtering, or move the solve off the main thread. **Not yet decided.** |
| Browser-side stress test | **Not done.** All figures are Node algorithm-level measurements, excluding rendering and GC pauses. |
| Thin candidate lists | 13 "zone/tier" combinations are down to 1–2 candidates (weakest: `大桥海湾/喧闹铁路` four-zone expert has only `9x8★6`; `极昼之地/凌云狂飙` four-zone expert has only `ssc★2`). |
| Redundant `max` field | `star_rule.max` matches `cars.json`'s `max_stars` for all 9 cars that declare it (`att`/`杰弟`/`dose` use 6 = unconstrained). Whether to merge them is undecided. |
