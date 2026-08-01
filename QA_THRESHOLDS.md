# QA rule set and threshold justification — GPS track cleaning

| Rule | Threshold | Justification |
|---|---|---|
| **Outside campaign window (checked first)** | date not in 2026-03-09 to 2026-03-13 flagged | Discovered empirically once real tracks were supplied: 81.2% of all points across T01-T03 carry a timestamp date outside the five real campaign days (one file spans 20 days beyond its own filename date). Checked before every other rule, since duty-hour/gap/stationary logic assumes the date is already correct. |
| Implausible speed | > 12 km/h flagged | House-to-house teams move on foot between compounds. Brisk walking is ~5-6 km/h; a loaded team rarely exceeds ~8 km/h even briefly. 12 km/h allows a short jog/lift without accepting vehicle-speed fixes (>20 km/h). Real data confirms a clean bimodal split: 95th percentile of in-window speeds is 5.6 km/h, 99th percentile jumps to 155 km/h. |
| Poor positional accuracy | > 30 m flagged | Consumer/handheld GPS loggers typically report 3-10 m accuracy under open sky. 30 m approaches the settlement-to-settlement spacing floor in this pack. Note: real in-window accuracy runs smoothly from ~5-57 m with no clean break, so this threshold (kept as an operational standard, not reverse-fitted) flags a larger share (~42%) than field experience with real hardware would suggest -- reported as-is rather than loosened to shrink the number. |
| Outside duty hours | before 07:00 or after 18:00 flagged | SIA field SOPs typically run 08:00-17:00; a 1-hour buffer either side covers muster/briefing and debrief. Real data shows hour-of-day is close to uniformly distributed even within the correct date window (~2,700 points every single hour, including 2-5 a.m.) -- a further sign the raw timestamps are not a trustworthy chronological record. |
| Gap in fix sequence | > 15 minutes between consecutive fixes flagged | Loggers record a fix roughly every 60 seconds. A gap beyond 15x that interval rules out routine signal flicker while still catching a lunch break, vehicle transfer, or device fault while diagnosable. |
| Stationary cluster | >= 8 minutes within a 15 m radius flagged | A team vaccinating house to house shows continuous small displacement. 15 m is roughly one compound/GPS-noise radius; 8+ minutes excludes normal in-compound registration/vaccination time (2-5 min/household) while catching loggers left at a rest point, vehicle, or team leader's house. |

**A second, independent equipment defect found on real ingestion:** the same
`(team_id, logger_id, timestamp)` triple recurs 77,877 times with
**different** coordinates -- `logger_id` is reused across a team's files with
no per-fix disambiguation. The ingestion primary key was corrected to include
coordinates so `INSERT OR IGNORE` cannot silently discard a legitimate,
distinct fix; the collisions themselves are logged to
`output/logger_collisions.csv` for escalation, since `logger_id` cannot be
trusted as a unique per-device key in this campaign.

**Principle applied throughout:** points are *flagged*, never deleted. The QA
column (`gps_tracks.qa_flags`) is additive (a point can carry more than one
flag) and every downstream step can choose which flags it tolerates — e.g.
the settlement-attribution step in `03_attribute_settlements.py` uses only
points with **zero** flags for the primary coverage claim, and reports
flagged-point volumes separately as a lower-confidence layer.

## Settlement attribution tolerance

**Method:** buffered proximity around the settlement masterlist point (not a
micro-grid — that needs building-footprint data this pack does not include).

**Rural buffer: 150 m.** Independent, roughly Gaussian error sources added in
quadrature: GPS accuracy (~8 m) + masterlist point-placement error (~50 m,
since a village centroid is not exact) + team walking-path offset within the
settlement (~100 m) → √(8²+50²+100²) ≈ 112 m, rounded up to 150 m.

**Urban buffer (Idi-Oro): 250 m.** Multipath reflection off buildings
degrades consumer GPS accuracy from ~8 m to 20–50 m in dense urban terrain,
and settlements/neighbourhoods sit closer together. The wider buffer absorbs
multipath noise; overlap ties between neighbouring buffers are broken by
nearest-centroid rather than "any buffer containing the point," trading a
small false-negative risk for a larger reduction in false-positive
(wrongly-credited) visits — the safer error direction for a coverage claim
used to plan mop-up.

## What track-vs-e-tally reconciliation is for

GPS proves physical presence at a location; the e-tally proves a dose was
recorded. They can and do diverge for reasons that are not mutually
exclusive: late/never-uploaded e-tally sheets, wrong-settlement selection on
the reporting tablet, a team present but a security incident cutting the
visit short, or (rarely) fabricated tally entries. Neither source should be
trusted blindly — both should be shown to the Incident Manager, with the
scale and direction of any mismatch reported so it can be investigated
rather than resolved by picking one number.
