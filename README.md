# MutualExclusionAllocator

A constraint-based resource allocation tool with Pareto-optimal matching algorithm and pure static-web architecture.

---

## Problem Definition

Multi-group allocation with mutual exclusion constraints:

- **Resource pool** — a set of items, each can be marked as available or unavailable (garage).
- **Allocation groups** — multiple groups, each with multiple candidate slots. Slots within the same group category are mutually exclusive (only one can be selected per category).
- **Priority-ordered preference lists** — each slot has a ranked list of preferred resources.
- **No-reuse constraint** — a resource assigned to one slot cannot be reassigned to another.

The goal is to assign available resources to the selected slots according to their preference priority, while respecting the mutual exclusion and no-reuse constraints.

---

## Algorithm

**Pareto-optimal exhaustive search with non-dominated filtering:**

1. User selects up to 5 slot categories (big maps) and their specific slots (small maps), ensuring no duplicate categories.
2. The system enumerates all valid assignments via backtracking — for each slot, it tries every possible priority-group and every owned vehicle within that group, respecting the no-reuse constraint.
3. From the full set of valid assignments, it computes the **Pareto front** (non-dominated set): a scheme A strictly dominates B if A's priority vector is ≤ B's vector in every dimension and strictly better in at least one.
4. Only non-dominated schemes are presented to the user, sorted by total priority score (ascending).

This approach guarantees that the user never sees a scheme that is strictly worse than another across all priorities.

**Complexity:** In the worst case the backtracking explores O(k^n) candidate assignments where k is avg. recommendation-list length and n is the number of selected slots. In practice k ≤ ~20 and n ≤ 5, so the search completes near-instantly for typical racing-game data sizes.

---

## Features

- **Pareto-optimal filtering** — only "can't-beat" allocation schemes are shown
- **Total priority score** — each scheme shows its aggregate priority sum (lower = better)
- **Interactive garage** — toggle individual owned vehicles with one click
- **Persistent garage state** — vehicle selection is saved to localStorage
- **Mutual exclusion enforcement** — duplicate big-map selections are blocked
- **Loading indicator** — visual feedback during scheme computation
- **Fully static** — no server, no build step, no database

---

## System Design

- **Data-driven architecture** — all slot definitions and preference lists are stored in an external JSON file (`data.json`), decoupled from the UI logic.
- **Client-side state management** — the resource pool is tracked as local toggle state with localStorage persistence.
- **Pure static deployment** — entirely client-side (HTML, CSS, JavaScript). Hostable on GitHub Pages, Netlify, or any static web service.
- **Reusability** — adapt to other allocation scenarios by replacing `data.json` without modifying the algorithm or UI logic.

---

## Application Example

The current data configuration models a vehicle-to-track allocation scenario from **Asphalt 9: Legends** (racing game). Each "group category" is a map region (大地图), each "slot" is a specific track (小地图), and each "resource" is a vehicle. The assignment logic follows in-game recommended priority order and ensures no vehicle is assigned to multiple tracks.

---

## Usage

The project is deployed on GitHub Pages:

[https://testiphi.github.io/MutualExclusionAllocator/](https://testiphi.github.io/MutualExclusionAllocator/)

To run locally:

```bash
git clone https://github.com/Testiphi/MutualExclusionAllocator.git
```

Then open `index.html` in any modern browser. No build step or server is required.

---

## Project Structure

```
MutualExclusionAllocator/
├── index.html      # Single-page application (UI + algorithm)
├── data.json       # Slot definitions and priority lists
└── README.md       # This file
```

---

## Data Format

```json
{
  "擂台选车表": [
    {
      "大地图": "MapRegionName",
      "小地图": "TrackName",
      "选车顺序": ["Car1", "Car2", "Car3", ...]
    },
    ...
  ]
}
```

- `大地图` — mutually exclusive category (only one track per region per session)
- `小地图` — specific slot within the region
- `选车顺序` — priority-ordered list where lower index = higher recommendation priority

---
