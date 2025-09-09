"""
Finalize Colorado Fire Perimeter Updates

Purpose:
--------
This script finalizes the Colorado fire perimeter dataset by:
1. Selecting the "best" record for each set of duplicate fire perimeters
   using a defined field priority system.
2. Dissolving duplicates into a single perimeter with normalized attributes.
3. Assigning unique Fire IDs (MTBS-style IDs: CO + lat + lon + YYYYMMDD).
4. Calculating GIS Acres based on geometry.
5. Cleaning up fire names and labels.
6. Renaming/dropping fields to match the final schema.
7. Writing the cleaned dataset into the main geodatabase.

Workflow:
---------
Input:
- Scratch GDB containing the `duplication_check_output` feature class
  (results of earlier duplicate detection script).
- Final GDB: Colorado_Fire_Perimeters_1984_2024.gdb

Outputs:
--------
- Final feature class: Colorado_Fire_Perimeters_1984_2024

"""

import arcpy
import os
import re
from collections import defaultdict

arcpy.env.overwriteOutput = True

base_dir = r'E:\CFRI\Colorado_Fire_Severity\Fire_Perimeters'
update_dir = os.path.join(base_dir, 'UPDATE')
scratch_gdb = os.path.join(update_dir, 'perimeter_update.gdb')
arcpy.env.workspace = scratch_gdb

dupl_perimeters = os.path.join(scratch_gdb, 'duplication_check_output')

final_gdb = os.path.join(base_dir, 'Colorado_Fire_Perimeters_1984_2024.gdb')
final_perimeters = os.path.join(final_gdb, 'Colorado_Fire_Perimeters_1984_2024')

# Select best row data
print("Selecting best row of data based on priority among duplicates")
arcpy.MakeFeatureLayer_management(dupl_perimeters, "true_dupl_lyr")
grouped_rows = defaultdict(list)

fields_perimeters = ["n_Fire_ID",
                     "n_Fire_Name",
                     "n_Fire_Label",
                     "n_Year",
                     "n_StartMonth",
                     "n_StartDay",
                     "n_GIS_Acres",
                     "n_Fire_Type",
                     "n_Agency",
                     "n_Source",
                     "n_SourceID",
                     "Norm_Label", "Provenance_ID"]

all_fields = ["True_Duplicate", "n_Priority"] + fields_perimeters

with arcpy.da.SearchCursor("true_dupl_lyr", all_fields) as cursor:
    for row in cursor:
        flag_val = row[0]
        priority = row[1]
        field_values = dict(zip(fields_perimeters, row[2:]))

        if flag_val is not None:
            grouped_rows[flag_val].append({
                "priority": priority,
                **field_values
            })
            print(f"Duplicate Value: {flag_val} - {row}")
        else:
            print(f"⚠️ Skipping record with NULL True_Duplicate flag (OID unknown): {row}")

# Choose the best non_null source per intersect_group_field
best_rows = []

for intersect_group_field, rows in grouped_rows.items():
    # Sort rows by priority
    sorted_rows = sorted(rows, key=lambda x: x["priority"] if x["priority"] is not None else float('inf'))

    # Dict to hold best value for each field
    chosen_values = {field: None for field in fields_perimeters}

    # Get the first non-null value for each field by priority
    for field in fields_perimeters:
        for row in sorted_rows:
            n_value = row.get(field)
            if n_value not in [None, ""]:
                chosen_values[field] = n_value
                break

    # Print result
    print(f"Flag Field {intersect_group_field}: {sorted_rows}")
    for field in fields_perimeters:
        print(f"  {field} = {chosen_values[field]}")

    merge_dict = {'True_Duplicate': intersect_group_field} | {'n_Priority': sorted_rows[0]['priority']} | chosen_values
    best_rows.append(merge_dict)

# Build a lookup dictionary for fast access by intersect_group_field
update_lookup = {row["True_Duplicate"]: row for row in best_rows}

# Add "True_Duplicate" and "n_Priority" to fields to update list
fields_to_update = ["True_Duplicate", "n_Priority"] + fields_perimeters

# Use UpdateCursor to update the fields
with arcpy.da.UpdateCursor("true_dupl_lyr", fields_to_update) as cursor:
    for row in cursor:
        print(f"Updating row True Duplicate: {row[0]}, {row[4]}, {row[5]}")
        intersect_group_field = row[0]
        if intersect_group_field not in update_lookup:
            continue

        update_row = update_lookup[intersect_group_field]

        try:
            for i, field in enumerate(fields_to_update[1:], start=1):
                val = update_row.get(field)

                if val in ["", ""]:
                    val = None

                if val is None:
                    row[i] = None
                elif field in ["n_Year", "n_StartMonth", "n_StartDay", "n_Priority"]:
                    row[i] = int(val)
                elif field == "n_GIS_Acres":
                    row[i] = float(val)
                else:
                    row[i] = val

            cursor.updateRow(row)

        except Exception as e:
            print(f"⚠️ Error updating row with True_Duplicate = {intersect_group_field}: {e}")

out_dissolve = arcpy.Dissolve_management("true_dupl_lyr", os.path.join(scratch_gdb, "out_dissolve"),
                                         all_fields + ["Provenance_ID"])

# Create FIRE ID
# Check for OID field name
oid_field = [f.name for f in arcpy.ListFields(out_dissolve) if f.type == "OID"][0]
print(f"OID field name is: {oid_field}")

# Add counter as placeholder for Null month/day values
no_date_counter = 0
with arcpy.da.UpdateCursor(out_dissolve, [oid_field, "SHAPE@", "n_Year", "n_StartMonth", "n_StartDay", "n_Fire_ID"]) as cursor:
    for row in cursor:
        oid, shape, year, month_val, day_val, fire_id = row

        # If fire_id from MTBS already exists, skip update
        if fire_id is not None:
            print(f"ID STRING: {fire_id}  Length: {len(str(fire_id))} already exists!")
            continue    # Skip update

        # Create ID based on MTBS construction (CO + lat + long + YYYYMMDD) - 21 digits
        centroid = shape.centroid
        lat = str(centroid.Y).replace(".", "")
        lon = str(abs(centroid.X)).replace(".", "")

        # Format month
        if month_val is None:
            month = str(no_date_counter % 100).zfill(2)
            no_date_counter += 1
        else:
            month = str(month_val).zfill(2)

        # Format day
        if day_val is None:
            day = str(no_date_counter % 100).zfill(2)
            no_date_counter += 1
        else:
            day = str(day_val).zfill(2)

        # Build ID
        date_str = f"CO{lat[:6]}{lon[:5]}{year}{month}{day}"
        print(f"ID STRING: {date_str}   Length {len(date_str)} created!")

        row[5] = date_str
        cursor.updateRow(row)

# Calculate GIS acres
arcpy.CalculateField_management(out_dissolve, "n_GIS_Acres", "!shape.area@acres!", "PYTHON3")

# Rename Fire NAME and LABEL
with arcpy.da.UpdateCursor(out_dissolve, ["n_Fire_Name", "n_Fire_Label"]) as cursor:
    for row in cursor:
        row[0] = re.sub(r'\s+U(NIT)?[\s\w\-\\/]*$', '', row[0], flags=re.IGNORECASE) if row[0] else row[0]
        row[1] = re.sub(r'\s+U(NIT)?[\s\w\-\\/]*$', '', row[1], flags=re.IGNORECASE) if row[1] else row[1]
        cursor.updateRow(row)

# Change wildland fire use to wildfire
with arcpy.da.UpdateCursor(out_dissolve, ["n_Fire_Type"]) as cursor:
    for row in cursor:
        if row[0] == "Wildland Fire Use":
            row[0] = "Wildfire"
        cursor.updateRow(row)

# Rename/update final fields
keep_fields = ['objectid', 'shape', 'shape_length', 'shape_area', "provenance_id"]  # all lowercase
fields = [f.name for f in arcpy.ListFields(out_dissolve)]
print(fields)

arcpy.DeleteField_management(out_dissolve, 'n_Priority')

for old_field in fields:
    old_field_lower = old_field.lower()
    if old_field.startswith("n_"):
        new_field = old_field[2:]
        try:
            arcpy.AlterField_management(out_dissolve, old_field, new_field, new_field)
            print(f"Renamed {old_field} to {new_field}")
        except Exception as e:
            print(f"Failed to rename {old_field}: {e}")
    elif old_field_lower not in keep_fields and not any(old_field == f[2:] for f in fields if f.startswith("n_")):
        try:
            arcpy.DeleteField_management(out_dissolve, old_field)
            print(f"Deleted {old_field}")
        except:
            print(f"{old_field} not deleted")

arcpy.CopyFeatures_management(out_dissolve, final_perimeters)

# Clean up
print("Cleaning up files")
arcpy.Delete_management(out_dissolve)
