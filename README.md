# Colorado Fire Perimeter Processing

This project contains a set of **ArcPy scripts** used to compile, clean, and update fire perimeter data for Colorado.  
The workflow supports both **regular updates** (e.g., new data releases) and **quality control** (e.g., duplicate handling, provenance tracking).  
The final product feeds into the **Colorado Fire Tracker** and related analysis projects.  

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