# AI_USE.md

## Tool used

Claude (Anthropic), used interactively in a chat/code-execution session
across this project's entire development. No other AI tool was used.

## What it was used for

- **Code scaffolding and full implementation.** All Python in `src/` was
  written by Claude in an iterative, tool-using session (bash execution,
  file editing, direct inspection of the CSVs/GeoPackage), not hand-written
  by me and cleaned up afterward. This includes the ingestion pipeline, the
  QA rule implementation, the buffered-proximity attribution logic, the
  Local Moran's I cluster analysis, and the map/brief generation.
- **Substitute-library implementation.** The sandbox Claude was working in
  had no network access, so standard geospatial libraries
  (`geopandas`/`pyproj`/`shapely`/`duckdb`) could not be installed. Claude
  wrote `src/utils/gpkg_wkb.py` (a minimal GeoPackage WKB parser) and
  `src/utils/utm.py` (a pure-numpy UTM projection) from the GeoPackage
  binary spec and the standard Snyder UTM formula respectively, as
  functional substitutes. I reviewed both against the format spec and the
  formula before accepting them.
- **Data quality investigation.** Claude discovered, and I independently
  verified against the raw CSVs, several real defects: 38 duplicate
  settlement records in the masterlist, inconsistent `ward_name`
  spelling/case, a `logger_id` reuse defect causing 212,151
  same-key/different-coordinate collisions, and the dominant finding that
  ~81% of raw GPS timestamps fall outside the real 5-day campaign window.
  Claude proposed the detection logic and the fix in each case; I checked
  the underlying numbers (e.g. re-ran the raw `awk`/`grep` checks myself)
  before accepting the conclusion into the written response.
- **Debugging.** Two real bugs were caught and fixed during development: a
  `numpy.select` dtype error, and — more substantively — an initial
  ingestion key (`team_id, logger_id, timestamp`) that was silently
  dropping legitimate, distinct GPS fixes due to the logger-reuse defect
  above. That was caught by noticing an implausibly high "0 rows inserted"
  count on re-ingestion, not found by Claude proactively; once flagged,
  Claude diagnosed the cause and proposed the coordinate-inclusive key fix.
- **Document drafting.** `docs/WRITTEN_RESPONSE.md` (and its PDF render),
  `README.md`, `docs/QA_THRESHOLDS.md`, and this file were drafted by
  Claude and edited by me for accuracy and length.
- **Threshold justification framing.** The QA thresholds
  (speed/accuracy/duty-hours/gap/stationary) were proposed by Claude with
  first-principles justifications (device physics, campaign SOP,
  settlement spacing), then checked by me against the actual data
  distributions in `docs/QA_THRESHOLDS.md` before being finalised — in one
  case (positional accuracy) the real data distribution didn't match the
  "clean bimodal" assumption behind the threshold, and that mismatch is
  reported honestly in the write-up rather than the threshold being
  quietly loosened to hide it.

## What it was not used for

- Fabricating results: every number in the written response and the CSV/PDF
  outputs comes from an actual run of the pipeline against the supplied
  data, reproducible via `run_pipeline.sh`.
- Deciding the analytical approach unsupervised: the choice of Local
  Moran's I over Getis-Ord Gi*/SaTScan, the buffer-distance error budget,
  and the decision to require both-source corroboration for the final
  "missed" indicator were discussed and agreed with Claude's proposed
  reasoning, not accepted uncritically — I can defend each in the live
  walkthrough, including alternatives that were considered and not used.

## What I can defend live

I wrote none of the code character-by-character, but I ran it, broke it,
watched it fail, and worked through each fix and each data-quality finding
in real time rather than receiving a finished package. I can walk through
any script, explain why a given threshold or method was chosen over the
alternatives, and modify the pipeline live.
