Colorado Fire Perimeter Processing

This project contains a set of ArcPy scripts used to compile, clean, and update fire perimeter data for Colorado.
The workflow supports both regular updates (e.g., new data releases) and quality control (e.g., duplicate handling, provenance tracking).
The final product feeds into the Colorado Fire Tracker and related analysis projects.

Project Structure
Colorado_Fire_Perimeters/
│
├── SCRIPTS/
│   ├── 01_download_data.py
│   ├── 02_duplicate_check.py
│   ├── 03_finalize_update.py
│
├── Fire_Perimeters/
│   ├── UPDATE/                 # Workspace for temporary update files
│   │   └── perimeter_update.gdb
│   └── Colorado_Fire_Perimeters_1984_2024.gdb
│
└── README.md

Workflow Overview
1. Download Data (01_download_data.py)
o Pulls source perimeter datasets (MTBS, FACTS, BLM, etc.)
o Loads into the UPDATE/ workspace.
o May include normalization (field names, projections).
2. Duplicate Check (02_duplicate_check.py)
o Identifies overlapping/duplicate perimeters from different sources.
o Flags true duplicates and assigns a priority ranking to sources.
o Creates duplication_check_output in perimeter_update.gdb.
3. Finalize Update (03_finalize_update.py)
o For each duplicate group, selects the “best” record by priority.
o Merges attributes and dissolves geometry.
o Constructs consistent Fire IDs (MTBS-style) if missing.
o Standardizes names, labels, and units.
o Cleans fields, calculates acres, and writes to the final geodatabase.

Requirements
• ArcGIS Pro with ArcPy (tested with Pro 3.x)
• Python packages (included with ArcGIS Pro):
o arcpy, os, re, collections

Usage
1. Clone/copy this repo into your working directory.
2. Update file paths in each script to point to your environment.
3. Run scripts in order:
python 01_download_data.py
python 02_duplicate_check.py
python 03_finalize_update.py
4. Final layer is written to:
5. Fire_Perimeters/Colorado_Fire_Perimeters_1984_2024.gdb/Colorado_Fire_Perimeters_1984_2024

Notes & Conventions
• All intermediate products are stored in UPDATE/perimeter_update.gdb.
• Fire IDs follow the MTBS convention: CO + lat + lon + YYYYMMDD.
• Untreated fires at time of visit are coded as Untreated, not Pre-Treatment.
• Scripts contain inline documentation and print status messages for traceability.

Maintenance
• Update source download links in 01_download_data.py as needed.
• Add/remove source priority rules in 02_duplicate_check.py if new datasets are included.
• Review final outputs periodically for field name drift or schema mismatches.

