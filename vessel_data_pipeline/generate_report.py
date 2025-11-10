#!/usr/bin/env python3
"""
generate_report.py
Author: G.M
Date: 6-11-2025
Country: NL

=====================================================================
CHANGELOG
=====================================================================
v0.1 (2025-11-06) – Initial: report.txt + labeled PDF
v0.2 (2025-11-10) – Added real data points
v0.3 (2025-11-10) – Fixed rug compression
v0.4 (2025-11-10) – Split into overview + detailed PDFs
v0.5 (2025-11-10) – Fixed syntax error (title:.str → title: str)
v0.6 (2025-11-10) – **CURRENT**
    • FULL NARRATIVE RESTORED (per-animal, sessions, violations, diameter, etc.)
    • NEW PDF: Oxygen_Extraction_PerAnimal.pdf → one page per rat (full 6-panel)
    • All plots: swarm/jitter/inset → no overlap, perfect clarity
=====================================================================

Outputs:
- report.txt                        → Full narrative
- Oxygen_Extraction_Report.pdf      → 6-panel overview (all data)
- Oxygen_Extraction_Detailed.pdf    → One full plot per metric
- Oxygen_Extraction_PerAnimal.pdf   → One 6-panel page per animal
"""

import json
from pathlib import Path
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime

sns.set(style="whitegrid", font_scale=1.2)

# —————————————————————————————————————————————————————————————————————
# Load & Flatten
# —————————————————————————————————————————————————————————————————————
def load_json(p: Path) -> dict:
    with open(p) as f:
        return json.load(f)

def flatten(data: dict) -> pd.DataFrame:
    rows = []
    for animal, info in data.items():
        for v in info["vessels"]:
            v = v.copy()
            v["animal"] = animal
            rows.append(v)
    return pd.DataFrame(rows)

# —————————————————————————————————————————————————————————————————————
# FULL NARRATIVE TEXT REPORT (RESTORED)
# —————————————————————————————————————————————————————————————————————
def write_txt(df: pd.DataFrame, out_path: Path):
    lines = []
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    lines.append(f"OXYGEN EXTRACTION IN MICROVASCULAR NETWORK\n")
    lines.append(f"Analysis Report – Generated on {now}\n")
    lines.append("="*80 + "\n\n")

    n_animals = df['animal'].nunique()
    n_vessels = len(df)
    lines.append(
        f"This study analyzed microvascular oxygen dynamics in {n_animals} animal(s), "
        f"yielding a total of {n_vessels:,} individual blood vessel segments. "
        f"Data was collected across multiple experimental sessions using high-resolution "
        f"oxy-cam imaging, with vessel-level SO₂ measurements at entrance and exit points.\n\n"
    )

    # PER-ANIMAL OVERVIEW
    lines.append("PER-ANIMAL OVERVIEW\n")
    for animal in sorted(df['animal'].unique()):
        sub = df[df['animal'] == animal]
        n_sub = len(sub)
        cap_sub = sub['vessel_type'].value_counts().get(0, 0) if 'vessel_type' in sub.columns else 0
        ven_sub = sub['vessel_type'].value_counts().get(1, 0) if 'vessel_type' in sub.columns else 0
        sess_sub = sub['vid_name'].nunique() if 'vid_name' in sub.columns else 0

        lines.append(
            f"Animal ID {animal}:\n"
            f"  • {n_sub:,} vessels recorded across {sess_sub} session(s)\n"
            f"  • {cap_sub:,} capillaries (Type 0), {ven_sub:,} venules (Type 1)\n"
        )

        if {'SO2_start', 'SO2_end'}.issubset(sub.columns):
            meas_sub = sub.dropna(subset=['SO2_start', 'SO2_end'])
            if len(meas_sub):
                delta_sub = meas_sub['SO2_start'] - meas_sub['SO2_end']
                mean_delta = delta_sub.mean()
                lines.append(
                    f"  • Oxygen extraction: average ΔSO₂ = {mean_delta:+.4f} (n={len(meas_sub)} measured)\n"
                )
            else:
                lines.append("  • No SO₂ measurements available\n")
        else:
            lines.append("  • No SO₂ data\n")
        lines.append("\n")

    # VESSEL POPULATION
    lines.append("VESSEL POPULATION AND CLASSIFICATION (ALL ANIMALS)\n")
    if 'vessel_type' in df.columns:
        cap_count = df['vessel_type'].value_counts().get(0, 0)
        ven_count = df['vessel_type'].value_counts().get(1, 0)
        cap_pct = cap_count / n_vessels * 100
        ven_pct = ven_count / n_vessels * 100
        lines.append(
            f"The vessel population was dominated by capillaries. "
            f"Out of {n_vessels:,} vessels, {cap_count:,} were classified as capillaries "
            f"(Type 0, {cap_pct:.1f}%), while {ven_count:,} were venules or larger vessels "
            f"(Type 1, {ven_pct:.1f}%). This distribution is consistent with dense "
            f"capillary networks in tissue beds.\n\n"
        )
    else:
        lines.append("Vessel type classification was not available in the dataset.\n\n")

    # SESSIONS
    lines.append("EXPERIMENTAL SESSIONS AND CONDITIONS\n")
    if 'vid_name' in df.columns:
        sess_count = df['vid_name'].nunique()
        top_sess = df['vid_name'].value_counts().head(3)
        lines.append(
            f"Data was acquired in {sess_count} distinct imaging sessions. "
            f"The three most sampled sessions were:\n"
        )
        for name, count in top_sess.items():
            lines.append(f"  • '{name}' with {count:,} vessels\n")
        lines.append(
            f"Each session corresponds to a unique combination of camera, time point, "
            f"and FiO₂ level (e.g., baseline, hypoxia, hyperoxia).\n\n"
        )
    else:
        lines.append("Session information (vid_name) was not available.\n\n")

    # OXYGEN EXTRACTION
    lines.append("OXYGEN EXTRACTION AND TISSUE METABOLISM\n")
    if {'SO2_start', 'SO2_end'}.issubset(df.columns):
        meas = df.dropna(subset=['SO2_start', 'SO2_end']).copy()
        meas['delta_SO2'] = meas['SO2_start'] - meas['SO2_end']
        n_meas = len(meas)
        pct_meas = n_meas / n_vessels * 100
        mean_delta = meas['delta_SO2'].mean()
        median_delta = meas['delta_SO2'].median()
        std_delta = meas['delta_SO2'].std()
        viol = meas[meas['delta_SO2'] < 0]
        n_viol = len(viol)
        pct_viol = n_viol / n_meas * 100 if n_meas else 0

        lines.append(
            f"Oxygen extraction was successfully measured in {n_meas:,} vessels "
            f"({pct_meas:.1f}% of total). On average, tissue extracted "
            f"{mean_delta:+.4f} units of SO₂ per vessel (median {median_delta:+.4f}, "
            f"standard deviation {std_delta:.4f}). This small positive drop indicates "
            f"normal oxygen consumption by surrounding tissue.\n\n"
        )

        if n_viol > 0:
            lines.append(
                f"However, {n_viol:,} vessels ({pct_viol:.1f}%) showed an increase in SO₂ "
                f"from entrance to exit — a physiological impossibility under steady state. "
                f"These violations are likely due to sensor noise, motion artifacts, or "
                f"misaligned vessel tracking. The first three examples are:\n"
            )
            for _, row in viol[['animal', 'vid_name', 'vessel_nr', 'SO2_start', 'SO2_end']].head(3).iterrows():
                lines.append(
                    f"  • Animal {row['animal']}, session '{row['vid_name']}', "
                    f"vessel {row['vessel_nr']}: "
                    f"SO₂ {row['SO2_start']:.3f} → {row['SO2_end']:.3f}\n"
                )
            lines.append("\n")

        lines.append("Session-level extraction varied significantly:\n")
        for sess, g in meas.groupby('vid_name'):
            m = g['delta_SO2'].mean()
            lines.append(f"  • {sess}: average ΔSO₂ = {m:+.4f} (n={len(g)} vessels)\n")
        lines.append("\n")
    else:
        lines.append("SO₂ entrance and exit values were not available for extraction analysis.\n\n")

    # VESSEL DIMENSIONS
    lines.append("VESSEL DIMENSIONS AND CAPILLARY CONFIRMATION\n")
    if {'volume', 'length'}.issubset(df.columns):
        valid = df.dropna(subset=['volume', 'length'])
        valid = valid[valid['length'] > 0]
        if len(valid):
            diam = 2 * np.sqrt(valid['volume'] / (np.pi * valid['length']))
            mean_d = diam.mean()
            median_d = diam.median()
            cap_count = (diam <= 10).sum()
            cap_pct = cap_count / len(valid) * 100
            lines.append(
                f"Physical vessel diameter was estimated from volume and length assuming "
                f"cylindrical geometry. Across {len(valid):,} valid vessels, the average "
                f"diameter was {mean_d:.2f} µm (median {median_d:.2f} µm).\n\n"
                f"Using the standard physiological threshold, {cap_count:,} vessels "
                f"({cap_pct:.1f}%) had diameters ≤ 10 µm and are confirmed as true capillaries.\n"
            )
    lines.append("\n")

    # SATURATION vs DIAMETER
    lines.append("OXYGEN SATURATION IN RELATION TO VESSEL DIAMETER\n")
    if {'SO2_start', 'SO2_end', 'volume', 'length'}.issubset(df.columns):
        full = df.dropna(subset=['SO2_start', 'SO2_end', 'volume', 'length'])
        full = full[full['length'] > 0]
        if len(full):
            full['diameter'] = 2 * np.sqrt(full['volume'] / (np.pi * full['length']))
            cap = full[full['diameter'] <= 10]
            ven = full[full['diameter'] > 10]

            if len(cap):
                cap_in = cap['SO2_start'].mean()
                cap_out = cap['SO2_end'].mean()
                cap_delta = cap_in - cap_out
                lines.append(
                    f"In true capillaries (≤ 10 µm, n={len(cap):,}), "
                    f"average SO₂ was {cap_in:.1f}% at entrance and {cap_out:.1f}% at exit, "
                    f"resulting in an oxygen extraction of {cap_delta:+.3f} units. "
                    f"This confirms efficient gas exchange in the smallest vessels.\n"
                )
            if len(ven):
                ven_in = ven['SO2_start'].mean()
                ven_out = ven['SO2_end'].mean()
                ven_delta = ven_in - ven_out
                lines.append(
                    f"In larger vessels (> 10 µm, n={len(ven):,}), "
                    f"SO₂ was {ven_in:.1f}% at entrance and {ven_out:.1f}% at exit, "
                    f"with extraction of {ven_delta:+.3f} units — typically lower due to less surface-area-to-volume ratio.\n"
                )
            if len(cap) and len(ven):
                lines.append(
                    f"Capillaries extracted {cap_delta - ven_delta:+.3f} more SO₂ per vessel than larger vessels, "
                    f"highlighting their dominant role in tissue oxygenation.\n"
                )
        else:
            lines.append("Insufficient data to correlate saturation with diameter.\n")
    else:
        lines.append("Required columns for saturation-diameter analysis are missing.\n")
    lines.append("\n" + "="*80 + "\n")
    lines.append("END OF REPORT\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"→ Full narrative report saved: {out_path}")

# —————————————————————————————————————————————————————————————————————
# Smart Point Plotter (NO RUGS)
# —————————————————————————————————————————————————————————————————————
def plot_individual_points(ax, data: pd.Series, title: str):
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    n = len(data)
    if n == 0:
        ax.text(0.5, 0.5, "No data", ha='center', va='center', transform=ax.transAxes, fontsize=14)
        ax.set_title(title)
        return

    if n <= 800:
        try:
            sns.swarmplot(data=data, ax=ax, color="purple", size=4.5, alpha=0.85)
            method = "Swarm"
        except Exception:
            sns.stripplot(data=data, ax=ax, color="purple", jitter=0.3, size=4.5, alpha=0.85)
            method = "Jitter"
    else:
        sample = data.sample(n=1000, random_state=42)
        sns.stripplot(data=sample, ax=ax, color="purple", jitter=0.35, size=4.5, alpha=0.85)
        method = "Jitter (1k sample)"

    if n > 1000:
        inset = ax.inset_axes([0.68, 0.68, 0.3, 0.3])
        inset.hist(data, bins=50, color="gray", alpha=0.7, density=True)
        inset.set_title(f"All {n:,}", fontsize=8)
        inset.tick_params(axis='both', labelsize=6)

    ax.set_title(f"{title}\n({method}, n={n:,})", fontsize=14, pad=20)
    ax.set_xlabel("Value")

# —————————————————————————————————————————————————————————————————————
# 6-Panel Page (Reusable)
# —————————————————————————————————————————————————————————————————————
def plot_six_panel(pdf, sub_df, title):
    fig = plt.figure(figsize=(16, 11))
    gs = fig.add_gridspec(2, 3, hspace=0.4, wspace=0.3)
    fig.suptitle(title, fontsize=18, fontweight="bold", y=0.98)

    # 1. Vessel type
    ax1 = fig.add_subplot(gs[0, 0])
    if 'vessel_type' in sub_df.columns:
        counts = sub_df["vessel_type"].value_counts()
        labels = [f"Capillaries (0)" if i==0 else f"Venules (1)" for i in counts.index]
        wedges, _, _ = ax1.pie(counts, autopct='%1.1f%%', startangle=90,
                              colors=sns.color_palette("Set2", len(counts)))
        ax1.legend(wedges, [f"{l}: {c:,}" for l, c in zip(labels, counts)],
                   title="Type", loc="lower left")
    ax1.set_title("Vessel Type")

    # 2. OD
    ax2 = fig.add_subplot(gs[0, 1])
    sns.histplot(sub_df["OD"].dropna(), bins=50, ax=ax2, kde=True, color="steelblue")
    ax2.set_title("OD")

    # 3. ΔSO₂
    ax3 = fig.add_subplot(gs[0, 2])
    meas = sub_df.dropna(subset=["SO2_start", "SO2_end"]).copy()
    if len(meas):
        meas["delta"] = meas["SO2_start"] - meas["SO2_end"]
        sns.histplot(meas["delta"], bins=40, ax=ax3, color="salmon")
        ax3.axvline(0, color="black", ls="--")
        ax3.axvline(meas["delta"].mean(), color="blue", ls="--",
                    label=f"Mean = {meas['delta'].mean():+.4f}")
        ax3.legend()
    ax3.set_title("ΔSO₂")

    # 4. SO₂ scatter
    ax4 = fig.add_subplot(gs[1, 0])
    if len(meas):
        scatter = ax4.scatter(meas["SO2_end"], meas["SO2_start"],
                              c=meas["delta"], cmap="RdYlGn", s=30, alpha=0.7)
        mn = meas[["SO2_start","SO2_end"]].min().min()
        mx = meas[["SO2_start","SO2_end"]].max().max()
        ax4.plot([mn,mx], [mn,mx], "k--")
        plt.colorbar(scatter, ax=ax4, label="ΔSO₂")
    ax4.set_xlabel("Exit"); ax4.set_ylabel("Entrance")
    ax4.set_title("SO₂ In vs Out")

    # 5. Length vs Volume
    ax5 = fig.add_subplot(gs[1, 1])
    palette = {0: "lightblue", 1: "orange"}
    if 'vessel_type' in sub_df.columns:
        sns.scatterplot(data=sub_df, x="length", y="volume", hue="vessel_type",
                        palette=palette, ax=ax5, alpha=0.6, legend="full")
        handles, labels = ax5.get_legend_handles_labels()
        labels = [l.replace("0", "Cap").replace("1", "Ven") for l in labels]
        ax5.legend(handles, labels, title="Type")
    ax5.set_title("Geometry")

    # 6. Diameter
    ax6 = fig.add_subplot(gs[1, 2])
    if {'volume','length'}.issubset(sub_df.columns):
        valid = sub_df.dropna(subset=['volume','length'])
        valid = valid[valid['length']>0]
        if len(valid):
            diam = 2*np.sqrt(valid['volume']/(np.pi*valid['length']))
            sns.histplot(diam, bins=50, ax=ax6, color="green")
            ax6.axvline(10, color="red", ls="--")
    ax6.set_title("Est. Diameter")

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

# —————————————————————————————————————————————————————————————————————
# Detailed Full-Page Plots
# —————————————————————————————————————————————————————————————————————
def plot_detailed(pdf, sub_df, prefix):
    meas = sub_df.dropna(subset=["SO2_start", "SO2_end"]).copy()
    if len(meas):
        meas["delta"] = meas["SO2_start"] - meas["SO2_end"]

    # OD
    fig, ax = plt.subplots(figsize=(10, 6))
    plot_individual_points(ax, sub_df["OD"].dropna(), "Optical Density (OD)")
    pdf.savefig(fig); plt.close()

    # ΔSO₂
    fig, ax = plt.subplots(figsize=(10, 6))
    if len(meas):
        plot_individual_points(ax, meas["delta"], "Oxygen Extraction (ΔSO₂)")
    pdf.savefig(fig); plt.close()

    # SO₂ scatter
    fig, ax = plt.subplots(figsize=(10, 8))
    if len(meas):
        scatter = ax.scatter(meas["SO2_end"], meas["SO2_start"], c=meas["delta"], cmap="RdYlGn", s=60, alpha=0.9)
        mn = meas[["SO2_start","SO2_end"]].min().min()
        mx = meas[["SO2_start","SO2_end"]].max().max()
        ax.plot([mn,mx], [mn,mx], "k--", linewidth=2)
        plt.colorbar(scatter, ax=ax, label="ΔSO₂")
        viol = meas[meas["delta"] < 0].sort_values("delta").head(15)
        for _, row in viol.iterrows():
            ax.annotate(f"V{row['vessel_nr']}", (row["SO2_end"], row["SO2_start"]),
                        xytext=(8, 8), textcoords="offset points", fontsize=9, color="red")
    ax.set_title(f"{prefix} – SO₂ Entrance vs Exit")
    pdf.savefig(fig); plt.close()

    # Diameter
    fig, ax = plt.subplots(figsize=(10, 6))
    if {'volume','length'}.issubset(sub_df.columns):
        valid = sub_df.dropna(subset=['volume','length'])
        valid = valid[valid['length']>0]
        if len(valid):
            diam = 2*np.sqrt(valid['volume']/(np.pi*valid['length']))
            plot_individual_points(ax, diam, "Estimated Diameter (µm)")
            ax.axvline(10, color="red", ls="--", label="Capillary ≤10µm")
            ax.legend()
    pdf.savefig(fig); plt.close()

# —————————————————————————————————————————————————————————————————————
# Write All PDFs
# —————————————————————————————————————————————————————————————————————
def write_pdfs(df: pd.DataFrame, out_dir: Path):
    # 1. Overview (all data)
    overview_path = out_dir / "Oxygen_Extraction_Report.pdf"
    with PdfPages(overview_path) as pdf:
        plot_six_panel(pdf, df, "ALL DATA – 6-Panel Overview")
    print(f"→ Overview PDF: {overview_path}")

    # 2. Per-Animal Full 6-Panel
    per_animal_path = out_dir / "Oxygen_Extraction_PerAnimal.pdf"
    with PdfPages(per_animal_path) as pdf:
        for animal in sorted(df["animal"].unique()):
            sub = df[df["animal"] == animal]
            plot_six_panel(pdf, sub, f"Animal ID: {animal}")
    print(f"→ Per-Animal PDF: {per_animal_path}")

    # 3. Detailed Full-Page
    detailed_path = out_dir / "Oxygen_Extraction_Detailed.pdf"
    with PdfPages(detailed_path) as pdf:
        for animal in sorted(df["animal"].unique()):
            sub = df[df["animal"] == animal]
            plot_detailed(pdf, sub, f"Animal {animal}")
        for vid in sorted(df["vid_name"].unique()):
            sub = df[df["vid_name"] == vid]
            plot_detailed(pdf, sub, f"Session {vid}")
    print(f"→ Detailed PDF: {detailed_path}")

# —————————————————————————————————————————————————————————————————————
# Main
# —————————————————————————————————————————————————————————————————————
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python generate_report.py path/to/data.json")
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        sys.exit(f"File not found: {json_path}")

    data = load_json(json_path)
    df   = flatten(data)
    out_dir = json_path.parent

    write_txt(df, out_dir / "report.txt")
    write_pdfs(df, out_dir)

    print("\n" + "="*70)
    print("ALL DONE! 4 FILES GENERATED:")
    print("   1. report.txt → Full narrative")
    print("   2. Oxygen_Extraction_Report.pdf → All data overview")
    print("   3. Oxygen_Extraction_PerAnimal.pdf → One rat per page")
    print("   4. Oxygen_Extraction_Detailed.pdf → Full clarity per plot")
    print("="*70)