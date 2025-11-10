# **Vessel Data Pipeline** – README & User Guide  

**Author:** G.M  
**Date:** November 10, 2025  
**Country:** NL  
**X:** @Artifioicus  

---

## OVERVIEW

This repository contains a **complete, publication-ready pipeline** for analyzing **microvascular oxygen extraction** from imaging data (oxy-cam) in rats.

It converts Excel → JSON → analyzes → visualizes → generates **3 PDFs + full narrative report**.

---

## FOLDER STRUCTURE

```
vessel_data_pipeline/
│
├── data/                     ← Put your Excel/JSON here
│   └── example_data.json
│
├── scripts/
│   ├── excel_to_nested_json.py   ← Convert Excel → nested JSON
│   ├── analyze_vessels.py        ← Terminal stats (debug)
│   ├── visualize_oxygen.py       ← 6-panel overview + detailed plots
│   └── generate_report.py        ← Full report + 3 PDFs
│
├── output/                   ← Auto-generated
│   ├── report.txt
│   ├── Oxygen_Extraction_Report.pdf
│   ├── Oxygen_Extraction_PerAnimal.pdf
│   └── Oxygen_Extraction_Detailed.pdf
│
├── environment.yml           ← Conda environment
└── README.md                 ← This file
```

---

## STEP 1: SETUP ENVIRONMENT

### 1.1 Install Conda (if not already)

```bash
# Miniconda (recommended)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

### 1.2 Create & Activate Environment

```bash
# From project root
conda env create -f environment.yml
conda activate vessel_pipeline
```

> **Success?** You should see `(vessel_pipeline)` in your terminal.

---

## STEP 2: PREPARE YOUR DATA

### Option A: You have **Excel (.xlsx)**

```bash
cp your_data.xlsx data/raw_data.xlsx
```

### Option B: You already have **JSON**

```bash
cp your_data.json data/data.json
```

---

## STEP 3: RUN THE PIPELINE

### 3.1 Convert Excel → JSON (if needed)

```bash
python scripts/excel_to_nested_json.py data/raw_data.xlsx
```

**Output:**  
`data/raw_data/data.json` ← nested, grouped by animal

---

### 3.2 Run Full Report (RECOMMENDED)

```bash
python scripts/generate_report.py data/data.json
```

**Generates 4 files in `output/`**:

| File | Description |
|------|-------------|
| `report.txt` | **Full narrative** (per-animal, sessions, violations, diameter, etc.) |
| `Oxygen_Extraction_Report.pdf` | 6-panel **overview of all data** |
| `Oxygen_Extraction_PerAnimal.pdf` | **One full page per rat** – crystal clear individual view |
| `Oxygen_Extraction_Detailed.pdf` | **One full plot per metric** (OD, ΔSO₂, SO₂ scatter, diameter) with **no overlapping points** |

---

### 3.3 Quick Debug (Terminal Only)

```bash
python scripts/analyze_vessels.py data/data.json
```

Shows stats in terminal (vessel counts, ΔSO₂, violations, etc.)

---

### 3.4 Visualization Only

```bash
python scripts/visualize_oxygen.py data/data.json
```

Generates only the **overview + detailed PDFs** (no text report)

---

## SCRIPT DETAILS

| Script | What It Does | Key Features |
|-------|--------------|-------------|
| `excel_to_nested_json.py` | Converts `.xlsx` → nested `data.json` grouped by `animal` | Auto-detects animal column<br>Creates output folder<br>Handles 100k+ rows |
| `analyze_vessels.py` | Terminal-only stats | Fast debugging<br>Shows violations, per-session ΔSO₂ |
| `visualize_oxygen.py` | 6-panel plots + detailed views | Smart point display (swarm/jitter/in fset)<br>No rugplot compression |
| `generate_report.py` | **Main script** – does **everything** | Full narrative `report.txt`<br>3 PDFs<br>Per-animal pages |

---

## ENVIRONMENT.YML (Dependencies)

```yaml
name: vessel_pipeline
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pandas
  - numpy
  - matplotlib
  - seaborn
  - openpyxl
  - jupyter
```

Install with:

```bash
conda env create -f environment.yml
```

---

## TRO ~

### Troubleshooting

| Issue | Solution |
|------|----------|
| `File not found` | Check path: `data/data.json` must exist |
| `KeyError: 'SO2_start'` | Your JSON is missing columns → check Excel |
| `MemoryError` | Use smaller dataset or `sample(n=1000)` in code |
| `Swarmplot failed` | Falls back to `stripplot` automatically |
| `PDF blank` | Run with `--no-sandbox` in Jupyter or check Matplotlib backend |
| `Conda not found` | Install Miniconda: <https://docs.conda.io/en/latest/miniconda.html> |

---

## EXAMPLE WORKFLOW (Copy-Paste)

```bash
# 1. Setup
conda activate vessel_pipeline

# 2. Convert Excel
python scripts/excel_to_nested_json.py data/my_experiment.xlsx

# 3. Generate full report
python scripts/generate_report.py data/my_experiment/data.json

# 4. Open results
xdg-open output/Oxygen_Extraction_PerAnimal.pdf
```

---

## OUTPUT EXPLAINED

### `report.txt`

- Per-animal vessel counts
- Capillary vs venule
- Average ΔSO₂ per animal
- Session-level extraction
- **Violations listed** (negative ΔSO₂)
- Diameter statistics
- Capillary confirmation (≤10µm)

### `Oxygen_Extraction_Report.pdf`

- **One page**: all animals combined
- 6 small panels

### `Oxygen_Extraction_PerAnimal.pdf`

- **One page per rat**
- Full 6-panel layout
- **Perfect for presentations**

### `Oxygen_Extraction_Detailed.pdf`

- **One full page per plot**
- OD, ΔSO₂, SO₂ scatter, diameter
- **No point overlap** – uses swarm/jitter

---

## TIPS FOR PROFESSOR / REVIEW

- Use **`Oxygen_Extraction_PerAnimal.pdf`** in talks
- Show **`report.txt`** for methods/results
- Use **`Detailed.pdf`** for supplemental figures

---

## FUTURE IDEAS (Optional)

| Feature | Command |
|-------|--------|
| Interactive HTML | `jupyter nbconvert --to html` |
| Web Dashboard | Add Streamlit |
| Auto-email PDF | Add `smtplib` |

---

## FINAL WORDS

> **You now have a professional, reproducible, publication-ready pipeline.**  
> No more compressed points. No more short reports.  
> Just **clear science**.

---

**Need help?**  
DM @Artifioicus on X or open an issue.

**Star this repo if it helped!** 🌟

---

**Generated on:** November 10, 2025 at 10:17 AM CET  
**Version:** v0.6 (stable)

---

## 🆕 NEW SCRIPT – `visualize_oxygen_redesigned_paired.py`

A redesigned and extended visualization module that builds upon `visualize_oxygen_redesigned.py`.

### **Description**

Generates enhanced per-animal reports with:

- **Panel 7** → *Paired SO₂ (In → Out)* for all vessels
- **Automatic separation** of small (≤10 µm) and large (>10 µm) vessels
- **Mean ± SEM** markers and **paired t-test** results
- **Adaptive axis scaling** to avoid compressed data
- **Standalone PDFs** for each group and style (Scientific & Modern)
- **Connection table CSV** mapping vessel–correspondence pairs (`corresp`)

### **Usage**

```bash
python scripts/visualize_oxygen_redesigned_paired.py data/data.json
```

**Generates:**

```
output_redesign/
├── Vessel_Connections_Report.csv
├── scientific/
│   └── PerAnimal_scientific.pdf
├── modern/
│   └── PerAnimal_modern.pdf
└── paired/
    ├── scientific/
    │   ├── Paired_SO2_Animal_<id>.pdf
    │   ├── Paired_SO2_Small_Animal_<id>.pdf
    │   └── Paired_SO2_Large_Animal_<id>.pdf
    └── modern/
        ├── Paired_SO2_Animal_<id>.pdf
        ├── Paired_SO2_Small_Animal_<id>.pdf
        └── Paired_SO2_Large_Animal_<id>.pdf
```

### **Key Features**

| Feature             | Description                                                                   |
| ------------------- | ----------------------------------------------------------------------------- |
| Panel 7             | Adds Paired SO₂ (In→Out) with mean ± SEM and p-values                         |
| Small / Large plots | Separate standalone PDFs for ≤10 µm and >10 µm vessels                        |
| Adaptive scaling    | Prevents compressed data points automatically                                 |
| Statistical output  | Paired t-test per group (displays *p*-value)                                  |
| Connection report   | Exports `Vessel_Connections_Report.csv` mapping `vessel_nr` ↔ `corresp` pairs |

---

## 🆕 NEW OUTPUTS

### **`Vessel_Connections_Report.csv`**

A structured CSV summarizing all vessel links via the `corresp` column.

| Animal | Vessel | Connected_To | SO2_start | SO2_end | Delta_SO2 |
| ------ | ------ | ------------ | --------- | ------- | --------- |
| 1      | 45     | 46           | 0.82      | 0.79    | +0.03     |
| 1      | 46     | 47           | 0.79      | 0.77    | +0.02     |

Saved automatically in:

```
output_redesign/Vessel_Connections_Report.csv
```

Use this to trace connectivity across the microvascular network.

---

## 🆕 UPDATED SCRIPT TABLE

| Script                                  | What It Does                                                     | Key Features                                                                                                                         |
| --------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `visualize_oxygen_redesigned_paired.py` | Extended redesign including Paired SO₂ panel + connection report | Adds Panel 7 (Paired SO₂ In→Out)<br>Generates per-animal, small-only, and large-only PDFs<br>Exports `Vessel_Connections_Report.csv` |

---

## 🆕 TIPS

- **Use the “Paired” PDFs** for presentations comparing in/out oxygen extraction across vessel sizes.
- **Check `Vessel_Connections_Report.csv`** to validate connectivity and trace flow direction.
- Use the **Scientific style** for journals and the **Modern style** for slides.

---

**Version:** v0.7 (extended paired release)
**Updated:** November 11 2025
