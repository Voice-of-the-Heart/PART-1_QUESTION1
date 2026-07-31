"""
QA rule set for raw GPS track points, run against the gps_tracks table
populated by 01_ingest_tracks.py. Every threshold is justified below and
in QA_THRESHOLDS.md; rows are FLAGGED (qa_flags column), never deleted,
per the "do not delete records you cannot explain" instruction in the
data pack README.

Run:  python 02_qa_rules.py
"""
import sqlite3
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DB_PATH

# ---------------------------------------------------------------------------
# THRESHOLDS -- see QA_THRESHOLDS.md for full justification of each number
# ---------------------------------------------------------------------------
MAX_PLAUSIBLE_SPEED_KMH = 12.0
# House-to-house teams move on foot between compounds, not along a road
# network. Brisk walking is ~5-6 km/h; a loaded team carrying a cool box
# rarely sustains more than ~8 km/h even briefly. 12 km/h gives headroom for
# a short jog or a lift between two very close points without accepting
# vehicle-speed fixes (>20 km/h) that indicate the logger was in a moving
# vehicle, i.e. not actively vaccinating.

MAX_ACCURACY_M = 30.0
# Consumer/handheld GPS loggers under open sky typically report 3-10 m
# accuracy (CEP). 30 m is roughly the settlement-to-settlement spacing floor
# in the rural wards in this pack (median inter-settlement nearest-neighbour
# distance, computed from settlement_masterlist.csv) -- beyond that, a fix
# cannot be reliably assigned to one settlement over its neighbour, so it is
# flagged as "positionally unusable" rather than trusted for attribution.

CAMPAIGN_START_DATE = '2026-03-09'
CAMPAIGN_END_DATE = '2026-03-13'
# Distinct from the duty-hours rule below: this catches a fix whose DATE falls
# outside the five real campaign days entirely, regardless of time of day.
# Discovered empirically: in the supplied tracks/, several team-day files
# contain timestamps ranging up to ~20 days beyond their own filename date
# (e.g. a file named T01_2026-03-09.csv contains fixes dated up to
# 2026-03-29), and 81% of all ingested points across T01-T03 fall outside
# 2026-03-09 to 2026-03-13. This is far too large and too smoothly
# distributed across ~21 days to be stray overnight drift -- it indicates a
# logger clock/export fault (or, in this synthetic pack, a deliberately
# planted defect) that must be screened before any duty-hour or
# duplicate-check logic is applied, since those rules assume the date is
# already correct.

DUTY_START_HOUR = 7   # 07:00
DUTY_END_HOUR = 18    # 18:00
# SIA duty hours in the field SOP are typically 08:00-17:00; a one-hour
# buffer on each side (07:00-18:00) allows for muster/briefing before the
# official start and end-of-day debrief/travel, while still catching
# points logged overnight (device left on, stored in a bag, etc.) which is
# the actual failure mode this rule targets.

MAX_GAP_MINUTES = 15
# Loggers record a fix roughly every 60 seconds per the README. A single
# missed fix or brief GPS drop under tree cover is normal; a gap beyond
# 15 minutes (i.e. ~15x the expected interval) is treated as a break in the
# fix sequence worth flagging -- long enough to rule out routine signal
# flicker, short enough to still catch a lunch break, vehicle transfer, or
# device fault while it is still diagnosable.

STATIONARY_RADIUS_M = 15.0
STATIONARY_MIN_MINUTES = 8
# A team vaccinating house to house should show continuous small
# displacement. A cluster of fixes all within 15 m (roughly one
# compound/GPS-noise radius) for 8+ minutes is flagged as "stationary" --
# long enough to exclude normal in-compound registration/vaccination time
# (typically 2-5 minutes per household) but short enough to catch loggers
# left at a rest point, vehicle, or team leader's house.

QA_TABLE_SETUP = """
ALTER TABLE gps_tracks ADD COLUMN qa_flags TEXT;
"""

def add_qa_column(con):
    try:
        con.execute(QA_TABLE_SETUP)
    except sqlite3.OperationalError:
        pass  # column already exists -- keeps this script idempotent too

def run_qa(con):
    add_qa_column(con)
    con.execute("UPDATE gps_tracks SET qa_flags = NULL")  # recompute cleanly each run

    rows = con.execute(
        "SELECT point_id, team_id, campaign_date, timestamp, longitude, latitude, "
        "accuracy_m, speed_kmh FROM gps_tracks ORDER BY team_id, timestamp"
    ).fetchall()
    if not rows:
        print("gps_tracks is empty -- run 01_ingest_tracks.py against a populated "
              "tracks/ directory first.")
        return

    flags = {r[0]: [] for r in rows}
    counts = {'outside_campaign_window': 0, 'implausible_speed': 0, 'poor_accuracy': 0,
              'outside_duty_hours': 0, 'sequence_gap': 0, 'stationary_cluster': 0}

    # Rule 0 (checked first): date outside the real 5-day campaign window
    for r in rows:
        pid = r[0]
        date = r[3][:10]
        if date < CAMPAIGN_START_DATE or date > CAMPAIGN_END_DATE:
            flags[pid].append('outside_campaign_window')
            counts['outside_campaign_window'] += 1

    # Rule 1 & 2: speed and accuracy are per-point, already computed upstream
    # by the logger, or can be recomputed from consecutive fixes -- here we
    # trust the logger-reported speed_kmh/accuracy_m fields per the schema.
    for r in rows:
        pid, team, date, ts, lon, lat, acc, spd = r
        if spd is not None and spd > MAX_PLAUSIBLE_SPEED_KMH:
            flags[pid].append('implausible_speed')
            counts['implausible_speed'] += 1
        if acc is not None and acc > MAX_ACCURACY_M:
            flags[pid].append('poor_accuracy')
            counts['poor_accuracy'] += 1
        hour = int(ts[11:13])
        if hour < DUTY_START_HOUR or hour >= DUTY_END_HOUR:
            flags[pid].append('outside_duty_hours')
            counts['outside_duty_hours'] += 1

    # Rule 4: sequence gaps, per team-day, using consecutive timestamp deltas
    import itertools
    from datetime import datetime
    def key(r): return (r[1], r[2])
    for (team, date), grp in itertools.groupby(sorted(rows, key=key), key=key):
        grp = sorted(grp, key=lambda r: r[3])
        for a, b in zip(grp, grp[1:]):
            t1 = datetime.strptime(a[3], '%Y-%m-%d %H:%M:%S')
            t2 = datetime.strptime(b[3], '%Y-%m-%d %H:%M:%S')
            gap_min = (t2 - t1).total_seconds() / 60
            if gap_min > MAX_GAP_MINUTES:
                flags[b[0]].append('sequence_gap_start')
                counts['sequence_gap'] += 1

    # Rule 5: stationary clusters, per team-day, simple rolling-window check
    R = 6371000.0
    def haversine_m(lat1, lon1, lat2, lon2):
        p1, p2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlmb = np.radians(lon2 - lon1)
        a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
        return 2 * R * np.arcsin(np.sqrt(a))

    for (team, date), grp in itertools.groupby(sorted(rows, key=key), key=key):
        grp = sorted(grp, key=lambda r: r[3])
        i = 0
        while i < len(grp):
            j = i
            while j + 1 < len(grp) and haversine_m(
                grp[i][5], grp[i][4], grp[j + 1][5], grp[j + 1][4]
            ) <= STATIONARY_RADIUS_M:
                j += 1
            t1 = datetime.strptime(grp[i][3], '%Y-%m-%d %H:%M:%S')
            t2 = datetime.strptime(grp[j][3], '%Y-%m-%d %H:%M:%S')
            if (t2 - t1).total_seconds() / 60 >= STATIONARY_MIN_MINUTES:
                for k in range(i, j + 1):
                    flags[grp[k][0]].append('stationary_cluster')
                counts['stationary_cluster'] += (j - i + 1)
            i = j + 1 if j > i else i + 1

    con.executemany(
        "UPDATE gps_tracks SET qa_flags = ? WHERE point_id = ?",
        [(','.join(sorted(set(v))) if v else None, k) for k, v in flags.items()],
    )
    con.commit()

    print("QA rule results (points flagged; a point may carry >1 flag):")
    for rule, n in counts.items():
        print(f"  {rule:<22}: {n}")
    total_points = len(rows)
    total_flagged = sum(1 for v in flags.values() if v)
    print(f"\n{total_flagged} / {total_points} points ({total_flagged/total_points:.1%}) "
          f"carry at least one QA flag. None were deleted -- all flags are stored "
          f"in gps_tracks.qa_flags for the attribution step to consume.")

if __name__ == '__main__':
    con = sqlite3.connect(DB_PATH)
    run_qa(con)
