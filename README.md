# Bansara State SIA — Coverage Reconciliation and Missed-Settlement Cluster Analysis

**Part 1, Question 1.** Reproducible pipeline for GPS-track ingestion, quality
assurance, settlement attribution, e-tally reconciliation, and missed-settlement
cluster analysis for a five-day house-to-house Supplementary Immunization
Activity (SIA) across four Local Government Areas in Bansara State.

All data used here is **synthetic**, supplied as an assessment data pack. No real
settlement, facility, campaign record or population appears in any file, and
nothing in this repository may be cited as evidence about any real programme.

## Deliverables

| Document | Location |
| --- | --- |
| Written assessment response | `docs/WRITTEN_RESPONSE.pdf` |
| A3 technical map | `docs/A3_missed_settlement_clusters_FINAL.pdf` |
| One-page Incident Manager brief | `docs/decision_brief_FINAL.pdf` |
| QA rule and threshold justification | `docs/QA_THRESHOLDS.md` |
| AI tool disclosure | `AI_USE.md` |

All are committed, so they can be reviewed without running the pipeline.
`results/` holds the reference CSV outputs from the authoring run.

## Requirements

**Python 3.10 or newer.** Dependencies are given as lower bounds in
`requirements.txt`; the analysis uses no version-specific APIs, so any recent
numpy/pandas/matplotlib/scipy will do.

## Reproducing the results

The data pack is **not committed** — it is supplied separately with the
assessment. Place it inside `data/` exactly as issued, without renaming or
restructuring it:

```
data/
└── Part1_Q1_Campaign_Tracking/     <- the pack, unmodified
    ├── tracks/                     <- 160 <team_id>_<date>.csv GPS exports
    ├── settlement_masterlist.csv
    ├── etally_daily.csv
    ├── inaccessible_settlements.csv
    └── boundaries.gpkg
```

Then:

```bash
git clone https://github.com/Voice-of-the-Heart/PART-1_QUESTION1.git
cd PART-1_QUESTION1

# macOS / Linux
python3 -m venv .venv && source .venv/bin/activate
# Windows (Git Bash)
py -m venv .venv && source .venv/Scripts/activate

pip install -r requirements.txt

ls data/Part1_Q1_Campaign_Tracking/tracks | wc -l   # must print 160
bash run_pipeline.sh                                 # or: make all
```

If the track count is not 160, stop — the pack is not in place, and the pipeline
will fail several stages later with an unhelpful error. Ingestion processes
roughly 956,000 raw GPS fixes and takes a few minutes.

If your pack sits elsewhere, edit `PACK_DIR` in `src/config.py`. That is the only
path setting the pipeline needs; every script derives its paths from it.

### Outputs

Everything is written to `output/`, which is gitignored:

| File | Contents |
| --- | --- |
| `campaign.sqlite` | full ingested, QA'd and rule-flagged track store |
| `settlement_final_reconciliation.csv` | settlement-level status combining GPS and e-tally evidence |
| `ward_final_cluster_summary.csv` | ward-level coverage and cluster summary |
| `A3_missed_settlement_clusters_FINAL.pdf` | A3 technical map |
| `decision_brief_FINAL.pdf` | one-page Incident Manager brief |
| plus per-stage intermediate CSVs | |

Re-running `bash run_pipeline.sh` is safe. Ingestion is idempotent: each source
file is content-hash checked, so a genuine re-run inserts zero new rows, and
every downstream stage recomputes cleanly from the current state of `output/`.

## Manual steps

**One step is not automated: placing the supplied data pack into `data/`.**

This is a data-provisioning step, not a processing step. The pack is issued with
the assessment and is not redistributed here; in production the equivalent files
arrive from outside the repository's control — a shared drive, an API pull from
the logger fleet's device-management system, or a manual upload — and different
environments source them differently. Automating that hand-off is an
infrastructure integration decision for whoever operates the pipeline, not
something this repository can responsibly assume.

The 160 track exports are also too bulky for version control: committing ~40 MB
of raw instrument output would burden every clone permanently, for data the
assessor already holds.

Everything downstream of that hand-off — ingestion, QA, attribution,
reconciliation, cluster analysis, map and brief generation — is fully scripted
and runs unattended via `run_pipeline.sh`. No source file is edited by hand at
any point; all defect handling is in code.

## Repository layout

```
├── data/                    # the supplied pack goes here, unmodified (gitignored)
├── src/
│   ├── config.py                    # all paths; edit PACK_DIR if the pack sits elsewhere
│   ├── utils/
│   │   ├── gpkg_wkb.py              # minimal GeoPackage WKB parser (no GDAL dependency)
│   │   └── utm.py                   # pure-numpy UTM Zone 32N projection (no pyproj dependency)
│   ├── 01_ingest_tracks.py          # idempotent raw-track ingestion into SQLite
│   ├── 02_qa_rules.py               # QA rule set (justified in docs/QA_THRESHOLDS.md)
│   ├── 03_attribute_settlements.py  # buffered-proximity settlement attribution
│   ├── 04_coverage_and_clusters.py  # e-tally-only coverage + preliminary Local Moran's I
│   ├── 05_final_reconciliation.py   # GPS + e-tally corroborated reconciliation + final clusters
│   ├── 06_make_a3_map.py            # A3 technical map (PDF)
│   └── 07_make_decision_brief.py    # one-page Incident Manager brief (PDF)
├── docs/                    # submitted deliverables (committed)
├── results/                 # reference CSV outputs from the authoring run (committed)
├── output/                  # regenerated by the pipeline (gitignored)
├── requirements.txt
├── run_pipeline.sh          # single entry point, stages 1-7 in order
├── Makefile                 # `make all` == run_pipeline.sh
├── AI_USE.md
└── README.md
```

`docs/` and `results/` hold artefacts that must survive a clone. `output/` holds
everything the pipeline rebuilds from scratch, and is deliberately ignored so a
stale generated file cannot be mistaken for a current one.

## Coordinate reference systems

Source data is supplied in **EPSG:4326** (WGS 84 geographic). Degrees are not a
metric unit, so every distance, buffer and nearest-neighbour operation is carried
out in **EPSG:32632** (WGS 84 / UTM Zone 32N) — the zone covering Bansara State's
7.0–8.5°E extent, which keeps scale distortion below 1 part in 2,500 across the
study area. The A3 map is displayed in geographic coordinates with a latitude
aspect correction; all measurement behind it is projected.

## Key design decisions

Full justification is in `docs/QA_THRESHOLDS.md` and `docs/WRITTEN_RESPONSE.pdf`.

- **Store:** SQLite (Python standard library, zero install, portable for review).
  The schema and the idempotency mechanism — a deterministic content-hash key
  plus `INSERT OR IGNORE` — carry over unchanged to PostGIS or DuckDB spatial;
  only the SQL dialect differs in a production deployment.

- **No GDAL / pyproj / shapely / geopandas dependency.** The analysis was built
  where those could not be installed, so `src/utils/gpkg_wkb.py` is a compact
  GeoPackage WKB parser and `src/utils/utm.py` a pure-numpy UTM Zone 32N forward
  projection (Snyder formula, WGS 84 ellipsoid). Both are drop-in replaceable by
  `geopandas` and `pyproj` where that stack is available.

- **QA rule set:** every threshold is justified from device physics, campaign
  SOP, or observed settlement spacing in `docs/QA_THRESHOLDS.md`, not fitted to
  the data. One rule (`outside_campaign_window`) was added after inspecting the
  pack: 81% of raw points carry a timestamp date outside the five-day campaign
  window, a systemic defect the original five-rule brief did not anticipate.
  Nothing is silently dropped — every rule flags, and the counts it flagged are
  reported.

- **Reconciliation:** the defensible "missed" indicator requires agreement of
  both e-tally absence **and** the absence of any QA-clean GPS fix within the
  settlement buffer. Where the two sources disagree, neither is treated as
  automatically authoritative; the disagreement is quantified and reported rather
  than resolved by assumption. See `src/05_final_reconciliation.py`.

- **Cartography:** the A3 sheet carries coordinate ticks on the neatline rather
  than an interior graticule, and derives every count from
  `settlement_final_reconciliation.csv` at render time, so the map cannot drift
  out of step with the analysis.
