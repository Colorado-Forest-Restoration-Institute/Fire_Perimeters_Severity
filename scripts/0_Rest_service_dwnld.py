''' 
WORKING - IN PROGRESS - CODE NOT COMPLETED
Code to download data directly from online sources of record to feed into script 1
'''


# Import libraries
import arcpy
import os
import urllib.request
from zipfile import ZipFile

arcpy.env.overwriteOutput = True

# Define target spatial reference
target_sr = arcpy.SpatialReference(26913)  # NAD 1983 UTM Zone 13N

arcpy.env.workspace = r'E:\CFRI\Colorado_Fire_Severity\Fire_Perimeters\UPDATE'
fldr = arcpy.env.workspace
scratch_workspace = os.path.join(fldr, 'scratch')
scratch_gdb = os.path.join(fldr, 'dwnld_perimeters.gdb')

CO_perim = r"E:\CFRI\BASE_LAYER_DATA\GENERAL_DATA_LAYERS\ADMINISTRATIVE_BOUNDARIES\US_States_Colorado.shp"

# Perimeter URLs
##MTBS_url = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MTBS_01/MapServer/63" ### Currently incomplete ###
wfigs_interagency_url = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/ArcGIS/rest/services/WFIGS_Interagency_Perimeters/FeatureServer/0"
wfigs_historical_url = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/ArcGIS/rest/services/InterAgencyFirePerimeterHistory_All_Years_View/FeatureServer/0"
geomac_url = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/ArcGIS/rest/services/Historic_Geomac_Perimeters_Combined_2000_2018/FeatureServer/0"
blm_veg_url = "https://gis.blm.gov/coarcgis/rest/services/vegetation/BLM_Colorado_Vegetation_Treatment_Area_Completed_Polygons/FeatureServer/23"
#usfs_url = "htts://data.fs.usda.gov/govdata/edw/edw_resources/fc/S_USA_Actv_CommonAttribute_PL.gdb.zip ## NEEDS TESTING


def import_feature_service_filter(feature_service_url, output_fc, filtered_perimeter, CO_perim):
    """
    Downloads a feature service URL, saves to output_fc, and clips data to Colorado.
    """
    # Download data
    try:
        print("Loading feature service...")
        feature_set = arcpy.FeatureSet()
        feature_set.load(feature_service_url)
        temp_result = arcpy.CopyFeatures_management(feature_set, output_fc)
        temp_fc = temp_result.getOutput(0)
        print(f"Feature service data save to {temp_fc}")
    except Exception as e:
        print(f"Error loading or saving feature service data: {e}")
        return

    # Project data to NAD 1983 UTM Zone 13N
    try:
        print(f"Projecting to NAD 83 UTM Zone 13N ({target_sr.name})...")
        projected_fc = arcpy.Project_management(temp_fc, "projected_fc.shp", target_sr)
    except Exception as e:
        print(f"Error projecting data: {e}")
        return

    # Clip to Colorado extent
    print("Clipping to Colorado extent...")
    try:
        arcpy.MakeFeatureLayer_management(projected_fc, "fires_fc_lyr")
        arcpy.SelectLayerByLocation_management(
            in_layer="fires_fc_lyr",
            overlap_type="INTERSECT",
            select_features=CO_perim
        )
        arcpy.CopyFeatures_management("fires_fc_lyr", filtered_perimeter)
        print(f"Clipped data saved to {filtered_perimeter}")
    except Exception as e:
        print(f"Error during clip/selection: {e}")

    # Cleanup
    print("Cleaning up interim data...")
    try:
        if arcpy.Exists(temp_fc):
            arcpy.Delete_management(temp_fc)
        if arcpy.Exists(output_fc):
            arcpy.Delete_management(output_fc)
        if arcpy.Exists(projected_fc):
            arcpy.Delete_management(projected_fc)
    except Exception as e:
        print(f"Cleanup error: {e}")


# Download data
scratch_out = os.path.join(scratch_gdb, "tmp_output")

# 1 MTBS
# Currently there is an issue with the map service that does not download all of the fires
#print("!Downloading MTBS")
#import_feature_service_filter(MTBS_url,
                              #scratch_out,
                              #os.path.join(scratch_gdb, "mtbs_dwnld"),
                              #CO_perim)

# 2 WFIGS Current
print("!Downloading WFIGS Current")
import_feature_service_filter(wfigs_interagency_url,
                              scratch_out,
                              os.path.join(scratch_gdb, "wfigs_current_dwnld"),
                              CO_perim)

# 3 WFIGS Historical
print("!Downloading WFIGS Historical")
# noinspection PyNoneFunctionAssignment
import_feature_service_filter(wfigs_historical_url,
                              scratch_out,
                              os.path.join(scratch_gdb, "wfigs_historical_dwnld"),
                              CO_perim)

# 4 GeoMAC
print("!Downloading GeoMAC")
import_feature_service_filter(geomac_url,
                              scratch_out,
                              os.path.join(scratch_gdb, "geomac_dwnld"),
                              CO_perim)

# 5 BLM
print("!Downloading BLM")
import_feature_service_filter(blm_veg_url,
                              scratch_out,
                              os.path.join(scratch_gdb, "blm_dwnld"),
                              CO_perim)

# 6 USFS Fire Perimeters
# ## Takes too long to run
#print("!Downloading USFS")
#import_feature_service_filter(usfs_url,
#                              scratch_out,
#                              os.path.join(scratch_gdb, "usfs_dwnld"),
#                              CO_perim)
