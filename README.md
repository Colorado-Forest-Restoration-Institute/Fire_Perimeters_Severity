Colorado Fire Perimeter Processing



This project contains a set of ArcPy scripts used to compile, clean, and update fire perimeter data for Colorado.

The workflow supports both regular updates (e.g., new data releases) and quality control (e.g., duplicate handling, provenance tracking).

The final product feeds into the Colorado Fire Tracker and related analysis projects.



Project Structure

Colorado\_Fire\_Perimeters/

│

├── SCRIPTS/

│   ├── 01\_download\_data.py

│   ├── 02\_duplicate\_check.py

│   ├── 03\_finalize\_update.py

│

├── Fire\_Perimeters/

│   ├── UPDATE/                 # Workspace for temporary update files

│   │   └── perimeter\_update.gdb

│   └── Colorado\_Fire\_Perimeters\_1984\_2024.gdb

│

└── README.md



Workflow Overview



Download Data (01\_download\_data.py)



Pulls source perimeter datasets (MTBS, FACTS, BLM, etc.)



Loads into the UPDATE/ workspace.



May include normalization (field names, projections).



Duplicate Check (02\_duplicate\_check.py)



Identifies overlapping/duplicate perimeters from different sources.



Flags true duplicates and assigns a priority ranking to sources.



Creates duplication\_check\_output in perimeter\_update.gdb.



Finalize Update (03\_finalize\_update.py)



For each duplicate group, selects the “best” record by priority.



Merges attributes and dissolves geometry.



Constructs consistent Fire IDs (MTBS-style) if missing.



Standardizes names, labels, and units.



Cleans fields, calculates acres, and writes to the final geodatabase.



Requirements



ArcGIS Pro with ArcPy (tested with Pro 3.x)



Python packages (included with ArcGIS Pro):



arcpy, os, re, collections



Usage



Clone/copy this repo into your working directory.



Update file paths in each script to point to your environment.



Run scripts in order:



python 01\_download\_data.py

python 02\_duplicate\_check.py

python 03\_finalize\_update.py





Final layer is written to:



Fire\_Perimeters/Colorado\_Fire\_Perimeters\_1984\_2024.gdb/Colorado\_Fire\_Perimeters\_1984\_2024



Notes \& Conventions



All intermediate products are stored in UPDATE/perimeter\_update.gdb.



Fire IDs follow the MTBS convention: CO + lat + lon + YYYYMMDD.



Untreated fires at time of visit are coded as Untreated, not Pre-Treatment.



Scripts contain inline documentation and print status messages for traceability.



Maintenance



Update source download links in 01\_download\_data.py as needed.



Add/remove source priority rules in 02\_duplicate\_check.py if new datasets are included.



Review final outputs periodically for field name drift or schema mismatches.



