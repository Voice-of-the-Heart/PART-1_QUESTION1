"""
STAGE 1-2  Idempotent ingestion + documented QA rule set.

Design notes (defend these in interview):
 * Idempotency is by CONTENT HASH, not by filename or row order. Each point gets
   point_uid = sha256(team|logger|timestamp|lon|lat|acc|speed). That is the natural
   key of an observation. INSERT OR IGNORE against a PRIMARY KEY makes re-running
   the loader a no-op. A load_manifest table stores the sha256 of each source file
   so an unchanged file is skipped entirely on re-run (cheap idempotency) while a
   CHANGED file is re-read and re-merged (correct idempotency).
 * QA rules FLAG in bit-columns; nothing is deleted. `qa_fail_mask` carries the
   hard-reject bits, `qa_warn_mask` the advisory bits. Analysts choose the gate.
"""
import hashlib, os, glob, sqlite3, struct, json
import numpy as np, pandas as pd
import geocore as gc

SRC = "Part1_Q1_Campaign_Tracking/"
GPKG = "outputs/campaign_tracks.gpkg"
UTM_ZONE = 32
EPSG_UTM = 32632
CAMPAIGN = ("2026-03-09", "2026-03-13")

# ---- QA rule bit definitions -------------------------------------------------
RULES = {
    "R1_date_overflow":   (1 << 0, "fail", "Timestamp outside the date asserted by the source filename"),
    "R2_exact_duplicate": (1 << 1, "fail", "Byte-identical repeat of an already-loaded observation"),
    "R3_null_island":     (1 << 2, "fail", "lon=0 and lat=0 sentinel; no position recorded"),
    "R4_coord_transpose": (1 << 3, "warn", "lon/lat transposed; repaired by swap, original retained"),
    "R5_outside_state":   (1 << 4, "fail", "Position outside Bansara State boundary"),
    "R6_impossible_speed":(1 << 5, "fail", "Reported or derived speed physically impossible on foot/road"),
    "R7_low_accuracy":    (1 << 6, "warn", "Reported positional accuracy worse than the stratum threshold"),
    "R8_accuracy_missing":(1 << 7, "warn", "accuracy_m null; quality of fix unverifiable"),
    "R9_outside_duty":    (1 << 8, "warn", "Fix outside 07:00-19:00 declared duty window"),
    "R10_seq_gap":        (1 << 9, "warn", "Preceding fix interval > 120 s (2x nominal 60 s epoch)"),
    "R11_partial_session":(1 << 10,"warn", "Team-day session < 50% of the fleet-median team-day fix count"),
    "R12_stationary":     (1 << 11,"warn", "Member of a stationary dwell cluster (accuracy-aware radius, >=10 min)"),
}
# ---- tunable gates, all justified from the observed distributions in this dataset
SPEED_GATE_KMH   = 120.0   # see writeup: any gate in 6-400 km/h flags the identical rows
ACC_GATE_M       = {"Urban": 60.0, "Mixed": 30.0, "Rural": 30.0}
DUTY_START, DUTY_END = 7, 19
GAP_GATE_S       = 120.0   # 2x the nominal 60 s logging epoch
PARTIAL_FRAC     = 0.50    # session shorter than half the fleet-median team-day
DWELL_MIN_MIN    = 10.0    # minimum plausible household-cluster working stop
DWELL_MIN_FIX    = 10
DWELL_RADIUS_MIN_M = 50.0
DWELL_ACC_MULT   = 2.0     # radius = max(50 m, 2 x median accuracy in the window)

FAIL_MASK = sum(b for b, k, _ in RULES.values() if k == "fail")


def sha_file(p, buf=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while (c := f.read(buf)):
            h.update(c)
    return h.hexdigest()


def point_uids(df):
    # NaN-safe: a null accuracy is itself part of the observation's identity and
    # must hash consistently rather than poisoning the key.
    def f(v):
        return "NA" if pd.isna(v) else f"{v:.6f}"
    key = (df.team_id.astype(str) + "|" + df.logger_id.astype(str) + "|" +
           df.timestamp.astype(str) + "|" + df.longitude.map(f) + "|" +
           df.latitude.map(f) + "|" + df.accuracy_m.map(f) + "|" + df.speed_kmh.map(f))
    return key.map(lambda s: hashlib.sha256(s.encode()).hexdigest()[:32])


# ---------------------------------------------------------------- GPKG writer
def gpkg_point_blob(x, y, srs_id):
    hdr = b"GP" + bytes([0, 0b0000_0001]) + struct.pack("<i", srs_id)   # no envelope, LE
    wkb = struct.pack("<BI2d", 1, 1, x, y)
    return hdr + wkb


def init_gpkg(path):
    if os.path.exists(path):
        os.remove(path)
    con = sqlite3.connect(path)
    con.executescript("""
    PRAGMA application_id=1196444487; PRAGMA user_version=10400;
    CREATE TABLE gpkg_spatial_ref_sys(srs_name TEXT NOT NULL,srs_id INTEGER PRIMARY KEY,
      organization TEXT NOT NULL,organization_coordsys_id INTEGER NOT NULL,definition TEXT NOT NULL,description TEXT);
    CREATE TABLE gpkg_contents(table_name TEXT PRIMARY KEY,data_type TEXT NOT NULL,identifier TEXT UNIQUE,
      description TEXT DEFAULT '',last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      min_x DOUBLE,min_y DOUBLE,max_x DOUBLE,max_y DOUBLE,srs_id INTEGER);
    CREATE TABLE gpkg_geometry_columns(table_name TEXT NOT NULL,column_name TEXT NOT NULL,
      geometry_type_name TEXT NOT NULL,srs_id INTEGER NOT NULL,z TINYINT NOT NULL,m TINYINT NOT NULL,
      CONSTRAINT pk_geom_cols PRIMARY KEY(table_name,column_name));
    """)
    for sid, org, oid, name in [(-1, "NONE", -1, "Undefined cartesian"), (0, "NONE", 0, "Undefined geographic"),
                                (4326, "EPSG", 4326, "WGS 84")]:
        con.execute("INSERT INTO gpkg_spatial_ref_sys VALUES(?,?,?,?,?,?)",
                    (name, sid, org, oid, "undefined" if sid < 4326 else
                     'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
                     'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]]', name))
    con.commit()
    return con


def register_layer(con, table, geom_col, gtype, srs, bounds):
    con.execute("INSERT OR REPLACE INTO gpkg_contents(table_name,data_type,identifier,min_x,min_y,max_x,max_y,srs_id)"
                " VALUES(?,'features',?,?,?,?,?,?)", (table, table, *bounds, srs))
    con.execute("INSERT OR REPLACE INTO gpkg_geometry_columns VALUES(?,?,?,?,0,0)", (table, geom_col, gtype, srs))


# ------------------------------------------------------------------- STAGE 1
def ingest(con):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS load_manifest(
      src_file TEXT PRIMARY KEY, file_sha256 TEXT NOT NULL, rows_in_file INT,
      rows_on_date INT, rows_overflow INT, loaded_at TEXT DEFAULT (datetime('now')));
    CREATE TABLE IF NOT EXISTS track_points(
      point_uid TEXT PRIMARY KEY, fid INTEGER, team_id TEXT, logger_id TEXT,
      ts TEXT, campaign_date TEXT, src_file TEXT, src_date TEXT,
      longitude REAL, latitude REAL, easting REAL, northing REAL,
      accuracy_m REAL, speed_kmh REAL, geom BLOB);
    """)
    files = sorted(glob.glob(SRC + "tracks/*.csv"))
    seen = dict(con.execute("SELECT src_file,file_sha256 FROM load_manifest").fetchall())
    frames, manifest, skipped = [], [], 0
    for f in files:
        b = os.path.basename(f)[:-4]
        sh = sha_file(f)
        if seen.get(b) == sh:                       # unchanged -> skip (idempotent fast path)
            skipped += 1
            continue
        df = pd.read_csv(f)
        df["src_file"] = b
        df["src_date"] = b.split("_")[1]
        ts = pd.to_datetime(df.timestamp, errors="coerce")
        df["cdate"] = ts.dt.date.astype(str)
        on = df.cdate == df.src_date
        manifest.append((b, sh, len(df), int(on.sum()), int((~on).sum())))
        # R1: slice to the date the filename asserts. Overflow is recorded in the
        # manifest (count preserved) but not loaded: overlapping files DISAGREE on
        # values for the same (team,timestamp), so concatenating them would corrupt.
        frames.append(df[on])
    if not frames:
        print(f"  ingest: nothing new ({skipped} files unchanged, skipped)")
        return 0
    d = pd.concat(frames, ignore_index=True)
    d["point_uid"] = point_uids(d)
    n_dup = int(d.point_uid.duplicated().sum())
    d = d.drop_duplicates("point_uid")
    d["easting"], d["northing"] = gc.to_utm(d.longitude, d.latitude, UTM_ZONE)
    rows = [(u, t, l, str(ts), cd, sf, sd, lo, la, e, n, a, s,
             gpkg_point_blob(lo, la, 4326))
            for u, t, l, ts, cd, sf, sd, lo, la, e, n, a, s in zip(
                d.point_uid, d.team_id, d.logger_id, d.timestamp, d.cdate, d.src_file,
                d.src_date, d.longitude, d.latitude, d.easting, d.northing,
                d.accuracy_m, d.speed_kmh)]
    cur = con.executemany(
        "INSERT OR IGNORE INTO track_points(point_uid,team_id,logger_id,ts,campaign_date,"
        "src_file,src_date,longitude,latitude,easting,northing,accuracy_m,speed_kmh,geom)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    inserted = con.total_changes
    con.executemany("INSERT OR REPLACE INTO load_manifest(src_file,file_sha256,rows_in_file,"
                    "rows_on_date,rows_overflow) VALUES(?,?,?,?,?)", manifest)
    con.execute("UPDATE track_points SET fid=rowid WHERE fid IS NULL")
    con.commit()
    print(f"  ingest: {len(files)} files, {skipped} skipped unchanged, "
          f"{len(d)+n_dup} on-date rows, {n_dup} exact duplicates collapsed, {len(d)} loaded")
    return len(d)


# ------------------------------------------------------------------- STAGE 2
def qa(con):
    d = pd.read_sql("SELECT * FROM track_points", con)
    d["ts"] = pd.to_datetime(d.ts)
    # Sort ONCE, up front: every sequence-dependent rule (speed, gaps, dwell) and the
    # mask array must share a single stable row order.
    d = d.sort_values(["team_id", "ts"]).reset_index(drop=True)
    n = len(d)
    mask = np.zeros(n, np.int64)
    counts = {}

    def hit(rule, cond):
        cond = np.asarray(cond, bool)
        mask[cond] |= RULES[rule][0]
        counts[rule] = int(cond.sum())

    # R1/R2 are enforced at ingest; recover their counts from the manifest.
    man = pd.read_sql("SELECT * FROM load_manifest", con)
    counts["R1_date_overflow"] = int(man.rows_overflow.sum())
    counts["R2_exact_duplicate"] = int(man.rows_on_date.sum() - n)

    # R3 null island
    ni = ((d.longitude == 0) & (d.latitude == 0)).values
    hit("R3_null_island", ni)

    # R4 transposed coordinates: outside the state bbox, but inside it when swapped.
    # Repaired rather than discarded - the observation is real, only the field order
    # is wrong, and the repair is verifiable (it lands inside the state polygon).
    _, gs = gc.read_gpkg_layer(SRC + "boundaries.gpkg", "state")
    x0, y0, x1, y1 = gc.bbox_layer(gs)
    inb = (d.longitude.between(x0, x1) & d.latitude.between(y0, y1)).values
    swp = ~inb & ~ni & d.latitude.between(x0, x1).values & d.longitude.between(y0, y1).values
    hit("R4_coord_transpose", swp)
    d.loc[swp, ["longitude", "latitude"]] = d.loc[swp, ["latitude", "longitude"]].values
    d.loc[swp, "easting"], d.loc[swp, "northing"] = gc.to_utm(
        d.loc[swp, "longitude"].values, d.loc[swp, "latitude"].values, UTM_ZONE)

    # R5 outside the state polygon, evaluated AFTER the R4 repair
    ins = gc.polys_contain(d.longitude.values, d.latitude.values, gs[0])
    hit("R5_outside_state", ~ins & ~ni)

    # R6 impossible speed, from TWO independent estimators: the logger's own speed
    # field and a speed derived from consecutive positions. Either one over the gate
    # fails the fix. The derived estimator is essential because a teleport corrupts
    # the segment into and out of the bad fix, which the logger field does not report.
    g = d.groupby(["team_id", "campaign_date"])
    dt = g.ts.diff().dt.total_seconds()
    dist = np.hypot(g.easting.diff(), g.northing.diff())
    d["derived_kmh"] = (dist / dt) * 3.6
    d["gap_s"] = dt
    hit("R6_impossible_speed",
        ((d.speed_kmh > SPEED_GATE_KMH) | (d.derived_kmh > SPEED_GATE_KMH)).fillna(False).values)

    # Assign LGA + settlement-density stratum once; several rules are stratified by it.
    al, gl = gc.read_gpkg_layer(SRC + "boundaries.gpkg", "lgas")
    d["lga_name"] = None; d["lga_type"] = None
    for at, pg in zip(al, gl):
        m = gc.polys_contain(d.longitude.values, d.latitude.values, pg)
        d.loc[m, "lga_name"] = at["lga_name"]; d.loc[m, "lga_type"] = at["lga_type"]

    # R7 accuracy, STRATIFIED. Rural loggers sit at ~8 m median, urban at ~34 m
    # because of multipath. A single global gate would delete most urban data and
    # silently zero out coverage in the highest-population LGA.
    gate = d.lga_type.map(ACC_GATE_M).fillna(30.0)
    hit("R7_low_accuracy", (d.accuracy_m > gate).fillna(False).values)
    hit("R8_accuracy_missing", d.accuracy_m.isna().values)

    # R9 duty window
    hr = d.ts.dt.hour
    hit("R9_outside_duty", ((hr < DUTY_START) | (hr >= DUTY_END)).values)

    # R10 sequence gaps beyond 2x the nominal 60 s epoch
    hit("R10_seq_gap", (d.gap_s > GAP_GATE_S).fillna(False).values)

    # R11 partial sessions, defined RELATIVE to the observed fleet median rather than
    # an absolute count, so the rule survives a change of logging epoch.
    sz = g.size().rename("nfix")
    d = d.merge(sz, left_on=["team_id", "campaign_date"], right_index=True, how="left")
    med = float(sz.median())
    hit("R11_partial_session", (d.nfix < PARTIAL_FRAC * med).values)

    # R12 stationary dwell clusters. The radius is ACCURACY-AWARE: with a 34 m median
    # accuracy in urban Idi-Oro, receiver jitter alone exceeds a fixed 50 m disc, so a
    # fixed radius would systematically fail to detect urban dwell and would bias
    # coverage downward exactly where the population is largest.
    d["dwell_id"] = -1
    dwell_rows = []
    for (tm, dy), grp in d.groupby(["team_id", "campaign_date"], sort=False):
        E = grp.easting.values; N = grp.northing.values; T = grp.ts.values
        A = pd.to_numeric(grp.accuracy_m).values
        i = 0; L = len(grp)
        while i < L:
            j = i + 1
            while j < L:
                sl = slice(i, j + 1)
                with np.errstate(all="ignore"):
                    r = np.nanmedian(A[sl]) if np.isfinite(A[sl]).any() else np.nan
                rad = max(DWELL_RADIUS_MIN_M, DWELL_ACC_MULT * (r if np.isfinite(r) else 10.0))
                if np.hypot(E[sl] - E[sl].mean(), N[sl] - N[sl].mean()).max() > rad:
                    break
                j += 1
            dur = (T[j - 1] - T[i]) / np.timedelta64(1, "m")
            if dur >= DWELL_MIN_MIN and j - i >= DWELL_MIN_FIX:
                did = len(dwell_rows)
                d.loc[grp.index[i:j], "dwell_id"] = did
                sl = slice(i, j)
                dwell_rows.append(dict(
                    dwell_id=did, team_id=tm, campaign_date=dy, n_fix=int(j - i),
                    dur_min=float(dur), start_ts=str(pd.Timestamp(T[i])),
                    end_ts=str(pd.Timestamp(T[j - 1])),
                    easting=float(E[sl].mean()), northing=float(N[sl].mean()),
                    spread_m=float(np.hypot(E[sl] - E[sl].mean(), N[sl] - N[sl].mean()).max()),
                    mean_acc=float(np.nanmean(A[sl])),
                    # standard error of the mean position: averaging n fixes shrinks
                    # ZERO-MEAN error by sqrt(n). This is what recovers usable urban
                    # precision without widening the attribution buffer.
                    sem_m=float((np.nanmean(A[sl]) if np.isfinite(np.nanmean(A[sl])) else 10.0)
                                / np.sqrt(j - i)),
                    lga_name=grp.lga_name.iloc[i] if i < len(grp) else None))
                i = j
            else:
                i += 1
    hit("R12_stationary", (d.dwell_id >= 0).values)
    m2 = mask
    dw = pd.DataFrame(dwell_rows)

    d["qa_mask"] = m2
    d["qa_fail"] = (m2 & FAIL_MASK) > 0

    # persist
    d.to_sql("track_points_qa", con, if_exists="replace", index=False)
    dw.to_sql("dwell_clusters", con, if_exists="replace", index=False)
    rep = pd.DataFrame([dict(rule=k, action=RULES[k][1], definition=RULES[k][2],
                             n_flagged=counts.get(k, 0)) for k in RULES])
    rep["pct_of_loaded"] = (rep.n_flagged / n * 100).round(3)
    rep.to_sql("qa_rule_report", con, if_exists="replace", index=False)
    con.commit()
    print(f"  QA: {n} loaded points, {int(d.qa_fail.sum())} hard-fail, "
          f"{n - int(d.qa_fail.sum())} analysis-ready, {len(dw)} dwell clusters")
    return d, dw, rep


if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    con = init_gpkg(GPKG)
    print("STAGE 1  ingest")
    ingest(con)
    print("  -- re-running ingest to prove idempotency --")
    ingest(con)
    n1 = con.execute("SELECT COUNT(*) FROM track_points").fetchone()[0]
    ingest(con)
    n2 = con.execute("SELECT COUNT(*) FROM track_points").fetchone()[0]
    print(f"  IDEMPOTENCY CHECK: {n1} -> {n2} rows after re-runs  "
          f"[{'PASS' if n1 == n2 else 'FAIL'}]")
    x0, y0, x1, y1 = (con.execute("SELECT MIN(longitude),MIN(latitude),MAX(longitude),"
                                  "MAX(latitude) FROM track_points").fetchone())
    register_layer(con, "track_points", "geom", "POINT", 4326, (x0, y0, x1, y1))
    con.commit()
    print("STAGE 2  QA")
    d, dw, rep = qa(con)
    print(rep.to_string(index=False))
    rep.to_csv("outputs/qa_rule_report.csv", index=False)
    con.close()
