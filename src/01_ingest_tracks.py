"""
Idempotent ingestion of raw GPS track files into a single spatially-enabled store.

Reference implementation uses Python's built-in sqlite3 (always available, zero
install) so it runs anywhere. In a production deployment with network access,
swap the CREATE TABLE / INSERT statements below for:
  - PostGIS:  same schema, geometry column as `geometry(Point,4326)`, and
              `INSERT ... ON CONFLICT (team_id, timestamp) DO NOTHING`
  - DuckDB spatial: `INSTALL spatial; LOAD spatial;` then use ST_Point() and
              `INSERT OR IGNORE` / a MERGE statement
The idempotency mechanism (a deterministic primary key + INSERT OR IGNORE) is
identical in all three engines -- only the SQL dialect changes.

Expected input: DATA_DIR/tracks/<team_id>_<date>.csv, columns:
  team_id, logger_id, timestamp, longitude, latitude, accuracy_m, speed_kmh

Run:  python src/01_ingest_tracks.py
"""
import sys
import glob
import hashlib
import sqlite3
import csv
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DB_PATH, TRACKS_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS gps_tracks (
    point_id      TEXT PRIMARY KEY,   -- deterministic hash: team_id|logger_id|timestamp
    team_id       TEXT NOT NULL,
    logger_id     TEXT NOT NULL,
    campaign_date TEXT NOT NULL,      -- derived from source filename, not just timestamp,
                                       -- so a mis-set device clock cannot silently move a
                                       -- point into the wrong day's ingestion batch
    timestamp     TEXT NOT NULL,
    longitude     REAL NOT NULL,
    latitude      REAL NOT NULL,
    accuracy_m    REAL,
    speed_kmh     REAL,
    source_file   TEXT NOT NULL,
    ingested_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_tracks_team_day ON gps_tracks(team_id, campaign_date);
CREATE INDEX IF NOT EXISTS idx_tracks_ll ON gps_tracks(longitude, latitude);

CREATE TABLE IF NOT EXISTS ingestion_log (
    source_file   TEXT PRIMARY KEY,
    file_hash     TEXT NOT NULL,      -- content hash: lets us detect a *changed* file
                                       -- re-supplied under the same name, vs a harmless re-run
    rows_in_file  INTEGER,
    rows_inserted INTEGER,
    ingested_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS logger_timestamp_collisions (
    team_id          TEXT NOT NULL,
    logger_id        TEXT NOT NULL,
    timestamp        TEXT NOT NULL,
    n_distinct_fixes INTEGER,
    source_files     TEXT,
    PRIMARY KEY (team_id, logger_id, timestamp)
);
"""

def point_id(team_id, logger_id, timestamp, longitude, latitude):
    # NOTE: keying on (team_id, logger_id, timestamp) alone is NOT safe in this
    # data pack -- the same (team, logger, timestamp) triple recurs across
    # different source files with DIFFERENT coordinates (a real defect: the
    # logger_id is reused/clock-collides across days rather than being a
    # stable per-device-per-instant key). Keying on the full tuple including
    # position makes a genuine re-run of the same file idempotent (identical
    # row -> identical hash -> correctly ignored) while NOT silently discarding
    # a distinct, legitimate fix that merely shares team/logger/timestamp with
    # another. The collision itself is separately detected and logged below.
    key = f"{team_id}|{logger_id}|{timestamp}|{longitude}|{latitude}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]

def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def campaign_date_from_filename(path):
    # <team_id>_<YYYY-MM-DD>.csv
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.split('_', 1)[1]

def ingest():
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    files = sorted(glob.glob(str(TRACKS_DIR / '*.csv')))
    if not files:
        print(f"No files found under {TRACKS_DIR} -- nothing to ingest. "
              f"Populate data/tracks/ with the raw <team_id>_<date>.csv files first.")
        return
    total_inserted = 0
    for path in files:
        fname = os.path.basename(path)
        fhash = file_hash(path)
        prev = con.execute(
            "SELECT file_hash, rows_inserted FROM ingestion_log WHERE source_file=?", (fname,)
        ).fetchone()
        if prev and prev[0] == fhash:
            print(f"SKIP  {fname}: already ingested, unchanged (idempotent no-op)")
            continue
        if prev and prev[0] != fhash:
            print(f"WARN  {fname}: previously ingested but file content has changed "
                  f"since -- re-ingesting; old rows are NOT deleted automatically, "
                  f"review before trusting totals.")
        cdate = campaign_date_from_filename(path)
        rows_in_file = 0
        rows_inserted = 0
        with open(path, newline='') as f:
            reader = csv.DictReader(f)
            batch = []
            for row in reader:
                rows_in_file += 1
                pid = point_id(row['team_id'], row['logger_id'], row['timestamp'],
                               row['longitude'], row['latitude'])
                batch.append((
                    pid, row['team_id'], row['logger_id'], cdate, row['timestamp'],
                    float(row['longitude']), float(row['latitude']),
                    float(row['accuracy_m']) if row['accuracy_m'] not in ('', None) else None,
                    float(row['speed_kmh']) if row['speed_kmh'] not in ('', None) else None,
                    fname,
                ))
            cur = con.executemany(
                """INSERT OR IGNORE INTO gps_tracks
                   (point_id, team_id, logger_id, campaign_date, timestamp,
                    longitude, latitude, accuracy_m, speed_kmh, source_file)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                batch,
            )
            rows_inserted = cur.rowcount if cur.rowcount != -1 else len(batch)
        con.execute(
            """INSERT INTO ingestion_log (source_file, file_hash, rows_in_file, rows_inserted)
               VALUES (?,?,?,?)
               ON CONFLICT(source_file) DO UPDATE SET
                 file_hash=excluded.file_hash,
                 rows_in_file=excluded.rows_in_file,
                 rows_inserted=excluded.rows_inserted,
                 ingested_at=datetime('now')""",
            (fname, fhash, rows_in_file, rows_inserted),
        )
        con.commit()
        total_inserted += rows_inserted
        print(f"OK    {fname}: {rows_in_file} rows read, {rows_inserted} inserted")
    print(f"\nTotal newly inserted this run: {total_inserted}")
    n = con.execute("SELECT COUNT(*) FROM gps_tracks").fetchone()[0]
    print(f"Total rows now in gps_tracks: {n}")

    # --- detect (team_id, logger_id, timestamp) collisions: the same instant
    # recorded with DIFFERENT coordinates under the same team+logger. This is
    # not resolved automatically -- it is logged so it can be escalated to
    # whoever manages the logger fleet (reused device ID, clock fault, or a
    # device handed to a second team without re-registering it).
    con.execute("DELETE FROM logger_timestamp_collisions")
    con.execute("""
        INSERT INTO logger_timestamp_collisions
            (team_id, logger_id, timestamp, n_distinct_fixes, source_files)
        SELECT team_id, logger_id, timestamp,
               COUNT(DISTINCT longitude || ',' || latitude) AS n_distinct_fixes,
               GROUP_CONCAT(DISTINCT source_file)
        FROM gps_tracks
        GROUP BY team_id, logger_id, timestamp
        HAVING COUNT(DISTINCT longitude || ',' || latitude) > 1
    """)
    con.commit()
    n_collisions = con.execute("SELECT COUNT(*) FROM logger_timestamp_collisions").fetchone()[0]
    n_points_involved = con.execute(
        "SELECT SUM(n_distinct_fixes) FROM logger_timestamp_collisions"
    ).fetchone()[0] or 0
    print(f"\nQA FINDING: {n_collisions} (team, logger, timestamp) combinations map to "
          f"more than one distinct coordinate ({n_points_involved} genuinely distinct "
          f"fixes kept, none silently dropped). logger_id is therefore NOT a reliable "
          f"unique per-device key across this campaign -- see "
          f"logger_timestamp_collisions table / output/logger_collisions.csv, and "
          f"escalate to the logger fleet manager: likely cause is a physical device "
          f"reused across teams/days without being re-registered, or a clock fault.")
    import csv as _csv
    rows = con.execute(
        "SELECT team_id, logger_id, timestamp, n_distinct_fixes, source_files "
        "FROM logger_timestamp_collisions ORDER BY team_id, timestamp"
    ).fetchall()
    with open(str(DB_PATH.parent / 'logger_collisions.csv'), 'w', newline='') as f:
        w = _csv.writer(f)
        w.writerow(['team_id', 'logger_id', 'timestamp', 'n_distinct_fixes', 'source_files'])
        w.writerows(rows)

if __name__ == '__main__':
    ingest()
