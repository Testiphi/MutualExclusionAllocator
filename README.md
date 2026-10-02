# [MutualExclusionAllocator](https://github.com/Testiphi/MutualExclusionAllocator)

**English** | [中文](README.zh-CN.md)

> 🌐 **Live demo**: [testiphi.github.io/MutualExclusionAllocator](https://testiphi.github.io/MutualExclusionAllocator/)

A car allocator for Gauntlet challenges, supporting five-zone/four-zone pools, four data tiers, star ratings and special routes. It returns Pareto-optimal schemes without reusing cars.

---

## Overview

This tool solves a **multi-group mutual-exclusion allocation problem**:

- You have a **pool of resources** (e.g., items, agents, assets), each available or unavailable.
- You define up to **N allocation groups**, each with a **priority-ordered list of candidate subsets**.
- Each candidate subset is one or more resources that are mutually interchangeable for that slot.
- A resource assigned to one slot **cannot be reused** elsewhere.
- Some entries may have **alternative routes** that yield different efficiency metrics, enabled per-slot.

The algorithm visits all feasible assignments via **backtracking enumeration**, maintaining the **Pareto non-dominated front** at each leaf to return only schemes that cannot be strictly improved across all dimensions.

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

Some entries carry an `sc` (special/heuristic route) flag and a required valid `sc_type`. When enabled, normal and special routes compete: each car uses its faster effective time, then candidates are ranked by time.

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

Each leaf is compared immediately with the current front: discard it if dominated, otherwise remove the schemes it dominates and add it.
Different car assignments with equal vectors are retained. After enumeration, sort by total priority and then lexicographically by vector, returning at most 25 schemes.
The objective is each map's candidate rank; it does not directly minimise the sum of race times.

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
- **Three states**: `all` (default) / a specific route type / `off`. Off removes all SC entries for the slot;
  a specific type keeps only matching SC entries while normal routes remain available.
- **One candidate per car**: compare normal and allowed SC results, using the faster effective time for each car.
  Changing routes reorders candidates. Normal recorded times stay unchanged, but a car's priority rank may change.
- **Independent estimation**: expert times are interpolated/extrapolated separately for the normal route and each `sc_type`, then compared. Different special routes are never combined for interpolation. Display and ranking share one scoring entry point.
- **Affects**: both the allocation order (which items the algorithm tries first) and the displayed efficiency score.
- Every `sc_type` must be registered in `SC_TYPES` (`repo/data_tools.py`, currently 9 values);
  new route types must be added to that constant first.

---

## Multi-Zone Mode

Each slot can have two independent priority lists (e.g., "Zone A" and "Zone B"). The user switches between zones; switching filters the candidate list and resource pool accordingly.

The two resource pools, and the per-item star-rating rules, are declared per item in `cars.json`
(`zones` / `star_rule`) and shared with the Python validation scripts — see "Architecture".
Four-zone special-modification star limits are hand-maintained. A full-upgrade score above 4200 alone does not make a car invalid in that pool.

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
| `time` | number / null / absent | Recorded time must be positive finite seconds; lower is better. Null or absent means no result |
| `sc` | bool | Marks the entry as an alternative (heuristic) route |
| `sc_type` | string | Route type; must belong to `data_tools.SC_TYPES` |

Theory/expert tiers are sorted by `time` ascending, with result-less entries last; normal/auto tiers express availability without times.
Current maintenance creates theory/expert entries only when results exist, without pre-populating placeholders; tools still support existing result-less entries.
Only **non-SC expert entries** require a matching normal-tier mirror with the same car and stars.
SC belongs only in theory/expert tiers and does not create normal mirrors. Each track must explicitly contain both zones and all four tiers, which may be empty lists.

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
config.js → api.js → index.html (state, candidate preparation, rendering)
                         ├→ allocator.js (pure allocation algorithm)
                         └→ race_scores.js (time calculation)
```

- **Config** — paths, keys, storage settings
- **Data loader** — currently fetches static JSON; API mode is a reserved interface with no backend implementation in this repository
- **Rule derivation** — the zone pools (`zones`) and star rules (`star_rule`) are derived from
  `cars.json` by `buildCarRules()` in `index.html`; **this is the single source of truth** and the page
  no longer keeps a hardcoded copy
- **Application logic** — prepares candidates, estimates star-adjusted times, manages state and renders the UI
- **Algorithm module** — `allocator.js` has no DOM/network dependencies and incrementally maintains the Pareto front during backtracking
- **Scoring module** — `race_scores.js` has no DOM/network dependencies and owns the star curve and independent route estimates; an empty four-zone candidate list remains empty instead of borrowing five-zone entries
- **State persistence** — garage, star ratings and UI preferences use this browser's localStorage; there are no accounts or cross-device sync
- **Local maintenance** — Python tools maintain JSON/Excel and are not part of the web runtime

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
Each track must explicitly contain both zones and all four tiers; empty lists are valid. SC is allowed only in theory/expert tiers.
Zone sync retains the score threshold and also checks both pools and star ranges. Ineligible entries are reported and skipped; existing invalid data still blocks sync.

Run `python sync_zones.py` to review a dry run before using `--write`.
Different times across zones use the faster value. Before writing, the source is checked for changes during processing; this is not a multi-process file lock.

Run regression checks:

```bash
python -m unittest test_data_tools -v      # data tools and validation
node --test test_allocator.js              # allocator boundary cases
node --test test_race_scores.js            # score boundaries and page wiring
node test_boot_smoke.js                    # page boot smoke test (DOM stub, no browser)
```

As of 2026-10-02, 44 Python tests, 15 allocator tests, 11 scoring tests and the boot smoke test pass, with zero data-validation errors.
The boot test uses a DOM stub and does not validate real-browser interaction or performance.

### Algorithm Notes

- Leaf count is bounded by `O((k+1)^n)` including blanks. Each leaf also scans the front; a large front can still increase comparison cost and memory.
- Leaves are compared directly against the current front. Dominated assignments are discarded without copying arrays.
  Equal vectors with different assignments are retained; sorting and the 25-scheme limit apply only after enumeration finishes.
- **Comparison (2026-10-01, Node v24.15.0 / Windows x64 / i9-13900H / 63.6 GB RAM)**:

  | Zone / tier | Unique candidates | Leaves | Time old→new(ms) | Before/after heap delta old→new(MB) |
  |---|---|---|---|---|
  | Five-zone / theory | 22/18/18/18/18 | 2,347,041 | 517.6→150.1 | 631.8→0.6 |
  | Five-zone / expert | 20/12/11/11/10 | 309,414 | 74.0→23.2 | 88.9→1.0 |
  | Four-zone / theory | 12/12/11/10/10 | 186,020 | 46.9→14.6 | 56.3→2.0 |
  | Four-zone / expert | 9/8/7/7/7 | 31,404 | 9.6→4.8 | 10.8→2.0 |

  Each version used a separate process, one cold call, and `--expose-gc --max-old-space-size=8192`.
  Inputs use the five maps with most unique candidates, a full zone garage, all SC routes and default stars;
  expert times use the original frontend estimator. Timing covers only the solve; leaf counting runs separately.
  GC runs before the call, not after. **Heap delta is neither peak heap nor total allocations**; GC may occur during the call.
  The old algorithm is from `ce30445`. Earlier reports counted multiple stars/routes of one car as separate candidates;
  this input now matches the page, so absolute values are not directly comparable with those reports.
  These are dense examples, not a proof of the worst case or statistics from repeated measurements.
- Solving still runs synchronously on the browser main thread; deferring the start does not remove the work.
  **No browser-side stress test has been run**; Node figures exclude page rendering and do not predict browser/mobile latency.
- Partial assignments: any slot may be left blank, and the blank branch is enumerated explicitly like
  any other. A blank costs the sentinel value (99), so when resources are plentiful blank schemes are
  always dominated and never appear on the front.
- `SCHEME_LIMIT` caps only schemes **returned/displayed**, not enumeration or the search-time front size.

---

## Deployment

- **GitHub Pages**: [testiphi.github.io/MutualExclusionAllocator](https://testiphi.github.io/MutualExclusionAllocator/)
- **Repo**: [github.com/Testiphi/MutualExclusionAllocator](https://github.com/Testiphi/MutualExclusionAllocator)

Static hosting (GitHub Pages, Netlify, any web server).

Deployment files: `index.html`, `styles.css`, `config.js`, `api.js`, `allocator.js`, `race_scores.js`, `gauntlet_data.json`, `cars.json`.
When updating an older deployment, upload both the new `index.html` and `race_scores.js`; omitting the new module prevents page startup.
Besides vehicle data, `cars.json` carries the zone pools and star rules, so it is a **hard dependency** —
if it fails to load the page reports the error instead of degrading.

For local preview, run from the repository directory:

```bash
python -m http.server 8000
```

Open [localhost:8000](http://localhost:8000/) in a browser. Use HTTP; opening the HTML directly may prevent JSON loading due to browser restrictions.
Python is used only for this preview server and local maintenance; the deployed static page does not require it.

---

## Known Limitations & Future Directions

(Implemented features are no longer listed here; only items confirmed as unfinished.)

| Item | Status |
|------|--------|
| Solve performance | Incremental front filtering is implemented; the dense example takes ~150 ms (see "Algorithm Notes"). Full enumeration and front scans still run on the main thread. Pruning and Workers are not implemented. |
| Browser-side stress test | **Not done.** Figures are single Node algorithm calls; GC during a call may affect timing. Browser rendering and responsiveness remain untested. |
| Thin candidate lists | 13 "zone/tier" combinations are down to 1–2 candidates (weakest: `大桥海湾/喧闹铁路` four-zone expert has only `9x8★6`; `极昼之地/凌云狂飙` four-zone expert has only `ssc★2`). |
| Redundant `max` field | `star_rule.max` matches `cars.json`'s `max_stars` for all 9 cars that declare it (`att`/`杰弟`/`dose` use 6 = unconstrained). Whether to merge them is undecided. |
