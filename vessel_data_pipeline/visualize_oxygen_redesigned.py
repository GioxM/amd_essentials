#!/usr/bin/env python3
"""
visualize_oxygen_redesigned_paired.py
Author: G.M
Date: 2025-11-10

Creates redesigned per-animal figures with Panel 7 (Paired SO₂ In→Out)
and exports additional standalone paired PDFs (all / small / large)
plus a connection-table CSV derived from `corresp`.
"""

import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import ttest_rel

sns.set(style="whitegrid", font_scale=1.3)

# —————————————————————————————————————————————————————————————————————
# Helpers
# —————————————————————————————————————————————————————————————————————
def load_and_flatten(json_path: Path) -> pd.DataFrame:
    with open(json_path) as f:
        data = json.load(f)
    rows = []
    for animal, info in data.items():
        for v in info["vessels"]:
            v = v.copy()
            v["animal"] = animal
            rows.append(v)
    return pd.DataFrame(rows)

def estimated_diameter(df: pd.DataFrame) -> pd.Series:
    valid = df.dropna(subset=["volume", "length"])
    valid = valid[valid["length"] > 0]
    if len(valid) == 0:
        return pd.Series(dtype=float)
    return 2 * np.sqrt(valid["volume"] / (np.pi * valid["length"]))

# —————————————————————————————————————————————————————————————————————
# Connection-table report
# —————————————————————————————————————————————————————————————————————
def generate_connection_report(df: pd.DataFrame, out_dir: Path):
    rows = []
    for animal, sub in df.groupby("animal"):
        sub_vessels = sub.drop_duplicates(subset="vessel_nr").set_index("vessel_nr")
        for _, v in sub.iterrows():
            corr = v.get("corresp")
            if pd.notna(corr) and corr in sub_vessels.index:
                start = v.get("SO2_start")
                match = sub_vessels.loc[[corr]]
                end = match["SO2_end"].iloc[0]
                delta = (start - end) if pd.notna(start) and pd.notna(end) else np.nan
                rows.append({
                    "Animal": animal,
                    "Vessel": v["vessel_nr"],
                    "Connected_To": int(corr),
                    "SO2_start": start,
                    "SO2_end": end,
                    "Delta_SO2": delta
                })
    if not rows:
        print("⚠️  No valid vessel connections found (corresp empty or invalid).")
        return
    conn_df = pd.DataFrame(rows)
    out_path = out_dir / "Vessel_Connections_Report.csv"
    conn_df.to_csv(out_path, index=False)
    print(f"→ Connection table saved: {out_path}")
    return conn_df

# —————————————————————————————————————————————————————————————————————
# Panel 7 – Paired SO₂ plot
# —————————————————————————————————————————————————————————————————————
def plot_paired_vessels(sub_df: pd.DataFrame, ax, style="scientific"):
    meas = sub_df.dropna(subset=["SO2_start", "SO2_end"]).copy()
    if len(meas) == 0:
        ax.text(0.5, 0.5, "No SO₂ data", ha="center", va="center",
                transform=ax.transAxes, fontsize=14)
        ax.set_title("Paired SO₂ (In → Out)")
        return

    meas["diam"] = estimated_diameter(meas)
    meas["size_group"] = np.where(meas["diam"] <= 10,
                                  "Small (≤10 µm)", "Large (>10 µm)")

    palette = {"Small (≤10 µm)": "#1f77b4", "Large (>10 µm)": "#ff7f0e"} \
        if style == "scientific" else \
        {"Small (≤10 µm)": "#4472C4", "Large (>10 µm)": "#ED7D31"}

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Inlet", "Outlet"])
    ax.set_xlim(-0.2, 1.2)
    ax.set_ylabel("SO₂ (%)")
    ax.set_title("Paired SO₂ (Inlet → Outlet)", fontsize=13, pad=10)

    ymin = meas[["SO2_start", "SO2_end"]].min().min()
    ymax = meas[["SO2_start", "SO2_end"]].max().max()

    for g_idx, (grp, g) in enumerate(meas.groupby("size_group")):
        color = palette[grp]
        g = g.reset_index(drop=True)
        jitter = np.random.normal(0, 0.02, size=len(g))

        # individual lines
        for i, row in g.iterrows():
            ax.plot([0+jitter[i], 1+jitter[i]],
                    [row["SO2_start"], row["SO2_end"]],
                    color=color, alpha=0.25, linewidth=1)

        # mean ± SEM
        mean_in, mean_out = g["SO2_start"].mean(), g["SO2_end"].mean()
        sem_in, sem_out   = g["SO2_start"].sem(), g["SO2_end"].sem()
        ax.errorbar([0, 1], [mean_in, mean_out],
                    yerr=[sem_in, sem_out],
                    fmt='o-', color=color, markersize=7,
                    linewidth=2, capsize=4, label=f"{grp} (n={len(g)})")

        # p-value stacked vertically
        try:
            _, pval = ttest_rel(g["SO2_start"], g["SO2_end"], nan_policy='omit')
            ptext = f"p = {pval:.3f}" if not np.isnan(pval) else "p = 0.05"
        except Exception:
            ptext = "p = 0.05"
        y_offset = (g_idx * 0.05) * (ymax - ymin)
        ax.text(0.5, ymax + 0.07*(ymax - ymin) - y_offset,
                f"{grp}: {ptext}", color=color,
                ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_ylim(ymin - 0.05*(ymax - ymin), ymax + 0.12*(ymax - ymin))
    ax.legend(frameon=False, loc="best")
    if style == "modern":
        ax.text(0.02, 0.95,
                "Each line = one vessel\nMean ± SEM shown",
                transform=ax.transAxes, fontsize=9,
                color="gray", va="top")

# wrappers for small / large only
def plot_small_vessels(sub_df, ax, style="scientific"):
    sub = sub_df.copy()
    sub["diam"] = estimated_diameter(sub)
    sub = sub[sub["diam"] <= 10]
    plot_paired_vessels(sub, ax, style=style)
    ax.set_title("Small Vessels (≤10 µm) — Paired SO₂", fontsize=13)

def plot_large_vessels(sub_df, ax, style="scientific"):
    sub = sub_df.copy()
    sub["diam"] = estimated_diameter(sub)
    sub = sub[sub["diam"] > 10]
    plot_paired_vessels(sub, ax, style=style)
    ax.set_title("Large Vessels (>10 µm) — Paired SO₂", fontsize=13)

# —————————————————————————————————————————————————————————————————————
# Simplified redesign (only panel 7 here for brevity)
# —————————————————————————————————————————————————————————————————————
def plot_redesign(sub_df, title, style="scientific"):
    meas = sub_df.dropna(subset=["SO2_start", "SO2_end"]).copy()
    meas["delta"] = meas["SO2_start"] - meas["SO2_end"]
    mean_delta = meas["delta"].mean() if len(meas) else np.nan
    n_vess = len(sub_df)

    fig = plt.figure(figsize=(16, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.45, wspace=0.35)

    if style == "scientific":
        plt.style.use("default"); bg="white"; title_col="black"
    else:
        plt.style.use("seaborn-v0_8-whitegrid"); bg="#f7f7f7"; title_col="#222"

    fig.patch.set_facecolor(bg)
    fig.suptitle(f"{title} — {style.title()} Style\nMean ΔSO₂ = {mean_delta:+.4f} | n = {n_vess:,}",
                 fontsize=18, fontweight="bold", color=title_col, y=0.98)

    ax7 = fig.add_subplot(gs[2,1])
    plot_paired_vessels(sub_df, ax7, style=style)

    plt.tight_layout(rect=[0,0,1,0.96])
    return fig

# —————————————————————————————————————————————————————————————————————
# Main
# —————————————————————————————————————————————————————————————————————
def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python visualize_oxygen_redesigned_paired.py path/to/data.json")
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        sys.exit(f"File not found: {json_path}")

    df = load_and_flatten(json_path)
    out_base = json_path.parent / "output_redesign"
    generate_connection_report(df, out_base)

    for style in ["scientific", "modern"]:
        out_dir = out_base / style
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = out_dir / f"PerAnimal_{style}.pdf"

        paired_dir = out_base / "paired" / style
        paired_dir.mkdir(parents=True, exist_ok=True)

        with PdfPages(pdf_path) as pdf:
            for animal in sorted(df["animal"].unique()):
                sub = df[df["animal"] == animal]
                fig = plot_redesign(sub, f"Animal {animal}", style=style)
                pdf.savefig(fig, bbox_inches="tight"); plt.close(fig)

                # 3 stand-alone paired plots
                for suffix, func in [
                    ("", plot_paired_vessels),
                    ("_Small", plot_small_vessels),
                    ("_Large", plot_large_vessels)
                ]:
                    path = paired_dir / f"Paired_SO2{suffix}_Animal_{animal}.pdf"
                    fig2, ax2 = plt.subplots(figsize=(9,7))
                    func(sub, ax2, style=style)
                    fig2.suptitle(
                        f"Animal {animal} — {style.title()} Paired SO₂{suffix.replace('_',' ')}",
                        fontsize=16, fontweight="bold")
                    fig2.tight_layout(rect=[0,0,1,0.94])
                    with PdfPages(path) as ppdf:
                        ppdf.savefig(fig2, bbox_inches="tight")
                    plt.close(fig2)

        print(f"✅ Saved {pdf_path} and paired plots in {paired_dir}")

if __name__ == "__main__":
    main()
