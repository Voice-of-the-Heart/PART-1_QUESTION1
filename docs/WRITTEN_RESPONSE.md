---
title: "Bansara State SIA — Coverage Reconciliation and Missed-Settlement Cluster Analysis"
subtitle: "Written Response — Part 1, Question 1"
author: "GIS / Data Analyst Coordinator Assessment"
date: "31 July 2026"
geometry: margin=2.2cm
fontsize: 10pt
---

> **Note on page limit:** no page limit was stated in the requirements
> supplied to me. This response is deliberately kept to a working paper's
> length (~9 pages) rather than expanded to fill space — trim further to
> whatever explicit limit applies to your process. Full code, all
> intermediate CSVs, and the two final PDF outputs are in the repository;
> this document argues the design decisions, not repeats their code.

# 0. Data received and a scope note

The supplied pack contained `settlement_masterlist.csv` (2,562 rows),
`etally_daily.csv`, `inaccessible_settlements.csv`, `boundaries.gpkg`
(wards/LGAs/state polygons), and — across three later uploads — the full
160-file, 929,733-row raw GPS track set for all 32 teams. Every number
below is from an actual run of the pipeline in this repository
(`run_pipeline.sh`), not a hypothetical.

The environment this was built in had **no network access**, so
`geopandas`/`pyproj`/`shapely`/`duckdb` could not be installed. Two small
substitute modules were written instead: a ~60-line GeoPackage WKB parser
(`src/utils/gpkg_wkb.py`) and a pure-numpy UTM Zone 32N projection
(`src/utils/utm.py`, standard Snyder formula, WGS84 ellipsoid). Both are
drop-in replaceable by the standard stack if available; I did not use their
absence as a reason to skip the reprojection or the boundary rendering.

# 1. Reproducible ingestion pipeline

**Store:** SQLite (`output/campaign.sqlite`), chosen for zero-install
portability during review. The schema and idempotency mechanism are
identical in PostGIS or DuckDB spatial — only the SQL dialect changes for a
production deployment with network access to those engines (documented in
`src/01_ingest_tracks.py` header).

**Idempotency:** each row's primary key is a SHA-256 hash of
`team_id|logger_id|timestamp|longitude|latitude`, and ingestion uses
`INSERT OR IGNORE`. A per-file content hash (not just filename) is logged
in `ingestion_log`, so a genuine re-run inserts zero new rows, and a file
that changes content under the same name is detected and flagged rather
than silently skipped or silently overwritten. This was verified in
practice: re-running ingestion after adding new teams' files skipped every
previously-ingested file unchanged and only processed the new ones.

**A design decision I had to revisit:** the key above was not my first
attempt. I initially keyed on `team_id|logger_id|timestamp` alone. On first
real ingestion, a large fraction of rows silently returned "0 inserted" —
which turned out to mean the key was colliding: the same
`(team, logger, timestamp)` triple recurs **212,151 times** across this
dataset with **different** coordinates, because `logger_id` is reused per
team across all its files with no per-fix disambiguation. The original key
was therefore discarding real, distinct GPS fixes. I include the
coordinates in the key now (§ above) and log every collision to
`output/logger_collisions.csv` instead — a finding to escalate to the
logger fleet manager, not a bug to hide.

# 2. QA rule set and thresholds

Six rules, applied in order, each threshold justified from first
principles (not fitted to the data) and documented in full in
`docs/QA_THRESHOLDS.md`. Points are **flagged, never deleted** — every raw
row and its flags remain in `gps_tracks.qa_flags` for audit.

| Rule | Threshold | Points flagged (of 929,733) |
|---|---|---:|
| **Outside campaign window** (checked first) | date ∉ [2026-03-09, 2026-03-13] | 633,207 (68.1%) |
| Poor positional accuracy | > 30 m | 379,335 (40.8%) |
| Outside duty hours | before 07:00 / after 18:00 | 475,158 (51.1%) |
| Implausible speed | > 12 km/h | 4,568 (0.5%) |
| Stationary cluster | ≥ 8 min within 15 m | 11,535 (1.2%) |
| Sequence gap | > 15 min to next fix | 88 (<0.1%) |
| **Any flag (union)** | | **811,996 (87.3%)** |

**The dominant finding is the first rule, and it was not in the original
five-rule brief.** Checking the *date* portion of every timestamp against
the real campaign window shows 68–81% of points (rate varies slightly by
team batch) are dated outside the five real days — one file named
`T01_2026-03-09.csv` contains fixes timestamped up to `2026-03-29`, twenty
days past its own filename date, and every file shows the same pattern:
daily point counts form a smooth bell curve peaking mid-campaign and
tapering at both ends. That shape is far too smooth and too large to be
"logger left on overnight" drift; it is much more consistent with five
overlapping exports of one long continuous per-team trace, each mislabelled
with a single day. I added this as the first-checked rule because every
other rule (duty hours, gaps, stationary clusters) assumes the date is
already trustworthy.

Two further observations from the genuinely in-window subset reinforce
this is a real data defect, not noise: hour-of-day is close to **uniformly
distributed** even within the correct dates (~equal counts in every single
hour, including 2–5 a.m.), which real fieldwork does not produce; and
accuracy runs smoothly from ~5–57 m with no clean bimodal break, so the
30 m threshold (kept as an operational standard tied to settlement
spacing, not reverse-fitted) flags a larger share of this dataset than
field experience with real consumer GPS hardware would predict — reported
as-is rather than loosened to produce a smaller, more flattering number.

**Net effect:** 117,737 of 929,733 points (12.7%) pass every rule and are
used for attribution. This is the honest cost of the defect above, not a
tuning failure — loosening thresholds to raise this number would not fix
timestamps that are outside the campaign entirely.

# 3. Settlement attribution

**Method:** buffered proximity around the settlement masterlist centroid,
not a micro-grid (a footprint-level grid needs building-footprint data this
pack does not include, so a centroid buffer is the appropriate level of
ambition for a point masterlist).

**Rural tolerance: 150 m**, from an error budget added in quadrature
(independent, roughly Gaussian sources): GPS accuracy (~8 m) + masterlist
point-placement error (~50 m) + team walking-path offset within the
settlement (~100 m) → √(8²+50²+100²) ≈ 112 m, rounded up to 150 m.

**Urban tolerance (Idi-Oro): 250 m.** Multipath reflection off buildings
degrades consumer GPS accuracy from ~8 m to 20–50 m in dense terrain, and
settlements sit closer together. I widen the buffer to absorb multipath
noise, and break overlap ties by **nearest centroid** rather than "any
buffer containing the point" — trading a small false-negative risk (an
adjacent, genuinely-visited settlement occasionally not credited) for a
larger reduction in false-positive risk (crediting a visit the team never
made). That is the safer error direction for a coverage claim used to plan
mop-up deployment.

Only QA-clean points (zero flags) feed attribution — 20,858 of 117,737
clean points fell within a settlement buffer, confirming 1,278 of 2,562
settlements as track-visited.

# 4. Coverage and reconciliation

**Denominator correction first.** The raw masterlist has two defects,
found and corrected before any coverage math: 38 settlements duplicated
under a second `settlement_id` (same name/ward/population, coordinates
within ~1.2 km — a re-digitisation artefact, confirmed by checking that
e-tally never references the duplicate IDs), and inconsistent `ward_name`
spelling/case for the same `ward_code` (normalised to one canonical name
per code). True denominator: **2,524 settlements**.

**The reconciliation that matters is the one requiring both sources to
agree**, not e-tally alone:

| Status | Settlements | % |
|---|---:|---:|
| Confirmed both sources | 1,113 | 44.1% |
| E-tally only (no clean GPS fix nearby) | 903 | 35.8% |
| GPS only (visited, never reported) | 149 | 5.9% |
| **Missed both sources** | **359** | **14.2%** |

That 14.2% corroborated missed-rate — not the 20.1% e-tally-only figure
from an earlier partial run — is the number I would present to an Incident
Manager, and here is why: absence of an e-tally record is **weak**
evidence on its own, because most e-tally-only "missed" settlements simply
have no surviving clean GPS fix nearby, given how much data the timestamp
defect removes (§2) — not because the team skipped them. Presence of a
clean GPS fix inside a settlement's buffer is **strong** evidence, so the
149 GPS-confirmed-but-unreported settlements are the more actionable class:
proven presence, no dose record, consistent with a team that visited but
didn't submit or submitted against the wrong settlement — the specific
"present but unreported" failure mode a reconciliation exercise exists to
surface.

**Two findings this resolved, one it surfaced:**

- **Okriba ward** looked 100% missing from e-tally alone (all 36
  settlements, no security flag) — the strongest possible signal of a
  systemic reporting failure rather than 36 independent misses. GPS
  confirms this directly: 32 of 36 settlements are track-visited. Do not
  send a mop-up team to Okriba; send a data-reconciliation team.
- **Team T25** has full, normal-density GPS tracks for all five days
  (~3,400 points) but **zero e-tally rows anywhere in the campaign**. A
  single missing paper-tally-sheet problem for one team, not a
  settlement-coverage problem, and the cheapest finding in this analysis
  to act on.
- **Katsuma LGA's under-coverage survives corroboration** — it was already
  the state's worst LGA on e-tally alone and remains the dominant,
  statistically significant cluster once GPS evidence is required too
  (§5). This is the one finding I would treat as genuine geographic
  under-coverage rather than a reporting artefact.

Ward/LGA-level tables: `output/ward_final_cluster_summary.csv`,
`output/lga_coverage.csv`. Settlement-level final status:
`output/settlement_final_reconciliation.csv`.

# 5. Missed-settlement cluster analysis

**Statistic:** Local Moran's I (local indicator of spatial association) on
the binary "missed both sources" variable from §4 — the corroborated
indicator, not e-tally-missed alone, since a spatial statistic run on a
weaker signal produces a weaker conclusion.

**Spatial weights:** k-nearest-neighbour, k=8, row-standardised, on
coordinates reprojected to UTM Zone 32N (the state spans 6.95–8.43°E,
entirely inside zone 32N, so a single zone introduces no material
distortion). k-NN over a fixed-distance threshold because settlement
density varies sharply between urban Idi-Oro and the rural wards — a
fixed-distance rule would give urban settlements far denser neighbourhoods
than rural ones, while k-NN holds neighbour count comparable everywhere.

**Significance:** conditional permutation, 999 randomisations per
settlement, two-sided pseudo p-value, significance at p<0.05, High-High
quadrant only (a missed settlement surrounded by other missed settlements,
more than chance predicts).

**Result:** 87 settlements sit inside significant HH clusters, concentrated
almost entirely in **Katsuma LGA** — Satide, Sashasa, Longoma, Sudefa,
Suwade, Bazasa, and Tasayi wards all remain significant after requiring
both e-tally and GPS to agree the settlement was missed, which is the bar
that distinguishes a real geographic gap from a reporting artefact.

**What this does not license:**

- It does not mean every settlement inside a flagged cluster was
  individually missed for the same reason — the variable being clustered
  is "no confirming evidence from either source," not a certified
  non-visit, and evidence absence and true non-visit are not identical.
- It says nothing about individual children within any settlement — the
  statistic operates on settlements as spatial units.
- A cluster is a pattern, not a cause. Team non-deployment, tablet
  misreporting, security access, and genuine non-coverage can all produce
  the same spatial signature; the statistic cannot distinguish between
  them, and field verification is still required before acting on any
  single settlement.

# 6. Outputs

- **A3 technical map** (`output/A3_missed_settlement_clusters_FINAL.pdf`):
  ward/LGA boundaries parsed directly from `boundaries.gpkg`, settlements
  classified visited / missed (explained by security classification) /
  missed (unexplained), significant-cluster settlements ringed, legend,
  north arrow, scale bar, coordinate grid, data sources, projection note,
  and the corroboration method printed on the sheet itself.
- **One-page Incident Manager brief**
  (`output/decision_brief_FINAL.pdf`): situation summary, ranked priority
  wards, 24-hour recommended actions, risks and limitations — written for
  a reader with no GIS background and 24 hours to act, not as a shorter
  version of this document.

Both were regenerated after an initial layout defect: several bullet lines
in the first brief draft ran past the page's right margin because
`matplotlib`'s `fig.text()` does not wrap automatically. I added explicit
text-wrapping sized to the actual page width and verified the fix
programmatically — by rendering the figure and checking every text
element's bounding box stays inside the page, not just by eye — before
accepting it as fixed.

# 7. Limitations, honestly stated

- The corroborated missed-list (§4) is the best available answer given the
  timestamp defect in §2, not a fully GPS-verified one. If the raw export
  is corrected at source, re-running `run_pipeline.sh` unchanged would
  sharpen every number here.
- `logger_id` cannot be treated as a stable per-device key in this
  campaign (§1); any downstream device-level analysis needs that fixed
  first.
- One step is genuinely manual: placing raw track files into
  `data/tracks/` before running the pipeline (README.md, "Manual steps").
  Everything after that hand-off is scripted and unattended.
