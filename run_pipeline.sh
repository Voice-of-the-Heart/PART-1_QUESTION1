#!/usr/bin/env bash
# Runs the full SIA coverage-reconciliation pipeline end to end, from raw
# GPS track CSVs to final map/brief outputs. No manual intervention required
# beyond the one documented exception (see README.md, "Manual steps").
#
# Usage:
#   bash run_pipeline.sh
#
# Prerequisites:
#   - Python environment with requirements.txt installed
#   - data/reference/ populated (already committed -- small reference files)
#   - data/tracks/*.csv populated with raw <team_id>_<date>.csv track exports
#     (NOT committed to git -- see README.md for why)

set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/7 Ingest raw GPS tracks (idempotent) =="
python3 src/01_ingest_tracks.py

echo "== 2/7 Apply QA rule set =="
python3 src/02_qa_rules.py

echo "== 3/7 Attribute clean tracks to settlements =="
python3 src/03_attribute_settlements.py

echo "== 4/7 E-tally coverage + preliminary cluster analysis =="
python3 src/04_coverage_and_clusters.py

echo "== 5/7 Final GPS+e-tally corroborated reconciliation =="
python3 src/05_final_reconciliation.py

echo "== 6/7 A3 technical map =="
python3 src/06_make_a3_map.py

echo "== 7/7 One-page Incident Manager brief =="
python3 src/07_make_decision_brief.py

echo
echo "Done. Outputs written to output/."
