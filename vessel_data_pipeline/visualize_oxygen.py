#!/usr/bin/env python3
"""
visualize_oxygen.py
Author: G.M
Date: 6-11-2025
Country: NL
X: @Artifioicus

=====================================================================
CHANGELOG
=====================================================================
v0.1 (2025-11-06) – Initial version: 6-panel PDF, basic stats
v0.2 (2025-11-10) – Added rugplots + stripplot for real data points
v0.3 (2025-11-10) – Fixed rug compression: smart layering (rug/strip/sample)
v0.4 (2025-11-10) – **CURRENT**
    • REMOVED RUGPLOTS ENTIRELY in detailed view
    • SPLIT INTO TWO PDFs:
        - Overview: 6-panel summary
        - Detailed: ONE PLOT PER PAGE (full size, swarm/jitter, no overlap)
    • Auto-swarm for n≤800, jitter for n>800
    • Inset histograms for n>1000
    • Clear versioned changelog in header
=====================================================================

Creates:
1. Oxygen_Extraction_Report.pdf      → Overview (6 small panels)
2. Oxygen_Extraction_Detailed.pdf    → One full-page plot per metric
"""

import json
from pathlib import Path
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

sns.set(style="whitegrid", font_scale=1.2)

# —————————————————————————————————————————————————————————————————————
# Load & Prep
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
        return pd.Series()
    return 2 * np.sqrt(valid["volume"] / (np.pi * valid["length"]))

# —————————————————————————————————————————————————————————————————————
# Smart Point Plotter (NO RUGS!)
# —————————————————————————————————————————————————————————————————————
def plot_individual_points(ax, data: pd.Series, title: str):
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    n = len(data)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_title(title)
        return

    # FULL SIZE PLOT → use swarm or jitter
    if n <= 800:
        try:
            sns.swarmplot(data=data, ax=ax, color="purple", size=4, alpha=0.8)
        except:
            sns.stripplot(data=data, ax=ax, color="purple", jitter=0.3, size=4, alpha=0.8)
        method = "Swarm"
    else:
        sample = data.sample(n=1000, random_state=42)
        sns.stripplot(data=sample, ax=ax, color="purple", jitter=0.35, size=4, alpha=0.8)
        method = "Jitter (1k sample)"

    # Inset for large n
    if n > 1000:
        inset = ax.inset_axes([0.68, 0.68, 0.3, 0.3])
        inset.hist(data, bins=50, color="gray", alpha=0.7, density=True)
        inset.set_title(f"All {n:,}", fontsize=8)
        inset.tick_params(axis='both', which='major', labelsize=6)

    ax.set_title(f"{title}\n({method}, n={n:,})", fontsize=14, pad=20)
    ax.set_xlabel("Value")

# —————————————————————————————————————————————————————————————————————
# 6-Panel Overview Page
# —————————————————————————————————————————————————————————————————————
def plot_overview_page(pdf, df_page, title):
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    fig.suptitle(f"OVERVIEW – {title}", fontsize=16, fontweight="bold")

    # 1. Vessel Type
    counts = df_page["vessel_type"].value_counts().sort_index()
    labels = ["Capillaries", "Venules"]
    axes[0,0].pie(counts, labels=labels, autopct="%1.1f%%", startangle=90)
    axes[0,0].set_title("Vessel Type")

    # 2. OD
    sns.histplot(df_page["OD"].dropna(), bins=50, ax=axes[0,1], color="skyblue", kde=True)
    axes[0,1].set_title("OD")

    # 3. ΔSO₂
    meas = df_page.dropna(subset=["SO2_start", "SO2_end"]).copy()
    if len(meas):
        meas["delta"] = meas["SO2_start"] - meas["SO2_end"]
        sns.histplot(meas["delta"], bins=30, ax=axes[0,2], color="salmon")
        axes[0,2].axvline(0, color="black", ls="--")
    axes[0,2].set_title("ΔSO₂")

    # 4. SO₂ Scatter
    if len(meas):
        axes[1,0].scatter(meas["SO2_end"], meas["SO2_start"], c=meas["delta"], cmap="RdYlGn", alpha=0.7, s=20)
        mn = meas[["SO2_start","SO2_end"]].min().min()
        mx = meas[["SO2_start","SO2_end"]].max().max()
        axes[1,0].plot([mn,mx], [mn,mx], "k--")
    axes[1,0].set_xlabel("Exit"); axes[1,0].set_ylabel("Entrance")
    axes[1,0].set_title("SO₂ In vs Out")

    # 5. Length vs Volume
    sns.scatterplot(data=df_page, x="length", y="volume", hue="vessel_type", ax=axes[1,1], alpha=0.6)
    axes[1,1].set_title("Geometry")

    # 6. Diameter
    diam = estimated_diameter(df_page)
    if len(diam):
        sns.histplot(diam, bins=50, ax=axes[1,2], color="green")
    axes[1,2].set_title("Est. Diameter")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    pdf.savefig(fig)
    plt.close()

# —————————————————————————————————————————————————————————————————————
# Full-Page Detailed Plots
# —————————————————————————————————————————————————————————————————————
def plot_detailed_pages(pdf, df_page, title_prefix):
    meas = df_page.dropna(subset=["SO2_start", "SO2_end"]).copy()
    if len(meas):
        meas["delta"] = meas["SO2_start"] - meas["SO2_end"]

    # 1. OD
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_individual_points(ax, df_page["OD"].dropna(), "Optical Density (OD)")
    pdf.savefig(fig); plt.close()

    # 2. ΔSO₂
    fig, ax = plt.subplots(figsize=(10, 6))
    if len(meas):
        plot_individual_points(ax, meas["delta"], "Oxygen Extraction (ΔSO₂)")
    else:
        ax.text(0.5, 0.5, "No SO₂ data", ha='center', va='center', transform=ax.transAxes)
        ax.set_title("ΔSO₂")
    pdf.savefig(fig); plt.close()

    # 3. SO₂ Scatter (full page)
    fig, ax = plt.subplots(figsize=(10, 8))
    if len(meas):
        scatter = ax.scatter(meas["SO2_end"], meas["SO2_start"], c=meas["delta"], cmap="RdYlGn", s=50, alpha=0.8)
        mn = meas[["SO2_start","SO2_end"]].min().min()
        mx = meas[["SO2_start","SO2_end"]].max().max()
        ax.plot([mn,mx], [mn,mx], "k--", linewidth=2)
        plt.colorbar(scatter, ax=ax, label="ΔSO₂")
        viol = meas[meas["delta"] < 0]
        for _, row in viol.head(15).iterrows():
            ax.annotate(f"V{row['vessel_nr']}", (row["SO2_end"], row["SO2_start"]),
                        xytext=(8, 8), textcoords="offset points", fontsize=9, color="red")
    ax.set_xlabel("SO₂ Exit"); ax.set_ylabel("SO₂ Entrance")
    ax.set_title(f"{title_prefix} – SO₂ Entrance vs Exit")
    pdf.savefig(fig); plt.close()

    # 4. Diameter
    diam = estimated_diameter(df_page)
    fig, ax = plt.subplots(figsize=(10, 6))
    if len(diam):
        plot_individual_points(ax, diam, "Estimated Diameter (µm)")
        ax.axvline(10, color="red", ls="--", label="Capillary limit")
        ax.legend()
    pdf.savefig(fig); plt.close()

# —————————————————————————————————————————————————————————————————————
# Main
# —————————————————————————————————————————————————————————————————————
def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python visualize_oxygen.py path/to/data.json")
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        sys.exit(f"File not found: {json_path}")

    df = load_and_flatten(json_path)
    out_dir = json_path.parent

    # OVERVIEW PDF
    overview_pdf = out_dir / "Oxygen_Extraction_Report.pdf"
    with PdfPages(overview_pdf) as pdf:
        for animal in sorted(df["animal"].unique()):
            sub = df[df["animal"] == animal]
            plot_overview_page(pdf, sub, f"Animal {animal}")
        if df["animal"].nunique() == 1:
            for vid in sorted(df["vid_name"].unique()):
                sub = df[df["vid_name"] == vid]
                plot_overview_page(pdf, sub, f"Session {vid}")
    print(f"OVERVIEW PDF: {overview_pdf}")

    # DETAILED PDF
    detailed_pdf = out_dir / "Oxygen_Extraction_Detailed.pdf"
    with PdfPages(detailed_pdf) as pdf:
        for animal in sorted(df["animal"].unique()):
            sub = df[df["animal"] == animal]
            plot_detailed_pages(pdf, sub, f"Animal {animal}")
        if df["animal"].nunique() == 1:
            for vid in sorted(df["vid_name"].unique()):
                sub = df[df["vid_name"] == vid]
                plot_detailed_pages(pdf, sub, f"Session {vid}")
    print(f"DETAILED PDF: {detailed_pdf}")
    print("\nDONE! Both PDFs generated.")
    print("   • Report.pdf → Quick overview")
    print("   • Detailed.pdf → Full clarity on every data point")

if __name__ == "__main__":
    main()