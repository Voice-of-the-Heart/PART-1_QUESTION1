import sys, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'utils'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, FancyArrow
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.lines import Line2D
from gpkg_wkb import parse_gpkg_geom
from config import REFERENCE_DIR, OUTPUT_DIR, BOUNDARIES_GPKG

DATA = str(REFERENCE_DIR)
OUT = str(OUTPUT_DIR)

con = sqlite3.connect(str(BOUNDARIES_GPKG))
cur = con.cursor()

def load_layer(table, name_field):
    cur.execute(f"SELECT geom, {name_field} FROM {table}")
    feats = []
    for geom_blob, name in cur.fetchall():
        polys = parse_gpkg_geom(geom_blob)
        feats.append((polys, name))
    return feats

wards = load_layer('wards', 'ward_name')
lgas = load_layer('lgas', 'lga_name')

d = pd.read_csv(f'{OUT}/settlement_final_reconciliation.csv')
inacc_ids = set(d.loc[d['security_classification'] != 'Accessible', 'settlement_id'])

fig = plt.figure(figsize=(23.4, 16.5))  # A3 landscape at ~200dpi-equivalent inches (mm/25.4*... use inches directly)
# A3 = 420mm x 297mm = 16.54in x 11.69in; use landscape 16.54 x 11.69
fig = plt.figure(figsize=(16.54, 11.69))
ax = fig.add_axes([0.06, 0.08, 0.68, 0.86])   # main map
ax_leg = fig.add_axes([0.76, 0.08, 0.22, 0.86])  # side panel for legend/text
ax_leg.axis('off')

# --- ward boundaries (thin) ---
ward_patches = []
for polys, name in wards:
    for rings in polys:
        outer = rings[0]
        ward_patches.append(MplPolygon(outer, closed=True))
pc = PatchCollection(ward_patches, facecolor='none', edgecolor='#999999', linewidth=0.5, zorder=2)
ax.add_collection(pc)

# --- LGA boundaries (bold) ---
lga_patches = []
for polys, name in lgas:
    for rings in polys:
        outer = rings[0]
        lga_patches.append(MplPolygon(outer, closed=True))
pc2 = PatchCollection(lga_patches, facecolor='none', edgecolor='#222222', linewidth=1.8, zorder=3)
ax.add_collection(pc2)

# LGA labels at polygon centroid (simple average of outer ring)
for polys, name in lgas:
    outer = polys[0][0]
    xs = [p[0] for p in outer]; ys = [p[1] for p in outer]
    ax.text(np.mean(xs), np.mean(ys), name.upper(), fontsize=13, fontweight='bold',
            color='#333333', ha='center', va='center', zorder=4,
            bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=1))

# --- settlement points ---
reported = d[d['final_status'].isin(['Confirmed both sources', 'GPS only (unreported)'])]
missed_expl = d[(d['final_status'] == 'Missed both sources') & (d['security_classification'] != 'Accessible')]
missed_unexpl = d[(d['final_status'] == 'Missed both sources') & (d['security_classification'] == 'Accessible')]
sig = d[d['significant_HH_missed_both']]

ax.scatter(reported['longitude'], reported['latitude'], s=4, c='#2ca25f', alpha=0.5,
           label='Visited (e-tally and/or GPS)', zorder=5)
ax.scatter(missed_expl['longitude'], missed_expl['latitude'], s=14, c='#fdae61', marker='^',
           edgecolor='black', linewidth=0.3, label='Missed - classified inaccessible/partial', zorder=6)
ax.scatter(missed_unexpl['longitude'], missed_unexpl['latitude'], s=14, c='#d7191c', marker='o',
           edgecolor='black', linewidth=0.3, label='Missed - unexplained', zorder=6)
ax.scatter(sig['longitude'], sig['latitude'], s=110, facecolors='none', edgecolors='#7b0000',
           linewidth=1.6, label='Significant missed-settlement\ncluster (Local Moran\'s I, p<0.05)', zorder=7)

ax.set_xlim(d['longitude'].min() - 0.05, d['longitude'].max() + 0.05)
ax.set_ylim(d['latitude'].min() - 0.05, d['latitude'].max() + 0.05)
ax.set_aspect(1 / np.cos(np.radians(d['latitude'].mean())))

# coordinate grid
ax.grid(True, which='major', linestyle=':', linewidth=0.5, color='gray', zorder=1)
ax.set_xlabel('Longitude (°E)  —  WGS84 / EPSG:4326', fontsize=9)
ax.set_ylabel('Latitude (°N)  —  WGS84 / EPSG:4326', fontsize=9)
ax.tick_params(labelsize=8)

# north arrow
ax.annotate('N', xy=(0.955, 0.93), xytext=(0.955, 0.86), xycoords='axes fraction',
            fontsize=14, fontweight='bold', ha='center',
            arrowprops=dict(facecolor='black', width=3, headwidth=10, headlength=10))

# scale bar (approx, in km, using local latitude for deg->km conversion)
lat0 = d['latitude'].mean()
km_per_deg_lon = 111.32 * np.cos(np.radians(lat0))
bar_km = 20
bar_deg = bar_km / km_per_deg_lon
x0 = ax.get_xlim()[0] + 0.05
y0 = ax.get_ylim()[0] + 0.04
ax.plot([x0, x0 + bar_deg], [y0, y0], color='black', linewidth=3, zorder=8)
ax.text(x0 + bar_deg / 2, y0 + 0.015, f'{bar_km} km', ha='center', fontsize=9, zorder=8)

ax.set_title('BANSARA STATE SIA — MISSED SETTLEMENT CLUSTERS (e-TALLY DERIVED)\n'
             '9–13 March 2026  |  Idi-Oro, Gwarin, Katsuma, Ilela LGAs', fontsize=15, fontweight='bold', pad=12)

# --- side panel: legend + metadata block ---
handles = [
    Line2D([], [], marker='o', color='w', markerfacecolor='#2ca25f', markersize=7, label='Visited (e-tally and/or GPS)'),
    Line2D([], [], marker='^', color='w', markerfacecolor='#fdae61', markeredgecolor='black', markersize=8, label='Missed — classified\ninaccessible/partial'),
    Line2D([], [], marker='o', color='w', markerfacecolor='#d7191c', markeredgecolor='black', markersize=8, label='Missed — unexplained\n(no security reason on file)'),
    Line2D([], [], marker='o', color='w', markerfacecolor='none', markeredgecolor='#7b0000', markersize=12, markeredgewidth=1.8, label="Significant missed cluster\n(Local Moran's I, p<0.05)"),
    Line2D([], [], color='#222222', linewidth=1.8, label='LGA boundary'),
    Line2D([], [], color='#999999', linewidth=0.8, label='Ward boundary'),
]
leg = ax_leg.legend(handles=handles, loc='upper left', frameon=True, fontsize=9.5, title='LEGEND',
                     title_fontsize=11, handletextpad=1.0, labelspacing=1.3, borderpad=1.2)

meta_text = (
    "METHOD (UPDATED)\n"
    "'Missed' now requires BOTH no e-tally\n"
    "record AND no QA-clean GPS fix within\n"
    "the settlement buffer -- corroborated\n"
    "by two independent sources, not\n"
    "e-tally alone. 359/2524 settlements\n"
    "(14.2%) meet this stricter bar.\n\n"
    "METHOD\n"
    "Missed = no e-tally record AND no clean\n"
    "GPS fix within 150m(rural)/250m(urban)\n"
    "of the settlement centroid, out of 2,524\n"
    "planned settlements (38 duplicate\n"
    "masterlist records removed).\n"
    "Cluster statistic: Local Moran's I on the\n"
    "binary missed indicator, k=8 nearest-\n"
    "neighbour row-standardised weights,\n"
    "999-permutation pseudo p-values,\n"
    "significance at p<0.05, High-High only.\n\n"
    "DATA SOURCES\n"
    "settlement_masterlist.csv,\n"
    "etally_daily.csv,\n"
    "inaccessible_settlements.csv,\n"
    "boundaries.gpkg (Bansara State SIA\n"
    "data pack, synthetic).\n\n"
    "PROJECTION\n"
    "Geographic WGS84 (EPSG:4326) for display;\n"
    "UTM Zone 32N (EPSG:32632) used internally\n"
    "for all distance/nearest-neighbour\n"
    "calculations.\n\n"
    "AUTHOR / DATE\n"
    "Prepared for SIA coverage review\n"
    "31 July 2026\n\n"
    "SCALE\n"
    "Approx. 1:  see bar scale on map\n"
    "Sheet size: A3 (420 x 297 mm)"
)
ax_leg.text(0.0, -0.02, meta_text, fontsize=8.3, va='top', ha='left',
            transform=ax_leg.transAxes, family='monospace')

fig.savefig(f'{OUT}/A3_missed_settlement_clusters_FINAL.pdf', format='pdf')
print("Saved A3 map.")
