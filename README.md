# Colorado Fire Perimeter Processing

This project contains a set of **ArcPy scripts** used to compile, clean, and update fire perimeter data for Colorado.  
The workflow supports both **regular updates** (e.g., new data releases) and **quality control** (e.g., duplicate handling, provenance tracking).  

The final product feeds into the **Colorado Fire Tracker** and related analysis projects.  

---

## Workflow Overview

1. **Download Data (`01_download_data.py`)**  
   - Pulls source perimeter datasets (MTBS, FACTS, BLM, etc.)  
   - Loads into the `UPDATE/` workspace.  
   - May include normalization (field names, projections).  

2. **Duplicate Check (`02_duplicate_check.py`)**  
   - Identifies overlapping/duplicate perimeters from different sources.  
   - Flags true duplicates and assigns a `priority` ranking to sources.  
   - Creates `duplication_check_output` in `perimeter_update.gdb`.  

3. **Finalize Update (`03_finalize_update.py`)**  
   - For each duplicate group, selects the “best” record by priority.  
   - Merges attributes and dissolves geometry.  
   - Constructs consistent **Fire IDs** (MTBS-style) if missing.  
   - Standardizes names, labels, and units.  
   - Cleans fields, calculates acres, and writes to the final geodatabase.  

---

## Project Structure

```
Fire_Perimeters/
│
├── SCRIPTS/ 
│├── 1_data_attribute_mapping.py
│├── 2_tag_duplicates.py
│├── 3_finalize_perimeters.py
├── README.md   
├── UPDATE/     ← working geodatabase folder
│├── dwnld_perimeters.gdb
│├── perimeter_update.gdb
│├── scratch
```

---

## Requirements

- ArcGIS Pro (with arcpy)  
- Python 3.x (as installed with ArcGIS Pro)  
- pandas, numpy  

---

## Usage

1. Run scripts in order:  
   ```
   python 01_download_data.py
   python 02_duplicate_check.py
   python 03_finalize_update.py
   ```
2. Final output will be written to:  
   ```
   Colorado_Fire_Perimeters_1984_2024.gdb/Colorado_Fire_Perimeters_1984_2024
   ```

---

## Notes

- This repository is designed for repeatable updates as new fire perimeter data becomes available.  