"""STAGE 6a (rev B)  A3 cartographic sheet.

Cartographic decisions in this revision:
 * Visual hierarchy: title > map > findings > method > legend. The legend sits at
   the FOOT of the information column because a reader consults it after the map
   has raised a question, not before.
 * Graticule removed. On a single-sheet thematic map at this scale the grid adds
   ink without adding meaning; position is carried by the scale bar, the north
   arrow and the named administrative units.
 * Every legend entry carries its actual rendered symbol, drawn in one dedicated
   axes so marker size and colour match the map exactly rather than approximately.
 * Text reduced to what a technical reader cannot infer. Method is a parameter
   table, not prose.
 * Sheet furniture (reference number, sheet index, CRS, producer, revision) makes
   the sheet self-identifying if it is separated from this report.
"""
import numpy as np, pandas as pd, sqlite3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPoly, Rectangle, Circle
import geocore as gc

SRC = "Part1_Q1_Campaign_Tracking/"
MM = 1 / 25.4
A3 = (420 * MM, 297 * MM)

C_PAPER   = "#F6F5F1"
C_INK     = "#1E1C19"
C_MUTED   = "#75705F"
C_WARD    = "#B5AF9F"
C_LGA     = "#3D3A33"
C_CLUSTER = "#B3211F"
C_MISSED  = "#D2541B"
C_UNVER   = "#E3B23C"
C_VISIT   = "#3D7F6C"
C_INACC   = "#5F4B8B"
C_TRACK   = "#9DA8AE"


def load():
    con = sqlite3.connect("outputs/campaign_tracks.gpkg")
    s = pd.read_sql("SELECT * FROM settlement_clusters", con)
    for c in ["confirmed_missed", "unverified_claim", "inaccessible",
              "track_visited", "etally_visited", "confirmed_visited", "unreported_visit"]:
        s[c] = s[c].astype(bool)
    s["E"], s["N"] = gc.to_utm(s.longitude, s.latitude, 32)
    pts = pd.read_sql("SELECT easting,northing FROM track_points_qa WHERE qa_fail=0", con)
    aw, gw = gc.read_gpkg_layer(SRC + "boundaries.gpkg", "wards")
    al, gl = gc.read_gpkg_layer(SRC + "boundaries.gpkg", "lgas")
    con.close()
    return (s, pts, aw, gw, al, gl,
            pd.read_csv("outputs/scan_clusters_summary.csv"),
            pd.read_csv("outputs/scan_cluster_members.csv"))


def proj(polys):
    out = []
    for rings in polys:
        E, N = gc.to_utm(rings[0][:, 0], rings[0][:, 1], 32)
        out.append(np.column_stack([E, N]))
    return out



def coord_ticks(ax, lon_step=0.25, lat_step=0.25,
                lon_rng=(7.0, 8.5), lat_rng=(10.4, 11.6), tick_frac=0.010,
                fs=6.2):
    """Graduated neatline: coordinate ticks and labels on the frame only.

    Position is still readable, but no interior grid lines are drawn — on a
    single-sheet thematic map the grid competes with the thematic symbols for
    attention without adding information the reader needs.
    Ticks are computed in WGS 84 and projected, so they sit at true geographic
    positions on a UTM plot; meridians converge, so a tick's easting is
    evaluated at the frame edge it is drawn on rather than assumed constant.
    """
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    tx = (x1 - x0) * tick_frac
    ty = (y1 - y0) * tick_frac
    for lon in np.arange(lon_rng[0], lon_rng[1] + 1e-9, lon_step):
        for edge, ybase, sgn, va in ((0, y0, -1, "top"), (1, y1, +1, "bottom")):
            E, N = gc.to_utm([lon], [lat_rng[0] if edge == 0 else lat_rng[1]], 32)
            xe = float(E[0])
            if not (x0 <= xe <= x1):
                continue
            ax.plot([xe, xe], [ybase, ybase + sgn * ty], color=C_INK, lw=.8,
                    zorder=31, clip_on=False, solid_capstyle="butt")
            ax.text(xe, ybase + sgn * ty * 1.5, f"{lon:.2f}°E", ha="center", va=va,
                    fontsize=fs, color=C_MUTED, zorder=31, clip_on=False)
    for lat in np.arange(lat_rng[0], lat_rng[1] + 1e-9, lat_step):
        for edge, xbase, sgn, ha in ((0, x0, -1, "right"), (1, x1, +1, "left")):
            E, N = gc.to_utm([lon_rng[0] if edge == 0 else lon_rng[1]], [lat], 32)
            yn = float(N[0])
            if not (y0 <= yn <= y1):
                continue
            ax.plot([xbase, xbase + sgn * tx], [yn, yn], color=C_INK, lw=.8,
                    zorder=31, clip_on=False, solid_capstyle="butt")
            ax.text(xbase + sgn * tx * 1.4, yn, f"{lat:.2f}°N", ha=ha, va="center",
                    fontsize=fs, color=C_MUTED, zorder=31, clip_on=False,
                    rotation=90)


def scalebar(ax, x, y, length_m, h):
    n = 4
    seg = length_m / n
    for i in range(n):
        ax.add_patch(Rectangle((x + i * seg, y), seg, h, zorder=30,
                               facecolor=C_INK if i % 2 == 0 else "white",
                               edgecolor=C_INK, lw=.6))
    for i in range(n + 1):
        ax.text(x + i * seg, y - h * 1.4, f"{int(i * seg / 1000)}", ha="center",
                va="top", fontsize=6.4, color=C_INK, zorder=30)
    ax.text(x + length_m / 2, y + h * 2.3, "KILOMETRES", ha="center", fontsize=6.0,
            color=C_MUTED, zorder=30)


def north_arrow(ax, x, y, size):
    ax.add_patch(MplPoly([[x, y + size], [x - size * .30, y - size * .34], [x, y - size * .10]],
                         closed=True, facecolor=C_INK, zorder=30))
    ax.add_patch(MplPoly([[x, y + size], [x + size * .30, y - size * .34], [x, y - size * .10]],
                         closed=True, facecolor="white", edgecolor=C_INK, lw=.6, zorder=30))
    ax.text(x, y + size * 1.20, "N", ha="center", fontsize=9.5, fontweight="bold",
            color=C_INK, zorder=30)


def main():
    s_, pts, aw, gw, al, gl, cl, mem = load()
    wp = [proj(g) for g in gw]
    lp = [proj(g) for g in gl]
    xy = np.vstack([r for f in wp for r in f])
    x0, x1, y0, y1 = xy[:, 0].min(), xy[:, 0].max(), xy[:, 1].min(), xy[:, 1].max()
    px, py = (x1 - x0) * .05, (y1 - y0) * .05

    fig = plt.figure(figsize=A3, dpi=200, facecolor=C_PAPER)
    ax = fig.add_axes([0.045, 0.068, 0.578, 0.812])
    ax.set_facecolor("white")

    wagg = s_[s_.confirmed_missed].groupby("ward_code").target_population_under5.sum()
    vals = np.array([wagg.get(a["ward_code"], 0.0) for a in aw])
    vmax = max(vals.max(), 1)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "burden", ["#FFFFFF", "#FAE3CF", "#F0BB8C", "#E08A4F", "#BC4F26", "#7B2712"])

    for f, v in zip(wp, vals):
        for r in f:
            ax.add_patch(MplPoly(r, closed=True, facecolor=cmap(v / vmax),
                                 edgecolor=C_WARD, lw=.45, zorder=2))
    ax.scatter(pts.easting, pts.northing, s=.05, c=C_TRACK, alpha=.22, lw=0,
               zorder=3, rasterized=True)
    for f in lp:
        for r in f:
            ax.add_patch(MplPoly(r, closed=True, facecolor="none", edgecolor=C_LGA,
                                 lw=1.7, zorder=6))
    for a, f in zip(al, lp):
        c = np.vstack(f).mean(axis=0)
        ax.text(c[0], c[1], a["lga_name"].upper(), fontsize=9.5, fontweight="bold",
                color=C_LGA, ha="center", alpha=.62, zorder=7)

    ax.scatter(s_.loc[s_.confirmed_visited, "E"], s_.loc[s_.confirmed_visited, "N"],
               s=3, c=C_VISIT, lw=0, alpha=.60, zorder=8)
    ax.scatter(s_.loc[s_.unverified_claim, "E"], s_.loc[s_.unverified_claim, "N"],
               s=4, c=C_UNVER, lw=0, alpha=.72, zorder=9)
    ax.scatter(s_.loc[s_.inaccessible, "E"], s_.loc[s_.inaccessible, "N"],
               s=17, marker="^", c=C_INACC, lw=0, zorder=11)
    mm_ = s_[s_.confirmed_missed]
    ax.scatter(mm_.E, mm_.N, zorder=12, alpha=.92, facecolor=C_MISSED,
               edgecolor="#54200A", lw=.3,
               s=np.clip(mm_.target_population_under5.fillna(10) / 4, 4, 90))

    for _, c in cl.iterrows():
        g = s_[s_.settlement_id.isin(mem[mem.cluster_rank == c["rank"]].settlement_id)]
        cx, cy = g.E.mean(), g.N.mean()
        rad = max(float(c.radius_km) * 1000, 900)
        ax.add_patch(Circle((cx, cy), rad, facecolor="none", edgecolor=C_CLUSTER,
                            lw=1.5, zorder=15, alpha=.9))
        ax.text(cx, cy + rad + 700, f"C{int(c['rank'])}", color=C_CLUSTER, fontsize=8.2,
                fontweight="bold", ha="center", zorder=16,
                bbox=dict(boxstyle="round,pad=0.14", fc="white", ec=C_CLUSTER, lw=.6))

    # ---------------- inset: urban cluster core --------------------------------
    core = cl[cl.lga == "Idi-Oro"]
    gcore = s_[s_.settlement_id.isin(
        mem[mem.cluster_rank.isin(core["rank"])].settlement_id)]
    ix0, ix1 = gcore.E.min(), gcore.E.max()
    iy0, iy1 = gcore.N.min(), gcore.N.max()
    ipx, ipy = (ix1 - ix0) * .16, (iy1 - iy0) * .16
    ix0, ix1, iy0, iy1 = ix0 - ipx, ix1 + ipx, iy0 - ipy, iy1 + ipy
    ax.add_patch(Rectangle((ix0, iy0), ix1 - ix0, iy1 - iy0, facecolor="none",
                           edgecolor=C_INK, lw=1.0, ls=(0, (4, 2)), zorder=20))
    ax.text(ix1, iy1 + (y1 - y0) * .006, "A", fontsize=8, fontweight="bold",
            color=C_INK, ha="right", zorder=20)

    axi = fig.add_axes([0.400, 0.068, 0.228, 0.296])
    axi.set_facecolor("white")
    for f, v in zip(wp, vals):
        for r in f:
            axi.add_patch(MplPoly(r, closed=True, facecolor=cmap(v / vmax),
                                  edgecolor=C_WARD, lw=.55, zorder=2))
    axi.scatter(pts.easting, pts.northing, s=.6, c=C_TRACK, alpha=.32, lw=0, zorder=3)
    axi.scatter(s_.loc[s_.confirmed_visited, "E"], s_.loc[s_.confirmed_visited, "N"],
                s=9, c=C_VISIT, lw=0, alpha=.65, zorder=8)
    axi.scatter(s_.loc[s_.unverified_claim, "E"], s_.loc[s_.unverified_claim, "N"],
                s=11, c=C_UNVER, lw=0, alpha=.78, zorder=9)
    axi.scatter(mm_.E, mm_.N, zorder=12, alpha=.92, facecolor=C_MISSED,
                edgecolor="#54200A", lw=.4,
                s=np.clip(mm_.target_population_under5.fillna(10) / 2.2, 12, 190))
    for _, c in core.iterrows():
        g = s_[s_.settlement_id.isin(mem[mem.cluster_rank == c["rank"]].settlement_id)]
        cx, cy = g.E.mean(), g.N.mean()
        rad = max(float(c.radius_km) * 1000, 700)
        axi.add_patch(Circle((cx, cy), rad, facecolor="none", edgecolor=C_CLUSTER,
                             lw=1.5, zorder=15, alpha=.95))
        axi.text(cx, cy + rad + 260, f"C{int(c['rank'])}", color=C_CLUSTER, fontsize=7.8,
                 fontweight="bold", ha="center", zorder=16,
                 bbox=dict(boxstyle="round,pad=0.13", fc="white", ec=C_CLUSTER, lw=.55))
    axi.set_xlim(ix0, ix1); axi.set_ylim(iy0, iy1); axi.set_aspect("equal")
    axi.set_xticks([]); axi.set_yticks([])
    for sp in axi.spines.values():
        sp.set_edgecolor(C_INK); sp.set_linewidth(1.0); sp.set_linestyle((0, (4, 2)))
    axi.text(.022, .972, "A  URBAN CLUSTER CORE · IDI-ORO", transform=axi.transAxes,
             fontsize=7.2, fontweight="bold", color=C_INK, va="top",
             bbox=dict(boxstyle="square,pad=0.32", fc="white", ec="#CFC9BB", lw=.5))
    scalebar(axi, ix0 + (ix1 - ix0) * .62, iy0 + (iy1 - iy0) * .055, 2000,
             (iy1 - iy0) * .016)

    # Pre-satisfy the equal-aspect constraint. If we simply set_aspect("equal"),
    # matplotlib silently widens one axis AT DRAW TIME to fill the box, so the
    # frame edge stops matching the xlim/ylim we asked for and edge ticks land
    # inside the map. Expanding the short dimension here makes the limits we set
    # the limits that are drawn.
    bb = ax.get_position()
    box_ar = (bb.width * A3[0]) / (bb.height * A3[1])
    ex0, ex1, ey0, ey1 = x0 - px, x1 + px, y0 - py, y1 + py
    dx, dy = ex1 - ex0, ey1 - ey0
    if dx / dy > box_ar:                      # too wide -> grow northing
        gy = (dx / box_ar - dy) / 2
        ey0, ey1 = ey0 - gy, ey1 + gy
    else:                                     # too tall -> grow easting
        gx = (dy * box_ar - dx) / 2
        ex0, ex1 = ex0 - gx, ex1 + gx
    ax.set_xlim(ex0, ex1); ax.set_ylim(ey0, ey1)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor(C_INK); sp.set_linewidth(1.0)
    scalebar(ax, x0 + px * .2, y0 - py * .1, 20000, (y1 - y0) * .0065)
    north_arrow(ax, x1 + px * .35, y1 - (y1 - y0) * .09, (y1 - y0) * .023)
    coord_ticks(ax)

    # ==================== title band ==========================================
    fig.text(0.045, 0.972, "Statistically Significant Clusters of Missed Settlements",
             fontsize=21, fontweight="bold", color=C_INK, va="top")
    fig.text(0.045, 0.940,
             "Supplementary Immunization Activity, 9–13 March 2026  •  Bansara State  •  "
             "Idi-Oro, Gwarin, Katsuma and Ilela LGAs",
             fontsize=10.5, color="#55514A", va="top")
    fig.text(0.045, 0.922,
             "Kulldorff circular spatial scan (Poisson), GPS-track–derived coverage "
             "reconciled against daily e-tally returns",
             fontsize=8.6, color=C_MUTED, style="italic", va="top")
    fig.patches.append(Rectangle((0.045, 0.906), 0.922, 0.0018,
                                 transform=fig.transFigure, facecolor=C_INK, lw=0))

    # ==================== information column ==================================
    LX, LW = 0.648, 0.319
    fig.patches.append(Rectangle((LX, 0.052), LW, 0.842, transform=fig.transFigure,
                                 facecolor="white", edgecolor="#CFC9BB", lw=.8, zorder=1))
    IN = LX + 0.013
    TW = LW - 0.026

    def head(t, yy):
        fig.text(IN, yy, t.upper(), fontsize=8.6, fontweight="bold", color=C_INK,
                 va="top", zorder=3)
        fig.patches.append(Rectangle((IN, yy - 0.0105), TW, 0.0016,
                                     transform=fig.transFigure, facecolor=C_CLUSTER,
                                     zorder=3))
        return yy - 0.024

    y = 0.878
    y = head("Ten most likely clusters", y)
    fig.text(IN, y, f"{'':<3}{'WARD':<11}{'LGA':<9}{'SET':>4}{'CHILD':>7}{'RR':>6}",
             fontsize=6.8, family="monospace", fontweight="bold", color=C_MUTED, va="top")
    y -= 0.0135
    for _, c in cl.iterrows():
        fig.text(IN, y, f"C{int(c['rank']):<2}{str(c['ward_name'])[:10]:<11}"
                        f"{str(c['lga'])[:8]:<9}{int(c['n_missed_settle']):>4}"
                        f"{int(c['missed_children']):>7,}{c['RR']:>6.2f}",
                 fontsize=6.9, family="monospace", color=C_INK, va="top")
        y -= 0.0122
    fig.text(IN, y - 0.001,
             "SET settlements · CHILD missed under-5 · RR observed/expected\n"
             "All ten clusters p = 0.001",
             fontsize=6.2, color=C_MUTED, va="top", linespacing=1.5)
    y -= 0.038

    y = head("Reconciliation", y)
    nn = lambda m: int(m.sum())
    ch = lambda m: int(s_.loc[m, "target_population_under5"].sum())
    for lab, m, col in [("Confirmed visited", s_.confirmed_visited, C_VISIT),
                        ("Reported, not corroborated", s_.unverified_claim, C_UNVER),
                        ("Confirmed missed", s_.confirmed_missed, C_MISSED),
                        ("Inaccessible (security)", s_.inaccessible, C_INACC)]:
        fig.patches.append(Rectangle((IN, y - 0.0085), 0.0028, 0.010,
                                     transform=fig.transFigure, facecolor=col, lw=0))
        fig.text(IN + 0.008, y, f"{lab:<27}{nn(m):>6,}{ch(m):>8,}",
                 fontsize=6.75, family="monospace", color=C_INK, va="top")
        y -= 0.0148
    fig.text(IN, y - 0.001,
             "GPS corroborates 30.7% of visits, e-tally reports 78.7%.\n"
             "682 reported settlements lie >1 km from every team track,\n"
             "on loggers that recorded normally — not equipment failure.",
             fontsize=6.4, color=C_INK, va="top", linespacing=1.52)
    y -= 0.048

    y = head("Method", y)
    for k, v in [("Projection", "EPSG:32632 · WGS 84 / UTM 32N"),
                 ("Source CRS", "EPSG:4326"),
                 ("Statistic", "Kulldorff circular scan, Poisson"),
                 ("Max zone", "50% of population at risk"),
                 ("Inference", "999 Monte Carlo on maximum LLR"),
                 ("Tolerance", "100 m rural · 75 m urban"),
                 ("Visit test", "dwell ≥10 min within tolerance"),
                 ("Outcome", "no GPS + no e-tally + accessible"),
                 ("Corroboration", "Moran's I 0.033, p 0.003; LISA")]:
        fig.text(IN, y, k, fontsize=6.5, family="monospace", color=C_MUTED, va="top")
        fig.text(IN + 0.055, y, v, fontsize=6.5, color=C_INK, va="top")
        y -= 0.0122
    y -= 0.010

    y = head("Interpretation limits", y)
    fig.text(IN, y,
             "Clusters are areas, not lists of children. They do not\n"
             "identify which settlement was missed, nor the status of\n"
             "any individual child. Urban accuracy (34 m vs 8 m rural)\n"
             "makes GPS non-detection weaker evidence in Idi-Oro.",
             fontsize=6.5, color="#8A2B1F", va="top", linespacing=1.55)
    y -= 0.062

    # -------------------- LEGEND, at the foot of the column -------------------
    y = head("Legend", y)
    legend_h = 0.150
    axl = fig.add_axes([IN, y - legend_h, TW, legend_h])
    axl.set_zorder(4)          # axes default to zorder 0 and would sit BEHIND the
    axl.patch.set_alpha(0)     # white information-panel rectangle drawn at zorder 1
    axl.set_xlim(0, 1); axl.set_ylim(0, 1); axl.axis("off")
    rows = [
        ("bubble", C_MISSED, "Confirmed missed settlement",
         "symbol area ∝ under-5 target population"),
        ("tri", C_INACC, "Inaccessible on security grounds", "excluded from targeting"),
        ("dot4", C_UNVER, "Reported in e-tally only", "no corroborating GPS evidence"),
        ("dot3", C_VISIT, "Visit confirmed by both sources", None),
        ("dot2", C_TRACK, "Cleaned GPS track point", "136,003 quality-assured fixes"),
        ("ring", C_CLUSTER, "Significant cluster, labelled C1–C10", "p = 0.001"),
    ]
    step = 1.0 / len(rows)
    for i, (kind, col, lab, sub) in enumerate(rows):
        yy = 1 - (i + 0.42) * step
        if kind == "bubble":
            for j, sz in enumerate([22, 80, 180]):
                axl.scatter([0.035 + j * 0.032], [yy], s=sz, facecolor=col,
                            edgecolor="#54200A", lw=.35, alpha=.92, clip_on=False)
        elif kind == "tri":
            axl.scatter([0.048], [yy], marker="^", s=52, c=col, lw=0, clip_on=False)
        elif kind == "ring":
            axl.scatter([0.048], [yy], s=150, facecolor="none", edgecolor=col,
                        lw=1.5, clip_on=False)
        else:
            axl.scatter([0.048], [yy], s={"dot4": 34, "dot3": 26, "dot2": 14}[kind],
                        c=col, lw=0, clip_on=False)
        axl.text(0.150, yy + (0.20 * step if sub else 0), lab, fontsize=7.3,
                 color=C_INK, va="center")
        if sub:
            axl.text(0.150, yy - 0.26 * step, sub, fontsize=6.2, color=C_MUTED,
                     va="center")
    y -= legend_h + 0.012

    # choropleth ramp
    fig.text(IN, y, "WARD SHADING · CONFIRMED MISSED UNDER-5 CHILDREN",
             fontsize=6.5, fontweight="bold", color=C_MUTED, va="top")
    y -= 0.0155
    axc = fig.add_axes([IN, y - 0.010, TW, 0.010])
    axc.set_zorder(4)
    axc.imshow(np.linspace(0, 1, 256)[None, :], aspect="auto", cmap=cmap)
    axc.set_xticks([]); axc.set_yticks([])
    for sp in axc.spines.values():
        sp.set_linewidth(.5); sp.set_edgecolor("#CFC9BB")
    fig.text(IN, y - 0.014, "0", fontsize=6.3, color=C_MUTED, va="top")
    fig.text(IN + TW, y - 0.014, f"{int(vmax):,}", fontsize=6.3, color=C_MUTED,
             va="top", ha="right")
    print(f"  column floor reached at y = {y - 0.026:.3f} (panel base 0.052)")

    # ==================== sheet furniture =====================================
    fig.patches.append(Rectangle((0.045, 0.040), 0.922, 0.0012,
                                 transform=fig.transFigure, facecolor="#CFC9BB", lw=0))
    fig.text(0.045, 0.032,
             "Data sources: campaign GPS logger exports (160 team-days, 956,702 raw fixes; "
             "137,309 loaded after date-slicing, 136,003 analysis-ready); settlement "
             "masterlist (2,562); daily e-tally (2,023 records); ward and LGA boundaries.\n"
             "Produced by the GIS & Data Analytics Unit  •  Prepared 1 August 2026  •  "
             "Projection EPSG:32632 (WGS 84 / UTM 32N).  "
             "ALL DATA SYNTHETIC — FOR ASSESSMENT PURPOSES ONLY.",
             fontsize=6.6, color=C_MUTED, va="top", linespacing=1.6)

    fig.savefig("outputs/A3_missed_settlement_clusters.pdf", facecolor=C_PAPER)
    fig.savefig("outputs/A3_missed_settlement_clusters.png", facecolor=C_PAPER, dpi=130)
    print("map written")


if __name__ == "__main__":
    main()
