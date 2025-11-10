#!/usr/bin/env python3
"""
visualize_oxygen_redesigned.py
Author: G.M
Date: 2025-11-10

Creates TWO redesign versions of the per-animal summary pages:
    • Scientific (clean white, journal-ready)
    • Modern (annotated, presentation style)
Outputs saved in:
    ./output_redesign/scientific/
    ./output_redesign/modern/
"""

import json
from pathlib import Path
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

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
# One-page Plot Function
# —————————————————————————————————————————————————————————————————————
def plot_redesign(sub_df, title, style="scientific"):
    meas = sub_df.dropna(subset=["SO2_start", "SO2_end"]).copy()
    meas["delta"] = meas["SO2_start"] - meas["SO2_end"]

    mean_delta = meas["delta"].mean() if len(meas) else np.nan
    n_vess = len(sub_df)

    # figure layout
    fig = plt.figure(figsize=(16, 11))
    gs = fig.add_gridspec(2, 3, hspace=0.4, wspace=0.3)

    if style == "scientific":
        plt.style.use("default")
        bg_color = "white"
        title_color = "black"
        palette = sns.color_palette("colorblind")
    else:
        plt.style.use("seaborn-v0_8-whitegrid")
        bg_color = "#f7f7f7"
        title_color = "#222222"
        palette = ["#4472C4", "#ED7D31"]

    fig.patch.set_facecolor(bg_color)
    fig.suptitle(f"{title} — {style.title()} Style\nMean ΔSO₂ = {mean_delta:+.4f}  |  n = {n_vess:,}",
                 fontsize=18, fontweight="bold", color=title_color, y=0.97)

    # PANEL 1 – Vessel Type
    ax1 = fig.add_subplot(gs[0, 0])
    if "vessel_type" in sub_df.columns:
        counts = sub_df["vessel_type"].value_counts()
        labels = ["Capillaries" if i == 0 else "Venules" for i in counts.index]
        ax1.pie(counts, labels=labels, autopct="%1.1f%%", startangle=90,
                colors=palette)
    ax1.set_title("Vessel Type")

    # PANEL 2 – Optical Density
    ax2 = fig.add_subplot(gs[0, 1])
    sns.histplot(sub_df["OD"].dropna(), bins=40, ax=ax2, color=palette[0], kde=True)
    ax2.set_title("Optical Density (OD)")
    if style == "modern":
        ax2.text(0.05, 0.9, "Distribution of light absorption\nper vessel segment",
                 transform=ax2.transAxes, fontsize=9, color="gray")

    # PANEL 3 – ΔSO₂
    ax3 = fig.add_subplot(gs[0, 2])
    if len(meas):
        sns.histplot(meas["delta"], bins=40, ax=ax3, color=palette[1])
        ax3.axvline(0, color="black", ls="--")
        ax3.axvline(mean_delta, color="blue", ls="--",
                    label=f"Mean ΔSO₂ = {mean_delta:+.4f}")
        ax3.legend()
    ax3.set_title("Change in Oxygen Saturation (ΔSO₂)")
    if style == "modern":
        ax3.text(0.05, 0.9, "Positive = oxygen extracted", transform=ax3.transAxes,
                 fontsize=9, color="gray")

    # PANEL 4 – SO₂ In vs Out
    ax4 = fig.add_subplot(gs[1, 0])
    if len(meas):
        scatter = ax4.scatter(meas["SO2_end"], meas["SO2_start"],
                              c=meas["delta"], cmap="RdYlGn", s=40, alpha=0.8)
        mn = meas[["SO2_start", "SO2_end"]].min().min()
        mx = meas[["SO2_start", "SO2_end"]].max().max()
        ax4.plot([mn, mx], [mn, mx], "k--")
        plt.colorbar(scatter, ax=ax4, label="ΔSO₂")
    ax4.set_xlabel("Exit (%)"); ax4.set_ylabel("Entrance (%)")
    ax4.set_title("SO₂ Entrance vs Exit")

    # PANEL 5 – Length vs Volume
    ax5 = fig.add_subplot(gs[1, 1])
    if "vessel_type" in sub_df.columns:
        sns.scatterplot(data=sub_df, x="length", y="volume", hue="vessel_type",
                        palette=palette, ax=ax5, alpha=0.7)
        ax5.legend(title="Vessel Type", labels=["Capillary", "Venule"])
    ax5.set_title("Geometry (Length vs Volume)")

    # PANEL 6 – Estimated Diameter
    ax6 = fig.add_subplot(gs[1, 2])
    diam = estimated_diameter(sub_df)
    if len(diam):
        sns.histplot(diam, bins=40, ax=ax6, color="green")
        ax6.axvline(10, color="red", ls="--", label="Capillary limit (10 µm)")
        ax6.legend()
    ax6.set_title("Estimated Diameter (µm)")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


# —————————————————————————————————————————————————————————————————————
# Main
# —————————————————————————————————————————————————————————————————————
def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python visualize_oxygen_redesigned.py path/to/data.json")
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        sys.exit(f"File not found: {json_path}")

    df = load_and_flatten(json_path)

    out_base = json_path.parent / "output_redesign"
    for style in ["scientific", "modern"]:
        out_dir = out_base / style
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = out_dir / f"PerAnimal_{style}.pdf"
        with PdfPages(pdf_path) as pdf:
            for animal in sorted(df["animal"].unique()):
                sub = df[df["animal"] == animal]
                fig = plot_redesign(sub, f"Animal {animal}", style=style)
                pdf.savefig(fig, bbox_inches="tight")
                plt.close()
        print(f"Saved {pdf_path}")

if __name__ == "__main__":
    main()
