import json, textwrap
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_DIR
OUT = str(OUTPUT_DIR)
stats = json.load(open(f'{OUT}/final_summary_stats.json'))
ward = pd.read_csv(f'{OUT}/ward_final_cluster_summary.csv')
top_wards = ward.sort_values(['n_sig_cluster', 'pct_missed_both'], ascending=False).head(6)

PAGE_W_IN = 8.27   # exact A4 width
PAGE_H_IN = 11.69  # exact A4 height
LEFT = 0.06
RIGHT = 0.95        # hard right boundary, in figure-fraction coords
AVAIL_IN = (RIGHT - LEFT) * PAGE_W_IN

fig = plt.figure(figsize=(PAGE_W_IN, PAGE_H_IN))
fig.suptitle('INCIDENT MANAGER BRIEF — SIA MOP-UP PRIORITISATION (FINAL)',
             fontsize=13.5, fontweight='bold', y=0.978)
fig.text(0.5, 0.955,
         'Bansara State, 9-13 March 2026 SIA  |  All 160 GPS track files + full e-tally  |  24-hour mop-up window',
         ha='center', fontsize=8.3, style='italic')

y = 0.935

def chars_per_line(fontsize, monospace=False):
    avg_char_w_in = (fontsize / 72.0) * (0.60 if monospace else 0.52)
    return max(20, int(AVAIL_IN / avg_char_w_in))

def line(txt, dy=0.0148, size=8.6, bold=False, monospace=False, indent=LEFT):
    global y
    width = chars_per_line(size, monospace=monospace)
    wrapped = textwrap.wrap(txt, width=width) if txt else ['']
    family = 'monospace' if monospace else 'sans-serif'
    for wline in wrapped:
        fig.text(indent, y, wline, fontsize=size, fontweight='bold' if bold else 'normal',
                  family=family, va='top')
        y -= dy
    return len(wrapped)

def gap(dy=0.006):
    global y
    y -= dy

line('1. SITUATION SUMMARY', size=10.5, bold=True, dy=0.020); gap()
line(f"Full reconciliation across all 32 teams' GPS tracks (929,733 raw points, 117,737 QA-clean) "
     f"against e-tally, for {stats['n_total_settlements']:,} planned settlements.")
gap()
line(f"{stats['n_confirmed_both']:,} settlements confirmed by BOTH e-tally and GPS. "
     f"{stats['n_gps_only_unreported']:,} were GPS-visited but never reported (a reporting gap, not an access "
     f"gap). {stats['n_etally_only']:,} were reported in e-tally with no surviving clean GPS fix nearby "
     f"(usually GPS data sparsity, not a false report).")
gap()
line(f"{stats['n_missed_both']:,} settlements ({stats['n_missed_both']/stats['n_total_settlements']:.1%}) have "
     f"NEITHER an e-tally record NOR a GPS-confirmed visit -- this is the corroborated, defensible missed list, "
     f"roughly half the size of the e-tally-only estimate from the earlier partial analysis.")
gap()
line(f"Local Moran's I on this corroborated indicator flags {stats['n_significant_HH_missed_both']} settlements "
     f"inside statistically significant missed-clusters (k=8 nearest-neighbour weights, 999 permutations, p<0.05).")
gap()
line(f"Team {stats['teams_with_gps_but_no_etally'][0]} has full GPS coverage (~3,400 points, all 5 days) but "
     f"ZERO e-tally rows anywhere in the campaign -- a missing paper-tally-sheet problem for one entire team, "
     f"not a missed-settlement problem.")
gap()
line("Okriba ward (Ilela) looked 100% missing from e-tally in the earlier partial view. With GPS, 32 of its 36 "
     "settlements are confirmed visited -- a reporting failure, not a coverage failure. Do not send a mop-up "
     "team there; send a data-reconciliation team instead.")
gap(0.012)

line('2. PRIORITY AREAS FOR THE NEXT 24 HOURS (corroborated missed clusters)', size=10.5, bold=True, dy=0.020)
gap(0.006)
line(f"{'Ward':<16}{'LGA':<10}{'Settlements':>12}{'Missed(both)':>14}{'Sig.cluster':>13}{'% missed':>10}",
     size=7.8, monospace=True, dy=0.0135)
for _, r in top_wards.iterrows():
    line(f"{r['ward_name']:<16}{r['lga_name']:<10}{r['n_settlements']:>12}{r['n_missed_both']:>14}"
         f"{r['n_sig_cluster']:>13}{r['pct_missed_both']*100:>9.0f}%", size=7.8, monospace=True, dy=0.0135)
gap()
line("The Katsuma cluster (Satide, Sashasa, Longoma, Sudefa, Suwade, Bazasa, Tasayi) is now the dominant, "
     "corroborated priority: all seven wards remain significant after requiring both sources to agree, meaning "
     "this is real geographic under-coverage, not a reporting artefact.")
gap()
line("Idi-Oro's flagged wards (Bishama, Satita, Okradu, Bayoyi) are lower-percentage and more scattered; check "
     "for buffer-overlap ties (urban 250m radius) before committing scarce mop-up capacity there ahead of "
     "Katsuma.")
gap(0.012)

line('3. RECOMMENDED ACTIONS (next 24 hours)', size=10.5, bold=True, dy=0.020); gap()
line("1. Deploy available mop-up capacity to the Katsuma cluster first -- it is the only LGA where the "
     "corroborated (not just e-tally) missed rate is both high and geographically concentrated.")
gap()
line("2. Contact Team T25's supervisor today for the missing paper tally sheets -- do not send a mop-up team "
     "anywhere on T25's route until it is confirmed whether settlements were actually missed or just "
     "unreported.")
gap()
line("3. Route the 149 statewide GPS-confirmed-but-unreported settlements to LGA data-entry teams for same-day "
     "tally reconciliation rather than mop-up.")
gap()
line("4. Re-verify security classification for the corroborated missed settlements not already on the "
     "inaccessible list before deploying teams.")
gap(0.012)

line('4. RISKS AND LIMITATIONS', size=10.5, bold=True, dy=0.020); gap()
line("Raw GPS timestamps have a severe, systemic defect: about 80% of all points carry a date outside the real "
     "5-day campaign window (files span up to 20 days beyond their filename date), so only about 13% of raw "
     "points survive QA. The corroborated missed list is the best available answer, not a fully GPS-verified "
     "one.")
gap()
line("A cluster finding is an area-level pattern only -- it does not confirm any single settlement was "
     "unvisited or that any individual child was missed.")
gap()
line("logger_id is reused across days without a stable per-device key (212,151 timestamp collisions resolved "
     "by keying on full fix content); flag to the logger fleet manager for the next round.")

fig.savefig(f'{OUT}/decision_brief_FINAL.pdf', format='pdf')
print(f"Saved. Final y position: {y:.3f} (must stay > 0 to fit one page)")
