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
- **Multiple subtypes**: a slot may have several distinct heuristic methods, each with its own toggle (e.g., "method A", "method B").
- **Replacement semantics**: when enabled, the heuristic entry replaces the normal entry for the same items at the same priority position; it does not add a duplicate.
- **Affects**: both the allocation order (which items the algorithm tries first) and the displayed efficiency score.

---

## Multi-Zone Mode

Each slot can have two independent priority lists (e.g., "Zone A" and "Zone B"). The user switches between zones; switching filters the candidate list and resource pool accordingly.

---

## Data Format

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

### Entry Properties

| Field | Type | Description |
|-------|------|-------------|
| `items` | `[{id, ?stars}]` | Candidate resources; pick one |
| `score` | number/null | Efficiency metric (lower = better) |
| `heuristic` | bool | Marks as heuristic route entry |
| `heuristic_type` | string | Subtype for multi-heuristic slots |
| `heuristic_note` | string | Human-readable note |

---

## Architecture

Pure client-side static application:

```
config → data loader (api abstraction) → application logic (IIFE)
```

- **Config** — paths, keys, storage settings
- **Data loader** — fetches JSON data, handles static and API modes
- **Application logic** — builds slot indexes, runs backtracking + Pareto filtering, renders UI
- **State persistence** — resource pool state saved to localStorage

No server, no build step, no database.

---

## Development

### Data Pipeline

See [Python maintenance tools](PYTHON_TOOLS.md) for installation, paths, review steps and recovery.

1. Export a separate baseline: `python export_xlsx.py --output baseline.xlsx`.
2. Generate a keyed review list: `python diff_xlsx.py --base baseline.xlsx --user user.xlsx --output changes.review.json`.
3. Review individually; set `accepted` to `true` only for approved entries.
4. Preflight: `python apply_changes.py --review changes.review.json`; use `--output` for a separate preview.
5. Apply with `--write`, run `python validate_data.py`, then re-export and compare.

Existing destinations are backed up before atomic replacement. Historical dated scripts remain as records.
Run regression checks with `python -m unittest test_data_tools -v` and `node --test test_allocator.js`.

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

Requires: `index.html`, `gauntlet_data.json`, `cars.json` (or equivalent data files).

---

## Future Directions

| Priority | Feature |
|----------|---------|
| P0 | Time-based sorting for Expert tier (currently uses arbitrary index order) |
| P1 | Per-item star rating UI (affects availability and priority) |
| P2 | Better score display (units, null handling, heuristic route annotations) |
| P3 | Ban list configuration for Normal tier |
| P4 | Secondary zone data for Theory tier |
| P5 | Heuristic route data for Expert tier |
| P6 | UI polish (tier name in header, detailed scheme info) |
