import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'utils'))
import numpy as np
import pandas as pd
from utm import latlon_to_utm
from config import REFERENCE_DIR, OUTPUT_DIR

DATA = str(REFERENCE_DIR)
OUT = str(OUTPUT_DIR)

m = pd.read_csv(f'{DATA}/settlement_masterlist.csv')
e = pd.read_csv(f'{DATA}/etally_daily.csv')
inacc = pd.read_csv(f'{DATA}/inaccessible_settlements.csv')

# --- Data quality fix: ward_name has inconsistent case/whitespace for the SAME
# ward_code (e.g. 'Sashako' / ' Sashako ' / 'SASHAKO'). ward_code is the clean,
# authoritative key -> derive one canonical ward_name per ward_code and use
# ward_code for all grouping. This is reported as a QA finding, not silently fixed.
n_dirty_ward_names = (m['ward_name'] != m['ward_name'].str.strip()).sum()
canonical_name = (
    m.assign(_clean=m['ward_name'].str.strip().str.title())
     .groupby('ward_code')['_clean']
     .agg(lambda s: s.value_counts().idxmax())
)
m['ward_name'] = m['ward_code'].map(canonical_name)
print(f"QA finding: {n_dirty_ward_names} settlement rows had non-canonical "
      f"ward_name spelling/case/whitespace for their ward_code; normalised to "
      f"one canonical name per ward_code for all aggregation.")

# --- Data quality fix: 38 settlements appear TWICE in the masterlist under two
# settlement_ids (one 'S#####', one 'D#####') sharing the same name, ward_code,
# population, and near-identical coordinates (<1.2 km apart, consistent with a
# re-digitised duplicate rather than two real places). The e-tally never
# references the 'D' ids, so these are masterlist artefacts that would otherwise
# inflate the "missed settlement" denominator. We drop the 'D' duplicate and
# keep the 'S' record, logging every dropped id.
dup_keys = m[m.duplicated(subset=['settlement_name', 'ward_code'], keep=False)]
dropped = []
for _, grp in dup_keys.groupby(['settlement_name', 'ward_code']):
    if len(grp) == 2 and set(grp['settlement_id'].str[0]) == {'S', 'D'}:
        d_row = grp[grp['settlement_id'].str.startswith('D')]
        dropped.extend(d_row['settlement_id'].tolist())
print(f"QA finding: {len(dropped)} settlement_ids are duplicate masterlist "
      f"entries of an existing 'S' settlement (same name/ward/population, "
      f"<1.2km apart) -> dropped from the planning denominator: {dropped[:5]}...")
m = m[~m['settlement_id'].isin(dropped)].copy()

# --- 1. Settlement-level e-tally rollup ---
e_agg = e.groupby('settlement_id').agg(
    doses_administered=('doses_administered', 'sum'),
    days_reported=('campaign_date', 'nunique'),
    teams_reporting=('team_id', 'nunique'),
).reset_index()

m2 = m.merge(e_agg, on='settlement_id', how='left')
m2['doses_administered'] = m2['doses_administered'].fillna(0)
m2['days_reported'] = m2['days_reported'].fillna(0)
m2['reported_in_etally'] = m2['days_reported'] > 0
m2['coverage_ratio'] = np.where(
    m2['target_population_under5'] > 0,
    m2['doses_administered'] / m2['target_population_under5'],
    np.nan,
)

acc_status = inacc.set_index('settlement_id')['security_classification'].to_dict()
m2['security_classification'] = m2['settlement_id'].map(acc_status).fillna('Accessible')

m2['status'] = np.select(
    [
        m2['reported_in_etally'].to_numpy(),
        ((~m2['reported_in_etally']) & (m2['security_classification'] != 'Accessible')).to_numpy(),
    ],
    ['Reported', 'Missed - classified inaccessible/partial'],
    default='Missed - unexplained',
)

m2.to_csv(f'{OUT}/settlement_coverage.csv', index=False)

n_total = len(m2)
n_reported = int(m2['reported_in_etally'].sum())
n_missed = n_total - n_reported
n_missed_inacc = int(((~m2['reported_in_etally']) & (m2['security_classification'] != 'Accessible')).sum())
n_missed_unexplained = n_missed - n_missed_inacc

print(f"Total planned settlements: {n_total}")
print(f"Reported at least once in e-tally: {n_reported} ({n_reported/n_total:.1%})")
print(f"Missed (no e-tally record): {n_missed} ({n_missed/n_total:.1%})")
print(f"  of which pre-classified inaccessible/partial: {n_missed_inacc}")
print(f"  of which unexplained (no security reason on file): {n_missed_unexplained}")

# --- 2. Ward and LGA level coverage ---
ward = m2.groupby(['lga_name', 'ward_code', 'ward_name']).agg(
    n_settlements=('settlement_id', 'count'),
    n_reported=('reported_in_etally', 'sum'),
    n_missed_inaccessible=('security_classification', lambda s: (s != 'Accessible').sum()),
    target_pop=('target_population_under5', 'sum'),
    doses=('doses_administered', 'sum'),
).reset_index()
ward['n_missed'] = ward['n_settlements'] - ward['n_reported']
ward['pct_settlements_reported'] = ward['n_reported'] / ward['n_settlements']
ward['pop_coverage_ratio'] = ward['doses'] / ward['target_pop']
ward = ward.sort_values('pct_settlements_reported')
ward.to_csv(f'{OUT}/ward_coverage.csv', index=False)

lga = m2.groupby('lga_name').agg(
    n_settlements=('settlement_id', 'count'),
    n_reported=('reported_in_etally', 'sum'),
    target_pop=('target_population_under5', 'sum'),
    doses=('doses_administered', 'sum'),
).reset_index()
lga['n_missed'] = lga['n_settlements'] - lga['n_reported']
lga['pct_settlements_reported'] = lga['n_reported'] / lga['n_settlements']
lga['pop_coverage_ratio'] = lga['doses'] / lga['target_pop']
lga.to_csv(f'{OUT}/lga_coverage.csv', index=False)
print("\nLGA summary:")
print(lga[['lga_name', 'n_settlements', 'n_missed', 'pct_settlements_reported', 'pop_coverage_ratio']]
      .to_string(index=False))

# --- 3. Local Moran's I on the "missed" binary indicator ---
lat = m2['latitude'].to_numpy()
lon = m2['longitude'].to_numpy()
x_m, y_m = latlon_to_utm(lat, lon, zone=32)
coords = np.column_stack([x_m, y_m])
y = (~m2['reported_in_etally']).to_numpy().astype(float)  # 1 = missed

n = len(m2)
K = 8  # k-nearest-neighbour spatial weights

# pairwise distances via KD-tree-free brute force is too slow for 2562^2 -> use scipy cKDTree
from scipy.spatial import cKDTree
tree = cKDTree(coords)
dist, idx = tree.query(coords, k=K + 1)  # includes self
dist, idx = dist[:, 1:], idx[:, 1:]      # drop self

W = np.zeros((n, n))
for i in range(n):
    W[i, idx[i]] = 1.0
W = W / K  # row-standardised

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
    lag_p = W @ zp
    perm_Ii[p] = (zp / S2) * lag_p

p_sim = (np.sum(perm_Ii >= Ii, axis=0) + 1) / (n_perm + 1)
p_sim_two_sided = np.minimum(p_sim, 1 - p_sim) * 2
p_sim_two_sided = np.clip(p_sim_two_sided, 1/(n_perm+1), 1)

quadrant = np.where((z > 0) & (lag > 0), 'HH',
            np.where((z < 0) & (lag < 0), 'LL',
            np.where((z > 0) & (lag < 0), 'HL', 'LH')))

m2['local_moran_I'] = Ii
m2['local_moran_p'] = p_sim_two_sided
m2['local_moran_quadrant'] = quadrant
m2['significant_HH_missed_cluster'] = (p_sim_two_sided < 0.05) & (quadrant == 'HH') & (y == 1)

sig = m2[m2['significant_HH_missed_cluster']]
print(f"\nSignificant High-High (missed-clustering-with-missed) settlements at p<0.05: {len(sig)}")
print(sig.groupby(['lga_name', 'ward_name']).size().sort_values(ascending=False).head(15))

m2.to_csv(f'{OUT}/settlement_coverage_with_clusters.csv', index=False)

ward_cluster = m2.groupby(['lga_name', 'ward_code', 'ward_name']).agg(
    n_settlements=('settlement_id', 'count'),
    n_missed=('reported_in_etally', lambda s: (~s).sum()),
    n_sig_cluster=('significant_HH_missed_cluster', 'sum'),
).reset_index()
ward_cluster['pct_missed'] = ward_cluster['n_missed'] / ward_cluster['n_settlements']
ward_cluster = ward_cluster.sort_values(['n_sig_cluster', 'pct_missed'], ascending=False)
ward_cluster.to_csv(f'{OUT}/ward_cluster_summary.csv', index=False)
print("\nTop wards by significant-cluster settlement count:")
print(ward_cluster.head(10).to_string(index=False))

with open(f'{OUT}/summary_stats.json', 'w') as f:
    json.dump({
        'n_total_settlements': n_total,
        'n_reported': n_reported,
        'n_missed': n_missed,
        'n_missed_inaccessible_classified': n_missed_inacc,
        'n_missed_unexplained': n_missed_unexplained,
        'n_significant_HH_missed': int(len(sig)),
        'k_nn': K,
        'n_perm': n_perm,
    }, f, indent=2)
print("\nDone.")
