# MutualExclusionAllocator

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
  for each entry group (by ascending priority):
    for each resource in the group:
      if resource is not already used AND is available:
        assign → recurse to next slot
```

If a slot has zero available resources, it is left unassigned and enumeration continues (partial assignments are allowed).

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

1. Edit source data files (tier definitions, ban/allow lists)
2. Run migration script: `python migrate.py`
3. Reformat: `python reformat.py`
4. Deploy: push to hosting

### Algorithm Notes

- Complexity: `O(k^n)` worst case where `k` = avg. entry group count and `n` = slot count. With realistic constraints (`n ≤ 5`, `k ≤ ~25`), enumeration completes near-instantly.
- Partial assignments: slots with no available resources are left unassigned rather than blocking the entire solution.
- The Pareto filter runs on the full enumeration output; for very large item pools, the scheme count may be capped.

---

## Deployment

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
