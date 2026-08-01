import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'utils'))
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from utm import latlon_to_utm
from config import OUTPUT_DIR, ETALLY_CSV

OUT = str(OUTPUT_DIR)

cov = pd.read_csv(f'{OUT}/settlement_coverage_with_clusters.csv')   # deduped, 2524 settlements
tv = pd.read_csv(f'{OUT}/settlement_track_visits.csv')              # raw masterlist, 2562 rows

d = cov.merge(tv[['settlement_id', 'track_visited']], on='settlement_id', how='left')
d['track_visited'] = d['track_visited'].fillna(False)

def status(r):
    if r['reported_in_etally'] and r['track_visited']:
        return 'Confirmed both sources'
    if r['reported_in_etally'] and not r['track_visited']:
        return 'E-tally only'
    if (not r['reported_in_etally']) and r['track_visited']:
        return 'GPS only (unreported)'
    return 'Missed both sources'

d['final_status'] = d.apply(status, axis=1)
print(d['final_status'].value_counts())
print()

# e-tally lists 31 teams (T01-T24, T26-T32); T25 never appears at all -- flag explicitly
import pandas as pd
e = pd.read_csv(ETALLY_CSV)
all_teams = set(f"T{n:02d}" for n in range(1, 33))
reporting_teams = set(e.team_id.unique())
missing_teams = sorted(all_teams - reporting_teams)
print(f"Teams with GPS tracks but ZERO e-tally rows anywhere in the campaign: {missing_teams}")

d.to_csv(f'{OUT}/settlement_final_reconciliation.csv', index=False)

# --- Re-run Local Moran's I on "Missed both sources" -- the properly
# corroborated missed indicator, now that GPS covers effectively the whole
# state (only settlements with neither an e-tally record nor a QA-clean GPS
# fix nearby count as missed).
lat = d['latitude'].to_numpy()
lon = d['longitude'].to_numpy()
x_m, y_m = latlon_to_utm(lat, lon, zone=32)
coords = np.column_stack([x_m, y_m])
y = (d['final_status'] == 'Missed both sources').to_numpy().astype(float)

n = len(d)
K = 8
tree = cKDTree(coords)
dist, idx = tree.query(coords, k=K + 1)
idx = idx[:, 1:]

W = np.zeros((n, n))
for i in range(n):
    W[i, idx[i]] = 1.0
W = W / K

y_bar = y.mean()
z = y - y_bar
S2 = (z ** 2).sum() / n
lag = W @ z
Ii = (z / S2) * lag

rng = np.random.default_rng(42)
n_perm = 999
perm_Ii = np.zeros((n_perm, n))
for p in range(n_perm):
    zp = rng.permutation(z)
    perm_Ii[p] = (zp / S2) * (W @ zp)

p_sim = (np.sum(perm_Ii >= Ii, axis=0) + 1) / (n_perm + 1)
p_two = np.clip(np.minimum(p_sim, 1 - p_sim) * 2, 1 / (n_perm + 1), 1)
quadrant = np.where((z > 0) & (lag > 0), 'HH', np.where((z < 0) & (lag < 0), 'LL',
            np.where((z > 0) & (lag < 0), 'HL', 'LH')))

d['local_moran_I_final'] = Ii
d['local_moran_p_final'] = p_two
d['significant_HH_missed_both'] = (p_two < 0.05) & (quadrant == 'HH') & (y == 1)

n_missed_both = int(y.sum())
n_sig = int(d['significant_HH_missed_both'].sum())
print(f"\nSettlements missed by BOTH e-tally and GPS: {n_missed_both} / {n} ({n_missed_both/n:.1%})")
print(f"Of those, in a statistically significant HH cluster (p<0.05): {n_sig}")

ward_final = d.groupby(['lga_name', 'ward_code', 'ward_name']).agg(
    n_settlements=('settlement_id', 'count'),
    n_missed_both=('final_status', lambda s: (s == 'Missed both sources').sum()),
    n_sig_cluster=('significant_HH_missed_both', 'sum'),
).reset_index()
ward_final['pct_missed_both'] = ward_final['n_missed_both'] / ward_final['n_settlements']
ward_final = ward_final.sort_values(['n_sig_cluster', 'pct_missed_both'], ascending=False)
ward_final.to_csv(f'{OUT}/ward_final_cluster_summary.csv', index=False)
print("\nTop wards, corroborated missed-settlement clusters:")
print(ward_final.head(12).to_string(index=False))

d.to_csv(f'{OUT}/settlement_final_reconciliation.csv', index=False)

with open(f'{OUT}/final_summary_stats.json', 'w') as f:
    json.dump({
        'n_total_settlements': int(n),
        'n_confirmed_both': int((d['final_status'] == 'Confirmed both sources').sum()),
        'n_etally_only': int((d['final_status'] == 'E-tally only').sum()),
        'n_gps_only_unreported': int((d['final_status'] == 'GPS only (unreported)').sum()),
        'n_missed_both': n_missed_both,
        'n_significant_HH_missed_both': n_sig,
        'teams_with_gps_but_no_etally': missing_teams,
    }, f, indent=2)
print("\nSaved settlement_final_reconciliation.csv, ward_final_cluster_summary.csv, final_summary_stats.json")
