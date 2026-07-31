"""
Attribute cleaned GPS tracks to planned settlements ("was this settlement
visited?"), and roll up to settlement- and ward-level track-derived coverage.

METHOD: buffered proximity, not a settlement micro-grid.
A micro-grid (drawing an actual footprint polygon per settlement) needs
building-footprint or cadastral data we do not have; with only a settlement
centroid, a buffer around that point is the correct level of ambition and is
what NPHCDA/WHO M&E teams use in practice with point masterlists.

TOLERANCE: 150 m base radius, widened to 250 m in the urban LGA (Idi-Oro).
Justification (add in quadrature, not simple sum, since these are
independent, roughly Gaussian error sources):
  - GPS fix accuracy under open sky (rural):           ~8 m  (median accuracy_m)
  - Settlement masterlist point placement error:      ~50 m  (a hand/GPS-placed
    centroid for a village of houses spread over a few streets is not exact)
  - Team walking-path offset (teams cover the settlement, not stand on its
    centroid, so at some point in the visit the fix is 50-100 m away):  ~100 m
  sqrt(8^2 + 50^2 + 100^2) ~= 112 m -> rounded up to 150 m for a rural buffer.

URBAN / DENSE-AREA ADJUSTMENT: In Idi-Oro (urban), multipath reflection off
buildings degrades consumer GPS accuracy to 20-50 m (vs ~8 m in open rural
terrain), and settlements (wards/neighbourhoods) are closer together, so the
same 150 m buffer would both (a) under-attribute visits, because a genuinely
present team's fix bounces outside a tight radius, and (b) over-attribute,
because neighbouring settlement buffers overlap and a single fix could be
credited to the wrong one. We therefore: (1) widen the buffer to 250 m in
Idi-Oro to absorb multipath noise, and (2) break buffer-overlap ties by
nearest-centroid rather than "any buffer containing the point", so a fix in
an overlap zone is credited to the settlement it is physically closest to.
This trades a small amount of false-negative risk (a genuinely-visited but
very close neighbour occasionally not credited) for a much larger reduction
in false-positive risk (crediting a visit to a settlement the team never
actually reached), which is the safer error direction for coverage claims.

Run:  python 03_attribute_settlements.py
"""
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'utils'))
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from utm import latlon_to_utm
from config import DB_PATH, MASTERLIST_CSV, OUTPUT_DIR

RURAL_BUFFER_M = 150.0
URBAN_BUFFER_M = 250.0
URBAN_LGA_NAME = 'Idi-Oro'

# Only use points that passed QA (no flags at all) for the primary coverage
# claim; flagged points are reported separately as a lower-confidence layer
# rather than silently dropped, per the "flag, don't delete" rule.
CLEAN_ONLY_SQL = "SELECT team_id, campaign_date, timestamp, longitude, latitude FROM gps_tracks WHERE qa_flags IS NULL"

def main():
    con = sqlite3.connect(DB_PATH)
    try:
        tracks = pd.read_sql(CLEAN_ONLY_SQL, con)
    except Exception as e:
        print(f"Could not read QA-flagged tracks ({e}). This pack has no tracks/ "
              f"directory, so 01_ingest_tracks.py and 02_qa_rules.py have nothing to "
              f"process yet -- run them against a populated tracks/ directory first.")
        return
    if tracks.empty:
        print("No QA-clean track points available yet -- nothing to attribute.")
        return

    m = pd.read_csv(MASTERLIST_CSV)
    tx, ty = latlon_to_utm(tracks['latitude'].to_numpy(), tracks['longitude'].to_numpy())
    sx, sy = latlon_to_utm(m['latitude'].to_numpy(), m['longitude'].to_numpy())

    tree = cKDTree(np.column_stack([sx, sy]))
    dist, idx = tree.query(np.column_stack([tx, ty]), k=1)

    buffer_m = np.where(m['lga_name'].to_numpy()[idx] == URBAN_LGA_NAME, URBAN_BUFFER_M, RURAL_BUFFER_M)
    within = dist <= buffer_m

    visited_settlement_ids = set(m['settlement_id'].to_numpy()[idx[within]])
    m['track_visited'] = m['settlement_id'].isin(visited_settlement_ids)

    out = str(OUTPUT_DIR / 'settlement_track_visits.csv')
    m.to_csv(out, index=False)
    print(f"{within.sum()} / {len(tracks)} clean track points attributed within buffer "
          f"({m['track_visited'].sum()} / {len(m)} settlements track-confirmed visited).")
    print(f"Saved: {out}")

if __name__ == '__main__':
    main()
