import geopandas as gpd
import sys
import os
import pandas as pd

__all__ = ['check_osc_duplicates', 'check_invalid_cable_refs', 'report_splice_counts_by_closure']
#########################################################################
#######################check_invalid_cable_refs##########################
#########################################################################

def check_invalid_cable_refs(workspace):
    """
    Checks all cable piece shapefiles against their corresponding cable shapefiles
    for invalid or missing CableID references.

    Parameters:
    workspace (str): Path to the Comsof output folder

    Returns:
    None - prints the validation result per cable type
    """
    # Define cable types and file naming
    cable_types = [
        "Feeder", 
        "Drop", 
        "PrimDistribution", 
        "Distribution"
    ]

    print(f"🔍 Checking CableID references in workspace:\n{workspace}\n")

    for layer in cable_types:
        cable_file = f"OUT_{layer}Cables.shp"
        piece_file = f"OUT_{layer}CablePieces.shp"

        cable_path = os.path.join(workspace, cable_file)
        piece_path = os.path.join(workspace, piece_file)

        if not os.path.exists(cable_path):
            print(f"⚠️ Cable file missing: {cable_file}")
            continue
        if not os.path.exists(piece_path):
            print(f"⚠️ Cable piece file missing: {piece_file}")
            continue

        # Load shapefiles
        cables = gpd.read_file(cable_path)
        pieces = gpd.read_file(piece_path)

        # Check for invalid CableID references
        valid_ids = set(cables["CABLE_ID"])
        invalid_pieces = pieces[~pieces["CABLE_ID"].isin(valid_ids)]

        if invalid_pieces.empty:
            print(f"✅ {layer}CablePieces: All CABLE_IDs are valid.")
        else:
            print(f"❌ {layer}CablePieces: Found {len(invalid_pieces)} invalid CableID references.")
            print(invalid_pieces[["CABLE_ID"]].drop_duplicates().to_string(index=False))
        print("-" * 60)

#########################################################################
###########################check_osc_duplicates##########################
#########################################################################

def check_osc_duplicates(workspace):
    """
    Checks for duplicated OSC values in the OUT_Closures.shp's LINKED_AGG column.
    
    Args:
        workspace (str): Path to the directory containing OUT_Closures.shp
    
    Returns:
        bool: True if duplicates found, False if no duplicates, None if errors occurred
    """
    # Construct full path to shapefile
    shapefile_path = os.path.join(workspace, "OUT_Closures.shp")
    
    # Verify file exists
    if not os.path.isfile(shapefile_path):
        print(f"⛔ Error: OUT_Closures.shp not found in workspace: {workspace}")
        return None

    try:
        # Read shapefile
        gdf = gpd.read_file(shapefile_path)
    except Exception as e:
        print(f"⛔ Error reading shapefile: {e}")
        return None

    # Check for required column
    if 'LINKED_AGG' not in gdf.columns:
        print("⛔ Error: 'LINKED_AGG' column not found in the shapefile")
        return None

    # Check for duplicates
    duplicates = gdf['LINKED_AGG'].duplicated(keep=False)
    
    if duplicates.any():
        print("\n⚠️  We have a problem of duplicated OSCs! ⚠️")
        print(f"Total duplicated entries: {duplicates.sum()}")
        
        duplicates_df = gdf[duplicates]['LINKED_AGG'].value_counts().reset_index()
        duplicates_df.columns = ['OSC Value', 'Duplicate Count']
        
        print("\nDuplicate occurrences:")
        print(duplicates_df.to_string(index=False))
        return True
    else:
        print("\n✅ Everything is okay - no duplicated OSCs found!")
        return False
    
#########################################################################
###########################check_splice_overload##########################
#########################################################################

def report_splice_counts_by_closure(workspace):
    """
    Reports the number of splices per closure in the Comsof export directory,
    grouped by closure type (IDENTIFIER).

    Parameters:
    workspace (str): Path to the Comsof output folder

    Returns:
    None – prints a formatted table
    """
    closure_file = os.path.join(workspace, "OUT_Closures.shp")
    splice_file = os.path.join(workspace, "OUT_Splices.shp")

    print(f"\n🔍 Reporting splices per closure type in:\n{workspace}\n")

    if not os.path.exists(closure_file):
        print("❌ Missing file: OUT_Closures.shp")
        return
    if not os.path.exists(splice_file):
        print("❌ Missing file: OUT_Splices.shp")
        return

    # Load shapefiles
    closures = gpd.read_file(closure_file)
    splices = gpd.read_file(splice_file)

    # Count splices per closure ID
    splice_counts = splices["ID"].value_counts().reset_index()
    splice_counts.columns = ["ID", "SpliceCount"]

    # Merge counts into closures
    closures["ID"] = closures["ID"].astype(str)
    splice_counts["ID"] = splice_counts["ID"].astype(str)
    report_df = closures[["IDENTIFIER", "ID"]].copy()
    report_df = report_df.merge(splice_counts, on="ID", how="left")
    report_df["SpliceCount"] = report_df["SpliceCount"].fillna(0).astype(int)

    # Sort and print
    report_df.sort_values(by="SpliceCount", ascending=False, inplace=True)

    print(f"{'Closure Type (IDENTIFIER)':<30} {'Closure ID (ID)':<20} {'# Splices':<10}")
    print("-" * 65)

    for _, row in report_df.iterrows():
        identifier = row['IDENTIFIER'] if pd.notnull(row['IDENTIFIER']) else 'N/A'
        closure_id = str(row['ID']) if pd.notnull(row['ID']) else 'N/A'
        splice_count = row['SpliceCount']
        print(f"{identifier:<30} {closure_id:<20} {splice_count:<10}")

    print("\n✅ Report complete.\n")



    


