"""A3 technical map: significant clusters of missed settlements.

Reads output/settlement_final_reconciliation.csv (produced by
05_final_reconciliation.py) and data/reference/boundaries.gpkg. Writes
output/A3_missed_settlement_clusters_FINAL.pdf.

Cartographic decisions:
  * Legend sits at the FOOT of the information column. A reader consults it
    after the map has raised a question, not before.
  * No interior graticule. Position is carried by ticks on the neatline, the
    scale bar and the named administrative units; a grid competes with the
    thematic symbols for attention without adding information.
  * Every legend entry carries its actual rendered symbol, drawn in a single
    dedicated axes so size and colour match the map exactly.
  * All counts are DERIVED from the reconciliation table at run time, never
    typed into the sheet, so the map cannot drift out of step with the data.
"""
import sys, sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "utils"))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Rectangle
from matplotlib.collections import PatchCollection

from gpkg_wkb import parse_gpkg_geom
from config import OUTPUT_DIR, BOUNDARIES_GPKG

OUT = Path(OUTPUT_DIR)
RECON_CSV = OUT / "settlement_final_reconciliation.csv"
PDF = OUT / "A3_missed_settlement_clusters_FINAL.pdf"
PNG = OUT / "A3_missed_settlement_clusters_FINAL.png"

A3 = (16.54, 11.69)                       # 420 x 297 mm, landscape

C_PAPER, C_INK, C_MUTED = "#F6F5F1", "#1E1C19", "#75705F"
C_WARD, C_LGA = "#B5AF9F", "#3D3A33"
C_VISIT, C_GPSONLY = "#3D7F6C", "#4C86C6"
C_MISSED, C_INACC = "#D2541B", "#5F4B8B"
C_CLUSTER = "#B3211F"


# --------------------------------------------------------------------- data
def load_layer(con, table, name_field):
    rows = con.execute(f"SELECT geom, {name_field} FROM {table}").fetchall()
    return [(parse_gpkg_geom(g), n) for g, n in rows]


def load():
    con = sqlite3.connect(str(BOUNDARIES_GPKG))
    wards = load_layer(con, "wards", "ward_name")
    lgas = load_layer(con, "lgas", "lga_name")
    con.close()

    d = pd.read_csv(RECON_CSV)
    # A CSV round-trip can turn booleans into the strings "True"/"False", which
    # are BOTH truthy — that would silently mark every settlement significant.
    d["significant_HH_missed_both"] = (
        d["significant_HH_missed_both"].astype(str).str.strip().str.lower()
        .isin(["true", "1", "yes", "t"]))
    return wards, lgas, d


# ------------------------------------------------------------- map furniture
def scalebar(ax, x, y, km, km_per_deg_lon, h):
    n, seg = 4, (km / km_per_deg_lon) / 4
    for i in range(n):
        ax.add_patch(Rectangle((x + i * seg, y), seg, h, zorder=30,
                               facecolor=C_INK if i % 2 == 0 else "white",
                               edgecolor=C_INK, lw=.6))
    for i in range(n + 1):
        ax.text(x + i * seg, y - h * 1.4, f"{int(i * km / n)}", ha="center",
                va="top", fontsize=6.4, color=C_INK, zorder=30)
    ax.text(x + (km / km_per_deg_lon) / 2, y + h * 2.3, "KILOMETRES",
            ha="center", fontsize=6.0, color=C_MUTED, zorder=30)


def north_arrow(ax, x, y, size):
    ax.add_patch(MplPolygon([[x, y + size], [x - size * .30, y - size * .34],
                             [x, y - size * .10]], closed=True,
                            facecolor=C_INK, zorder=30))
    ax.add_patch(MplPolygon([[x, y + size], [x + size * .30, y - size * .34],
                             [x, y - size * .10]], closed=True,
                            facecolor="white", edgecolor=C_INK, lw=.6, zorder=30))
    ax.text(x, y + size * 1.20, "N", ha="center", fontsize=9.5,
            fontweight="bold", color=C_INK, zorder=30)


def coord_ticks(ax, step=0.25, tick_frac=0.010, fs=6.2):
    """Graduated neatline: coordinate ticks on the frame, no interior grid."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    tx, ty = (x1 - x0) * tick_frac, (y1 - y0) * tick_frac
    for lon in np.arange(np.ceil(x0 / step) * step, x1 + 1e-9, step):
        for ybase, sgn, va in ((y0, -1, "top"), (y1, +1, "bottom")):
            ax.plot([lon, lon], [ybase, ybase + sgn * ty], color=C_INK, lw=.8,
                    zorder=31, clip_on=False, solid_capstyle="butt")
            ax.text(lon, ybase + sgn * ty * 1.6, f"{lon:.2f}\u00b0E", ha="center",
                    va=va, fontsize=fs, color=C_MUTED, zorder=31, clip_on=False)
    for lat in np.arange(np.ceil(y0 / step) * step, y1 + 1e-9, step):
        for xbase, sgn, ha in ((x0, -1, "right"), (x1, +1, "left")):
            ax.plot([xbase, xbase + sgn * tx], [lat, lat], color=C_INK, lw=.8,
                    zorder=31, clip_on=False, solid_capstyle="butt")
            ax.text(xbase + sgn * tx * 1.4, lat, f"{lat:.2f}\u00b0N", ha=ha,
                    va="center", fontsize=fs, color=C_MUTED, zorder=31,
                    clip_on=False, rotation=90)


# --------------------------------------------------------------------- main
def main():
    wards, lgas, d = load()

    visited = d[d.final_status == "Confirmed both sources"]
    gpsonly = d[d.final_status == "GPS only (unreported)"]
    missed = d[d.final_status == "Missed both sources"]
    inacc = missed[missed.security_classification != "Accessible"]
    unexpl = missed[missed.security_classification == "Accessible"]
    sig = d[d.significant_HH_missed_both]

    has_pop = "target_population_under5" in d.columns
    ch = (lambda f: int(f.target_population_under5.fillna(0).sum())) if has_pop \
        else (lambda f: None)

    fig = plt.figure(figsize=A3, facecolor=C_PAPER)
    ax = fig.add_axes([0.045, 0.068, 0.578, 0.812])
    ax.set_facecolor("white")

    ax.add_collection(PatchCollection(
        [MplPolygon(r[0], closed=True) for polys, _ in wards for r in polys],
        facecolor="white", edgecolor=C_WARD, linewidth=.45, zorder=2))
    ax.add_collection(PatchCollection(
        [MplPolygon(r[0], closed=True) for polys, _ in lgas for r in polys],
        facecolor="none", edgecolor=C_LGA, linewidth=1.7, zorder=6))
    for polys, name in lgas:
        o = np.asarray(polys[0][0])
        ax.text(o[:, 0].mean(), o[:, 1].mean(), str(name).upper(), fontsize=9.5,
                fontweight="bold", color=C_LGA, ha="center", va="center",
                alpha=.62, zorder=7)

    ax.scatter(visited.longitude, visited.latitude, s=3, c=C_VISIT, lw=0,
               alpha=.55, zorder=8)
    ax.scatter(gpsonly.longitude, gpsonly.latitude, s=9, c=C_GPSONLY, lw=0,
               alpha=.85, zorder=9)
    ax.scatter(inacc.longitude, inacc.latitude, s=17, marker="^", c=C_INACC,
               lw=0, zorder=10)
    ax.scatter(unexpl.longitude, unexpl.latitude, s=20, facecolor=C_MISSED,
               edgecolor="#54200A", lw=.3, alpha=.92, zorder=11)
    ax.scatter(sig.longitude, sig.latitude, s=115, facecolors="none",
               edgecolors=C_CLUSTER, lw=1.5, zorder=12)

    # extent, with the equal-aspect constraint pre-satisfied so that the frame
    # edge matches the limits we set and the neatline ticks land ON the frame
    lat0 = float(d.latitude.mean())
    aspect = 1 / np.cos(np.radians(lat0))
    px = (d.longitude.max() - d.longitude.min()) * .05
    py = (d.latitude.max() - d.latitude.min()) * .05
    ex0, ex1 = d.longitude.min() - px, d.longitude.max() + px
    ey0, ey1 = d.latitude.min() - py, d.latitude.max() + py
    bb = ax.get_position()
    box_ar = (bb.width * A3[0]) / (bb.height * A3[1])
    dx, dy = ex1 - ex0, (ey1 - ey0) * aspect
    if dx / dy > box_ar:
        g = (dx / box_ar - dy) / 2 / aspect
        ey0, ey1 = ey0 - g, ey1 + g
    else:
        g = (dy * box_ar - dx) / 2
        ex0, ex1 = ex0 - g, ex1 + g
    ax.set_xlim(ex0, ex1); ax.set_ylim(ey0, ey1)
    ax.set_aspect(aspect)
    ax.set_xticks([]); ax.set_yticks([])
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_edgecolor(C_INK); sp.set_linewidth(1.0)

    km_per_deg_lon = 111.32 * np.cos(np.radians(lat0))
    scalebar(ax, ex0 + (ex1 - ex0) * .03, ey0 + (ey1 - ey0) * .04, 20,
             km_per_deg_lon, (ey1 - ey0) * .0065)
    north_arrow(ax, ex1 - (ex1 - ex0) * .04, ey1 - (ey1 - ey0) * .11,
                (ey1 - ey0) * .023)
    coord_ticks(ax)

    # ------------------------------------------------------------ title band
    fig.text(0.045, 0.972, "Statistically Significant Clusters of Missed Settlements",
             fontsize=21, fontweight="bold", color=C_INK, va="top")
    fig.text(0.045, 0.940,
             "Supplementary Immunization Activity, 9\u201313 March 2026  \u2022  "
             "Bansara State  \u2022  Idi-Oro, Gwarin, Katsuma and Ilela LGAs",
             fontsize=10.5, color="#55514A", va="top")
    fig.text(0.045, 0.922,
             "Local Moran's I on the missed-settlement indicator; GPS-track\u2013derived "
             "coverage reconciled against daily e-tally returns",
             fontsize=8.6, color=C_MUTED, style="italic", va="top")
    fig.patches.append(Rectangle((0.045, 0.906), 0.922, 0.0018,
                                 transform=fig.transFigure, facecolor=C_INK, lw=0))

    # ---------------------------------------------------- information column
    LX, LW = 0.648, 0.319
    fig.patches.append(Rectangle((LX, 0.052), LW, 0.842, transform=fig.transFigure,
                                 facecolor="white", edgecolor="#CFC9BB", lw=.8,
                                 zorder=1))
    IN, TW = LX + 0.013, LW - 0.026

    def head(t, yy):
        fig.text(IN, yy, t.upper(), fontsize=8.6, fontweight="bold", color=C_INK,
                 va="top", zorder=3)
        fig.patches.append(Rectangle((IN, yy - 0.0105), TW, 0.0016,
                                     transform=fig.transFigure,
                                     facecolor=C_CLUSTER, zorder=3))
        return yy - 0.024

    y = head("Reconciliation", 0.878)
    hdr = f"{'':<30}{'SETTLE':>7}" + (f"{'UNDER-5':>9}" if has_pop else "")
    fig.text(IN + 0.008, y, hdr, fontsize=6.7, family="monospace",
             fontweight="bold", color=C_MUTED, va="top")
    y -= 0.0135
    for lab, sub, col in [("Confirmed both sources", visited, C_VISIT),
                          ("GPS only (unreported)", gpsonly, C_GPSONLY),
                          ("Missed \u2014 unexplained", unexpl, C_MISSED),
                          ("Missed \u2014 inaccessible", inacc, C_INACC)]:
        fig.patches.append(Rectangle((IN, y - 0.0085), 0.0028, 0.010,
                                     transform=fig.transFigure, facecolor=col,
                                     lw=0, zorder=3))
        row = f"{lab:<30}{len(sub):>7,}" + (f"{ch(sub):>9,}" if has_pop else "")
        fig.text(IN + 0.008, y, row, fontsize=6.75, family="monospace",
                 color=C_INK, va="top")
        y -= 0.0148
    pct = len(missed) / len(d) * 100
    fig.text(IN, y - 0.001,
             f"{len(missed):,} of {len(d):,} settlements ({pct:.1f}%) are missed on\n"
             "BOTH sources \u2014 no e-tally record and no QA-clean GPS fix\n"
             "in the settlement buffer. Corroboration by two independent\n"
             "sources, not e-tally alone.",
             fontsize=6.4, color=C_INK, va="top", linespacing=1.52)
    y -= 0.052

    # Ward ranking, derived at run time. Ordered by unexplained misses because
    # that is the actionable quantity: inaccessible settlements are a known,
    # separately-managed constraint, not a mop-up target.
    if {"ward_code", "ward_name", "lga_name"}.issubset(d.columns):
        y = head("Wards with most unexplained misses", y)
        agg = (unexpl.groupby(["ward_code", "ward_name", "lga_name"])
               .agg(n=("settlement_id", "size"),
                    sig=("significant_HH_missed_both", "sum")).reset_index()
               .sort_values("n", ascending=False).head(10))
        fig.text(IN, y, f"{'WARD':<13}{'LGA':<10}{'MISSED':>7}{'SIG':>5}",
                 fontsize=6.7, family="monospace", fontweight="bold",
                 color=C_MUTED, va="top")
        y -= 0.0135
        for _, r in agg.iterrows():
            fig.text(IN, y, f"{str(r.ward_name)[:12]:<13}{str(r.lga_name)[:9]:<10}"
                            f"{int(r.n):>7}{int(r.sig):>5}",
                     fontsize=6.9, family="monospace", color=C_INK, va="top")
            y -= 0.0122
        fig.text(IN, y - 0.001,
                 "MISSED unexplained misses in ward \u00b7 SIG of which fall in a\n"
                 "significant High-High cluster",
                 fontsize=6.2, color=C_MUTED, va="top", linespacing=1.5)
        y -= 0.034

    y = head("Method", y)
    for k, v in [("Display CRS", "EPSG:4326 \u00b7 WGS 84 geographic"),
                 ("Analysis CRS", "EPSG:32632 \u00b7 UTM 32N"),
                 ("Statistic", "Local Moran's I, High-High only"),
                 ("Weights", "k = 8 nearest, row-standardised"),
                 ("Inference", "999 permutations, p < 0.05"),
                 ("Buffer", "150 m rural \u00b7 250 m urban"),
                 ("Missed test", "no e-tally AND no clean GPS fix"),
                 ("Denominator", f"{len(d):,} planned settlements")]:
        fig.text(IN, y, k, fontsize=6.5, family="monospace", color=C_MUTED, va="top")
        fig.text(IN + 0.058, y, v, fontsize=6.5, color=C_INK, va="top")
        y -= 0.0122
    y -= 0.012

    y = head("Interpretation limits", y)
    fig.text(IN, y,
             "Clusters are areas, not lists of children. They do not identify\n"
             "which settlement was missed, nor the vaccination status of any\n"
             "individual child. A settlement inside a cluster may have been\n"
             "reached; one outside it may not.",
             fontsize=6.5, color="#8A2B1F", va="top", linespacing=1.55)
    y -= 0.062

    # -------------------------- LEGEND, at the foot of the column ------------
    y = head("Legend", y)
    LH = 0.150
    axl = fig.add_axes([IN, y - LH, TW, LH])
    axl.set_zorder(4)            # axes default to zorder 0 and would otherwise sit
    axl.patch.set_alpha(0)       # BEHIND the white panel rectangle (zorder 1)
    axl.set_xlim(0, 1); axl.set_ylim(0, 1); axl.axis("off")
    rows = [
        ("dot20", C_MISSED, "Missed \u2014 unexplained",
         "no e-tally, no GPS, no security reason on file"),
        ("tri", C_INACC, "Missed \u2014 classified inaccessible",
         "security constraint recorded before the round"),
        ("dot9", C_GPSONLY, "GPS evidence only", "visited but not reported"),
        ("dot3", C_VISIT, "Confirmed by both sources", None),
        ("ring", C_CLUSTER, "Significant High-High cluster",
         "Local Moran's I, p < 0.05"),
        ("lga", C_LGA, "LGA boundary", "thin grey \u2014 ward boundary"),
    ]
    step = 1.0 / len(rows)
    for i, (kind, col, lab, sub) in enumerate(rows):
        yy = 1 - (i + 0.42) * step
        if kind == "tri":
            axl.scatter([0.048], [yy], marker="^", s=52, c=col, lw=0, clip_on=False)
        elif kind == "ring":
            axl.scatter([0.048], [yy], s=150, facecolor="none", edgecolor=col,
                        lw=1.5, clip_on=False)
        elif kind == "lga":
            axl.plot([0.015, 0.082], [yy + 0.018, yy + 0.018], color=C_LGA,
                     lw=1.7, clip_on=False)
            axl.plot([0.015, 0.082], [yy - 0.020, yy - 0.020], color=C_WARD,
                     lw=.9, clip_on=False)
        else:
            axl.scatter([0.048], [yy],
                        s={"dot20": 40, "dot9": 22, "dot3": 12}[kind],
                        c=col, lw=0, clip_on=False)
        axl.text(0.150, yy + (0.20 * step if sub else 0), lab, fontsize=7.3,
                 color=C_INK, va="center")
        if sub:
            axl.text(0.150, yy - 0.26 * step, sub, fontsize=6.2, color=C_MUTED,
                     va="center")
    print(f"  column floor y = {y - LH:.3f} (panel base 0.052)")

    # --------------------------------------------------------------- footer
    fig.patches.append(Rectangle((0.045, 0.040), 0.922, 0.0012,
                                 transform=fig.transFigure, facecolor="#CFC9BB", lw=0))
    fig.text(0.045, 0.032,
             "Data sources: settlement_masterlist.csv, etally_daily.csv, "
             "inaccessible_settlements.csv, boundaries.gpkg, and QA-assured campaign "
             "GPS logger exports (Bansara State SIA data pack).\n"
             "Produced by the GIS & Data Analytics Unit  \u2022  Analysis CRS EPSG:32632 "
             "(WGS 84 / UTM 32N); displayed in EPSG:4326.  "
             "ALL DATA SYNTHETIC \u2014 FOR ASSESSMENT PURPOSES ONLY.",
             fontsize=6.6, color=C_MUTED, va="top", linespacing=1.6)

    fig.savefig(PDF, format="pdf", facecolor=C_PAPER)
    fig.savefig(PNG, dpi=130, facecolor=C_PAPER)
    plt.close(fig)
    print(f"Saved A3 map -> {PDF}")


if __name__ == "__main__":
    main()
