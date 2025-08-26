"""
Colorado Fire Perimeter Find Duplicate Perimeters & Provenance Script
--------------------------------------------------------

This script identifies duplicate or overlapping fire perimeter records across
multiple datasets, normalizes fire names, and assigns a common provenance ID
to groups of perimeters that represent the same fire event. It also creates a
provenance table to track the original source IDs for each grouped perimeter.

Input:
    - raw_Colorado_Fire_Perimeters_duplicates
        (output from '1_data_attribute_mapping.py')

Outputs:
    - dup_check_output (feature class with grouping fields and Provenance_IDs)
    - Fire_Perimeter_Provenance (table linking Provenance_IDs to original
      source identifiers and attributes)

Example directory structure:

    E:\CFRI\Colorado_Fire_Severity\Fire_Perimeters\
        ├── UPDATE\
        │     ├── dwnld_perimeters.gdb\
        │     └── perimeter_update.gdb\
        │            ├── raw_Colorado_Fire_Perimeters_duplicates
        │            ├── dup_check_output                 (output)
        │            └── Fire_Perimeter_Provenance        (output)

What the script does:
    1. Replaces inconsistent fire name strings (e.g., "Unknown", "Unnamed") with NULL
    2. Normalizes fire labels (removing suffixes, non-alphanumeric chars, etc.)
    3. Builds proximity groups using a 500m near table (same year only)
    4. Groups by:
        - Proximity + Name similarity
        - Proximity + Start date
    5. Assigns a Provenance_ID to each group (or unique ID for ungrouped perimeters)
    6. Creates a provenance table mapping Provenance_IDs back to original source IDs
    7. Outputs a cleaned perimeter feature class with duplication fields

Future enhancements will include tuning similarity thresholds.
"""

import arcpy
import os
import re
from collections import defaultdict
from difflib import SequenceMatcher

# Configuration
base_dir = r'E:\CFRI\Colorado_Fire_Severity\Fire_Perimeters'
update_dir = os.path.join(base_dir, 'UPDATE')
scratch_gdb = os.path.join(update_dir, 'perimeter_update.gdb')

arcpy.env.workspace = scratch_gdb
arcpy.env.overwriteOutput = True

# File and Layer paths
input_fc = os.path.join(scratch_gdb, 'raw_Colorado_Fire_Perimeters_duplicates')
#input_fc = os.path.join(scratch_gdb, "Colorado_Fire_Perimeters_duplicates_test")  #TEST FILE
temp_copy = os.path.join(scratch_gdb, 'wrk_fires_start')
provenance_table = os.path.join(scratch_gdb, "Fire_Perimeter_Provenance")
final_output = os.path.join(scratch_gdb, 'duplication_check_output')

# Create a copy of all fire perimeters as duplicates
arcpy.CopyFeatures_management(input_fc, temp_copy)
oid_field = [f.name for f in arcpy.ListFields(temp_copy) if f.type == "OID"][0]

# Replace text "Unknown" or similar with Null to create consistency
print("Replacing unnamed attributes with NULL")
fields = [f.name for f in arcpy.ListFields(temp_copy) if f.type in ["String"]]
with arcpy.da.UpdateCursor(temp_copy, fields) as cursor:
    for row in cursor:
        new_row = []
        for value in row:
            if isinstance(value, str) and value.strip().upper() in ["UNKNOWN", "UNNAMED", "UNK", "N/A"]:
                new_row.append(None)
            else:
                new_row.append(value)
        cursor.updateRow(new_row)


# --- CLEAN STRINGS ---
def normalize_label(label_str): 
    if not label_str:
        return ""
    label_new = label_str.strip()
    # Strip trailing "wfu", "fire", or "wildfire"
    label_new = re.sub(r'\s+(wfu|(wild)?fire)$', '', label_new, flags=re.IGNORECASE)
    # Remove trailing prescribed fire unit numbers like "UNIT 2", "U2", "UNIT2"
    label_new = re.sub(r'\s+U(NIT)?[\s\w\-\\/]*$', '', label_new, flags=re.IGNORECASE)
    # Remove all non-alphanumeric characters
    label_new = re.sub(r'[^A-Za-z0-9]', '', label_new)
    return label_new.upper()


def label_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


# --- Union-find/ connected components ---
def find_root(node, parent):
    while parent[node] != node:
        parent[node] = parent[parent[node]]
        node = parent[node]
    return node


def union(a, b, parent):
    ra, rb = find_root(a, parent), find_root(b, parent)
    if ra != rb:
        parent[rb] = ra


# Prep Fields
print("Adding grouping and ID fields")
group_prox = "group_prox"
group_name = "group_name"
group_date = "group_date"
true_duplicate_field = "True_Duplicate"
norm_label = "Norm_Label"
provenance_field = "Provenance_ID"

for fld in [group_prox, group_name, group_date, true_duplicate_field, norm_label, provenance_field]:
    if fld not in [f.name for f in arcpy.ListFields(temp_copy)]:
        arcpy.AddField_management(temp_copy, fld, "LONG" if fld != norm_label else "TEXT")

# Build proximity-based groups
near_table = os.path.join("in_memory", "near_table")
arcpy.GenerateNearTable_analysis(temp_copy, temp_copy, near_table, "500 Meters", "NO_LOCATION", "NO_ANGLE", "ALL", 0)
print(f"Generated near table: {arcpy.GetCount_management(near_table)[0]} proximity pairs")

# Map OID to year
print("Building OID to Year mapping...")
oid_to_year = {row[0]: row[1] for row in arcpy.da.SearchCursor(temp_copy, [oid_field, "n_Year"])}

# Build adjacency list with year constraint
adj = defaultdict(set)
print("Filtering near pairs by year and building adjacency list")
with arcpy.da.SearchCursor(near_table, ["IN_FID", "NEAR_FID"]) as cursor:
    for in_fid, near_fid in cursor:
        if in_fid == near_fid:
            continue
        # Only connect if they are from the same year
        if oid_to_year.get(in_fid) == oid_to_year.get(near_fid):
            adj[in_fid].add(near_fid)
            adj[near_fid].add(in_fid)

# Create parent dict
all_oids = set(adj.keys())
parent = {oid: oid for oid in all_oids}
for a in all_oids:
    for b in adj[a]:
        union(a, b, parent)

# Assign group IDs
root_to_group = {}
group_counter = 1
oid_to_group = {}

for oid in all_oids:
    root = find_root(oid, parent)
    if root not in root_to_group:
        root_to_group[root] = group_counter
        group_counter += 1
    oid_to_group[oid] = root_to_group[root]

# Update group ID field
with arcpy.da.UpdateCursor(temp_copy, [oid_field, group_prox]) as cursor:
    for row in cursor:
        group_id = oid_to_group.get(row[0])
        if group_id:
            print(f"Assigning Prox_Group {group_id} to OID {row[0]}")
            row[1] = group_id
            cursor.updateRow(row)

# Update norm_label
with arcpy.da.UpdateCursor(temp_copy, ["n_Fire_Label", "Norm_Label"]) as cursor:
    for row in cursor:
        row[1] = normalize_label(row[0]) 
        cursor.updateRow(row)

# Group by proximity field and same normalized label
print("Group perimeters by proximity and normalized label")
name_match_groups = defaultdict(list)
with arcpy.da.SearchCursor(temp_copy, [oid_field, group_prox, norm_label]) as cursor:
    for oid, group, label in cursor:
        print(f"OID: {oid}  group: {group}  label: {label}")
        if group is not None and label:
            name_match_groups[group].append((oid, label))

group_id_counter = 1
name_match_dict = {}

for key, oid_label_list in name_match_groups.items():
    clusters = []
    for oid, label in oid_label_list:
        placed = False
        for cluster in clusters:
            if label_similarity(label, cluster[0][1]) > 0.85:
                cluster.append((oid, label))
                placed = True
                break
        if not placed:
            clusters.append([(oid, label)])

    for cluster in clusters:
        for oid, _ in cluster:
            name_match_dict[oid] = group_id_counter
        group_id_counter += 1

with arcpy.da.UpdateCursor(temp_copy, [oid_field, group_name]) as cursor:
    for row in cursor:
        row[1] = name_match_dict.get(row[0])
        cursor.updateRow(row)

# Group by proximity field and same start month and start day
print("Group perimeters by proximity and start date (month/year)")
date_match_groups = defaultdict(list)
with arcpy.da.SearchCursor(temp_copy, [oid_field, group_prox, "n_StartMonth", "n_StartDay"]) as cursor:
    for oid, group, month, day in cursor:
        print(f"OID: {oid}  group: {group}  month/day: {month}/{day}")
        if group is None or month is None or day is None:
            continue
        date_match_groups[(group, month, day)].append(oid)

oid_to_group_date = {}
group_date_id_counter = 1

for key, oid_list in date_match_groups.items():
    for oid in oid_list:
        oid_to_group_date[oid] = group_date_id_counter
    group_date_id_counter += 1

with arcpy.da.UpdateCursor(temp_copy, [oid_field, group_date]) as cursor:
    for row in cursor:
        row[1] = oid_to_group_date.get(row[0])
        cursor.updateRow(row)

# Group by proximity field and WHERE LABEL or DATE are the same
print("Group perimeters by proximity and LABEL or START DATE (month/year)")
duplicate_groups = defaultdict(list)
with arcpy.da.SearchCursor(temp_copy, [oid_field, group_prox, group_name, group_date]) as cursor:
    for oid, group, name, date in cursor:
        print(f"OID: {oid}  group: {group}  label: {name}   month/day: {date}")
        if group is None:
            continue
        if name is not None:
            duplicate_groups[('name', group, name)].append(oid)
        if date is not None:
            duplicate_groups[('date', group, date)].append(oid)

oid_to_dupl = {}
dupl_id_counter = 1

for key, oid_list in duplicate_groups.items():
    for oid in oid_list:
        if oid not in oid_to_dupl:
            oid_to_dupl[oid] = dupl_id_counter
    dupl_id_counter += 1

with arcpy.da.UpdateCursor(temp_copy, [oid_field, true_duplicate_field]) as cursor:
    for row in cursor:
        dupl_val = oid_to_dupl.get(row[0])
        if dupl_val:
            row[1] = dupl_val
            cursor.updateRow(row)

# Assign Provenance_ID based on final True Duplicate field or oid counter when not grouped
max_oid = max(row[0] for row in arcpy.da.SearchCursor(temp_copy, [oid_field]))
oid_counter = 1
with arcpy.da.UpdateCursor(temp_copy, [oid_field, true_duplicate_field, "Provenance_ID"]) as cursor:
    for row in cursor:
        if row[1] is not None:
            row[2] = row[1]
        else:
            row[2] = max_oid + oid_counter
            oid_counter += 1
        cursor.updateRow(row)

# Create provenance table to track all contributing source IDs
print("Creating provenance table")
arcpy.CreateTable_management(scratch_gdb, os.path.basename(provenance_table))
arcpy.AddField_management(provenance_table, "Provenance_ID", "LONG")
arcpy.AddField_management(provenance_table, "Original_ID", "TEXT", 100)
arcpy.AddField_management(provenance_table, "Source", "TEXT", 50)
arcpy.AddField_management(provenance_table, "Norm_Label", "TEXT", 100)
arcpy.AddField_management(provenance_table, "Fire_Year", "SHORT")

with arcpy.da.SearchCursor(temp_copy, ["Provenance_ID", "n_SourceID", "n_Source", "n_Fire_Label", "n_Year"]) as search_cursor, \
        arcpy.da.InsertCursor(provenance_table, ["Provenance_ID", "Original_ID", "Source", "Norm_Label", "Fire_Year"]) as insert_cursor:
    for pid, sid, source, label, year in search_cursor:
        update_label = normalize_label(label)
        insert_cursor.insertRow((pid, sid, source, update_label, year))

# Export copy with true duplicates assigned
arcpy.CopyFeatures_management(temp_copy, final_output)

# Clean up
arcpy.Delete_management(temp_copy)
