# [MutualExclusionAllocator](https://github.com/Testiphi/MutualExclusionAllocator)

> 2026-10-22: Announcements, account controls and manual garage saving are deployed and user-accepted; scheduled backups are restored. Temporary car/star changes do not overwrite saved profiles. See [deployment and security check record](COMMUNITY_DEPLOYMENT.md).


**English** | [中文](README.zh-CN.md)

> 🌐 **Website**: [RacePick](https://racepick.cn/) · **Static guest demo**: [testiphi.github.io/MutualExclusionAllocator](https://testiphi.github.io/MutualExclusionAllocator/)

A car allocator for Gauntlet challenges, supporting five-zone/four-zone pools, four data tiers, star ratings and special routes. It returns Pareto-optimal schemes without reusing cars.

## Current Features and Release Status

Latest user-confirmed status (2026-10-22): application `651ea3d88a27bdff95088b75`, community_schema=1. Existing accounts and profiles were preserved; score version `c8889ff96eb29714d80248cca283b9fa` and write enablement were unchanged. Production acceptance, coherent backup and isolated restore drill passed; scheduled backups are restored. The feature branch has not been merged into main.

Latest data deployment: on 2026-10-21, three five-zone theory time improvements went live in release `09897d5f81a696dca0b95c8e` (source `7a2f164`). The user confirmed the updated results and account features work correctly. See the [deployment record](PRODUCTION_DEPLOYMENT.md). Official score writeback had not yet been deployed at that point.

The account feature branch was merged into main on 2026-10-20, preserving the latest main-branch score data and existing workbooks. This source merge did not redeploy the production service; official score writeback had not yet been deployed at that point.

Accounts and submission review went live on 2026-10-20. The user completed production acceptance for registration/email verification, password reset with old-password and session invalidation, garage/star persistence, submission review and role isolation.

- Guests can continue allocating cars without an account; signed-in users can save their garage and star ratings.
- Players submit results and provide requested follow-up information. Administrators can rate results, adjust tiers, accept or ignore submissions, and provide feedback.
- A protected superadministrator manages email-bound administrator invitations and permissions.

Acceptance saves a review decision; it does not update official scores automatically. The user has since confirmed deployment and enablement of versioned score writes, which require explicit superadministrator confirmation. Workbook synchronization remains local. Excel bulk import and contribution-based access unlocking are not implemented. The contribution leaderboard (0–10 quality points plus 10 adoption points, public nicknames, all-time and monthly rankings) and grouped homepage navigation are deployed and user-accepted. Deployment, backup and cleanup evidence is recorded in [production upgrade notes](CONTRIBUTIONS_PRODUCTION.md); start future operations from the [cloud handoff](CLOUD_HANDOFF.md). See also [local setup and acceptance](CONTRIBUTIONS_LOCAL.md).

Manual database backup succeeded and the automatic backup timer is enabled. The user has since confirmed the scheduled run, coherent backup and isolated restore drill. See [production deployment and acceptance](PRODUCTION_DEPLOYMENT.md).


---

## Overview

This tool solves a **multi-group mutual-exclusion allocation problem**:

- You have a **pool of resources** (e.g., items, agents, assets), each available or unavailable.
- You define up to **N allocation groups**, each with a **priority-ordered list of candidate subsets**.
- Each candidate subset is one or more resources that are mutually interchangeable for that slot.
- A resource assigned to one slot **cannot be reused** elsewhere.
- Some entries may have **alternative routes** that yield different efficiency metrics, enabled per-slot.

The algorithm uses exact backtracking with optimistic-bound pruning, maintaining the **Pareto non-dominated front** at visited leaves. A branch is skipped only when an existing scheme strictly dominates its lower bound, including the unassigned option.

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

Allocation runs in the browser. The production website uses Nginx HTTPS and FastAPI, with SQLite for accounts, garages, submissions and review records:

```
config.js → app_state.js → api.js → index.html (state, candidate preparation, rendering)
                         ├→ allocator.js (pure allocation algorithm)
                         └→ race_scores.js (time calculation)

auth.js / profile_store.js / submissions.js / admin_access.js
        → Nginx HTTPS → FastAPI → SQLite
                              └→ Aliyun SMTP (verification and reset)
```

- **Config** — paths, keys, storage settings
- **Score data loader** — still fetches public JSON; the score-data API mode in `api.js` remains reserved and is separate from the implemented account/submission APIs
- **Rule derivation** — the zone pools (`zones`) and star rules (`star_rule`) are derived from
  `cars.json` by `buildCarRules()` in `index.html`; **this is the single source of truth** and the page
  no longer keeps a hardcoded copy
- **Application logic** — prepares candidates, estimates star-adjusted times, manages state and renders the UI
- **Algorithm module** — `allocator.js` has no DOM/network dependencies and incrementally maintains the Pareto front during backtracking
- **Scoring module** — `race_scores.js` has no DOM/network dependencies and owns the star curve and independent route estimates; an empty four-zone candidate list remains empty instead of borrowing five-zone entries
- **State boundaries** — `app_state.js` validates garage/route selections and publishes only the latest queued computation. Storage failures are shown in the page; invalid saved garage data is not overwritten at startup.
- **State persistence** — guest garages and stars remain browser-local; signed-in profiles are saved to the account through `auth.js`/`profile_store.js`. UI preferences remain local
- **Local maintenance** — Python tools maintain JSON/Excel; the production account backend does not automatically apply score changes
- **Per-track top three** — expand the collapsed list below a selected track to see up to three owned cars from the current zone, using the current tier, stars and SC setting. Each track is ranked independently; other tracks do not reserve cars here. Normal/auto tiers retain candidate priority order, and missing scores show “暂无成绩”. Changing tracks collapses the list; garage and settings changes refresh its contents.

Static guest hosting needs no backend or database. Production accounts require a Python service, SQLite and SMTP. The frontend still needs no bundling step.

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
python -B -X utf8 -m unittest test_data_tools test_car_catalog test_release_tools -v      # data tools and validation
node --test test_allocator.js              # allocator boundary cases
node --test test_race_scores.js test_app_state.js            # score boundaries and page wiring
node test_boot_smoke.js                    # page boot smoke test (DOM stub, no browser)
```

As of 2026-10-03, 53 Python tests pass (one additional Linux symlink test is skipped on Windows), alongside 15 allocator, 11 scoring, 12 state tests and the boot smoke test; data validation reports zero errors.
The boot test uses a DOM stub and does not validate real-browser interaction or performance.

### Algorithm Notes

- **2026-10-11 exact pruning:** traversal, equal-vector assignments, sorting and truncation are unchanged. Reproducible real-page inputs, proof, full ordered comparisons, desktop Node/browser timings and limitations are in [perf/REPORT.md](perf/REPORT.md). Run `node --test test_allocator_pruning.js` and `node --expose-gc perf/benchmark.js`; open `perf/browser.html` through the local HTTP server for browser measurements. Tiny inputs can regress due to extra comparisons. The 2026-10-01 table below is historical, before branch pruning.

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
  Desktop browser algorithm measurements are now recorded separately in the report above; Node figures exclude page rendering and do not predict browser/mobile latency.
- Partial assignments: any slot may be left blank, and the blank branch is enumerated explicitly like
  any other. A blank costs the sentinel value (99), so when resources are plentiful blank schemes are
  always dominated and never appear on the front.
- `SCHEME_LIMIT` caps only schemes **returned/displayed**, not enumeration or the search-time front size.

---

## Deployment and Local Development

### Production Accounts Website

[RacePick](https://racepick.cn/) runs accounts, real email and submission review. It uses a separate production database and a loopback-only application listener behind Nginx HTTPS. systemd supplies credentials; secrets are not committed or bundled.

See [production deployment](PRODUCTION_DEPLOYMENT.md) for packaging, installation, owner bootstrap, backups and rollback. Use `build_production.py` and `deploy_production.py`: staging is the default, and application activation is separate from switching Nginx traffic. Do not upload local account databases or test workbooks to production.

### Local Account Development

```bash
python -m pip install -r backend/requirements.txt
python -B -m backend.app --port 8000
```

Open [127.0.0.1:8000](http://127.0.0.1:8000/). The default uses a separate local database and file-based test emails; SMTP testing is opt-in. See [ACCOUNTS_LOCAL.md](ACCOUNTS_LOCAL.md). This local entry point is not a public deployment command.

### Static Guest Version

The [GitHub Pages demo](https://testiphi.github.io/MutualExclusionAllocator/) provides static guest functionality. Deploy nine files: `index.html`, `styles.css`, `config.js`, `app_state.js`, `api.js`, `allocator.js`, `race_scores.js`, `gauntlet_data.json`, and `cars.json`. The vehicle rules in `cars.json` are a required dependency.

Static packaging and rollback are documented in [DEPLOYMENT.md](DEPLOYMENT.md), separately from production accounts. To preview the static version, run `python -m http.server 8000` and open [localhost:8000](http://localhost:8000/); accounts are not loaded. Use HTTP rather than opening the HTML directly, which may block JSON loading.

---

## Known Limitations & Future Directions

(Implemented features are no longer listed here; only items confirmed as unfinished.)

| Item | Status |
|------|--------|
| Solve performance | Conservative exact pruning is implemented; front scans still run on the main thread. Workers are not implemented. Repeated measurements and regressions are in perf/REPORT.md. |
| Browser-side stress test | Desktop Chromium solve time and timer delay measured with real page candidates. Phones, full-page interaction latency and peak memory remain untested. |
| Thin candidate lists | 13 "zone/tier" combinations are down to 1–2 candidates (weakest: `大桥海湾/喧闹铁路` four-zone expert has only `9x8★6`; `极昼之地/凌云狂飙` four-zone expert has only `ssc★2`). |
| Redundant `max` field | `star_rule.max` matches `cars.json`'s `max_stars` for all 9 cars that declare it (`att`/`杰弟`/`dose` use 6 = unconstrained). Whether to merge them is undecided. |

## Feature and Maintenance Documentation

| Document | Scope |
|---|---|
| [Production deployment and acceptance](PRODUCTION_DEPLOYMENT.md) | Live release, real email, backup, rollback and user acceptance |
| [Local accounts](ACCOUNTS_LOCAL.md) | Local startup, profile persistence and historical acceptance |
| [Email integration](MAIL_LOCAL.md) | File delivery, restricted SMTP tests and production integration |
| [Submissions and review](SUBMISSIONS_LOCAL.md) | Submission, follow-up, ratings, tier adjustment and feedback |
| [Administrator invitations](INVITATIONS_LOCAL.md) | Superadministrator, invitations and role isolation |
| [Read-only change previews](PREVIEWS_LOCAL.md) | Local only: additions, updates, slower results and ordinary mirrors |
| [Disposable writeback lab](WRITEBACK_LAB.md) | Local testing only: item confirmation, backup/rollback and workbook sync |
| [Data maintenance tools](PYTHON_TOOLS.md) | JSON/Excel maintenance, change review and validation |

New local phase: [versioned score data and release confirmation](SCORE_VERSIONS_LOCAL.md). An independent sandbox supports code/data separation, superadministrator item/slower approvals, backup and rollback. Not merged into main or enabled in production; existing workbooks are not synchronized automatically.

Production score-version migration is prepared in [SCORE_PRODUCTION_DEPLOYMENT.md](SCORE_PRODUCTION_DEPLOYMENT.md): preserve accounts, migrate read-only by default, rehearse coherent backup recovery, then enable writes separately. No live migration has been performed. The user has confirmed the first scheduled account backup succeeded.

## Account nicknames, shared buttons and private feedback (deployed)
Account nickname display/search, shared button styling and private text feedback are deployed and user-accepted in production. Feedback is visible only to its author and the superadministrator. Deployment, backup-drill and timer-restoration evidence is recorded in [feedback deployment notes](FEEDBACK_PRODUCTION.md); start future operations from the [cloud handoff](CLOUD_HANDOFF.md). The [local environment and acceptance steps](FEEDBACK_LOCAL.md) are retained. International-server support is outside this change.

## International mode accepted locally (2026-10-24)

The user accepted local international-mode testing: maximum-star five-zone theory, 321 independent score records, separate local garages, and OC selection. This release has not been deployed; international cloud profiles and submissions are not enabled. See [local acceptance and maintenance](LOCAL_INTERNATIONAL.md) and the [deployment preparation](INTERNATIONAL_DEPLOYMENT.md).
