#!/usr/bin/env python3
"""
analyze_vessels.py
Author: G.M
Date: 6-11-2025
Version: 0.1

Robust analysis:
- Safe column access
- Delta SO2 calculated only when both start/end exist
- Per-animal + per-vid_name oxygen extraction
- No KeyError crashes
"""

import json
from pathlib import Path
import sys
import pandas as pd
import numpy as np

def load_json(json_path: Path) -> dict:
    print(f"[LOAD] Reading: {json_path}")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        animals = list(data.keys())
        print(f"   → {len(animals)} animal(s): {', '.join(animals)}")
        return data
    except Exception as e:
        sys.exit(f"ERROR: {e}")

def flatten_vessels(data: dict) -> pd.DataFrame:
    print("[FLATTEN] Building DataFrame...")
    rows = []
    for animal, info in data.items():
        for v in info["vessels"]:
            v = v.copy()
            v["animal"] = animal
            rows.append(v)
    df = pd.DataFrame(rows)
    print(f"   → {len(df):,} vessels")
    return df

def safe_stats(series: pd.Series, name: str):
    if series.empty:
        return f"{name}: (no data)"
    return (f"{name}: "
            f"mean={series.mean():.4f}, "
            f"median={series.median():.4f}, "
            f"std={series.std():.4f}, "
            f"n={len(series)}")

def analyze(df: pd.DataFrame):
    print("\n" + "="*70)
    print("OXYGEN EXTRACTION & VESSEL ANALYSIS")
    print("="*70)

    # 1. Basics
    print(f"\n[1] ANIMALS: {df['animal'].nunique()}")
    print(f"[1] TOTAL VESSELS: {len(df):,}")

    # 2. Vessel Types
    print(f"\n[2] VESSEL TYPES")
    if 'vessel_type' in df.columns:
        type_counts = df['vessel_type'].value_counts().sort_index()
        for t, c in type_counts.items():
            print(f"    Type {t}: {c:,} ({c/len(df)*100:5.2f}%)")
    else:
        print("    (no vessel_type column)")

    # 3. Sessions
    print(f"\n[3] SESSIONS (vid_name)")
    if 'vid_name' in df.columns:
        for name, count in df['vid_name'].value_counts().items():
            print(f"    {name}: {count:,} vessels")
    else:
        print("    (no vid_name)")

    # 4. OXYGEN EXTRACTION (MAIN FOCUS)
    print(f"\n[4] OXYGEN EXTRACTION (SO2_start → SO2_end)")
    if 'SO2_start' in df.columns and 'SO2_end' in df.columns:
        measured = df.dropna(subset=['SO2_start', 'SO2_end']).copy()
        measured['delta_SO2'] = measured['SO2_start'] - measured['SO2_end']

        print(f"    Measured vessels: {len(measured):,} ({len(measured)/len(df)*100:.2f}%)")
        print(f"    {safe_stats(measured['delta_SO2'], 'ΔSO₂')}")

        violations = measured[measured['delta_SO2'] < 0]
        print(f"    VIOLATIONS (O₂ increase): {len(violations)}")

        if len(violations) > 0:
            print("    First 3 violations:")
            print(violations[['animal', 'vid_name', 'vessel_nr', 'SO2_start', 'SO2_end', 'delta_SO2']]
                  .head(3).to_string(index=False))

        # Per session extraction
        if 'vid_name' in measured.columns:
            print(f"\n    PER SESSION EXTRACTION:")
            for sess, g in measured.groupby('vid_name'):
                print(f"      • {sess}: {safe_stats(g['delta_SO2'], 'ΔSO₂')}")

    else:
        print("    (SO2_start or SO2_end missing)")

    # 5. OD
    print(f"\n[5] OD (optical density)")
    if 'OD' in df.columns:
        od = df['OD']
        print(f"    {safe_stats(od, 'OD')}")
        neg = (od < 0).sum()
        if neg:
            print(f"    ⚠️  NEGATIVE OD: {neg} values")
    else:
        print("    (no OD)")

    # 6. Geometry
    print(f"\n[6] GEOMETRY")
    for col in ['length', 'volume']:
        if col in df.columns:
            s = df[col]
            print(f"    {col}: mean={s.mean():.1f}, range=[{s.min():.1f}–{s.max():.1f}]")

    # 7. Estimated diameter
    print(f"\n[7] ESTIMATED DIAMETER (volume & length → µm)")
    if 'volume' in df.columns and 'length' in df.columns:
        valid = df.dropna(subset=['volume', 'length'])
        valid = valid[valid['length'] > 0]
        if len(valid) > 0:
            diam = 2 * np.sqrt(valid['volume'] / (np.pi * valid['length']))
            print(f"    Valid: {len(valid):,}")
            print(f"    Mean diameter: {diam.mean():.2f} µm")
            print(f"    Median: {diam.median():.2f} µm")
        else:
            print("    (no valid data)")
    else:
        print("    (missing volume or length)")

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

# ——— Run ———
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python analyze_vessels.py path/to/data.json")

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        sys.exit(f"File not found: {json_path}")

    data = load_json(json_path)
    df = flatten_vessels(data)
    analyze(df)