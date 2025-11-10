#!/usr/bin/env python3
"""
excel_to_nested_json.py

Description:
    Converts a large Excel (.xlsx) file with animal vessel data into a
    beautifully nested JSON, grouped by animal (e.g., subject_id).
    
    Features:
    - Auto-creates output folder named after the input file (without .xlsx)
    - Saves JSON as: <folder>/data.json
    - Clear, step-by-step terminal feedback
    - Handles huge files safely
    - Auto-detects animal column
    - Preserves ALL columns from Excel in the JSON (except grouping key)
    
    Author: G.M
    Date: 6-11-2025
    Version: 0.1

"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def print_step(msg: str):
    """Print a clear step message."""
    print(f"\n[STEP] {msg}")


def load_excel(path: Path, sheet_name: str | int = 0) -> pd.DataFrame:
    print_step(f"Loading Excel file: {path.name}")
    try:
        df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
        print(f"   → Loaded {len(df):,} rows, {len(df.columns)} columns")
    except Exception as e:
        sys.exit(f"ERROR: Failed to read Excel file: {e}")

    # Clean up empty rows/columns
    before = len(df)
    df.dropna(how="all", axis=0, inplace=True)
    df.dropna(how="all", axis=1, inplace=True)
    after = len(df)
    if before != after:
        print(f"   → Removed {before - after:,} empty rows")
    return df


def detect_animal_column(df: pd.DataFrame) -> str:
    print_step("Detecting animal identifier column...")
    candidates = [
        col for col in df.columns
        if "subject" in col.lower() or "id" in col.lower() or "animal" in col.lower()
    ]
    if not candidates:
        sys.exit("ERROR: No column with 'subject', 'id', or 'animal' found. Use --animal-col")

    # Pick column with fewest unique values
    col = min(candidates, key=lambda c: df[c].nunique(dropna=True))
    unique_count = df[col].nunique(dropna=True)
    print(f"   → Using column: '{col}' ({unique_count:,} unique animals)")
    if unique_count > 100:
        print(f"   ⚠️  WARNING: {unique_count} unique values — is this really per-animal?")
    return col


def build_nested(df: pd.DataFrame, animal_col: str) -> dict:
    print_step(f"Grouping data by '{animal_col}' and nesting vessels...")
    nested = {}
    total_vessels = 0

    for animal, group in df.groupby(animal_col):
        animal_key = str(animal)
        vessels = group.drop(columns=[animal_col]).to_dict(orient="records")
        total_vessels += len(vessels)

        # Optional summary stats
        summary = {
            "n_vessels": len(vessels),
        }
        if "SO2_start" in group.columns:
            summary["mean_SO2_start"] = round(group["SO2_start"].mean(), 3)
        if "SO2_end" in group.columns:
            summary["mean_SO2_end"] = round(group["SO2_end"].mean(), 3)

        nested[animal_key] = {
            "vessels": vessels,
            "summary": summary
        }

    print(f"   → Created {len(nested):,} animal entries with {total_vessels:,} total vessel records")
    return nested


def save_json(nested_data: dict, output_dir: Path):
    json_path = output_dir / "data.json"
    print_step(f"Saving nested JSON to: {json_path}")
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            # json.dump(nested_data, f, indent=2, ensure_ascii=False)
            json.dump(nested, f, indent=2, ensure_ascii=False, default=lambda x: None if pd.isna(x) else x)
        print(f"   → JSON saved successfully! ({json_path})")
    except Exception as e:
        sys.exit(f"ERROR: Failed to write JSON: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Excel → Nested JSON (grouped by animal) with auto folder output"
    )
    parser.add_argument("excel", type=Path, help="Path to input .xlsx file")
    parser.add_argument(
        "-s", "--sheet", default=0, help="Sheet name or index (default: 0)"
    )
    parser.add_argument(
        "-a", "--animal-col", default=None, help="Animal column name (auto-detected if omitted)"
    )
    args = parser.parse_args()

    # Validate input
    if not args.excel.exists():
        sys.exit(f"ERROR: File not found: {args.excel}")
    if not args.excel.suffix.lower() == ".xlsx":
        print(f"WARNING: File extension is '{args.excel.suffix}', expected .xlsx")

    # Load data
    df = load_excel(args.excel, args.sheet)

    # Detect or use animal column
    animal_col = args.animal_col or detect_animal_column(df)

    # Build nested structure
    nested = build_nested(df, animal_col)

    # Create output folder: same as Excel name (without .xlsx)
    base_name = args.excel.stem  # e.g., "MyExperiment_v2" → folder name
    output_dir = args.excel.parent / base_name
    output_dir.mkdir(exist_ok=True)
    print_step(f"Output folder: {output_dir}")

    # Save JSON
    save_json(nested, output_dir)

    # Final summary
    print("\n" + "="*60)
    print("CONVERSION COMPLETE!")
    print(f"   Input Excel : {args.excel}")
    print(f"   Output Dir  : {output_dir}")
    print(f"   JSON File   : {output_dir / 'data.json'}")
    print(f"   Animals     : {len(nested):,}")
    print(f"   Total Rows  : {sum(len(a['vessels']) for a in nested.values()):,}")
    print("="*60)


if __name__ == "__main__":
    # Run: pip install pandas openpyxl
    main()