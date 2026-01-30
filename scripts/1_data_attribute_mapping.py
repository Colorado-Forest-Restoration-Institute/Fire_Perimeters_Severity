"""
Colorado Fire Perimeter Integration and Attribute Mapping Script
------------------------------------------

This script prepares and standardizes wildfire and prescribed fire perimeter datasets
from multiple sources into a single geodatabase for further analysis. It applies a
consistent field schema, filters features by year, and merges outputs into a unified
feature class. Sources currently included:

    - MTBS
    - WFIGS (Interagency & Historical)
    - GeoMAC
    - BLM Colorado
    - USFS FACTS

⚠ Pre-processing required:
At this stage, the script assumes that perimeter data from the various sources has
already been downloaded, clipped to Colorado, and stored in a geodatabase called:

    dwnld_perimeters.gdb

This geodatabase should reside inside the UPDATE folder defined in `base_dir`.
Each source must be placed in `dwnld_perimeters.gdb` under the expected
feature class names (e.g., mtbs_download, wfigs_interagency_download, etc.).

Example directory structure:

    E:\CFRI\Colorado_Fire_Severity\Fire_Perimeters\
        ├── UPDATE\
        │     ├── dwnld_perimeters.gdb\
        │     │      ├── mtbs_download
        │     │      ├── wfigs_interagency_download
        │     │      ├── wfigs_historical_download
        │     │      ├── geomac_download
        │     │      ├── blm_download
        │     │      └── usfs_download
        │     └── perimeter_update.gdb   (scratch workspace, created by script)

The script then:
    - Copies and standardizes attributes across datasets
    - Adds missing fields to match a final schema
    - Applies mapping rules to harmonize naming, dates, and identifiers
    - Filters perimeters to a given year range (default: 1984–2024)
    - Selects prescribed fire treatments for BLM and USFS
    - Merges all outputs into a single feature class:
        raw_Colorado_Fire_Perimeters_duplicates
    - Repairs geometry and removes extraneous fields

Future enhancements will include automating the pre-processing steps so that
downloaded datasets can be ingested directly.
"""

import arcpy
import os

# --- Configurable Base Directories ---
base_dir = r'C:\Users\semue\Documents\GITHUB\Fire_Perimeters_Severity'
data_dir = os.path.join(base_dir, 'data')
download_gdb = os.path.join(data_dir, 'dwnld_perimeters.gdb')
scratch_gdb = os.path.join(data_dir, 'perimeter_update.gdb')

arcpy.env.workspace = scratch_gdb
arcpy.env.overwriteOutput = True

# --- Temporary Outputs ---
tmp_mapping = os.path.join(scratch_gdb, "tmp_mapping")

# --- Final Output for Combined Perimeters ---
combined_perimeters = os.path.join(scratch_gdb, "raw_Colorado_Fire_Perimeters_duplicates")

dt_start = 2025  # START DATE for filter
dt_end = 2026  # END DATE for filter


def add_new_fields(fc, final_field_list):
    """ Add final gdb fields to perimeter feature classes """
    existing_fields = [f.name for f in arcpy.ListFields(fc)]
    for field_name, field_type in final_field_list.items():
        if field_name not in existing_fields:
            arcpy.AddField_management(fc, field_name, field_type)


def apply_mapping(fc, mapping, final_field_list):
    """ Update new fields in the feature class using the provided mapping """
    all_fields = list(set(mapping.keys()).union(fc_fields(fc)))

    with arcpy.da.UpdateCursor(fc, all_fields) as cursor:
        for row in cursor:
            row_dict = dict(zip(all_fields, row))
            updated_row = list(row)

            for field_name in final_field_list.keys():
                map_func = mapping.get(field_name)
                if map_func:
                    try:
                        value = map_func(row_dict)
                        updated_row[all_fields.index(field_name)] = value
                    except Exception as e:
                        print(f"Error processing field {field_name}: {e}")

            cursor.updateRow(updated_row)


def filter_by_year(fc, start_year, end_year, final_output):
    filter_years_clause = f"n_Year >= {start_year} AND n_Year <= {end_year}"
    arcpy.MakeFeatureLayer_management(fc, "year_filter_lyr", filter_years_clause)
    arcpy.CopyFeatures_management("year_filter_lyr", final_output)


def fc_fields(fc):
    """ Get a list of all field names in the feature class """
    return [f.name for f in arcpy.ListFields(fc)]


def process_fire_layer(input_fc, output_fc, mapping, final_field_list, final_output, start_year, end_year):
    """ Full process: add fields, apply mapping, and save to output"""
    print(f"Processing {input_fc}")
    arcpy.CopyFeatures_management(input_fc, output_fc)
    add_new_fields(output_fc, final_field_list)
    apply_mapping(output_fc, mapping, final_field_list)
    filter_by_year(output_fc, start_year, end_year, final_output)
    arcpy.Delete_management(output_fc)
    print(f"Saved output to {final_output}")


# Perimeter feature classes
#MTBS = os.path.join(download_gdb, "mtbs_download")
WFIGS_INTERAGENCY = os.path.join(download_gdb, "wfigs_interagency_download")
#WFIGS_HISTORICAL = os.path.join(download_gdb, "wfigs_historical_download")
#GEOMAC = os.path.join(download_gdb, "geomac_download")
#BLM = os.path.join(download_gdb, "blm_download")
#USFS = os.path.join(download_gdb, "usfs_download")


# Dictionary of final fields
final_fields = {"n_Fire_ID": "TEXT",
                "n_Fire_Name": "TEXT",
                "n_Fire_Label": "TEXT",
                "n_Year": "LONG",
                "n_StartMonth": "SHORT",
                "n_StartDay":"SHORT",
                "n_GIS_Acres": "FLOAT",
                "n_Fire_Type": "TEXT",
                "n_Agency": "TEXT",
                "n_Source": "TEXT",
                "n_SourceID": "TEXT",
                "n_Priority": "SHORT"
                }

# Dataset mappings

# MTBS
mtbs_mapping = {
    "n_Fire_ID": lambda row: row['Event_ID'],
    "n_Fire_Name": lambda row: 'Unknown' if row['Incid_Name'] == 'UNNAMED' else row['Incid_Name'],
    "n_Fire_Label": lambda row: row['Incid_Name'].title() if row['Incid_Name'] else None,
    "n_Year": lambda row: row['Ig_Date'].year if row['Ig_Date'] else None,
    "n_StartMonth": lambda row: row['Ig_Date'].month if row['Ig_Date'] else None,
    "n_StartDay": lambda row: row['Ig_Date'].day if row['Ig_Date'] else None,
    "n_GIS_Acres": lambda row: None,
    "n_Fire_Type": lambda row: row['Incid_Type'],
    "n_Agency": lambda row: None,
    "n_Source": lambda row: 'MTBS',
    "n_SourceID": lambda row: row['Event_ID'],
    "n_Priority": lambda row: '1'
    }

# WFIGS interagency
wfigs_interagency_mapping = {
    "n_Fire_ID": lambda row: None,
    "n_Fire_Name": lambda row: row['poly_IncidentName'],
    "n_Fire_Label": lambda row: row['poly_IncidentName'].title() if row['poly_IncidentName'] else None,
    "n_Year": lambda row: row['attr_FireDiscoveryDateTime'].year if row['attr_FireDiscoveryDateTime'] else None,
    "n_StartMonth": lambda row: row['attr_FireDiscoveryDateTime'].month if row['attr_FireDiscoveryDateTime'] else None,
    "n_StartDay": lambda row: row['attr_FireDiscoveryDateTime'].day if row['attr_FireDiscoveryDateTime'] else None,
    "n_GIS_Acres": lambda row: None,
    "n_Fire_Type": lambda row: 'Prescribed Fire' if row['attr_IncidentTypeCategory'] == 'RX' else 'Wildfire',
    "n_Agency": lambda row: row['attr_POOProtectingAgency'],
    "n_Source": lambda row: 'WFIGS Interagency',
    "n_SourceID": lambda row: row['attr_UniqueFireIdentifier'],
    "n_Priority": lambda row: '2'
    }


# WFIGS historical
wfigs_historical_mapping = {
    "n_Fire_ID": lambda row: None,
    "n_Fire_Name": lambda row: row['INCIDENT'],
    "n_Fire_Label": lambda row: row['INCIDENT'].title() if row['INCIDENT'] else None,
    "n_Year": lambda row: row['FIRE_YEAR'],
    "n_StartMonth": lambda row: None,
    "n_StartDay": lambda row: None,
    "n_GIS_Acres": lambda row: None,
    "n_Fire_Type": lambda row: 'Wildfire' if row['FEATURE_CA'] and row['FEATURE_CA'].startswith('Wildfire') else 'Prescribed Fire',
    "n_Agency": lambda row: row['AGENCY'],
    "n_Source": lambda row: 'WFIGS Historical',
    "n_SourceID": lambda row: row['UNQE_FIRE_'] if row['UNQE_FIRE_'] else None,
    "n_Priority": lambda row: '3'
    }

# GeoMAC
geomac_mapping = {
    "n_Fire_ID": lambda row: None,
    "n_Fire_Name": lambda row: row['incidentname'],
    "n_Fire_Label": lambda row: row['incidentname'].title() if row['incidentname'] else None,
    "n_Year": lambda row: row['fireyear'],
    "n_StartMonth": lambda row: row['perimeterdatetime'].month if row['perimeterdatetime'] else None,
    "n_StartDay": lambda row: row['perimeterdatetime'].day if row['perimeterdatetime'] else None,
    "n_GIS_Acres": lambda row: None,
    "n_Fire_Type": lambda row: 'Wildfire',
    "n_Agency": lambda row: row['agency'],
    "n_Source": lambda row: 'Geomac',
    "n_SourceID": lambda row: row['uniquefireidentifier'] if row['uniquefireidentifier'] else None,
    "n_Priority": lambda row: "4"
    }

# BLM Colorado
blm_mapping = {
    "n_Fire_ID": lambda row: None,
    "n_Fire_Name": lambda row: row['TRTMNT_NM'],
    "n_Fire_Label": lambda row: row['TRTMNT_NM'].title() if row['TRTMNT_NM'] else None,
    "n_Year": lambda row: row['TRTMNT_START_DT'].year if row['TRTMNT_START_DT'] else None,
    "n_StartMonth": lambda row: row['TRTMNT_START_DT'].month if row['TRTMNT_START_DT'] else None,
    "n_StartDay": lambda row: row['TRTMNT_START_DT'].day if row['TRTMNT_START_DT'] else None,
    "n_GIS_Acres": lambda row: None,
    "n_Fire_Type": lambda row: 'Prescribed Fire',
    "n_Agency": lambda row: 'BLM',
    "n_Source": lambda row: 'BLM CO',
    "n_SourceID": lambda row: row['UNIQUE_ID'] if row['UNIQUE_ID'] else None,
    "n_Priority": lambda row: '5'
    }

# USFS FACTS Common Attributtes
usfs_mapping = {
    "n_Fire_ID": lambda row: None,
    "n_Fire_Name": lambda row: row['NAME'],
    "n_Fire_Label": lambda row: row['NAME'].title() if row['NAME'] else None,
    "n_Year": lambda row: row['DATE_COMPLETED'].year if row['DATE_COMPLETED'] else None,
    "n_StartMonth": lambda row: row['DATE_COMPLETED'].month if row['DATE_COMPLETED'] else None,
    "n_StartDay": lambda row: row['DATE_COMPLETED'].day if row['DATE_COMPLETED'] else None,
    "n_GIS_Acres": lambda row: None,
    "n_Fire_Type": lambda row: "Prescribed Fire",
    "n_Agency": lambda row: 'USFS',
    "n_Source": lambda row: 'USFS FACTS',
    "n_SourceID": lambda row: row['EVENT_CN'],
    "n_Priority": lambda row: "6"
    }


# Run field updates for each layer
tmp_mapping = os.path.join(scratch_gdb, "tmp_mapping")

# MTBS
#process_fire_layer(MTBS, tmp_mapping, mtbs_mapping, final_fields,
#                   os.path.join(scratch_gdb, 'mapping_mtbs'), dt_start, dt_end)

# WFIGS interagency
process_fire_layer(WFIGS_INTERAGENCY, tmp_mapping, wfigs_interagency_mapping, final_fields,
                   os.path.join(scratch_gdb, 'mapping_wfigs_interagency'), dt_start, dt_end)

# WFIGS historical
#process_fire_layer(WFIGS_HISTORICAL, tmp_mapping, wfigs_historical_mapping, final_fields,
#                   os.path.join(scratch_gdb, 'mapping_wfigs_historical'), dt_start, dt_end)

# GeoMAC
#process_fire_layer(GEOMAC, tmp_mapping, geomac_mapping, final_fields,
#                   os.path.join(scratch_gdb, 'mapping_geomac'), dt_start, dt_end)
'''
# BLM Colorado
# Select prescribed fire activities
blm_where_clause = (
    "TRTMNT_TYPE_CD = 3 AND "
    "UPPER(TRTMNT_NM) NOT LIKE '%PILE%' AND "
    "UPPER(TRTMNT_COMMENTS) NOT LIKE '%PILE%' AND "
    "UPPER(TRTMNT_NM) NOT LIKE '%PILING%' AND "
    "UPPER(TRTMNT_COMMENTS) NOT LIKE '%PILING%' AND "
    "UPPER(TRTMNT_NM) NOT LIKE '%WILDFIRE%' AND "
    "UPPER(TRTMNT_COMMENTS) NOT LIKE '%WILDFIRE%' AND "
    "UPPER(TRTMNT_NM) NOT LIKE '%FIRE USE%' AND "
    "UPPER(TRTMNT_COMMENTS) NOT LIKE '%FIRE USE%'"
)
arcpy.MakeFeatureLayer_management(BLM, "blm_lyr", blm_where_clause)
process_fire_layer("blm_lyr", tmp_mapping, blm_mapping, final_fields,
                   os.path.join(scratch_gdb, 'mapping_blm'), dt_start, dt_end)

# USFS FACTS Common Attributes
# Select prescribed fire activities
FACTS_where_clause = (
    "ACTIVITY = 'Broadcast Burning - Covers a majority of the unit' OR "
    "ACTIVITY = 'Control of Understory Vegetation- Burning' OR "
    "ACTIVITY = 'Site Preparation for Natural Regeneration - Burning' OR "
    "ACTIVITY = 'Site Preparation for Planting - Burning' OR "
    "ACTIVITY = 'Underburn - Low Intensity (Majority of Unit)' "
)
arcpy.MakeFeatureLayer_management(USFS, "usfs_lyr", FACTS_where_clause)
process_fire_layer("usfs_lyr", tmp_mapping, usfs_mapping, final_fields,
                   os.path.join(scratch_gdb, 'mapping_usfs'), dt_start, dt_end)
'''
# Combine all perimeters
mapping_list = arcpy.ListFeatureClasses("mapping_*")
perimeters_merge = arcpy.Merge_management(mapping_list,
                                          os.path.join(scratch_gdb, "raw_Colorado_Fire_Perimeters_duplicates"))
perimeters_merge_path = perimeters_merge.getOutput(0)

# Repair geometry of final layer
arcpy.RepairGeometry_management(perimeters_merge_path)

# Delete extraneous fields
print("Deleting unnecessary fields")
perimeter_fields = set(final_fields.keys())
merge_fields = [f.name for f in arcpy.ListFields(perimeters_merge_path)]
for fld in merge_fields:
    if fld not in perimeter_fields and fld.lower() not in ['objectid', 'shape', 'shape_length', 'shape_area']:
        try:
            arcpy.DeleteField_management(perimeters_merge_path, fld)
        except:
            print(f"{fld} not deleted")

